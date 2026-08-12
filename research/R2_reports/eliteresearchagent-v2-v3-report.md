# EliteResearchAgent v2 & v3 — Development Map

Combined development-mapping report for Scott's prosopography tooling iterations.
Repo roots: `C:\Users\spatt\Desktop\EliteResearchAgent_v2` (git 2026-02-12..02-13, 7 commits) and
`C:\Users\spatt\Desktop\EliteResearchAgent_v3` (git 2026-02-17..02-25, 14 commits).
All findings below were verified by reading the actual files and git history.

---

## Overview

EliteResearchAgent is a prosopography research tool for **international elites** — UN High-Level Panel
members and related figures. It ingests unstructured biographical/source text, extracts structured facts
(education history, career events, organizational affiliations), and classifies the organizations those
individuals belong to. The project went through a series of rapid iterations in Feb 2026:

- **v1**: (prior iteration, not covered here) — initial RAG + reranking question-answering against a
  PostgreSQL database of embedded source chunks.
- **v2** (7 commits, 2026-02-12 → 2026-02-13): Built a **services/education pipeline** (extraction →
  consolidation → verification → provenance → JSON reports), a **biographical** service of the same shape,
  and a cluster of **ontology** services that classify organizations (initially universities, then UN/gov,
  then a unified + career ontology).
- **v3** (14 commits, 2026-02-17 → 2026-02-25): Rebased and **hardened the organizational-ontology /
  entity-resolution layer** — a config-driven service layout with versioned `.txt` prompt files, a Serper
  + Cohere "stub enrichment" pipeline, a fuzzy/LLM matcher, and stub-review UI. It also carried over v2's
  education *data* (copy scripts) but did **not** re-implement v2's education *pipeline*.

In short: **v2's emphasis was on the education/bio extraction pipeline and the university ontology; v3's
emphasis shifted to career-event extraction and org-entity matching/classification.** Both converge on the
same underlying goal (clean, verifiable prosopographic records), but v3's focus moved from "answer the
education/bio question" to "build and de-duplicate the organization ontology that underlies career
analysis."

---

## v2 Timeline & Focus

**Git log (7 commits):**

```
51d9dab 2026-02-12 initial
e5a0e46 2026-02-13 added biographical and educational service
1cfe8cf 2026-02-13 add university ontology
cb849da 2026-02-13 update ontology eval site
13f0f8b 2026-02-13 working on eval interface
b366ae4 2026-02-13 struggling with interface and edge cases
ce4be51 2026-02-13 added ontology builder for university
```

v2 was a single two-day burst. The `initial` commit is the v1→v2 handoff; everything else in v2 is new.
**What v2 added on top of v1:**

- **`services/education/`** — a complete, config-driven education-history pipeline (see next section).
- **`services/biographical/`** — a sibling pipeline for biographical facts (same module shape:
  `pipeline.py`, `retrieval.py`, `extraction.py`, `verification.py`, `provenance.py`, `report.py`,
  `batch.py`, plus `config/`, `prompts/`, `reports/`, `review/`, `data/`).
- **`services/AppliedOntology_01/` and `AppliedOntology_02/`** — the "applied ontology" layer: chunk
  loading (`load_data.py`), stepwise extraction (`extraction_step1..3.py`), `classification.py`,
  `event_splitter.py`, `person_aggregator.py`, `process_person.py`, `profile_enricher.py`, plus
  `ontology/`, `output/`, `pipeline/`. This is the career-event extraction machinery.
- **Ontology services** — `Ontology_Initial_University`, `Ontology_unified`, `OntologyBuilder_v1`,
  `OntologyCareer_v1` (see "v2 Ontology work" below).
- **`services/simplified/`** — per-person simplified data JSONs (e.g. `Abhijit_Banerjee.json`,
  `Amina_J._Mohammed.json`, ...).
- **`UNIVERSITY_ONTOLOGY_WORKFLOW.md`** — a runbook tying the education reports to the university-ontology
  service (extract university names → LLM-tag → human-review in Streamlit → export verified ontology).
