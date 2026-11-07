import io
import json

import pytest

from runbookrag.generator import OllamaGenerator, generator_from_env
from runbookrag.store import SQLiteStore


def test_store_stats_and_feedback(tmp_path):
    store = SQLiteStore(tmp_path / "db" / "q.db")
    assert store.stats()["queries"] == 0 and store.stats()["helpful_rate"] is None
    a = store.log_query("disk full", "hybrid", "disk-full#symptoms", True, 1.5)
    store.log_query("zzz", "bm25", None, False, 0.5)
    assert store.add_feedback(a, True)
    assert not store.add_feedback("missing", False)
    s = store.stats()
    assert s["queries"] == 2 and s["answered_rate"] == 0.5 and s["avg_latency_ms"] == 1.0
    assert s["helpful_rate"] == 1.0 and s["top_sections"] == [{"id": "disk-full#symptoms", "count": 1}]


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_ollama_generator_posts_prompt():
    seen = {}

    def opener(req, timeout):
        seen["url"], seen["body"] = req.full_url, json.loads(req.data)
        return FakeResponse(json.dumps({"response": " Restart the service [a#b]. "}).encode())

    gen = OllamaGenerator("http://ollama:11434/", model="m", opener=opener)
    hits = [{"id": "a#b", "title": "T", "section": "S", "text": "x"}]
    assert gen.generate("q?", hits) == "Restart the service [a#b]."
    assert seen["url"] == "http://ollama:11434/api/generate"
    assert seen["body"]["model"] == "m" and "[a#b]" in seen["body"]["prompt"]


def test_ollama_generator_empty_response():
    gen = OllamaGenerator("http://x", opener=lambda req, timeout: FakeResponse(b'{"response": ""}'))
    with pytest.raises(RuntimeError):
        gen.generate("q", [])


def test_generator_from_env(monkeypatch):
    monkeypatch.delenv("RUNBOOKRAG_OLLAMA_URL", raising=False)
    assert generator_from_env() is None
    monkeypatch.setenv("RUNBOOKRAG_OLLAMA_URL", "http://localhost:11434")
    monkeypatch.setenv("RUNBOOKRAG_OLLAMA_MODEL", "qwen2.5:0.5b")
    gen = generator_from_env()
    assert gen.base_url == "http://localhost:11434" and gen.model == "qwen2.5:0.5b"
