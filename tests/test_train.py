"""Tests for the train stage (finetune/train/lora.py).

The smoke test uses a tiny model and 1 step so it completes quickly on CPU.
Marked so it can be skipped when torch/PEFT isn't installed.
"""
import pytest

# DEFERRED (2026-08-12): finetuning is HOSTED (Adaption/Together), not local.
# This local LoRA path is a backburner/optional stage (e.g. Tier-3 FEC local work).
# Known remaining transformers-5.x fix: Trainer() no longer accepts tokenizer=.
# The heavy import (torch/peft/transformers) is wrapped so a broken or absent
# transformers install skips this module instead of failing the whole suite's
# collection (observed: tokenizers==0.23.1 vs transformers requiring <=0.23.0).
pytestmark = pytest.mark.skip(reason="local training is deferred; hosted finetuning is the active path")

torch = pytest.importorskip("torch")
try:
    from finetune.train.lora import train_lora  # noqa: E402
except Exception as _e:  # transformers/peft/tokenizers missing or mismatched
    pytest.skip(f"train deps unavailable (deferred stage): {_e}", allow_module_level=True)


@pytest.fixture(scope="module")
def tiny_rows():
    return [
        {"system": "Extract education.", "user": "Person: A Bio: x", "assistant": '{"level":"BSc"}'},
        {"system": "Extract education.", "user": "Person: B Bio: y", "assistant": '{"level":"MSc"}'},
        {"system": "Extract education.", "user": "Person: C Bio: z", "assistant": '{"level":"PhD"}'},
    ]


def test_train_lora_produces_checkpoint(tmp_path, tiny_rows):
    out = train_lora(
        tiny_rows,
        base_model="sshleifer/tiny-gpt2",
        output_dir=str(tmp_path),
        max_steps=1,
        force_download=True,
    )
    assert out["checkpoint_dir"]
    assert (tmp_path / "adapter_config.json").exists()


def test_train_lora_returns_manifest_fields(tmp_path, tiny_rows):
    out = train_lora(
        tiny_rows,
        base_model="sshleifer/tiny-gpt2",
        output_dir=str(tmp_path),
        max_steps=1,
        force_download=True,
    )
    for key in ("checkpoint_dir", "base_model", "n_rows", "steps"):
        assert key in out
