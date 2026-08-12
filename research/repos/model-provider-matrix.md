# Foundation-model x provider matrix for small-model finetuning

- **Date:** 2026-08-12
- **Project:** Reusable small-model finetuning pipelines for prosopography research (education extraction, professional background, org harmonization)
- **Author:** R1 online research dispatch, memo 2 of 6
- **Scope:** Pick small, cheap-to-run base models and hosted finetuning providers. Finetuning must be **hosted/paid** (no local training GPU); a **Jetson tier** (Orin Nano 8 GB unified memory, max ~7B Q4 GGUF via llama.cpp) must be runnable for inference from the same base models.
- **Axis:** Provider/model geography matters (West/USA vs China vs EU/global).

> **Reading guide.** Scores are 1–5 relative within this small-model set (5 = best quality per the open benchmark signal I could verify). Cost-to-finetune figures are **estimates** for a typical small LoRA/SFT run (single epoch over ~100K–1M training tokens) on the quoted per-token/per-hour rate; they are order-of-magnitude, not quotes. Anything I could not verify against a primary source is labelled **unverified**. All prices were current as of the research date but change often — re-check the cited pricing page before committing budget.

---

## 1. Foundation-model x platform scored table (one row per model)

GGUF sizes are the **Q4_K_M** quant file size from the cited HF hub repos unless noted; "RAM ≈" adds typical llama.cpp overhead (weights + KV cache) and is an approximation. **Jetson-feasible** assumes Orin Nano 8 GB unified memory (~6.5 GB usable), max ~7B at Q4 via llama.cpp, small context.

| Model (origin) | Perf proxy (1–5) | Approx cost to finetune (small LoRA/SFT) | Provider / location | Jetson-feasible ≤7B Q4 GGUF? | Note |
|---|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct (Alibaba/China) | 2 | ~$0.05–0.10 (Together SFT LoRA $0.48/1M up to 16B) | China; host on US (Together/Fireworks) or run local | **Y** (~1.1 GB file, ~2 GB RAM) | Fast, cheap; OK for simple field tagging, weaker for nuanced org/professional reasoning. |
| Qwen2.5-3B-Instruct (China) | 3 | ~$0.10–0.20 | China; host on US | **Y** (~1.7–2.0 GB file) | Good small workhorse for structured extraction; slightly dated vs Qwen3. |
| Qwen2.5-7B-Instruct (China) | 4 | ~$0.20–0.50 | China; host on US | **Y** (~3.8 GB Q4_K_M file, ~6 GB RAM) | Strong, well-trodden base for LoRA; many prosopography-friendly evals. |
| Qwen3-0.6B (China) | 1 | ~$0.03–0.05 | China; host on US | **Y** (~0.6 GB) | Coherent but thin; mobile-class. Only for trivial classification. |
| Qwen3-1.7B (China) | 2 | ~$0.05–0.10 | China; host on US | **Y** (~1.2–1.5 GB) | Modern architecture, thinking toggle; a step up from Qwen2.5-1.5B. |
| Qwen3-4B (China) | 4 | ~$0.10–0.20 | China; host on US | **Y** (~2.5 GB Q4_K_M) | **Top small-tier pick:** modern, strong reasoning/instruction, fits Jetson comfortably. |
| Qwen3-8B (China) | 5 | ~$0.15–0.30 | China; host on US | **Y, tight** (~4.8–5.0 GB Q4_K_M, ~6.5 GB RAM, small ctx) | **Top cloud-tier pick**; borderline on 8 GB Jetson — keep context small or drop to Q4_0/Q4_K_S. |
| Llama 3.2-1B (Meta/USA) | 2 | ~$0.05–0.10 | USA | **Y** (~0.9–1.0 GB) | Clean license, weak capacity; mainly for tiny on-device tasks. |
| Llama 3.2-3B (Meta/USA) | 3 | ~$0.10–0.20 | USA | **Y** (~2.1 GB) | Solid, permissive; good default if US-origin preference dominates. |
| Llama 3.2-8B (Meta/USA) | 4 | ~$0.20–0.50 | USA | **Y, tight** (~4.9 GB Q4) | Well-supported in all providers; slightly behind Qwen3-8B on recent benchmarks (unverified, subjective). |
| Gemma 3-4B (Google/USA) | 4 | ~$0.10–0.20 | USA | **Y** (~2.2 GB Q4_K_M) | Multilingual (140+ langs) — a plus for international prosopography records; strong quality-per-GB. |
| Mistral Small 7B / Mistral 7B (Mistral/France, EU) | 3 | ~$0.20–0.50 | EU/France; host on US | **Y** (~4.1 GB Q4) | EU-origin option; good EU data-residency story. Note: "Mistral Small 3" is 24B (not Jetson-runnable) — the 7B here is the older Mistral-7B-class. |
| Phi-4-mini 3.8B (Microsoft/USA) | 3 | ~$0.10–0.20 | USA | **Y** (~2.5 GB 4-bit) | Strong reasoning for size; non-commercial license restriction on the mini (check terms before production). |
| DeepSeek-R1-Distill-Qwen-1.5B (DeepSeek/China) | 2 | ~$0.05–0.10 | China | **Y** (~1.2 GB) | Reasoning-style; chain-of-thought useful for hard field disambiguation at tiny size. |
| DeepSeek-R1-Distill-Qwen-7B (DeepSeek/China) | 4 | ~$0.20–0.50 | China | **Y** (~4.7 GB Q4_K_M, needs ~8 GB) | Reasoning-enhanced Qwen2.5-7B; high quality but slower (CoT token overhead) on Jetson. |

