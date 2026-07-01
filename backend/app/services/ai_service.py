"""
backend/app/services/ai_service.py
====================================
Singleton AI inference service for DeskTriage.

Loads the fine-tuned mlx-community/Meta-Llama-3.1-8B-Instruct-4bit model
with LoRA adapters once at server startup and exposes generate_triage().

The model was trained to respond in strict JSON format:
  { "department": "...", "priority": "...", "llm_draft_reply": "..." }

Valid department values:  IT_Support | Finance | HR
Valid priority values:    Low | Medium | High | Critical
"""

import os
import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Module-level singletons (populated by load_model()) ──────────────────────
_model   = None
_tokenizer = None

# ── Absolute path to adapters (relative to backend/ working directory) ────────
BASE_MODEL    = os.getenv("MLX_BASE_MODEL", "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit")
ADAPTER_PATH  = os.getenv("MLX_ADAPTER_PATH", "./m5_adapters_8b")

# ── Modal Cloud Inference Settings ──────────────────────────────────────────
USE_MODAL_INFERENCE = os.getenv("USE_MODAL_INFERENCE", "false").lower() == "true"
MODAL_ENDPOINT_URL  = os.getenv("MODAL_ENDPOINT_URL", "")

# ── Safe fallback if model fails to classify ─────────────────────────────────
FALLBACK_RESULT = {
    "department":    "IT_Support",
    "priority":      "Medium",
    "ai_draft_reply": "",
    "ai_failed":     True,
}

# ── Exact system prompt the model was trained on ─────────────────────────────
SYSTEM_PROMPT = (
    "You are an expert corporate triage assistant. Analyze the employee's issue "
    "and return a valid JSON object containing department, priority, and llm_draft_reply. "
    "Do not include any introductory sentences, markdown blocks, or conversational filler."
)

SYSTEM_PROMPT_WITH_CONTEXT = (
    "You are an expert corporate triage assistant. Analyze the employee's issue using the provided Corporate SOPs context. "
    "In your draft reply, you MUST provide the specific troubleshooting steps, commands, or URLs described in the context. "
    "Return a valid JSON object containing department, priority, and llm_draft_reply. "
    "Do not include any introductory sentences, markdown blocks, or conversational filler."
)


def load_model() -> None:
    """
    Load the base MLX model and fuse the LoRA adapters.
    Called once during FastAPI lifespan startup.
    Subsequent calls are no-ops (idempotent guard).
    """
    global _model, _tokenizer

    if USE_MODAL_INFERENCE:
        logger.info("☁️ Using Modal inference endpoint — skipping local model load to save RAM.")
        return

    if _model is not None:
        logger.info("AI model already loaded — skipping duplicate load.")
        return

    try:
        from mlx_lm import load

        logger.info(f"🔄 Loading base model: {BASE_MODEL}")
        logger.info(f"🔄 Applying LoRA adapters from: {ADAPTER_PATH}")

        _model, _tokenizer = load(BASE_MODEL, adapter_path=ADAPTER_PATH)

        logger.info("✅ AI triage model loaded and ready.")

        # Warm-up: fire a silent prompt so the first real request is fast
        _run_warm_up()

    except Exception as exc:
        logger.error(f"❌ CRITICAL: Failed to load AI model: {exc}")
        logger.warning("⚠️  System will continue without AI inference. Tickets will use fallback values.")


def _run_warm_up() -> None:
    """
    Send a minimal warm-up prompt to JIT-compile the model graph.
    Keeps the first employee submission snappy.
    """
    try:
        logger.info("🔥 Running model warm-up...")
        _generate_raw("Test connectivity.")
        logger.info("✅ Model warm-up complete.")
    except Exception as exc:
        logger.warning(f"⚠️  Warm-up failed (non-fatal): {exc}")


def _build_prompt(title: str, description: str, context: str = "") -> str:
    """
    Construct the exact ChatML prompt format the model was fine-tuned on,
    with optional retrieval-augmented context.
    """
    if context:
        user_message = f"Context from Corporate SOPs:\n{context}\n\nEmployee Issue:\nTitle: {title}\n\n{description}"
        system_prompt = SYSTEM_PROMPT_WITH_CONTEXT
    else:
        user_message = f"Title: {title}\n\n{description}"
        system_prompt = SYSTEM_PROMPT

    return (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{system_prompt}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )


def _generate_raw(user_text: str, max_tokens: int = 512) -> str:
    """
    Low-level generation call. Returns the raw model output string.
    """
    from mlx_lm import generate

    prompt = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n{user_text}<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )

    response = generate(
        _model,
        _tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        verbose=False,
    )
    return response.strip()


