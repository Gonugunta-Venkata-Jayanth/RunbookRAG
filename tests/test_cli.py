from runbookrag.__main__ import main

from .conftest import ROOT


def test_cli_build_search_ask_eval(tmp_path, capsys):
    idx = str(tmp_path / "index.json")
    assert main(["build", "--corpus", str(ROOT / "corpus"), "--out", idx, "--dims", "8"]) == 0
    assert "indexed 88 sections from 22 runbooks" in capsys.readouterr().out
    assert main(["search", "port already in use", "--index", idx, "-k", "2"]) == 0
    assert "port-already-in-use#" in capsys.readouterr().out
    assert main(["ask", "cron job not running from crontab", "--index", idx]) == 0
    assert "source: cron-job-not-running#" in capsys.readouterr().out
    assert main(["ask", "zzzz qqqq", "--index", idx]) == 0
    assert "No grounded answer" in capsys.readouterr().out
    assert main(["eval", "--index", idx, "--queries", str(ROOT / "eval" / "queries.jsonl")]) == 0
    assert '"mrr"' in capsys.readouterr().out


def test_cli_missing_index(tmp_path, capsys):
    assert main(["search", "disk", "--index", str(tmp_path / "missing.json")]) == 2
    assert "index not found" in capsys.readouterr().err