- Top-level scratch files: `2.9`, `-p/`, `requests/`, `orders.md`, `database/`, `.env`,
  `requirements.txt`.

v2's final commit message, "struggling with interface and edge cases," signals that the Streamlit
review interface for ontology tagging was the friction point where v2 ended.

---

## v2 Education Pipeline in detail

Located at `services/education/`. Config-driven, Cohere-based, five stages wired together by
`pipeline.py`. Config lives in `config/config.json` (retrieval + extraction + verification settings) and
`config/questions/education_history.json` (the single question template). Prompts are external files in
`prompts/` (`system.txt`, `user.txt`, `consolidation.txt`, `verification.txt`, `final_selection.txt`).
Outputs are full per-person JSON reports written to `reports/` (e.g.
`Abhijit_Banerjee_education_history_20260212_190736.json`, ~20–42 KB each).

**Stage 1 — `retrieval.py`** (`retrieve_chunks`)
Embeds the question query per person with Cohere `embed-v4.0` (1536-dim), computes cosine similarity
against pre-embedded source chunks (a `chunks_dataset.pkl` DataFrame filtered to the person), keeps the
top ~40 above a 0.15 threshold, then re-ranks with Cohere `rerank-v3.5` (top 15). A variant
`retrieve_chunks_excluding()` fetches substantiation chunks while excluding already-used chunk ids.

**Stage 2 — `extraction.py`** (`extract_education_events`)
For each retrieved chunk, builds a system+user prompt from the templates and calls Cohere
`command-a-03-2025` (temp 0.3, max_tokens 800) to pull structured `education_events`. A regex-based
parser extracts `reasoning`, `confidence` (high/medium/low), `supporting_quote`, `evidence_type`, and the
events array. `validate_education_event` enforces schema: requires `organization` + `degree_program`,
**filters out academic-employment events** (professor/postdoc/lecturer/faculty indicators) so only
*student* experiences survive, validates degree level/status against the question config, coerces years to
1900–2099 ints, and cleans string fields.

**Stage 3 — `consolidation.py`** (`consolidate_education_events`)
Merges near-duplicate events across chunks via a low-temp (0.1) Cohere call using `prompts/consolidation.txt`.
Returns `consolidated_events`, `discarded_events`, and `consolidation_reasoning`. **Crucially it has a
rule-based fallback** (`perform_fallback_consolidation`) that groups by normalized org name, keeps the most
complete event as the base, and records discarded duplicates with reasons — used on API/network failure.

**Stage 4 — `verification.py`** (`verify_education_events`)
Corroboration scoring. Normalizes events (org name variants like "University of Oxford"→"Oxford";
handles combined degrees), compares with a weighted similarity function
(org 40% / degree components 30% / level 20% / time 10%), merges similar events into `EducationEvent`
objects that track distinct source domains and field-level evidence, and assigns status per event:
`verified` (≥ threshold sources, default 2), `partial` (1), `unverified` (0). Produces overall
`verification_status` (`verified` / `partial_verified` / `mixed` / `partial` / `no_evidence`).

**Stage 5 — `provenance.py`** (`generate_education_provenance` / `..._json`)
Writes a human-readable provenance narrative (RETRIEVAL / EXTRACTION / EVENT CONSOLIDATION / VERIFICATION /
EVENT DETAILS / QUALITY ASSESSMENT / RECOMMENDATIONS) and a structured provenance dict carrying retrieval
stats, confidence distribution, consolidation reasoning, and verification event details.

**`pipeline.py`** (`run_education_pipeline`) orchestrates 1→5, with **early stopping** (stops scanning
chunks once one event is verified), emits progress to stdout, and dumps a single comprehensive JSON report
per person containing the result, retrieval candidates, extractions, consolidation, verification, and both
provenance forms. Supports `--person all` and `--question all` batch modes. CLI: `python pipeline.py
--person "Name" --question education_history`.

