"""emit_adaption.py — write collected gold rows to an Adaption-ready CSV.

Adaption accepts prompt/context/output columns, mapped via
column_mapping = {"prompt": "prompt", "context": ["context"], "completion": "output"}
(see finetune/adapt/adaption.py COLUMN_MAPPING and the R1 adaption memo).

Usage:
    python -m finetune.collect.emit_adaption \
        --gold "C:/.../education_check.json" \
        --out datasets/education/adaption_trackA.csv \
        --max-rows 100
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .gold import SYSTEM_PROMPT, gold_to_rows

PROMPT_TEMPLATE = (
    "Extract the target person's education history as JSON.\n"
    "Target person: {name}\n"
    "Return a JSON array of degrees with fields: level, field, university, year, country. "
    "Only include information about the target person."
)


def build_adaption_rows(gold: dict, max_rows: int | None = None) -> list[dict]:
    """One row per degree: prompt (system+person), context (bio), output (degree JSON)."""
    out = []
    for person in gold.get("people", []):
        name = person.get("name", "")
        bio = person.get("body_full") or person.get("body") or ""
        prompt = PROMPT_TEMPLATE.format(name=name)
        for degree in person.get("degrees", []):
            output = json.dumps(degree.get("fields", {}), ensure_ascii=False)
            out.append({
                "prompt": prompt,
                "context": bio,
                "output": output,
                "person": name,
            })
            if max_rows and len(out) >= max_rows:
                return out
    return out


def write_csv(rows: list[dict], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["prompt", "context", "output"])
        writer.writeheader()
        for r in rows:
            writer.writerow({"prompt": r["prompt"], "context": r["context"], "output": r["output"]})
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, help="path to education_check.json")
    ap.add_argument("--out", default="datasets/education/adaption_trackA.csv")
    ap.add_argument("--max-rows", type=int, default=None)
    args = ap.parse_args()

    gold = json.load(open(args.gold, encoding="utf-8"))
    rows = build_adaption_rows(gold, args.max_rows)
    p = write_csv(rows, args.out)
    print(f"wrote {len(rows)} rows to {p} ({p.stat().st_size/1e3:.0f} KB)")
    print("first row prompt:", rows[0]["prompt"][:80] if rows else "none")


if __name__ == "__main__":
    main()
