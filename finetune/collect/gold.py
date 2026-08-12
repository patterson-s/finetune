"""gold.py — convert a gold source (education_check.json shape) into canonical
training rows: {system, user, assistant, person, ...}.

Canonical row contract (shared across collect stage):
  system    - task instruction
  user      - the input (person bio / source material prompt)
  assistant - the expected structured output (JSON)
  person    - person identifier (used for person-disjoint splitting)
"""
from __future__ import annotations

import json
import random
from typing import Any, Iterable

SYSTEM_PROMPT = (
    "You extract a person's education history from biographical source material. "
    "Return a JSON array of degrees. Each degree has fields: level, field, "
    "university, year, country. Only include information that is about the target "
    "person. Return an empty array [] if no education is found."
)


def _degree_to_json(degree: dict) -> dict:
    return degree.get("fields", {})


def gold_to_rows(gold: dict, system_prompt: str = SYSTEM_PROMPT) -> list[dict]:
    """Convert an education_check.json-shaped gold dict into training rows.

    Each person yields one row per degree, so a person with N degrees produces N
    rows. The `user` includes the person's name + bio so the model can ground on
    the target identity; the `assistant` is the JSON for that one degree (so each
    row teaches one extraction).
    """
    rows: list[dict] = []
    for person in gold.get("people", []):
        name = person.get("name", "")
        bio = person.get("body_full") or person.get("body") or ""
        user_text = f"Person: {name}\n\nBiography:\n{bio}".strip()
        for degree in person.get("degrees", []):
            assistant = json.dumps(_degree_to_json(degree), ensure_ascii=False)
            rows.append({
                "system": system_prompt,
                "user": user_text,
                "assistant": assistant,
                "person": name,
                "degree_index": degree.get("index"),
                "quote": degree.get("quote", ""),
            })
    return rows


def split_rows_person_disjoint(
    rows: list[dict], eval_frac: float = 0.2, seed: int = 42
) -> tuple[list[dict], list[dict]]:
    """Split rows into train/eval by PERSON so no person spans both splits.

    Prevents leakage where the model would 'remember' a person's degrees from
    training and get an inflated eval score.
    """
    people = sorted({r["person"] for r in rows})
    rng = random.Random(seed)
    rng.shuffle(people)
    n_eval = max(1, round(len(people) * eval_frac))
    eval_people = set(people[:n_eval])
    train = [r for r in rows if r["person"] not in eval_people]
    eval_rows = [r for r in rows if r["person"] in eval_people]
    return train, eval_rows


def build_distractor_rows(
    rows: list[dict], gold: dict, n: int = 0, seed: int = 42
) -> list[dict]:
    """Build distractor rows for the anti-hallucination probe.

    For a person's true degrees, inject another person's degree into the bio and
    assert the expected output must NOT include it. (Not wired into training —
    used by the C3 probe.)
    """
    rng = random.Random(seed)
    by_person: dict[str, list[dict]] = {}
    for person in gold.get("people", []):
        by_person[person.get("name", "")] = person.get("degrees", [])
    others = {p: d for p, d in by_person.items()}
    out = []
    for row in rows:
        p = row["person"]
        distractor_pool = [o for o in others if o != p]
        if not distractor_pool or n and len(out) >= n:
            continue
        other = rng.choice(distractor_pool)
        other_deg = rng.choice(others[other])
        out.append({
            "person": p,
            "true_degree": row["assistant"],
            "distractor_degree": json.dumps(_degree_to_json(other_deg), ensure_ascii=False),
            "distractor_person": other,
        })
    return out