The overall design is a clean RAG → extraction → dedupe/merge → multi-source corroboration → auditable
report loop, purpose-built to answer one question type ("education_history").

---

## v2 Ontology work

Four related ontology services were built or refined in v2:

**`Ontology_Initial_University`** — the entry point. `main.py`/`tagging_service.py` send university name
strings to Cohere to produce minimal canonical tags ("Harvard University"→"Harvard", "Oxon."→"Oxford"),
saved to `data/university_tags_verified.json` and `data/tag_library.json`. Several Streamlit interface
variants (`interface.py`, `interface_clean.py`, `interface_final.py`) power the human-review UI
(progress bar, autocomplete, batch verify, autosave every 5 min, export). `link_universities_to_chunks.py`
connects universities back to source chunks. Config in `config/config.json`.

**`OntologyBuilder_v1`** — *university ontology enrichment.* `ontology_enricher.py` + `search_engine.py`
(Serper web search) + Cohere extraction add official names, country codes, and city locations to each
university entry, with an interactive CLI for careful per-entry verification, automatic backups
(`data/backups/`), and a Serper search cache. Produces `data/university_ontology.json` — **144 entries**
(verified via a count). Each entry's schema:
```json
{ "tag": "AUC",
  "title_official": "The American University in Cairo",
  "sector": "academia",
  "unstructured": ["American University in Cairo", "American University of Cairo"],
  "location_country": "EGY", "location_city": "Cairo" }
```
Also `consolidate_education_data.py` and a `final_education/` dir of per-person consolidated education
event JSONs (`Abhijit_Banerjee_education_events.json`, etc.).

**`Ontology_unified`** — a service (`cli.py`, `generate_tree.py`, `unified_ontology.json`,
`un_ontology_tree.txt`, `test_unified_ontology.py`) that **merges the UN System, national-government, and
university ontologies into one unified schema**. Per-org record example (from `unified_ontology.json`):
```json
{ "canonical_name": "Brundtland Commission (World Commission on Environment and Development)",
  "org_types": ["commission"], "meta_type": "io", "sector": "intergovernmental",
  "location_country": null, "location_city": null, "source": "un_gov_ontology",
  "un_ontology": { "canonical_tag": "UN:TemporaryAdvisoryBodies:SGCommissions:Brundtland",
                   "hierarchical_tags": ["United Nations","UN","UN:TemporaryAdvisoryBodies", ...],
                   "tag_count": 5, "status": "completed" }, "gov_ontology": {} }
```

**`OntologyCareer_v1`** — the career-organizational ontology (UN + government tagging).
Files like `apply_gov_ontology.py`, `meta_type_classifier.py`, `integrate_un_ontology.py`,
`add_meta_types.py`, `analyze_other_category.py`, and `data/completed*.json`,
`data/combined_organizational_ontology*.json` show iterative classification of orgs into meta-types /
sectors, with `docs/un_ontology_report.md` summarizing the UN tagging work.

**Workflow glue**: `UNIVERSITY_ONTOLOGY_WORKFLOW.md` documents the end-to-end path — `extract_university_names.py`
scans education reports for university mentions → `universities_all.json` → LLM tagging → Streamlit human
review → export verified university ontology for downstream education enhancement and social-network analysis.

---

## v3 Focus

v3 restarts from a cleaner, **config-and-prompts-driven** base (git dates 2026-02-17 → 02-25):

```
4b3a77c 2026-02-17 initial commit
8b85f00 2026-02-17 initial
60f4daa 2026-02-17 added cohere API service
8f26b48 2026-02-18 added WikiPrompt service
d15b261 2026-02-18 add timeline improvements
4ac1f7b 2026-02-18 add ontology_01 matching service
cb7dd93 2026-02-18 fix matcher: skip fuzzy for ngo/private/other types, raise review threshold
c286ca3 2026-02-18 add stub enrichment: Serper search + LLM field extraction + merge/dismiss
0799d67 2026-02-18 swap enrichment LLM from Claude to Cohere Command-A
5055964 2026-02-18 add parent_org field and multi-tag support to stub review
6072be0 2026-02-18 fix stub review widget key collision causing data bleed between stubs
4021dac 2026-02-18 add production batch enrichment CLI (batch_enrich_full.py)
6ac86b2 2026-02-25 added targeted_01 service
3124554 2026-02-25 updated missing people
```

