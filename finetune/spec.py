"""Task-spec loader: read configs/tasks.yaml into typed TaskSpec objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = REPO_ROOT / "configs" / "tasks.yaml"


@dataclass
class TaskSpec:
    """A single finetuning task definition (one block in tasks.yaml)."""

    id: str
    name: str
    tier: int
    status: str
    description: str = ""
    gold_source: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    model_tiers: dict = field(default_factory=dict)
    data_tracks: dict = field(default_factory=dict)
    eval: dict = field(default_factory=dict)
    prior_art: str = ""
    architecture_note: str = ""
    status_note: str = ""
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, task_id: str, data: dict) -> "TaskSpec":
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in known}
        clean["id"] = task_id
        # Stash any unknown keys under extra so nothing is silently dropped.
        clean["extra"] = {k: v for k, v in data.items() if k not in known}
        return cls(**clean)


def load_tasks(path: str | Path = TASKS_PATH) -> dict[str, TaskSpec]:
    """Load all tasks from tasks.yaml. Returns {task_id: TaskSpec}."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Task config not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    tasks = raw.get("tasks", {})
    return {tid: TaskSpec.from_dict(tid, data) for tid, data in tasks.items()}
