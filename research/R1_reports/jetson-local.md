# Jetson local feasibility for small finetuned models

**Date:** 2026-08-12
**Memo:** 3 of 6 — R1 online research dispatch (small-model finetuning pipelines project)
**Scope:** Feasibility of running small open-weight (≤ ~7B, Q4 GGUF) and finetuned models locally on an NVIDIA Jetson Orin Nano Super (8GB unified memory) for on-demand inference only.

---

## 0. Target hardware & software baseline

| Item | Spec |
|---|---|
| Board | NVIDIA **Jetson Orin Nano Super Developer Kit**, 8GB unified LPDDR5 |
| GPU | NVIDIA Ampere, 1024 CUDA cores, 32 Tensor cores |
| Memory bandwidth | **~102 GB/s** (Super dev kit; NVIDIA spec). *Note: the original (non-Super) Orin Nano is ~68 GB/s — figures in this memo assume the Super.* |
| Peak compute | ~67 TOPS (INT8) on the Super dev kit *(vendor marketing figure; see §4 — inference is memory-bound, not compute-bound)* |
| Cooling | Passive reference cooler (user constraint) → **on-demand inference only** |
| Runtime | llama.cpp (CUDA build, `sm_87`), ollama, and a **validated DeepSeek-OCR GGUF path** already installed |

Usable memory: with the OS + display sharing the 8GB unified pool, roughly **~5.2–6.0 GB** is available to the model + KV cache (varies by JetPack; MakerPortal assumes 75% ≈ 6.0 GiB usable, ericxliu measured ~5.2 GB after OS overhead). This is the hard budget for weights + KV cache.

**Bottom line:** every model in the task list below fits in 8GB at Q4 GGUF, with the 7B-class models being *tight* and requiring reduced context. Decoding on this device is **memory-bandwidth bound**, so tokens/sec is governed by (weights size) ÷ (102 GB/s), i.e. smaller quantizations and smaller models are faster.

---

## 1. Which smallest open-weight models run within 8GB unified memory (≤ ~7B Q4 GGUF via llama.cpp)

Feasibility = **weights (Q4_K_M) + KV cache (context) ≤ ~5.2–6.0 GB usable.**

| Model | ~Q4_K_M weights | Fits in 8GB? | Notes |
|---|---|---|---|
| Qwen2.5-1.5B-Instruct | ~0.9–1.1 GB | ✅ Yes, comfortable | Even fits at FP16 (~3GB); leaves large context headroom |
| Qwen2.5-3B-Instruct | ~1.8 GB | ✅ Yes, comfortable | 36-layer GQA; tiny KV cache (36 KiB/tok) → long context affordable |
| Qwen3-1.7B | ~1.0 GB | ✅ Yes, comfortable | Fast, small footprint |
| Qwen3-4B | ~2.3 GB | ✅ Yes | 36-layer, 144 KiB/tok KV; ~27k-token context at Q4_K_M per roofline calc |
| Llama-3.2-1B-Instruct | ~0.77 GB | ✅ Yes, very comfortable | ~47 tok/s at 25W (measured, SmolHub) |
| Llama-3.2-3B-Instruct | ~1.9 GB | ✅ Yes | Q8_0 (3.2GB) is the largest that fits comfortably; Q4_K_M leaves ~38k-token context |
| Gemma-3-4B-IT | ~2.4 GB | ✅ Yes | 34 layers w/ sliding-window attention (29 layers capped at 1k window) → very long context affordable; Q8_0 (4.3GB) also fits |
| Phi-4-mini-Instruct | ~2.3 GB | ✅ Yes | 128k trained context; Q4_K_M ≈ 30k-token window fits |
| DeepSeek-R1-Distill-Qwen-1.5B | ~1.0 GB | ✅ Yes, very comfortable | Confirmed working on Orin Nano Super (Cytron) |
| DeepSeek-R1-Distill-Qwen-7B | ~4.4–4.7 GB | ⚠️ Yes, **tight** | Needs reduced context (~8–16k) to fit with KV cache in ~6GB. The ~4.7GB Q4_K_M footprint (per APXML/llama.cpp) + a modest KV cache fits, but there is little headroom |

**Conclusion:** All ten candidate models run within 8GB at Q4_K_M. Qwen2.5 1.5B/3B, Qwen3 1.7B/4B, Llama 3.2 1B/3B, Gemma 3 4B, Phi-4-mini, and DeepSeek-R1-Distill-Qwen 1.5B are **comfortable**; DeepSeek-R1-Distill-Qwen **7B is feasible but context-limited** — the largest model that makes sense for this Jetson tier.

