import math

import pytest

from runbookrag.answer import build_prompt, extractive_answer
from runbookrag.evaluate import evaluate, load_queries
from runbookrag.index import load_index, save_index
from runbookrag.search import Retriever

from .conftest import ROOT


def test_index_roundtrip(tmp_path, index):
    path = save_index(index, tmp_path / "i.json")
    loaded = load_index(path)
    assert loaded["vocab"] == index["vocab"]
    assert len(loaded["embeddings"]) == len(loaded["chunks"])
    assert len(loaded["projection"]) == len(loaded["vocab"])
    assert all(math.isclose(sum(v * v for v in e), 1.0, abs_tol=1e-3) for e in loaded["embeddings"])


def test_load_index_rejects_unknown_format(tmp_path, index):
    path = save_index({**index, "format": 99}, tmp_path / "bad.json")
    with pytest.raises(ValueError, match="format"):
        load_index(path)


@pytest.mark.parametrize("mode", ["hybrid", "bm25", "dense"])
@pytest.mark.parametrize(
    ("query", "doc"),
    [("container exits with code 137", "docker-restart-loop"),
     ("Permission denied (publickey)", "ssh-publickey-denied"),
     ("FATAL sorry too many clients already", "postgres-too-many-connections")],
)
def test_top_document(retriever, mode, query, doc):
    assert retriever.rank_docs(query, mode)[0] == doc


def test_rankings_sorted_and_positive(retriever):
    for mode in ("hybrid", "bm25", "dense"):
        ranking = retriever.rank("nginx upstream connection refused", mode)
        scores = [s for _, s in ranking]
        assert scores == sorted(scores, reverse=True)
        assert all(s > 0 for s in scores)


def test_hits_are_serialisable(retriever):
    hit = retriever.search("disk full", k=1)[0].to_dict()
    assert hit["rank"] == 1 and hit["doc"] == "disk-full" and hit["text"]


def test_out_of_vocabulary_query(retriever):
    assert retriever.rank("zzzz qqqq", "hybrid") == []
    assert retriever.dense_scores("zzzz") == [0.0] * len(retriever.chunks)


def test_invalid_mode(retriever):
    with pytest.raises(ValueError):
        retriever.rank("disk", "bogus")


def test_extractive_answer_is_grounded(retriever):
    result = extractive_answer(retriever, "lambda inside a vpc cannot reach the internet")
    assert result["answer"]
    assert result["citations"][0].startswith("aws-lambda-timeout#")
    assert 1 <= len(result["sentences"]) <= 3
    for s in result["sentences"]:
        chunk = next(c for c in retriever.chunks if c["id"] == s["source"])
        assert s["text"] in chunk["text"]  # every sentence is quoted verbatim from its source


def test_extractive_answer_refuses_unsupported(retriever):
    assert extractive_answer(retriever, "zzzz qqqq")["answer"] is None
    weak = extractive_answer(retriever, "kubernetes helm chart rollback strategy for ingress certificate")
    assert weak["answer"] is None and weak["coverage"] < 0.34 and weak["hits"]


def test_prompt_contains_citations(retriever):
    hits = [h.to_dict() for h in retriever.search("cron job", k=2)]
    prompt = build_prompt("why does cron not run?", hits)
    assert hits[0]["id"] in prompt and "Question: why does cron not run?" in prompt


def test_evaluation_meets_quality_bar(retriever):
    report = evaluate(retriever, load_queries(ROOT / "eval" / "queries.jsonl"))
    hybrid = report["results"]["hybrid"]
    assert report["queries"] >= 80
    assert hybrid["recall@3"] >= 0.95
    assert hybrid["mrr"] >= 0.90


def test_evaluation_rejects_unknown_labels(retriever, tmp_path):
    bad = tmp_path / "q.jsonl"
    bad.write_text('{"query": "x", "relevant": "nope"}\n')
    with pytest.raises(ValueError, match="unknown"):
        evaluate(retriever, load_queries(bad))
    bad.write_text('{"query": ""}\n')
    with pytest.raises(ValueError):
        load_queries(bad)


def test_retriever_from_saved_index(tmp_path, index):
    r = Retriever(load_index(save_index(index, tmp_path / "i.json")))
    assert r.rank_docs("ssh brute force")[0] == "ssh-brute-force"
