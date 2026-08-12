# EliteResearchAgent v4 & v5 — Development Map

Report of two related repos: Scott's prosopography tooling iterations for UN governance panels, feeding the Finetune training-data project.

- **v4**: `C:\Users\spatt\Desktop\EliteResearchAgent_v4` — git `main`, 22 commits, **2026-03-31 → 04-17** (database + analysis centric).
- **v5**: `C:\Users\spatt\Desktop\EliteResearchAgent_v5` — git `main`, **1 commit** (`856e09c`, "initial", **2026-05-26**) + a large **uncommitted working tree** (9-stage pipeline rework, Obsidian migration, tests all uncommitted).

---

## Overview

Both repos are iterations of a **prosopography research tool** — software that builds structured biographical/career profiles of the elites who staff UN high-level panels, then derives analytical typologies for research. They share the same DNA (PostgreSQL + FastAPI + Cohere + Serper, the `career_positions`/`position_tags`/`person_attributes`/`derivative_runs` table family) but took sharply different directions:

| | v4 (Mar–Apr 2026) | v5 (May 2026+) |
|---|---|---|
| Core mode | **Database-centric** curation + read-only explorer | **App/frontend-centric** interactive research agent |
| Corpus | Fixed: **75 members** of four UN High-Level Panels (2004/2007/2012/2020) | On-demand: **40 UN AI Panel members** (`panel_members.json`) |
| DB schema | `prosopography` | `prosopography_v5` (fresh) |
| Writes | Manual ontology annotation via editor | Full **9-stage human-in-the-loop pipeline** writes profiles |
| UI | Vanilla-JS single page + ontology editor | **React + Vite SPA**, SSE streaming, HITL toggles |
| Tests | None | **pytest (73) + Vitest (15) = 88 tests** |
| Extra output | Static PDFs (75 person + 1 org) | **Obsidian vault migration** (file-based notes) |

v4 built and enriched the data model; v5 productized the same model into a usable end-to-end research workflow for a new subject set.

---

## v4 Timeline & Focus

Read from `CLAUDE.md`, `DATABASE.md`, `instructions.md`, `instructions_31mar2026.md`, `improvements.md`, `pickup.md` (all at repo root).

**Commit timeline** (git log, newest first; focus inferred from messages):
- **03-31** `initial` — base scaffolding.
- **04-01** `new derivatives`, `added non-UN IO derivatives`, `graph resolve` — began LLM-derived analytical tables.
- **04-02** `add schema review` — reviewed the schema (see `pickup.md`).
- **04-08** `update`, `render deploy`, `render`, `fix tags router`, `add auth diagnostic`, `auth` — added Basic Auth, deployed to **Render** (`render.yaml`, `DATABASE_URL` support).
- **04-17** `added pdf support and location information`, `add location map`, `update location`, `update python compatibility`, `fix location views for Render`, `update for render`, `run migrate_23 DDL at startup; support DATABASE_URL in db_utils`, `debug`, `add location_region to startup migration` — location enrichment, map, PDF generation, Render fixes. Final commit.

