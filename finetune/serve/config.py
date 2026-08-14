"""serve/config.py — build a ServeConfig from configs/providers.yaml.

Defines how the finetuned model is exposed locally (which backend, on which
host:port, under which model name), matching the provider defaults documented
in providers.yaml (llama_cpp port 8080, ollama port 11434).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..spec import REPO_ROOT

PROVIDERS_PATH = REPO_ROOT / "configs" / "providers.yaml"

# Backend -> (host, default_port). The OpenAI-compatible /v1 base URL is derived.
BACKEND_DEFAULTS: dict[str, dict] = {
    "llama_cpp": {"host": "127.0.0.1", "port": 8080, "endpoint": "/v1"},
    "ollama": {"host": "127.0.0.1", "port": 11434, "endpoint": "/v1"},
}


@dataclass
class ServeConfig:
    """How/where to expose a finetuned model locally."""

    backend: str
    model: str
    host: str = "127.0.0.1"
    port: int = 8080
    endpoint: str = "/v1"
    api_key: str = ""  # llama.cpp/ollama usually need none; kept for parity
    extra: dict = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}{self.endpoint}"


def _load_providers(path: str | Path = PROVIDERS_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def build_serve_config(
    backend: str,
    model: str,
    *,
    host: str | None = None,
    port: int | None = None,
    providers_path: str | Path = PROVIDERS_PATH,
) -> ServeConfig:
    """Build a ServeConfig for a backend, defaulting host/port from providers.yaml.

    Raises ValueError for an unknown backend (misspelling would otherwise silently
    point at port 8080 and confuse a downstream health check).
    """
    defaults = BACKEND_DEFAULTS.get(backend)
    if defaults is None:
        raise ValueError(f"Unknown serve backend: {backend!r} (expected {sorted(BACKEND_DEFAULTS)})")

    # provider notes (e.g. llama_cpp port, ollama port) can override the defaults
    prov = _load_providers(providers_path).get("providers", {}).get(backend, {})
    return ServeConfig(
        backend=backend,
        model=model,
        host=host or defaults["host"],
        port=port or defaults["port"],
        endpoint=defaults["endpoint"],
        extra={"provider_notes": prov.get("notes", "")},
    )
