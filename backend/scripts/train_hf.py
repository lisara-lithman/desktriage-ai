"""
train_hf.py
===========
Industry-standard PyTorch fine-tuning script using Hugging Face (Transformers, PEFT, TRL).
Configured for QLoRA (4-bit quantization + LoRA adapters) on Nvidia GPUs.

Integrations:
1. Direct data ingestion from Hugging Face Hub (Lisara/desktriage-dataset)
2. Experiment tracking via Weights & Biases (Wandb)
3. Automatic upload of final adapters to Hugging Face Hub

Run this on Google Colab (with T4 GPU):
Usage:
    pip install transformers peft trl bitsandbytes accelerate datasets wandb
    python train_hf.py
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

# Base Model and HF Destinations
BASE_MODEL_ID = "meta-llama/Meta-Llama-3.1-8B-Instruct"
DATASET_REPO = "Lisara/desktriage-dataset"
ADAPTER_REPO_ID = "Lisara/desktriage-adapters"
LOCAL_OUTPUT_DIR = "./hf_adapters_8b"

def main():
    print("🚀 Initializing Hugging Face QLoRA Training Pipeline...")
    
    # 1. Load Dataset directly from Hugging Face Hub
    print(f"📡 Loading private dataset from HF Hub: {DATASET_REPO}...")
    dataset = load_dataset(DATASET_REPO, token=True)
    
    # Handle both single split and multiple splits in the repo
    if "train" in dataset:
        dataset_split = dataset["train"]
    else:
        dataset_split = dataset
        
    # Split into train/validation (90/10) for training evaluation
    dataset_split = dataset_split.train_test_split(test_size=0.1, seed=42)
    print(f"✅ Dataset loaded. Train size: {len(dataset_split['train'])}, Val size: {len(dataset_split['test'])}")

    # 2. Configure 4-bit Quantization (bitsandbytes)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True
    )

    # 3. Load Base Model & Tokenizer
    print(f"🔄 Downloading/Loading Base Model: {BASE_MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, token=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        token=True
    )
    
    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)

    # 4. Configure LoRA parameters (matching our MLX parameters)
    peft_config = LoraConfig(
        r=8,
        lora_alpha=20,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    # No manual get_peft_model wrapping needed. SFTTrainer handles this internally when peft_config is provided.
    print("✅ LoRA configuration defined.")

    # 5. Define Training Configurations using SFTConfig
    sft_config = SFTConfig(
        output_dir=LOCAL_OUTPUT_DIR,
        dataset_text_field="text",
        max_length=1024,           # Changed from max_seq_length to max_length
        packing=False,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2, # Effective batch size = 4
        learning_rate=5e-5,            # Stabilized learning rate matching MLX
        logging_steps=10,
        max_steps=400,                 # Total iterations matching our local setup
        save_strategy="steps",
        save_steps=100,
        eval_strategy="steps",
        eval_steps=100,
        fp16=False,
        bf16=True,                     # Use bfloat16 precision for training stability
        optim="paged_adamw_8bit",      # High-efficiency memory optimizer
        warmup_steps=12,               # Fixed from warmup_ratio deprecation
        lr_scheduler_type="constant",  # Matches MLX schedule
        report_to="wandb"              # Logs graphs directly to Wandb
    )

    # 6. Initialize SFTTrainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset_split["train"],
        eval_dataset=dataset_split["test"],
        peft_config=peft_config,
        processing_class=tokenizer,
        args=sft_config
    )

    # 7. Start Training
    print("✅ Model wrapped with LoRA adapters successfully.")
    trainer.model.print_trainable_parameters()
    print("🔥 Starting Model Training Run...")
    trainer.train()
    
    # 8. Save fine-tuned adapters locally
    print(f"💾 Saving fine-tuned adapters locally to {LOCAL_OUTPUT_DIR}...")
    trainer.model.save_pretrained(LOCAL_OUTPUT_DIR)
    tokenizer.save_pretrained(LOCAL_OUTPUT_DIR)
    print("✅ Local save complete.")

    # 9. Push adapters directly to the Hugging Face Hub (Private Repo)
    print(f"🛰️ Uploading adapters to Hugging Face Hub: {ADAPTER_REPO_ID}...")
    try:
        trainer.model.push_to_hub(
            repo_id=ADAPTER_REPO_ID,
            token=True,
            private=True
        )
        tokenizer.push_to_hub(
            repo_id=ADAPTER_REPO_ID,
            token=True,
            private=True
        )
        print(f"🎉 Success! Adapters are safely stored in your Hugging Face Hub.")
        print(f"🔗 Hub Destination: https://huggingface.co/models/{ADAPTER_REPO_ID}")
    except Exception as e:
        print(f"❌ Failed to upload adapters to Hugging Face Hub: {str(e)}")
        print("👉 You can still download the files manually from Colab's file explorer.")

if __name__ == "__main__":
    main()
