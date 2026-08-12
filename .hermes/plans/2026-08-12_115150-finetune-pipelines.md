# Finetune Pipelines & Prosopography Models — Implementation Plan

> **For Hermes:** Use subagent-driven-development to implement this plan stream-by-stream and task-by-task.

**Goal:** Build reusable, small-model finetuning pipelines (collect → augment/synthetic → adapt → train → store → serve) and prove them end-to-end on a first candidate case: prosopography extraction (education, professional background, org harmonization) for the UN_AI_PANEL project.

**Architecture:** A Python package (`finetune/`) with a pluggable stage-pipeline (collect / augment / adapt / train / store / serve) plus a `models/` spec layer where each task is defined once (task.yaml → data, target model, output format). First candidate case is validated end-to-end against the UN_AI_PANEL gold standard (193 education degrees, already fact-checked with citations) before any expansion. Research runs in parallel streams that converge on a design memo.

**Tech Stack:** Python 3.11, PyTorch + PEFT/LoRA (open-weight path), llama.cpp GGUF (local Jetson path), HuggingFace Hub (weights registry), Adaption Labs API (hosted free-credit path, already prototyped in pydeal_type), OpenAI finetune API (legacy path from FEC_BLS), git + GitHub for cross-device sync.

**Repo:** `C:\Users\spatt\Desktop\finetune` (base). **Do NOT modify** the source repos (EliteResearchAgent v1–v5, finetune_FEC_BLS, pydeal_type, UN_AI_PANEL) — copy background material in read-only.

---

## Context & Assumptions

- User wants small, cheap models that do one function well, addressing common failure modes (e.g. "is this education/job info actually about the target person?").
- Broader vision: start each project with a general LLM, then *miniaturize to a smaller fine-tuned model* once the workflow stabilizes. Fine-tuned models are a more durable IP asset than prompt directories.
- Multiple models per task is acceptable: a high performer (cloud) and a small Jetson-runnable version.
- Adaption Labs is already on the radar — `pydeal_type/runs/USA_01/prompt/aggressor_05/analysis/build_adaption_dataset.py` already produced `adaption_test_dataset_v1.csv` (100 rows, prompt/context/output, class-balanced, decade-covered). That script is the seed of the `collect`+`adapt` stages.
- Existing finetune precedent: `finetune_FEC_BLS` used OpenAI GPT-3.5 finetune with a **decoder map** (model emits a token, map decodes to human label) to curb hallucination — a pattern worth carrying forward.
- UN_AI_PANEL already has a **gold-standard label set**: `review/education_check/build_data.py` produces `education_check.json` — 79 people, 193 degrees, each with structured fields (level, field, university, year, country), source quotes, and resolved citations. Ideal supervised target for Task 1.
- **Jetson Orin Nano: 8 GB unified memory → hard ceiling ≤ ~7B Q4 GGUF.** llama.cpp CUDA build + ollama already installed. DeepSeek-OCR GGUF already validated. Local inference path = llama.cpp + GGUF, on-demand only (thermals).
- Foundation models worth evaluating (open weights): Qwen2.5/3, Llama 3.x, Gemma, Mistral, Phi — mapped on multiple axes (performance, cost, provider location, Jetson size/feasibility).
- Repo `Desktop\finetune` is currently empty (no commits, no remote). Needs git init + GitHub remote + regular pushes.
- Research updates live in the repo AND mirrored to `C:\Users\spatt\Desktop\JetsonVault\projects\finetune`.

---

## Stream Architecture & Dependency Graph (Kanban/Gantt)

Research streams run in parallel; build depends on the design memo.