> ⚠️ *Caveat:* on some JetPack releases (e.g. R36.4.7) a known llama.cpp/CMA memory-fragmentation regression can block GGUF models needing contiguous CUDA buffers above ~1.1 GB at load time; upgrading to JetPack 6.2.2 (L4T 36.5) resolves it (SmolHub, 2026). Validate each GGUF's load on the actual installed JetPack before committing.

---

## 2. Quantization / format options and expected tokens/sec on Orin Nano (8GB, ~102 GB/s)

### 2.1 Quantization formats (GGUF via llama.cpp)

| Format | Bits/weight | Relative size | Use case |
|---|---|---|---|
| **Q4_K_M** | ~5.0 | ~25–30% of FP16 | **Recommended default** — best quality/speed/memory balance on Jetson (ProventusNova, ericxliu) |
| **Q5_K_M** | ~5.8 | ~10% larger than Q4_K_M | Slightly better quality, more memory/slower; use when quality-critical and context is short |
| Q8_0 | ~8.5 | ~2× Q4 | Near-lossless, but 2× the memory traffic → ~half the tok/s; only for smallest models (≤3B) or when context must be huge |
| **IQ4_XS / IQ4_NL** | ~4.3 | slightly smaller than Q4_K_M | Newer "importance-matrix" 4-bit-ish quants; marginally smaller/faster with comparable quality — worth A/B testing |
| Q3_K_M / IQ3 | ~4 | ~15% smaller than Q4 | More speed at a real quality cost; generally not recommended for extraction/harmonization tasks |
| Q6_K / Q5_K | 5.7–6.6 | between Q4 and Q8 | Mid-tier; Q8_0's FP16 KV-cache sibling for KV can also be quantized to 8-bit to save context memory |

- **KV cache** can be run in 8-bit or 4-bit (`--cache-type-k/v q8_0` etc.) to free significant memory on long contexts — recommended on the 7B models.
- The DeepSeek-OCR GGUF already validated on the box is a good fit for the OCR/education front-end (see §3).

### 2.2 Expected tokens/sec (measured where possible, roofline-derived where not)

Token generation on this device is **memory-bandwidth bound**: every output token reads the full weights once. The 102 GB/s roofline ceiling ≈ `102 GB/s ÷ bytes-per-token`; real runtimes land at roughly **60–80% of the roofline** (MakerPortal, ericxliu). Figures below are at 25W unless noted.

| Model | Quant | Expected tok/s (25W) | Basis |
|---|---|---|---|
| Qwen2.5-1.5B | Q4_K_M | **~30** | Measured ~30 t/s fully on-device (Reddit); roofline ceiling ~55–60 → ~60–80% |
| Qwen2.5-3B | Q4_K_M | **~28–37** | Roofline ceiling 46; measured 19.2 t/s on one forum run (JetPack 6.2, likely lower clocks) |
| Qwen3-1.7B | Q4_K_M | **~30–40** | Roofline-derived (comparable to 1.5B class) |
| Qwen3-4B | Q4_K_M | **~17–28** | **~17 t/s measured** (Reddit, Orin Nano 8GB 4bit); roofline ceiling 28 → 60–80% |
| Llama-3.2-1B | Q4_K_M | **~40–47** | **~47 t/s measured** at 25W (SmolHub llama.cpp) |
| Llama-3.2-3B | Q4_K_M | **~20–28** | Roofline ceiling 34; Jetson AI Lab reports 27.7 t/s; forum reports ~19–23 |
| Gemma-3-4B | Q4_K_M | **~16–25** | **~16–20 t/s measured** via ollama (julien.cloud); roofline ceiling 35; ~17.5 on CPU-only |
| Phi-4-mini | Q4_K_M | **~17–23** | Roofline ceiling 29; sibling Phi-3-mini measured 28 gen t/s (ProventusNova) |
| DeepSeek-R1-Distill-Qwen-1.5B | Q4_K_M | **~24–27** | **Measured:** 24.2 t/s at 25W, 27.5 t/s at MAXN (Cytron) |
| DeepSeek-R1-Distill-Qwen-7B | Q4_K_M | **~10–14** | Roofline ceiling ~21 (4.7GB); 7.5GB models ~>10 t/s reported; ~10–20 t/s expected |

> ⚠️ **Unverified / to confirm on this exact box:** several figures are roofline-derived or from single third-party runs (Reddit/forums) rather than controlled benchmarks on the *same* JetPack + llama.cpp build. Token rates vary ±20–30% with power mode, JetPack version, context length, KV-cache quantization, and `jetson_clocks`. **Benchmark the specific GGUF on the actual hardware before sizing.**

**Power-mode scaling (measured, SmolHub & Cytron):** 15W ≈ 60–70% of 25W speed; 7W ≈ 40–50% of 25W; MAXN only marginally faster than 25W (~5–15%) while drawing much more power and risking thermal/over-current throttling. **25W is the Pareto sweet spot.**

