# R2 — Repo Deep-Analysis Memo (finetune pipelines)

**Date:** 2026-08-12
**Stream:** R2 — Repo analysis (EliteResearchAgent v1–v5, prior finetune FEC_BLS + pydeal_type, UN_AI_PANEL data)
**Status:** Complete. Read-only analysis; no source repos modified.

---

## 1. EliteResearchAgent v1–v5 — prosopography services & data artifacts

### 1.1 v1 (`C:\Users\spatt\Desktop\EliteResearchAgent`)
The canonical architecture doc `prosopography.md` defines a prosopography tool whose **component services map 1:1 onto the finetune candidate tasks**. This is the strongest signal in the whole analysis: the finetune "tasks" already exist as hand-built prompt pipelines, and their outputs are ready-made training data.

| Service (prosopography.md §) | Folder | Candidate finetune task | State |
|---|---|---|---|
| Web search + doc processing (§1) | (serper-based) | n/a (data acquisition) | working |
| Biographical info (§2) | `biographical/birthyear` | n/a | working, not atomized |
| **Education event (§3)** | v2 `services/education` | **Task 1: education extraction** | *"not confident… needs improvement"* → RAG/prompt weakness |
| **Career-event detection (§4a)** | `services/careerfinder_base_01`, `careerfinder_granular_01`, `RetroPropogation_01`, `EventAlign_*`, `Prosopography_01` | **Task 2: professional background extraction** | working, needs cleanup |
| **Org ontology (§4b)** | `services/org_ontology_01`, `org_ontology_02` | **Task 3: org harmonization** | *"weak link… needs most work"* |
| Ongoing career detection (§5a) | `RetroPropogation_02`, `RetroPropogation_03` | Task 2 (re-applied) | partially drafted |
| Ongoing ontology updates (§5b) | — | Task 3 | not started |

Key design principle stated by Scott in prosopography.md: preserve **claim→source links**, **triage by confidence**, verify claims in **≥2 sources** rather than trusting LLM self-eval. This is directly relevant to the anti-hallucination / "is this info about the target person" concern in the finetune plan.

### 1.2 Org ontology data (`org_ontology_02/ontology.json`)
Existing hand/LLM-built ontology with a clean schema — **this is a normalization/mapping gold source for Task 3**:
```json
{
  "Indian Foreign Service": {
    "canonical_name": "Foreign Service",
    "org_type": "Ministry of Foreign Affairs",
    "country": "India"
  },
  "Indian Embassy": { "canonical_name": "Foreign Service", "org_type": "Ministry of Foreign Affairs",
                      "country": "India", "posting_country": "Iran", "posting_city": "Tehran" }
}
```
Pattern: raw org mention → canonical name + org_type + country (+ optional posting geo). This is exactly the `classify + map` shape that suits a decoder-map finetune approach. `org_ontology_01` also has `motif.json.motif.json`, `explore_db.py`, `mfa_finder.py` (earlier exploration).

### 1.3 Careerfinder data (`careerfinder_granular_01`)
Per-person chunked career-event extraction exists under `review/<Person>/`:
- `summary.json` (per person: total_chunks, successful, errors, total_events, chunk list with source URLs)
- `chunk_*_results.json` (per-chunk career events, per source)
- `review/Abhijit_Banerjee/summary.json` shows 60 chunks, 219 events, 0 errors — a large **structured career-event gold source** for Task 2 (professional background).

### 1.4 v2–v5 evolution
- **v2** added the mature `services/education/` pipeline (extraction, consolidation, provenance, retrieval, verification, reports) + `services/AppliedOntology_*` + `Ontology_Initial_University` + `Ontology_unified` (university-name ontology with tag library + human-review Streamlit). `UNIVERSITY_ONTOLOGY_WORKFLOW.md` documents the extract-university-names → LLM-tag → human-review → export workflow. **Directly reusable for education-university harmonization.**
- **v3** has `config/config.json` + `config/prompts/` (versioned prompt files — the "save prompts as txt in consistent locations" convention from prosopography.md).
- **v4** is a database-heavy iteration (`db`, `backup.dump`, `DATABASE.md`, `improvements.md`).
- **v5** has `panel_members.json` (structured member list incl. Maria Ressa, Yoshua Bengio with bio/country) + `db/` + `frontend/` + pytest — the most "productized" version.

### 1.5 Takeaway for R2
- **EliteResearchAgent is the training-data mother lode.** The exact tasks we want to finetune (education, career, org harmonization) already have hand-tuned prompt pipelines and structured JSON outputs across v1–v5.
- **Do NOT copy these into the live finetune repo now** — just reference paths. The finetune `collect` stage should read from these repos read-only, or from exported snapshots.
- Highest-value gold sources: `careerfinder_granular_01/review/*/` (career), `org_ontology_02/ontology.json` + v2 `Ontology_*` (org/university normalization), v2 `services/education` (education pipeline logic + prompts).

---

## 2. Prior finetune work — FEC_BLS + pydeal_type

### 2.1 finetune_FEC_BLS (`C:\Users\spatt\Desktop\finetune_FEC_BLS`)
Occupation classifier → US BLS SOC code, via **OpenAI GPT-3.5 finetune with a decoder map** (this is the key reusable pattern):
- `data/finetune.jsonl`: `{"prompt": "classify this profession:  Salesperson ->", "completion": "sales representatives, wholesale...", "transformed_completion": "salesrepresentativeswholesale... ###", "prompt_occupation": "Salesperson"}`.
  The **`transformed_completion` is a normalized token** (spaces/punct stripped) that the model emits; a decoder map (`streamlit/gpt_finetune_streamlit.py`) maps it back to the human label. This **restrains hallucination / output-space drift** — directly relevant to the finetune plan's decoder-map idea for org harmonization.
