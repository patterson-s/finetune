# External Finetuning and Hosting Options (No Local GPU)

**Memo 6 of 6 — R1 online research dispatch, small-model finetuning pipelines project**
**Date:** 2026-08-12
**Status:** Online research memo. Self-contained. Pricing figures marked `[unverified]` where they could not be confirmed against a primary source.
**Author:** Hermes subagent (web research dispatch)

---

## 1. Premise and Goal

Scott has **no dedicated local GPU for finetuning** (no hardware capable of training). Finetuning therefore must happen on an external/hosted service. He is **open to paying API costs** for both finetuning and inference. The target workflow is:

1. **Select a base model** from a catalog (open-weight models like Llama, Qwen, Gemma, Mistral, GLM preferred so the result stays portable).
2. **Provide his own training data** in some accepted format (JSONL / Parquet / CSV / messages format).
3. **Kick off a finetune** (LoRA or full).
4. **DOWNLOAD the resulting weights** — this is the crux. Without downloadable weights, the result is locked in the vendor's cloud.
5. **Host/serve the model** behind an **OpenAI-compatible endpoint** that Hermes / Claude Code can call.
6. **Shrink / quantize** the result to **≤ ~7B Q4 GGUF** so a Jetson tier (llama.cpp) stays possible.

Weight-downloadability is weighted **heavily** because it is what keeps both the "bring-your-own serving" option and the Jetson tier alive.

---

## 2. Methodology

Web research via `web_search` + `web_extract` against vendor docs and pricing pages (2026-08-12). Where a fact was not verifiable from a primary source, it is explicitly marked `[unverified]`. Pricing for hosted finetune services (per-token, per-GPU-hour, per-month) changes frequently; treat all numbers as "as of research date" snapshots.

---

## 3. Master Scoring Table (one row per platform)

Legend: ✅ = strong/yes · 🟡 = partial/possible · ❌ = no/weak · `[unv]` = unverified. "Wt DL" = **weight downloadability** (the crux). "Jetson" = can the result be shrunk/quantized to ≤7B Q4 GGUF for llama.cpp.