**Config-driven design.** `config/config.json` is minimal and central:
```json
{ "service_name": "eliteresearchagent_v3", "version": "1.0.0",
  "model": "command-a-03-2025", "temperature": 0.1, "max_tokens": 4000,
  "api_key_env_var": "COHERE_API_KEY",
  "llm": {...}, "processing": { "context_window_words": 30 },
  "prompts": { "test_cohere_connection": "config/prompts/test_cohere_connection.txt" } }
```
`config/prompts/` holds **versioned, explicitly-labelled `.txt` prompt files** — `OrgExtraction_01.txt`,
`OrgExtraction_02.txt`, `OrgExtraction_03.txt` (incrementally refined org-extraction prompts) and
`test_cohere_connection.txt`. The `instructions.md` progress log confirms this was a deliberate pattern:
"each of the prompts should be in a txt file and clearly labelled." v3 also modernized the Cohere call to
`ClientV2.chat()` (the legacy `generate()` was deprecated).

**Service inventory (v3):**
- `services/data_loader/` — loads career-event chunks from PostgreSQL, filters by person, saves JSON.
- `services/biographical/` — retained bio pipeline (batch, extraction, provenance, report, retrieval,
  review).
- `services/ontology_01/` — the **centerpiece**: `matcher.py`, `fuzzy_match.py`, `llm_match.py`,
  `smart_merge.py`, `targeted_merge.py`, `comprehensive_merge.py`, `merge_similar_entities.py`,
  `embedding_match.py`, `ontology_db.py`, `review_app.py`, `run_matching.py`, `batch_enrich.py`,
  `batch_enrich_full.py`, and outputs `smart_ontology.json`, `targeted_ontology.json`,
  `merged_ontology.json`, `combined_ontology.json`, `final_ontology_v2.json`, `unified_ontology.json`.
  This is the entity-resolution / org-matching subsystem: match fuzzy org names → LLM field extraction →
  merge/dismiss → human review.
- `services/OrgExtraction/` — org extraction (`org_extraction.py` + test).
- `services/WikiPrompt/` and `services/WikiAugment/` — an alternative career-timeline approach: batch
  Wikipedia processing, LLM timeline extraction, gap-finding, dedup, fact-checking
  (`step2_fact_check.py`, `step3_gap_finder.py`, `step4_dedup.py`). Builds granular career records.
- `services/FactChecking_01/` — fact-checking service + extensive tests and `person_test_results/`.
- `services/analysis_01/`, `services/analysis_02/` — career-event / HLP analysis runs over
  `career_events/` (ontology.json + `run_analysis.py`).
- `services/integrated_01/` — the integrated system (`integrated_01.md`): hybrid strategy using RAG for
  narrow-answer questions and WikiPrompt+WikiAugment for full career-path questions.
- `services/targeted_01/` — targeted RAG question-answering service (`retrieval.py`, `report.py`,
  `runner.py`, per-person `data/` with `*_base.json`).
- Top-level: `analysis/` (typology, ideal_types, career_tags, locations, orgs analysis pipelines),
  `endgame/`, `utils/example_cohere_api.py`.

**Carrying education data forward.** v3 did *not* abandon the education output. A cluster of scripts at the
repo root — `copy_education_files.py`, `copy_education_batches.py`, `copy_education_simple.py`,
`copy_education_final.py`, `copy_all_education.bat`, `copy_education_batch.bat`, `copy_education_complete.bat`,
`create_bio_files.py`, `generate_copy_commands.py`, `debug_education.py`, `check_missing_files.py` — copy
v2's `*_education_history_*.json` reports into per-person `career_events` directories in v3 (renamed to
`*_edu.json`), and verify which people are missing `_career_events.json` / `_bio.json` / `_edu.json` /
`_org_links.json`. So **v3 reuses v2's education *data* but drops v2's education *pipeline code***.