- `streamlit/gpt_finetune_streamlit.py`: model `ft:gpt-3.5-turbo-0613:personal::...`, temperature 0.1, max_tokens 50; on unmatched output it flags "Likely hallucination" and offers retry. Good pattern for **output validation in the serve stage**.
- Pipeline scripts in `scripts/`: classification batch, reverse-batch, scale, postcorrection merge/analysis. Data: `contribs_2022.db`, `All_Occupations_ONET2024.csv`, `2020_SOC_classification.csv` (BLS/ONET mapping as ground truth).
- **Lesson:** OpenAI finetune works, but the decoder map + low temperature + explicit hallucination detection were what made it usable. The model id is a hardcoded legacy id (no longer portable).

### 2.2 pydeal_type (`C:\Users\spatt\Desktop\pydeal_type`)
UNGA speech → aggressor-state classification. The **Adaption Labs seed already exists here**:
- `runs/USA_01/prompt/aggressor_05/analysis/build_adaption_dataset.py` → `output/adaption_test_dataset_v1.csv` (100 rows: `prompt, context, output`), with a rigorous sampling discipline:
  - 40 positive (classification=1) / 60 negative (0), class-balanced.
  - Per-speaker cap (≤3) and per-target cap (≤3) to avoid domination.
  - ≥1 example per decade (1940s–2020s); both Cold War (pre-1991) and post-1991 eras.
  - Verifies no unfilled prompt placeholders.
  - **This is the template for the finetune `augment` stage's balanced sampling** (it generalizes to per-person caps + era coverage in the education/career tasks).
- The prompt reconstruction (`build_prompt`) shows the system + user template injection pattern (`system_prompt.txt` + `user_prompt.txt`).
- Evaluations live under `evaluation/` (eval_app.py, sampling/, annotated jsonl, accuracy metrics).

### 2.3 Takeaway for R2
- **Carry forward from FEC_BLS:** decoder-map output constraint, low temperature, hallucination detection, and the (now legacy) OpenAI finetune path.
- **Carry forward from pydeal_type:** the balanced/covered dataset sampler (`build_adaption_dataset.py`) as the `augment` stage template, and the Adaption `prompt/context/output` CSV format.

---

## 3. UN_AI_PANEL — gold-standard data inventory (feeds Task 1)

Confirmed the **education gold set** is richer than the plan assumed:
- `people/` = **79 member directories**.
- `review/education_check/education_check.json` (13.8 MB, generated 2026-08-10) has keys `[generated, vault, people, sources]`:
  - **79 people**, each with: `name, body, role, country, identity_confidence, factcheck_heading, terminal_education, education_header, degrees[], all_sources[], legacy_table, extra_sections`.
  - **`degrees[]`** — structured education per person. First person (Bilal Mateen) has 3 degrees. Fields per degree (from `build_data.py`): `id, index, row_number, fields{level,field,university,year,country}, quote, quote_effective, quote_inherited_from, source_note, sources_cell, citations[], flags[]`.
  - **842 source documents** embedded in `sources` (the plan said ~161; actual is 842 — even better).
- The `build_data.py` pipeline already: resolves block-reference citations back to raw sources, matches quotes (exact/partial/none), and flags issues (malformed, unsourced, possible_two_degrees, year_prose, single_citation, quote_paraphrased). Regression bar: 79 people / 193 degrees / 334 anchored citations.

### 3.1 Takeaway for R2
- **Task 1 (education extraction) is fully supervised** with a fact-checked, citation-resolved gold set: person bio + raw source docs → structured degrees (level/field/university/year/country). The `education_check.json` records are the natural `assistant` targets for the finetune `collect` stage.
- **Distractor/anti-hallucination material is already present:** `all_sources[]` lists every fetched source *including uncited ones*, so we can build negatives where a degree in an uncited source must NOT be attributed to the target — exactly the C3 probe need.
- Counts to reconcile in C1 split: 79 people / 193 degrees; use person-disjoint split.

---

## Synthesis for the finetune pipeline

| Pipeline stage | Reusable prior art (read-only path) |
|---|---|
| `collect` | `education_check.json` (Task 1 gold); `careerfinder_granular_01/review/*/` (Task 2); `org_ontology_02/ontology.json` + v2 `Ontology_*` (Task 3) |
| `augment` | `pydeal_type/.../build_adaption_dataset.py` (balanced/covered sampling), FEC_BLS decoder-map (output constraint) |
| `adapt` | `pydeal_type/.../adaption_test_dataset_v1.csv` (prompt/context/output format) |
| `train` | FEC_BLS `finetune.jsonl` shape (prompt/completion/transformed_completion) |
| `store` | none yet — new |
| `serve` | FEC_BLS `gpt_finetune_streamlit.py` (temp 0.1, hallucination detection) |

**Recommendation:** R2 confirms the "prove Task 1 end-to-end first" plan is right. Education extraction has a complete, fact-checked gold set (79 people / 193 degrees / 842 sources) and the anti-hallucination distractor material already exists. The three candidate tasks map to three existing EliteResearchAgent prompt pipelines, so the broader vision (miniaturize a stabilized general-LLM workflow to a small finetuned model) is directly applicable once Task 1 is proven.
