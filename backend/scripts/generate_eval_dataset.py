"""
generate_eval_dataset.py
========================
Generates a brand-new, unseen synthetic evaluation dataset of 30 tickets
using OpenAI's Structured Outputs. Saves it to backend/data/eval_dataset.jsonl.
"""

import os
import sys
import json
import random
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Load config relative to script path
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "../.env"))

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("CRITICAL ERROR: OPENAI_API_KEY not found in active environment configs.")

client = OpenAI()

class SyntheticTicketItem(BaseModel):
    employee_problem_text: str = Field(description="The realistic corporate problem submitted by an employee.")
    predicted_department: str = Field(description="Must match exactly one: 'IT_Support', 'Finance', 'HR'")
    predicted_priority: str = Field(description="Must match exactly one: 'Low', 'Medium', 'High', 'Critical'")
    llm_draft_reply: str = Field(description="A helpful internal response draft in a highly professional corporate tone.")

class SyntheticBatchResponse(BaseModel):
    tickets: List[SyntheticTicketItem]

DEPARTMENTS = ["IT_Support", "Finance", "HR"]
TONES = [
    "frustrated and panicked", 
    "formal and business-oriented", 
    "brief and direct", 
    "confused with typos", 
    "overly wordy"
]
TOPICS = {
    "IT_Support": ["software crash", "hardware failure", "expired token", "VPN failure", "printer error", "access privileges"],
    "Finance": ["payroll mismatch", "invoice discrepancy", "expense report rejection", "direct deposit update", "bonus tax query"],
    "HR": ["paternity leave details", "health insurance onboard", "policy confirmation", "corporate vacation log", "performance review schedule"]
}

def build_dynamic_prompt(batch_size: int) -> str:
    target_dept = random.choice(DEPARTMENTS)
    chosen_topic = random.choice(TOPICS[target_dept])
    chosen_tone = random.choice(TONES)
    typo_instruction = "Include authentic typing errors, missing punctuation, or casual phrasing." if random.random() > 0.4 else "Keep the text clean."
    
    return f"""
    Generate exactly {batch_size} unique, distinct, and highly realistic employee support tickets.
    Focus heavily on the '{target_dept}' department, specifically dealing with '{chosen_topic}'.
    The employee perspective must be written in a '{chosen_tone}' tone.
    {typo_instruction}
    
    Ensure these tickets are completely new scenarios, distinct from any common templates.
    """

def main():
    total_target = 30
    batch_size = 10
    iterations = total_target // batch_size
    output_path = os.path.abspath(os.path.join(script_dir, "../data/eval_dataset.jsonl"))
    
    print(f"🚀 Generating {total_target} brand-new unseen evaluation tickets...")
    
    eval_records = []
    
    for i in range(iterations):
        prompt_instruction = build_dynamic_prompt(batch_size)
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a master dataset generation asset."},
                    {"role": "user", "content": prompt_instruction}
                ],
                response_format=SyntheticBatchResponse,
                temperature=0.95  # Slightly higher temp for extra variety
            )
            
            parsed_response = completion.choices[0].message.parsed
            
            for ticket in parsed_response.tickets:
                assistant_payload = {
                    "department": ticket.predicted_department,
                    "priority": ticket.predicted_priority,
                    "llm_draft_reply": ticket.llm_draft_reply
                }
                safe_json_string = json.dumps(assistant_payload, ensure_ascii=False)
                
                chatml_formatted_string = (
                    "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
                    "You are an expert corporate triage assistant. Analyze the employee's issue and return a valid JSON object containing department, priority, and llm_draft_reply.<|eot_id|>"
                    f"<|start_header_id|>user<|end_header_id|>\n\n{ticket.employee_problem_text}<|eot_id|>"
                    f"<|start_header_id|>assistant<|end_header_id|>\n\n{safe_json_string}<|eot_id|>"
                )
                
                eval_records.append({"text": chatml_formatted_string})
                
        except Exception as e:
            print(f"⚠️ Error generating batch {i+1}: {e}")
            continue

    with open(output_path, "w", encoding="utf-8") as f:
        for record in eval_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"🎉 Generation Complete! Exported {len(eval_records)} unseen tickets to '{output_path}'.")

if __name__ == "__main__":
    main()
