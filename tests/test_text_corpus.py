import pytest

from runbookrag.corpus import load_corpus, parse_runbook, slugify
from runbookrag.text import split_sentences, stem, tokenize


@pytest.mark.parametrize(
    ("word", "expected"),
    [("entries", "entry"), ("restarting", "restart"), ("killed", "kill"), ("processes", "process"),
     ("logs", "log"), ("status", "status"), ("dns", "dns"), ("analysis", "analysis"), ("class", "class")],
)
def test_stem(word, expected):
    assert stem(word) == expected


def test_tokenize_drops_stopwords_and_short_tokens():
    assert tokenize("The Container is restarting, exit code 137!") == ["container", "restart", "exit", "code", "137"]
    assert tokenize("a the of") == []


def test_split_sentences():
    assert split_sentences("One. Two? Three!  ") == ["One.", "Two?", "Three!"]


def test_corpus_shape(chunks):
    docs = {c.doc for c in chunks}
    assert len(docs) == 22
    assert len(chunks) == 88
    assert all(c.id.startswith(f"{c.doc}#") for c in chunks)
    assert {c.section for c in chunks} == {"Symptoms", "Diagnosis", "Resolution", "Prevention"}


def test_parse_runbook_errors():
    with pytest.raises(ValueError, match="front matter"):
        parse_runbook("x", "# no front matter")
    with pytest.raises(ValueError, match="category"):
        parse_runbook("x", "---\ntitle: T\n---\n## A\ntext")
    with pytest.raises(ValueError, match="sections"):
        parse_runbook("x", "---\ntitle: T\ncategory: c\n---\nno headings")


def test_parse_runbook_skips_empty_sections():
    chunks = parse_runbook("x", "---\ntitle: T\ncategory: c\ntags: a, b\n---\n## Empty\n\n## Full Section\nSome text.")
    assert [c.id for c in chunks] == ["x#full-section"]
    assert chunks[0].tags == ("a", "b")
    assert "T. Full Section. a b." in chunks[0].index_text


def test_load_corpus_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_corpus(tmp_path)
    (tmp_path / "a.md").write_text("---\ntitle: T\ncategory: c\n---\n## S\none\n## S\ntwo")
    with pytest.raises(ValueError, match="duplicate"):
        load_corpus(tmp_path)


def test_slugify():
    assert slugify("  Root Cause / Fix ") == "root-cause-fix"
