"""Tests for the adapt stage (finetune/adapt/*)."""
import pytest

from finetune.adapt.base import TrainerAdapter
from finetune.adapt.fake import FakeAdapter


def test_trainer_adapter_is_abstract():
    with pytest.raises(TypeError):
        TrainerAdapter()  # abstract base cannot be instantiated


def test_fake_adapter_implements_contract():
    a = FakeAdapter()
    assert hasattr(a, "submit")
    assert hasattr(a, "status")
    assert hasattr(a, "download")


def test_fake_adapter_submit_and_status():
    a = FakeAdapter()
    job = a.submit({"rows": [{"system": "s", "user": "u", "assistant": "a"}]}, base_model="Qwen/Qwen3-4B-Instruct")
    assert job["job_id"]
    st = a.status(job["job_id"])
    assert st["status"] in ("pending", "running", "succeeded", "failed")
    assert st["base_model"] == "Qwen/Qwen3-4B-Instruct"


def test_fake_adapter_download_returns_artifact():
    a = FakeAdapter()
    job = a.submit({"rows": []}, base_model="Qwen/Qwen3-4B-Instruct")
    dl = a.download(job["job_id"])
    assert "path" in dl
    assert dl["job_id"] == job["job_id"]


def test_fake_adapter_status_unknown_job():
    a = FakeAdapter()
    assert a.status("nope")["status"] == "failed"
