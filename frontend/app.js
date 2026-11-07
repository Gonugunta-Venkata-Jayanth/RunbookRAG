import { createEngine } from "./engine.js";

const cfg = window.RUNBOOKRAG_CONFIG || { apiBase: null };
const useApi = typeof cfg.apiBase === "string";
const $ = (s) => document.querySelector(s);
const EXAMPLES = [
  "container exits with code 137",
  "lambda inside a vpc times out calling an external api",
  "df shows free space but I cannot create files",
  "nginx 502 bad gateway",
  "hosts disagree about the current time",
];

let engine = null;
let chunks = [];
let mode = "hybrid";
let lastQueryId = null;
let lastTerms = [];

const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// Render `inline code` from the runbooks after escaping.
const fmt = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>");

// Highlight query terms on escaped text first, then render inline code, so markup is never matched.
function highlight(text, terms) {
  if (!terms.length) return fmt(text);
  const marked = esc(text).replace(/&#?\w+;|[A-Za-z0-9]+/g, (w) => {
    if (w.startsWith("&")) return w;
    const t = engine ? engine.tokenize(w)[0] : w.toLowerCase();
    return t && terms.includes(t) ? `<mark>${w}</mark>` : w;
  });
  return marked.replace(/`([^`]+)`/g, "<code>$1</code>");
}
const MODE_LABEL = { hybrid: "hybrid", bm25: "BM25", dense: "semantic (LSA)" };

async function api(path, opts) {
  const res = await fetch(cfg.apiBase + path, opts);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

async function init() {
  // The index is always loaded: it powers the runbook viewer and term highlighting in both modes.
  const index = await (await fetch("index.json")).json().catch(() => null);
  if (index) { engine = createEngine(index); chunks = index.chunks; }
  if (useApi) {
    const h = await api("/health").catch(() => null);
    $("#backend").textContent = h ? `API connected · ${h.chunks} sections` : "API unreachable";
    if (!chunks.length && h) {
      const { runbooks } = await api("/api/runbooks");
      const full = await Promise.all(runbooks.map((r) => api(`/api/runbooks/${r.id}`)));
      chunks = full.flatMap((d) => d.sections.map((s) => ({ ...s, doc: d.id, title: d.title, category: d.category })));
    }
  } else {
    $("#backend").textContent = engine ? `In-browser engine · ${chunks.length} sections` : "Index failed to load";
  }
  $("#backend").classList.toggle("ok", Boolean(engine || useApi));
  renderCorpus();
  renderExamples();
  loadMetrics();
}

function renderExamples() {
  $("#examples").innerHTML = EXAMPLES.map((e) => `<button type="button">${esc(e)}</button>`).join("");
  $("#examples").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    $("#q").value = b.textContent; run(b.textContent);
  }));
}

function renderCorpus() {
  const docs = new Map();
  chunks.forEach((c) => docs.has(c.doc) || docs.set(c.doc, c));
  $("#corpus-n").textContent = `${docs.size} runbooks`;
  $("#corpus").innerHTML = [...docs.values()].sort((a, b) => a.title.localeCompare(b.title))
    .map((c) => `<li><button type="button" data-doc="${c.doc}">${esc(c.title)}</button><span class="tag">${esc(c.category)}</span></li>`).join("");
  $("#corpus").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => showDoc(b.dataset.doc)));
}

function showDoc(doc, focusId) {
  const parts = chunks.filter((c) => c.doc === doc);
  if (!parts.length) return;
  $("#doc-cat").textContent = parts[0].category;
  $("#doc").innerHTML = `<h3>${esc(parts[0].title)}</h3>` + parts.map((c) =>
    `<h4 id="sec-${c.id.replace(/[^a-z0-9]/g, "-")}" class="${c.id === focusId ? "hl" : ""}">${esc(c.section)}</h4><p>${highlight(c.text, lastTerms)}</p>`).join("");
  if (focusId) document.getElementById(`sec-${focusId.replace(/[^a-z0-9]/g, "-")}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

