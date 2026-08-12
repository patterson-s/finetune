---
title: "Harness integration: wiring Hermes and Claude Code to a local GGUF model"
date: 2026-08-12
project: small-model-finetuning
dispatch: R1-online
memo: 4-of-6
type: research-memo
status: draft
sources: llama.cpp server README, Ollama OpenAI-compatibility docs, Hermes Agent docs, Claude Code community guides
verification: PARTIAL — flags below marked UNVERIFIED; config keys cited from official docs where noted
---

# Harness integration: wiring Hermes and Claude Code to a local GGUF model

**Date:** 2026-08-12
**Goal:** Expose a fine-tuned small model over an **OpenAI-compatible `/v1` endpoint** so that **both** Hermes Agent (Nous Research) and Claude Code (Anthropic) can call it — served locally via llama.cpp or Ollama on the Jetson/PC, or hosted by any OpenAI-compatible provider.

This memo covers: (1) the two local serving options and their OpenAI-compatible endpoints, (2) the generic hosted option, (3) the exact config keys to wire **Hermes**, (4) the practical wiring for **Claude Code** (which speaks Anthropic, not OpenAI, natively), and (5) a concrete end-to-end wiring diagram with endpoint URLs, model ids, and env/config snippets.

---

## 1. Local serving options (OpenAI-compatible `/v1` endpoint)

Both major local runtimes expose an OpenAI-compatible API, so **no translation shim is needed for Hermes** — it can point directly at either. The only place a shim is required is **Claude Code** (see §4).

### 1a. llama.cpp `llama-server`

llama.cpp ships a C/C++ HTTP server binary, `llama-server`, that natively serves **OpenAI-compatible** routes (`/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`, `/v1/models`) plus **Anthropic Messages API–compatible** chat completions. It supports function calling, JSON-schema grammar, continuous batching, and multi-user parallel decoding.

- **Docs (source):** https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- **Relevant CLI flags (verified against the master README):**
  - `-m, --model <file>` — path to the `.gguf` file
  - `--port <PORT>` — listen port (**default 8080**; env `LLAMA_ARG_PORT`)
  - `--host <HOST>` — bind address (use `0.0.0.0` to expose on the network)
  - `--api-key <KEY>` — optional bearer key (env `LLAMA_API_KEY`); comma-separated list supported
  - `-c, --ctx-size <N>` — context window (env `LLAMA_ARG_CTX_SIZE`)
  - `--n-gpu-layers <N>` / `--gpu-layers` — offload layers to GPU (`-ngl 99` for full)
- **OpenAI-compatible base URL:** `http://<host>:8080/v1`

```bash
# Serve a fine-tuned GGUF on the default port, listening on all interfaces
llama-server \
  -m /models/finetuned-qwen-3b-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -c 8192 \
  --n-gpu-layers 99 \
  --api-key local-key
```

Note: when `--api-key` is not set the server requires none; set one so a remote PC can reach the Jetson without exposing it keyless.

### 1b. Ollama

Ollama exposes the same OpenAI-compatible surface on its default port **11434**. It manages models by **name** (no `.gguf` path), which is convenient once a model is `ollama create`d from a GGUF/Modelfile.

- **Docs (source):** https://docs.ollama.com/api/openai-compatibility
- **OpenAI-compatible base URL:** `http://<host>:11434/v1`
- **API key:** any value, e.g. `"ollama"` — "required but ignored" (per official docs)
- **Endpoints supported:** `/v1/chat/completions`, `/v1/completions`, `/v1/responses` (v0.13.3+), `/v1/models`, `/v1/embeddings`
- **Model id:** the Ollama model name (e.g. `finetuned-qwen3`). To satisfy tools that hardcode OpenAI model names, `ollama cp <name> gpt-3.5-turbo` creates an alias.

```bash
ollama serve                 # listens on 0.0.0.0:11434 by default
ollama create finetuned-qwen3 -f Modelfile   # register a fine-tuned GGUF
curl http://localhost:11434/v1/models
```

---

## 2. Hosted option (generic OpenAI-compatible API)

