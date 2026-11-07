"""Command line interface: build an index, query it and evaluate retrieval quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from runbookrag.answer import extractive_answer
from runbookrag.corpus import load_corpus
from runbookrag.evaluate import evaluate, load_queries
from runbookrag.index import DEFAULT_DIMS, build_index, load_index, save_index
from runbookrag.search import MODES, Retriever

DEFAULT_INDEX = "build/index.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="runbookrag", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="index a directory of Markdown runbooks")
    b.add_argument("--corpus", default="corpus")
    b.add_argument("--out", default=DEFAULT_INDEX)
    b.add_argument("--dims", type=int, default=DEFAULT_DIMS)

    for name in ("search", "ask"):
        p = sub.add_parser(name, help=f"{name} the index")
        p.add_argument("query")
        p.add_argument("--index", default=DEFAULT_INDEX)
        p.add_argument("--mode", choices=MODES, default="hybrid")
        p.add_argument("-k", type=int, default=5)

    e = sub.add_parser("eval", help="Recall@k and MRR on a labelled query set")
    e.add_argument("--index", default=DEFAULT_INDEX)
    e.add_argument("--queries", default="eval/queries.jsonl")

    args = parser.parse_args(argv)
    if args.command == "build":
        chunks = load_corpus(args.corpus)
        path = save_index(build_index(chunks, dims=args.dims), args.out)
        print(f"indexed {len(chunks)} sections from {len({c.doc for c in chunks})} runbooks -> {path}")
        return 0

    if not Path(args.index).exists():
        print(f"index not found: {args.index} (run 'python -m runbookrag build' first)", file=sys.stderr)
        return 2
    retriever = Retriever(load_index(args.index))
    if args.command == "search":
        for hit in retriever.search(args.query, mode=args.mode, k=args.k):
            print(f"{hit.rank}. {hit.score:.4f}  {hit.chunk['id']}  ({hit.chunk['title']})")
        return 0
    if args.command == "ask":
        result = extractive_answer(retriever, args.query, mode=args.mode)
        print(result["answer"] or "No grounded answer found in the runbooks.")
        for cid in result["citations"]:
            print(f"  source: {cid}")
        return 0
    report = evaluate(retriever, load_queries(args.queries))
    print(json.dumps({m: {k: v for k, v in r.items() if k != "misses"} for m, r in report["results"].items()},
                     indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
