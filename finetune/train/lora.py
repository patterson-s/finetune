"""lora.py — minimal local LoRA training via PEFT + transformers.

Purpose: an iterate-fast smoke/training path on the PC. The real production
run for Tier-1 goes through the hosted adapt stage (Together/Adaption); this
local path is for validating the training loop cheaply (tiny model, few steps).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

SYSTEM_TEMPLATE = "{system}\n\n{user}"


def _tokenize(tokenizer, rows: list[dict], max_len: int = 512):
    texts = [
        SYSTEM_TEMPLATE.format(system=r["system"], user=r["user"]) + "\n\n" + r["assistant"]
        for r in rows
    ]
    enc = tokenizer(
        texts, truncation=True, max_length=max_len, padding="max_length"
    )
    # enc is a BatchEncoding (dict of lists of ints); expand to a list of dicts
    # with plain int lists so Dataset.from_list is happy.
    n = len(enc["input_ids"])
    out = []
    for i in range(n):
        out.append({
            "input_ids": list(enc["input_ids"][i]),
            "attention_mask": list(enc["attention_mask"][i]),
            "labels": list(enc["input_ids"][i]),
        })
    return out


def train_lora(
    rows: list[dict],
    base_model: str,
    output_dir: str | Path = "weights/lora-out",
    max_steps: int = 50,
    max_len: int = 512,
    lr: float = 5e-5,
    force_download: bool = False,
    device: str | None = None,
    **_: Any,
) -> dict:
    """Train a LoRA adapter on canonical rows. Returns manifest-ish dict.

    The returned dict is consumed by the store stage (B6) for the manifest.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    dev = device or ("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(base_model, force_download=force_download)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        force_download=force_download,
        device_map=None,
    ).to(dev)

    lora_cfg = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["c_attn"],  # GPT-2 style; adapt for Qwen/Llama in prod
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(model, lora_cfg)

    ds = Dataset.from_list(_tokenize(tokenizer, rows, max_len))
    args = TrainingArguments(
        output_dir=str(out),
        max_steps=max_steps,
        per_device_train_batch_size=2,
        learning_rate=lr,
        report_to=[],
        save_strategy="steps",
        save_steps=1,
    )
    trainer = Trainer(model=model, args=args, train_dataset=ds, tokenizer=tokenizer)
    trainer.train()

    model.save_pretrained(str(out))

    return {
        "checkpoint_dir": str(out),
        "base_model": base_model,
        "n_rows": len(rows),
        "steps": max_steps,
        "device": dev,
    }
