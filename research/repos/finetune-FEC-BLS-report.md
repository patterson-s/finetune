# finetune_FEC_BLS — Development Map

**Repo root:** `C:\Users\spatt\Desktop\finetune_FEC_BLS`
**Git:** `main`, 8 commits, 2024-12-13 → 2025-01-17. `data/` and `.env` are gitignored (`data/`, `.env` in `.gitignore`), so all data artifacts below are untracked working-tree files.

---

## Overview

This is a fine-tuning project that classifies **free-text US campaign-contribution occupations** (e.g. `"Salesperson"`, `"Sales Rep"`, `"Lawyer"`) into **BLS SOC / O\*NET occupation labels** using an **OpenAI GPT-3.5 (`gpt-3.5-turbo-0613`) fine-tuned model**.

The pipeline:
1. **Fine-tune** a chat model so that, given a prompt `"classify this profession: <occupation> ->"`, it emits a **normalized token** (the "transformed completion") rather than the human label directly.
2. **Decoder map**: a JSONL file (`data/finetune.jsonl`) that maps each normalized token back to the human-readable BLS occupation label. The model only ever needs to emit one of a closed set of normalized tokens; a deterministic dictionary (`decoder_map[transformed_completion] → completion`) converts the token to the real occupation name. Anything the model emits that is **not a key** in the map is treated as a **hallucination** and retried or flagged.
3. **Scale**: run the fine-tuned model over the unique occupations found in a large contribution dataset (`contribs_2022.db` / DIME data), in resumable batches, decode via the map, and merge the classifications back onto the full contribution rows.

---

## Timeline & Development

| Date | Commit | What it added |
|------|--------|---------------|
| 2024-12-13 | `5e5b987` | "created environment and readme" — project skeleton + `README.md` |
| 2024-12-13 | `3be2aa9` | "added base model usage script" — `OccupationClassifier_base_01.py` (interactive, no decoder) |
| 2024-12-13 | `a001b72` | "added v2 of classification script" — `OccupationClassifier_base_02.py` (adds decoder map + hallucination retry loop) |
| 2024-12-13 | `a7e22ee` | "Removed finetune.jsonl and updated .gitignore" — training data taken out of version control |
| 2024-12-13 | `a1ec297` | "added OccupationSimulation demo" — `OccupationSimulation_base_01.py` (+ `.ipynb`) |
| 2024-12-15 | `fc7944a` | "added full classifier script to work with dataset" — `batch_02`/`batch_03`/`batch_04`, `scale_01`, `correction_01`, `contribs_2022_mapback`, `contribs_2022_descriptives` |
| 2024-12-20 | `d38d9b0` | "added batch classifier and script for adding dime to sqlite database" — `batch_04_reverse`, `batch_05`, `dime_sqlite.py`, `dime_subset_01/02/03` |
| 2025-01-17 | `4a4266b` | "catching up" — `contribs_2022_postcorrection_merge/analysis`, `contribs2022_filter`, `contribs_2022_mapback_02`, `contribs_2022_descriptives_02` |
| 2025-01-16 | *(run artifact)* | `scripts/decoder_process.log` — an actual batch post-correction run (see below) |

**Later, un-committed work (files dated 2025-07-24):** the `debug/` directory contains `debug_01.py`…`debug_14.py` and large CSVs that map the final classification categories onto **O\*NET SOC codes** via fuzzy matching. See the Data-Assets section. These artifacts sit outside the git history but document the project's final stage (SOC mapping + coverage analysis).

---

## Architecture

```
finetune_FEC_BLS/
├── README.md                     # one-line stub: "#Replication materials for project"
├── .gitignore                    # ignores data/ and .env
├── draft_article.pdf             # (working tree) article draft
├── data/                         # ALL data is gitignored
│   ├── finetune.jsonl            # decoder file + training data (106,935 records)
│   ├── finetune_old.jsonl        # older 3-field variant (no prompt_occupation)
│   ├── 2020_SOC_classification.csv   # SOC crosswalk (1,921 rows)
│   ├── All_Occupations_ONET2024.csv  # O*NET occupation list (1,016 rows)
│   ├── dime_codebook_v3_1 (1).pdf
│   ├── contribs_2022.csv         # huge raw contribution dump (unreadable via read tool, GBs)
│   ├── contribs_2022.db          # SQLite copy of contribs (table `contributions`)
│   ├── contribs_2022_filtered*.csv, test/, temp_classifier/
│   └── contribs_2022/            # DIME-derived working set + classified outputs
├── scripts/                      # all pipeline scripts (23 .py + log)
├── streamlit/
│   └── gpt_finetune_streamlit.py # interactive web UI demo
└── debug/                        # untracked post-commit SOC/O*NET mapping work
```

