"""Tests for the education dataset builder (finetune/collect/educ.py)."""
import json
import tempfile
from pathlib import Path

from finetune.collect.educ import (
    build_classifier_balanced,
    build_dataset,
    chunk_context,
    doc_context,
    is_excluded,
    meaningful_lines,
    write_jsonl,
)


def _gold():
    return {
        "sources": {
            "a.md": {"lines": [
                "skip to main content",  # boilerplate
                "This is a short nav line",
                "He completed his Bachelor of Science in Neuroscience at University College London in 2005.",
                "He then earned a Master of Public Health from the University of Edinburgh.",
                "He works at PATH as Chief AI Officer.",
                "privacy notice",
            ]},
            "b.md": {"lines": ["He has no education listed in this source.", "Just career facts here."]},
        },
        "people": [
            {"name": "Person A", "all_sources": [
                {"key": "a.md", "cited": True},
                {"key": "b.md", "cited": False},
            ], "degrees": [
                {
                    "fields": {"level": "BSc", "field": "Neuroscience",
                               "university": "University College London",
                               "year": "2005", "country": "United Kingdom"},
                    "citations": [
                        {"source_key": "a.md", "anchor_line_no": 3},
                    ],
                },
            ]},
            # this row is NOT a real degree -> must be excluded
            {"name": "Person B", "degrees": [
                {"fields": {"level": "Undergraduate (study abroad)",
                            "field": "", "university": "", "year": "", "country": ""},
                 "citations": [{"source_key": "a.md", "anchor_line_no": 3}]},
            ]},
        ],
    }


def test_meaningful_lines_drops_boilerplate():
    lines = ["skip to main content", "Real education sentence here is long enough.", "privacy notice"]
    out = meaningful_lines(lines)
    assert len(out) == 1
    assert "Real education sentence" in out[0]


def test_is_excluded():
    assert is_excluded("Undergraduate (study abroad)")
    assert is_excluded("Fulbright Fellowship (not a degree)")
    assert is_excluded("Master's thesis research (visiting student)")
    assert is_excluded("MSc — likely a single degree described two different ways")
    assert not is_excluded("PhD")
    assert not is_excluded("BSc")


def test_is_excluded_fields():
    from finetune.collect.educ import is_excluded_fields
    # hedged/unknown university or field -> excluded
    assert is_excluded_fields("PhD", "Law", "Defended in Yekaterinburg, Russia")
    assert is_excluded_fields("Master's", "institution not clearly stated", "Ambiguous")
    assert is_excluded_fields("PhD", "good field", "Unknown — not confirmed")
    # merged degree in level -> excluded
    assert is_excluded_fields("BSc / BA", "field", "Bahir Dar University")
    # clean -> not excluded
    assert not is_excluded_fields("PhD", "Computer Science", "MIT")


def test_chunk_and_doc_context():
    lines = ["nav line one", "He completed his Bachelor of Science at UCL in 2005.", "then an MSc.", "He later worked as Chief AI Officer at a large global health organization."]
    # anchor_line_no=2 -> the meaningful line containing it
    c = chunk_context(lines, 2)
    assert "Bachelor of Science" in c
    d = doc_context(lines)
    assert "Bachelor of Science" in d
    assert "Chief AI Officer" in d


def test_build_dataset_excludes_non_degrees_and_has_label():
    rows = build_dataset(_gold(), include_negatives=False)
    # Person A: 1 cited source x 2 granularities = 2 rows, all has_education=1
    pa = [r for r in rows if r["person"] == "Person A"]
    assert len(pa) == 2
    assert all(r["has_education"] == 1 for r in pa)
    # Person B excluded entirely (study abroad)
    assert not any(r["person"] == "Person B" for r in rows)
    # both granularities present
    gran = {r["granularity"] for r in pa}
    assert gran == {"chunk", "doc"}
    # extraction schema present
    ex = pa[0]["extraction"]
    for k in ("degree_field", "degree_level", "university_name",
              "university_country", "year_start", "year_finished", "finished"):
        assert k in ex


def test_build_dataset_includes_negatives():
    rows = build_dataset(_gold(), include_negatives=True)
    neg = [r for r in rows if r["has_education"] == 0]
    assert neg, "expected negative (education-free) rows"
    assert all(r["extraction"] is None for r in neg)
    # b.md is education-free -> should appear as a negative for Person A
    b_negs = [r for r in neg if r["source"] == "b.md"]
    assert b_negs, "b.md should be a negative source"


def test_build_dataset_no_negatives_when_disabled():
    rows = build_dataset(_gold(), include_negatives=False)
    assert all(r["has_education"] == 1 for r in rows)


def test_chunk_context_locates_quote_not_leading_window():
    # Quote is near the end; context must center on it, not the leading nav line.
    lines = [
        "skip to main content nav nav nav nav nav nav nav nav",
        "He is the Chief AI Officer leading a large portfolio of global work.",
        "He completed his Master of Public Health from the University of Edinburgh in 2012.",
    ]
    quote = "He completed his Master of Public Health from the University of Edinburgh"
    c = chunk_context(lines, None, quote)
    assert "Master of Public Health" in c


def test_write_jsonl_roundtrip(tmp_path):
    rows = [{"a": 1, "extraction": {"x": "y"}}]
    p = write_jsonl(rows, tmp_path / "out.jsonl")
    assert p.exists()
    assert json.loads(p.read_text(encoding="utf-8"))["a"] == 1


def test_build_classifier_balanced_is_1to1_and_covers_classes():
    rows = build_classifier_balanced(_gold(), max_neg_per_person=50)
    pos = [r for r in rows if r["has_education"] == 1]
    neg = [r for r in rows if r["has_education"] == 0]
    assert pos, "expected some positive rows"
    assert neg, "expected some negative rows"
    # 1:1 balance (subsampled positives to match negatives)
    assert len(pos) == len(neg)
    # negatives carry the education-free source (b.md) and no extraction
    assert all(r["extraction"] is None for r in neg)
    # excluded Person B (study abroad) must not appear as a positive
    assert not any(r["person"] == "Person B" and r["has_education"] == 1 for r in rows)
