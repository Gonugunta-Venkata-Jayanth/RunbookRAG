// In-browser port of runbookrag (text.py, search.py, answer.py).
// It reads the same index.json as the Python service and must rank identically;
// frontend/tests/engine.test.mjs checks parity against Python output in CI.

const TOKEN_RE = /[a-z0-9]+/g;
const SENTENCE_RE = /(?<=[.!?])\s+/;
export const MODES = ["hybrid", "bm25", "dense"];
const CONTEXT_CHUNKS = 3;
const RESULT_HITS = 5;
const MAX_SENTENCES = 3;
const MIN_COVERAGE = 0.34;

export function stem(t) {
  if (t.length > 5 && t.endsWith("ies")) return t.slice(0, -3) + "y";
  if (t.length > 5 && t.endsWith("ing")) return t.slice(0, -3);
  if (t.length > 4 && t.endsWith("ed")) return t.slice(0, -2);
  if (t.endsWith("sses")) return t.slice(0, -2);
  if (t.length > 3 && t.endsWith("s") && !t.endsWith("ss") && !t.endsWith("us") && !t.endsWith("is")) {
    return t.slice(0, -1);
  }
  return t;
}

export function makeTokenizer(stopwords) {
  const stop = new Set(stopwords);
  return (text) => (text.toLowerCase().match(TOKEN_RE) || [])
    .filter((t) => t.length > 1 && !stop.has(t))
    .map(stem);
}

export function splitSentences(text) {
  return text.trim().split(SENTENCE_RE).map((s) => s.trim()).filter(Boolean);
}

function ranked(scores) {
  const pairs = [];
  scores.forEach((s, i) => { if (s > 0) pairs.push([i, s]); });
  pairs.sort((a, b) => (b[1] - a[1]) || (a[0] - b[0]));
  return pairs;
}

export function createEngine(index) {
  const tokenize = makeTokenizer(index.stopwords);
  const termId = new Map(index.vocab.map((t, i) => [t, i]));
  const tf = index.tf.map((row) => new Map(row));
  const { k1, b, rrf_k: rrfK } = index.params;
  const chunks = index.chunks;

  function queryTerms(query) {
    const seen = [];
    for (const tok of tokenize(query)) {
      const j = termId.get(tok);
      if (j !== undefined && !seen.includes(j)) seen.push(j);
    }
    return seen;
  }

  function bm25Scores(query) {
    const terms = queryTerms(query);
    return tf.map((row, r) => {
      const norm = k1 * (1 - b + (b * index.lengths[r]) / index.avg_len);
      let s = 0;
      for (const j of terms) {
        const f = row.get(j);
        if (f) s += (index.bm25_idf[j] * f * (k1 + 1)) / (f + norm);
      }
      return s;
    });
  }

  function denseScores(query) {
    const counts = new Map();
    for (const tok of tokenize(query)) {
      const j = termId.get(tok);
      if (j !== undefined) counts.set(j, (counts.get(j) || 0) + 1);
    }
    if (counts.size === 0) return chunks.map(() => 0);
    const dims = index.params.dims;
    const q = [...counts].map(([j, n]) => [j, (1 + Math.log(n)) * index.tfidf_idf[j]]);
    const qn = Math.hypot(...q.map(([, w]) => w));
    const z = new Array(dims).fill(0);
    for (const [j, w] of q) {
      const row = index.projection[j];
      for (let d = 0; d < dims; d++) z[d] += (w / qn) * row[d];
    }
    const zn = Math.hypot(...z);
    if (zn === 0) return chunks.map(() => 0);
    return index.embeddings.map((e) => e.reduce((acc, v, d) => acc + v * (z[d] / zn), 0));
  }

  function rank(query, mode = "hybrid") {
    if (!MODES.includes(mode)) throw new Error(`mode must be one of ${MODES}`);
    if (mode === "bm25") return ranked(bm25Scores(query));
    if (mode === "dense") return ranked(denseScores(query));
    const fused = chunks.map(() => 0);
    for (const list of [ranked(bm25Scores(query)), ranked(denseScores(query))]) {
      list.forEach(([i], pos) => { fused[i] += 1 / (rrfK + pos + 1); });
    }
    return ranked(fused);
  }

  function search(query, mode = "hybrid", k = 5) {
    return rank(query, mode).slice(0, k).map(([i, score], n) => ({
      rank: n + 1, ...pick(chunks[i]), score: Math.round(score * 1e6) / 1e6,
    }));
  }

  function rankDocs(query, mode = "hybrid") {
    const out = [];
    for (const [i] of rank(query, mode)) if (!out.includes(chunks[i].doc)) out.push(chunks[i].doc);
    return out;
  }

  function answer(question, mode = "hybrid") {
    const hits = search(question, mode, RESULT_HITS);
    const qTerms = queryTerms(question);
    if (!hits.length || !qTerms.length) {
      return { answer: null, sentences: [], citations: [], coverage: 0, hits: [] };
    }
    const qSet = new Set(qTerms);
    const candidates = [];
    // Answer from the top-ranked runbook only, so one answer never mixes two procedures.
    const context = hits.filter((h) => h.doc === hits[0].doc).slice(0, CONTEXT_CHUNKS);
    for (const hit of context) {
      splitSentences(hit.text).forEach((sentence, pos) => {
        const present = new Set();
        for (const t of tokenize(sentence)) {
          const j = termId.get(t);
          if (j !== undefined && qSet.has(j)) present.add(j);
        }
        if (!present.size) return;
        let score = 0;
        for (const j of present) score += index.bm25_idf[j];
        score /= 1 + 0.5 * (hit.rank - 1);
        candidates.push({ score, rank: hit.rank, pos, sentence, source: hit.id, present });
      });
    }
    candidates.sort((x, y) => (y.score - x.score) || (x.rank - y.rank) || (x.pos - y.pos));
    const chosen = candidates.slice(0, MAX_SENTENCES).sort((x, y) => (x.rank - y.rank) || (x.pos - y.pos));
    const covered = new Set();
    chosen.forEach((c) => c.present.forEach((j) => covered.add(j)));
    const coverage = Math.round((covered.size / new Set(tokenize(question)).size) * 1e4) / 1e4;
    const citations = [...new Set(chosen.map((c) => c.source))];
    const grounded = chosen.length > 0 && coverage >= MIN_COVERAGE;
    return {
      answer: grounded ? chosen.map((c) => c.sentence).join(" ") : null,
      sentences: grounded ? chosen.map((c) => ({ text: c.sentence, source: c.source })) : [],
      citations: grounded ? citations : [],
      coverage,
      hits,
    };
  }

  return { search, rank, rankDocs, answer, queryTerms, tokenize, chunks };
}

function pick(c) {
  return { id: c.id, doc: c.doc, title: c.title, section: c.section, category: c.category, text: c.text };
}