**Directory roles:**
- **`data/`** — raw inputs (contributions, SOC/O\*NET references), the decoder/finetune JSONL, SQLite DB, and the intermediate + final classified outputs under `data/contribs_2022/`.
- **`scripts/`** — three functional families: (a) OpenAI classifier scripts (`OccupationClassifier_*`), (b) DIME→SQLite extraction/subset scripts (`dime_*`, `contribs2022_filter`), and (c) post-processing that maps decoded classifications back and analyzes them (`contribs_*`).
- **`streamlit/`** — a single Streamlit app wrapping the same model + decoder for interactive use.
- **`debug/`** — 14 numbered debug scripts and multi-GB CSVs used to validate/map the final O\*NET/SOC classifications (fuzzy matching).

---

## The Finetune Approach in detail

### Training data & the decoder-map pattern — `data/finetune.jsonl`

Each line is a JSON object with 4 keys:

```json
{
  "prompt": "classify this profession:  Salesperson ->",
  "completion": "sales representatives, wholesale and manufacturing, except technical and scientific product",
  "transformed_completion": "salesrepresentativeswholesaleandmanufacturingexcepttechnicalandscientificproduct ###",
  "prompt_occupation": "Salesperson"
}
```

- **`prompt`** — the exact fine-tuning prompt: `"classify this profession:  <occupation> ->"`. Note the prompt format and the trailing `->` marker that the model learns to complete.
- **`completion`** — the **human-readable** BLS occupation label (the "true" target for downstream analysis).
- **`transformed_completion`** — a **normalized token**: lowercase, all whitespace/punctuation removed, with a literal ` ###` suffix. This is what the model is actually trained to emit.
- **`prompt_occupation`** — the raw occupation string from the contribution data.

The **decoder-map pattern**: the model is trained to produce a *restricted, normalized token* instead of the free-form label. At inference time, every script builds
`decoder_map[transformed_completion] → completion` (via `decoder_map[entry["transformed_completion"].strip()] = entry["completion"]` in `load_decoder()`). The pipeline then:
1. Asks the model for the transformed completion.
2. Looks it up in `decoder_map`.
3. If found → yields the human label. If **not found** → the output is considered a **hallucination** and the row is retried (or flagged `insufficient_information_gpt`).

Because only a finite set of occupation labels exists (≈1,016 unique), the normalized token space is closed, making hallucination detection cheap and deterministic.

The newer decoder loaders also build a **`prompt_map`** (`prompt_occupation → transformed_completion`), enabling a pure lookup fallback: `data/contribs_2022_postcorrection_merge.py`-adjacent `batch_05.py`/`correction_01.py` use `prompt_map` to resolve occupations that exist verbatim in the training set without re-calling the API.

**Counts (verified):** `finetune.jsonl` = **106,935 records**. `finetune_old.jsonl` = 106,935 records but only 3 fields (`prompt`, `completion`, `transformed_completion`) — it predates the `prompt_occupation` field. `scripts/decoder_process.log` (2025-01-16 run) reports **"Loaded 1016 decoder mappings and 64008 prompt mappings"** — i.e. the training set contains ~64,008 distinct occupation-title spellings mapping onto ~1,016 unique occupation labels.

### Inference — `streamlit/gpt_finetune_streamlit.py`

The canonical inference call (identical across all classifier scripts):

```python
response = openai.ChatCompletion.create(
    model="ft:gpt-3.5-turbo-0613:personal::7qnGb8rm",   # the fine-tuned model ID
    messages=[
        {"role": "system", "content": "classify this entry:"},
        {"role": "user",   "content": occup_title}
    ],
    max_tokens=50,
    temperature=0.1
)
raw = response['choices'][0]['message']['content'].strip()
human = decoder_map.get(raw, None)     # None ⇒ hallucination
```

- **Model ID:** `ft:gpt-3.5-turbo-0613:personal::7qnGb8rm` (hard-coded in every script and the Streamlit app).
- **temperature = 0.1**, **max_tokens = 50** — low-temperature, short-output classification.
- **System prompt:** `"classify this entry:"` (the user message is the raw occupation).
- **Hallucination detection:** `decoder_map.get(raw, None)` returns `None` when the model emits an out-of-vocabulary token.
- **Retry UX (Streamlit `main()`):** shows "Raw Classification" and "Human-Readable Classification"; on a failed decode it prints a warning *"No match found for the raw output. Likely hallucination."* and offers a **Yes/No** radio to re-run.