---

## Path Divergences (v2 vs v3)

| Dimension | v2 | v3 |
|---|---|---|
| **Dates / size** | 2026-02-12 → 02-13; 7 commits, one 2-day burst | 2026-02-17 → 02-25; 14 commits over ~9 days |
| **Primary focus** | Question-answer pipelines: **education** + biographical; university ontology | **Organization ontology / entity resolution** (matcher, enrichment, stub review); career-event + integrated analysis |
| **Education** | Full 5-stage pipeline + per-person JSON reports | Pipeline **removed**; only the reports carried over via copy scripts (renamed to `*_edu.json`) |
| **Ontology thrust** | Universities first, then UN/gov, then unified; Streamlit review UI | Org matching/enrichment: Serper + Cohere stub enrichment, fuzzy/LLM/smart/targeted merge, review_app |
| **Prompt management** | Prompts as files under each service's `prompts/` (system/user/consolidation/etc.) | Central `config/prompts/` with **versioned** files (`OrgExtraction_01/02/03.txt`) — explicit "prompts in txt files" rule |
| **Config** | Per-service `config/config.json` (rich, e.g. retrieval/extraction/verification blocks) | Minimal central `config/config.json` + config-driven services |
| **LLM call style** | `co.chat(...)` (Cohere) | Cohere `ClientV2.chat()`; one commit swapped enrichment LLM Claude→Cohere Command-A |
| **Analysis** | Light | Heavy: `analysis/` typology, ideal_types, locations, orgs, career_tags; integrated_01/targeted_01 hybrid strategy |

**Did v3 abandon v2's education pipeline?** Effectively **yes** as *code* — none of
`extraction.py` / `consolidation.py` / `verification.py` / `provenance.py` / `pipeline.py` survive in v3's
`services/`. But v3 **kept the education data** by copying the reports into per-person career_events dirs,
and it retained a `services/biographical/` pipeline. The strategic pivot was from "answer biographical +
education questions via RAG with corroboration" (v2) toward "build a clean, de-duplicated organization
ontology + full career-event record, then answer analytical questions" (v3, as articulated in
`integrated_01.md` — where the author explicitly notes v2's RAG approach failed at full career-path
reconstruction due to a recentness bias).

---

## Training-Data Potential for Finetune

These repos are rich sources of **supervised extraction and entity-resolution training data**:

1. **Education extraction + consolidation + verification pairs (v2).**
   - `services/education/reports/*_education_history_*.json` — per-person reports bundling raw LLM
     extraction output, extracted `education_events`, consolidation reasoning, verification status,
     source/domain evidence, and provenance narratives. Ideal for training (a) structured-event extraction
     from biographies, (b) near-duplicate event merging, (c) multi-source corroboration/verification.
   - `services/education/config/questions/education_history.json` + `prompts/*.txt` give the exact prompt
     templates and field-validation rules (good instruction-pair context).
   - `services/OntologyBuilder_v1/final_education/*_education_events.json` — cleaned per-person event lists.

2. **University / org ontology (v2 + v3).**
   - `services/OntologyBuilder_v1/data/university_ontology.json` — **144** university records with
     canonical tag, official title, sector, unstructured name variants, ISO country code, city. Perfect
     canonical-variant (entity resolution) pairs.
   - `services/Ontology_Initial_University/data/university_tags_verified.json` and `tag_library.json` —
     original name → LLM tag → human-verified tag triples (including flagged/bad extractions, useful as
     negative examples).
   - `services/Ontology_unified/unified_ontology.json` — UN/gov/university merged schema with
     hierarchical UN tags (e.g. `UN:TemporaryAdvisoryBodies:SGCommissions:Brundtland`).
   - v3 `services/ontology_01/` outputs — `smart_ontology.json`, `targeted_ontology.json`,
     `merged_ontology.json`, `combined_ontology.json`, `final_ontology_v2.json` — multiple rounds of
     fuzzy/LLM/targeted merge results, plus `review_app.py` stub-review logic. These are natural
     input/output pairs for entity matching and deduplication finetuning.

