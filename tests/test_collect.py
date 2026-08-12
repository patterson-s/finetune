"""Tests for the collect stage (finetune/collect/gold.py)."""
import json
import tempfile
from pathlib import Path

import pytest

from finetune.collect.gold import gold_to_rows, split_rows_person_disjoint


def _sample_gold() -> dict:
    """A tiny self-contained education_check.json-shaped fixture."""
    return {
        "people": [
            {
                "name": "Person A",
                "body_full": "Bio A",
                "degrees": [
                    {
                        "fields": {"level": "BSc", "field": "CS", "university": "U1",
                                   "year": "2000", "country": "Ethiopia"},
                        "quote": "received a BSc from U1",
                    },
                    {
                        "fields": {"level": "MSc", "field": "AI", "university": "U2",
                                   "year": "2003", "country": "Ireland"},
                        "quote": "received an MSc from U2",
                    },
                ],
                "all_sources": [],
            },
            {
                "name": "Person B",
                "body_full": "Bio B",
                "degrees": [
                    {
                        "fields": {"level": "PhD", "field": "Law", "university": "U3",
                                   "year": "2010", "country": "France"},
                        "quote": "earned a PhD at U3",
                    },
                ],
                "all_sources": [],
            },
        ]
    }


def test_gold_to_rows_produces_canonical_rows():
    rows = gold_to_rows(_sample_gold())
    # 3 degrees across 2 people -> 3 rows
    assert len(rows) == 3
    for row in rows:
        assert "system" in row and "user" in row and "assistant" in row
        assert row["system"].strip()
        assert row["user"].strip()
        assert row["assistant"].strip()


def test_assistant_contains_structured_degrees():
    rows = gold_to_rows(_sample_gold())
    # assistant should contain the degree info (e.g. university name)
    assert "U1" in rows[0]["assistant"]
    assert "U3" in rows[2]["assistant"]


def test_rows_keep_person_metadata():
    rows = gold_to_rows(_sample_gold())
    assert rows[0]["person"] == "Person A"
    assert rows[2]["person"] == "Person B"


def test_split_rows_person_disjoint():
    rows = gold_to_rows(_sample_gold())
    train, eval_rows = split_rows_person_disjoint(rows, eval_frac=0.5, seed=42)
    # No person appears in both splits
    train_people = {r["person"] for r in train}
    eval_people = {r["person"] for r in eval_rows}
    assert train_people.isdisjoint(eval_people)
    # Every row accounted for
    assert len(train) + len(eval_rows) == len(rows)
