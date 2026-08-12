"""Tests for the augment stage (finetune/augment/sample.py)."""
import pytest

from finetune.augment.sample import balance_sample


def _rows(n=200):
    # 20 people, each with both classes (5 pos / 5 neg each), enough headroom
    # that per-person caps don't starve the class-balance quotas.
    return [
        {"person": f"P{i % 20}", "label": i % 2, "text": f"row {i}"}
        for i in range(n)
    ]


def test_balance_sample_respects_class_balance():
    rows = _rows()
    out = balance_sample(rows, n_positive=20, n_negative=30, seed=42)
    pos = sum(1 for r in out if r["label"] == 1)
    neg = sum(1 for r in out if r["label"] == 0)
    assert pos == 20
    assert neg == 30
    assert len(out) == 50


def test_balance_sample_per_person_cap():
    rows = _rows()  # 10 people, 10 rows each
    out = balance_sample(rows, n_positive=25, n_negative=25, per_person_cap=3, seed=42)
    from collections import Counter
    counts = Counter(r["person"] for r in out)
    assert max(counts.values()) <= 3


def test_balance_sample_deterministic():
    rows = _rows()
    a = balance_sample(rows, n_positive=20, n_negative=20, seed=7)
    b = balance_sample(rows, n_positive=20, n_negative=20, seed=7)
    assert [r["text"] for r in a] == [r["text"] for r in b]


def test_balance_sample_handles_insufficient():
    # Only 3 positives available but asked for 20 -> returns what's there, no crash
    rows = _rows(20)  # 10 pos / 10 neg
    out = balance_sample(rows, n_positive=20, n_negative=20, seed=1)
    assert len(out) <= 20
