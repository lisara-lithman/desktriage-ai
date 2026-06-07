import json
import httpx

# Pointing completely inward to your Mac's local system port
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:1b"

# Our classic multi-department messy test ticket
TEST_TICKET = (
    "Hey team, I started my paternity leave tracking log on the HR portal, but the webpage completely "
    "crashed mid-way through. Now my employee dashboard is frozen, I can't log back in, and I'm worried "
    "my direct deposit details for this month's payroll cycle didn't save correctly. Please fix my account!"
)

def run_local_baseline_test():
    # Constructing the raw ChatML prompt template manually for the local engine
    formatted_prompt = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "You are an expert corporate triage assistant. Analyze the employee's issue "
        "and return a valid JSON object containing department, priority, and llm_draft_reply. "
        "Do not include any introductory sentences, markdown blocks, or conversational filler.<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n{TEST_TICKET}<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
    
    # Configuration arguments built specifically for Ollama's API payload layout
    payload = {
        "model": MODEL_NAME,
        "prompt": formatted_prompt,
        "stream": False,         # False means wait and give us the full paragraph all at once
        "options": {
            "temperature": 0.1   # Keep it strictly analytical, killing random creativity
        },
        "raw": True              # Tells Ollama to respect our explicit Llama 3.2 ChatML formatting tags
    }
    
    print(f"🛰️ Sending ticket to your local Mac processing unit ({MODEL_NAME})...")
    
    try:
        # Fire the post request directly to your localhost port
        response = httpx.post(OLLAMA_URL, json=payload, timeout=30.0)
        result = response.json()
        raw_output = result.get("response", "").strip()
        
        print("\n📥 === [LOCAL BASELINE BEFORE SFT] RAW MODEL OUTPUT ===")
        print(raw_output)
        print("========================================================\n")
        
        # Rigorous production JSON verification pipeline
        try:
            json.loads(raw_output)
            print("✅ SUCCESS: The un-tuned local model unexpectedly returned perfect, parseable JSON!")
        except json.JSONDecodeError:
            print("❌ STACK FAILURE: The raw model failed formatting constraints.")
            print("👉 DIAGNOSIS: It chatted back, added markdown backticks, or split the text. "
                  "This confirms our FastAPI backend would throw an immediate crash without Fine-Tuning.")
            
    except Exception as e:
        print(f"❌ Connection to local Ollama service failed: {str(e)}")
        print("👉 Check if your download window finished or if Ollama is running in your Mac menu bar.")

if __name__ == "__main__":
    run_local_baseline_test()