3. **Career-event extraction (v3).**
   - `services/WikiPrompt/` — `batch_outputs/`, `llm_timeline_data/`, per-person `*_v1.json` / `*_v2.json`
     career-event JSONs and raw Wikipedia text (`Abhijit_Banerjee_raw.txt`, `amina_mohammed_wikipedia.txt`).
   - `services/FactChecking_01/person_test_results/` and `results/` — fact-checking runs over careers.
   - `services/analysis_01/career_events/` and `services/targeted_01/data/` — per-person base/career JSONs.

4. **Prompt-engineering corpus.** v3's `config/prompts/OrgExtraction_01/02/03.txt` show an explicit
   iterative-prompt-refinement trajectory (v1→v2→v3 of the same task) — useful for studying how prompt
   edits change outputs, if the corresponding outputs were preserved.

**Caveat:** the `.env` files contain a live Serper API key (also hardcoded in
`OntologyBuilder_v1/config.py`); strip secrets before any data sharing. Many report filenames are
timestamped per run, so there are multiple versions of the same person's data (e.g. two
`Anand_Panyarachun_education_history_*.json` files) — a ready-made consistency/eval set but also a
deduping concern.

---

## File/Path Index

### v2 — `C:\Users\spatt\Desktop\EliteResearchAgent_v2`
- `UNIVERSITY_ONTOLOGY_WORKFLOW.md` — end-to-end runbook: education reports → university ontology.
- `services/education/` — 5-stage pipeline. Files: `retrieval.py`, `extraction.py`, `consolidation.py`,
  `verification.py`, `provenance.py`, `pipeline.py`, `__init__.py`; `config/config.json`,
  `config/questions/education_history.json`; `prompts/{system,user,consolidation,verification,final_selection}.txt`;
  `reports/*_education_history_*.json`; `utils/{extract_university_names.py,README.md}`.
- `services/biographical/` — `batch.py`, `extraction.py`, `load_data.py`, `load_review.py`, `pipeline.py`,
  `provenance.py`, `report.py`, `retrieval.py`, `verification.py` + `config/`, `prompts/`, `reports/`,
  `review/`, `data/`.
- `services/AppliedOntology_01/` — `load_data.py`, `extraction_step1..3.py`, `classification.py`,
  `event_splitter.py`, `person_aggregator.py`, `process_person.py`, `profile_enricher.py`, `ontology/`,
  `output/`, `pipeline/`, `config/`, `data/`, `utils/`, `test_output/`, `test_fixes_output/`.
- `services/AppliedOntology_02/` — (career-event ontology layer; see root `instructions.md`-style docs).
- `services/Ontology_Initial_University/` — `main.py`, `tagging_service.py`, `interface*.py`,
  `link_universities_to_chunks.py`, `prepare_enhanced_data.py`, `CLI_GUIDE.md`, `config/config.json`,
  `prompts/university_tagging.txt`, `data/{universities.json, universities_with_chunks.json,
  university_tags_verified.json, university_tags_enhanced.json, tag_library.json, uploaded_education_data.json}`.
- `services/Ontology_unified/` — `cli.py`, `generate_tree.py`, `test_unified_ontology.py`, `README.md`,
  `unified_ontology.json`, `un_ontology_tree.txt`, `ontologie_report.{md,txt}`.
- `services/OntologyBuilder_v1/` — `config.py`, `search_engine.py`, `ontology_enricher.py`,
  `consolidate_education_data.py`, `README.md`; `data/university_ontology.json` (144 entries),
  `data/search_cache/`, `data/backups/`, `final_education/*_education_events.json`,
  `visualizations/`.
