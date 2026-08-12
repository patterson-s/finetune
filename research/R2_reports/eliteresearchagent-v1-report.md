# EliteResearchAgent v1 — Development Map

**Repo:** `C:\Users\spatt\Desktop\EliteResearchAgent`
**Nature:** "v1" prosopography tool for elite research (UN High-Level Panel on Digital Cooperation members)
**Scale:** ~671 MB working tree, ~13,850 files (excluding `.git`; 18,319 incl.), 43 commits, git history 2025-11-25 → 2026-02-04
**Git:** loose-object repo, 4,422 objects / ~103 MB; no packs. Branches: `main` (HEAD), `focused-hertz`, `claude/infallible-lehmann` (remote `origin/main`, `origin/focused-hertz`).

---

## Overview

EliteResearchAgent is a **prosopography pipeline** for building biographical and career-event networks of international elites. The subject population is the members of the **UN High-Level Panel on Digital Cooperation** (76 names in `names/person_names.json` — from Anand Panyarachun and Gro Harlem Brundtland through Amandeep Singh Gill, Jack Ma, Melinda French Gates, to Jean Tirole and Gordon Brown).

The tool turns unstructured web biographies (Wikipedia, CVs, PDFs, news) into **structured, quote-backed career events** (roles at organizations over time, plus awards), storing them in PostgreSQL with pgvector embeddings. It is a **collection + LLM-extraction + human-review** system, built entirely on prompt-driven LLM pipelines (Cohere `command-a`, Anthropic Claude) with a **review-first** design philosophy: every extraction writes JSON to a `review/` folder for human inspection before any DB commit, and every claim carries verbatim source quotes + source URL + chunk id (provenance).

The project is explicitly *in progress* — the top-level `prosopography.md` (last edited Feb 13 2026) is a status/roadmap document rating each of 6 services, and `CLAUDE.md` documents the working architecture.

---

## Timeline & Development

From `git log --date=short` (oldest→newest). Branch labels noted:

| Date | Commit | Notes |
|------|--------|-------|
| 2025-11-25 | `4baf74a` initial | First commit; then `c59ff14` built search + initial database, `a994193` completed search function, `8a65e2b`/`8c42835` added birthyear function/markdown |
| 2025-12-17 | `f25e65d` add birthyear md | Biographical service + design principles |
| 2026-01-13 | `55e5fea` catch up | |
| 2026-01-14 | `ecbfa8d` org_ontology_01; `99cd4ec` rerun career finder; `6fe648a` group evaluation; `9599b14` scrollable team-eval interface | Careerfinder + org ontology work; **careerfinder_base_01 review batch run 20260114** |
| 2026-01-19 | `07d6830` pipeline; `f34eaa7` org ontology interface; `1685dd1` mistral interface; `fe3b71b` interface for org ontology | Streamlit UI experiments; `org_ontology_02` created; `EventAlign_01` empty scaffold |
| 2026-01-21 | `36b0184` streamlined eval interface; `cb110c5` fix updated interface; `fc1890c` update interface multi-person; | `analysis/` stratified sampling scripts + plots; `review/human_eval` |
| 2026-01-29 | `50d51ef` added award separation; `7bce400` added granular career detector; `81f162d` full pipeline; `1f51358` add pipeline for granular; `8b5ca7e`/`eca7739` EventAlign_02/03 | **careerfinder_granular_01 review run (chunk_*_results.json, 75 persons)** |
| 2026-02-02 | `a586c8a` add event align; `2bd21ee` eventalign4; `7ffe3aa` add retroprop; | EventAlign_04, RetroPropogation_01 |
| 2026-02-03 | `bbf5b03` added retroprop2; `4442b69` Add Prosopography_01 combined tool; `85ce5e2` fix Streamlit imports; `6fc3e3e` Add database setup script | **focused-hertz branch tip** = `6fc3e3e` (merge-base with main). Prosopography_01 introduced. |
| 2026-02-03/04 | `6fdf071` Serper integration + Cohere compat; `f2065ad`/`aaba1da` Render deploy config; `6da1a8a` Python 3.11.4; `5dadbd6` auto-Wikipedia fetch; `2f4a3ba` org inference for diplomatic careers; `d1bfd5e`–`719d904` evidence-panel UI polish + batch Phase 1 | **main tip** = `719d904` (Feb 4). Prosopography_01 becomes a full Streamlit web app (Dashboard / Template Builder / Review Events / Supplementation pages). |

