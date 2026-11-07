"""Lexical (BM25), semantic (LSA) and hybrid (reciprocal rank fusion) retrieval."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import numpy as np

from runbookrag.text import tokenize

MODES = ("hybrid", "bm25", "dense")


@dataclass(frozen=True)
class Hit:
    rank: int
    chunk: dict
    score: float

    def to_dict(self) -> dict:
        c = self.chunk
        return {
            "rank": self.rank,
            "id": c["id"],
            "doc": c["doc"],
            "title": c["title"],
            "section": c["section"],
            "category": c["category"],
            "score": round(self.score, 6),
            "text": c["text"],
        }


def _ranked(scores: list[float]) -> list[tuple[int, float]]:
    """Positive scores, best first; ties broken by chunk order (mirrors engine.js)."""
    pairs = [(i, s) for i, s in enumerate(scores) if s > 0]
    pairs.sort(key=lambda p: (-p[1], p[0]))
    return pairs


class Retriever:
    def __init__(self, index: dict) -> None:
        self.index = index
        self.chunks: list[dict] = index["chunks"]
        self.term_id = {t: i for i, t in enumerate(index["vocab"])}
        self.bm25_idf = index["bm25_idf"]
        self.tfidf_idf = index["tfidf_idf"]
        self.tf = [{t: n for t, n in row} for row in index["tf"]]
        self.lengths = index["lengths"]
        self.avg_len = index["avg_len"]
        self.params = index["params"]
        self.projection = np.asarray(index["projection"], dtype=float)
        self.embeddings = np.asarray(index["embeddings"], dtype=float)

    def query_terms(self, query: str) -> list[int]:
        """Unique in-vocabulary term ids, in first-occurrence order."""
        seen: list[int] = []
        for tok in tokenize(query):
            j = self.term_id.get(tok)
            if j is not None and j not in seen:
                seen.append(j)
        return seen

    def bm25_scores(self, query: str) -> list[float]:
        k1, b = self.params["k1"], self.params["b"]
        terms = self.query_terms(query)
        scores = []
        for row, tf in enumerate(self.tf):
            norm = k1 * (1 - b + b * self.lengths[row] / self.avg_len)
            s = 0.0
            for j in terms:
                f = tf.get(j)
                if f:
                    s += self.bm25_idf[j] * f * (k1 + 1) / (f + norm)
            scores.append(s)
        return scores

    def dense_scores(self, query: str) -> list[float]:
        counts = Counter(self.term_id[t] for t in tokenize(query) if t in self.term_id)
        if not counts:
            return [0.0] * len(self.chunks)
        q = np.zeros(self.projection.shape[0])
        for j, tf in counts.items():
            q[j] = (1.0 + math.log(tf)) * self.tfidf_idf[j]
        q /= np.linalg.norm(q)
        z = q @ self.projection
        norm = np.linalg.norm(z)
        if norm == 0:
            return [0.0] * len(self.chunks)
        return (self.embeddings @ (z / norm)).tolist()

    def rank(self, query: str, mode: str = "hybrid") -> list[tuple[int, float]]:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if mode == "bm25":
            return _ranked(self.bm25_scores(query))
        if mode == "dense":
            return _ranked(self.dense_scores(query))
        rrf_k = self.params["rrf_k"]
        fused = [0.0] * len(self.chunks)
        for ranking in (_ranked(self.bm25_scores(query)), _ranked(self.dense_scores(query))):
            for pos, (i, _) in enumerate(ranking, start=1):
                fused[i] += 1.0 / (rrf_k + pos)
        return _ranked(fused)

    def search(self, query: str, mode: str = "hybrid", k: int = 5) -> list[Hit]:
        return [Hit(r, self.chunks[i], s) for r, (i, s) in enumerate(self.rank(query, mode)[:k], start=1)]

    def rank_docs(self, query: str, mode: str = "hybrid") -> list[str]:
        """Document ids in the order their best chunk appears."""
        out: list[str] = []
        for i, _ in self.rank(query, mode):
            doc = self.chunks[i]["doc"]
            if doc not in out:
                out.append(doc)
        return out
