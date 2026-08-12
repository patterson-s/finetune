# Full Cross-Repo Development Map — All Finetune-Relevant Repos

**Date:** 2026-08-12
**Scope:** Synthesizes all per-repo reports across Scott's research and finetuning repos to give a single, complete picture of the work that has gone into each, their timelines, their path divergences, and — most importantly for the current project — **what each one offers as training data and reusable finetuning patterns**.

**Repos covered:**
| Repo | Path | Period | Focus |
|---|---|---|---|
| pydeal_type | `C:\Users\spatt\Desktop\pydeal_type` | Jan–Apr 2025 | UNGA diplomatic accusation classification (multi-model) |
| finetune_FEC_BLS | `C:\Users\spatt\Desktop\finetune_FEC_BLS` | Dec 2024–Jan 2025 (+ Jul 2025 debug) | Occupation→BLS SOC fine-tune |
| EliteResearchAgent v1–v5 | `C:\Users\spatt\Desktop\EliteResearchAgent(_v2.._v5)` | Nov 2025–Jun 2026 | Prosopography tooling for UN panels |

---

## 1. The big picture

Across ~18 months Scott built three distinct bodies of work that share a hidden common thread:

1. **pydeal_type** (early 2025) — a *multi-model LLM classification pipeline* over UNGA speeches, where the core innovation was running **two different Cohere models over the same data** so outputs could be cross-checked for confidence. It also contains the **only finished Adaption Labs dataset** in the whole ecosystem.
2. **finetune_FEC_BLS** (late 2024–early 2025) — the **only actual model fine-tune** in the ecosystem (OpenAI GPT-3.5). It pioneered the **decoder-map / closed-vocabulary output** pattern that keeps hallucination out of classification.
3. **EliteResearchAgent v1–v5** (late 2025–mid 2026) — a *prosopography tool* for UN panel elites that evolved through five divergent iterations, producing enormous amounts of **structured, source-grounded, verification-labeled extraction data** — the largest training-data reservoir of all.

**The unifying opportunity:** the EliteResearchAgent repos contain the *tasks we want to finetune for* (education extraction, career/professional extraction, org harmonization) already solved as prompt-pipelines with rich outputs and verification labels. pydeal_type shows *how to triage confidence* via multi-model agreement. finetune_FEC_BLS shows *how to keep a small finetuned model from hallucinating* (decoder map). The finetune project can combine all three: use EliteResearchAgent data as the training corpus, pydeal_type's confidence-triage as the label-filtering method, and FEC_BLS's decoder-map as the output architecture.

---

## 2. pydeal_type — the multi-model confidence experiment

**Research question:** How do states construct/contest social facts about other states in UNGA rhetoric, and when is one state explicitly portrayed as aggressive/malicious toward another?

**Timeline (commits ≠ work):** git shows 8 commits (2025-01-27 → 02-18), but the working tree spans **2025-01-22 → 2025-04-14**. Two-phase:
- **Phase 1 (Jan 2025):** theory-heavy 4-prompt "ladder of abstraction" typology (`scripts/` + `runs/ungdc_*`, `extended_test*`, `test*`).
- **Phase 2 (Feb 2025, "big push"):** pivot (commit 2025-02-04 "moved towards single country focus") to a **binary aggressor/victim classifier** on the USA case — `runs/USA_01/prompt/` with ~14 self-contained prompt variants (aggressor_02..05, victim_01..03, aggressor_victim_01, contestedstate, idealyear_*, applyideal_other_01, rus_victim_01, socialfact_01). Flagship = `aggressor_05`, which processed the full 1946–2022 corpus (~21,400 records).

**The crown jewel — two Cohere models on the same data:**
- `command-r7b-12-2024` (small/cheap, temp 0.7) → `output/full/ungdc_commandr7b_{YEAR}.jsonl` (per year)
- `command-r-plus-08-2024` (large) → `output/parsed/ungdc_commandrplus_{YEAR}.jsonl`
- Same `doc_id`/`chunk_id`/`text`/`target` on both sides → **direct per-record comparison** via `merger7brplus.py`. Also `victim_01_results_{r7b,commandrplus}.jsonl`, `aggressor_02/output/{initial_r7b, commandrplus_2022/}`.
- `command-a-03-2025` was the planned QC/reviewer model (`plan_tomorrow.md`).