```
                 ONLINE RESEARCH (parallel, Stream O)
   O1 Adaption Labs  O2 Foundation-model/provider matrix  O3 Jetson local feasibility
   O4 Harness integration (Hermes/Claude Code)             O5 Weight storage/registry
        │   │   │   │   │
        ▼   ▼   ▼   ▼   ▼
   ┌─────────────────────────────┐
   │   Stream S: SYNTHESIS        │  ← design memo (models.md, providers.md, pipelines.md)
   └─────────────────────────────┘
                 │
                 ▼
   ┌─────────────────────────────┐        ┌─────────────────────────────┐
   │  Stream B: BUILD PIPELINES   │  ←dep→  │ Stream C: FIRST CANDIDATE   │
   │  (collect/augment/train/     │        │  CASE (UN_AI_PANEL edu ext)  │
   │   serve skeleton + tests)    │        │  end-to-end + gold validate  │
   └─────────────────────────────┘        └─────────────────────────────┘
                 │
                 ▼
   Stream D: EXPAND (professional bg, org harmonization) — only after C validated

REPO DEEP-ANALYSIS (parallel, Stream R)
   R1 Mine EliteResearchAgent v1–v5 (prompts, data, org_ontology, careerfinder)
   R2 Mine finetune_FEC_BLS + pydeal_type (finetune patterns, adaption dataset)
   R3 Inventory UN_AI_PANEL data sources + education_check.json schema
        │
        ▼  (feeds O-stream decisions AND Build stage datasets)
```

**Dependency rules:**
- O1–O5, R1–R3 all run in parallel (independent reads).
- Synthesis (S) consumes all memos → single design memo before build.
- Build (B) and Candidate-case pipeline authoring (C) can begin once S is done; C's *training/eval* needs the collect/augment stages from B.
- Expansion (D) strictly gated on C passing the gold-standard bar.

---

# STREAM O — ONLINE RESEARCH (parallelizable as 5 independent sub-tasks)

Each sub-task produces a memo at `research/online/<topic>.md`. Dispatch in parallel via delegate_task. Provide each with the exact URLs already known + the axis guidance.

### O1: Adaption Labs integration
**Objective:** Document Adaption Labs API, auth, dataset format, fine-tune invocation, pricing/credits, and how our `collect`/`augment` outputs map to it.
**Seed:** `pydeal_type/runs/USA_01/prompt/aggressor_05/output/adaption_test_dataset_v1.csv` and `build_adaption_dataset.py`.
**Deliverable:** `research/online/adaption-labs.md` — exact API endpoints, payload format, credit usage, example call, plus a decision: use Adaption as primary hosted trainer or secondary.
**Verification:** Memo contains a copy-pasteable curl/python call and cites the docs URL.

### O2: Foundation-model & provider matrix
**Objective:** Map candidate small open-weight models × provider/location × cost × size, on the axes Scott specified (performance, cost, provider location West/USA/China/EU, Jetson size/feasibility).
**Models to score:** Qwen2.5 1.5B/3B/7B, Qwen3, Llama 3.2 1B/3B/8B, Gemma 3 4B, Mistral Small 7B, Phi-4-mini, DeepSeek-R1-Distill-Qwen-1.5B/7B.
**Providers to compare:** Together (LoRA pricing known), Fireworks, Replicate, Modal, HuggingFace AutoTrain/Inference, OpenPipe, Novita, local on PC, local on Jetson. Note provider geography (US/West vs China).
**Deliverable:** `research/online/model-provider-matrix.md` — a scored table + recommended default for cloud path and Jetson path.
**Verification:** Table has a row per model, columns for cost, quality proxy, location, Jetson-feasible (Y/N at ≤7B Q4).

### O3: Jetson local feasibility
**Objective:** Confirm the smallest useful open-weight models that run within 8 GB (≤~7B Q4 GGUF), quantization/format options (GGUF via llama.cpp, already proven), expected token/s on the Orin Nano, and a recommended "Jetson tier" model per candidate task.
**Inputs:** jetson-orin-nano skill (llama.cpp CUDA + ollama already installed; DeepSeek-OCR validated).
**Deliverable:** `research/online/jetson-local.md`.
**Verification:** Recommends a concrete GGUF model per candidate task and notes the on-demand-only thermals constraint.

