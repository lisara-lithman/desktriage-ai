"""
evaluate_triage.py
==================
Automated evaluation pipeline comparing the baseline un-tuned model 
versus the fine-tuned model (with LoRA adapters) on corporate triage tickets.

It measures:
1. JSON Parse Success Rate (Strict format adherence)
2. Department Classification Accuracy
3. Priority Classification Accuracy
4. Formatting Issues (e.g. markdown code fences, conversational preambles)
5. Average latency and output token lengths
"""

import os
import re
import json
import time
from typing import Tuple, Optional, Dict, Any

# Target model details
BASE_MODEL = "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit"
ADAPTER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../m5_adapters_8b"))
DATASET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/eval_dataset.jsonl"))
NUM_TEST_SAMPLES = 30  # Adjust as needed for speed vs precision

SYSTEM_PROMPT = (
    "You are an expert corporate triage assistant. Analyze the employee's issue "
    "and return a valid JSON object containing department, priority, and llm_draft_reply. "
    "Do not include any introductory sentences, markdown blocks, or conversational filler."
)

def parse_record(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Extracts the user problem text and the target assistant JSON output from 
    the raw training dataset line format.
    """
    user_match = re.search(r"<\|start_header_id\|>user<\|end_header_id\|>\n\n(.*?)<\|eot_id\|>", text, re.DOTALL)
    assistant_match = re.search(r"<\|start_header_id\|>assistant<\|end_header_id\|>\n\n(.*?)<\|eot_id\|>", text, re.DOTALL)
    
    if user_match and assistant_match:
        user_text = user_match.group(1).strip()
        assistant_json_str = assistant_match.group(1).strip()
        try:
            expected = json.loads(assistant_json_str)
            return user_text, expected
        except json.JSONDecodeError:
            return None
    return None

def build_prompt(user_text: str) -> str:
    """Builds standard Llama 3 ChatML template."""
    return (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n{user_text}<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )

def parse_model_json(raw_output: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, bool]]:
    """
    Tries to parse JSON and records if clean-up/regex was required.
    """
    flags = {
        "strict_json": False,
        "contains_markdown": False,
        "contains_preamble": False
    }
    
    clean_output = raw_output.strip()
    
    # Check for markdown code block formatting
    if "```" in clean_output:
        flags["contains_markdown"] = True
    
    # Try strict direct load
    try:
        parsed = json.loads(clean_output)
        flags["strict_json"] = True
        return parsed, flags
    except json.JSONDecodeError:
        pass

    # Try regex extraction - find first { ... } block
    match = re.search(r'\{.*?\}', clean_output, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            flags["contains_preamble"] = True
            return parsed, flags
        except json.JSONDecodeError:
            pass

    return None, flags

def evaluate_model(model, tokenizer, test_data: list, desc: str) -> Dict[str, Any]:
    """Runs inference across all test samples and computes metrics."""
    from mlx_lm import generate
    
    results = []
    print(f"\n🔄 Running evaluation for model: {desc}...")
    
    for idx, (user_text, expected) in enumerate(test_data):
        prompt = build_prompt(user_text)
        
        start_time = time.time()
        raw_output = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=256,
            verbose=False
        )
        latency = time.time() - start_time
        
        raw_output = raw_output.strip()
        parsed, flags = parse_model_json(raw_output)
        
        # Validation checks
        dept_match = False
        priority_match = False
        
        if parsed:
            dept_match = str(parsed.get("department", "")).lower() == str(expected.get("department", "")).lower()
            priority_match = str(parsed.get("priority", "")).lower() == str(expected.get("priority", "")).lower()
            
        results.append({
            "idx": idx + 1,
            "raw_output": raw_output,
            "parsed": parsed,
            "expected": expected,
            "flags": flags,
            "dept_match": dept_match,
            "priority_match": priority_match,
            "latency": latency,
            "char_count": len(raw_output)
        })
        
        print(f"  [{idx+1}/{len(test_data)}] Parse: {'✅' if parsed else '❌'} | Dept: {'✅' if dept_match else '❌'} | Priority: {'✅' if priority_match else '❌'} ({latency:.2f}s)")

    # Aggregate metrics
    total = len(test_data)
    parse_success = sum(1 for r in results if r["parsed"] is not None)
    strict_json = sum(1 for r in results if r["flags"]["strict_json"])
    markdown_fences = sum(1 for r in results if r["flags"]["contains_markdown"])
    preambles = sum(1 for r in results if r["flags"]["contains_preamble"])
    dept_accuracy = sum(1 for r in results if r["dept_match"])
    priority_accuracy = sum(1 for r in results if r["priority_match"])
    exact_match = sum(1 for r in results if r["dept_match"] and r["priority_match"] and r["parsed"] is not None)
    avg_latency = sum(r["latency"] for r in results) / total
    avg_chars = sum(r["char_count"] for r in results) / total
    
    return {
        "parse_success_rate": (parse_success / total) * 100,
        "strict_json_rate": (strict_json / total) * 100,
        "markdown_fences_rate": (markdown_fences / total) * 100,
        "preambles_rate": (preambles / total) * 100,
        "department_accuracy": (dept_accuracy / total) * 100,
        "priority_accuracy": (priority_accuracy / total) * 100,
        "exact_match_accuracy": (exact_match / total) * 100,
        "avg_latency": avg_latency,
        "avg_chars": avg_chars,
        "raw_results": results
    }

def main():
    # 1. Load test dataset slice
    print(f"📡 Loading dataset from '{DATASET_PATH}'...")
    if not os.path.exists(DATASET_PATH):
        print(f"❌ ERROR: Dataset path '{DATASET_PATH}' does not exist!")
        return
        
    test_data = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Pick the last N samples as test set (so they represent a clean slice)
    for line in reversed(lines):
        record = json.loads(line)
        parsed = parse_record(record.get("text", ""))
        if parsed:
            test_data.append(parsed)
            if len(test_data) >= NUM_TEST_SAMPLES:
                break
                
    if len(test_data) < NUM_TEST_SAMPLES:
        print(f"⚠️ Warning: Only found {len(test_data)} valid records out of target {NUM_TEST_SAMPLES}.")
    else:
        print(f"✅ Loaded {len(test_data)} test records.")

    from mlx_lm import load
    
    # 2. Evaluate Base Model (Un-tuned)
    print(f"\n🧠 Loading RAW BASE model: {BASE_MODEL}")
    base_model, base_tokenizer = load(BASE_MODEL)
    base_metrics = evaluate_model(base_model, base_tokenizer, test_data, "Base (Un-tuned)")
    
    # Unload / clean references to save memory before loading adapters
    del base_model
    del base_tokenizer
    
    # 3. Evaluate Fine-Tuned Model (LoRA adapters)
    print(f"\n🧠 Loading FINE-TUNED model with adapters: {ADAPTER_PATH}")
    ft_model, ft_tokenizer = load(BASE_MODEL, adapter_path=ADAPTER_PATH)
    ft_metrics = evaluate_model(ft_model, ft_tokenizer, test_data, "Fine-Tuned (adapters)")

    # 4. Generate beautiful Markdown report
    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../evaluation_report.md"))
    print(f"\n📝 Writing evaluation report to '{report_path}'...")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Model Evaluation Report: Base vs. Fine-Tuned Llama-3.1-8B\n\n")
        f.write("This report documents the performance comparison between the raw baseline model "
                "and the fine-tuned adapter version on internal corporate triage tickets.\n\n")
        
        f.write("## Summary Metrics\n\n")
        f.write("| Metric | Base (Un-tuned) | Fine-Tuned (Adapters) | Change |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        
        metrics_to_show = [
            ("JSON Parse Success Rate (Any Format)", "parse_success_rate", "%"),
            ("Strict JSON Output (No fences/filler)", "strict_json_rate", "%"),
            ("Markdown Fences Output (```json)", "markdown_fences_rate", "%"),
            ("Preamble / Conversational Filler", "preambles_rate", "%"),
            ("Department Classification Accuracy", "department_accuracy", "%"),
            ("Priority Classification Accuracy", "priority_accuracy", "%"),
            ("Perfect Triage Match (Strict + Correct)", "exact_match_accuracy", "%"),
            ("Average Generation Latency", "avg_latency", "s"),
            ("Average Output Character Length", "avg_chars", " chars")
        ]
        
        for name, key, unit in metrics_to_show:
            val_base = base_metrics[key]
            val_ft = ft_metrics[key]
            diff = val_ft - val_base
            diff_str = f"{'+' if diff >= 0 else ''}{diff:.1f}{unit}" if unit == "%" else f"{diff:+.2f}{unit}"
            
            f.write(f"| {name} | {val_base:.1f}{unit} | {val_ft:.1f}{unit} | **{diff_str}** |\n")
            
        f.write("\n\n## Sample Outputs Comparison\n\n")
        f.write("Here is a side-by-side comparison of the first 3 test samples:\n\n")
        
        for i in range(min(3, len(test_data))):
            user_text = test_data[i][0]
            expected = test_data[i][1]
            base_res = base_metrics["raw_results"][i]
            ft_res = ft_metrics["raw_results"][i]
            
            f.write(f"### Sample {i+1} Ticket Input\n")
            f.write(f"> **Input Text:** {user_text}\n\n")
            f.write(f"> **Expected JSON:** `{json.dumps(expected)}`\n\n")
            
            f.write("#### 🔴 Raw Base Output:\n")
            f.write(f"```text\n{base_res['raw_output']}\n```\n\n")
            
            f.write("#### 🟢 Raw Fine-Tuned Output:\n")
            f.write(f"```text\n{ft_res['raw_output']}\n```\n\n")
            f.write("---\n\n")

    # 5. Output Summary directly to Terminal
    print("\n=======================================================")
    print("               EVALUATION SUMMARY RESULTS              ")
    print("=======================================================")
    print(f"Metric                         | Base     | Fine-Tuned")
    print("-------------------------------------------------------")
    print(f"JSON Parse Success Rate        | {base_metrics['parse_success_rate']:6.1f}% | {ft_metrics['parse_success_rate']:10.1f}%")
    print(f"Strict JSON Rate (Clean)       | {base_metrics['strict_json_rate']:6.1f}% | {ft_metrics['strict_json_rate']:10.1f}%")
    print(f"Department Accuracy            | {base_metrics['department_accuracy']:6.1f}% | {ft_metrics['department_accuracy']:10.1f}%")
    print(f"Priority Accuracy              | {base_metrics['priority_accuracy']:6.1f}% | {ft_metrics['priority_accuracy']:10.1f}%")
    print(f"Perfect Match (Strict+Correct) | {base_metrics['exact_match_accuracy']:6.1f}% | {ft_metrics['exact_match_accuracy']:10.1f}%")
    print(f"Average Latency                | {base_metrics['avg_latency']:5.2f}s  | {ft_metrics['avg_latency']:9.2f}s")
    print(f"Average Output Length (chars)  | {base_metrics['avg_chars']:6.1f}  | {ft_metrics['avg_chars']:10.1f}")
    print("=======================================================")
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()
