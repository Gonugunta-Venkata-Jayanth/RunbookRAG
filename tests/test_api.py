import pytest
from fastapi.testclient import TestClient

from api import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNBOOKRAG_INDEX", str(tmp_path / "index.json"))  # built on start-up
    monkeypatch.setenv("RUNBOOKRAG_DB", str(tmp_path / "q.db"))
    monkeypatch.delenv("RUNBOOKRAG_OLLAMA_URL", raising=False)
    with TestClient(main.app) as c:
        yield c


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["chunks"] == 88 and body["generator"] is False


def test_search(client):
    body = client.get("/api/search", params={"q": "nginx 502", "mode": "bm25", "k": 3}).json()
    assert len(body["hits"]) == 3 and body["hits"][0]["doc"] == "nginx-502-bad-gateway"


def test_search_validation(client):
    assert client.get("/api/search", params={"q": "disk", "mode": "nope"}).status_code == 422
    assert client.get("/api/search", params={"q": "x"}).status_code == 422


def test_ask_feedback_and_stats(client):
    r = client.post("/api/ask", json={"question": "postgres too many clients already"}).json()
    assert r["answer"] and r["citations"][0].startswith("postgres-too-many-connections#")
    assert r["generated"] is None and r["latency_ms"] >= 0
    assert client.post("/api/feedback", json={"query_id": r["query_id"], "helpful": True}).json() == {"ok": True}
    assert client.post("/api/feedback", json={"query_id": "nope", "helpful": True}).status_code == 404
    stats = client.get("/api/stats").json()
    assert stats["queries"] == 1 and stats["helpful_rate"] == 1.0


def test_ask_with_generator(client):
    class Gen:
        def generate(self, question, hits):
            return f"generated from {hits[0]['id']}"

    class Broken:
        def generate(self, question, hits):
            raise RuntimeError("model offline")

    main.app.state.generator = Gen()
    r = client.post("/api/ask", json={"question": "dns resolution failure", "generate": True}).json()
    assert r["generated"].startswith("generated from dns-resolution-failure#")
    main.app.state.generator = Broken()
    r = client.post("/api/ask", json={"question": "dns resolution failure", "generate": True}).json()
    assert r["generated"] is None and r["generator_error"] == "model offline" and r["answer"]


def test_ask_validation(client):
    assert client.post("/api/ask", json={"question": "hi"}).status_code == 422
    assert client.post("/api/ask", json={"question": "disk full", "mode": "x"}).status_code == 422


def test_runbooks(client):
    books = client.get("/api/runbooks").json()["runbooks"]
    assert len(books) == 22 and books[0]["sections"]
    doc = client.get("/api/runbooks/oom-killer").json()
    assert doc["title"].startswith("Process killed") and len(doc["sections"]) == 4
    assert client.get("/api/runbooks/missing").status_code == 404


def test_frontend_assets(client):
    assert "RunbookRAG" in client.get("/").text
    assert 'apiBase: ""' in client.get("/config.js").text
    assert client.get("/engine.js").status_code == 200
    assert client.get("/index.json").json()["format"] == 1


def test_evaluation_json(client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    assert client.get("/evaluation.json").status_code == 404
