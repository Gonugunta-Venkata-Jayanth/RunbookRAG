// Parity test: the browser engine must reproduce the Python reference implementation.
// Prerequisite: python -m runbookrag build && python scripts/export_parity.py
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { createEngine, MODES, stem } from "../engine.js";

const root = new URL("../../", import.meta.url);
const index = JSON.parse(readFileSync(new URL("build/index.json", root)));
const cases = JSON.parse(readFileSync(new URL("build/parity.json", root)));
const engine = createEngine(index);
const EPS = 1e-6;

test("stemmer rules", () => {
  assert.equal(stem("entries"), "entry");
  assert.equal(stem("restarting"), "restart");
  assert.equal(stem("killed"), "kill");
  assert.equal(stem("processes"), "process");
  assert.equal(stem("logs"), "log");
  assert.equal(stem("status"), "status");
  assert.equal(stem("dns"), "dns");
});

test("tokenizer matches Python", () => {
  for (const c of cases) assert.deepEqual(engine.tokenize(c.query), c.tokens, c.query);
});

for (const mode of MODES) {
  test(`${mode} rankings match Python`, () => {
    for (const c of cases) {
      const js = engine.rank(c.query, mode).slice(0, 10);
      assert.equal(js.length, c[mode].length, `${mode}: ${c.query}`);
      js.forEach(([i, score], n) => {
        const [id, pyScore] = c[mode][n];
        assert.ok(Math.abs(score - pyScore) < EPS, `${mode} score ${c.query} #${n}`);
        // Identity must match unless two chunks are tied within EPS.
        const tied = c[mode].some(([other, s], m) => m !== n && other === engine.chunks[i].id
          && Math.abs(s - pyScore) < EPS);
        assert.ok(engine.chunks[i].id === id || tied, `${mode} id ${c.query} #${n}`);
      });
    }
  });
}

test("extractive answers match Python", () => {
  for (const c of cases) {
    const a = engine.answer(c.query);
    assert.equal(a.answer !== null, c.answer.answered, c.query);
    assert.deepEqual(a.sentences.map((s) => s.source), c.answer.sources, c.query);
    assert.ok(Math.abs(a.coverage - c.answer.coverage) < 1e-4, c.query);
  }
});