If the model is hosted on a cloud/vendor OpenAI-compatible endpoint instead of served locally, the integration is identical to the local case — you just change the `base_url` and `api_key` and use the vendor's **model id** (e.g. `meta-llama/Llama-3.1-70B-Instruct-Turbo`). Any OpenAI-compatible gateway (vLLM, Together, Portkey, LiteLLM, Fireworks, etc.) works.

```
Endpoint URL:  https://<vendor>/v1          (or .../v1/ for some providers)
Model id:      <vendor's model identifier>
API key:       <vendor key>
```

Hermes (which is OpenAI-compatible-native) can use this directly. Claude Code needs the Anthropic shim described in §4, which can itself forward to the hosted OpenAI endpoint.

---

## 3. Wiring Hermes Agent to the endpoint

Hermes Agent can point at **any OpenAI-compatible base URL + model id**. Per the **official Hermes docs** (`https://hermes-agent.nousresearch.com/docs/integrations/providers`, "Custom & Self-Hosted LLM Providers"), the config keys live under the `model:` section of `~/.hermes/config.yaml`:

| Key | Purpose |
|-----|---------|
| `model.default` (alias `model.model`) | the **model id** to request |
| `model.provider` | must be `custom` for a custom/self-hosted OpenAI-compatible endpoint |
| `model.base_url` | the OpenAI-compatible base URL (overrides provider routing) |
| `model.api_key` | key for that endpoint (may be left empty for local/unauthenticated) |
| `model.context_length` | optional, useful for local models (e.g. `64000`) |

Per the docs, when `base_url` is set Hermes ignores the provider and calls that endpoint directly, using `api_key` (or falling back to `OPENAI_API_KEY`). Both `hermes model` (interactive picker → "Custom endpoint (self-hosted / VLLM / etc.)") and direct `config.yaml` edits persist to `config.yaml`, which is the source of truth. **IMPORTANT (UNVERIFIED for this Hermes version):** use `hermes config set <key> <val>` to edit rather than hand-editing YAML, to avoid corrupting the live gateway config.

### Hermes config.yaml snippet (placeholders)

```yaml
model:
  default: finetuned-qwen3            # <MODEL_ID> as reported by the server
  provider: custom
  base_url: http://localhost:8080/v1  # llama.cpp default; 11434/v1 for Ollama
  api_key: local-key                  # or leave empty for keyless local serving
  # context_length: 64000             # optional; avoids "context limit" startup error
```

Equivalent CLI form:

```bash
hermes config set model.provider custom
hermes config set model.base_url http://localhost:8080/v1
hermes config set model.default finetuned-qwen3
```

