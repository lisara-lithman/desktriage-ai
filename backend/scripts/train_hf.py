"""
train_hf.py
===========
Industry-standard PyTorch fine-tuning script using Hugging Face (Transformers, PEFT, TRL).
Configured for QLoRA (4-bit quantization + LoRA adapters) on Nvidia GPUs.

Run this on Google Colab (with T4 GPU) or any Nvidia GPU cloud server.
Usage:
    pip install transformers peft trl bitsandbytes accelerate datasets
    python train_hf.py
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# Configurations matching our local MLX run
MODEL_ID = "meta-llama/Meta-Llama-3.1-8B-Instruct"
DATASET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/train_dataset.jsonl"))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../hf_adapters_8b"))

def main():
    print("🚀 Initializing Hugging Face QLoRA Training Pipeline...")
    
    # 1. Load Dataset
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}. Please generate or upload it first.")
        
    print(f"📡 Loading dataset from {DATASET_PATH}...")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    
    # Split into train/validation (90/10)
    dataset = dataset.train_test_split(test_size=0.1, seed=42)
    print(f"✅ Dataset loaded. Train size: {len(dataset['train'])}, Val size: {len(dataset['test'])}")

    # 2. Configure 4-bit Quantization (bitsandbytes)
    # This matches the 4-bit quantization memory efficiency of MLX
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True
    )

    # 3. Load Base Model & Tokenizer
    print(f"🔄 Downloading/Loading Base Model: {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16
    )
    
    # Prepare model for k-bit training (gradient checkpointing support)
    model = prepare_model_for_kbit_training(model)

    # 4. Configure LoRA parameters (matching our MLX config)
    peft_config = LoraConfig(
        r=8,
        lora_alpha=20, # In MLX, scale=20. In HF PEFT, scale = lora_alpha / r, so alpha=20 gives scale=2.5.
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, peft_config)
    print("✅ LoRA adapters successfully configured and attached to model.")
    model.print_trainable_parameters()

    # 5. Define Training Arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2, # Effective batch size = 4
        learning_rate=5e-5,            # Stabilized learning rate matching MLX
        logging_steps=10,
        max_steps=400,                 # Total iterations matching our local setup
        save_strategy="steps",
        save_steps=100,
        evaluation_strategy="steps",
        eval_steps=100,
        fp16=False,
        bf16=True,                     # Use bfloat16 precision for training stability
        optim="paged_adamw_8bit",      # High-efficiency memory optimizer
        warmup_ratio=0.03,
        lr_scheduler_type="constant",  # Matches MLX schedule
        report_to="none"               # Set to "wandb" if you want logs tracked on Weights & Biases
    )

    # 6. Initialize SFTTrainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=1024,
        tokenizer=tokenizer,
        args=training_args,
        packing=False
    )

    # 7. Start Training
    print("🔥 Starting Model Training Run...")
    trainer.train()
    
    # 8. Save fine-tuned adapters
    print(f"💾 Saving fine-tuned adapters to {OUTPUT_DIR}...")
    trainer.model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("🎉 Training Complete! Adapters successfully saved.")

if __name__ == "__main__":
    main()