| Platform                  | Cat                | Model catalog flexibility               | Data upload                           | **Wt DL**                                           | Hosted inference                                  | OpenAI-compatible serve                | Price (finetune + infer)                                                                            | Geography                           | Jetson tier              |
| ------------------------- | ------------------ | --------------------------------------- | ------------------------------------- | --------------------------------------------------- | ------------------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------ |
| **Together AI**           | A                  | ✅ huge catalog + BYOM from HF           | ✅ JSONL/Parquet via API               | ✅ LoRA adapter + merged downloadable                | ✅ dedicated endpoints                             | ✅                                      | ✅ FT per-token (~$0.48/M tokens LoRA-16B, $3.20/M full-70B) + dedicated H100 $6.49/hr `[unv exact]` | West/USA                            | ✅                        |
| **Fireworks**             | A                  | ✅ large open catalog                    | ✅ JSONL messages (SFT, LoRA, vision)  | ✅ **LoRA adapter OR merged BF16 — explicit docs**   | ✅                                                 | ✅                                      | 🟡 `[unv]` per-token FT + serving                                                                   | West/USA                            | ✅                        |
| **Replicate**             | A                  | ✅ many open base models (LoRA-style)    | ✅ zip / files API; LLM JSONL `[unv]`  | ✅ weights + LoRA `.tar` downloadable                | ✅                                                 | ✅ (OpenAI-compatible proxy)            | 🟡 `[unv]`; image FT <$2, LLM varies                                                                | West/USA                            | ✅                        |
| **Baseten**               | A (mainly serving) | ✅ serve any HF/open checkpoint          | N/A (bring your own model/checkpoint) | ✅ you own the weights you bring                     | ✅                                                 | ✅ fully OpenAI-compatible              | 🟡 `[unv]` deployment GPU-based                                                                     | West/USA                            | ✅                        |
| **OpenPipe**              | A                  | ✅ open models (Llama 3.x, etc.)         | ✅ request logging + two-click train   | ✅ "own your weights, deploy anywhere"               | ✅                                                 | ✅                                      | 🟡 `[unv]` free tier to start                                                                       | West/USA                            | ✅                        |
| **Predibase**             | A                  | ✅ open models; LoRA-first (LoRAX)       | ✅ upload dataset                      | ✅ exportable weights                                | ✅ LoRAX multi-adapter serving                     | ✅                                      | 🟡 `[unv]`; ~$30/job one-click estimate                                                             | West/USA                            | ✅                        |
| **Lepton AI**             | A                  | ✅ open models                           | ✅ upload                              | ✅ exportable `[unv]`                                | ✅                                                 | ✅                                      | 🟡 `[unv]`                                                                                          | West/USA                            | ✅                        |
| **HuggingFace AutoTrain** | A                  | ✅ any model on the Hub                  | ✅ CSV/JSONL/HF dataset                | ✅ **result pushed to HF Hub — always downloadable** | ✅ via HF Inference Endpoints                      | ✅ (HF endpoints are OpenAI-compatible) | 🟡 `[unv]` compute-based                                                                            | West/USA                            | ✅                        |
| **Novita AI**             | A                  | ✅ open models (LoRA/dedicated endpoint) | 🟡 `[unv]`                            | 🟡 `[unv]`                                          | ✅ dedicated endpoints                             | ✅                                      | 🟡 `[unv]`                                                                                          | 🇸🇬 Singapore/global (origin Asia) | 🟡 depends on wt DL      |
| **Groq**                  | A                  | 🟡 limited LPU-optimized catalog        | ✅ OpenAI-style fine_tunings           | ❌ **no weight download** (proprietary serving)      | ✅ extremely fast                                  | ✅                                      | 🟡 `[unv]`                                                                                          | West/USA                            | ❌ cannot extract weights |
| **RunPod**                | B                  | ✅ bring any model; any stack            | ✅ you control everything              | ✅ full control (your storage)                       | ✅ serverless/Public Endpoints                     | ✅ (bring vLLM/Llama.cpp)               | ✅ H100 ~$2.99/hr on-demand; A6000 ~$0.29–0.48/hr                                                    | West/USA + global                   | ✅                        |
| **Vast.ai**               | B                  | ✅ bring any model; any stack            | ✅ full control                        | ✅ full control                                      | 🟡 DIY serving only (no managed endpoint)         | 🟡 DIY                                 | ✅ cheapest: H100 ~$1.33–2.80/hr; 2080Ti ~$0.08/hr                                                   | Global marketplace                  | ✅                        |
| **Lambda**                | B                  | ✅ bring any model                       | ✅ full control                        | ✅ full control                                      | 🟡 DIY serving                                    | 🟡 DIY                                 | ✅ H100 $3.29–4.29/hr; A6000 $1.09/hr                                                                | West/USA                            | ✅                        |
| **Modal**                 | B (managed)        | ✅ any model via code (Unsloth examples) | ✅ code/volume upload                  | ✅ download from job output/volume                   | ✅ serverless + OpenAI-compatible endpoint example | ✅                                      | ✅ pay-per-use `[unv]`                                                                               | West/USA                            | ✅                        |
| **Hyperbolic**            | B                  | ✅ bring any model                       | ✅ full control                        | ✅ full control                                      | 🟡 DIY serving                                    | 🟡 DIY                                 | ✅ H100 ~$3.19/hr; 4090 ~$0.20/hr; H200 $3.99/hr                                                     | West/USA + global                   | ✅                        |

---

## 4. Category A — Managed finetune + host all-in-one (notes)

