# R3 — Design Memo (Synthesis of R1 + R2)

**Date:** 2026-08-12
**Status:** Authoritative design for the finetune project. Unblocks B0 (pipeline build) and C0 (first case).
**Inputs:** R1 online research (7 memos in `research/R1_reports/`), R2 repo analysis (8 reports in `research/R2_reports/`), and the R1 next-steps memo (`2026-08-12_next-steps.md`).
**Outputs:** this memo + `configs/tasks.yaml` + `configs/providers.yaml`.

---

## 1. Vision & priority tiers

The overarching vision (from Initialize.md): start each research project with a general-purpose LLM, then **miniaturize to a small fine-tuned model** once the workflow stabilizes. Fine-tuned models are a more durable IP asset than a directory of prompts. This project builds the reusable pipelines to do that.

The work is organized into **three priority tiers** — this is the roadmap, not just one task:

### Tier 1 — Immediate: Education-extraction model (the first case)
- **Why first:** relatively simple, high-value, and directly useful to the UN_AI_PANEL and prosopography projects today.
- **Goal:** a small, Jetson-runnable education-extraction model, produced and validated end-to-end, with a data-optimization experiment run in parallel.
- **Gold set already exists:** UN_AI_PANEL `education_check.json` — 79 people / 193 degrees / 842 source docs, fact-checked with citations (from R2).
- This is the "prove it works end-to-end" case per the plan's validate-first principle.

### Tier 2 — Short-term: Prosopography-adjacent finetune tasks
Existing UN_AI_PANEL / prosopography tasks we can miniaturize (all surfaced in R2 as having rich training data in the EliteResearchAgent repos):
- **Career / professional-background extraction** — gold source: `EliteResearchAgent/services/careerfinder_granular_01/review/` (75 persons, 2,714 chunk→extraction pairs, 10,469 events).
- **Organization ontology / harmonization** (types, names, hierarchies) — gold sources: v2 `university_ontology.json` (144 canonical-variant), v4 `org_ontology_mappings` (168 equivalence classes), plus raw org pool `org_ontology_01/data/careerfinder_results.jsonl`.
- These are useful to existing projects *now*, so they're the next tranche once Tier 1 is proven.

### Tier 3 — Backburner: Re-architecture of prior finetuning projects
Not immediately useful, but strong long-term value; two candidate projects:
- **FEC finetuning project re-architecture:** a **hierarchical classification** system that exploits the output taxonomy's hierarchy (job types → parent categories), moving off OpenAI infra to a small, possibly multi-step model, then benchmarking against the current approach. (R2 confirmed the current project is a decoder-map GPT-3.5 finetune; the hierarchy idea is a natural evolution.)
- **pydeal_type re-architecture:** a huge existing corpus (24GB, two Cohere models on the same data = built-in confidence triage) that "must have something we can do with it" — likely a small aggressor/victim classification model, possibly using the cross-model agreement as labels.
- Both are set-aside until Tier 1 & 2 are running; the pipeline built for Tier 1 will apply to them.

**This tiering is the operative plan** and supersedes the earlier flat task list where they conflict.

---

## 2. Architecture

A pluggable stage-pipeline, implemented as a Python package `finetune/`. Each candidate task is defined once in `configs/tasks.yaml`; each stage is a small, tested, interchangeable unit.

```
collect → augment → adapt → train → store → serve
  │        │         │        │       │       │
  gold      sampling /  hosted   LoRA /  weights  GGUF /
  source    synthetic   (Adaption  hosted  → HF    llama.cpp
  → rows    (pydeal     /Together) or     repo   Ollama →
            sampler)    → job       local          Hermes/
                                            Claude Code
```

**Stage contracts** (from the plan B-series, confirmed by R1/R2):
- **collect** — turn a gold source into canonical training rows (`system`/`user`/`assistant` JSONL). Reuses UN_AI_PANEL gold, EliteResearchAgent corpora.
- **augment** — balanced/covered sampling + optional synthetic generation. Template = pydeal_type `build_adaption_dataset.py` (class balance, era/person caps). Also the decoder-map output-constraint idea from FEC_BLS.
- **adapt** — Adaption Labs (hosted, free credits) + optionally a second provider as interchangeable `TrainerAdapter` backends.
- **train** — local LoRA (PEFT) for smoke/iteration + hosted training for the real run.
- **store** — weights + manifest → private HF repo; artifact-id + git tag (R1 memo 5).
- **serve** — GGUF export → llama.cpp/Ollama OpenAI-compatible endpoint → wire into Hermes + Claude Code (R1 memo 4).

---

## 3. First case (Tier 1) design — education extraction

### 3.1 Task
Given a person's biographical source material, extract their structured education history (level, field, university, year, country) — and crucially, **verify the info is actually about the target person** (anti-hallucination / distractor resistance).

