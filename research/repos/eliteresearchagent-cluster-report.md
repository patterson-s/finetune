# EliteResearchAgent Cluster — Cross-Repo Development Map (v1 → v5)

**Date:** 2026-08-12
**Scope:** Synthesizes the five per-repo reports for `EliteResearchAgent` (v1), `EliteResearchAgent_v2`, `_v3`, `_v4`, `_v5`. This is the story of one prosopography tooling effort evolving through five divergent iterations across ~6 months (Nov 2025 → Jun 2026), converging on a productized, human-in-the-loop research agent.

**Purpose for the finetune project:** map the full development trajectory, identify what each iteration contributed, and catalog the reusable training data left behind — so we can finetune small models to reproduce these proven extraction/verification/organization tasks.

---

## 1. The overall arc

All five repos serve one research goal: **build structured, source-grounded biographical and career profiles of the international elites who staff UN high-level panels** (High-Level Panel on Digital Cooperation / HLP on Digital Cooperation, the four UN High-Level Panels, and finally the UN AI Panel / High-Level Advisory Body on AI), then derive analytical typologies (career phases, ideal types, org ontologies) for social-science analysis.

The unifying design philosophy (from v1 `design/designprinciples.md`, restated across versions): **review-first** (extractions go to a `review/` folder for human inspection before any DB commit), **complete provenance** (every claim carries verbatim quotes + source URL + chunk id), **2-source rule** (claims confirmed by ≥2 independent sources before "verified"), and **prompts as versioned `.txt` files**. This philosophy is exactly the "anti-hallucination / is-this-about-the-right-person" concern you want the finetune models to internalize.

**Timeline at a glance:**

| Iteration | Dates | Commits | Core focus | Deliverable |
|---|---|---|---|---|
| v1 | 2025-11-25 → 2026-02-04 | 43 | Service architecture; career-event + org-ontology services | `Prosopography_01` Streamlit web app |
| v2 | 2026-02-12 → 02-13 | 7 | Education + biographical QA pipelines; university ontology | 5-stage education pipeline + per-person reports |
| v3 | 2026-02-17 → 02-25 | 14 | Org entity-resolution / matching; career-event + integrated analysis | `ontology_01` matcher/enrichment + `WikiPrompt`/`WikiAugment` |
| v4 | 2026-03-31 → 04-17 | 22 | Database/curation-centric; org ontology annotation + location enrichment | Postgres `prosopography` schema + read-only FastAPI explorer + PDFs |
| v5 | 2026-05-26 (+ uncommitted work through Jun) | 1 (snapshot) | App/pipeline-centric; human-in-the-loop research agent + Obsidian migration | React SPA 9-stage research agent + `prosopography_v5` |

---

## 2. Iteration-by-iteration development map