### O4: Harness integration (Hermes / Claude Code)
**Objective:** Design how a fine-tuned model is exposed so Hermes and Claude Code can call it: local llama.cpp/ollama OpenAI-compatible endpoint on the Jetson, vs a hosted endpoint. Map to Hermes' ability to point at a custom OpenAI-compatible base URL / model, and Claude Code's model config.
**Deliverable:** `research/online/harness-integration.md` — a concrete wiring diagram (endpoint URL, model id, env config) for both Hermes and Claude Code.
**Verification:** Includes the exact config keys/snippets to make Hermes and Claude Code target a local GGUF server.

### O5: Weight storage / registry
**Objective:** Decide where weights live (HuggingFace Hub private repo vs local disk) + a versioning/CI story so a trained model is reproducible and recoverable across devices.
**Deliverable:** `research/online/weights-registry.md`.
**Verification:** Recommends a storage scheme + a `store` stage contract (push weights + manifest to HF, tag git).

---

# STREAM R — REPO DEEP-ANALYSIS (parallel with Stream O)

Each sub-task produces a memo at `research/repos/<topic>.md`. Read-only over the source repos.

### R1: Mine EliteResearchAgent v1–v5
**Objective:** Extract reusable prompts, training-data-like artifacts, and org-ontology logic from `EliteResearchAgent`/`_v2`/`_v3`/`_v4`/`_v5`.
**Key finds so far:** `services/RetroPropogation_03/.../org_ontology_02/ontology.json`, `org_ontology_01/motif.json`, `careerfinder_granular_01/review/<Person>/chunk_*_results.json` (per-person chunked career results), `prosopography.md`.
**Deliverable:** `research/repos/elite-agents.md` — catalog of reusable prompt templates, the org-ontology schema, and candidate training examples (esp. org harmonization + career finding). Do NOT copy into the live repo yet — just inventory with paths.
**Verification:** Lists each service's role, its data artifacts, and which is a viable training-source for each candidate task.

### R2: Mine finetune_FEC_BLS + pydeal_type
**Objective:** Capture the finetuning patterns that worked: OpenAI finetune + decoder-map approach, the Adaption dataset builder, and evaluation practices.
**Deliverable:** `research/repos/prior-finetune.md` — summarize the FEC_BLS decoder-map trick, the pydeal_type adaption dataset sampling logic (class balance, decade anchors, speaker/target caps), and lessons learned.
**Verification:** Each stage in the target pipeline is cross-referenced to a concrete prior-art file.

### R3: Inventory UN_AI_PANEL data sources
**Objective:** Map the exact supervised data available for the candidate cases. Reuse `review/education_check/build_data.py` output (`education_check.json`) as the gold standard; inventory `people/<Name>/raw/*.md` source docs, `biography.md`, and any org/career fields.
**Deliverable:** `research/repos/un-ai-panel-data.md` — schema of education_check.json, counts (79 people / 193 degrees / 334 anchored citations), list of candidate task→gold-source mappings (education, professional background, org harmonization), and gaps.
**Verification:** Confirms Task 1 (education extraction) has a full supervised gold set; flags whether professional/org tasks need additional labeling.

---

# STREAM S — SYNTHESIS (single design memo)

**Objective:** Converge all O/R memos into the authoritative design that gates the build.

**Files:**
- Create: `docs/design.md` — the single source of truth (architecture, chosen models per task, provider decision, data contracts, serve topology).
- Create: `configs/tasks.yaml` — one block per candidate task: id, name, gold-data-source, target model (cloud + jetson), output format, eval metric.
- Create: `configs/providers.yaml` — chosen providers with credentials env-var names.

**Step 1:** Read all memos under `research/online/` and `research/repos/`.
**Step 2:** Draft `docs/design.md` + `configs/tasks.yaml` + `configs/providers.yaml`.
**Step 3:** Review: does Task 1 (education extraction) have a defined gold source, target models on both tiers, an output schema, and an eval metric? If yes, proceed. If not, fix before building.
**Step 4:** Commit.

---

# STREAM B — BUILD THE PIPELINE (TDD)

Repo scaffold + core stages. Each stage is a small, tested unit. This stream delivers the *framework*; Stream C wires the first task through it.