**Branches:**
- `main` — the live line of work, ending with the **Prosopography_01 Streamlit web app** (Feb 4).
- `focused-hertz` — tip = `6fc3e3e` (Feb 3), which is exactly the **merge-base** of main and focused-hertz. It has **zero commits not on main**; it is a *snapshot behind main*, not a forward branch. Diff `main..focused-hertz` = the 12 commits main added after the fork (the entire Prosopography_01 web-app layer: `source_search.py`, `batch_processor.py`, `render.yaml`, `startup.py`, and the 4 Streamlit UI pages were *added on main*, i.e. absent from focused-hertz). Effectively **abandoned/stale** — its name suggests an early attempt to "focus" the Hertz-era codebase, superseded by the full Prosopography_01 app on main.
- `claude/infallible-lehmann` — a lightweight pointer branch; `git rev-parse` confirms it points to the **same commit as main HEAD** (`719d904`). Not divergent. It corresponds to the Claude Code **worktree** found nested inside the repo at `services/RetroPropogation_03/.claude/worktrees/infallible-lehmann/` (6,702 files, ~267 MB — a near-duplicate of the whole repo), which accounts for most of the 671 MB footprint and the 13,850 file count. (Also explains object/blob duplication of `chunks_dataset.pkl`, `all_chunks.json`, etc.)

---

## Architecture

`prosopography.md` defines the target as a set of **services 1–5b**. Mapping to folders:

| # | Service (per prosopography.md) | Status (doc) | Folder(s) |
|---|-------------------------------|--------------|-----------|
| 1 | Web search + document processing (Serper → fetch → chunk → embed → DB) | working | `search/` (sub: `serper/`, `ocr/`, `embeddings/`, `provenance/`, `pipeline.py`, `load_review.py`) + `database/` |
| 2 | Biographical info (birth year, alive/death, nationality) | working, not atomized | `biographical/birthyear/` |
| 3 | Education event service | not confident | (no dedicated folder; folded into career extraction) |
| 4a | Population-level career-event detection | working | `services/careerfinder_base_01/`, `services/careerfinder_granular_01/`, `services/RetroPropogation_01/`, `services/Prosopography_01/phase1..3`, `services/EventAlign_03/` |
| 4b | Initial organizational ontology | drafted, not complete (**HIGH priority, weak link**) | `services/org_ontology_01/`, `services/org_ontology_02/` |
| 5a | Ongoing career-event detection | partially drafted | `services/RetroPropogation_02/`, `services/RetroPropogation_03/` |
| 5b | Ongoing ontology updates | not started | — |

**Top-level folders:**
- `search/` — collection tier. Serper API search → HTML/PDF fetch (BeautifulSoup/PyPDF2) → Mistral OCR for poor PDFs → ~400-token chunks → Cohere `embed-v4.0` → PostgreSQL. `search/pipeline.py` orchestrates 5 steps; `search/load_review.py` commits reviewed JSON to DB. `search/serper/` has `client.py`, `fetcher.py`, `batch.py`, `outputs/`; `search/embeddings/` has `chunk_json.py`, `embed_json.py`; `search/ocr/` has `mistral.py`; `search/provenance/generate.py` writes narrative provenance. (The heavy chunk/embed artifacts live in the DB, not in-tree.)
- `database/` — PostgreSQL module. `connection.py` (pooling), `schema/sources.sql` (schemas: `persons_searched`, `search_results`, `chunks`, `embeddings`). `README.md` documents `eliteresearch` DB. `run_schema.py` at root creates the `prosopography` schema from `services/Prosopography_01/db/schema.sql`.
- `analysis/` — QA/monitoring: `stratified_sample_01.py`, `stratified_sample_02.py` (sample the careerfinder_base_01 review JSONs for human eval) + two PNG distributions of events-per-chunk (`distribution_events_per_chunk.png`, `cumulative_distribution_events_per_chunk_logscale.png`, Jan 21).
- `names/` — `person_names.json`: the 76-person target list.
- `review/` — `human_eval/` staging for manual evaluation of extractions.
- `design/` — `designprinciples.md`: the review-first / provenance / confidence-triage philosophy.
- `biographical/birthyear/` — the service-2 implementation (pipeline, batch, extraction, verification, provenance, schema.sql, usage.md, MARKDOWN.md, `review/` for 75 people, `data/chunks_dataset.pkl`).
- `services/` — all extraction services (below).

