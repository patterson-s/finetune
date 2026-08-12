"""educ.py — build a proper education-extraction training dataset.

Output: one row per education experience, with the raw unstructured context
that contains (or fails to contain) it. Supports BOTH:
  - single extractor model (rows carry has_education=1 + the extraction target), and
  - two-stage (binary classifier + extractor) — every row has a has_education label.

Schema per row:
  person, granularity (chunk|doc), has_education (0|1),
  context (raw unstructured text),
  extraction: {degree_field, degree_level, university_name, university_country,
               year_start, year_finished, finished}  (present only when has_education=1)

Context is produced at BOTH granularities for every example:
  - chunk: a window of meaningful lines around the education quote anchor
  - doc:   the full meaningful text of the cited source document (boilerplate stripped)

Exclusions (per product spec): study-abroad, exchange, visiting-student, high-school,
and fellowship/"not a degree" entries are EXCLUDED — only real degrees are retained.
degree_level is kept RAW (coarse normalization is deferred to a later stage).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# --- boilerplate / noise filtering -------------------------------------------

BOILERPLATE_LOW = {
    "accept", "skip to main content", "close popup", "give now", "donate",
    "search", "back", "learn more", "privacy notice", "sign in", "login",
    "subscribe", "share", "next", "previous", "menu", "home", "newsletter",
    "read more", "view all", "download", "contact us",
}

MIN_MEANINGFUL_LEN = 30


def _is_meaningful(line: str) -> bool:
    s = line.strip()
    if len(s) < MIN_MEANINGFUL_LEN:
        return False
    low = s.lower()
    if low in BOILERPLATE_LOW:
        return False
    # near-empty nav/cookie fragments
    if re.fullmatch(r"[©®™\s\W]{0,40}", s):
        return False
    return True


def meaningful_lines(lines: list[str]) -> list[str]:
    """Keep only substantive content lines, dropping nav/cookie/empty noise."""
    return [l.strip() for l in lines if _is_meaningful(l)]


# --- level classification / exclusion ----------------------------------------

# Phrases that indicate this "degree row" is NOT a real awarded degree.
NOT_A_DEGREE = re.compile(
    r"study abroad|exchange|visiting student|visiting researcher|high school|"
    r"fellowship|not a degree|not a separate|not awarded|honorary|attended|"
    r"executive program|continuing education|workshop|seminar|certificate program"
    r"|undergraduate \(study|master's thesis research", re.I
)

# Phrases that indicate a credential listing rather than a standalone education
# experience (kept only if clearly a degree; handled by NOT_A_DEGREE above).
CREDENTIAL_ONLY = re.compile(r"\(credential only|credentials\)", re.I)

# Phrases in the level/field that mark a hedged, uncertain, or multi-way label
# that must NOT be used as a training target.
UNCERTAIN = re.compile(
    r"likely|conflict|not in the existing|missing from|maybe|possibly|"
    r"candidate|implied|not verifiable|not clearly|not stated|not confirmed|"
    r"ambiguous|per one source|per another|two different|three different|"
    r"mislabeled|not a separate", re.I
)

# University field that is not an actual institution (city, dash, unknown, hedge).
BAD_UNI = re.compile(r"defended in|^—$|unknown|not stated|not confirmed|ambiguous|not verifiable", re.I)

# Multi-degree merged into one row (e.g. "BSc / BA", "MPhil / PhD", "BA + BS").
COMBINED = re.compile(r"[/&]|\band\b|\+", re.I)
COMBINED_LEVEL = re.compile(r"BSc|BA|MSc|MA|PhD|MPhil|MBBS|LL\.?B|LL\.?M|JD|MD|BS\b|MS\b")


def is_excluded(level_raw: str) -> bool:
    """Return True if a degree row should be dropped (not a clean, single degree)."""
    if NOT_A_DEGREE.search(level_raw):
        return True
    if CREDENTIAL_ONLY.search(level_raw):
        return True
    if UNCERTAIN.search(level_raw):
        return True
    return False


def is_excluded_fields(level_raw: str, field_raw: str, uni_raw: str) -> bool:
    """Deeper audit exclusion: hedge/conflict in field or non-institution university."""
    if UNCERTAIN.search(field_raw):
        return True
    if BAD_UNI.search(uni_raw):
        return True
    if COMBINED.search(level_raw) and COMBINED_LEVEL.search(level_raw):
        return True
    return False


# --- context extraction ------------------------------------------------------

CHUNK_WINDOW = 4  # meaningful lines above + below the anchor


def _quote_fragments(quote: str, n: int = 40) -> list[str]:
    """Split a quote into searchable fragments (longest-first)."""
    frags = re.split(r"[…]|/|\|", quote)
    out = []
    for f in frags:
        f = f.strip(" \t\"'’‘“”…-")
        if len(f) >= 12:
            out.append(f)
    out.sort(key=len, reverse=True)
    return out[:n]


def chunk_context(
    lines: list[str],
    anchor_line_no: int | None,
    quote: str = "",
    window: int = CHUNK_WINDOW,
) -> str:
    """A window of meaningful lines around the line containing the degree's quote.

    The quote is the authoritative evidence of where the education info lives, so
    we search the meaningful lines for the longest quote fragment first, falling
    back to the anchor line, then to a leading window.
    """
    meaningful = meaningful_lines(lines)
    if not meaningful:
        return ""

    # 1) best match on quote fragments
    best_idx = -1
    best_len = 0
    frags = _quote_fragments(quote)
    for i, ml in enumerate(meaningful):
        mln = ml.replace("\u00a0", " ")
        for frag in frags:
            fn = frag.replace("\u00a0", " ").lower()
            if len(frag) >= best_len and fn in mln.lower():
                best_len = len(frag)
                best_idx = i
    if best_idx >= 0:
        lo = max(0, best_idx - window)
        hi = min(len(meaningful), best_idx + window + 1)
        return " ".join(meaningful[lo:hi])

    # 2) fall back to the anchor line (raw 1-indexed)
    if anchor_line_no and 0 < anchor_line_no <= len(lines):
        target = lines[anchor_line_no - 1].strip()
        if target:
            for i, ml in enumerate(meaningful):
                if target[:60] in ml or ml[:60] in target:
                    lo = max(0, i - window)
                    hi = min(len(meaningful), i + window + 1)
                    return " ".join(meaningful[lo:hi])

    # 3) leading window
    return " ".join(meaningful[: window * 2 + 1])


def doc_context(lines: list[str]) -> str:
    """Full meaningful text of the source document (boilerplate stripped)."""
    return " ".join(meaningful_lines(lines))


# --- gold → rows -------------------------------------------------------------

def _extraction(degree: dict) -> dict:
    f = degree.get("fields", {})
    # gold has a single `year`; map to year_finished (graduation), year_start unknown
    year = f.get("year", "") or ""
    if year in ("—", "-", "Not stated (gap)", "not stated", ""):
        year = ""
    return {
        "degree_field": f.get("field", ""),
        "degree_level": f.get("level", ""),      # raw, normalization deferred
        "university_name": f.get("university", ""),
        "university_country": f.get("country", ""),
        "year_start": "",                          # not in gold; filled later if derivable
        "year_finished": year,
        "finished": True,                          # gold rows are awarded degrees
    }


# Phrases indicating a passage likely discusses education (used only to help
# pick NEGATIVE sources — a source that never mentions these is a clean negative).
EDU_KEYWORDS = re.compile(
    r"university|college|degree|bachelor|master|ph\.?d|doctorate|dphil|"
    r"graduated|alma mater|enrolled|studied|faculty|school of|earned a|"
    r"m\.?s\.?c|b\.?s\.?c|b\.?a\b|m\.?a\b|m\.?b\.?b\.?s|ll\.?b|ll\.?m|jd\b",
    re.I,
)


def negative_sources(person: dict, sources: dict, max_per_person: int = 3) -> list[dict]:
    """Pick raw sources for this person that contain NO education info.

    Uses the person's `all_sources` (every fetched source, cited or not); excludes
    the ones cited for education (positive evidence) and any that mention education
    keywords, so the negatives are genuinely education-free.
    """
    cited = set()
    for deg in person.get("degrees", []):
        for c in deg.get("citations", []):
            if c.get("source_key"):
                cited.add(c["source_key"])
    neg = []
    for s in person.get("all_sources", []):
        sk = s.get("key")
        if not sk or sk in cited:
            continue
        src = sources.get(sk)
        if not src or not src.get("lines"):
            continue
        text = " ".join(meaningful_lines(src["lines"]))
        if not text or EDU_KEYWORDS.search(text):
            continue
        neg.append({"source": sk.split("/")[-1], "lines": src["lines"]})
        if len(neg) >= max_per_person:
            break
    return neg


def build_negative_rows(person: dict, sources: dict, max_per_person: int = 3) -> list[dict]:
    """Education-free chunk + doc rows (has_education=0) for the classifier stage."""
    name = person.get("name", "")
    rows = []
    for s in negative_sources(person, sources, max_per_person):
        rows.append({
            "person": name,
            "source": s["source"],
            "granularity": "chunk",
            "has_education": 0,
            "context": chunk_context(s["lines"], None, ""),
            "extraction": None,
        })
        rows.append({
            "person": name,
            "source": s["source"],
            "granularity": "doc",
            "has_education": 0,
            "context": doc_context(s["lines"]),
            "extraction": None,
        })
    return rows


def build_needs_fix(gold: dict) -> list[dict]:
    """Preserve the records excluded from training (for later manual fix).

    These are the audit-flagged degrees — infobox errors, hedges, conflicts,
    non-degrees, merged degrees — kept so the information isn't silently lost.
    """
    out = []
    for person in gold.get("people", []):
        name = person.get("name", "")
        for degree in person.get("degrees", []):
            level_raw = degree.get("fields", {}).get("level", "")
            field_raw = degree.get("fields", {}).get("field", "")
            uni_raw = degree.get("fields", {}).get("university", "")
            reason = []
            if is_excluded(level_raw):
                reason.append("level")
            if is_excluded_fields(level_raw, field_raw, uni_raw):
                reason.append("fields")
            if reason:
                out.append({
                    "person": name,
                    "fields": degree.get("fields", {}),
                    "quote": degree.get("quote", ""),
                    "reason": "|".join(reason),
                })
    return out


def build_dataset(gold: dict, include_negatives: bool = True) -> list[dict]:
    """Build the full training dataset at BOTH granularities.

    Positive rows: one per (person, degree, cited-source) at chunk + doc
    granularity, with has_education=1 and the extraction target.
    Negative rows: education-free sources at chunk + doc granularity with
    has_education=0 and extraction=None (for the two-stage classifier / robustness).
    """
    rows: list[dict] = []
    sources = gold.get("sources", {})
    for person in gold.get("people", []):
        name = person.get("name", "")
        if include_negatives:
            rows.extend(build_negative_rows(person, sources))
        for degree in person.get("degrees", []):
            level_raw = degree.get("fields", {}).get("level", "")
            field_raw = degree.get("fields", {}).get("field", "")
            uni_raw = degree.get("fields", {}).get("university", "")
            if is_excluded(level_raw) or is_excluded_fields(level_raw, field_raw, uni_raw):
                continue
            ext = _extraction(degree)
            # Dedupe source keys (a degree may cite the same source twice)
            seen = set()
            for cit in degree.get("citations", []):
                sk = cit.get("source_key")
                if not sk or sk in seen:
                    continue
                seen.add(sk)
                src = sources.get(sk)
                if not src:
                    continue
                lines = src.get("lines", [])
                anchor = cit.get("anchor_line_no")
                if not lines:
                    continue
                rows.append({
                    "person": name,
                    "source": sk.split("/")[-1],
                    "granularity": "chunk",
                    "has_education": 1,
                    "context": chunk_context(lines, anchor, degree.get("quote", "")),
                    "extraction": ext,
                })
                rows.append({
                    "person": name,
                    "source": sk.split("/")[-1],
                    "granularity": "doc",
                    "has_education": 1,
                    "context": doc_context(lines),
                    "extraction": ext,
                })
    return rows


def write_jsonl(rows: list[dict], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return p


def to_adaption_csv(rows: list[dict], path: str | Path, positive_only: bool = False) -> Path:
    """Export rows to Adaption's prompt/context/output CSV.

    prompt = the extraction instruction; context = the raw unstructured text;
    output = the expected JSON extraction (empty when has_education=0 and not
    positive_only). Column mapping matches finetune/adapt/adaption.COLUMN_MAPPING.
    """
    import csv
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = [r for r in rows if not positive_only or r["has_education"] == 1]
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["prompt", "context", "output"])
        writer.writeheader()
        for r in rows:
            prompt = (
                "Extract the education history of this person from the text. "
                "Return a JSON array of degrees with fields: degree_field, degree_level, "
                "university_name, university_country, year_start, year_finished, finished. "
                "Only include real awarded degrees; ignore study abroad, exchange, high school, "
                "or fellowships. Return [] if no education is present."
            )
            out = ""
            if r["has_education"] == 1:
                out = json.dumps([r["extraction"]], ensure_ascii=False)
            writer.writerow({"prompt": prompt, "context": r["context"], "output": out})
    return p


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, help="path to education_check.json")
    ap.add_argument("--out", default="datasets/education/train_educ.jsonl")
    args = ap.parse_args()
    gold = json.load(open(args.gold, encoding="utf-8"))
    rows = build_dataset(gold)
    p = write_jsonl(rows, args.out)
    pos = sum(1 for r in rows if r["has_education"])
    print(f"wrote {len(rows)} rows -> {p} ({p.stat().st_size/1e6:.2f} MB)")
    print(f"  positive (has_education=1): {pos}")
    from collections import Counter
    print("  by granularity:", dict(Counter(r['granularity'] for r in rows)))


if __name__ == "__main__":
    main()