### v1 (Nov 2025 – Feb 2026) — the architecture that defined the problem
- **Subject cohort:** 76 members of the UN High-Level Panel on Digital Cooperation (`names/person_names.json`).
- **Built:** the full service map from `prosopography.md` — Service 1 collection (`search/`, Serper→fetch→Mistral OCR→chunk→Cohere embed→Postgres), Service 2 biographical (`biographical/birthyear/`, 75 people), Service 4a career detection (3 generations: `careerfinder_base_01` "max recall" → `careerfinder_granular_01` 3-step extract/assemble/verify → `Prosopography_01` consolidated app), Service 4b org ontology (`org_ontology_01`/`_02`, the **declared weak link**), Service 5a/5b ongoing detection (`RetroPropogation_01/02/03`, `EventAlign_01..04`).
- **Key data assets left behind (the biggest in the whole cluster):**
  - `services/careerfinder_granular_01/review/` — **75 persons, 2,714 chunk→extraction JSON pairs, 10,469 events**, each with verbatim quotes, source URL, event_type (career/award), confidence, and step3 verification flags. The single largest structured training corpus.
  - `EventAlign_02/03` — multi-source corroboration labels (source_event_count/source_chunks), the operationalized "2-source rule" signal, across 75 people.
  - `biographical/birthyear/review/` — 75 per-person biographical extractions.
  - `org_ontology_02/ontology.json` — the org-normalization schema (raw org → canonical_name/org_type/country/posting-geo), but **only 2 seeded entries** (the gap that became v2/v3/v4's obsession).
- **Path divergences:** `main` (full app) vs `focused-hertz` (a stale snapshot behind main, nothing worth salvaging) vs `claude/infallible-lehmann` (a Claude Code worktree pointer = the same commit as main). ~267MB / 6,700 files of the 671MB footprint is a duplicated worktree in `RetroPropogation_03/`.

### v2 (Feb 12–13 2026) — a two-day education/bio push
- **Built:** a clean 5-stage education pipeline (`services/education/`: retrieval→extraction→consolidation→verification→provenance→per-person JSON reports) with a rule-based consolidation fallback and an early-stop. Sibling `biographical/` service. Cluster of ontology services: `Ontology_Initial_University` (LLM tag → human review), `OntologyBuilder_v1` (Serper+Cohere enrichment → **144-entry `university_ontology.json`** with canonical tag/official title/ISO country/city/variants), `Ontology_unified` (merges UN/gov/university), `OntologyCareer_v1`.
- **Ended** on "struggling with interface and edge cases" — the Streamlit human-review UI was the friction.
- **Training assets:** per-person education reports (extraction + consolidation reasoning + verification status), 144 university canonical-variant records, verified tag triples.

### v3 (Feb 17–25 2026) — org entity-resolution, config-driven
- **Built:** the org-matching subsystem (`services/ontology_01/`: matcher, fuzzy_match, llm_match, smart/targeted/comprehensive merge, review_app, `batch_enrich_full.py`), `WikiPrompt`/`WikiAugment` (Wikipedia career-timeline extraction + fact-checking), `FactChecking_01`, `integrated_01`/`targeted_01` (RAG for narrow questions + wiki for full career paths), heavy `analysis/` (typology, ideal_types, locations, orgs, career_tags).
- **Notable pivot:** dropped v2's education *pipeline code* but **kept the education *data*** via copy scripts into per-person `career_events/` dirs. Documented reason: v2's RAG approach had a **recentness bias** at full career-path reconstruction (`integrated_01.md`).
- **Training assets:** multiple rounds of merge outputs (`smart_ontology.json`, `merged_ontology.json`, `final_ontology_v2.json`, `unified_ontology.json`), the versioned `OrgExtraction_01/02/03.txt` prompt trajectory, per-person career JSONs.

### v4 (Mar 31 – Apr 17 2026) — database/curation-centric
- **Built:** a full PostgreSQL `prosopography` schema for **75 members of four UN High-Level Panels** — star schema (persons → career_positions **2,183** / education **219** / awards **715** / nationalities **79** / provenance **301**), analytical derivatives `position_tags` (8-dim taxonomy incl. career_phase, organization_type, un_placement), `person_attributes` (7 ideal types), `org_ontology_mappings` (equivalence classes: mfa/executive/io_non_un/un_agencies), 23 idempotent migrations, Serper+Cohere location enrichment, geocoding, static PDFs (75 person + org digest), read-only FastAPI explorer + ontology annotation editor, deployed to Render. `backup.dump` (22MB Postgres dump, gitignored).
- **Training assets:** the 8-dim + 7 ideal-type taxonomies with full value vocabularies (see `DATABASE.md`); `career_positions.verified_sources`/`supporting_quotes` grounded-evidence pairs; `biographical_provenance` full LLM pipeline traces. **Caveat: all derivatives are `evaluation_status='draft'` with coverage gaps** (career_typology missing for 20/75, career_phase 'unknown' for 31.8%).

### v5 (May 26 2026 + uncommitted work through Jun) — productization
- **Built:** a **9-stage human-in-the-loop research agent** for a new subject set — **40 UN AI Panel (High-Level Advisory Body on AI) members** in `panel_members.json` (Maria Ressa, Yoshua Bengio, Hoda Heidari, Adji Boussi Dieng, Awa Bousso Dramé...). React+Vite SPA, SSE streaming, Cohere tool-use (`command-a-03-2025`) with Pydantic schemas, per-session JSONB resume (`research_sessions.stage_data`), HITL toggles per stage, transactional save. **88 passing tests** (73 pytest + 15 Vitest). Plus `obsidian_migrate_folder/` — a tiered fetcher (httpx→Playwright→PDF→Mistral OCR) + `build_biographies.py` producing `biography.md` per person with YAML provenance + Obsidian `[[backlinks]]` + structured tables; **37 of 40** built.
- **Repo-state caveat:** only ONE commit (`856e09c`, capturing an older 8-stage/Anthropic form). Everything that makes v5 what it is — the 9-stage/Cohere rework, panel picker, tests, Obsidian migration, `panel_members.json` — is **uncommitted** in the working tree. **Back up v5's working tree before touching it.**

---

## 3. The organization-ontology thread (the "weak link" that drove everything)

The single most consistent thread across v1→v5 is the **organization ontology** (Service 4b, rated "HIGH priority, weak link" in v1's `prosopography.md`):

- **v1** defined the schema and builder UI but left only 2 seeded entries (`org_ontology_02/ontology.json`).
- **v2** built the **university** ontology to 144 canonical-variant records + a unified UN/gov/university schema.
- **v3** built the org **matching/enrichment** machinery (fuzzy + LLM + merge + human review) with versioned prompts.
- **v4** operationalized it in the DB as `org_ontology_mappings` (168 equivalence-class mappings, `mfa`/`executive`/`io_non_un`/`un_agencies` categories) with a full annotation editor.
- **v5** dropped the deep ontology columns (hierarchy_path, equivalence_class) from its `organizations` table to stay lean — the ontology knowledge lives on in v4.

**Finetune implication:** this is a textbook **entity-normalization / canonicalization** task (raw org mention → canonical name + type + country, with equivalence classes and hierarchy). It fits the FEC_BLS decoder-map pattern perfectly: constrain output to a finite canonical-name space to prevent hallucination. The raw-org→canonical mapping data lives across v2 (`university_ontology.json`, 144), v3 (merged ontologies), and v4 (`org_ontology_mappings`, 168), and the pool of raw org strings to map is in `org_ontology_01/data/careerfinder_results.jsonl` (2.5MB).

---

## 4. Confidence-triage and verification machinery (the anti-hallucination theme)

Every iteration built a version of verification/corroboration — this is the deepest shared asset, and it aligns exactly with the finetune goal of "make sure the info is actually about the target person":

- **2-source rule** (v1) → operationalized as `source_event_count`/`source_chunks` in `EventAlign_02/03` (v1).
- **Multi-model runs** on the same data: v1 `RetroPropogation_01/outputs/` has cohere_01 (66 people) + anthropic_claude_01 (2 people); the Gro Harlem Brundtland package has the full entity→canonical-org→event→verification chain under two models.
- **Step-based verification** (`careerfinder_granular_01` step3): temporal coherence + quote support, with `valid`/`warning`/`error` flags (v1).
- **Weighted similarity corroboration** in v2 `verification.py` (org 40% / degree 30% / level 20% / time 10%), statuses `verified`/`partial`/`unverified`.
- **Grounded evidence columns** in v4: `verified_sources` + `supporting_quotes` per career_position; `biographical_provenance` storing full retrieval/extraction/verification/substantiation traces.
- **v5** human-in-the-loop gates at all 9 stages + quote-span highlighting.

**Finetune implication:** the verified/flagged/negative examples accumulated across these systems are exactly what a confidence-triage finetune model needs. The `warning`/`error`/`partial`/`unverified`/`none` labels are weak-supervision signals; the 2-source corroboration is a target we can teach a small model to predict or reproduce.

---

## 5. Consolidated training-data inventory (best assets per task)

For the finetune project's candidate tasks:

| Candidate finetune task | Best source | Size / format |
|---|---|---|
| **Education extraction** (Task 1) | v2 `services/education/reports/*_education_history_*.json` + v2 `OntologyBuilder_v1/final_education/*_education_events.json`; ALSO the UN_AI_PANEL `education_check.json` (79 people / 193 degrees / 842 sources) built separately | per-person JSON reports, structured |
| **Professional / career extraction** (Task 2) | v1 `careerfinder_granular_01/review/` — **2,714 chunk→extraction pairs, 10,469 events** with quotes+URLs+step3 flags | instruction-style chunk→event-JSON |
| **Career label/classification** | v1 `EventAlign_03` per-person `01a/01b` labels + `02a/02b` classifications | 75 people |
| **Org harmonization** (Task 3) | v2 `university_ontology.json` (144 canonical-variant) + v3 merged ontologies + v4 `org_ontology_mappings` (168) + raw pool `careerfinder_results.jsonl` | canonical→variant pairs, equivalence classes |
| **Person-level typology** | v4 `person_attributes` (7 ideal types, 414 rows) + `position_tags` (8 dims) | structured labels (draft status) |
| **Biographical QA** | v1 `biographical/birthyear/review/` (75 people) + v5 `panel_members.json` (40 curated bios) | QA pairs / instructional bios |
| **Schema-faithful generation** | v5 `web/llm.py` tool schemas + `web/models.py` Pydantic + stage routers | Cohere tool-use examples |

**Shared caveats across the cluster:**
- Almost all LLM outputs are **unvalidated** (except the small human-eval sets and v4's provenance traces); treat as weak supervision, not gold.
- **Schema drift between iterations**: base_01 uses `raw_extractions`, granular uses step-based, v4 uses SQL tables, v5 uses tool-call schemas. Pick one per task; normalize on intake.
- **Secrets**: a live Serper API key is in v3's `.env` and hardcoded in `OntologyBuilder_v1/config.py`. **Redact before any data sharing / GitHub publication.**
- **Repo hygiene**: v1 has a 267MB duplicated worktree; v5 has most real work uncommitted. **Back up v5's working tree.**

---

## 6. Path-divergence summary (the "why it split" story)

1. **v1 → v2:** from *broad service architecture* to a *focused education/bio QA pipeline* + university ontology. The pivot: education (v1 Service 3) was "not confident," so he built a dedicated corroborated RAG pipeline for it.
2. **v2 → v3:** from *education QA* to *org entity-resolution + career-event reconstruction*. Reason recorded: RAG had a **recentness bias** for full career paths (`integrated_01.md`). Education *data* carried forward, education *code* dropped.
3. **v3 → v4:** from *scripted services* to a *rigorous relational database* with provenance-tracked derivatives + annotation UI. The deliverable became the curated corpus + schema, not the pipeline.
4. **v4 → v5:** from *database/curation-centric* to *application/pipeline-centric* — a reusable human-in-the-loop research agent that *writes* the schema on demand, for a new subject set (UN AI Panel), with a real test suite and Obsidian output. The nearest thing to a finished product.

**Net: the development split along a recurring tension** — "how do I make the extraction trustworthy?" drove the verification machinery (v1 2-source rule → v2 corroboration → v4 grounded evidence → v5 HITL), while "how do I structure the organizations?" drove the ontology thread (v1 schema → v2 university → v3 matching → v4 DB ontology → v5 lean). Both are exactly the tasks we want to finetune small models to perform cheaply and durably.

---

## 7. File/Path index (cluster)

- v1: `C:\Users\spatt\Desktop\EliteResearchAgent` — `prosopography.md`, `design/designprinciples.md`, `names/person_names.json`, `services/careerfinder_granular_01/review/`, `services/EventAlign_02/03`, `services/org_ontology_02/ontology.json`, `services/org_ontology_01/data/careerfinder_results.jsonl`, `biographical/birthyear/review/`, `services/Prosopography_01/`.
- v2: `C:\Users\spatt\Desktop\EliteResearchAgent_v2` — `services/education/reports/`, `services/OntologyBuilder_v1/data/university_ontology.json`, `services/Ontology_unified/unified_ontology.json`, `UNIVERSITY_ONTOLOGY_WORKFLOW.md`.
- v3: `C:\Users\spatt\Desktop\EliteResearchAgent_v3` — `config/prompts/OrgExtraction_01..03.txt`, `services/ontology_01/*_ontology.json`, `services/WikiPrompt/`, `services/FactChecking_01/`, `integrated_01.md`.
- v4: `C:\Users\spatt\Desktop\EliteResearchAgent_v4` — `DATABASE.md`, `db/migrate_01..23`, `web/routers/`, `static/person_pdfs/`, `backup.dump` (gitignored).
- v5: `C:\Users\spatt\Desktop\EliteResearchAgent_v5` — `panel_members.json`, `web/routers/stage1_search..stage9_save.py`, `web/llm.py`, `frontend/src/`, `tests/`, `obsidian_migrate_folder/`.

---

*Synthesis of per-repo reports: `eliteresearchagent-v1-report.md`, `eliteresearchagent-v2-v3-report.md`, `eliteresearchagent-v4-v5-report.md` (all in this folder).*