def _parse_json_output(raw: str) -> Optional[dict]:
    """
    Robustly extract a JSON object from model output.

    Strategy:
      1. Try direct json.loads() on the full output
      2. Extract the first {...} block using regex (handles markdown fences or preamble)
      3. Return None if all parsing fails
    """
    # 1. Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Regex extraction — find first { ... } block
    match = re.search(r'\{.*?\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 3. Wider search for multi-line JSON
    match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _validate_and_normalise(parsed: dict) -> dict:
    """
    Validate and normalise the model's parsed JSON output.
    Ensures only known department/priority values are accepted.
    Falls back to safe defaults for invalid values.
    """
    VALID_DEPARTMENTS = {"IT_Support", "Corporate_Finance", "HR_Operations"}
    VALID_PRIORITIES  = {"Low", "Medium", "High", "Critical"}

    department    = parsed.get("department", "IT_Support")
    priority      = parsed.get("priority", "Medium")
    draft_reply   = parsed.get("llm_draft_reply", "")

    # Normalise department — case-insensitive partial match as safety net
    if department not in VALID_DEPARTMENTS:
        dept_lower = department.lower()
        if "finance" in dept_lower:
            department = "Corporate_Finance"
        elif "hr" in dept_lower or "human" in dept_lower:
            department = "HR_Operations"
        else:
            department = "IT_Support"

    # Normalise priority — case-insensitive match
    if priority not in VALID_PRIORITIES:
        pri_lower = priority.lower()
        if "critical" in pri_lower:
            priority = "Critical"
        elif "high" in pri_lower:
            priority = "High"
        elif "low" in pri_lower:
            priority = "Low"
        else:
            priority = "Medium"

    return {
        "department":    department,
        "priority":      priority,
        "ai_draft_reply": str(draft_reply).strip(),
        "ai_failed":     False,
    }


def generate_triage(title: str, description: str) -> dict:
    """
    Main public interface.

    Given a ticket title and description, returns:
      {
        "department":    "IT_Support" | "Finance" | "HR",
        "priority":      "Low" | "Medium" | "High" | "Critical",
        "ai_draft_reply": "<draft reply text>",
        "ai_failed":     bool
      }

    Never raises — always returns a safe dict so tickets are never lost.
    """
    # 1. First, retrieve the augmented context from RAG (same for both local and cloud)
    try:
        from rag_engine.retriever import retrieve_context
        retrieved = retrieve_context(f"{title} {description}")
        context = retrieved.get("context", "")
    except Exception as e:
        logger.warning(f"⚠️ Failed to retrieve context: {e}")
        context = ""
    prompt = _build_prompt(title, description, context)
    # 2. Write diagnostics log (same as before)
    try:
        from datetime import datetime
        debug_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "triage_debug.log")
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n===================================================\n")
            f.write(f"TIME: {datetime.now().isoformat()}\n")
            f.write(f"TICKET TITLE: {title}\n")
            f.write(f"TICKET DESCRIPTION: {description}\n")
            f.write(f"RETIRED CONTEXT LENGTH: {len(context)}\n")
            f.write(f"RETIRED CONTEXT:\n{context}\n")
            f.write(f"FULL PROMPT SENT TO LLM:\n{prompt}\n")
            f.write(f"===================================================\n")
    except Exception as log_err:
        logger.warning(f"⚠️ Failed to write diagnostics to triage_debug.log: {log_err}")
    if USE_MODAL_INFERENCE:
        try:
            import requests # Make sure you have the 'requests' library installed
            
            logger.info(f"Sending classification request to Modal API: {MODAL_ENDPOINT_URL}")
            
            # Construct structured messages list for correct control token encoding in HuggingFace
            system_prompt = (
                "You are an expert corporate triage assistant. Analyze the employee's issue using the provided Corporate SOPs context. "
                "In your draft reply, you MUST provide the specific troubleshooting steps, commands, or URLs described in the context. "
                "Return a valid JSON object containing department, priority, and llm_draft_reply. "
                "Do not include any introductory sentences, markdown blocks, or conversational filler."
            )
            user_message = f"Context from Corporate SOPs:\n{context}\n\nEmployee Issue:\nTitle: {title}\n\n{description}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Send HTTP request to the Modal app URL
            response = requests.post(
                MODAL_ENDPOINT_URL,
                json={"messages": messages},
                timeout=120 # 120 seconds to account for possible cold start
            )
            response.raise_for_status()
            
            raw_output = response.json().get("result", "").strip()
            logger.debug(f"Raw Modal model output: {raw_output[:300]}")
            
            # Write response to diagnostics log
            try:
                with open(debug_log_path, "a", encoding="utf-8") as f:
                    f.write(f"RAW MODAL OUTPUT:\n{raw_output}\n")
                    f.write(f"===================================================\n")
            except Exception:
                pass
                
            parsed = _parse_json_output(raw_output)
            if parsed is None:
                logger.warning(f"⚠️ Could not parse JSON from Modal output: {raw_output[:200]}")
                fallback = FALLBACK_RESULT.copy()
                fallback["ai_draft_reply"] = raw_output
                return fallback
            return _validate_and_normalise(parsed)
        except Exception as exc:
            logger.error(f"❌ Modal inference failed: {exc}")
            return FALLBACK_RESULT.copy()
    # 4. Local MLX Fallback Path (old logic)
    if _model is None:
        logger.warning("⚠️ Local model not loaded. Returning fallback triage result.")
        return FALLBACK_RESULT.copy()
    try:
        from mlx_lm import generate
        raw_output = generate(
            _model,
            _tokenizer,
            prompt=prompt,
            max_tokens=512,
            verbose=False,
        )
        raw_output = raw_output.strip()
        logger.debug(f"Raw model output: {raw_output[:300]}")
        parsed = _parse_json_output(raw_output)
        if parsed is None:
            logger.warning(f"⚠️  Could not parse JSON from model output: {raw_output[:200]}")
            fallback = FALLBACK_RESULT.copy()
            fallback["ai_draft_reply"] = raw_output
            return fallback
        return _validate_and_normalise(parsed)
    except Exception as exc:
        logger.error(f"❌ generate_triage() failed: {exc}")
        return FALLBACK_RESULT.copy()