- `services/OntologyCareer_v1/` — `apply_gov_ontology.py`, `meta_type_classifier.py`,
  `integrate_un_ontology.py`, `add_meta_types.py`, `analyze_other_category.py`, `GOV_TAGGING_SERVICE_SETUP.md`,
  `data/{completed*.json, combined_organizational_ontology*.json, analyze_ngos.py}`,
  `docs/un_ontology_report.md`, `tagging/`.
- `services/simplified/data/*.json` — per-person simplified records.
- Top-level: `2.9`, `orders.md`, `-p/`, `requests/`, `database/`, `.env`, `requirements.txt`.

### v3 — `C:\Users\spatt\Desktop\EliteResearchAgent_v3`
- `config/config.json` (minimal central config); `config/prompts/` — `OrgExtraction_01.txt`,
  `OrgExtraction_02.txt`, `OrgExtraction_03.txt`, `test_cohere_connection.txt`.
- Root scripts (education data migration): `copy_education_files.py`, `copy_education_batches.py`,
  `copy_education_simple.py`, `copy_education_final.py`, `copy_all_education.bat`,
  `copy_education_batch.bat`, `copy_education_complete.bat`, `create_bio_files.py`,
  `generate_copy_commands.py`, `debug_education.py`, `check_missing_files.py`.
- `instructions.md` (progress log), `integrated_01.md` (integration strategy), `requirements.txt`, `.gitignore`.
- `services/ontology_01/` — `matcher.py`, `fuzzy_match.py`, `llm_match.py`, `smart_merge.py`,
  `targeted_merge.py`, `comprehensive_merge.py`, `merge_similar_entities.py`, `embedding_match.py`,
  `ontology_db.py`, `review_app.py`, `run_matching.py`, `batch_enrich.py`, `batch_enrich_full.py`,
  `check_*.py`, outputs (`smart_ontology.json`, `targeted_ontology.json`, `merged_ontology.json`,
  `combined_ontology.json`, `final_ontology_v2.json`, `unified_ontology.json`), `instructions.md`.
- `services/data_loader/` — `load_data.py`, `extract_wikipedia.py`, per-person chunk JSONs,
  `EMBEDDING_ACCESS_REPORT.md`.
- `services/biographical/` — retained bio pipeline.
- `services/OrgExtraction/` — `org_extraction.py`, `test_org_extraction.py`, `README.md`.
- `services/WikiPrompt/` — `batch_process_wikipedia.py`, `extract_timeline_with_llm.py`,
  `enhance_timeline_data.py`, `run_extraction.py`, `prompt_main.txt`, per-person raw/v1/v2 JSONs,
  `batch_outputs/`, `llm_timeline_data/`.
- `services/WikiAugment/` — `pipeline.py`, `retrieval.py`, `schema.py`, `step2_fact_check.py`,
  `step3_gap_finder.py`, `step4_dedup.py`, `utils.py`, `outputs/`.
- `services/FactChecking_01/` — `fact_checking_service.py`, `debug_embedding.py`, tests, `results/`,
  `person_test_results/`, `prompts/`, `README.md`.
- `services/analysis_01/`, `services/analysis_02/` — `run_analysis.py`/`run_hlp_analysis.py`,
  `career_events/`, `ontology.json`, `prompts/`.
- `services/integrated_01/` — `pipeline.py`, `career_analyzer.py`, `rag_runner.py`, `wiki_runner.py`,
  `retrieval.py`, `report.py`, `db.md`, `template.md`, `plan.md`, `targeted_01.md`, `update.md`,
  `wiki_cache/`, `outputs/`.
- `services/targeted_01/` — `pipeline.py`, `retrieval.py`, `report.py`, `runner.py`, `data/` (per-person
  `*_base.json`), `outputs/`, `scripts/`, `prompts/`, docs.
- `analysis/` — `CLAUDE.md`, `instructions*.md`, `load_db.py`, and `career_tags/`, `ideal_types/`,
  `locations/`, `orgs/`, `typology/`, `typology_02/` pipelines + build_report scripts.
- `utils/example_cohere_api.py`; `endgame/instructions_23mar2026.md`.
