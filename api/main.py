"""FastAPI service: search, grounded answers, runbook browsing, feedback and usage stats."""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from runbookrag import __version__
from runbookrag.answer import extractive_answer
from runbookrag.corpus import load_corpus
from runbookrag.generator import generator_from_env
from runbookrag.index import build_index, load_index, save_index
from runbookrag.search import MODES, Retriever
from runbookrag.store import SQLiteStore

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    mode: str = "hybrid"
    generate: bool = False


class FeedbackRequest(BaseModel):
    query_id: str
    helpful: bool


def load_or_build(index_path: Path, corpus_dir: Path) -> dict:
    if not index_path.exists():
        save_index(build_index(load_corpus(corpus_dir)), index_path)
    return load_index(index_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    index_path = Path(os.getenv("RUNBOOKRAG_INDEX", ROOT / "build" / "index.json"))
    corpus_dir = Path(os.getenv("RUNBOOKRAG_CORPUS", ROOT / "corpus"))
    app.state.index_path = index_path
    app.state.retriever = Retriever(load_or_build(index_path, corpus_dir))
    app.state.store = SQLiteStore(os.getenv("RUNBOOKRAG_DB", ROOT / "data" / "runbookrag.db"))
    app.state.generator = generator_from_env()
    yield


app = FastAPI(title="RunbookRAG", version=__version__, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("RUNBOOKRAG_CORS", "*").split(","),
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


def _mode(mode: str) -> str:
    if mode not in MODES:
        raise HTTPException(422, f"mode must be one of {list(MODES)}")
    return mode


@app.get("/health")
def health() -> dict:
    r: Retriever = app.state.retriever
    return {"status": "ok", "version": __version__, "chunks": len(r.chunks),
            "generator": app.state.generator is not None}


@app.get("/api/search")
def search(q: str = Query(min_length=2, max_length=500), mode: str = "hybrid",
           k: int = Query(5, ge=1, le=20)) -> dict:
    hits = app.state.retriever.search(q, mode=_mode(mode), k=k)
    return {"query": q, "mode": mode, "hits": [h.to_dict() for h in hits]}


@app.post("/api/ask")
def ask(req: AskRequest) -> dict:
    started = time.perf_counter()
    result = extractive_answer(app.state.retriever, req.question, mode=_mode(req.mode))
    result["generated"] = None
    if req.generate and app.state.generator and result["hits"]:
        try:
            result["generated"] = app.state.generator.generate(req.question, result["hits"])
        except Exception as exc:  # generation is optional; the extractive answer still stands
            result["generator_error"] = str(exc)
    latency = (time.perf_counter() - started) * 1000
    top = result["hits"][0]["id"] if result["hits"] else None
    result["query_id"] = app.state.store.log_query(req.question, req.mode, top, result["answer"] is not None,
                                                   latency)
    result["latency_ms"] = round(latency, 3)
    return result


@app.post("/api/feedback")
def feedback(req: FeedbackRequest) -> dict:
    if not app.state.store.add_feedback(req.query_id, req.helpful):
        raise HTTPException(404, "unknown query_id")
    return {"ok": True}


@app.get("/api/runbooks")
def runbooks() -> dict:
    docs: dict[str, dict] = {}
    for c in app.state.retriever.chunks:
        d = docs.setdefault(c["doc"], {"id": c["doc"], "title": c["title"], "category": c["category"],
                                       "tags": c["tags"], "sections": []})
        d["sections"].append(c["section"])
    return {"runbooks": list(docs.values())}


@app.get("/api/runbooks/{doc_id}")
def runbook(doc_id: str) -> dict:
    sections = [c for c in app.state.retriever.chunks if c["doc"] == doc_id]
    if not sections:
        raise HTTPException(404, "runbook not found")
    return {"id": doc_id, "title": sections[0]["title"], "category": sections[0]["category"],
            "sections": [{"id": c["id"], "section": c["section"], "text": c["text"]} for c in sections]}


@app.get("/api/stats")
def stats() -> dict:
    return app.state.store.stats()


@app.get("/config.js", include_in_schema=False)
def config_js() -> Response:
    # Same-origin deployment: the dashboard talks to this API instead of its in-browser engine.
    return Response('window.RUNBOOKRAG_CONFIG = { apiBase: "" };\n', media_type="application/javascript")


@app.get("/index.json", include_in_schema=False)
def index_json() -> FileResponse:
    return FileResponse(app.state.index_path, media_type="application/json")


@app.get("/evaluation.json", include_in_schema=False)
def evaluation_json() -> FileResponse:
    path = ROOT / "reports" / "evaluation.json"
    if not path.exists():
        raise HTTPException(404, "no evaluation report; run scripts/evaluate.py")
    return FileResponse(path, media_type="application/json")


@app.get("/", include_in_schema=False)
def index_page() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND), name="frontend")
