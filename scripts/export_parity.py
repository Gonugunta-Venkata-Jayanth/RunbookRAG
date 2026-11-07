"""Write build/parity.json: Python rankings and answers that the JS engine must reproduce."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runbookrag.answer import extractive_answer  # noqa: E402
from runbookrag.evaluate import load_queries  # noqa: E402
from runbookrag.index import load_index  # noqa: E402
from runbookrag.search import MODES, Retriever  # noqa: E402


def main(index_path: str = "build/index.json", out: str = "build/parity.json") -> None:
    retriever = Retriever(load_index(ROOT / index_path))
    queries = [q["query"] for q in load_queries(ROOT / "eval" / "queries.jsonl")]
    queries += ["", "zzzz qqqq", "the and of"]  # empty / out-of-vocabulary / stopword-only
    cases = []
    for q in queries:
        case = {"query": q, "tokens": __import__("runbookrag.text", fromlist=["tokenize"]).tokenize(q)}
        for mode in MODES:
            case[mode] = [[retriever.chunks[i]["id"], round(s, 9)] for i, s in retriever.rank(q, mode)[:10]]
        ans = extractive_answer(retriever, q)
        case["answer"] = {"sources": [s["source"] for s in ans["sentences"]], "coverage": ans["coverage"],
                          "answered": ans["answer"] is not None}
        cases.append(case)
    Path(ROOT / out).write_text(json.dumps(cases, indent=1), encoding="utf-8")
    print(f"wrote {len(cases)} parity cases -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