### B0: Repo scaffold
**Objective:** Empty repo → git-initialized, structured, pushable.
**Files:**
- Create: `README.md`, `.gitignore` (ignore `.venv/`, `data/`, `weights/`, `__pycache__/`, `*.gguf`, `*.safetensors`, env files)
- Create: `pyproject.toml` (package `finetune`, deps: torch, peft, transformers, datasets, llama-cpp-python, pyyaml, httpx)
- Create: `finetune/__init__.py`, `tests/__init__.py`

**Step 1:** `git init` in `C:\Users\spatt\Desktop\finetune`.
**Step 2:** Add remote (ask Scott for the GitHub repo URL; default to a new private repo `scott-patterson/finetune`).
**Step 3:** Write README/.gitignore/pyproject/stubs.
**Step 4:** `git add -A && git commit -m "chore: scaffold finetune repo" && git push -u origin main`.
**Verification:** `git log --oneline` shows the commit; `git push` succeeds; a fresh clone on another device sees the tree.

### B1: Task-spec loader
**Objective:** Load `configs/tasks.yaml` into typed dataclasses.
**Files:**
- Create: `finetune/spec.py`, `tests/test_spec.py`

**Step 1 (RED):** Test that `load_tasks("configs/tasks.yaml")` returns a `TaskSpec` with required fields (id, gold_source, model_tiers, output_schema, eval_metric).
**Step 2:** `python -m pytest tests/test_spec.py -v` → FAIL (module missing).
**Step 3:** Implement `spec.py` (dataclasses + yaml loader + validation that required keys exist).
**Step 4:** PASS. Commit `feat: task spec loader`.

### B2: collect stage (gold → training rows)
**Objective:** Turn a gold source (e.g. `education_check.json`) into a canonical training dataset (JSONL: `system`, `user`, `assistant`).
**Files:**
- Create: `finetune/collect/__init__.py`, `finetune/collect/gold.py`, `tests/test_collect.py`
- Create: `finetune/collect/schema.py` (the canonical row schema + conversion helpers)

**Step 1 (RED):** Test that `gold_to_rows(education_check_sample)` yields N rows with `system`/`user`/`assistant` fields and no empty `assistant`.
**Step 2:** FAIL. **Step 3:** Implement conversion (person raw bio snippet → user; the fact-checked degree fields → assistant JSON). **Step 4:** PASS. Commit.

### B3: augment stage (synthetic / balanced sampling)
**Objective:** Borrow the pydeal_type sampling discipline: class balance, era/person caps, dedup. Plus a pluggable synthetic-generation hook (LLM-assisted) for later.
**Files:**
- Create: `finetune/augment/sample.py`, `finetune/augment/synth.py` (stub), `tests/test_augment.py`

**Step 1 (RED):** Test balance/caps logic against the pydeal_type constraints (40/60 split, per-person cap, era coverage).
**Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. Commit `feat: augment/sample`.

### B4: adapt stage (Adaption Labs + OpenAI adapters)
**Objective:** Wrap Adaption Labs (hosted, free credits) and OpenAI finetune as two interchangeable `TrainerAdapter` backends with a shared interface.
**Files:**
- Create: `finetune/adapt/base.py`, `finetune/adapt/adaption.py`, `finetune/adapt/openai.py`, `tests/test_adapt.py`

**Step 1 (RED):** Test the adapter interface contract (each adapter exposes `submit(dataset)` → job id and `status(id)`).
**Step 2:** FAIL. **Step 3:** Implement base + a fake in-memory adapter for tests (no network), plus real Adaption/OpenAI wrappers behind `APISecret` env vars. **Step 4:** PASS (fake backend). Commit `feat: adapt stage`.

### B5: train stage (local open-weight LoRA)
**Objective:** Local PEFT/LoRA training on a small model (e.g. Qwen2.5-1.5B) with a smoke run that completes on the PC, so no cloud credit is needed for iteration.
**Files:**
- Create: `finetune/train/lora.py`, `tests/test_train.py` (smoke: 1 step)

