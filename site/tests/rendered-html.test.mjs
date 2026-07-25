import assert from "node:assert/strict";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("dist/server/index.js", root);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("built Worker renders the galdr foundation", async () => {
  const response = await render();
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /<title>galdr/i);
  assert.match(
    html,
    /A method for engineering agents that does not trust claims\./i,
  );
  assert.match(
    html,
    /galdr routes each request, requires a failing test before production code, and records fresh evidence before work is called done\./i,
  );
  assert.match(html, /<main/);
  assert.doesNotMatch(html, /fonts\.(?:googleapis|gstatic)\.com/i);
});

test("built Worker renders the complete public composition", async () => {
  const response = await render();
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /<header/);
  assert.match(html, /<nav[^>]+aria-label="Primary"/);
  assert.match(html, /<main/);
  assert.match(html, /<footer/);
  assert.match(html, /data-record-state="REQUEST"/);
  assert.match(html, /data-record-state="RECORDED"/);
  assert.match(html, /route → shape → plan → waves → verify → memory/);
  assert.match(html, /<span>SAMPLE<\/span> EV \[/);
  assert.match(html, /https:\/\/github\.com\/nyelonong\/galdr\/tree\/main\/skills/);
  assert.match(
    html,
    /https:\/\/github\.com\/nyelonong\/galdr\/blob\/main\/skills\/tdd\/SKILL\.md/,
  );
  assert.match(
    html,
    /https:\/\/github\.com\/nyelonong\/galdr\/blob\/main\/CHANGELOG\.md/,
  );
  assert.doesNotMatch(html, /testimonial|trusted by|codex-preview/i);
});