### 3.2 Training data — two-track head-to-head
From R2, the fact-checked gold set exists. Test **two ways** of preparing it, same model + train + eval:

- **Track A — Minimal conversion:** the `collect` stage turns `education_check.json` into training rows directly (least work). Straightforward baseline.
- **Track B — Adaption Labs optimization:** use Adaption Adaptive Data to optimize/shape the same data before training (Scott has **credits + beta access**). Exercising `adapt` + the augment philosophy.
- **Outcome:** a head-to-head comparison that validates whether Adaption's data shaping is worth the credits.

### 3.3 Model target — Jetson-first
- **Base:** a small Qwen ~3B (rationale in next-steps memo; R1 model matrix confirms fit).
- **Target footprint:** under ~5GB on the 8GB Jetson → a Q4-class GGUF of a 3B model fits comfortably, leaving overhead for KV cache + context + OS.
- **Two tiers, one family:**
  - Cloud tier (training is hosted): Qwen3-8B-Instruct (best quality proxy; Together LoRA = pennies).
  - Jetson tier (inference is local): **Qwen3-4B-Instruct Q4_K_M (~2.5GB)** — the sweet spot; same family so the finetune→GGUF path is shared. (R1 model matrix §3.)
- **Pending confirmation:** Qwen2.5-3B vs Qwen3-3B/4B flavor — recommend Qwen3-4B for the modern architecture + thinking toggle, subject to a footprint/quality check.

### 3.4 Finetuning provider
- **Agnostic** — any capable hosted service. Default: **Together AI** (LoRA, per-1M-token ~$0.48, weights downloadable, first-class Qwen support; R1 matrix §2/§3).
- Adaption Labs is the data-shaping layer (Track B), and **may integrate with Together** for the actual training (R1 adaption memo). Decision rule: pick whichever is easiest/best-value given the Adaption credits, keeping **weight downloadability + Jetson feasibility** as hard requirements.

### 3.5 Weight storage
- **Private HuggingFace repo** (R1 memo 5): store the LoRA adapter + merged Q4 GGUF + `manifest.json` per artifact-id, so the model is recoverable across PC and Jetson. Artifact-id = content-derived hash; git-tagged.
- License note: keep repos private; record base-model license in the manifest.

### 3.6 Validation
- **Person-disjoint train/eval split** (hold out ~15–20% of *people*, not degrees — no leakage).
- **Eval metric:** field-level match (level/field/university/year/country) + structural validity of the JSON output. To be finalized before training (open question).
- **Anti-hallucination probe:** feed the model a bio snippet **plus a distractor** (another person's degree) and assert it doesn't attribute the distractor to the target. The UN_AI_PANEL `all_sources[]` field (including uncited sources) provides natural negative material (R2).

---

## 4. Key decisions locked in (from R1+R2)

| Decision | Choice | Source |
|---|---|---|
| First case | Education extraction (Tier 1) | next-steps memo |
| Base model (cloud) | Qwen3-8B-Instruct | R1 model matrix |
| Base model (Jetson) | Qwen3-4B-Instruct Q4_K_M (~2.5GB) | R1 model matrix |
| Finetune provider | Together AI (LoRA) default; Adaption for data shaping | R1 matrix + adaption memo |
| Weight registry | Private HF repo (adapter + GGUF + manifest) | R1 weights memo |
| Serve | llama.cpp/Ollama OpenAI-compatible → Hermes + Claude Code | R1 harness memo |
| Data prep comparison | Track A minimal vs Track B Adaption | next-steps memo |
| Anti-hallucination | Distractor probe test | R2 + plan C3 |

## 5. Open questions (non-blocking, to confirm before/at training)

1. **Qwen flavor:** Qwen2.5-3B vs Qwen3-3B/4B. Recommend Qwen3-4B pending footprint/quality check.
2. **Adaption usage:** standalone (AutoScientist) vs via its Together integration. Recommend: use Adaption for **data shaping** (Track B), train on Together.
3. **Eval metric + split:** finalize field-match weights and confirm person-disjoint split proportions.

## 6. What this unblocks

- **B0** — pipeline scaffold + stage implementation (collect → serve), each TDD.
- **C0** — the Tier-1 education case end-to-end (dataset build → two-track train → gold-validate → distractor probe → Jetson GGUF serve → Hermes wiring).
- **D0** — Tier-2 (career, org) and Tier-3 (FEC hierarchical, pydeal_type) — gated on C0 success.

## 7. Reports referenced

- R1: `research/R1_reports/` (adaption-labs, model-provider-matrix, jetson-local, harness-integration, weights-registry, finetune-options, 2026-08-12_next-steps)
- R2: `research/R2_reports/` (5 per-repo + eliteresearchagent-cluster + full-cross-repo + r2-repo-analysis)