---

## 3. Recommended "Jetson tier" model per candidate task

General guidance: pick the **smallest model that reliably performs the task** to maximize tok/s and keep thermals low, since Jetson decoding is bandwidth-bound.

### 3.1 Education extraction
> *Structured extraction from educational source text (possibly with OCR of scans/PDFs).*

- **Primary:** **Qwen2.5-3B-Instruct (Q4_K_M)** — strong instruction-following and JSON/structured-output reliability, fast (~28–37 t/s), tiny KV cache means long documents fit.
- **OCR front-end:** **DeepSeek-OCR GGUF** (already validated on this box) for scanned materials → then pass extracted text to Qwen2.5-3B.
- **Fallback (higher quality / more reasoning):** **Qwen3-4B (Q4_K_M)**.

### 3.2 Professional background extraction
> *Entity/relation extraction from CVs, bios, and narrative professional histories.*

- **Primary:** **Qwen2.5-3B-Instruct (Q4_K_M)** — reliable structured entity/relation extraction at good speed.
- **Fallback (more reasoning):** **Gemma-3-4B (Q4_K_M)** (~16–25 t/s) or **Qwen3-4B (Q4_K_M)** — both fit comfortably and handle messier narrative text better.

### 3.3 Org harmonization
> *Entity resolution / normalizing organization names across variants (this is the most reasoning-heavy of the three tasks).*

- **Primary:** **Qwen3-4B (Q4_K_M)** — better reasoning + optional thinking mode; fits with long context.
- **Higher-quality / max-fidelity tier:** **DeepSeek-R1-Distill-Qwen-7B (Q4_K_M, reduced context ~8–16k)** — best reasoning of the set, but tight memory and slowest (~10–14 t/s). Use only for batch/offline harmonization, not interactive.

### Summary table

| Task | Recommended Jetson-tier model | Quant | Notes |
|---|---|---|---|
| Education extraction | **Qwen2.5-3B** (+ DeepSeek-OCR GGUF for scans) | Q4_K_M | Fast + reliable structured output |
| Professional background extraction | **Qwen2.5-3B** (or Gemma-3-4B / Qwen3-4B for harder text) | Q4_K_M | Good entity/relation extraction |
| Org harmonization | **Qwen3-4B** (or DeepSeek-R1-Distill-7B, context-limited) | Q4_K_M | Most reasoning-heavy; bigger model helps |

---

## 4. Constraints: on-demand-only inference, thermals, power modes

- **On-demand only (passive cooling):** the passive reference cooler cannot sustain long bursts at MAXN. Keep inference **bursty/on-demand**, let the SoC idle between requests, and avoid background/sustained generation. A single model kept loaded (warm) is fine — idle power is low; the risk is sustained *generation*.
- **Power modes** (via `sudo nvpmodel -m <n>`, then `sudo jetson_clocks` to lock clocks):
  - **7W** (`-m 3`, GPU ~408 MHz): ~40–50% of 25W speed. Battery/low-thermal mode.
  - **15W** (`-m 0`, GPU ~612 MHz): ~60–70% of 25W speed.
  - **25W** (`-m 1`, GPU ~820 MHz): **recommended default — Pareto sweet spot** (35–47% faster than 15W, best tok/J) (SmolHub).
  - **MAXN / MAXN_SUPER** (`-m 2` + `jetson_clocks`, GPU ~1020 MHz): only ~5–15% faster than 25W but higher power/heat; **avoid sustained use on passive cooling** — reports of "system throttled due to over-current" under MAXN + ollama (NVIDIA forums). *Power-mode availability bugs on some JetPack builds (stuck at 15W/25W) are documented — verify with `nvpmodel -q`.*
- **Thermal mitigation for on-demand inference:** load the model once and keep it warm (avoids repeated cold-load latency and, on JetPack 6 with CMA, avoids the unrecoverable CMA memory-fragmentation that a load/unload cycle can trigger — julien.cloud); keep a `keepalive` so the model isn't evicted between requests; if a larger model must run, cap context via `-c` and quantize the KV cache to 8-bit to shrink the footprint.
- **Memory/OOM watch:** on unified memory the allocation may succeed then the Linux OOM killer fires when the KV cache grows (ProventusNova). Drop one quant tier or shrink `-c` rather than relying on swap (swap collapses speed to <2 t/s — julien.cloud).

---

## 5. Serving a finetuned model (LoRA) on the Jetson tier

A finetuned model produced by LoRA on a small base can be deployed two ways on this box:

