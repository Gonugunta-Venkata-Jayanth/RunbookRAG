"""Assemble the static demo in dist/: the dashboard, the in-browser engine, index and evaluation."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runbookrag.corpus import load_corpus  # noqa: E402
from runbookrag.index import build_index, save_index  # noqa: E402

FILES = ("index.html", "styles.css", "app.js", "engine.js", "config.js")


def main(out: str = "dist") -> None:
    dist = ROOT / out
    shutil.rmtree(dist, ignore_errors=True)
    dist.mkdir(parents=True)
    for name in FILES:
        shutil.copy(ROOT / "frontend" / name, dist / name)
    save_index(build_index(load_corpus(ROOT / "corpus")), dist / "index.json")
    report = ROOT / "reports" / "evaluation.json"
    if report.exists():
        shutil.copy(report, dist / "evaluation.json")
    print(f"static demo written to {dist}")


if __name__ == "__main__":
    main(*sys.argv[1:])
