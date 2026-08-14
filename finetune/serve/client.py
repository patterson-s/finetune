"""serve/client.py — a small OpenAI-compatible chat client for the local endpoint.

The llama.cpp / Ollama servers both expose an OpenAI-compatible /v1/chat/completions.
This client is the thin, tested surface that the serve stage uses to (a) health-check
the endpoint and (b) send an extraction prompt, so downstream wiring (Hermes, Claude
Code) talks to the same contract. httpx is imported lazily so tests can inject a
fake transport and stay network-free.
"""
from __future__ import annotations

from typing import Any

from .config import ServeConfig

# Any reachable server answers /v1/models; used by health_check.
HEALTH_OK_STATUS = "ok"


class ServeClient:
    def __init__(self, cfg: ServeConfig, *, http=None) -> None:
        self.cfg = cfg
        self._http = http  # injectable for tests; lazily defaults to httpx

    def _client(self):
        if self._http is not None:
            return self._http
        import httpx  # lazy

        self._http = httpx.Client(base_url=self.cfg.base_url, timeout=30.0)
        return self._http

    def health_check(self) -> dict[str, Any]:
        """GET /v1/models; return {'status': 'ok'|'unreachable', 'models': [...]}."""
        try:
            r = self._client().get("/models")
            r.raise_for_status()
            models = r.json().get("data", [])
            return {"status": HEALTH_OK_STATUS, "models": models}
        except Exception as e:  # noqa: BLE001 - report any failure as unreachable
            return {"status": "unreachable", "error": str(e)}

    def chat(self, messages: list[dict[str, str]], *, max_tokens: int = 512, temperature: float = 0.1, **kw: Any) -> str:
        """POST /v1/chat/completions; return the assistant text content."""
        body = {
            "model": self.cfg.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        body.update(kw)
        r = self._client().post("/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]


def extraction_messages(system: str, user: str) -> list[dict[str, str]]:
    """Convenience: build the chat messages for an extraction request."""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
