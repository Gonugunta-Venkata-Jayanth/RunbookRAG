"""Build a portable JSON index: BM25 statistics plus an LSA (truncated SVD) embedding space.

The same JSON file is loaded by the FastAPI service, the AWS Lambda handler and the
in-browser engine, so all three return identical rankings.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from runbookrag import __version__
from runbookrag.corpus import Chunk
from runbookrag.text import STOPWORDS, tokenize

FORMAT_VERSION = 1
DEFAULT_DIMS = 16
BM25_K1 = 1.5
BM25_B = 0.75


def tfidf_weight(tf: int, idf: float) -> float:
    return (1.0 + math.log(tf)) * idf


def build_index(chunks: list[Chunk], dims: int = DEFAULT_DIMS) -> dict:
    tokenized = [tokenize(c.index_text) for c in chunks]
    counts = [Counter(toks) for toks in tokenized]
    vocab = sorted({t for c in counts for t in c})
    term_id = {t: i for i, t in enumerate(vocab)}
    n_chunks, n_terms = len(chunks), len(vocab)

    df = np.zeros(n_terms)
    for c in counts:
        for t in c:
            df[term_id[t]] += 1
    bm25_idf = np.log(1.0 + (n_chunks - df + 0.5) / (df + 0.5))
    tfidf_idf = np.log((1.0 + n_chunks) / (1.0 + df)) + 1.0

    # TF-IDF matrix (sublinear tf, L2-normalised rows) -> truncated SVD (LSA).
    x = np.zeros((n_chunks, n_terms))
    for row, c in enumerate(counts):
        for t, tf in c.items():
            j = term_id[t]
            x[row, j] = tfidf_weight(tf, tfidf_idf[j])
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    k = min(dims, n_chunks - 1, n_terms - 1)
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    projection = np.round(vt[:k].T, 4)  # n_terms x k, rounded once so every consumer shares it
    emb = x @ projection
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)

    return {
        "format": FORMAT_VERSION,
        "version": __version__,
        "params": {"k1": BM25_K1, "b": BM25_B, "dims": int(k), "rrf_k": 60},
        "stopwords": sorted(STOPWORDS),
        "vocab": vocab,
        "bm25_idf": [round(float(v), 6) for v in bm25_idf],
        "tfidf_idf": [round(float(v), 6) for v in tfidf_idf],
        "avg_len": round(sum(len(t) for t in tokenized) / n_chunks, 6),
        "chunks": [c.to_dict() for c in chunks],
        "lengths": [len(t) for t in tokenized],
        "tf": [[[term_id[t], n] for t, n in sorted(c.items(), key=lambda kv: term_id[kv[0]])] for c in counts],
        "projection": projection.tolist(),
        "embeddings": np.round(emb, 5).tolist(),
    }


def save_index(index: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
    return path


def load_index(path: str | Path) -> dict:
    index = json.loads(Path(path).read_text(encoding="utf-8"))
    if index.get("format") != FORMAT_VERSION:
        raise ValueError(f"unsupported index format {index.get('format')!r}")
    return index