**Confidence-triage machinery (already built):** `evaluation/evaluation_01.ipynb` computes `across_dataset_agreement` (PP/NN/PN/NP), `across-model_agreement`, `model_coverage_breakdown()`, `add_agreement_variables()`; `evaluation_02.ipynb` adds intra-coder (prompt-stability) reliability. Human-annotated samples exist (`evaluation_sample_20250323_*.jsonl`).

**Training data for finetune:**
- `adaption_test_dataset_v1.csv` — **the finished 100-row Adaption set** (prompt/context/output, class-balanced 40/60, decade-anchored 1940s–2020s, speaker/target caps ≤3). Ready to feed a hosted finetune now.
- `output/full/complete_v2.jsonl` — full labeled corpus (~21,400 records): `(text,target) → (classification, victims, reasoning)`.
- The ~21k records can be **pseudo-labeled by r7b/rplus agreement** (disagreement removed) for high-confidence finetune labels.

**Lessons / divergences:** theory-heavy typology → simple binary classification (the central pivot); victim-vs-aggressor framing was tested then dropped; multi-model runs for robustness stuck; the modular resumable batch pipeline (`loader→batch_processor→processor→file_merger` + `tracking.json`) and XML-tagged structured output (`<CLASSIFICATION>`) were what worked.

**Other value:** accusation networks (vis.js HTML), USA–China accusation network, worldmap, top-tier IR analysis, power-law/concentration analysis — real research artifacts.

---

## 3. finetune_FEC_BLS — the actual finetune (and the decoder-map pattern)

**What it did:** classify free-text US campaign-contribution occupations → BLS SOC/O*NET labels using an **OpenAI GPT-3.5 finetune** (`ft:gpt-3.5-turbo-0613:personal::7qnGb8rm`).

**Timeline:** 8 commits, 2024-12-13 → 2025-01-17; untracked `debug/` work through 2025-07-24 (the final O*NET SOC mapping). `data/` and `.env` are gitignored.

**The decoder-map pattern (the key reusable idea):** the model is trained to emit a **normalized token** (`transformed_completion`, e.g. `salesrepresentativeswholesale... ###`) rather than the human label; a deterministic `decoder_map[token] → label` converts it back. Anything not in the map = **hallucination**, retried or flagged `insufficient_information_gpt`.
```json
{"prompt": "classify this profession:  Salesperson ->",
 "completion": "sales representatives, wholesale and manufacturing...",
 "transformed_completion": "salesrepresentativeswholesale... ###",
 "prompt_occupation": "Salesperson"}
```
- `finetune.jsonl` = **106,935 training records**; ~64,008 distinct occupation spellings → ~1,016 unique labels.
- Inference: temp 0.1, max_tokens 50, system prompt `"classify this entry:"`.
- Multi-stage decode fallback: standard decode → prompt_map lookup (free) → API retry → `insufficient_information_gpt`, with audit columns.

**Lessons that transfer directly to the finetune project:**
1. Closed-vocabulary output (decoder map) makes hallucination detection trivial and retry transparent.
2. Low temp (0.1) + short max_tokens (50) is the right regime for classification.
3. Process **unique values then map back** (64k unique → 6M+ rows) — huge cost saving.
4. **Write-batches-and-resume** for long runs.
5. Final **deterministic crosswalk to an external taxonomy** (categories → O*NET, 99.71% coverage).
6. ⚠️ Leftover "TESTING ONLY" batch limit in `batch_05.py` — a silent-scope bug to watch for.

---

## 4. EliteResearchAgent v1–v5 — the prosopography training-data mother lode

*(See `eliteresearchagent-cluster-report.md` for the full cross-version story. Summary below.)*

A prosopography tool for UN high-level panel elites, evolved through 5 divergent iterations:

| Iteration | Period | Focus | Key training assets |
|---|---|---|---|
| **v1** | Nov 2025–Feb 2026 | Service architecture; career + org-ontology services | **`careerfinder_granular_01/review/` = 75 persons, 2,714 chunk→extraction pairs, 10,469 events** (quotes+URLs+step3 flags); `EventAlign_02/03` 2-source corroboration; `biographical/birthyear/review/` 75 people; `org_ontology_02/ontology.json` schema |
| **v2** | Feb 12–13 2026 | Education + bio QA pipelines; university ontology | **5-stage education pipeline reports** (extraction+consolidation+verification); **`university_ontology.json` 144 canonical-variant records**; `Ontology_unified` UN/gov/university schema |
| **v3** | Feb 17–25 2026 | Org entity-resolution/matching | Merged ontologies (`smart_ontology.json`, `merged_ontology.json`, `final_ontology_v2.json`, `unified_ontology.json`); versioned `OrgExtraction_01..03.txt` prompts; per-person career JSONs |
| **v4** | Mar 31–Apr 17 2026 | Database/curation-centric | **Postgres schema**: `career_positions` 2,183, `position_tags` (8-dim), `person_attributes` (7 ideal types), `org_ontology_mappings` (168 equivalence classes); `verified_sources`/`supporting_quotes` grounded evidence |
| **v5** | May 26–Jun 2026 | Productized HITL research agent + Obsidian migration | **`panel_members.json` 40 UN AI Panel bios**; `biography.md` ×37 (YAML provenance + structured tables); `web/llm.py` tool-call schemas; 88 tests |

**The org-ontology thread** (the "weak link" that drove everything): v1 schema → v2 university ontology (144) → v3 matching/enrichment → v4 DB equivalence classes (168) → v5 lean. **This is the org-harmonization training data, and it's a textbook entity-normalization task that fits the FEC_BLS decoder-map pattern.**

**The verification thread** (anti-hallucination): v1 2-source rule → v2 weighted corroboration (org 40/degree 30/level 20/time 10) → v4 grounded evidence columns → v5 9-stage HITL. Exactly the "make sure the info is about the target person" capability to finetune for.

**Shared caveats:** most LLM outputs are unvalidated (weak supervision, not gold); heavy schema drift between iterations; **live Serper API key in v3 `.env` and hardcoded in `OntologyBuilder_v1/config.py` (REDACT before any GitHub publication)**; v5 has most real work **uncommitted** (back it up); v1 has a 267MB duplicated worktree.

---

## 5. Cross-repo synthesis — the training-data map for the finetune project

| Candidate finetune task | Best gold/source | Where | Format / size |
|---|---|---|---|
| **Education extraction** (Task 1) | UN_AI_PANEL `education_check.json` (79 people / 193 degrees / 842 sources, fact-checked) **PLUS** v2 education reports | UN_AI_PANEL; EliteResearchAgent_v2 | structured degrees + citations |
| **Professional/career extraction** (Task 2) | `careerfinder_granular_01/review/` | EliteResearchAgent v1 | 2,714 chunk→event pairs, 10,469 events |
| **Career label/classification** | `EventAlign_03` per-person labels/classifications | EliteResearchAgent v1 | 75 people |
| **Org harmonization** (Task 3) | `university_ontology.json` (144) + `org_ontology_mappings` (168) + raw pool `careerfinder_results.jsonl` | v2 + v4 + v1 | canonical→variant / equivalence classes |
| **Person-level typology** | `person_attributes` (7 ideal types) + `position_tags` (8 dims) | EliteResearchAgent v4 | structured labels |
| **Biographical QA** | `biographical/birthyear/review/` (75) + `panel_members.json` (40) | v1 + v5 | QA pairs / bios |
| **Aggressor/victim classification** (separate task) | `adaption_test_dataset_v1.csv` + `complete_v2.jsonl` | pydeal_type | 100-row Adaption + 21k full corpus |
| **Occupation→SOC classification** (proven template) | `finetune.jsonl` (106,935) | finetune_FEC_BLS | decoder-map format |

