# Adaption Labs integration for model finetuning

**Memo date:** 2026-08-12
**Type:** Online research memo (Memo 1 of 6, R1 online research dispatch — small-model finetuning pipelines project)
**Purpose:** Document what Adaption Labs is, how to access it with free credits, its public API and SDK, pricing/credits mechanics, a copy-pasteable integration example, and how Adaption's dataset format maps onto our existing `adaption_test_dataset_v1.csv` (columns `prompt`, `context`, `output`).
**Status note:** Facts below are verified against live pages via web research. Anything not found on a public page is explicitly marked **unverified**. No pricing numbers are invented.

---

## 1. What Adaption Labs is

**Adaption Labs** (domain: `adaptionlabs.ai`) is a hosted AI company building "adaptive intelligence that continually learns" — a bet against brute-force model scaling, instead favoring efficient, continually-learning AI that adapts to a user's specific industry, language, or domain. It was co-founded by **Sara Hooker** (formerly VP of AI research at Cohere) and **Sudip Roy** (former Cohere leader, Google DeepMind veteran). In February 2026 Adaption Labs announced a **$50M seed round** to pursue this "learn-on-the-fly" approach. [Fortune, Feb 4 2026 — https://fortune.com/2026/02/04/adaption-labs-50-million-seed-funding-emergence-captial-sara-hooker-sudip-roy-ai-models-that-learn-on-the-fly/](https://fortune.com/2026/02/04/adaption-labs-50-million-seed-funding-emergence-captial-sara-hooker-sudip-roy-ai-models-that-learn-on-the-fly/) | [Homepage — https://adaptionlabs.ai/](https://adaptionlabs.ai/)

Adaption's platform is organized around **three pillars** ([homepage](https://adaptionlabs.ai/)):