**Focus, per the docs:**
- `instructions.md` — brief for enriching **organization location** data (city/country/region) via **Serper search + Cohere LLM**, keeping sources, validating across >1 source.
- `instructions_31mar2026.md` — brief for building an **organizational ontology** (start with national governments / Ministries of Foreign Affairs), as a **derivative** (new mapping, don't overwrite base data), with an annotation UI, autocomplete, and progress counter.
- `improvements.md` — surface the new org-ontology labels in the UI on org hover.
- `pickup.md` (2026-04-02) — "Ontology Editor v2 + UN Agencies Run" session summary: rebuilt the annotation editor to support class-first browsing + retroactive rework; documented the UN-agencies hierarchy and rework workflow.
- `DATABASE.md` — the full schema reference/handoff doc.

**v4 is database-heavy by design**: 23 sequential migrations under `db/`, a 22 MB `backup.dump`, org-location/geocode/PDF helper scripts, Render deployment, and a read-only explorer over the curated corpus.

---

## v4 Database Architecture

PostgreSQL database **`eliteresearch`**, schema **`prosopography`** (always fully-qualified: `prosopography.persons`). Connection via `.env` (`DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`) or `DATABASE_URL` on Render. Docs: `DATABASE.md` (full schema + row counts + SQL), `CLAUDE.md` (architecture).

**Star schema** — `persons` (75 rows) at the center radiating to:
- **Core tables**: `career_positions` (~2,183 rows, one per job; 93.8% matched to `org_id`), `education` (219), `awards` (715), `person_nationalities` (79), `biographical_provenance` (301 — audit trail of the v3 extraction pipeline's birth/death/nationality fields, storing `retrieval_json`/`extractions_json`/`verification_json`/`substantiation_json` JSONB traces).
- **Organizations**: `organizations` (2,619 per DATABASE.md / 2,805 per later CLAUDE.md; 1,010 are auto-created `pending_review` stubs), `organization_aliases` (209). Columns added over time: `location_city/country/region/lat/lng`, `un_canonical_tag`, `un_hierarchical_tags`, `gov_canonical_tag`, `gov_hierarchical_tags`, `review_status`.

**Analytical derivatives** — all provenance-tracked via `derivative_runs` (header table; every derivative row links a `run_id`):
- `position_tags` (2,181) — 8 dimensions per career position: `domain` (TEXT[]), `organization_type`, `un_placement`, `geographic_scope`, `role_type`, `function`, `career_phase` (formative/consolidation/apex/post_apex/unknown), `policy_bridge` (bool).
- `person_attributes` (414) — person-level: `career_domain`, `career_typology` (7 ideal types: DOMESTIC_POLITICAL_ELDER, NATIONAL_TO_GLOBAL_PIVOT, DEVELOPMENT_CIRCUIT_RIDER, CAREER_FOREIGN_SERVICE, DOMAIN_KNOWLEDGE_AUTHORITY, CIVIL_SOCIETY_PLATFORM_BUILDER, CORPORATE_TO_GOVERNANCE_CROSSOVER), `mobility_pattern`, `geo_edu_category`, `institution_prestige`.
- `org_ontology_mappings` (168) — equivalence classes (`equivalence_class`, `country_code`, `hierarchy_path` TEXT[], `thematic_tags`), categories: `mfa`, `executive`, `io_non_un`, plus a `un_agencies` run (pickup.md).
- `ontology_user_classes` (36), `org_location_searches` (Serper+Cohere enrichment results, added in migrate_22).
- **User-applied**: `user_functional_tags`, `functional_tag_vocab`, `person_notes` (migrate_20/21).

**Migration series** (`db/migrate_01..23`, idempotent): 01–05 base schema + persons + careers + provenance + validation; 06–08 org schema + org load + position→org matching; 09–11 derivatives schema + tags + attributes; 12–19 org ontology (MFA/executive/IO hierarchy, parent orgs, review status); 20–21 user tags/notes; 22–23 org location enrichment + lat/lng. Standalone (non-sequential) helpers: `resolve_parent_orgs.py`, `derive_functional_summary.py`, `enrich_org_locations.py` (Serper+Cohere), `geocode_org_locations.py` (Nominatim, rate-limited, resumable), `generate_person_pdfs.py`, `generate_org_pdf.py`.

**What `backup.dump` is**: a **PostgreSQL custom-format dump** (header "PostgreSQL custom database dump - v1.16-0", ~22,722,859 bytes ≈ 22 MB, dated Apr 8 12:04). It is gitignored (`backup.dump` and `.env` both in `.gitignore`) — a local DB snapshot of the `eliteresearch` database, not part of any commit. A point-in-time backup of the curated corpus + derivatives.

**Data flow**: v3 pipeline outputs (per-person source corpus) → migrations load base data with provenance → LLM derivative runs (Cohere) tag positions/attributes → org ontology + location enrichment add structure → served read-only by the FastAPI explorer. Two DB patterns: web layer `web/db.py::get_conn()` (connection per request, `row_to_dict()`), script layer `db/db_utils.py::get_connection()` (raw psycopg2, `RealDictCursor`).

**Web layer** (`web/`): FastAPI `app.py` (6 routers + BasicAuthMiddleware), routers `hlp`, `persons`, `organizations`, `search`, `ontology` (11 endpoints, most complex), `tags`, `locations` (career-presence scores + Leaflet map). Static SPA `web/static/index.html` + `ontology-editor.html` (v2) + `ontology-editor-v1.html` (legacy fallback). Deploys to Render (`render.yaml`).

---

## v5 Focus

Read from `CLAUDE.md`, `nexttime.md`, `testing_plan.md`, `testing_progress.md`, `panel_members.json`, `db/`, `frontend/`, `obsidian_migrate_folder/`.

**Product**: a **user-supervised research agent** — enter a person's name, and a **9-stage pipeline** builds a structured prosopographical profile, pausing for **human review at every stage**.

**The 9 stages** (`web/routers/`, one router per stage):
1. `stage1_search.py` — Serper search + Cohere disambiguation (sync).
2. `stage2_sources.py` — user selects source URLs (optional supplemental search).
3. `stage3_preview.py` — fetch primary URL + summarize.
4. `stage4_bio.py` — extract birth year, nationality, death status, education with verbatim quotes (multi-source fallthrough).
5. `stage5_extract.py` — **SSE streaming** career-event extraction from primary source.
6. `stage6_gaps.py` — fetch secondary sources, find missing career events.
7. `stage7_tags.py` — **SSE streaming** tagging on 8 analytic dimensions (reuses v4's taxonomy).
8. `stage8_synthesis.py` — **SSE streaming** synthesis of 6 person-level attributes.
9. `stage9_save.py` — **transactional** write to PostgreSQL.

**Key architecture** (`CLAUDE.md`): session state lives in a single `research_sessions.stage_data` JSONB column → fully resumable. All LLM calls are **Cohere tool-use** (`command-a-03-2025`, overridable), no free-text parsing. Long stages use SSE (`sse-starlette`), frontend consumes via `useSSE` hook. **HITL toggle** per stage (localStorage). Stage 9 saves `persons`/`career_positions`/`position_tags`/`person_attributes`/`derivative_runs` in one transaction.

**Frontend** (`frontend/`, React + Vite + TypeScript): `src/api/client.ts` + `api/types.ts` (typed), `src/components/stage{1..9}/`, `src/components/home/PanelPicker.tsx` (panel registry + resume UX), `src/components/layout/{HITLPanel,StageNav}.tsx`, `src/hooks/{useSSE,useHITL}.ts`, `src/utils/quoteHighlight.ts` (exact + fuzzy quote-span matching). `SOURCES_ONLY_MODE` (in `App.tsx`) restricts Stage-2 approval to bulk-gather sources before full-pipeline work.

**Panel-driven sourcing**: `panel_members.json` (repo root) — **40 UN AI Panel members**, each `{ "name", "country", "bio" }` (e.g., Maria Ressa, Yoshua Bengio, Hoda Heidari, Adji Boussi Dieng, Awa Bousso Dramé). Served read-only via `GET /api/panel-members` (plain function in `web/app.py`). This is the UN SG's High-Level Advisory Body on Artificial Intelligence — a different, larger subject set than v4's four HLP panels.

**DB** (`db/migrate_01_schema.py`, `migrate_02_stage_renum.py`): fresh schema **`prosopography_v5`** with `research_sessions` (JSONB `stage_data`, GIN index, `current_stage` 1–9), `persons`, `organizations`, `career_positions` (adds `session_id`, `event_source`, `source_url`, `sort_order`), `derivative_runs`, `position_tags`, `person_attributes`. Nearly identical derivative tables to v4 but **session-driven**.

**Testing** (`tests/`, `pytest.ini`, `requirements-dev.txt`, `frontend/vitest.config.ts`): **88 tests passing** — `test_health` (4), `test_sessions` (11), `test_stage1` (11), `test_stage2` (9), `test_stage8` (13, transactional DB save + rollback), `test_fetcher` (20), `quoteHighlight.test.ts` (15 TS). Tests use the **real PostgreSQL DB** (reads `.env`) but mock Cohere/Serper; test data tagged `__TEST__` and cleaned up. `testing_plan.md`/`testing_progress.md` are **stale planning notes** (describe an "8-stage/Anthropic" pipeline) per CLAUDE.md's own "Known Inconsistencies" — the code is now 9-stage/Cohere.

**Obsidian vault migration** (`obsidian_migrate_folder/`): an **independent batch pipeline** (no imports from `web/`) exporting gathered sources from `prosopography_v5` into a note-taking vault at `C:\Users\spatt\Desktop\UN_AI_PANEL\`. `report_26june2026.md` documents the migration: 46 unique people, 627 stub files, ~88% fetch success. Scripts:
- `robust_fetch.py` — tiered fetcher: Tier 1 httpx (~88% success), Tier 2 Playwright headless Chromium (JS pages/bot-blocked), Tier 3 Playwright→PDF→**Mistral OCR** (last resort). Skip list for LinkedIn/Facebook/Instagram; YouTube via `youtube-transcript-api`.
- `fetch_contents.py` — batch runner (reads stub `.md`, fetches URLs, writes content; resumable, `MAX_FILES`/`SKIP_EXISTING`/`USE_OCR` config).
- `check_progress.py` — live progress check.
- `build_biographies.py` — batch **biography builder**: priority-sorts sources (Wikipedia/CV first), filters PDF binary/auth walls, adaptive 80k→50k→30k char fallback, writes `biography.md` per person with YAML provenance frontmatter + Obsidian `[[backlinks]]` + structured tables (demographics/education/career/awards/expertise). `nexttime.md` (2026-05-26) reports **37 of 40** panel members have usable `biography.md`.

**Run**: backend on 8001 (`serve.bat` / uvicorn), frontend Vite dev on 5173 (proxies `/api`), prod build outputs to `web/static/`.

---

## Path Divergences (v4 vs v5)

**What direction did each take?**

- **v4 → database/curation centric.** The deliverable is a rich, provenance-tracked PostgreSQL schema + read-only web explorer over a **fixed curated corpus** (75 HLP members). Deep org-ontology annotation (equivalence classes, org splitting, hierarchy paths), location enrichment, static PDF generation. Human effort goes into **manual annotation** through the ontology editor; the DB is the artifact.

- **v5 → application/pipeline centric.** The deliverable is an **interactive research agent**: search → source selection → extraction → tagging → synthesis → save, all human-reviewed. The DB schema is secondary (a near-copy of v4's derivatives) and is *written to* by the pipeline rather than hand-curated. Added a full **React SPA** with SSE streaming and HITL controls, and a **pytest/vitest suite** (absent in v4). New subject set (UN AI Panel, 40 members) is treated as an on-demand registry (`panel_members.json`), not a pre-ingested corpus.

**What got carried over vs. abandoned:**
- **Carried**: `career_positions`/`position_tags` (same 8-dim taxonomy)/`person_attributes`/`derivative_runs` table family; Cohere + Serper; FastAPI + BasicAuth; the UN-org tagging vocabulary (`un_placement`, `organization_type`).
- **Abandoned / not carried into v5**: the deep **org-ontology annotation UI** (equivalence classes, split-org, hierarchy_path) — v5's `organizations` table drops all ontology columns (`un_hierarchical_tags`, `hierarchy_path`, `review_status`, `equivalence_class`); **static PDF generation**; the read-only curated-corpus explorer model; the 4-HLP fixed dataset.
- **New in v5**: LLM-driven **search + disambiguation** (Serper/Cohere) as stage 1; per-session **JSONB resume**; SSE streaming; HITL; Obsidian file-based output alongside Postgres; a test suite.

**Notable repo-state divergence:** v4 is fully committed (22 commits, clean-ish tree). v5 is essentially **one snapshot commit** (`856e09c`, 2026-05-26, "initial") — it captures the *older 8-stage/Anthropic* form. Everything that makes v5 what it is — the 9-stage/Cohere rework (routers renamed `stage4_extract→stage4_bio`, `stage5_gaps→stage6_gaps`, etc.), the `home/` panel picker, `migrate_02`, the entire `obsidian_migrate_folder/`, `tests/`, `panel_members.json`, `nexttime.md`, `report_26june2026.md` — lives **uncommitted** in the working tree (confirmed via `git status`, which also shows the old stage4–8 router files deleted). The Obsidian migration itself (dated June 2026) post-dates the only commit by a month.

---

## Training-Data Potential for Finetune

Verified, high-value material for building fine-tuning corpora:

1. **Structured analytical taxonomy (v4)** — a ready-made labeling scheme with full value vocabularies:
   - `position_tags` 8 dimensions incl. `career_phase` (formative/consolidation/apex/post_apex/unknown), `organization_type`, `un_placement`, `function`, `policy_bridge` — see `DATABASE.md` for all values.
   - 7 **career-typology ideal types** (`DOMESTIC_POLITICAL_ELDER` … `CORPORATE_TO_GOVERNANCE_CROSSOVER`) with definitions referenced in `DATABASE.md` (from `eliteresearchagent_v3/analysis/ideal_types/outputs/ideal_type_definitions.json`).
   - Org-ontology equivalence classes (`mfa`, `executive`, `io_non_un`, `un_agencies`) + `hierarchy_path` examples.

2. **Grounded evidence pairs** — `career_positions.verified_sources` and `supporting_quotes` JSONB columns tie every derived fact to source URLs + extracted text quotes; `biographical_provenance` stores full LLM pipeline traces (`retrieval_json`/`extractions_json`/`verification_json`/`substantiation_json`). Excellent for extraction/verification fine-tuning (fact → evidence).

3. **Cohere tool-call / schema-constrained generation (v5)** — `web/llm.py` (all tool schemas + streaming generators), `web/models.py` (Pydantic response models), `web/routers/stage*.py` — real examples of structured-output prompting with tool-use, per stage. Good for teaching schema-faithful generation.

4. **Instructional bios (v5)** — `panel_members.json` has 40 `{name, country, bio}` entries (curated one-paragraph bios) — natural instructional pairs for bio-generation.

5. **Biography builder output (v5)** — `build_biographies.py` produces `biography.md` with YAML provenance + Obsidian `[[backlinks]]` + structured tables; `nexttime.md` confirms 37 built. Realistic document-structuring exemplars from raw source corpora.

6. **Frontend matching algorithm (v5)** — `frontend/src/utils/quoteHighlight.ts` + its 15 Vitest tests demonstrate exact + fuzzy quote-span matching (≥80% threshold) — useful for span-localization tasks.

**Caveats**: all v4 derivative runs are `evaluation_status = 'draft'` (not systematically validated); coverage gaps (career_typology missing for 20/75, geo/prestige missing for 7, career_phase 'unknown' for 31.8% of positions). The LLM outputs were produced by Cohere (`command-a`/`command-a-plus`) and v3/Anthropic pipelines, so models differ across the corpus.

---

## Other-Useful Material

- **Deployment patterns**: `render.yaml` + `DATABASE_URL` support + Render-specific fixes (v4 04-17 commits, `web/app.py`, `db/db_utils.py`) — shows Postgres-on-Render migration at startup.
- **Auth**: HTTP Basic Auth via ASGI `BasicAuthMiddleware` (`SITE_USERNAME`/`SITE_PASSWORD`, empty password = disabled) — in both repos.
- **Two DB connection patterns** documented in `CLAUDE.md` (web `get_conn()` vs script `get_connection()`).
- **Resume/idempotency patterns**: migrations are idempotent; geocoder/enrichment scripts resume automatically; `fetch_contents.py` skips populated files; `build_biographies.py` smart re-runs via frontmatter diff.
- **Tiered web fetching**: `obsidian_migrate_folder/robust_fetch.py` — httpx→Playwright→PDF→Mistral-OCR escalation, with skip lists and a documented import gotcha (`mistralai.client.Mistral`, not `mistralai.Mistral`).
- **v4 static PDFs** (`static/person_pdfs/`, `static/org_pdfs/`) — generated artifact corpus of 75 member profiles + one org digest, useful as reference/benchmark documents.
- **`backup.dump`** (22 MB Postgres custom dump, v4) — a full DB snapshot usable to rebuild the schema+data offline.
- **Handoff docs**: `DATABASE.md` (SQL queries), `pickup.md` (session handoff), `nexttime.md`, `report_26june2026.md` — good style references for research-note generation.

---

## File/Path Index

**v4 root `C:\Users\spatt\Desktop\EliteResearchAgent_v4\`:**
- `CLAUDE.md`, `DATABASE.md`, `instructions.md`, `instructions_31mar2026.md`, `improvements.md`, `pickup.md`, `usage.md`, `webdesign.md`
- `backup.dump` (22 MB Postgres dump, gitignored), `.env` (gitignored), `requirements.txt`, `render.yaml`, `serve.bat`, `.gitignore` (`.env`, `backup.dump`)
- `db/` — `db_utils.py`, `migrate_01_create_schema.py` … `migrate_23_add_org_latlng.py` (23 migrations), `resolve_parent_orgs.py`, `derive_functional_summary.py`, `enrich_org_locations.py`, `geocode_org_locations.py`, `generate_person_pdfs.py`, `generate_org_pdf.py`
- `web/` — `app.py`, `db.py`, `models.py`; `web/routers/` `hlp.py`, `persons.py`, `organizations.py`, `search.py`, `ontology.py`, `tags.py`, `locations.py`; `web/static/` `index.html`, `ontology-editor.html`, `ontology-editor-v1.html`
- `static/person_pdfs/` (001_..075_*.pdf), `static/org_pdfs/organizations.pdf`

**v5 root `C:\Users\spatt\Desktop\EliteResearchAgent_v5\`:**
- `CLAUDE.md`, `nexttime.md`, `testing_plan.md`, `testing_progress.md`, `panel_members.json` (40 members), `pytest.ini`, `requirements.txt`, `requirements-dev.txt`, `serve.bat`, `'stage3'` (oddly-named artifact)
- `db/` — `db_utils.py`, `migrate_01_schema.py`, `migrate_02_stage_renum.py`
- `web/` — `app.py`, `db.py`, `models.py`, `llm.py`, `serper.py`, `fetcher.py`; `web/routers/` `sessions.py`, `stage1_search.py` … `stage9_save.py`; `web/static/` (built SPA + assets)
- `frontend/` — `package.json`, `vite.config.ts`, `vitest.config.ts`, `tsconfig.json`; `frontend/src/` `App.tsx`, `main.tsx`, `api/{client,types}.ts`, `data/countryCodes.ts`, `hooks/{useSSE,useHITL}.ts`, `utils/quoteHighlight.ts` (+`.test.ts`), `components/home/PanelPicker.tsx`, `components/layout/{HITLPanel,StageNav}.tsx`, `components/shared/*`, `components/stage{1..9}/*`
- `tests/` — `conftest.py`, `test_health.py`, `test_sessions.py`, `test_stage1.py`, `test_stage2.py`, `test_stage8.py`, `test_fetcher.py`; `.pytest_cache/`
- `obsidian_migrate_folder/` — `robust_fetch.py`, `fetch_contents.py`, `check_progress.py`, `build_biographies.py`, `report_26june2026.md`, `fetch_output.log`
- `frontend/node_modules/` (committed-heavy working tree), `.claude/settings.local.json`