**Step 1 (RED):** Test that `train_lora(dataset, model_id="Qwen/Qwen2.5-1.5B-Instruct", max_steps=1)` produces a checkpoint dir.
**Step 2:** FAIL (import/impl missing). **Step 3:** Implement minimal LoRA loop (peft + transformers, tiny max_steps). **Step 4:** PASS — a 1-step run completes. Commit `feat: train/lora`.

### B6: store stage (weights + manifest → HF/local)
**Objective:** Save the trained adapter + a manifest (task id, base model, dataset hash, metric) to disk and optionally HF Hub.
**Files:**
- Create: `finetune/store/registry.py`, `tests/test_store.py`

**Step 1 (RED):** Test that `store(model_dir, manifest)` writes `manifest.json` and returns a stable artifact id. **Step 2:** FAIL. **Step 3:** Implement (hash dataset → artifact id; write manifest; HF push stub). **Step 4:** PASS. Commit `feat: store/registry`.

### B7: serve stage (local GGUF + OpenAI-compatible endpoint for Hermes/Claude)
**Objective:** Export a trained model to GGUF (or load a GGUF base + adapter) and expose it via llama.cpp/ollama's OpenAI-compatible server so Hermes/Claude Code can target it.
**Files:**
- Create: `finetune/serve/local.py` (spawns llama.cpp/ollama server, returns base URL), `tests/test_serve.py`
- Create: `finetune/serve/harness.md` stub documenting the Hermes + Claude Code wiring (filled by O4).

**Step 1 (RED):** Test that `serve_config(model)` returns a valid base-url/model-id pair (pure function, no network). **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. Commit `feat: serve/local`.

### B8: CLI + Makefile orchestration
**Objective:** A single `finetune` CLI (`finetune collect <task>`, `augment`, `adapt`, `train`, `store`, `serve`) and a `Makefile`/`justfile` to chain stages.
**Files:**
- Create: `finetune/cli.py` (typer/click), `Makefile`, `tests/test_cli.py`

**Step 1 (RED):** Test `finetune --help` lists all stages. **Step 2:** FAIL. **Step 3:** Implement CLI wiring each stage. **Step 4:** PASS. Commit `feat: cli`.

---

# STREAM C — FIRST CANDIDATE CASE (education extraction, end-to-end + gold validate)

The "prove it works first" phase. Uses the UN_AI_PANEL education gold set end-to-end. Only after this passes the bar do we expand (Stream D).

### C1: Build the education training dataset
**Files:**
- Create: `datasets/education/train.jsonl`, `datasets/education/eval.jsonl` (via the collect stage, from `education_check.json`)
- Create: `datasets/education/split.py` (deterministic train/eval split, seeded; hold out ~15–20% of people, not degrees — avoid leakage)

**Step 1 (RED):** Test split is deterministic and person-disjoint across train/eval. **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
**Step 5:** Run `python -m finetune collect --task education` → produces train/eval JSONL from the real gold source.
**Verification:** `wc -l datasets/education/*.jsonl` matches ~193 degrees; eval contains no train persons. Commit.

### C2: Train the cloud-tier model (small open-weight, LoRA)
**Step 1:** Run local LoRA on `Qwen/Qwen2.5-1.5B-Instruct` (or 3B) with the education train set; log eval on held-out persons.
**Step 2:** Record eval metric (exact field match / partial / structural accuracy on the JSON output).
**Step 3:** If quality is below bar, try the Adaption Labs hosted path (free credits) with the same dataset for comparison.
**Verification:** `store` stage produces a manifest with the metric; artifact id recorded in `results/education/`.