The console equivalent (`OccupationClassifier_base_02.py`) implements a manual retry loop and clears the input only on a successful decode.

---

## Pipeline scripts (`scripts/`)

### 1. OpenAI classifier scripts — evolution toward resumable batch processing

| Script | Role |
|--------|------|
| `OccupationClassifier_base_01.py` | Minimal interactive classifier; no decoder; just prints raw model output. |
| `OccupationClassifier_base_02.py` | Adds the decoder map + hallucination/retry loop (console). |
| `OccupationClassifier_batch_02.py` | First batch processor: interactive column selection, csv/jsonl output, temp `temp_classifier/batch_*.{csv,jsonl}`, combine + cleanup; retries once per row then marks `insufficient_information_gpt`. |
| `OccupationClassifier_batch_03.py` | Refactor of batch_02 with logging/typing; same temp-file combine pattern. |
| `OccupationClassifier_batch_04.py` | Switches to **unique-occupation** processing over `most.recent.contributor.occupation`, writes incremental `temp_batches/batch_*.csv`, **resumes by skipping already-processed occupations** (`load_existing_batches`). |
| `OccupationClassifier_batch_04_reverse.py` | Same as batch_04 but iterates unique occupations in **reverse order** (for a partial/second-pass run), with the same resume capability. |
| `OccupationClassifier_batch_05.py` | Adds **`batch_decode_with_fallback`**: (1) standard decode, (2) **prompt_match** via `prompt_map`, (3) **retry** classification, then `insufficient_information_gpt`. Logs per-method stats. ⚠️ Contains a *TESTING ONLY* block (`num_batches = min(num_batches, 2)`; `unique_occupations = unique_occupations[:batch_size*2]`) commented as "Comment out these 2 lines for production". |
| `OccupationClassifier_scale_01.py` | The scale-up variant (jsonl output); loads decoder, processes rows in batches, temp-combine, with a 3-example preview before committing. |
| `OccupationClassifier_correction_01.py` | **Post-correction/rerun** pass: reads raw `batch_*.csv`, re-decodes each with the 3-step fallback, records audit columns (`initial_completion`, `prompt_match_completion`, `retry_transformed_completion`, `retry_completion`, `final_completion`, `decode_note`), writes `decoded_batch_*.csv`, logs to `decoder_process.log`, and **skips already-processed batches** via `get_processed_batches()`. |
| `OccupationSimulation_base_01.py` (+ `.ipynb`) | Demo that uses **gpt-4** (streaming) to *generate synthetic occupation misspellings* via an analogy prompt (Lawyer → Attorney; Atorney; Lawer; …) to simulate real-world occupation-title noise. |
| `OccupationSimulation_01.ipynb` | Notebook companion to the simulation demo. |

### 2. DIME → SQLite → subset scripts

| Script | Role |
|--------|------|
| `dime_sqlite.py` | Streams `data/contribs_2022.csv` into SQLite (`data/contribs_2022.db`, table `contributions`) in 1e6-row chunks. |
| `dime_subset_01.py` / `dime_subset_01_debug.py` | Chunked DB→CSV filter: `cycle 2020–2022`, `date 2019-01-01..2022-12-31`, `contributor.type == "I"`; writes `contribs_2022_filtered*.csv`. |
| `dime_subset_02.py` / `dime_subset_03.py` | Stricter filter: `cycle = 2022 AND seat LIKE 'federal:%' AND contributor.type = 'I'`; v3 uses `read_sql_query` with `chunksize` + tqdm. |
| `dime_subset_resume.py` | Same filter resuming from `offset = 3590000`. |
| `dime_subset_debug.py` | Dumps `PRAGMA table_info(contributions)` (column schema check). |
| `contribs2022_filter.py` | Pandas chunk filter of `contribs_2022.csv` to `contribs_2020_2022_filtered.csv` (dates 2020–2022, cycles [2020,2022], type `I`). |

### 3. Map-back / descriptives / post-correction

