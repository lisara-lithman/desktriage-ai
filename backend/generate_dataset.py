"""
generate_dataset.py — Synthetic training dataset generator using OpenAI Structured Outputs.
Outputs data in industry-standard JSONL format for pure Hugging Face SFTTrainer ingestion.
Usage: Ensure your virtual environment is active and OPENAI_API_KEY is present in your .env
       python generate_dataset.py
"""

import os
import json
import random
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# Guardrail check for infrastructure API key mapping
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("CRITICAL ERROR: OPENAI_API_KEY not found in active environment configs.")

client = OpenAI()

# ─── 1. STRUCTURAL DATA SCHEMAS (PYDANTIC CONSTRAINTS) ───
class SyntheticTicketItem(BaseModel):
    employee_problem_text: str = Field(description="The realistic corporate problem submitted by an employee. Vary length, style, and include realistic casual human language.")
    predicted_department: str = Field(description="Must match exactly one of these choices: 'IT_Support', 'Finance', 'HR'")
    predicted_priority: str = Field(description="Must match exactly one of these choices: 'Low', 'Medium', 'High', 'Critical'")
    llm_draft_reply: str = Field(description="A helpful internal response draft answering the core employee issue in a highly professional corporate tone.")

class SyntheticBatchResponse(BaseModel):
    tickets: List[SyntheticTicketItem]

# ─── 2. MATRIX PARAMETERS TO FORCE VOCABULARY DIVERSITY ───
DEPARTMENTS = ["IT_Support", "Finance", "HR"]
TONES = [
    "highly frustrated and panicked", 
    "extremely formal and business-oriented", 
    "brief, short-sentence, and direct", 
    "confused and disorganized with typos", 
    "overly wordy with unnecessary details"
]
TOPICS = {
    "IT_Support": ["software crash", "hardware failure", "expired token", "VPN failure", "printer error", "access privileges"],
    "Finance": ["payroll mismatch", "invoice discrepancy", "expense report rejection", "direct deposit update", "bonus tax query"],
    "HR": ["paternity leave details", "health insurance onboard", "policy confirmation", "corporate vacation log", "performance review schedule"]
}

def build_dynamic_prompt(batch_size: int) -> str:
    """Creates an entirely different permutation instructions for every script loop iteration."""
    target_dept = random.choice(DEPARTMENTS)
    chosen_topic = random.choice(TOPICS[target_dept])
    chosen_tone = random.choice(TONES)
    typo_instruction = "Make sure to include authentic human typing errors, missing punctuation, or casual phrasing." if random.random() > 0.4 else "Keep the text clean but natural."
    
    return f"""
    You are an advanced synthetic data engine configured to build training datasets for corporate triage operations.
    Generate exactly {batch_size} unique, distinct, and highly realistic employee support tickets.
    
    Focus heavily on the '{target_dept}' department, specifically dealing with '{chosen_topic}'.
    The employee's writing perspective must be written in a '{chosen_tone}' tone.
    {typo_instruction}
    
    CRITICAL INSTRUCTIONS:
    - Never duplicate problems. Ensure each ticket has an entirely distinct background story context.
    - Do not use obvious keywords all the time. Sometimes write tickets that mention multiple departments but clearly belong to only one dominant team.
    """

# ─── 3. PIPELINE REPETITION WORKER LOOP ───
def run_dataset_generation_pipeline(total_target: int = 1000, batch_size: int = 10):
    iterations = total_target // batch_size
    output_path = "train_dataset.jsonl"
    
    print(f"🚀 Launching Synthetic Assembly Factory. Target: {total_target} rows via {iterations} loops...")
    
    # Open the file stream once and keep it open for efficient streaming writes
    with open(output_path, "w", encoding="utf-8") as f:
        
        # tqdm creates our dynamic progress tracking visualizer bar in terminal
        for i in tqdm(range(iterations), desc="Generating Batches"):
            prompt_instruction = build_dynamic_prompt(batch_size)
            
            try:
                # beta.chat.completions.parse forces OpenAI to guarantee strict JSON schema compliance
                completion = client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a master dataset generation asset. Your outputs must match the strict structured boundaries requested."},
                        {"role": "user", "content": prompt_instruction}
                    ],
                    response_format=SyntheticBatchResponse,
                    temperature=0.9
                )
                
                parsed_response = completion.choices[0].message.parsed
                
                # ─── 4. FORMAT INTO PURE LLAMA 3.2 CHATML STRUCTURES ───
                for ticket in parsed_response.tickets:
                    
                    # Safely compile the assistant's target output into a bulletproof JSON string first
                    # This prevents nested strings or newlines from corrupting our final dataset rows
                    assistant_payload = {
                        "department": ticket.predicted_department,
                        "priority": ticket.predicted_priority,
                        "llm_draft_reply": ticket.llm_draft_reply
                    }
                    safe_json_string = json.dumps(assistant_payload, ensure_ascii=False)
                    
                    # Wrap everything inside the strict Llama 3.2 system prompt template tags
                    chatml_formatted_string = (
                        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
                        "You are an expert corporate triage assistant. Analyze the employee's issue and return a valid JSON object containing department, priority, and llm_draft_reply.<|eot_id|>"
                        f"<|start_header_id|>user<|end_header_id|>\n\n{ticket.employee_problem_text}<|eot_id|>"
                        f"<|start_header_id|>assistant<|end_header_id|>\n\n{safe_json_string}<|eot_id|>"
                    )
                    
                    # Package row inside a clean dictionary mapped to the 'text' key
                    record = {"text": chatml_formatted_string}
                    
                    # Stream write directly to disk with a clean newline character
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    
            except Exception as e:
                print(f"\n⚠️ Intercepted processing failure in batch iteration {i+1}: {str(e)}. Shifting to next loop execution...")
                continue

    print(f"\n🏆 Generation Complete! Successfully exported pure JSONL format to '{output_path}'.")

if __name__ == "__main__":
    run_dataset_generation_pipeline(total_target=1000, batch_size=10)