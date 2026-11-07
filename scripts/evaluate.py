"""Write reports/evaluation.json: Recall@k and MRR per retrieval mode, overall and per query set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runbookrag.answer import extractive_answer  # noqa: E402
from runbookrag.corpus import load_corpus  # noqa: E402
from runbookrag.evaluate import evaluate, load_queries  # noqa: E402
from runbookrag.index import DEFAULT_DIMS, build_index  # noqa: E402
from runbookrag.search import Retriever  # noqa: E402


def strip(report: dict) -> dict:
    return {m: {k: v for k, v in r.items() if k != "misses"} for m, r in report["results"].items()}


def main() -> None:
    chunks = load_corpus(ROOT / "corpus")
    queries = load_queries(ROOT / "eval" / "queries.jsonl")
    retriever = Retriever(build_index(chunks, dims=DEFAULT_DIMS))
    overall = evaluate(retriever, queries)
    by_set = {
        name: strip(evaluate(retriever, [q for q in queries if q.get("set") == name]))
        for name in sorted({q.get("set", "direct") for q in queries})
    }
    by_set_counts = {name: sum(1 for q in queries if q.get("set") == name) for name in by_set}
    sweep = {}
    for dims in (16, 32, 64):
        r = Retriever(build_index(chunks, dims=dims))
        para = [q for q in queries if q.get("set") == "paraphrase"]
        sweep[str(dims)] = {m: v["mrr"] for m, v in strip(evaluate(r, para)).items()}
    answers = {}
    for name in sorted({q.get("set", "direct") for q in queries}):
        subset = [q for q in queries if q.get("set") == name]
        results = [(q, extractive_answer(retriever, q["query"])) for q in subset]
        answered = [(q, a) for q, a in results if a["answer"]]
        answers[name] = {
            "answer_rate": round(len(answered) / len(subset), 4),
            "citation_precision": round(
                sum(all(c.split("#")[0] == q["relevant"] for c in a["citations"]) for q, a in answered)
                / len(answered), 4) if answered else None,
        }
    report = {
        "dataset": "eval/queries.jsonl (hand-written; labels are the runbook that answers each query)",
        "dims": DEFAULT_DIMS,
        "queries": overall["queries"],
        "documents": overall["documents"],
        "chunks": overall["chunks"],
        "overall": strip(overall),
        "by_set": by_set,
        "set_sizes": by_set_counts,
        "paraphrase_mrr_by_dims": sweep,
        "answers": answers,
        "misses_hybrid": overall["results"]["hybrid"]["misses"],
    }
    out = ROOT / "reports" / "evaluation.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"by_set": by_set, "answers": answers, "sweep": sweep}, indent=2))


if __name__ == "__main__":
    main()
