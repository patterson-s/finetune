"""sample.py — balanced, covered sampling of training rows.

Generalizes the sampling discipline from pydeal_type's build_adaption_dataset.py:
class balance, per-person (per-source) caps so no single person dominates, and a
seeded deterministic selection so runs are reproducible.
"""
from __future__ import annotations

import random
from collections import Counter


def _label(row: dict):
    return row.get("label", row.get("classification", 0))


def balance_sample(
    rows: list[dict],
    n_positive: int,
    n_negative: int,
    per_person_cap: int = 3,
    seed: int = 42,
    label_key: str = "label",
) -> list[dict]:
    """Return a class-balanced, per-person-capped sample.

    - Selects up to n_positive positive and n_negative negative rows.
    - No single person (rows[label_key_absent]) contributes more than per_person_cap.
    - Deterministic given `seed`.
    - Gracefully returns fewer rows if the pool is too small (no crash).
    """
    rng = random.Random(seed)
    pos = [r for r in rows if r.get(label_key) in (1, "1", True)]
    neg = [r for r in rows if r.get(label_key) in (0, "0", False)]

    # Shared per-person counter across BOTH classes, so a person can appear at
    # most per_person_cap times in the whole sample (faithful to pydeal_type).
    counts: Counter = Counter()

    def pick(pool: list[dict], quota: int) -> list[dict]:
        rng.shuffle(pool)
        out: list[dict] = []
        for r in pool:
            if len(out) >= quota:
                break
            person = r.get("person", r.get("source", "unknown"))
            if counts[person] >= per_person_cap:
                continue
            counts[person] += 1
            out.append(r)
        return out

    picked = pick(pos, n_positive) + pick(neg, n_negative)
    rng.shuffle(picked)
    return picked
