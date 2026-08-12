"""fake.py — an in-memory TrainerAdapter for tests (no network)."""
from __future__ import annotations

import uuid

from .base import TrainerAdapter


class FakeAdapter(TrainerAdapter):
    """Deterministic in-memory adapter; never makes a network call."""

    name = "fake"

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}

    def submit(self, dataset: dict, base_model: str, **kwargs) -> dict:
        job_id = f"fake-{uuid.uuid4().hex[:8]}"
        self._jobs[job_id] = {
            "job_id": job_id,
            "base_model": base_model,
            "status": "succeeded",
            "rows": len(dataset.get("rows", [])),
        }
        return self._jobs[job_id]

    def status(self, job_id: str) -> dict:
        if job_id not in self._jobs:
            return {"job_id": job_id, "status": "failed"}
        return dict(self._jobs[job_id])

    def download(self, job_id: str) -> dict:
        if job_id not in self._jobs:
            return {"job_id": job_id, "status": "failed"}
        return {"path": f"/tmp/{job_id}/adapter.safetensors", "job_id": job_id}
