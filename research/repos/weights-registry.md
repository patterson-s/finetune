# Weight storage and registry for finetuned models

**Date:** 2026-08-12
**Status:** Online research memo (R1 dispatch, memo 5 of 6). URLs cited below were extracted during research; exact pricing/limits and model-license terms should be re-verified against the live pages before relying on them. Anything not confirmed from a cited primary source is marked **[unverified]**.
**Context:** Solo researcher with a desktop PC (GPU training) and a Jetson Orin Nano 8GB (local inference). Goal: a concrete, reproducible "store" stage so any finetuned model is recoverable and loadable on *both* machines.

---

## 1. Where the weights should live

Three candidate homes for the weight artifacts, evaluated for a solo PC + Jetson setup.

### 1a. Hugging Face Hub — private repository

The Hub stores models/datasets/weights in Git-based repositories; private repos are visible only to the account (and any collaborators you grant access). Uploads are done via the `huggingface_hub` Python library or the `hf` CLI (e.g. `hf upload user/model model.safetensors`, or `--repo-type dataset` for data). [HF repositories getting started](https://huggingface.co/docs/hub/en/repositories-getting-started)

- **Pros**
  - One canonical home reachable from *both* the PC and the Jetson over HTTPS (no shared filesystem or VPN needed). This is the single biggest win for the cross-machine requirement.
  - Versioning built in (Git + Git LFS under the hood; LFS file references are tracked by SHA-256 OID). [HF storage limits doc](https://huggingface.co/docs/hub/en/storage-limits)
  - Free account includes ~100GB of *private* storage; PRO includes 1TB of private storage (above that is pay-as-you-go at ~$18/TB/mo). [HF storage limits doc](https://huggingface.co/docs/hub/en/storage-limits)
  - Natively hosts GGUF files with a metadata/tensor viewer, and integrates with llama.cpp, Ollama, LM Studio, GPT4All. [HF GGUF doc](https://huggingface.co/docs/hub/en/gguf)
  - First-class LoRA/adapter hosting via PEFT (push adapter weights, load with `PeftModel.from_pretrained`). [HF PEFT docs](https://huggingface.co/docs/peft/en/package_reference/lora), [HF transformers PEFT guide](https://huggingface.co/docs/transformers/en/peft)
- **Cons**
  - Private storage is billed above the free/pro tiers; weights + datasets + GGUFs accumulate.
  - Git repo structure has practical limits: keep files under ~200GB each, <100k files, avoid huge commit histories (can `super_squash_history` to reclaim LFS storage). [HF storage limits doc](https://huggingface.co/docs/hub/en/storage-limits)
  - Requires an account/authentication token on both machines (`huggingface-cli login`).
  - Repo is a *push* target — for large merged/GGUF artifacts on a Jetson you upload/download the whole file.

### 1b. Local disk (PC + Jetson)

- **Pros**
  - Fastest load, no auth, no quota, full control.
  - Fine for the *working* artifact tree during a training run.
- **Cons**
  - **No cross-machine sync by itself** — the two machines are separate filesystems. Unless you add rsync/Syncthing/git, a model trained on the PC is not on the Jetson.
  - No versioning, no checksum tracking, easy to overwrite.
  - Drive failure or an SD-card/SSD wipe on the Jetson loses everything.
- **Verdict:** local disk is a *cache/working copy*, not a registry. Keep a canonical copy in the Hub and treat local paths as a cache keyed by artifact id.

### 1c. Cloud blob (S3 / GCS / R2 / Azure Blob)

- **Pros**
  - Cheap object storage (R2/GCS/S3), no repo-structure limits, good for very large single files.
  - Reachable from both machines over HTTPS with auth.
- **Cons**
  - **No versioning semantics / no model metadata** out of the box — you must build the manifest + checksum bookkeeping yourself (you're reinventing the Hub).
  - No GGUF/LoRA ecosystem tooling, no model-card UI, no viewer.
  - Extra auth config on both machines.
- **Verdict:** worthwhile only if artifacts grow beyond HF private quota or if you need CDN-scale distribution; for a solo researcher the Hub is strictly less plumbing.

### 1d. Recommendation

> **Primary registry = a private Hugging Face Hub repository** (one repo per artifact id, or one repo with per-artifact subfolders). Local disk is the working cache on each machine. A cloud blob is optional spillover for very large files, not the default.

---

## 2. Versioning + reproducibility

Reproducibility needs the *inputs*, not just the weights. Lock them together.

### 2a. The manifest

A single `manifest.json` that records, at minimum:

| Field | Example |
| --- | --- |
| `artifact_id` | `data:<hash>-base:<hash>-cfg:<hash>` (see §3) |
| `task_id` | `summarization/legal-v1` |
| `base_model` | `google/gemma-2-2b` |
| `dataset` + `dataset_sha256` | `tome/legal-briefs:v3`, `a1b2c3...` |
| `config` / `train_config_sha256` | JSON of training hyperparameters + their hash |
| `seed` | `2026` |
| `eval_metric` + value | `rouge1: 0.42` |
| `license` | `gemma-2-license` (see §4) |
| `created_at`, `git_commit` of training code | ISO date + commit SHA |
| `files` | list of {filename, sha256, size_bytes} |

Dataset hashing is a well-established pattern: compute a SHA-256 manifest over the files in the data directory (e.g. `find $DATA -type f -print0 | sort -z | xargs -0 sha256sum > manifest.sha256`), and if any underlying file changes the hash changes — you immediately know you are no longer comparing like-for-like. See the dataset-versioning discussions at [ApX "Versioning LLM Datasets"](https://apxml.com/courses/how-to-build-a-large-language-model/chapter-8-building-managing-large-scale-datasets/dataset-versioning-reproducibility) and [Jick Patel, "5 Reproducible ML Habits"](https://medium.com/@jickpatel611/5-reproducible-ml-habits-seeds-to-dataset-locks-b73a4d1e3648).

### 2b. Git tagging of manifest + dataset

- Keep the **dataset definition + manifest** in a git repo (separate from weights). Commit the dataset-spec/dataset files with LFS, then tag:
  - `git tag dataset-v3` on the dataset spec commit
  - `git tag artifact-<artifact_id>` on the commit whose `manifest.json` records that dataset hash and base model
- The tag gives a human-readable handle; the SHA-256 hashes give a machine-checkable guarantee. Always record the *hash* (not just the tag name) in the manifest, because tags can move.

### 2c. CI story — a GitHub Action

A minimal, deterministic pipeline (runs on the PC side):

1. **On push to `main` / PR:** validate that `manifest.json` is well-formed and self-consistent:
   - `task_id`, `base_model`, `dataset_sha256`, `config_sha256` all present and non-empty;
   - recompute `dataset_sha256` over the committed dataset and compare;
   - recompute the artifact_id and confirm it matches the manifest.
2. **On tag `artifact-*` (optional release gate):** push the weight artifacts (adapter + GGUF + `manifest.json`) to the private HF repo using the `HF_TOKEN` secret. [HF repositories getting-started](https://huggingface.co/docs/hub/en/repositories-getting-started)

This keeps "validation" (cheap, every change) separate from "publish" (only on an explicit tag), so you never accidentally overwrite a released artifact.

---

## 3. Recommended "store" stage contract

The goal: after training, run one `store` command anywhere (PC or Jetson), and be able to fetch the exact model back on the other machine.

**Artifact id.** Deterministic, content-derived so identical inputs always produce the same id:

```
artifact_id = sha256(canonical(dataset_sha256) + "|" + base_model + "|" + config_sha256)[:16]
```

**What `store` writes (to a private HF repo `scott/finetune-<artifact_id>`):**

1. **LoRA adapter weights** (the training artifact) — small, faithful, and required to reproduce. Save via PEFT (`peft_model.save_pretrained`, push with `model.push_to_hub`) so it can be re-merged onto the base model. [HF PEFT LoRA docs](https://huggingface.co/docs/peft/en/package_reference/lora), [HF transformers PEFT guide](https://huggingface.co/docs/transformers/en/peft)
2. **Merged GGUF (quantized for the Jetson)** — the *runtime* artifact the Orin Nano actually loads. Convert/quantize the merged model to GGUF (e.g. via `ggml-org/gguf-my-repo`) and store a Q4/Q5 quant that fits in 8GB. GGUF is a self-contained binary (tensors + standardized metadata) designed for GGML executors and fast loading. [HF GGUF doc](https://huggingface.co/docs/hub/en/gguf), [ggml gguf.md spec](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md)
3. **`manifest.json`** — the full record from §2a, including hashes of the adapter and GGUF files.

**After store:**
- `git tag artifact-<artifact_id>` on the training-code/dataset repo commit (from §2b).
- Optionally trigger the CI publish action from §2c.

**Recovery contract.** On *either* machine:
- **PC:** `hf download scott/finetune-<id>` → load adapter + base for continued training/eval; or pull GGUF for llama.cpp.
- **Jetson:** `hf download` the GGUF + manifest → run via llama.cpp/Ollama; verify file SHA-256s match the manifest.

**Store-stage contract (formal):**
> A trained model is "stored" iff (a) a private HF repo exists for `artifact_id`, (b) it contains `adapter/` (LoRA), `<id>.gguf` (merged, quantized), and `manifest.json`, (c) `manifest.json` file hashes match the pushed files, and (d) git is tagged `artifact-<id>` with the dataset+manifest commit.

---

## 4. License implications of storing finetuned weights from open-weight bases

**Key point:** storing privately for your own use triggers *fewer* obligations than distributing — but the fine-tuned weights are still legally a **derivative work** of the base, and its license still governs what you may do with them (including whether you may later redistribute).

- **Private storage ≠ distribution.** For e.g. the Llama Community License, weight-distribution, relicensing, and derivative-disclosure obligations generally *activate only when you share the weights or product with external parties*. Keeping the repo private for your own PC↔Jetson sync is closer to internal use. **[unverified]** — confirm against the exact base-model license text. [WCR Legal, "What Happens to the License When You Fine-Tune a Model"](https://wcr.legal/fine-tuned-model-license/)
- **Derivative status:** a model fine-tuned from a base is typically a derivative of that base. E.g. a Llama-3 fine-tune is a "Llama 3 derivative" and must be distributed under the Llama 3 Community License, *not* re-licensed as Apache-2.0/MIT. [WCR Legal](https://wcr.legal/fine-tuned-model-license/), [promise.legal, "Open-Weight AI License Trap"](https://blog.promise.legal/open-weight-ai-license-trap-startups/)
- **LoRA adapters and quantizations (GGUF) are not a license escape hatch.** LoRA adapters are generally treated as derivative or derived from the base model for licensing purposes; GGUF quantizations are transformed copies of the merged weights, so the same license applies to the GGUF file. **[unverified]** — this is an active area of legal interpretation.
- **Practical rules for this project:**
  - Record the base model's license name in `manifest.json.license`.
  - Keep private repos *private*; don't publish the fine-tune unless you're prepared to release under the base's terms.
  - Be careful mixing datasets with their own licenses (e.g. CC-BY-SA on a Llama base can create conflicting obligations if you ever distribute). [WCR Legal](https://wcr.legal/fine-tuned-model-license/)
  - If the base requires it (e.g. Llama naming/attribution), keep the base name in the model name even if private. [promise.legal](https://blog.promise.legal/open-weight-ai-license-trap-startups/)
- **Not legal advice** — for anything you plan to release publicly, check the actual `LICENSE` file of the specific base model revision you used.

---

## Sources

- Hugging Face — Storage limits (private vs public, PRO tiers, repo limits, LFS SHA-256 OIDs): https://huggingface.co/docs/hub/en/storage-limits
- Hugging Face — Repositories getting started (`hf upload`, repo types): https://huggingface.co/docs/hub/en/repositories-getting-started
- Hugging Face — GGUF format on the Hub (quantization types, llama.cpp/Ollama integration, gguf-my-repo): https://huggingface.co/docs/hub/en/gguf
- ggml — GGUF file-format spec: https://github.com/ggml-org/ggml/blob/master/docs/gguf.md
- Hugging Face — PEFT LoRA reference (save/merge adapters): https://huggingface.co/docs/peft/en/package_reference/lora
- Hugging Face — Transformers PEFT guide (add adapter): https://huggingface.co/docs/transformers/en/peft
- ApX ML — Dataset versioning & reproducibility (manifest + SHA-256): https://apxml.com/courses/how-to-build-a-large-language-model/chapter-8-building-managing-large-scale-datasets/dataset-versioning-reproducibility
- Jick Patel — 5 Reproducible ML Habits (content hashes + manifests): https://medium.com/@jickpatel611/5-reproducible-ml-habits-seeds-to-dataset-locks-b73a4d1e3648
- WCR Legal — What happens to the license when you fine-tune a model: https://wcr.legal/fine-tuned-model-license/
- promise.legal — Open-Weight AI License Trap (Llama/Mistral/Gemma terms): https://blog.promise.legal/open-weight-ai-license-trap-startups/
