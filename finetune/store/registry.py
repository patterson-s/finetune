"""store/registry.py — the store stage: content-hash artifact-id + manifest.json.

Contract (design.md §2, stage 'store'):
  weights + manifest -> a private HF repo (or a local weights/ dir for the
  local-only path), keyed by a content-derived artifact-id and git-tagged.

The registry is an interchangeable backend (same philosophy as TrainerAdapter):
  LocalRegistry  - copies artifact files into weights/<artifact-id>/ and writes
                   a manifest.json. Network-free; used for local-only runs and
                   as the deterministic base for tests.
  HFRegistry     - pushes the artifact dir to a (default private) HF repo named
                   <namespace>/finetune-<task>-<artifact-id> and records the repo
                   id + tag in the manifest. huggingface_hub is imported lazily
                   so this module imports without it (tests use LocalRegistry).

Everything returns a manifest dict with the fields the downstream serve stage
and C-series cards consume: artifact_id, base_model, task, files, repo_id,
created_at, and any extra facts (n_rows, steps, device).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..spec import load_tasks

DEFAULT_NAMESPACE = "patterson-s"


def artifact_id(files: list[str | Path], salt: str = "") -> str:
    """Content-derived short hash over the given files' bytes (+ optional salt).

    Two runs on identical weights produce the same id; any change to any file
    (or an explicit salt, e.g. task id) changes it. First 12 hex chars for
    readability in repo/namespace names.
    """
    h = hashlib.sha256()
    if salt:
        h.update(salt.encode("utf-8"))
    for f in files:
        p = Path(f)
        if not p.is_file():
            continue
        # stream so huge GGUF/safetensors files don't need to fit in RAM
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()[:12]


def build_manifest(
    artifact_files: list[str | Path],
    base_model: str,
    task_id: str,
    *,
    artifact: str | None = None,
    repo_id: str | None = None,
    tag: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the manifest dict for a store operation.

    artifact defaults to a content hash of the files; tag defaults to
    f"{task_id}-{artifact}". Extra facts (n_rows, steps, device, ...) ride
    along unchanged.
    """
    artifact = artifact or artifact_id(artifact_files, salt=task_id)
    return {
        "artifact_id": artifact,
        "task_id": task_id,
        "base_model": base_model,
        "files": [str(p) for p in artifact_files],
        "repo_id": repo_id,
        "tag": tag or f"{task_id}-{artifact}",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **(extra or {}),
    }


class LocalRegistry:
    """Copy artifact files into a local weights/<artifact-id>/ + manifest.json."""

    def __init__(self, weights_dir: str | Path = "weights") -> None:
        self.weights_dir = Path(weights_dir)

    def store(
        self,
        artifact_files: list[str | Path],
        base_model: str,
        task_id: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        manifest = build_manifest(artifact_files, base_model, task_id, extra=extra)
        target = self.weights_dir / manifest["artifact_id"]
        target.mkdir(parents=True, exist_ok=True)
        copied: list[str] = []
        for f in artifact_files:
            p = Path(f)
            if not p.is_file():
                continue
            dest = target / p.name
            dest.write_bytes(p.read_bytes())
            copied.append(str(dest))
        manifest["files"] = copied
        self.write_manifest(manifest, target)
        return manifest

    def write_manifest(self, manifest: dict[str, Any], target: Path) -> Path:
        mpath = target / "manifest.json"
        mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return mpath

    def read_manifest(self, artifact_id: str) -> dict[str, Any] | None:
        mpath = self.weights_dir / artifact_id / "manifest.json"
        if not mpath.exists():
            return None
        return json.loads(mpath.read_text(encoding="utf-8"))


class HFRegistry:
    """Push an artifact dir to a (default private) HF repo + record repo_id/tag.

    huggingface_hub is imported lazily inside push() so this module imports fine
    without it and tests that never push stay network-free. Requires HF_TOKEN.
    """

    def __init__(
        self, namespace: str = DEFAULT_NAMESPACE, *, private: bool = True
    ) -> None:
        self.namespace = namespace
        self.private = private

    def repo_id(self, task_id: str, artifact: str) -> str:
        return f"{self.namespace}/finetune-{task_id}-{artifact}"

    def push(
        self,
        artifact_files: list[str | Path],
        base_model: str,
        task_id: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # stage locally first so the manifest records real local copies + hashes
        local = LocalRegistry().store(artifact_files, base_model, task_id, extra=extra)
        rid = self.repo_id(task_id, local["artifact_id"])
        local["repo_id"] = rid

        from huggingface_hub import HfApi  # lazy; network + token required

        api = HfApi()
        api.create_repo(rid, private=self.private, exist_ok=True)
        # push the whole artifact dir (adapter weights + manifest.json)
        api.upload_folder(
            folder_path=str(Path(local["files"][0]).parent),
            repo_id=rid,
            commit_message=f"store {local['artifact_id']} for {task_id}",
        )
        api.create_tag(repo_id=rid, tag=local["tag"], exist_ok=True)
        return local


def store_from_task(
    task_id: str,
    artifact_files: list[str | Path],
    *,
    backend: str = "local",
    namespace: str = DEFAULT_NAMESPACE,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience entry: look up the task's cloud base model, then store.

    backend: 'local' (default) or 'hf'. base_model is read from tasks.yaml so
    callers don't have to repeat it; pass task_id as the canonical id.
    """
    tasks = load_tasks()
    task = tasks.get(task_id)
    base = (task.model_tiers.get("cloud") if task else None) or ""
    files = [Path(f) for f in artifact_files]
    if backend == "hf":
        return HFRegistry(namespace=namespace).push(files, base, task_id, extra=extra)
    return LocalRegistry().store(files, base, task_id, extra=extra)