async function run(question) {
  const t0 = performance.now();
  let result;
  try {
    result = useApi
      ? await api("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, mode }) })
      : engine.answer(question, mode);
  } catch (err) {
    $("#answer").hidden = false;
    $("#answer-body").innerHTML = `<p class="noanswer">Request failed: ${esc(String(err.message || err))}</p>`;
    return;
  }
  const ms = performance.now() - t0;
  lastTerms = engine ? engine.tokenize(question) : [];
  lastQueryId = result.query_id || null;
  renderAnswer(result);
  renderResults(result.hits, ms);
  if (result.hits.length) showDoc(result.hits[0].doc, result.hits[0].id);
}

function renderAnswer(r) {
  $("#answer").hidden = false;
  $("#coverage").textContent = r.hits.length ? `query term coverage ${(r.coverage * 100).toFixed(0)}%` : "";
  if (!r.answer) {
    $("#answer-body").innerHTML = `<p class="noanswer">No grounded answer: the runbooks do not cover enough of this question.${r.hits.length ? " The closest sections are listed below." : ""}</p>`;
  } else {
    const order = r.citations;
    $("#answer-body").innerHTML = r.sentences.map((s) => {
      const n = order.indexOf(s.source) + 1;
      return `<p>${fmt(s.text)}<a class="cite" data-id="${s.source}" title="${esc(s.source)}">[${n}]</a></p>`;
    }).join("") + `<p class="muted">Sources: ${order.map((c, i) => `[${i + 1}] ${esc(c)}`).join(" · ")}</p>`;
    $("#answer-body").querySelectorAll(".cite").forEach((a) => a.addEventListener("click", () => showDoc(a.dataset.id.split("#")[0], a.dataset.id)));
  }
  if (r.generated) $("#answer-body").insertAdjacentHTML("afterbegin", `<p>${fmt(r.generated)}</p>`);
  $("#feedback").hidden = !(useApi && lastQueryId);
}

function renderResults(hits, ms) {
  $("#latency").textContent = `${hits.length} sections · ${ms.toFixed(1)} ms · ${MODE_LABEL[mode]}`;
  if (!hits.length) { $("#results").innerHTML = `<li class="muted">No section matched the query terms.</li>`; return; }
  $("#results").innerHTML = hits.map((h) => `<li class="hit" data-id="${h.id}" data-doc="${h.doc}">
      <div class="hit-head"><strong>${h.rank}. ${esc(h.title)} · ${esc(h.section)}</strong><span class="score">${h.score.toFixed(4)}</span></div>
      <p class="snippet">${highlight(h.text, lastTerms)}</p></li>`).join("");
  $("#results").querySelectorAll(".hit").forEach((li) => li.addEventListener("click", () => {
    $("#results").querySelectorAll(".hit").forEach((x) => x.classList.toggle("active", x === li));
    showDoc(li.dataset.doc, li.dataset.id);
  }));
}

async function loadMetrics() {
  const rep = await fetch("evaluation.json").then((r) => (r.ok ? r.json() : null)).catch(() => null);
  if (!rep) return;
  $("#eval-n").textContent = `${rep.queries} queries · ${rep.documents} runbooks`;
  const rows = [];
  for (const [set, res] of Object.entries(rep.by_set)) {
    const best = Math.max(...Object.values(res).map((m) => m.mrr));
    for (const [m, v] of Object.entries(res)) {
      rows.push(`<tr><td>${set} (${rep.set_sizes[set]}) · ${m}</td><td>${v["recall@1"].toFixed(3)}</td><td>${v["recall@3"].toFixed(3)}</td><td class="${v.mrr === best ? "best" : ""}">${v.mrr.toFixed(3)}</td></tr>`);
    }
  }
  $("#metrics").innerHTML = `<thead><tr><th>Set · mode</th><th>Recall@1</th><th>Recall@3</th><th>MRR</th></tr></thead><tbody>${rows.join("")}</tbody>`;
}

$("#ask-form").addEventListener("submit", (e) => { e.preventDefault(); const q = $("#q").value.trim(); if (q) run(q); });
document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
  mode = b.dataset.mode;
  document.querySelectorAll(".seg button").forEach((x) => { x.classList.toggle("on", x === b); x.setAttribute("aria-checked", String(x === b)); });
  const q = $("#q").value.trim(); if (q) run(q);
}));
$("#feedback").querySelectorAll("button").forEach((b) => b.addEventListener("click", async () => {
  if (!lastQueryId) return;
  await api("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query_id: lastQueryId, helpful: b.dataset.helpful === "true" }) }).catch(() => null);
  $("#feedback").innerHTML = `<span class="muted">Thanks, feedback recorded.</span>`;
}));

init();