**Cross-cutting patterns (from `design/designprinciples.md`, `CLAUDE.md`, code):**
1. **Review-first** — pipelines write JSON to `review/`; human inspects; separate `load_review.py` commits.
2. **Complete provenance** — every event = verbatim `supporting_quotes` + `source_url` + `chunk_id` + document_type.
3. **Pluggable LLM client** — `llm_client.py` per service; switch `anthropic`/`cohere`/`mistral` at runtime (`--llm-provider`). Cohere `command-a-03-2025` (temp 0.1) and Claude `claude-sonnet-4-5-20250929`/`4-6` used.
4. **Output namespacing** — results under `outputs/<run_id>/<person>/` so model runs don't overwrite.
5. **Structured output** — forced JSON/tool-call mode, no free-text parsing.
6. **2-source rule** — claims confirmed by ≥2 independent sources before "verified".
7. **Prompts as `.txt` files** in each service's `config/prompts/` for fast versioning (per prosopography.md Flow).

---

## The Services in Detail

### Service 1 — Web search & document processing (`search/` + `database/`)
Collects sources on the 76 elites, extracts document contents, chunks + embeds, stores in PostgreSQL. **Prompt approach:** none (deterministic scraping/OCR); Mistral OCR for poor PDFs; Cohere `embed-v4.0` for vectors. **Data artifacts:** `search/serper/outputs/search_results_<ts>.json` pipeline staging; provenance narratives; DB tables `sources.*`. **State (prosopography.md):** *working*. Doc notes the only gap is **name disambiguation** (Enrique Iglesias the singer vs. the panelist; Gareth Evans the filmmaker vs. politician) — priority VERY LOW.

### Service 2 — Biographical information (`biographical/birthyear/`)
Extracts birth year, alive/death, nationality from collected sources. **Prompt approach:** per-person LLM extraction with `verification.py` requiring corroboration; provenance tracked; `summarize_results.py` aggregates. **Data artifacts:** `review/birthyear_<Person>_<ts>.json` for **75 people** (Nov 26 2025 batch) + `batch_summary_20251126_005156.json`; `data/chunks_dataset.pkl` (44 MB source-chunk corpus); `all_people.json` (75 names). **State:** *working, but not atomized*; prosopography.md proposes upgrading to a targeted RAG (ask "in what year was X born", 2-source rule, unique-source count for triage). Priority LOW.

### Service 3 — Education events
Not separately implemented. prosopography.md rates it *not confident* and recommends a RAG approach (fewer events than careers, focus on university education, 2-source rule). Priority Medium.

