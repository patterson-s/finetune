"""base.py — the TrainerAdapter interface for hosted finetuning providers.

Every hosted finetuning backend (Adaption Labs, Together AI, ...) implements
this interface so the pipeline can swap providers without changing downstream
code. Backends are network-free in tests via FakeAdapter.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TrainerAdapter(ABC):
    """Submit a finetuning job and retrieve its result.

    Contract:
      submit(dataset, base_model, **kw) -> {"job_id": str, ...}
      status(job_id)                    -> {"status": pending|running|succeeded|failed, "job_id", ...}
      download(job_id)                  -> {"path": str, "job_id": str, ...}
    """

    name: str = "base"

    @abstractmethod
    def submit(self, dataset: dict, base_model: str, **kwargs: Any) -> dict:
        ...

    @abstractmethod
    def status(self, job_id: str) -> dict:
        ...

    @abstractmethod
    def download(self, job_id: str) -> dict:
        ...