1. **Merge + quantize to GGUF:** merge the LoRA adapter into the base weights (e.g. via `unsloth`, `peft`, or `mlx-lm`), then convert/quantize to GGUF (Q4_K_M) with llama.cpp's convert/quantize tools, and serve with `llama-server` or ollama. This is the simplest, most portable option and yields a single self-contained `.gguf`.
2. **Serve the adapter through an OpenAI-compatible endpoint:**
   - **ollama:** place the merged GGUF in the ollama model directory (or via a `Modelfile`), then call `http://<jetson>:11434/v1` — OpenAI-compatible chat/completions.
   - **llama.cpp:** `llama-server` exposes `/v1/chat/completions` natively; `-ngl 99` offloads all layers to the GPU. (Note: on Jetson the JetPack-6 ollama build is required for GPU offload — the stock ARM64 tarball can silently run CPU-only; confirm `ggml_cuda_init` / `compute=8.7` in logs, and that `ollama ps` shows 100% GPU offload.)

Either path gives an OpenAI-compatible endpoint on the Jetson, so downstream tooling is interchangeable. **Recommendation:** merge → Q4_K_M GGUF → serve via `llama-server` (or ollama) on the Jetson tier, using the per-task base model from §3 as the LoRA base so the finetuned adapter matches an already-validated Jetson-runnable architecture.

---

## References

- SmolHub — *Tiny LLM Benchmark: Jetson Orin Nano Super 8GB* (4 power modes × 8 models, llama.cpp vs Ollama, measured tok/s & tok/J): https://www.smolhub.com/posts/jetson-nano-super-benchmark-non-reasoning/
- MakerPortal — *LLM VRAM / roofline ceilings on Jetson Orin Nano Super (8GB)* for Llama 3.2 3B, Qwen2.5 3B, Qwen3 4B, Phi-4-mini, Gemma 3 4B: https://makerportal.ai/lab/llm-vram/gpu/jetson-orin-nano-super-8gb (and per-model pages, e.g. https://makerportal.ai/lab/llm-vram/qwen3-4b/jetson-orin-nano-super-8gb)
- ericxliu.me — *Why Your Jetson Orin Nano's 40 TOPS Goes Unused* (roofline analysis; measured sub-1B Q4 tok/s; memory-bound): https://ericxliu.me/posts/benchmarking-llms-on-jetson-orin-nano/
- julien.cloud — *Running Ollama on a Jetson Orin Nano: Gemma 3 to Gemma 4* (measured gemma3:4b ~16–20 t/s; gemma4 GPU 25.5 t/s; CMA/keepalive lessons): https://julien.cloud/blog/jetson-nano-ollama-edge-inference/
- ProventusNova — *Running LLMs on Jetson Orin, llama.cpp, Ollama* (Q4_K_M recommendation; Phi-3-mini 28 gen t/s on Orin Nano 8GB; memory formula; OOM tips): https://proventusnova.com/blog/llm-inference-jetson-orin-llamacpp-ollama/
- Cytron — *DeepSeek R1 on Jetson Orin Nano Super* (measured deepseek-r1:1.5b: 16.4 t/s @15W, 24.2 @25W, 27.5 @MAXN): https://www.cytron.io/tutorial/deepseek-r1-on-nvidia-jetson-orin-nano-super
- NVIDIA Developer Forums — *Jetson Orin Nano Super insufficient GPU memory* (DeepSeek-R1-Qwen-1.5B): https://forums.developer.nvidia.com/t/jetson-orin-nano-super-insufficient-gpu-memory/330777
- NVIDIA Developer Forums — power-mode/over-current reports (MAXN throttling): https://forums.developer.nvidia.com/t/system-throttled-due-to-over-current/318466 and https://forums.developer.nvidia.com/t/jetson-orin-nano-hitting-system-throttled-due-to-over-current/340708
- NVIDIA Developer Blog / Jetson AI Lab — Super mode & Llama 3.2 3B ~27.7 t/s reference: https://www.jetson-ai-lab.com/ and https://developer.nvidia.com/blog/nvidia-jetson-orin-nano-developer-kit-gets-a-super-boost/
- APXML — DeepSeek-R1 7B VRAM requirements (~4.7GB Q4_K_M): https://apxml.com/models/deepseek-r1-7b
- Reddit r/LocalLLaMA — Qwen3-4B ~17 t/s on Orin Nano 8GB: https://www.reddit.com/r/JetsonNano/comments/1rpygw4/running_qwen354b_as_a_terminal_agent_on_the_orin/ ; Qwen 1.5B ~30 t/s on-device: https://www.reddit.com/r/LocalLLaMA/comments/1oncd4a/running_qwen_15b_fully_ondevice_on_jetson_orin/
- NVIDIA spec (Jetson Orin Nano Super, 102 GB/s, 67 TOPS): https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/

*Figures marked "roofline-derived" or from Reddit/forums are single-source or theoretical and should be re-measured on the actual hardware + JetPack before production sizing.*
