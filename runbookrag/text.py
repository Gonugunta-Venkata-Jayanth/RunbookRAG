"""Tokenisation shared by indexing and querying.

The rules are intentionally simple and deterministic because the browser engine
(frontend/engine.js) re-implements them byte for byte; tests check both agree.
"""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

STOPWORDS = frozenset(
    """a about above after again against all also am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further had has
    have having he her here hers him his how i if in into is it its itself just me more most my no nor
    not now of off on once only or other our ours out over own same she should so some such than that
    the their theirs them then there these they this those through to too under until up very was we
    were what when where which while who whom why will with would you your yours get got use used using
    usually way ways need needs""".split()
)


def stem(token: str) -> str:
    """Light suffix stripping; applied identically in Python and JavaScript."""
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if token.endswith("sses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Lower-case, split on non-alphanumerics, drop stopwords and 1-char tokens, stem."""
    return [stem(t) for t in TOKEN_RE.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS]


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_RE.split(text.strip()) if s.strip()]
