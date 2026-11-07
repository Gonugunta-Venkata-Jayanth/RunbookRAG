"""Grounded answers: extractive by default, optionally rewritten by a local LLM.

The extractive path selects the sentences from the top retrieved sections that cover the
most informative query terms, and cites the section each sentence came from. It needs no
model, so it runs on the Lambda free tier and in the browser.
"""

from __future__ import annotations

from runbookrag.search import Retriever
from runbookrag.text import split_sentences, tokenize

CONTEXT_CHUNKS = 3
RESULT_HITS = 5
MAX_SENTENCES = 3
MIN_COVERAGE = 0.34


def extractive_answer(retriever: Retriever, question: str, mode: str = "hybrid") -> dict:
    hits = retriever.search(question, mode=mode, k=RESULT_HITS)
    q_terms = retriever.query_terms(question)
    if not hits or not q_terms:
        return {"answer": None, "sentences": [], "citations": [], "coverage": 0.0, "hits": []}

    # Answer from the top-ranked runbook only, so one answer never mixes two procedures.
    context = [h for h in hits if h.chunk["doc"] == hits[0].chunk["doc"]][:CONTEXT_CHUNKS]
    candidates = []
    for hit in context:
        for pos, sentence in enumerate(split_sentences(hit.chunk["text"])):
            present = {retriever.term_id.get(t) for t in tokenize(sentence)} & set(q_terms)
            if not present:
                continue
            score = sum(retriever.bm25_idf[j] for j in present) / (1 + 0.5 * (hit.rank - 1))
            candidates.append((score, hit.rank, pos, sentence, hit.chunk["id"], present))
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))
    chosen = sorted(candidates[:MAX_SENTENCES], key=lambda c: (c[1], c[2]))

    # Coverage counts every distinct query token, including ones the corpus has never seen,
    # so a question about an uncovered technology is refused rather than half-answered.
    covered = set().union(*(c[5] for c in chosen)) if chosen else set()
    coverage = round(len(covered) / len(set(tokenize(question))), 4)
    citations: list[str] = []
    for c in chosen:
        if c[4] not in citations:
            citations.append(c[4])
    sentences = [{"text": c[3], "source": c[4]} for c in chosen]
    grounded = bool(chosen) and coverage >= MIN_COVERAGE
    return {
        "answer": " ".join(c[3] for c in chosen) if grounded else None,
        "sentences": sentences if grounded else [],
        "citations": citations if grounded else [],
        "coverage": coverage,
        "hits": [h.to_dict() for h in hits],
    }


def build_prompt(question: str, hits: list[dict]) -> str:
    context = "\n\n".join(f"[{h['id']}] {h['title']} - {h['section']}: {h['text']}" for h in hits)
    return (
        "You are an SRE assistant. Answer the question using only the runbook excerpts below. "
        "Cite excerpt ids in square brackets. If the excerpts do not contain the answer, say so.\n\n"
        f"Excerpts:\n{context}\n\nQuestion: {question}\nAnswer:"
    )
