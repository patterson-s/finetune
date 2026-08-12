"""adaption.py — Adaption Labs TrainerAdapter (data shaping + AutoScientist).

Based on the R1 adaption-labs memo (docs.adaptionlabs.ai). The `adaption` SDK
is imported lazily so this module can be imported without it installed (tests
use FakeAdapter). Requires ADAPTION_API_KEY env var at call time.
"""
from __future__ import annotations

import os
from typing import Any

from .base import TrainerAdapter

# Maps our canonical row/CSV columns onto Adaption's column roles (memo §6).
COLUMN_MAPPING = {
    "prompt": "prompt",
    "context": ["context"],
    "completion": "output",
}


class AdaptionAdapter(TrainerAdapter):
    name = "adaption"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ADAPTION_API_KEY")
        if not self.api_key:
            raise ValueError("AdaptionAdapter requires ADAPTION_API_KEY")

    def _client(self):
        from adaption import Adaption  # lazy import
        return Adaption(api_key=self.api_key)

    def submit(self, dataset: dict, base_model: str, **kwargs: Any) -> dict:
        """Upload a dataset, run a data-adaptation job, and optionally start a
        training run. Mirrors the memo's documented lifecycle."""
        client = self._client()
        rows = dataset.get("rows", [])
        max_rows = kwargs.get("max_rows", 500)

        # Write rows to a temp CSV with our canonical columns
        import csv, tempfile
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        fieldnames = [k for k in ("prompt", "context", "output") if k in (rows[0] if rows else {})]
        writer = csv.DictWriter(tmp, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows[:max_rows]:
            writer.writerow({
                "prompt": r.get("system", ""),
                "context": r.get("user", ""),
                "output": r.get("assistant", ""),
            })
        tmp.close()

        try:
            res = client.datasets.upload_file(tmp.name)
            dataset_id = res.dataset_id
        finally:
            os.unlink(tmp.name)

        # Quote cost first (estimate), then run (memo recommends estimate=True first)
        if kwargs.get("estimate_only"):
            quote = client.datasets.run(
                dataset_id,
                column_mapping=COLUMN_MAPPING,
                job_specification={"max_rows": max_rows},
                estimate=True,
            )
            return {"job_id": dataset_id, "estimated_credits": getattr(quote, "estimated_credits_consumed", None)}

        run = client.datasets.run(
            dataset_id,
            column_mapping=COLUMN_MAPPING,
            job_specification={"max_rows": max_rows},
        )
        return {"job_id": dataset_id, "run_id": getattr(run, "run_id", None)}

    def status(self, job_id: str) -> dict:
        client = self._client()
        st = client.datasets.get_status(job_id)
        return {"job_id": job_id, "status": getattr(st, "status", "unknown"), "row_count": getattr(st, "row_count", None)}

    def download(self, job_id: str) -> dict:
        client = self._client()
        url = client.datasets.download(job_id)
        return {"job_id": job_id, "url": url}