**Verification status:** The `model: {default/model, provider: custom, base_url, api_key, context_length}` schema is confirmed against the current Hermes docs (https://hermes-agent.nousresearch.com/docs/integrations/providers, https://hermes-agent.nousresearch.com/docs/user-guide/configuration). If the running Hermes version on the machine differs from the docs, re-verify by running `hermes model` or reading `~/.hermes/config.yaml`.

> Note: this config controls the **main chat model**. Auxiliary tasks (vision, summarization, embeddings) can be pointed at a separate endpoint via an `auxiliary:` block with the same `base_url`/`api_key`/`model` keys — e.g. `auxiliary.vision.base_url` (per the configuration docs).

---

## 4. Wiring Claude Code to the endpoint

Claude Code (Anthropic) **natively speaks the Anthropic Messages API** (`/v1/messages`), not OpenAI. You **cannot** point `ANTHROPIC_BASE_URL` directly at an OpenAI-only endpoint. Practical paths, in order of preference:

### Path A — Serve an Anthropic-compatible shim / gateway (RECOMMENDED)

Set `ANTHROPIC_BASE_URL` to any server that speaks the **Anthropic Messages API** (`POST /v1/messages`), then run `claude`. Options:

- **llama.cpp `llama-server`** now exposes **Anthropic Messages API–compatible** chat completions directly (per the server README feature list) — so for the fully-local GGUF case you can point Claude Code straight at `llama-server` with **no separate shim**.
- **LiteLLM proxy** — translate Anthropic `messages` to any upstream OpenAI-compatible model: start the proxy on `:4000`, add a model mapping, point Claude Code at `http://localhost:4000`.
- **Community shims** such as `1rgs/claude-code-proxy` (exposes Anthropic-compatible API backed by OpenAI/Gemini/local endpoints, then `ANTHROPIC_BASE_URL=http://localhost:8082 claude`).

Relevant env vars (community-documented; **not officially supported by Anthropic — UNVERIFIED**):

| Env var | Purpose |
|---------|---------|
| `ANTHROPIC_BASE_URL` | base URL of the Anthropic-compatible gateway (e.g. `http://localhost:8080` for llama-server, `http://localhost:4000` for LiteLLM) |
| `ANTHROPIC_AUTH_TOKEN` | gateway key (any value for local) |
| `ANTHROPIC_MODEL` | main model id (often optional if the server maps it) |
| `ANTHROPIC_SMALL_FAST_MODEL` | background/haiku-class model id |
| `ANTHROPIC_API_KEY` | leave empty/unset so Claude Code does not fall back to Anthropic auth |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` | official; disables telemetry |
| `DISABLE_PROMPT_CACHING=1` / `DISABLE_INTERLEAVED_THINKING=1` | community flags for local models |

### Path B — OpenAI-compatible gateway in front (Hermes-style)

If you only have an OpenAI-compatible endpoint (the local llama.cpp/Ollama `/v1` endpoint), route it through a gateway that accepts Anthropic messages and forwards to OpenAI format — **LiteLLM** is the canonical example. This is the same gateway used in Path A; the key difference is whether the upstream is Anthropic-native (A) or OpenAI-native (B).

### Practical wiring for the fully-local GGUF case

For the pure llama.cpp route (Path A, no separate shim):

```bash
# If llama-server is on the Jetson and Claude Code runs on the PC:
export ANTHROPIC_BASE_URL="http://192.168.1.50:8080"   # llama-server (Anthropic-compatible)
export ANTHROPIC_AUTH_TOKEN="local-key"
export ANTHROPIC_API_KEY=""
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
claude
```

> **UNVERIFIED:** Whether Claude Code will accept a custom model name at the llama-server Anthropic endpoint, and the exact llama-server Anthropic route path, should be confirmed by curl-testing `POST /v1/messages` before trusting it. The README lists Anthropic compatibility as a feature, but the concrete routing/model-mapping behavior for Claude Code is not yet validated here.

---

## 5. Concrete wiring diagram

Reference topology: **fine-tuned GGUF served by llama.cpp on the Jetson** (or Ollama), consumed by **Hermes Agent** and **Claude Code** running on the PC (or on the Jetson itself).

```
                              ┌─────────────────────────────────────┐
                              │   LOCAL SERVER  (Jetson or PC)      │
                              │                                     │
   finetuned GGUF  ──►  llama-server  --host 0.0.0.0 --port 8080    │
   finetuned-qwen3 ──►  (or)  ollama serve  (port 11434)            │
                              │                                     │
                              │   /v1/chat/completions  (OpenAI)    │
                              │   /v1/messages          (Anthropic, llama-server only)
                              └──────────────┬──────────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             │                               │                               │
   ┌─────────▼─────────┐          ┌──────────▼──────────┐       ┌────────────▼───────────┐
   │   HERMES AGENT    │          │  CLAUDE CODE        │       │  (optional) LITELLM    │
   │ (OpenAI-native)   │          │ (Anthropic-native)  │       │  proxy :4000           │
   │  base_url=/v1     │          │  ANTHROPIC_BASE_URL │       │  messages→OpenAI trans. │
   └───────────────────┘          └─────────────────────┘       └────────────────────────┘
```

**Endpoint / model-id / auth summary**

| Consumer | Endpoint URL | Model id | Auth |
|----------|--------------|----------|------|
| Hermes (llama.cpp) | `http://<host>:8080/v1` | `finetuned-qwen3` (or the server's model/alias name) | `api_key: local-key` or empty |
| Hermes (Ollama) | `http://<host>:11434/v1` | Ollama model name, e.g. `finetuned-qwen3` (or `gpt-3.5-turbo` alias) | `api_key: ollama` (ignored) |
| Claude Code (llama.cpp, Path A) | `http://<host>:8080` (Anthropic endpoint) | via `ANTHROPIC_MODEL` | `ANTHROPIC_AUTH_TOKEN=local-key` |
| Claude Code (Ollama, Path B) | `http://localhost:4000` (LiteLLM) | `ANTHROPIC_MODEL` = mapped name | `ANTHROPIC_AUTH_TOKEN=sk-1234` |

Where `<host>` is:
- `localhost` / `127.0.0.1` if both the server and the harness run on the same machine;
- the Jetson's LAN IP (e.g. `192.168.1.50`) when the harness runs on a separate PC. Ensure the server binds `--host 0.0.0.0` (llama.cpp) so it is reachable.

### Example full setup (llama.cpp on Jetson → both harnesses on PC)

```bash
# ===== On the JETSON =====
llama-server -m /models/finetuned-qwen3-q4_k_m.gguf \
  --host 0.0.0.0 --port 8080 -c 8192 --n-gpu-layers 99 --api-key local-key

# ===== On the PC =====
# --- Hermes (~/.hermes/config.yaml, or via `hermes config set`) ---
#   model:
#     default: finetuned-qwen3
#     provider: custom
#     base_url: http://192.168.1.50:8080/v1
#     api_key: local-key

# --- Claude Code (env) ---
export ANTHROPIC_BASE_URL="http://192.168.1.50:8080"
export ANTHROPIC_AUTH_TOKEN="local-key"
export ANTHROPIC_MODEL="finetuned-qwen3"
export ANTHROPIC_API_KEY=""
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
claude
```

---

## Sources (cited)

1. llama.cpp HTTP server README (OpenAI-compatible `/v1` endpoints; `--port`, `--host`, `--api-key`, Anthropic Messages API compatibility): https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
2. Ollama — OpenAI compatibility (base URL `http://localhost:11434/v1`, `api_key` "ollama" required-but-ignored, supported endpoints, `ollama cp` model aliasing): https://docs.ollama.com/api/openai-compatibility
3. Hermes Agent — AI Providers / Custom & Self-Hosted LLM Providers (`model.default`/`model.model`, `provider: custom`, `base_url`, `api_key`, `context_length`; `hermes model`; `OPENAI_BASE_URL` legacy): https://hermes-agent.nousresearch.com/docs/integrations/providers
4. Hermes Agent — Configuration (`base_url` precedence, `auxiliary:` universal config pattern, `OPENAI_API_KEY` fallback): https://hermes-agent.nousresearch.com/docs/user-guide/configuration
5. Claude Code + local LLMs — Anthropic vs OpenAI protocol, `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / proxy necessity (community): https://medium.com/@michael.hannecke/connecting-claude-code-to-local-llms-two-practical-approaches-faa07f474b0f
6. LM Studio — Use LM Studio models in Claude Code (`ANTHROPIC_BASE_URL=http://localhost:1234`, `ANTHROPIC_AUTH_TOKEN=lmstudio`): https://lmstudio.ai/blog/claudecode
7. `1rgs/claude-code-proxy` — Anthropic-compatible proxy for OpenAI/Gemini/local models (`ANTHROPIC_BASE_URL=http://localhost:8082 claude`): https://github.com/1rgs/claude-code-proxy
8. Morph — Use a custom model with Claude Code (LiteLLM proxy pattern, `ANTHROPIC_MODEL` / `ANTHROPIC_SMALL_FAST_MODEL`): https://www.morphllm.com/use-different-llm-claude-code

## Verification status / flags

- ✅ **Hermes config keys** (`model.default/model`, `provider: custom`, `base_url`, `api_key`) — confirmed against current official Hermes docs. Re-verify against the **running** Hermes version on the machine (`hermes model` / read `~/.hermes/config.yaml`).
- ✅ **Ollama OpenAI endpoint** (`:11434/v1`, `api_key` ignored) — confirmed against official Ollama docs.
- ✅ **llama.cpp server flags** (`--port` default 8080, `--host`, `--api-key`, `--ctx-size`) and OpenAI `/v1` routes — confirmed against server README.
- ⚠️ **llama.cpp Anthropic Messages API route for Claude Code** — README lists the capability; exact routing/model-mapping for Claude Code is UNVERIFIED. Curl-test `POST /v1/messages` before relying on it.
- ⚠️ **Claude Code env vars** (`ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `DISABLE_INTERLEAVED_THINKING`) — community-documented, not officially supported by Anthropic. UNVERIFIED against a real local server.
- ⚠️ **LiteLLM proxy mapping** — standard pattern but not locally tested here.
