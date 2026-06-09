import os
from datasets import load_dataset

# Absolute path to your JSONL dataset
JSONL_PATH = "/Users/lisara/Documents/desktriage-ai/backend/train_dataset.jsonl"

# Your exact case-sensitive Hugging Face destination
TARGET_REPO = "Lisara/desktriage-dataset"

# Natively extract your token from your environment configuration
HF_TOKEN = os.environ.get("HF_TOKEN")

if not HF_TOKEN:
    print("❌ ERROR: Could not find 'HF_TOKEN' in your environment variables!")
    print("👉 Make sure you ran 'export HF_TOKEN=hf_...' or loaded your .env file.")
    exit(1)

print(f"🔄 Reading dataset from: {JSONL_PATH}")

try:
    # 1. Parse your specific file natively into an Apache Arrow memory structure
    dataset = load_dataset("json", data_files=JSONL_PATH)
    print("✅ File successfully loaded and verified.")
    
    # 2. Push it securely to the hub as a private repository
    print(f"🛰️ Uploading securely to huggingface.co/datasets/{TARGET_REPO}...")
    dataset.push_to_hub(TARGET_REPO, token=HF_TOKEN, private=True)
    
    print("\n🎉 SUCCESS! Your dataset is safely stored in your private cloud hub.")
    print(f"🔗 Cloud Destination: https://huggingface.co/datasets/{TARGET_REPO}")

except Exception as e:
    print(f"\n❌ UPLOAD FAILED: {str(e)}")