### 4.1 Together AI — ⭐ top managed pick
- **Model selection:** Very large catalog of open models (Qwen 3.x, Llama 3.x, Gemma, Mistral, GLM, Kimi MoE) **plus "bring your own model" from the HuggingFace Hub** ([docs.together.ai/docs/fine-tuning/overview](https://docs.together.ai/docs/fine-tuning/overview)). LoRA (default) and full fine-tuning, plus SFT, DPO, vision, function-calling, reasoning.
- **Data:** JSONL or Parquet, uploaded via Python/SDK/cURL with `purpose="fine-tune"` ([quickstart](https://docs.together.ai/docs/fine-tuning/quickstart)).
- **Weight download:** ✅ The deployment doc explicitly says *"Serve your fine-tuned model on a dedicated endpoint **or download it for local use**"* — LoRA adapter and/or merged weights are downloadable ([docs.together.ai/docs/fine-tuning/deployment](https://docs.together.ai/docs/fine-tuning/deployment)).
- **Hosting/OpenAI:** Dedicated endpoints are OpenAI-compatible; also serverless inference.
- **Price:** Finetuning billed **per token of training data**, not per GPU-hour: LoRA SFT on a 16B base ≈ **$0.48/M tokens**; full FT on 70–100B ≈ **$3.20/M**; DPO on 70–100B ≈ **$8/M** `[unverified exact, but consistently reported]`. Hosting on a dedicated H100 endpoint ≈ **$6.49/hr** `[unverified exact]` ([docs.together.ai/docs/fine-tuning/pricing](https://docs.together.ai/docs/fine-tuning/pricing), [eesel guide](https://www.eesel.ai/blog/together-ai-pricing)).
- **Jetson:** ✅ LoRA adapter downloadable → merge → quantize to GGUF. Solid.

### 4.2 Fireworks — ⭐ strongest explicit weight-download story
- **Model selection:** Large open catalog (Llama, Qwen, etc.), SFT + LoRA + vision ([docs.fireworks.ai/fine-tuning/fine-tuning-models](https://docs.fireworks.ai/fine-tuning/fine-tuning-models)).
- **Data:** JSONL in OpenAI `messages` format, uploaded as files.
- **Weight download:** ✅ **Best-documented of the managed platforms.** Dedicated "Downloading model weights" section: `firectl model download <FINE_TUNED_MODEL_ID>` for the **LoRA adapter** alone, or download the **merged (base + adapter) BF16** model; quantize afterward ([docs.fireworks.ai/fine-tuning/deploying-loras](https://docs.fireworks.ai/fine-tuning/deploying-loras)). Community notes confirm weights are available on request ([r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1efkoj8/question_about_finetuning_in_fireworksai/)).
- **Hosting/OpenAI:** ✅ fast hosted inference, OpenAI-compatible.
- **Price:** `[unverified]` per-token FT + per-token serving.
- **Geography:** USA.
- **Jetson:** ✅ Download LoRA or merged → quantize to Q4 GGUF. Excellent.

### 4.3 Replicate — train + host, weights downloadable
- **Model selection:** Many open base models; LoRA-style finetunes (FLUX for image, LLMs for text).
- **Data:** Files/zip upload API for image; JSONL for LLM `[unverified]` ([replicate.com/docs/get-started/fine-tune-with-flux](https://replicate.com/docs/get-started/fine-tune-with-flux), [API blog](https://replicate.com/blog/fine-tune-flux-with-an-api)).
- **Weight download:** ✅ Output includes a `weights` URL returning `trained_model.tar` (a "Download weights" button in UI). Community confirms downloading 7B Llama2 finetunes works ([r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/188fzhu/downloading_weights_from_replicate_of_finetuned/)).
- **Hosting/OpenAI:** ✅ Replicate serves your trained model; OpenAI-compatible proxy available.
- **Price:** `[unverified]`; image FT <$2, LLM varies with model/dataset.
- **Jetson:** ✅.

### 4.4 Baseten — really a serving layer (bring your own weights)
- **Positioning:** Baseten is primarily a **model deployment/serving** platform; you bring your own checkpoint/config rather than using a one-click managed finetune. Strong OpenAI-compatible serving (chat completions), fully supported ([baseten.co/resources/changelog/baseten-is-fully-openai-compatible](https://www.baseten.co/resources/changelog/baseten-is-fully-openai-compatible/), [docs build-your-model](https://docs.baseten.co/development/model/build-your-first-model)).
- **Weight control:** ✅ you own the weights you deploy.
- **Price:** `[unverified]` GPU-based deployment pricing.
- **Jetson:** ✅ (you already hold the weights). Not a finetune engine per se.

### 4.5 OpenPipe
- **Model selection:** Open models (Llama 3.x etc.).
- **Data:** Automatic request logging turns live traffic into training data in minutes; two-click train ([openpipe.ai/fine-tuning](https://openpipe.ai/fine-tuning)).
- **Weight download:** ✅ marketing states *"Own your model weights and deploy anywhere — cloud, edge, or on-prem."*
- **Hosting/OpenAI:** ✅.
- **Price:** `[unverified]`; free tier to start.
- **Jetson:** ✅.

### 4.6 Predibase
- **Model selection:** Open models, LoRA-first (LoRA Exchange / LoRAX lets you serve 100s of adapters on one GPU).
- **Data:** Upload dataset.
- **Weight download:** ✅ exportable weights ([odsc medium guide](https://odsc.medium.com/supercharge-your-llms-fine-tune-and-serve-slms-with-predibase-b53d4686f6d4), [one-click finetune comparison](https://alexstrick.com/posts/2024-06-17-one-click-finetuning.html)).
- **Price:** `[unverified]`; a one-click 7B finetune estimated ~$30 in a 2024 walkthrough.
- **Jetson:** ✅.

### 4.7 Lepton AI
- Managed finetune + deploy LLM. Weight export `[unverified]`. OpenAI-compatible serving. USA-based. `[unverified]` pricing.

### 4.8 HuggingFace AutoTrain — ⭐ best for guaranteed-downloadable + Jeterson
- **Model selection:** **Any model on the HuggingFace Hub** — effectively unbounded (Llama, Qwen, Gemma, Mistral, etc.) ([huggingface.co/docs/autotrain/tasks/llm_finetuning](https://huggingface.co/docs/autotrain/en/tasks/llm_finetuning)).
- **Data:** CSV / JSONL / HF dataset.
- **Weight download:** ✅ **The result is saved to a HF Hub repo** — always downloadable, trivially, forever.
- **Hosting/OpenAI:** ✅ serve via HF Inference Endpoints (OpenAI-compatible chat completions).
- **Price:** `[unverified]` compute-based (AutoTrain charges for compute; a free/limited tier exists).
- **Jetson:** ✅ — download the Hub repo, quantize to Q4 GGUF, run in llama.cpp. This is the cleanest path for the Jetson tier.

### 4.9 Novita AI
- LoRA finetune + dedicated OpenAI-compatible endpoints ([novita.ai/docs](https://novita.ai/docs/guides/llm-dedicated-endpoint)). Model catalog of open models. **Weight download `[unverified]`** (this is the deciding factor — if you cannot download, it cannot feed the Jetson tier). Headquartered Singapore/global, origin Asia. Pricing `[unverified]`.

### 4.10 Groq — ❌ for this use case (fast inference only)
- Groq offers LoRA **inference** and a fine-tuning API ([console.groq.com/docs/lora](https://console.groq.com/docs/lora)), but on LPU hardware and a **limited catalog** (Llama/Gemma-lineage). Critically: **you cannot download the weights** — serving is proprietary. Great for inference speed, **not** for a workflow that requires downloadable, portable, quantizable weights. **Jetson: ❌.**

---

## 5. Category B — Rent-a-GPU / bring-your-own-weights (notes)

These give maximum control (run Unsloth, Axolotl, LlamaFactory, MLX, llama.cpp) and **you always own the weights** because you hold all files in your own storage/volume. The tradeoff: no one-click "train then serve" product — you assemble the stack yourself.

### 5.1 RunPod — ⭐ best Category B default
- Rent GPUs on-demand (per-second), plus **serverless** and **Public Endpoints** for serving; fully supports bring-your-own stack (vLLM, TGI, llama.cpp) behind an OpenAI-compatible endpoint ([runpod.io/pricing](https://www.runpod.io/pricing), [serverless pricing update](https://www.runpod.io/blog/serverless-pricing-update)).
- **Price:** H100 ≈ **$2.99/hr** on-demand `[unverified, secondary source]`; serverless A6000 ≈ **$0.29–0.48/hr**; entry consumer GPUs cheaper. (~2.72/1.75/1.58/0.69/0.58 figures on the pricing page correspond to different tiers `[unverified exact mapping]`.)
- **Weight download:** ✅ full control. **Jetson:** ✅.
- Geography: West/USA + global regions.

### 5.2 Vast.ai — cheapest raw compute
- Peer-to-peer GPU marketplace; lowest prices of the group ([vast.ai/pricing](https://vast.ai/pricing)). H100 ≈ **$1.33–2.80/hr**, RTX 2080 Ti ≈ **$0.08/hr**, T4 ≈ **$0.11/hr** (market rates, fluctuate).
- **Weight download:** ✅ full control. **Jetson:** ✅.
- Caveat: no managed OpenAI endpoint — DIY serving; variability in hardware quality/uptime. Geography: global marketplace.

### 5.3 Lambda (Lambda Cloud)
- Reliable neocloud; on-demand instances. H100 ≈ **$3.29–4.29/hr**, A6000 ≈ **$1.09/hr**, A10 ≈ **$1.29/hr** ([lambda.ai/pricing](https://lambda.ai/pricing), [lambda.ai/instances](https://lambda.ai/instances)). No managed serving — bring your own. Weight download ✅, Jetson ✅. West/USA.

### 5.4 Modal (managed serverless) — ⭐ great for reproducible pipelines
- **Managed** serverless compute: write a function (e.g. Unsloth finetune example), Modal provisions the GPU, you download weights from the job's output/volume ([modal.com/docs/examples/unsloth_finetune](https://modal.com/docs/examples/unsloth_finetune)). Serving can be an **OpenAI-compatible endpoint** ([Modal docs video](https://www.youtube.com/watch?v=GzEcyBykkdo) "OpenAI-Compatible Endpoint Demo on Modal").
- **Weight download:** ✅ from output/volume. **Jetson:** ✅.
- Price: pay-per-use `[unverified]`. West/USA.

### 5.5 Hyperbolic — cheap marketplace
- GPU rental marketplace + some open access. H100 ≈ **$3.19/hr**, H200 ≈ **$3.99/hr**, B200 ≈ **$5.99/hr** ([hyperbolic.ai/marketplace](https://www.hyperbolic.ai/marketplace), [computeprices](https://computeprices.com/providers/hyperbolic)); RTX 4090 reportedly as low as **~$0.20/hr** `[unverified, news report]` ([cybernews](https://cybernews.com/tech/gpu-rental-prices-are-crashing/)). DIY serving. Weight download ✅, Jetson ✅. West/USA + global.

---

## 6. Recommendation

### 6.1 Best default for the cloud/finetune tier (paid, weights-downloadable, OpenAI-compatible serving)

**Primary: Together AI.**
- Large open-model catalog **plus bring-your-own-model from HF Hub** → the widest base-model choice.
- Explicit **weight download** (LoRA adapter and/or merged) so nothing is locked in.
- OpenAI-compatible dedicated endpoints for hosting (Hermes/Claude Code point straight at it).
- Reasonable per-token finetuning pricing (`$0.48/M` LoRA on ≤16B) — well-suited to a ≤7B project.
- **Runner-up / alternate: Fireworks** — the **best-documented weight-download path** (explicit `firectl model download` for LoRA or merged BF16), fast OpenAI-compatible hosting. Choose Fireworks if the definitive download story is the deciding factor; choose Together if you need the widest catalog + BYOM flexibility.

**For the guaranteed-Jetson-friendly managed path: HuggingFace AutoTrain.**
- Result always lands in a HF Hub repo you can download and quantize to Q4 GGUF. Cheapest mental overhead for a portable ≤7B artifact.

### 6.2 Platforms that keep the Jetson tier viable (download → quantize → llama.cpp)

All of these let you **extract the trained weights** and then quantize to ≤7B Q4 GGUF:

- **Category A (managed, weights downloadable):** **Together** (LoRA/merged), **Fireworks** (LoRA or merged BF16), **Replicate** (trained model `.tar`), **OpenPipe** (own weights), **Predibase** (exportable), **Lepton** `[unv]`, **HF AutoTrain** (always, via Hub repo). **Baseten** qualifies only in the sense that you hold the weights you deploy.
- **Category B (rent-a-GPU):** **RunPod, Modal, Lambda, Vast.ai, Hyperbolic** — you own all files, so the Jetson tier is trivially viable (quantize the checkpoint yourself).

**Explicitly NOT Jetson-viable: Groq** — weights cannot be downloaded (proprietary LPU serving). **Novita** is conditional on `[unverified]` weight download — verify before relying on it.

---

## 7. Key citations

- Together docs — fine-tuning overview / deployment (weight download): https://docs.together.ai/docs/fine-tuning/overview · https://docs.together.ai/docs/fine-tuning/deployment · https://docs.together.ai/docs/fine-tuning/pricing · https://docs.together.ai/docs/fine-tuning/lora-vs-full · https://docs.together.ai/docs/fine-tuning/quickstart
- Together pricing (3rd-party guide): https://www.eesel.ai/blog/together-ai-pricing
- Fireworks — SFT & weight download: https://docs.fireworks.ai/fine-tuning/fine-tuning-models · https://docs.fireworks.ai/fine-tuning/deploying-loras · https://fireworks.ai/blog/fine-tune-launch
- Fireworks weight-download community: https://www.reddit.com/r/LocalLLaMA/comments/1efkoj8/question_about_finetuning_in_fireworksai/
- Replicate — fine-tune / download weights: https://replicate.com/docs/get-started/fine-tune-with-flux · https://replicate.com/blog/fine-tune-flux-with-an-api · https://www.reddit.com/r/LocalLLaMA/comments/188fzhu/downloading_weights_from_replicate_of_finetuned/
- Baseten — OpenAI-compatible: https://www.baseten.co/resources/changelog/baseten-is-fully-openai-compatible/ · https://docs.baseten.co/development/model/build-your-first-model
- OpenPipe — own your weights: https://openpipe.ai/fine-tuning
- Predibase: https://odsc.medium.com/supercharge-your-llms-fine-tune-and-serve-slms-with-predibase-b53d4686f6d4 · https://alexstrick.com/posts/2024-06-17-one-click-finetuning.html
- HF AutoTrain LLM finetuning: https://huggingface.co/docs/autotrain/en/tasks/llm_finetuning
- Novita docs: https://novita.ai/docs/guides/llm-dedicated-endpoint
- Groq LoRA / fine-tuning: https://console.groq.com/docs/lora
- RunPod pricing: https://www.runpod.io/pricing · https://www.runpod.io/blog/serverless-pricing-update
- Vast.ai pricing: https://vast.ai/pricing · https://vast.ai/pricing/gpu/H100-SXM
- Lambda pricing: https://lambda.ai/pricing · https://lambda.ai/instances
- Modal Unsloth finetune: https://modal.com/docs/examples/unsloth_finetune
- Hyperbolic marketplace: https://www.hyperbolic.ai/marketplace · https://computeprices.com/providers/hyperbolic · https://cybernews.com/tech/gpu-rental-prices-are-crashing/

---

*End of memo. Next step (suggested): pick Together (or Fireworks) for the managed cloud tier and HF AutoTrain as the Jeterson-safe managed fallback; use RunPod/Modal if you want raw stack control. All `[unverified]` pricing should be re-confirmed against live vendor pricing pages at purchase time.*