1. **Adaptive Data** — the first product (early access opened Feb 24, 2026). A data-optimization platform that treats datasets as a "living, shapeable space," analyzing structure, adapting examples, evaluating quality, and exporting model-ready data. Adaption reports an **average 82% increase in data quality** across early deployments and support for **242 languages** and 8M+ data artifacts processed. [https://adaptionlabs.ai/blog/adaption-launches-adaptive-data-beta](https://adaptionlabs.ai/blog/adaption-launches-adaptive-data-beta) | [https://adaptionlabs.ai/adaptive-data](https://adaptionlabs.ai/adaptive-data)
2. **Adaptive Intelligence** — embodied by **AutoScientist** (launched May 13, 2026). A system that automates the full research loop behind model training/alignment: it co-optimizes data and model-training recipes until quality converges on your objective, and lets you download a trained checkpoint (LoRA or full). Free for the first 30 days after launch per TechCrunch. [https://adaptionlabs.ai/blog/autoscientist](https://adaptionlabs.ai/blog/autoscientist) | [TechCrunch, May 13 2026 — https://techcrunch.com/2026/05/13/adaption-aims-big-with-autoscientist-an-ai-tool-that-helps-models-train-themselves/](https://techcrunch.com/2026/05/13/adaption-aims-big-with-autoscientist-an-ai-tool-that-helps-models-train-themselves/)
3. **Adaptive Interfaces** — an innovation hub re-imagining the human–AI interface; waitlist-only. [https://adaptionlabs.ai/learn-more](https://adaptionlabs.ai/learn-more)

**Fine-tuning relation:** Adaption is not primarily a raw GPU fine-tuning host; its core value is *data shaping* (Adaptive Data) feeding into training. Actual model training happens two ways:
- **AutoScientist** runs the training loop and returns a downloadable checkpoint. [https://docs.adaptionlabs.ai/guides/autoscientist-api](https://docs.adaptionlabs.ai/guides/autoscientist-api)
- **Together AI partnership** (announced Apr 30, 2026): users connect their Together AI account and execute Together Fine-Tuning directly on an Adapted dataset (supports LoRA and full fine-tuning, large open models up to 100B+ params). [https://www.together.ai/blog/announcing-together-ai-and-adaption-partnership](https://www.together.ai/blog/announcing-together-ai-and-adaption-partnership)

### The free-credit / 'Adaptive Data' programs

Important clarification: **"Adaptive Data" is the product name**, not the credit program. The free-credit access comes through two separate programs:

- **Adaption for Startups** — gives early-stage teams access to the **Adaptive Data Plus plan and free credits** so they can build without a cost barrier. Applications are reviewed on a rolling basis, open worldwide, at **https://adaptionlabs.ai/adaption-for-startups/apply**. [https://adaptionlabs.ai/blog/adaption-for-startups](https://adaptionlabs.ai/blog/adaption-for-startups) | [https://adaptionlabs.ai/adaption-for-startups](https://adaptionlabs.ai/adaption-for-startups) — *the specific credit amount is **unverified** (no public number found).*
- **AutoScientist Challenge** — a $60K-prize hackathon (Summer 2026). "What We Provide: 1. **1000 in credits** for data adaptation and free compute for AutoScientist." [https://adaptionlabs.ai/blog/autoscientist-challenge](https://adaptionlabs.ai/blog/autoscientist-challenge) — *the "1000 credits" figure is verified here, but only in the context of that challenge prize package.*

Since Scott already has Adaption free credits, the likely route is either a granted Startup-Program credit balance or challenge credits. **The exact dollar/credit value of his balance is unverified** and should be confirmed in the Adaption app (Settings/credits).

### Sign up and authenticate

- **Sign in / sign up:** https://adaptionlabs.ai/app/auth (the "Login" and "Now onboarding" links across the site all point here). [https://adaptionlabs.ai/](https://adaptionlabs.ai/) | [https://adaptionlabs.ai/adaption-for-startups](https://adaptionlabs.ai/adaption-for-startups)
- **API key creation:** sign in → **Settings** → **API keys** tab (**https://adaptionlabs.ai/app/settings?tab=api_keys**) → create a key → copy it once (it is shown only once). Keys are prefixed `pt_live_...`. [https://docs.adaptionlabs.ai/introduction/create-api-keys](https://docs.adaptionlabs.ai/introduction/create-api-keys)
- **SDK install:** `pip install adaption` (Python 3.9+; package `adaption` on PyPI). [https://pypi.org/project/adaption/](https://pypi.org/project/adaption/) | [https://docs.adaptionlabs.ai/api/python](https://docs.adaptionlabs.ai/api/python)
- **SDK auth:** `client = Adaption(api_key="pt_live_...")` or set env var `ADAPTION_API_KEY` and construct without args. [https://docs.adaptionlabs.ai/introduction/getting-started](https://docs.adaptionlabs.ai/introduction/getting-started)
- **HTTP auth:** the SDK sends the key as an `Authorization: Bearer <key>` header (this is the standard Stainless-generated pattern and is how the docs' `api_key` maps to requests; the exact header string is **unverified** on the public docs). For HTTP you can also set `ADAPTION_BASE_URL` to override the SDK's default base URL. [https://docs.adaptionlabs.ai/api/python](https://docs.adaptionlabs.ai/api/python)

---

## 2. The API

Adaption ships a **documented public REST API and a generated Python SDK**. Official docs: **https://docs.adaptionlabs.ai/** (docs home) and **https://docs.adaptionlabs.ai/api** (API reference). SDK source: **https://github.com/Numi-Labs/adaption-python** (generated by Stainless).

### Exact REST endpoints (from the API reference)

**Datasets** ([https://docs.adaptionlabs.ai/api](https://docs.adaptionlabs.ai/api)):
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/datasets` | Create a dataset (file upload presigned flow, Hugging Face, or Kaggle) |
| GET | `/api/v1/datasets/{dataset_id}` | Get a dataset by ID |
| GET | `/api/v1/datasets` | List datasets (paged) |
| GET | `/api/v1/datasets/{dataset_id}/status` | Get processing status (e.g. `row_count`) |
| GET | `/api/v1/datasets/{dataset_id}/download` | Download the processed dataset (presigned S3 URL) |
| POST | `/api/v1/datasets/{dataset_id}/publish` | Publish dataset to an external platform |
| POST | `/api/v1/datasets/{dataset_id}/run` | Start an augmentation run, or `estimate=True` to quote cost |
| GET | `/api/v1/datasets/{dataset_id}/evaluation` | Get evaluation results |

**DatasetsUpload** (low-level presigned flow):
| POST | `/api/v1/datasets/upload/initiate` | Initiate an upload (returns presigned URL + instructions) |
| POST | `/api/v1/datasets/upload/complete` | Complete an upload and trigger processing |
| POST | `/api/v1/datasets/{dataset_id}/upload/complete` | Complete a file upload and trigger processing |

**AutoScientist (training):**
| POST | `/api/v1/autoscientist` | Create an AutoScientist (training) run |
| POST | `/api/v1/autoscientist/recommend-hyperparams` | Recommend hyperparameters |
| GET | `/api/v1/autoscientist/{experiment_id}` | Retrieve a training run |
| GET | `/api/v1/autoscientist` | List training runs |
| POST | `/api/v1/autoscientist/{experiment_id}/cancel` | Cancel a training run |
| GET | `/api/v1/autoscientist/{experiment_id}/download` | Download the best trained model checkpoint |
| GET | `/api/v1/autoscientist/models` | List available base models for training |
| GET | `/api/v1/training-models` | **Deprecated** alias |

> **Base URL:** The docs list paths as `/api/v1/...` but do not state the host. The SDK's default base URL is **unverified** on the public pages; the safest approach is to use the Python SDK, which sets the base URL for you. If you hand-write curl, prefix the endpoints with `https://api.adaptionlabs.ai` (**unverified**) and confirm against your SDK's `base_url` or a `network` log.

### Dataset upload format

- **Supported file extensions:** `.csv`, `.json`, `.jsonl`, `.parquet`. Or import directly from **Hugging Face** (`create_from_huggingface`) and **Kaggle** (`create_from_kaggle`, requires registered Kaggle credentials in API-key settings). [https://docs.adaptionlabs.ai/introduction/getting-started](https://docs.adaptionlabs.ai/introduction/getting-started) | [https://docs.adaptionlabs.ai/](https://docs.adaptionlabs.ai/)
- **Column roles** (the `column_mapping` on `datasets.run` maps your *source columns* to these semantic roles):
  - `prompt` — **required** in prompt mode. The prompt/instruction field.
  - `completion` — optional in prompt mode. The completion/response field.
  - `chat` — exclusive chat mode; when set, no other mapping fields allowed.
  - `context` — optional **list** of columns to include as context. Required (≥1) in universal-prompt mode.
  - `universal_prompt` — dataset-wide instruction folded into every row (no per-row prompt).
  - `image` — multimodal context column (disqualifies the dataset from finetuning).
  [https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run)

### How to invoke a finetune / training run

**Step 1 — Ingest:** `upload_file("training_data.csv")` (or `create_from_huggingface` / `create_from_kaggle`). Returns a `dataset_id`. Wait for file processing: poll `datasets.get_status(dataset_id)` until `row_count is not None`.

**Step 2 — Adapt (data run):** `datasets.run(dataset_id, column_mapping={...}, job_specification={"max_rows": N}, estimate=True)` to quote cost first, then re-run without `estimate=True` to start. Returns `run_id`, `estimated_minutes`, `estimated_credits_consumed`. This is the Adaptive Data augmentation job (dedup, prompt rephrasing, reasoning traces, brand controls, etc.).

**Step 3 — Wait:** `datasets.wait_for_completion(dataset_id, timeout=...)` returns status `succeeded`/`failed` (or use `get_status` to poll yourself).

**Step 4 — Train the model (AutoScientist):**
```python
run = client.autoscientist.create(
    dataset_id=dataset_id,
    max_iterations=3,          # 1–10
    target_win_rate=0.7,       # stops early once reached
    model="...",               # id from training_models.list()/autoscientist.models
    training_type="lora",      # or "full"
    augmentation_domain_rows=...,
    augmentation_general_rows=...,
)
run = client.autoscientist.wait_for_completion(run.id)  # statuses: pending/running/succeeded/failed/cancelled
# download best checkpoint:
client.autoscientist.with_streaming_response.download(run.id).stream_to_file("best-checkpoint.tgz")
```
Training is supervised SFT (`lora` default or `full`). The download is a tar archive containing `adapter_config.json`, `adapter_model.safetensors`, `tokenizer.json`, `trainer_state.json`. Alternative training path: connect a **Together AI** account and run fine-tuning on the adapted dataset there (LoRA + full). [https://docs.adaptionlabs.ai/guides/autoscientist-api](https://docs.adaptionlabs.ai/guides/autoscientist-api) | [https://www.together.ai/blog/announcing-together-ai-and-adaption-partnership](https://www.together.ai/blog/announcing-together-ai-and-adaption-partnership)

### How to poll status

- **Dataset processing / adaptation:** `datasets.get_status(dataset_id)` (returns `row_count`), or the convenience `datasets.wait_for_completion(dataset_id, timeout=600)` which polls with exponential backoff **2s → 4s → 8s → … up to 30s**, default timeout one hour. On timeout raises `DatasetTimeout` (carries last status). [https://docs.adaptionlabs.ai/introduction/getting-started](https://docs.adaptionlabs.ai/introduction/getting-started)
- **Training (AutoScientist):** statuses `pending`, `running`, `succeeded`, `failed`, `cancelled`. `autoscientist.wait_for_completion(run.id)` backs off **10s → 60s**, default timeout 4 hours. Between polls call `autoscientist.get(run.id)` to read `iterations_completed`, `max_iterations`, `best_win_rate`. [https://docs.adaptionlabs.ai/guides/autoscientist-api](https://docs.adaptionlabs.ai/guides/autoscientist-api)

---

## 3. Pricing and how credits are consumed

- **No public pricing page was found** — Adaption does not publish a per-credit or plan price on any page we could verify. All absolute prices are therefore **unverified**. The verified facts about credits are structural:
- **Credits are consumed per run / per output row.** The `datasets.run` response includes `estimated_credits_consumed` (and `estimated_minutes`). Call `datasets.run(..., estimate=True)` to get a cost quote *without* starting the run — this is the sanctioned way to know your cost before committing. [https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run) | [https://docs.adaptionlabs.ai/guides/processing-large-datasets](https://docs.adaptionlabs.ai/guides/processing-large-datasets)
- **Row-volume billing:** for recipes that expand rows (e.g. `language_expansion`), "Credits are billed on the expanded output row count" (`sample_rate` 0.01–1 of input expanded per target). [https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run)
- **The one concrete rate found (multimodal):** when an `image` column is mapped *and* listed in context columns, "output rows are billed at **10 credits per 100 rows** (1–100 rows cost 10 credits)," exposed as `multimodalPricingApplied: true` and `creditMultiplier: 10`. This is a multimodal-specific rate, not the text rate. [https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run)
- **Free credits:** the Startup Program grants free credits (amount **unverified**); the AutoScientist Challenge provides "**1000 in credits** for data adaptation and free compute for AutoScientist" (verified, challenge-specific). [https://adaptionlabs.ai/blog/adaption-for-startups](https://adaptionlabs.ai/blog/adaption-for-startups) | [https://adaptionlabs.ai/blog/autoscientist-challenge](https://adaptionlabs.ai/blog/autoscientist-challenge)
- **Cost-control workflow (recommended for us):** use `job_specification={"max_rows": N}` to subsample for a pilot, combine with `estimate=True` to get a quote, then run the full corpus only once the pilot is validated. [https://docs.adaptionlabs.ai/guides/processing-large-datasets](https://docs.adaptionlabs.ai/guides/processing-large-datasets)

---

## 4. Copy-pasteable example (Python SDK — recommended)

This is the documented end-to-end lifecycle (install → ingest → adapt → wait → export). Put your key in `ADAPTION_API_KEY` or pass `api_key=` directly.

```bash
pip install adaption
export ADAPTION_API_KEY="pt_live_..."
```

```python
import os, time
from adaption import Adaption, DatasetTimeout

client = Adaption(api_key=os.environ["ADAPTION_API_KEY"])

# 1) Ingest
result = client.datasets.upload_file("training_data.csv")
dataset_id = result.dataset_id
print("dataset_id:", dataset_id)

# 2) Wait for file processing
while True:
    status = client.datasets.get_status(dataset_id)
    if status.row_count is not None:
        break
    time.sleep(2)

# 3) Quote cost WITHOUT starting (recommended first)
quote = client.datasets.run(
    dataset_id,
    column_mapping={"prompt": "instruction", "completion": "response"},
    job_specification={"max_rows": 500},   # subsample for a pilot
    estimate=True,
)
print(f"Pilot would cost ~{quote.estimated_credits_consumed} credits")

# 4) Start the adaptation run
run = client.datasets.run(
    dataset_id,
    column_mapping={"prompt": "instruction", "completion": "response"},
    job_specification={"max_rows": 500},
)
print(f"Run started: {run.run_id}, ~{run.estimated_minutes} min, "
      f"{run.estimated_credits_consumed} credits")

# 5) Wait for completion (polling handled internally, 2s->30s backoff)
try:
    final = client.datasets.wait_for_completion(dataset_id, timeout=1800)
    print("Finished:", final.status)          # "succeeded" | "failed"
except DatasetTimeout as e:
    print("Timed out:", e.last_status)

# 6) Export adapted dataset
url = client.datasets.download(dataset_id)    # presigned S3 URL
print("Download:", url)
```

**Then train a model (AutoScientist):**
```python
run = client.autoscientist.create(
    dataset_id=dataset_id,
    max_iterations=3,
    target_win_rate=0.7,
    training_type="lora",
)
run = client.autoscientist.wait_for_completion(run.id)   # statuses: pending/running/succeeded/failed/cancelled
if run.status == "succeeded":
    with client.autoscientist.with_streaming_response.download(run.id) as resp:
        resp.stream_to_file("best-checkpoint.tgz")   # tar: adapter_config.json, adapter_model.safetensors, ...
```

**Raw curl skeleton (endpoint paths from the API reference; base host `https://api.adaptionlabs.ai` is unverified — use the SDK unless you confirm it):**
```bash
# Quote cost (estimate=true, no run started)
curl -X POST "https://api.adaptionlabs.ai/api/v1/datasets/DATASET_ID/run" \
  -H "Authorization: Bearer $ADAPTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"column_mapping":{"prompt":"instruction","completion":"response"},"estimate":true}'

# Poll status
curl "https://api.adaptionlabs.ai/api/v1/datasets/DATASET_ID/status" \
  -H "Authorization: Bearer $ADAPTION_API_KEY"
```

---

## 5. Verified URLs (all cited above)

**Product / site**
- Homepage: https://adaptionlabs.ai/
- Sign in / onboarding: https://adaptionlabs.ai/app/auth
- API key settings: https://adaptionlabs.ai/app/settings?tab=api_keys
- Adaptive Data product page: https://adaptionlabs.ai/adaptive-data

**Startups / free credits**
- Startups program (landing): https://adaptionlabs.ai/adaption-for-startups
- Startups program (apply): https://adaptionlabs.ai/adaption-for-startups/apply
- Startups blog announcement (Mar 31 2026): https://adaptionlabs.ai/blog/adaption-for-startups

**Blog / launch posts**
- Adaptive Data beta (Feb 24 2026): https://adaptionlabs.ai/blog/adaption-launches-adaptive-data-beta
- Adaptive Data API + Python SDK (Apr 09 2026): https://adaptionlabs.ai/blog/adaptive-data-api-and-python-sdk
- AutoScientist (May 13 2026): https://adaptionlabs.ai/blog/autoscientist
- AutoScientist Challenge ($60K / "1000 in credits", Jun 05 2026): https://adaptionlabs.ai/blog/autoscientist-challenge

**Documentation / API**
- Docs home: https://docs.adaptionlabs.ai/
- Getting started: https://docs.adaptionlabs.ai/introduction/getting-started
- Create API keys: https://docs.adaptionlabs.ai/introduction/create-api-keys
- API reference (endpoint list): https://docs.adaptionlabs.ai/api
- Run endpoint reference: https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/run
- AutoScientist API guide: https://docs.adaptionlabs.ai/guides/autoscientist-api
- Processing large datasets (max_rows + estimate): https://docs.adaptionlabs.ai/guides/processing-large-datasets
- Python SDK / PyPI: https://pypi.org/project/adaption/
- SDK source: https://github.com/Numi-Labs/adaption-python

**Third-party**
- Together AI partnership (Apr 30 2026): https://www.together.ai/blog/announcing-together-ai-and-adaption-partnership
- TechCrunch on AutoScientist (May 13 2026): https://techcrunch.com/2026/05/13/adaption-aims-big-with-autoscientist-an-ai-tool-that-helps-models-train-themselves/
- Fortune on $50M seed (Feb 4 2026): https://fortune.com/2026/02/04/adaption-labs-50-million-seed-funding-emergence-captial-sara-hooker-sudip-roy-ai-models-that-learn-on-the-fly/

---

## 6. Format-mapping note: our `prompt` / `context` / `output` CSV vs. Adaption

We already hold a seed file **`adaption_test_dataset_v1.csv`** (100 rows; on the PC at `pydeal_type/runs/USA_01/prompt/aggressor_05/output/`), with three columns: **`prompt`**, **`context`**, **`output`**.

**Good news: this maps cleanly and directly onto Adaption's upload format.** Adaption accepts `.csv` natively and its `column_mapping` semantics have exact counterparts for all three of our columns:

| Our column | Adaption role | Mapping |
|------------|---------------|---------|
| `prompt` | `prompt` (required, prompt-mode) | `"prompt": "prompt"` |
| `context` | `context` (optional list of columns) | `"context": ["context"]` |
| `output` | `completion` (optional response field) | `"completion": "output"` |

So the run call for our seed file is:

```python
client.datasets.run(
    dataset_id,
    column_mapping={
        "prompt": "prompt",
        "context": ["context"],
        "completion": "output",
    },
)
```

**Key points and caveats:**
- Adaption's `context` role is a **list**, so a single context column is passed as `["context"]` (our CSV has one context column; if we later have multiple, they all go in the list).
- `completion` maps to our `output` column — exactly the "answer/target" Adaption augments and evaluates against.
- Because we run in **prompt mode** (`prompt` + optional `completion` + optional `context`), our format is fully supported; no need to convert to chat mode.
- If we ever want to use the **raw training path** (skip data adaptation and train directly on the file as-is), `processing_mode="raw"` accepts the same prompt/completion mapping. [https://docs.adaptionlabs.ai/guides/autoscientist-api](https://docs.adaptionlabs.ai/guides/autoscientist-api)
- **For a 100-row seed**, run a pilot with `job_specification={"max_rows": 100}` and `estimate=True` first to learn the actual credit cost from our own file, since no public text pricing exists. [https://docs.adaptionlabs.ai/guides/processing-large-datasets](https://docs.adaptionlabs.ai/guides/processing-large-datasets)

---

## Key takeaways for the pipeline

1. Adaption Labs = adaptive data-shaping platform (Adaptive Data) + auto-training (AutoScientist) + optional Together AI fine-tuning. Fully scriptable via a documented REST API and the `adaption` Python SDK (Stainless-generated).
2. Free credits: via the **Adaption for Startups** program (Adaptive Data Plus + free credits, amount unverified) or challenge credits ("1000 in credits" verified for the AutoScientist Challenge). Confirm the live balance in the app.
3. Credits are per-run / per-output-row, quoted via `estimate=True` before committing. Only concrete published rate: multimodal at 10 credits/100 rows. Text pricing is **unverified** — always use `estimate=True`.
4. Our `prompt`/`context`/`output` CSV maps 1:1 onto `column_mapping={"prompt":..., "context":[...], "completion":...}`. No reformatting needed.
5. A documented public API **is** available (this is not an undocumented-API situation); use the Python SDK and the endpoint table in §2.
