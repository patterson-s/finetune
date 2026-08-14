"""Tests for the store stage (finetune/store/registry.py).

Uses LocalRegistry only — network-free and deterministic. HFRegistry.push is
covered by import-shape checks; actual pushes need HF_TOKEN + network.
"""
import json
from pathlib import Path

from finetune.store.registry import (
    HFRegistry,
    LocalRegistry,
    artifact_id,
    build_manifest,
    store_from_task,
)


def _files(tmp_path):
    a = tmp_path / "adapter_model.bin"
    a.write_bytes(b"weights-AAA")
    b = tmp_path / "adapter_config.json"
    b.write_bytes(b'{"r": 8}')
    return [a, b]


def test_artifact_id_is_content_derived_and_stable(tmp_path):
    f = tmp_path / "w.bin"
    f.write_bytes(b"hello world")
    assert artifact_id([f]) == artifact_id([f])
    assert artifact_id([f], salt="task-x") != artifact_id([f])
    f2 = tmp_path / "w2.bin"
    f2.write_bytes(b"hello world!")
    assert artifact_id([f]) != artifact_id([f2])


def test_build_manifest_fields(tmp_path):
    files = _files(tmp_path)
    m = build_manifest(files, "Qwen/Qwen3-8B-Instruct", "education_extraction",
                       extra={"n_rows": 10, "steps": 3})
    assert m["task_id"] == "education_extraction"
    assert m["base_model"] == "Qwen/Qwen3-8B-Instruct"
    assert m["artifact_id"]
    assert m["tag"] == f"education_extraction-{m['artifact_id']}"
    assert m["n_rows"] == 10
    assert "created_at" in m


def test_local_registry_copies_files_and_manifest(tmp_path):
    files = _files(tmp_path)
    reg = LocalRegistry(weights_dir=str(tmp_path / "weights"))
    m = reg.store(files, "Qwen/Qwen3-8B-Instruct", "education_extraction")
    art_dir = tmp_path / "weights" / m["artifact_id"]
    assert (art_dir / "adapter_model.bin").exists()
    assert (art_dir / "adapter_config.json").exists()
    assert (art_dir / "manifest.json").exists()
    # manifest files now point at the copied locations
    assert all(Path(f).exists() for f in m["files"])


def test_local_registry_roundtrip_manifest(tmp_path):
    files = _files(tmp_path)
    reg = LocalRegistry(weights_dir=str(tmp_path / "weights"))
    m = reg.store(files, "Qwen/Qwen3-8B-Instruct", "education_extraction")
    back = reg.read_manifest(m["artifact_id"])
    assert back is not None
    assert back["artifact_id"] == m["artifact_id"]
    assert json.loads((tmp_path / "weights" / m["artifact_id"] / "manifest.json").read_text())


def test_local_registry_read_missing_returns_none(tmp_path):
    reg = LocalRegistry(weights_dir=str(tmp_path / "weights"))
    assert reg.read_manifest("nope") is None


def test_hf_registry_repo_id_naming():
    r = HFRegistry(namespace="patterson-s")
    assert r.repo_id("education_extraction", "abc123") == "patterson-s/finetune-education_extraction-abc123"


def test_store_from_task_uses_tasks_yaml_base_model(tmp_path):
    files = _files(tmp_path)
    m = store_from_task("education_extraction", files, backend="local",
                        extra={"steps": 2})
    assert m["base_model"] == "Qwen/Qwen3-8B-Instruct"  # from tasks.yaml
    assert m["task_id"] == "education_extraction"