| Script | Role |
|--------|------|
| `contribs_2022_mapback.py` | Loads `temp_batches/batch_*.csv`, decodes via `finetune.jsonl`, fills NaN with `insufficient_information_gpt`, logs the % insufficient, saves `decoded_classifications.csv`. |
| `contribs_2022_mapback_02.py` | Left-merges decoded classifications back onto the original DIME file on `most.recent.contributor.occupation`. |
| `contribs_2022_descriptives.py` | Compares original vs merged row counts, NA%, unique occupations, and `insufficient_information_gpt` %. |
| `contribs_2022_descriptives_02.py` | Rebuilds the decoder from the `prompt` field (parses `classify this profession:`), then attempts to **re-decode `insufficient_information_gpt` rows** directly from `prompt_map`; saves `..._merged_updated.csv`. |
| `contribs_2022_postcorrection_merge.py` | Combines all `decoded_batch_*.csv` → `contribs_2022_decode_01.csv`, then left-merges `transformed_completion`, `final_completion`, `decode_note` onto the original → `contribs_2022_complete_01.csv`. |
| `contribs_2022_postcorrection_analysis.py` | Dedups `contribs_2022_complete_01.csv`, analyzes occupation nulls vs unmatched completions, and reports decode-note breakdown → `contribs_2022_complete_01_cleaned.csv`. |

### Real run stats — `scripts/decoder_process.log` (2025-01-16)
The `correction_01.py` rerun over the DIME dataset (batches of 100) logged a consistent decode-method mix, e.g. **standard_decode ≈ 88–94%, prompt_match_decode ≈ 1–4%, retry_decode ≈ 0–1%, insufficient_information_gpt ≈ 5–8%** per batch, with an estimated ~180–240 min total runtime.

---

## Data assets

| Asset | Path | Verified detail |
|-------|------|-----------------|
| Contributions DB | `data/contribs_2022.db` | SQLite, table `contributions`, loaded by `dime_sqlite.py` from `data/contribs_2022.csv`. |
| Raw contributions | `data/contribs_2022.csv` | Very large (single-file read times out); source of the DB and of the filtered DIME subset. |
| DIME individuals | `data/contribs_2022/dime_contributors_2022_individuals.csv` | The working DIME dataset (key column `most.recent.contributor.occupation`); also `dime_contributors_2022_individuals_merged[_updated].csv`. |
| Finetune/decoder data | `data/finetune.jsonl` | 106,935 training records; the canonical decoder file. `finetune_old.jsonl` = older 3-field version. |
| SOC crosswalk | `data/2020_SOC_classification.csv` | 1,921 rows; columns `uniqueID, majorgroup, submajorgroup, minorgroup, unitgroup, subunitgroup, OCC_TITLE_cap, OCC_TITLE, OCC_CODE` (e.g. `4122.01` = "Accounting clerks and bookkeepers"). |
| O\*NET occupations | `data/All_Occupations_ONET2024.csv` | 1,016 rows; columns `Job Zone, Code, Occupation, Data-level` (e.g. `13-2011.00` = "Accountants and Auditors"). |
| Classified outputs | `data/contribs_2022/contribs_2022_complete_01.csv`, `..._cleaned.csv`, `contribs_2022_decode_01.csv`, `decoded_classifications.csv` | Post-correction merged/cleaned datasets. |
| Batch artifacts | `data/contribs_2022/contribs_corrected/decoded_batch_*.csv` (~3,200 files, one per batch) | Per-batch decode audit output from `correction_01.py`. Also `contribs_rawbatches/`, `temp_batches - Copy/`, `temp_classifier/`. |
| DIME raw (debug) | `debug/dime_2022_final(240412).csv` | ~1 GB original DIME dump. |
| Final ONET-mapped | `debug/contribs_2022_final_02_with_onet.csv`, `..._clean - Copy.csv`, `contribs_2022_final_02.csv`, `contribs_2022_24july2025.csv` | Multi-GB datasets after O\*NET SOC mapping. |
| Mapping artifacts | `debug/final_completion_to_onet_mapping.json/.csv`, `debug/mapping_summary.txt`, `debug/onet_mapping_coverage_report.txt` | The final completion-category → O\*NET mapping plus coverage reports. |

**Final-stage SOC mapping results (from `debug/onet_mapping_coverage_report.txt`, verified):**
- Dataset: **6,087,017** records; **78.24%** (4,762,439) classified, **21.76%** unclassified.
- Classification method mix: `fuzzy_match` 2,834,128 (59.51%), `special_category` 1,927,866 (40.48%), `no_match` 445 (0.01%).
- Special categories: `not_employed` 1,786,442; `insufficient_information_gpt` 141,424.
- `debug/mapping_summary.txt`: 1,031 unique final categories → 1,026 successfully mapped to O\*NET, **99.71% coverage**, 3 unmapped (`actuary`, `orderly`, `nanny`).

