"""Colab: stable LoRA training WITHOUT TRL (Transformers Trainer).

Trains 5 LoRA adapters from Drive JSONL datasets and saves adapters back to Drive.

Usage (in Colab):
!python training/colab/train_5_adapters_transformers_trainer.py
"""

from __future__ import annotations


def main() -> int:
    # 1) Mount Drive
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")

    # 2) Install deps
    import os

    os.system(
        "pip -q install -U transformers datasets peft accelerate bitsandbytes sentencepiece"
    )

    # 3) Imports (after pip)
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    # ---- Paths (your confirmed paths) ----
    drive_root = "/content/drive/MyDrive/atlas/training"
    datasets = {
        "atlas": f"{drive_root}/atlas/train.jsonl",
        "neptune": f"{drive_root}/neptune/train.jsonl",
        "hydra": f"{drive_root}/hydra/train.jsonl",
        "chronos": f"{drive_root}/chronos/train.jsonl",
        "athena": f"{drive_root}/athena/train.jsonl",
    }
    out_dir = "/content/drive/MyDrive/atlas/adapters"

    # ---- Base model ----
    base_model = "Qwen/Qwen2.5-0.5B-Instruct"  # fast
    # base_model = "Qwen/Qwen2.5-1.5B-Instruct"  # better, slower

    # ---- Time budget knobs (tune these) ----
    max_steps_per_adapter = 120  # ~10-15 min each on T4 (rough), total ~50-75 min
    max_length = 384  # shorter => faster (512 also ok if time allows)
    batch_size = 8
    grad_accum = 2
    lr = 2e-4

    print("CUDA:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))

    print("Dataset path check:")
    for k, p in datasets.items():
        print(k, os.path.exists(p), p)
    assert all(os.path.exists(p) for p in datasets.values())
    os.makedirs(out_dir, exist_ok=True)

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16,
    )

    def format_messages(example):
        parts = []
        for m in example["messages"]:
            parts.append(f"<|{m['role']}|>\n{m['content']}\n")
        parts.append("<|assistant|>\n")
        return "".join(parts)

    def load_base_and_tokenizer():
        tok = AutoTokenizer.from_pretrained(base_model, use_fast=True, trust_remote_code=True)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            quantization_config=bnb,
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        model.config.use_cache = False
        model = prepare_model_for_kbit_training(model)

        lora_cfg = LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        )
        model = get_peft_model(model, lora_cfg)
        return tok, model

    def tokenize_dataset(ds, tok):
        def _tok(ex):
            text = format_messages(ex)
            return tok(text, truncation=True, max_length=max_length, padding=False)

        return ds.map(_tok, remove_columns=ds.column_names)

    def train_adapter(name: str, jsonl_path: str):
        tok, model = load_base_and_tokenizer()

        ds = load_dataset("json", data_files=jsonl_path, split="train")
        ds = tokenize_dataset(ds, tok)

        collator = DataCollatorForLanguageModeling(tok, mlm=False)

        out = os.path.join(out_dir, name)
        args = TrainingArguments(
            output_dir=out,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=grad_accum,
            learning_rate=lr,
            max_steps=max_steps_per_adapter,
            warmup_ratio=0.03,
            lr_scheduler_type="cosine",
            logging_steps=10,
            save_strategy="no",
            report_to=[],
            fp16=True,
        )

        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=ds,
            data_collator=collator,
        )
        trainer.train()

        model.save_pretrained(out)
        tok.save_pretrained(out)
        print("saved:", out)

    for dsl, path in datasets.items():
        train_adapter(dsl, path)

    print("DONE. Adapters saved to:", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