**Jetson-footprint reality check (Orin Nano 8 GB):** comfortable fits = Qwen3-4B (2.5 GB), Gemma 3 4B (2.2 GB), Llama 3.2 3B (2.1 GB), Phi-4-mini (2.5 GB). 7B-class (Qwen2.5-7B, Qwen3-8B, Llama 3.2 8B, R1-Distill-7B, Mistral 7B) at Q4 leave little room for context/KV — workable at small context, but slow (roughly single-digit tok/s) and risky on an 8 GB device. See [Qwen2.5-7B GGUF](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF) (Q4_K_M ≈3.81 GB), [Qwen3-8B GGUF](https://huggingface.co/unsloth/Qwen3-8B-GGUF) (Q4_K_M ≈4.79 GB), [Gemma 3 4B](https://willitrunai.com/blog/gemma-3-local-inference-guide) (~2.2 GB at Q4_K_M), [Llama 3.2 3B GGUF](https://huggingface.co/unsloth/Llama-3.2-3B-Instruct-GGUF) (~2.06 GB), [Phi-4-mini GGUF](https://huggingface.co/lm-kit/phi-4-mini-3.8b-instruct-gguf) (4-bit ~2.49 GB), [DeepSeek-R1-Distill-Qwen-7B GGUF](https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF) (Q4_K_M ≈4.68 GB; jan.ai recommends 8 GB+ to run the 7B).

---

## 2. Hosted finetuning provider comparison

| Provider | Finetuning model & pricing | Geography | Notes |
|---|---|---|---|
| **Together AI** | SFT-LoRA **$0.48 / 1M training tokens** (models ≤16B), DPO-LoRA $1.20/1M; 17–69B tier $1.50/1M; full-SFT $1.65/1M (17–69B). Dedicated inference endpoint after: H100 ~$6.49/hr (or per-token serverless). Supports Llama, Qwen, Mistral. ([pricing](https://www.together.ai/pricing), [docs](https://docs.together.ai/docs/fine-tuning/pricing)) | **USA** (San Francisco, CA) | Best "turn-key LoRA on small models" story; per-token so a small prosopography run is pennies. Watch the hosting bill, not the training bill. |
| **Fireworks AI** | **Serverless Training API** billed per 1M tokens (e.g. train ~$1.46/1M on an ~8–9B model; prefill/sample also billed); also **managed training per GPU-hour** (same rate as on-demand deployments). Finetunes Llama/Qwen/DeepSeek etc. ([pricing](https://fireworks.ai/pricing)) | **USA** (San Francisco) | Token-based billing; strong serving of the result. Prices vary by model size. |
| **Replicate** | Custom-model training billed **per GPU-second**: T4 $0.81/hr, L40S $3.51/hr, A100-80G $5.04/hr, H100 $5.49/hr. You bring a training script in a container; no built-in auto-LoRA wizard. ([pricing](https://replicate.com/pricing)) | **USA** (San Francisco; acquired by/operated with Cloudflare) | Flexible/DIY; for a small 3–8B LoRA a T4 or L40S run is a few dollars. More setup than Together/Fireworks. |
| **Modal** | Serverless **per-GPU-second** compute; bring your own training stack (e.g. HF + Unsloth/TRL in a container). H100 ~$3.95/hr ($0.001097/sec). No managed fine-tune wizard. ([Modal GPU pricing via Morph](https://www.morphllm.com/comparisons/modal-vs-groq)) | **USA** (San Francisco) | Cheapest flexible route if you want full control and can write a training container; scales to zero. Cost = GPU-seconds used. |
| **Hugging Face AutoTrain / Inference** | **AutoTrain** (no-code finetuning UI) is compute-credit based; UI shows an estimated project cost before launch — good for predictable small runs. Hosting via **Inference Endpoints**: T4 $0.50/hr, L4 $0.80/hr, L40S $1.80/hr, A100 $2.50/hr, H100 $4.50/hr. ([AutoTrain cost](https://huggingface.co/docs/autotrain/en/cost), [Endpoints pricing](https://huggingface.co/pricing)) | **EU** (France) | EU residency (GDPR) advantage; deep ecosystem support for every model in the table. AutoTrain abstracts away the infra. |
| **OpenPipe** | Developer-first **SFT platform**; ingest logged requests, auto-generate training sets, produce fine-tuned small models. Pricing is per-use/platform (specific $/1M not pinned here — **unverified**). Emphasis on distilling expensive models (e.g. GPT-class) into cheap fine-tuned ones. ([platform](https://openpipe.ai/fine-tuning), [YC](https://www.ycombinator.com/companies/openpipe)) | **USA** (Seattle, WA) | Best fit if the workflow is "capture production traffic → distill into a small model." |
| **Novita AI** | Serverless **open-model API + GPU instances + fine-tuning**; very low per-token inference (small models from ~$0.01–0.10/1M input). ([pricing](https://novita.ai/pricing), [inference guide](https://novita.ai/docs/guides/llm-recommended)) | **Singapore** (China-adjacent; SF office noted on Crunchbase) | Cheapest option for serving small open models; useful as a low-cost serving/fallback tier. Data-residency is a consideration (Singapore/US ops). |

**Geography quick-reference:** USA = Together, Fireworks, Replicate, Modal, OpenPipe. EU/France = Hugging Face (best for EU data). Singapore (China-adjacent, low-cost) = Novita. Model origin: China = all Qwen2.5/Qwen3/DeepSeek; USA = Llama/Gemma/Phi; EU = Mistral. If West/USA-hosted training + inference is a hard requirement, Together or Fireworks are the defaults; if EU residency matters, Hugging Face.

---

## 3. Recommendation

### CLOUD tier (finetuning is hosted/paid — no local training GPU)
- **Default base model: Qwen3-8B-Instruct** — highest performance proxy in the set, modern instruction-following/thinking toggle ideal for structured prosopography extraction (education, professional background, org harmonization), and cheap to LoRA-tune.
- **Default provider: Together AI (LoRA/SFT)** — USA-hosted, per-1M-token billing ($0.48/1M for ≤16B) makes a small research fine-tune cost pennies; first-class Llama/Qwen support; predictable serverless serving after. Runner-up: **Fireworks** (also USA, token-based) if their model/token mix is cheaper at your volume.
- Cost sanity check: a single-epoch LoRA over ~1M training tokens on Qwen3-8B ≈ **$0.15–0.30** in training tokens on Together; the real cost is hosting the tuned model afterward (serverless per-token, or ~$6.49/hr dedicated H100 if you need a private endpoint). Budget hosting, not training.

### JETSON tier (Orin Nano 8 GB, llama.cpp, ≤7B Q4)
- **Default base model: Qwen3-4B-Instruct (Q4_K_M, ~2.5 GB)** — the sweet spot: modern architecture with the thinking toggle, strong quality for its size, and it fits the 8 GB device with room for a real context window. It is the same model family as the cloud default, so the finetune + GGUF export pipeline is shared across tiers.
- **Runner-up for more capacity:** Qwen2.5-7B or Qwen3-8B at Q4 — workable but context/token-speed constrained on 8 GB (see table). **EU-origin alternative:** Gemma 3 4B (multilingual) or Mistral 7B; **US-license-safe alternative:** Llama 3.2-3B/8B.
- **Pipeline note:** finetune the base on the cloud tier (Together/Fireworks LoRA), then **export to GGUF** (llama.cpp `convert` + `quantize`, or grab a pre-quantized `unsloth`/`bartowski` GGUF of the tuned checkpoint) and run on Jetson with llama.cpp.

### Decision drivers
- **US-hosted, turn-key, cheap** → Together AI (LoRA) + Qwen3-8B (cloud) / Qwen3-4B (Jetson).
- **EU residency / GDPR** → Hugging Face AutoTrain + Inference Endpoints; keep same Qwen3 bases.
- **Lowest serving cost** → Novita (Singapore) for the tuned model, but mind data-residency.
- **Full control / lowest GPU cost** → Modal or Replicate with a custom Unsloth/TRL container.
- **Reasoning-heavy disambiguation** → DeepSeek-R1-Distill-Qwen-7B (cloud) and -1.5B (Jetson), accepting CoT token overhead.

---

### Sources
- GGUF sizes / RAM: [Qwen2.5-7B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF), [unsloth/Qwen3-8B-GGUF](https://huggingface.co/unsloth/Qwen3-8B-GGUF), [bartowski/Qwen_Qwen3-4B-GGUF](https://huggingface.co/bartowski/Qwen_Qwen3-4B-GGUF), [Gemma 3 VRAM guide](https://willitrunai.com/blog/gemma-3-local-inference-guide), [unsloth/Llama-3.2-3B-Instruct-GGUF](https://huggingface.co/unsloth/Llama-3.2-3B-Instruct-GGUF), [lm-kit/phi-4-mini-3.8b-instruct-gguf](https://huggingface.co/lm-kit/phi-4-mini-3.8b-instruct-gguf), [bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF](https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF), [jan.ai R1 local](https://jan.ai/post/deepseek-r1-locally)
- Provider pricing / HQ: [Together pricing](https://www.together.ai/pricing) & [docs](https://docs.together.ai/docs/fine-tuning/pricing) & [HQ SF](https://www.linkedin.com/company/togethercomputer); [Fireworks pricing](https://fireworks.ai/pricing); [Replicate pricing](https://replicate.com/pricing); [Modal GPU cost via Morph](https://www.morphllm.com/comparisons/modal-vs-groq); [HF AutoTrain cost](https://huggingface.co/docs/autotrain/en/cost) & [HF Endpoints pricing](https://huggingface.co/pricing); [OpenPipe platform](https://openpipe.ai/fine-tuning) & [YC Seattle](https://www.ycombinator.com/companies/openpipe); [Novita pricing](https://novita.ai/pricing) & [Novita/Singapore](https://x.com/ArtificialAnlys/status/1882478322611081403)
- OpenPipe exact per-token rate and any prices not present on the cited pages are **unverified** — confirm on the live pricing page before purchase.