### C3: Validate the anti-hallucination concern
**Objective:** The core pain point — "is the extracted education actually about the target person?" 
**Step 1:** Design a small probe eval: feed the model a bio snippet *plus* a distractor (another person's degree) and assert the model doesn't attribute it to the target.
**Step 2 (RED):** Write the probe test (`tests/test_probe_distractor.py`). **Step 3:** Run against the trained model; record pass/fail in `results/education/probe.md`. 
**Verification:** Probe result documented; if failing, note the augmentation/synth follow-up (Stream D/E).

### C4: Export & serve the Jetson tier
**Step 1:** Export/quantize a small tier model to GGUF (e.g. Qwen2.5-1.5B Q4) and load via llama.cpp on the Jetson (on-demand, 25W).
**Step 2:** Point Hermes (and optionally Claude Code) at the local OpenAI-compatible endpoint per O4 wiring.
**Verification:** A Hermes call to the local model returns an education extraction for a sample person; documented in `results/education/jetson-serve.md`.

### C5: First-case report
**Deliverable:** `results/education/REPORT.md` — what was trained, which provider, eval metric, probe result, Jetson result, cost. This is the gate for Stream D.

---

# STREAM D — EXPANSION (gated on C5)

Only after C5 passes the gold bar. Run as separate follow-up tasks (not parallel with C):
- **D1:** Professional-background extraction task (reuse R1 careerfinder artifacts + R3 inventory as gold source; may need a labeling pass).
- **D2:** Organization harmonization task (types/names/hierarchies — reuse `org_ontology.json`; this is more of a normalization task, possibly classify+map, good fit for the decoder-map trick).
- **D3:** Synthetic/augmentation expansion (LLM-assisted synthetic negatives targeting the distractor failure mode from C3).
- **D4:** Multi-project packaging (turn the pipeline into a reusable harness so any project can define a task and get a mini-model).

---

# Files likely to change (whole project)

- `C:\Users\spatt\Desktop\finetune\` — the new repo (all of Streams B–D).
- `research/online/*.md`, `research/repos/*.md`, `docs/design.md`, `configs/*.yaml` — memos + design.
- Mirror of research memos + reports → `C:\Users\spatt\Desktop\JetsonVault\projects\finetune\`.

# Tests / Validation

- Unit: `pytest tests/` per stage (RED-GREEN). Fake/no-network backends for adapt/serve so CI is fast.
- Gold validation: Task 1 metric computed on held-out people in `results/education/`.
- Probe: distractor anti-hallucination test (`tests/test_probe_distractor.py`).
- Jetion smoke: 1-step LoRA completes; GGUF loads and serves a real extraction.

# Risks, Tradeoffs, Open Questions

- **Cost vs quality tradeoff:** local LoRA on a 1.5B may underperform the hosted Adaption/OpenAI path; plan runs both and compares, but budgets Scott's free credits carefully.
- **Adaption Labs specifics unverified:** pricing, API shape, and credit terms need O1 confirmation before committing it as primary trainer.
- **Jetson ceiling:** anything >~7B won't fit; the Jetson tier may need a smaller/quantized model that trades accuracy — acceptable per the multi-tier plan.
- **Dataset leakage:** splitting by degrees vs people matters; plan uses person-disjoint split (C1).
- **Org harmonization labeling:** no obvious gold set yet — may require a manual labeling pass before it's a supervised task. (Open question for Scott.)
- **GitHub remote URL:** need the repo URL or permission to create a private repo under Scott's account.
- **Hermes/Claude Code custom-model config:** confirmed possible in principle; exact keys depend on the installed Hermes version — verify in O4 against the running Hermes, not just docs.
- **Licensing:** fine-tuned weights from open-weight bases are fine to store privately; keep base-model licenses documented in the manifest.

**Open questions for Scott (quick, batched):**
1. GitHub repo URL / whether to create a new private `scott-patterson/finetune`.
2. Adaption Labs account/credits available — confirm API key env var name or location.
3. For Task 1, confirm the education gold set (193 degrees from `education_check.json`) is the validation target.
4. Priority order for Stream D expansion (professional bg vs org harmonization first)?

---

## Suggested execution order (parallel where possible)

1. **Kick off Stream O (5 tasks) + Stream R (3 tasks) in parallel** via delegate_task → 8 memos.
2. **Synthesis (S)** → design memo + task/provider configs. Commit.
3. **Build (B0–B8)** → pipeline skeleton, TDD, commit per stage.
4. **Candidate case (C1–C5)** → train, gold-validate, probe, Jetson-serve, report.
5. **Expansion (D)** → only after C5 gate.
6. **Mirror** research + results to `C:\Users\spatt\Desktop\JetsonVault\projects\finetune\` and push to GitHub regularly.
