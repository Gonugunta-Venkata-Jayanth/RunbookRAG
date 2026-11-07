"""Retrieval evaluation: document-level Recall@k and MRR on a labelled query set."""

from __future__ import annotations

import json
from pathlib import Path

from runbookrag.search import MODES, Retriever

KS = (1, 3, 5)


def load_queries(path: str | Path) -> list[dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        if not row.get("query") or not row.get("relevant"):
            raise ValueError(f"bad evaluation row: {row}")
    return rows


def evaluate(retriever: Retriever, queries: list[dict]) -> dict:
    known = {c["doc"] for c in retriever.chunks}
    missing = sorted({q["relevant"] for q in queries} - known)
    if missing:
        raise ValueError(f"evaluation references unknown runbooks: {missing}")
    results = {}
    for mode in MODES:
        hits = {k: 0 for k in KS}
        rr = 0.0
        misses = []
        for q in queries:
            ranked = retriever.rank_docs(q["query"], mode)
            pos = ranked.index(q["relevant"]) + 1 if q["relevant"] in ranked else None
            for k in KS:
                hits[k] += int(pos is not None and pos <= k)
            rr += 1.0 / pos if pos else 0.0
            if pos != 1:
                misses.append({"query": q["query"], "relevant": q["relevant"], "rank": pos,
                               "top": ranked[0] if ranked else None})
        n = len(queries)
        results[mode] = {
            **{f"recall@{k}": round(hits[k] / n, 4) for k in KS},
            "mrr": round(rr / n, 4),
            "misses": misses,
        }
    return {"queries": len(queries), "documents": len(known), "chunks": len(retriever.chunks),
            "results": results}
