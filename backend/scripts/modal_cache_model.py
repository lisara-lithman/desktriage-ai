import os
import modal

# 1. Define the persistent volume and the Modal App
model_volume = modal.Volume.from_name("desktriage-model-cache")
app = modal.App("desktriage-cache-model")

# 2. Define the Linux/Python environment for the container
image = (
    modal.Image.debian_slim()
    .pip_install(
        "transformers",
        "peft",
        "accelerate",
        "torch",
        "huggingface_hub"
    )
)

# 3. Define the download function, attaching the Volume and HF Secret
@app.function(
    image=image,
    volumes={"/cache": model_volume}, # Mounts volume to /cache inside container
    env={"HF_HOME": "/cache"},        # Redirects HF downloader to save inside /cache
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
    timeout=1200 # 20 minutes limit to download big weights
)
def download_model():
    from huggingface_hub import login
    from transformers import AutoTokenizer, AutoModelForCausalLM
    
    # Authenticate with HuggingFace
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN not found in environment variables!")
    login(token=hf_token)
    
    # We will cache the base model and your adapter weights
    base_model_id = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    adapter_id = "Lisara/desktriage-adapters"
    
    print(f"Downloading base tokenizer: {base_model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    
    print(f"Downloading base model weights (approx 15GB)...")
    # We use CPU to download/save weights first to save GPU credits
    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype="auto",
        device_map="cpu"
    )
    
    print(f"Downloading adapters: {adapter_id}...")
    # Load and download adapter weights
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, adapter_id)
    
    # Save everything locally to make sure it is fully written to the volume
    print("Saving tokenizer to cache volume...")
    tokenizer.save_pretrained("/cache/desktriage-model")
    print("Saving merged/adapted model weights to cache volume...")
    model.save_pretrained("/cache/desktriage-model")
    
    # Commit changes to Modal Volume
    model_volume.commit()
    print("Model download complete and saved to volume!")

# Entrypoint for local execution
@app.local_entrypoint()
def main():
    download_model.remote()