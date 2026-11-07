"""Measure index build time and per-query latency of the Python engine on the evaluation queries."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runbookrag.answer import extractive_answer  # noqa: E402
from runbookrag.corpus import load_corpus  # noqa: E402
from runbookrag.evaluate import load_queries  # noqa: E402
from runbookrag.index import build_index  # noqa: E402
from runbookrag.search import MODES, Retriever  # noqa: E402


def main(repeats: int = 5) -> None:
    chunks = load_corpus(ROOT / "corpus")
    t0 = time.perf_counter()
    index = build_index(chunks)
    build_ms = (time.perf_counter() - t0) * 1000
    retriever = Retriever(index)
    queries = [q["query"] for q in load_queries(ROOT / "eval" / "queries.jsonl")]
    out = {"build_index_ms": round(build_ms, 1), "queries": len(queries), "repeats": repeats, "latency_ms": {}}
    for mode in MODES:
        samples = []
        for _ in range(repeats):
            for q in queries:
                t = time.perf_counter()
                retriever.rank(q, mode)
                samples.append((time.perf_counter() - t) * 1000)
        samples.sort()
        out["latency_ms"][mode] = {"p50": round(statistics.median(samples), 3),
                                   "p95": round(samples[int(0.95 * len(samples))], 3)}
    samples = []
    for q in queries:
        t = time.perf_counter()
        extractive_answer(retriever, q)
        samples.append((time.perf_counter() - t) * 1000)
    samples.sort()
    out["latency_ms"]["answer_hybrid"] = {"p50": round(statistics.median(samples), 3),
                                          "p95": round(samples[int(0.95 * len(samples))], 3)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
