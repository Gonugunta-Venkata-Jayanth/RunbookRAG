import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runbookrag.corpus import load_corpus  # noqa: E402
from runbookrag.index import build_index  # noqa: E402
from runbookrag.search import Retriever  # noqa: E402


@pytest.fixture(scope="session")
def chunks():
    return load_corpus(ROOT / "corpus")


@pytest.fixture(scope="session")
def index(chunks):
    return build_index(chunks)


@pytest.fixture(scope="session")
def retriever(index):
    return Retriever(index)
