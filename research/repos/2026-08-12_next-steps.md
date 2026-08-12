# Finetune Pipelines — Follow-Up Memo (Next Steps)

**Date:** 2026-08-12
**Status:** Follow-up to R1 research dispatch. Defines the first concrete build target.
**Companion docs:** R1 memos in `projects/finetune/R1-reports/`; `r2-repo-analysis.md`.

---

## 1. Objective

Move from research to a first working model. The goal is a **small, Jetson-runnable** education-extraction model, produced and validated end-to-end — with a data-optimization experiment run in parallel.

## 2. Task selection

- **Start with one task: an education-experience extractor.** This is the first candidate case and the highest-value proof of the pipeline.
- **Work-experience extractor** is a candidate follow-on task, but its design depends on the R2 report (prior-art mining of EliteResearchAgent / careerfinder / UN_AI_PANEL). We do not need to solve it now — only start with education extraction.
- **Org harmonization** remains a later task; no action now.

## 3. Model target — Jetson-first

- We are not particular about *where* finetuning happens, but the **model itself must fit the Jetson** (Orin Nano, 8 GB unified).
- **Chosen base: a small Qwen ~3B model** (e.g. Qwen2.5-3B / Qwen3). Rationale: small enough to run comfortably, strong enough for structured extraction.
- **Target footprint: under ~5 GB** on the Jetson, leaving overhead (KV cache, context, OS) inside the 8 GB budget. A Q4-class GGUF of a 3B model fits this comfortably.
- This keeps a real local inference tier on the Jetson with room to spare.

## 4. Training data — two-track head-to-head comparison

We believe the training data already exists (the fact-checked UN_AI_PANEL education gold set, 79 people / 193 degrees / 842 sources). Test two ways of preparing it:

- **Track A — Minimal conversion:** do the least work to turn what we already have into training rows. Straightforward `collect` stage from the gold source.
- **Track B — Adaption Labs optimization:** use Adaption Labs (Adaptive Data) to optimize / improve the same training data before training. Scott has **credits + early access as a beta tester**.
- **Outcome:** a **head-to-head comparison** of the two prepared datasets — same model, same training setup, same eval — to see which data prep wins.

This directly exercises the `collect` vs `augment` stages of the pipeline and validates whether Adaption's data shaping is worth the credits.

## 5. Where to finetune

- We are **agnostic on the finetuning provider** — any capable hosted service works.
- **Adaption Labs may integrate with Together AI** (which R1 flagged as a strong finetuning default, LoRA, weights-downloadable). We can use that integration, but **do not have to**. Treat it as an available option, not a requirement.
- Decision rule: pick whichever path is easiest / best-value given the Adaption credits, keeping **weight downloadability** and Jetson feasibility as hard requirements.

## 6. Weight storage

- **HuggingFace private repo** is the chosen registry (per R1 memo 5): store the LoRA adapter + a merged Q4 GGUF + `manifest.json` per artifact, so the model is recoverable across the PC and the Jetson.

---

## Next actions (proposed)

1. Confirm/assemble the education gold set into a base dataset (Track A) — minimal conversion.
2. Set up the Adaption Labs path on the same data (Track B) using beta credits.
3. Train the same Qwen 3B base on both tracks, head-to-head, same eval.
4. Validate on held-out people + the anti-hallucination probe.
5. Store the winner (and/or both) in a private HF repo; export a Q4 GGUF for the Jetson.
6. Serve via llama.cpp/Ollama and wire into Hermes (per R1 harness memo).

## Open questions (not blocking)

- Confirm Adaption↔Together integration is the best use of credits, or run standalone.
- Final Qwen flavor (Qwen2.5-3B vs Qwen3-3B/4B) pending footprint/quality check.
- Exact eval metric + person-disjoint split agreed before training.