---

## Lessons & reusable patterns for future finetuning

1. **Decode-with-closed-vocabulary beats open-text output.** Training the model to emit a *normalized token* and mapping it back deterministically makes hallucination detection trivial (`decoder_map.get(raw) → None`) and lets you **retry transparently**. The ` ###` suffix and whitespace-stripping guarantee a compact, stable token space.
2. **Low temperature (0.1) + short `max_tokens` (50)** is the right regime for closed-set classification: cheap, deterministic, and easy to gate on decode success.
3. **Process unique values, not rows.** The classifiers dedupe on `most.recent.contributor.occupation` before calling the API, build a crosswalk, then map back onto all rows — a huge cost saving when many rows share an occupation title (64k unique occupations vs 6M+ rows).
4. **Write-batches-and-resume.** Every scale script writes per-batch temp files and skips already-processed entries/batches on restart (`load_existing_batches`, `get_processed_batches`, the `batch_04_reverse` reverse-pass). This makes multi-hour runs resilient to crashes/rate limits.
5. **Multi-stage decode fallback.** The strongest design (`batch_05`/`correction_01`) layers: standard decode → **prompt_map lookup** (pure, free) → **API retry** → `insufficient_information_gpt`. Audit columns (`decode_note`, `initial/prompt_match/retry/final_completion`) make the provenance of every label transparent.
6. **Watch for leftover debug/test limits.** `batch_05.py` still contains a hard-coded "TESTING ONLY — limit to 2 batches" block that must be commented out for production — a classic silent-scope bug to check before re-running.
7. **Map to a stable external taxonomy last.** The 99.71% fuzzy-match mapping of the ~1,031 model categories onto O\*NET SOC codes shows the value of a final deterministic crosswalk step (categories → SOC/O\*NET), with a short explicit unmapped list (`actuary`, `orderly`, `nanny`) to resolve by hand.
8. **Keep the decoder file version-controlled and in-sync with the model.** The training/decoder data was deliberately removed from git (`a7e22ee`); the scripts hard-code absolute paths and one model ID (`ft:gpt-3.5-turbo-0613:personal::7qnGb8rm`) that must be updated together.

---

## File/Path Index

**Classifier scripts** — `scripts/OccupationClassifier_base_01.py`, `base_02.py`, `batch_02.py`, `batch_03.py`, `batch_04.py`, `batch_04_reverse.py`, `batch_05.py`, `scale_01.py`, `correction_01.py`
**Simulation** — `scripts/OccupationSimulation_base_01.py`, `scripts/OccupationSimulation_01.ipynb`
**DIME/DB extraction** — `scripts/dime_sqlite.py`, `dime_subset_01.py`, `dime_subset_02.py`, `dime_subset_03.py`, `dime_subset_resume.py`, `dime_subset_debug.py`, `dime_subset_01_debug.py`, `contribs2022_filter.py`
**Map-back / descriptives / post-correction** — `scripts/contribs_2022_mapback.py`, `contribs_2022_mapback_02.py`, `contribs_2022_descriptives.py`, `contribs_2022_descriptives_02.py`, `contribs_2022_postcorrection_merge.py`, `contribs_2022_postcorrection_analysis.py`, `scripts/decoder_process.log`
**App** — `streamlit/gpt_finetune_streamlit.py`
**Data root** — `data/finetune.jsonl`, `data/finetune_old.jsonl`, `data/2020_SOC_classification.csv`, `data/All_Occupations_ONET2024.csv`, `data/contribs_2022.csv`, `data/contribs_2022.db`
**DIME working set + classified outputs** — `data/contribs_2022/dime_contributors_2022_individuals*.csv`, `contribs_2022_complete_01*.csv`, `contribs_2022_decode_01.csv`, `decoded_classifications.csv`, `data/contribs_2022/contribs_corrected/decoded_batch_*.csv`
**Debug / SOC mapping (untracked, 2025-07-24)** — `debug/debug_01..14.py`, `debug/final_completion_to_onet_mapping.{json,csv}`, `debug/mapping_summary.txt`, `debug/onet_mapping_coverage_report.txt`, `debug/contribs_2022_final_02*.csv`, `debug/dime_2022_final(240412).csv`
