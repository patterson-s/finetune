"""Tests for the serve stage (finetune/serve/config.py + client.py).

Network-free: ServeClient is given a fake http object, so no socket is opened.
"""
import pytest

from finetune.serve.client import ServeClient, extraction_messages
from finetune.serve.config import build_serve_config


class FakeHTTP:
    """Minimal stand-in for httpx.Client implementing just what ServeClient uses."""

    def __init__(self, *, models=None, chat_reply="done"):
        self._models = models if models is not None else [{"id": "m1"}]
        self._chat_reply = chat_reply
        self.last_path = None
        self.last_json = None

    def get(self, path):
        self.last_path = path
        return _R(200, {"data": self._models})

    def post(self, path, json=None):
        self.last_path = path
        self.last_json = json
        return _R(200, {"choices": [{"message": {"content": self._chat_reply}}]})


class _R:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._payload


def test_build_serve_config_defaults():
    cfg = build_serve_config("llama_cpp", "Qwen/Qwen3-4B-Instruct")
    assert cfg.base_url == "http://127.0.0.1:8080/v1"
    assert cfg.backend == "llama_cpp"
    cfg2 = build_serve_config("ollama", "Qwen/Qwen3-4B-Instruct")
    assert cfg2.port == 11434


def test_build_serve_config_overrides():
    cfg = build_serve_config("llama_cpp", "m", host="0.0.0.0", port=9090)
    assert cfg.base_url == "http://0.0.0.0:9090/v1"


def test_build_serve_config_unknown_backend():
    with pytest.raises(ValueError):
        build_serve_config("nope", "m")


def test_health_check_ok():
    cfg = build_serve_config("llama_cpp", "m")
    c = ServeClient(cfg, http=FakeHTTP())
    hc = c.health_check()
    assert hc["status"] == "ok"
    assert hc["models"] == [{"id": "m1"}]
    assert c._http.last_path == "/models"


def test_health_check_unreachable():
    class Boom:
        def get(self, path):
            raise ConnectionError("refused")

    cfg = build_serve_config("llama_cpp", "m")
    c = ServeClient(cfg, http=Boom())
    assert c.health_check()["status"] == "unreachable"


def test_chat_returns_content_and_sends_model():
    cfg = build_serve_config("llama_cpp", "Qwen/Qwen3-4B-Instruct")
    fake = FakeHTTP(chat_reply='{"level":"BSc"}')
    c = ServeClient(cfg, http=fake)
    out = c.chat(extraction_messages("sys", "bio"))
    assert out == '{"level":"BSc"}'
    assert fake.last_json["model"] == "Qwen/Qwen3-4B-Instruct"
    assert fake.last_json["messages"][0] == {"role": "system", "content": "sys"}


def test_extraction_messages():
    msgs = extraction_messages("S", "U")
    assert msgs == [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "U"},
    ]