### Service 4a — Career-event detection
Three generations:
- **`careerfinder_base_01`** — first version. "Maximum recall, not precision." Single-stage: load all chunks per person → extract events per chunk → save raw. Event = org/role/location change → new event; partial events allowed; ≥1 supporting quote. **Prompt:** `config/prompts/system.txt` + `user.txt` (doc says *"initial version, poor prompt"*). **Data:** `data/all_chunks.json` + `all_chunks - Copy.json` (7.3 MB each, the shared source-chunk corpus); `review/` = **72 per-person `careerfinder_base_<Person>_20260114_*.json` files + 144 total files** (incl. `batch_state_20260114_122958.json`, `checkpoints/`). Note: the base_01 review files use a `raw_extractions` schema (org/role/location/start/end/description/quotes/chunk/source_url).
- **`careerfinder_granular_01`** — the "better version", 3-step: **step1** extract entities (time_markers/organizations/roles/locations, CV vs. narrative prompts), **step2** assemble entities into events + classify **career_position vs. award**, **step3** verify (temporal coherence, quote support, flag-don't-fix). **Prompts:** `config/prompts/step1_cv_structured.txt`, `step1_narrative.txt`, `step2_assembly.txt`, `step3_verification.txt`. **Data:** `review/<Person>/chunk_*_results.json` (each with step1/step2/step3) + `summary.json` per person → **75 persons, 2,714 chunk-result files, 2,789 JSON files, 10,469 total events** (see Careerfinder section). Model `command-a-03-2025`, temp 0.1.
- **`Prosopography_01/`** — the consolidated 3-phase tool (see below) that reproduces 4a inside a web interface.

### Service 4b — Organizational ontology (`services/org_ontology_01`, `_02`)
**`org_ontology_01`** — Streamlit + Mistral attempt to discover orgs from `data/careerfinder_results.jsonl` (2.5 MB, extracted orgs); files `explore_db.py`, `mfa_finder.py`, `mistral_streamlit.py`, `motif.json.motif.json`.
**`org_ontology_02`** — the "current" builder: `load_data.py` counts raw org strings + collects person/role/location/dates examples; `fuzzy_grouping.py` clusters org names (fuzzywuzzy/rapidfuzz, threshold 80 in `config.json`); `app.py` is a Streamlit **Organization Ontology Builder** that shows clusters of unmapped raw orgs and lets a human map them into `ontology.json`. **Schema** (see next section): raw org string → `canonical_name`, `org_type`, `country`, optional `posting_country`/`posting_city`. **State (prosopography.md):** *drafted, not complete*; needs to re-apply the ontology to career-event data; HIGH priority — identified as the project's **weakest link** (also confirmed in `CLAUDE.md`).

### Service 5a/5b — Ongoing detection & ontology updates (`services/RetroPropogation_*`)
- **`RetroPropogation_01`** — 4-step batch pipeline: step1 extract entities (parallel, 4 workers), step2 discover canonical orgs, step3 assemble events, step4 verify. **Data:** `outputs/cohere_01/` = **66 people**; `outputs/anthropic_claude_01/` = **2 people** (Amre Moussa, Gro Harlem Brundtland). E.g. Gro Harlem Brundtland (Anthropic run): 11 chunks / 27,287 chars → 175 time-markers, 92 orgs, 71 roles, 55 locations → 57 canonical orgs → 34 events (20 career, 14 award; 18 valid, 16 warnings). `validate_ui.py` reviews.
- **`RetroPropogation_02`** — incremental enrichment: `step1_extract_candidates.py`, `step2_match_or_new.py`, `step3a_enrich_event.py` / `step3b_create_event.py`, `prepare_source.py`, `load_existing.py`. Processes non-Wikipedia sources against existing events (match-and-enrich vs. create-new). `outputs/Amre_Moussa/` (decision_log.json, events.json, processed_sources.json, summary.json). `new/` holds tar.gz archives. Uses Cohere temp 0.3.
- **`RetroPropogation_03`** — folder that contains `RetroPropogation_01/` + `RetroPropogation_02/` copies AND the `.claude/worktrees/infallible-lehmann/` worktree (267 MB) — largely a packaging/backup container, not a distinct service.

**`Prosopography_01/`** (the current flagship, on main):
- **phase1** (`extract_entities.py`, `discover_orgs.py`, `assemble_events.py`, `verify_events.py`, `pipeline.py`) — initial full-pass extraction over all source chunks, with canonical-org discovery. `batch_processor.py` adds multi-person batching.
- **phase2** (`correction_service.py`, `event_editor.py`) — human correction layer.
- **phase3** (`extract_candidates.py`, `match_or_new.py`, `enrich_event.py`, `create_event.py`, `pipeline.py`) — ongoing detection on unseen sources (Service 5a), using `match_or_new` to decide supplement-vs-new.
- **UI** — Streamlit app: `ui/app.py`, `ui/pages/1_Dashboard.py`, `2_Template_Builder.py`, `3_Review_Events.py`, `4_Supplementation.py`, `ui/components/evidence_panel.py` (scrollable evidence context, HTML quote highlighting — the last commits). **Template Builder** auto-fetches Wikipedia.
- **db/** — `schema.sql` (schemas `prosopography.persons`, `canonical_organizations`, `organization_aliases`, `career_events`, evidence/correction/issue tables), repositories. `setup_database.py`, `startup.py` (Render), `render.yaml`, `requirements.txt`, `source_search.py`, `llm_client.py` (Cohere `command-a-03-2025`, temp 0.1, max_tokens 8000), `evaluation/metrics.py` (extraction-quality metrics), `validation/issue_tracker.py`, `review/Amre_Moussa/` (phase1_entities/canonical_orgs/events/verification JSONs).

**EventAlign (`services/EventAlign_01..04`)** — a parallel line for **timeline consolidation / cross-chunk event alignment**:
- `EventAlign_01` — **empty** scaffold.
- `EventAlign_02` — build_timeline, group_candidates, normalize_entities, consolidate_llm, explore/view_timeline. `outputs/`: `01_normalized_entities.json`, `02_candidate_groups.json`, `03_consolidated_events.json` (e.g. 50 consolidated events for Abhijit Banerjee with `consolidated_event_id` G001, decision different_events, variant aggregation, provenance source_event_count/source_chunks/source_urls, confidence), `04_final_timeline.json`, `temporal_clusters.json`, `unmapped_events.json`, `timeline_coverage.json`, `all_normalized_events.json`, `all_resolved_events.json`.
- `EventAlign_03` — **batch** pipeline (`batch_pipeline.py`, `analyze_coverage.py`, `generate_report.py`, `inspect_none.py`, `load_events.py`): phase1a discover career labels, phase1b award labels, phase2a/2b classify. `data/` = per-person chunk results; `outputs/` = **75 people** each with `01a_career_labels.json`, `01b_award_labels.json`, `02a_career_classifications.json`, `02b_award_classifications.json`, `03_cores_report.json` (+ `archive/`).
- `EventAlign_04` — `phase1a_extract_cores.py`, `phase1b_extract_none.py`; `outputs/` = **2 files** (Abhijit_Banerjee_phase1a/1b.json) — a partial/experimental run.

**`services/person_package/Gro_Harlem_Brundtland/`** — a hand-assembled reference package: `New folder/` (empty) + `RetroPropogation_01/` (pipeline_summary.json, step1_entities.json, step2_canonical_orgs.json, step3_events.json, step4_verification.json) — a model end-to-end run to emulate.

---

## Org Ontology data

**`services/org_ontology_02/ontology.json`** (read in full — only 13 lines / 2 entries):

```json
{
  "Indian Foreign Service": {
    "canonical_name": "Foreign Service",
    "org_type": "Ministry of Foreign Affairs",
    "country": "India"
  },
  "Indian Embassy": {
    "canonical_name": "Foreign Service",
    "org_type": "Ministry of Foreign Affairs",
    "country": "India",
    "posting_country": "Iran",
    "posting_city": "Tehran"
  }
}
```

**Schema** (raw org-string key → value object):
- `canonical_name` (string) — the standardized institution name raw orgs collapse into.
- `org_type` (string) — e.g. "Ministry of Foreign Affairs" (the DB enum in `Prosopography_01/db/schema.sql` is `university, government, international_org, company, research_center, ngo, commission, other`).
- `country` (string) — home country of the org.
- `posting_country` / `posting_city` (optional strings) — posting/assignment geography for diplomatic postings.

The two entries illustrate the intended modeling: "Indian Foreign Service" and "Indian Embassy" both canonicalize to "Foreign Service" (a ministry), with the embassy additionally carrying posting geography (Iran/Tehran). The ontology is **effectively empty** (2 seeded examples) — this is the concrete measure of how early-stage Service 4b is. The builder UI (`app.py`) and fuzzy-grouping (`fuzzy_grouping.py`) are built and working; the *content* still needs populating from the org names in `org_ontology_01/data/careerfinder_results.jsonl`.

---

## Careerfinder data

**`services/careerfinder_granular_01/review/`** — the richest structured dataset in the repo:

- **75 persons** with a `summary.json` each (one person missing vs. the 76-name list; e.g. the 76th — a long-tail name — is not in the granular review set; granular review holds 75 of 76 targets).
- **2,714 `chunk_*_results.json`** files (2,789 JSON files total in the folder).
- **10,469 total career events** across the 75 summaries (`total_events` summed). Aggregated run stats: 75 summaries, all successful, 0 errors.
- Example — **Abhijit Banerjee**: 60 chunks, 60 successful, 0 errors, **219 total events**. His `summary.json` lists per-chunk `source_url`, `events_count`, `valid_count` (e.g. chunk 3174 from a MIT short-bio → 10 events, 8 valid; MIT CV PDF chunks → 0). His `chunk_3115_results.json` (Wikipedia) has top keys `status, chunk_id, chunk_index, source_url, title, document_type` + `step1` (entities: time_markers with text/type point|range|open + quotes; organizations with name+quotes), `step2` (`assembled_events`: event_type career_position/award, time_marker_ids, organization_ids, role_ids, location_ids, supporting_quotes, confidence, notes), `step3` (`verified_events` with event_id/status/issues + `summary`).

**Schema of one chunk result** (granular, 3-step):
- `step1.entities.time_markers[]` = {text, type (point|range|open), quotes[]}
- `step1.entities.organizations[]` = {name, quotes[]}; `roles[]`, `locations[]` likewise
- `step2.assembled_events[]` = {event_type, time_marker_ids[], organization_ids[], role_ids[], location_ids[], supporting_quotes[], confidence, notes}
- `step3.verified_events[]` = {event_id, status (valid|warning|error), issues[]}; `step3.summary`

**`services/careerfinder_base_01/review/`** — earlier, lower-fidelity pass: **72 per-person files** `careerfinder_base_<Person>_20260114_*.json` (Jan 14 batch) with a `raw_extractions[]` schema (organization/role/location/start_date/end_date/description/supporting_quotes/chunk_id/source_url), plus `batch_state` and `checkpoints/` — **144 files, no `summary.json`**. Some files large (e.g. Mohammad Abdullah Al Gergawi ~2.3 MB).

**`analysis/stratified_sample_01.py`** consumes the base_01 review files (extracts person, chunk_id, source_url, and counts `"organization"` per raw extraction) for human-eval sampling — the QA workflow.

---

## Path Divergences

- **`main`** carries everything through Feb 4, culminating in the **Prosopography_01 Streamlit web application** (Serper integration in `source_search.py`, Render deployment, `batch_processor.py`, Wikipedia auto-fetch in Template Builder, diplomatic org inference, and the evidence-panel UI fixes). This is the active deliverable.
- **`focused-hertz`** (tip `6fc3e3e`, Feb 3) = the **merge-base**; it is **behind** main by 12 commits and has **no unique commits**. The diff `main..focused-hertz` (≈ −1,564 lines) shows focused-hertz lacks the entire Prosopography_01 web-app layer that main added: no root `render.yaml`, no `services/Prosopography_01/render.yaml`/`requirements.txt`/`startup.py`/`source_search.py`/`batch_processor.py`, and gutted UI pages (Dashboard −172, Supplementation −176, Template_Builder −114, evidence_panel −160) plus a smaller `db/connection.py` and `llm_client.py`. **Interpretation:** an early "focused" strip-down of the Hertz-era code that was **superseded/abandoned** once main built out the full Prosopography_01 app. Nothing in focused-hertz is worth salvaging that isn't already (superset) on main.
- **`claude/infallible-lehmann`** — **not a divergent branch**: it points at the same commit as `main` HEAD. It is the label for the **Claude Code worktree** physically present at `services/RetroPropogation_03/.claude/worktrees/infallible-lehmann/` (6,702 files, ~267 MB, a full working-tree duplicate of the repo). This duplicate is the main reason the repo is 671 MB / 13,850 files; `git count-objects` shows only ~103 MB of actual objects. The `RetroPropogation_03/` folder is itself largely a container of copied prior services plus this worktree — i.e. **packaging/backup noise**, not a functional service.
- **Abandoned/partial lines:** `EventAlign_01` (empty), `EventAlign_04` (only 2 test outputs, Jan-Feb), `org_ontology_01`'s Mistral UI (superseded by `org_ontology_02`), `RetroPropogation_03/RetroPropogation_02/new/*.tar.gz` archives, stray root `nul` file (45 bytes, a `type: .env` mishap), `review/human_eval` (staging only).

---

## Training-Data Potential for Finetune

The repo is a strong source of **paired extraction data with built-in ground-truth-ish structure and provenance**:

1. **Career-event extraction corpus (largest asset).** `services/careerfinder_granular_01/review/` gives **75 subjects, 2,714 source-chunk→extraction pairs, 10,469 events**, each carrying verbatim `supporting_quotes`, source URL, chunk id, document_type, event_type (career_position/award), confidence, and step3 verification status. This is a ready instruction/function-call dataset: *input = unstructured biography chunk, output = structured event JSON*. The step1/step2/step3 decomposition provides natural staged targets (entity-extraction → assembly → verification), and the `valid`/`warning` flags supply a weak supervision signal.

2. **Multi-source corroboration labels.** `EventAlign_02` consolidated events carry `provenance.source_event_count` / `source_chunks` / `source_urls` — i.e. **which events were seen in ≥2 independent sources** (the project's "2-source rule" verification signal). `EventAlign_03` adds per-person career/award **label** files (`01a/01b`) and **classifications** (`02a/02b`) + `03_cores_report.json` across **75 people** — a second, taxonomy-focused dataset.

3. **Canonical-organization mapping (small but high-value seed).** `org_ontology_02` shows the raw-org → canonical_name/org_type/country/posting-geo schema (2 seeded examples), while `org_ontology_01/data/careerfinder_results.jsonl` (2.5 MB) is the pool of raw org strings to map. Good for an org-normalization fine-tune, though labels are sparse (ontology still near-empty).

4. **Biographical QA.** `biographical/birthyear/review/` has **75 per-person JSON extractions** (birth year etc., Nov 26 2025) — usable as a biographical question-answering dataset.

5. **Cross-model outputs.** `RetroPropogation_01/outputs/` has **cohere_01 (66 people)** and **anthropic_claude_01 (2 people)** runs of the same 4-step pipeline — a small multi-model consistency/comparison set; the Gro Harlem Brundtland person package has the full 4-step artifact chain (entities→canonical orgs→events→verification).

6. **Human-eval sampling harness.** `analysis/stratified_sample_01.py`/`_02.py` already implement stratified sampling of the review data — reusable to build a train/eval split.

**Caveats for training:** no gold labels exist (all extractions are LLM-generated, unvalidated at scale); event/org IDs link to *IDs* not resolved strings in step2/3 (need joining); base_01 (`raw_extractions`) and granular (step-based) use **different schemas** — pick one; the ontology mapping and human-validation sets are the only "gold" pieces and are tiny.

---

## Other-Useful Material

- **`CLAUDE.md`** — concise architecture summary (4 tiers: collection → event discovery → incremental enrichment → database) + run commands (`search.pipeline`, `RetroPropogation_01/batch_pipeline.py`, `run_schema.py`), LLM config (Claude defaults in RetroProp_01; Cohere in RetroProp_02), and the same gap list as prosopography.md.
- **`prosopography.md`** — the living roadmap/status doc; essential for understanding intent vs. implementation.
- **`design/designprinciples.md`** — the review-first + provenance + confidence-triage philosophy (the "why" behind every pipeline).
- **`database/README.md`** + `database/schema/sources.sql` + `services/Prosopography_01/db/schema.sql` — the full relational model (sources → chunks → embeddings; persons → canonical_organizations → organization_aliases → career_events + evidence/correction/issue tables).
- **`render.yaml`** (root) — Render Blueprint: Streamlit web service (rootDir `services/Prosopography_01`) + free Postgres `prosopography-db`; pin `PYTHON_VERSION 3.11.4`; expects `DATABASE_URL`, `COHERE_API_KEY`, `SERPER_API_KEY`.
- **`.env`** — keys only: `SERPER_API_KEY, DB_HOST/PORT/NAME/USER/PASSWORD, COHERE_API_KEY, MISTRAL_API_KEY, ANTHROPIC_API_KEY`.
- **`requirements.txt`** (root): psycopg2-binary, requests, python-dotenv, beautifulsoup4, streamlit, cohere, flask==3.0.0, pyyaml, PyPDF2, mistralai, numpy, rapidfuzz, matplotlib, scipy, fuzzywuzzy, python-Levenshtein, anthropic.
- **`names/person_names.json`** — the canonical 76-subject roster (UN High-Level Panel on Digital Cooperation).
- **Not in-tree:** the actual chunk/embedding vectors and most scraped full-text live in the PostgreSQL DB, not the repo; only sample/all_chunks JSON corpora are versioned.

---

## File/Path Index

**Root:** `prosopography.md`, `CLAUDE.md`, `render.yaml`, `requirements.txt`, `.env`, `run_schema.py`, `nul` (junk).

**Collection:** `search/pipeline.py`, `search/load_review.py`, `search/serper/{client,fetcher,batch}.py`, `search/ocr/{mistral,inspect_json,process_json}.py`, `search/embeddings/{chunk_json,embed_json}.py`, `search/provenance/generate.py`.
**Database:** `database/{connection.py, README.md}`, `database/schema/sources.sql`, `services/Prosopography_01/db/schema.sql`.
**Roster:** `names/person_names.json` (76).
**Biographical:** `biographical/birthyear/` (`pipeline.py`, `batch.py`, `extraction.py`, `verification.py`, `provenance.py`, `summarize_results.py`, `schema.sql`, `review/` ×75, `data/chunks_dataset.pkl`, `all_people.json`).
**Design:** `design/designprinciples.md`.
**Analysis:** `analysis/stratified_sample_01.py`, `_02.py`, 2 PNG event-distribution plots.
**Review staging:** `review/human_eval/`.

**Services:**
- `services/careerfinder_base_01/` — `pipeline.py`, `pipeline_batch.py`, `extraction.py`, `evaluate.py`, `evaluate_team.py`, `config/prompts/{system,user}.txt`, `data/all_chunks*.json`, `review/` ×72+144.
- `services/careerfinder_granular_01/` — `extraction_step1/2/3.py`, `classification.py`, `pipeline_batch.py`, `load_data.py`, `fix_summary.py`, `app_test.py`, `config/prompts/step1_cv_structured|step1_narrative|step2_assembly|step3_verification.txt`, `review/` ×75 (2,714 chunk files, 10,469 events).
- `services/org_ontology_01/` — `explore_db.py`, `mfa_finder.py`, `mistral_streamlit.py`, `data/careerfinder_results.jsonl`.
- `services/org_ontology_02/` — `app.py`, `load_data.py`, `fuzzy_grouping.py`, `config.json`, **`ontology.json`**.
- `services/EventAlign_01/` (empty), `_02/` (`build_timeline.py`, `group_candidates.py`, `normalize_entities.py`, `consolidate_llm.py`, `pipeline.py`, `view/explore_timeline.py`, `outputs/*`), `_03/` (batch_pipeline, `phase1a/b`, `phase2a/b`, `analyze_coverage.py`, `generate_report.py`, `inspect_none.py`, `load_events.py`; `data/`+`outputs/` ×75), `_04/` (`phase1a_extract_cores.py`, `phase1b_extract_none.py`; 2 outputs).
- `services/RetroPropogation_01/` — `pipeline.py`, `batch_pipeline.py`, `llm_client.py`, `load_data.py`, `validate_ui.py`, `step1..4_*.py`, `outputs/{cohere_01 ×66, anthropic_claude_01 ×2}`.
- `services/RetroPropogation_02/` — `pipeline.py`, `prepare_source.py`, `load_existing.py`, `step1_extract_candidates.py`, `step2_match_or_new.py`, `step3a_enrich_event.py`, `step3b_create_event.py`, `prompts/`, `outputs/Amre_Moussa/`, `new/*.tar.gz`.
- `services/RetroPropogation_03/` — copies of RetroProp_01/02 + **`.claude/worktrees/infallible-lehmann/`** (duplicate repo, 267 MB).
- `services/Prosopography_01/` — `batch_processor.py`, `llm_client.py`, `source_search.py`, `setup_database.py`, `startup.py`, `utils.py`, `render.yaml`, `requirements.txt`, `config/{config.json,prompts/*.txt}`, `db/` (schema.sql + repos), `phase1/`, `phase2/`, `phase3/`, `ui/` (app + 4 pages + evidence_panel), `evaluation/metrics.py`, `validation/issue_tracker.py`, `review/Amre_Moussa/`.
- `services/person_package/Gro_Harlem_Brundtland/` — reference 4-step artifact set.

---

*Report generated from live exploration of the repo (git log/branch/diff, file reads, JSON inspection). All paths above verified to exist; event/entity counts computed directly from `summary.json`/`chunk_*_results.json`/pipeline summaries.*