**Reusable patterns (not just data):**
- **Decoder-map / closed-vocabulary output** (FEC_BLS) → the output architecture to keep for org-harmonization and any classification task.
- **Multi-model agreement for confidence triage** (pydeal_type) → the method to filter low-confidence labels before finetuning, and to teach models to flag uncertainty.
- **Multi-source corroboration / 2-source rule** (EliteResearchAgent) → the verification target to finetune for.
- **Resumable batch processing + unique-value processing** (FEC_BLS, pydeal_type) → the `train`/`collect` stage engineering.
- **Balanced/covered dataset sampling** (pydeal_type `build_adaption_dataset.py`) → the `augment` stage template.
- **LLM-as-judge QC** (pydeal_type Command-A plan) → dataset validation.

---

## 6. Path-divergence narrative (the "why" across all repos)

- **pydeal_type:** theory-heavy typology → pragmatic binary classification. The multi-model insight arose organically (r7b everywhere, then r-plus as a second opinion), and stuck because the evaluation rewarded it.
- **finetune_FEC_BLS:** a clean, self-contained finetune project that solved one hard problem (hallucination in classification) via the decoder map. No divergence — just the mature pattern to imitate.
- **EliteResearchAgent v1→v5:** a long evolutionary arc where each iteration re-aimed at a different trust/structure problem — from broad architecture (v1) to education QA (v2) to org resolution (v3) to curated database (v4) to productized HITL agent (v5). The recurring tension: *"make extraction trustworthy"* (verification machinery) vs *"structure the organizations"* (ontology thread) — both exactly the finetune targets.

**Net insight for the finetune project:** You have already, across these repos, solved the three candidate tasks as prompt-pipelines and left behind rich training data. The finetune project is not starting from scratch — it's **compiling and miniaturizing proven workflows**, exactly your stated vision. The UN_AI_PANEL education gold set is the natural first target (prove end-to-end), and the decoder-map + multi-model-triage patterns give you the architecture to keep the small models trustworthy.

---

## 7. Consolidated file/path index

**pydeal_type:** `C:\Users\spatt\Desktop\pydeal_type`
- `runs/USA_01/prompt/aggressor_05/output/adaption_test_dataset_v1.csv`
- `runs/USA_01/prompt/aggressor_05/output/full/{complete_v2.jsonl, ungdc_commandr7b_*.jsonl}`
- `runs/USA_01/prompt/aggressor_05/output/parsed/ungdc_commandrplus_*.jsonl`
- `runs/USA_01/prompt/aggressor_05/output/full/merger7brplus.py`
- `runs/USA_01/prompt/victim_01/output/victim_01_results_{r7b,commandrplus}.jsonl`
- `evaluation/{evaluation_01,02.ipynb, df_r7b_1,2.jsonl, df_rplus.jsonl, final_df.jsonl}`
- `evaluation/sampling/evaluation_sample_20250323_*.jsonl`
- `analysis/20feb2025/` (networks), `analysis/26mar2025/worldmap.png`

**finetune_FEC_BLS:** `C:\Users\spatt\Desktop\finetune_FEC_BLS`
- `data/finetune.jsonl` (106,935), `data/finetune_old.jsonl`
- `data/2020_SOC_classification.csv`, `data/All_Occupations_ONET2024.csv`, `data/contribs_2022.db`
- `scripts/OccupationClassifier_batch_05.py`, `correction_01.py`, `scale_01.py`
- `streamlit/gpt_finetune_streamlit.py`
- `debug/{onet_mapping_coverage_report.txt, mapping_summary.txt, final_completion_to_onet_mapping.json}`

**EliteResearchAgent cluster:** see `eliteresearchagent-cluster-report.md` §7 for the full index.

---

*Synthesized from: `pydeal_type-report.md`, `finetune-FEC-BLS-report.md`, `eliteresearchagent-v1-report.md`, `eliteresearchagent-v2-v3-report.md`, `eliteresearchagent-v4-v5-report.md`, `eliteresearchagent-cluster-report.md`.*
