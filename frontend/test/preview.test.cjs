const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

test("preview renders Markdown, escapes raw HTML, and leaves editor source alone", () => {
  const article = {innerHTML: ""};
  const editorSource = "# Título Ω\n\n**forte**\n\n![ok](photos/a%20b.png) ![escape](../secret.png) ![remote](https://example.test/x.png)\n\n<script>alert(1)</script>";
  const originalSource = editorSource;
  const context = {
    document: {querySelector: selector => selector === "#preview" ? article : null},
    window: {},
  };
  vm.runInNewContext(fs.readFileSync("dist/preview.js", "utf8"), context);
  context.window.setAssetSessionId("session-123");
  context.window.renderMarkdown(editorSource);

  assert.match(article.innerHTML, /<h1>Título Ω<\/h1>/);
  assert.match(article.innerHTML, /<strong>forte<\/strong>/);
  assert.match(article.innerHTML, /src="pdf2md-asset:\/\/session-123\/photos\/a%20b\.png"/);
  assert.match(article.innerHTML, /src="about:blank"/);
  assert.match(article.innerHTML, /src="https:\/\/example\.test\/x\.png"/);
  assert.match(article.innerHTML, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.equal(editorSource, originalSource);

  context.window.setAssetSessionId(null);
  context.window.renderMarkdown("![without session](sibling.png)");
  assert.match(article.innerHTML, /src="about:blank"/);
});

test("Phase 1 regression fixture matches the Markdown-it golden", () => {
  const fixture = fs.readFileSync("test/fixtures/phase1-regression.md");
  const source = fixture.toString("utf8");
  const golden = fs.readFileSync("test/golden/phase1-regression.html", "utf8");
  const article = {innerHTML: ""};
  const context = {
    document: {querySelector: selector => selector === "#preview" ? article : null},
    window: {},
  };

  vm.runInNewContext(fs.readFileSync("dist/preview.js", "utf8"), context);
  context.window.renderMarkdown(source);

  assert.equal(article.innerHTML, golden);
  assert.equal(fixture.toString("utf8"), source);
  assert.match(article.innerHTML, /\[\[nota-relacionada\]\]/);
  assert.match(article.innerHTML, /\$x\^2 \+ y\^2 = z\^2\$/);
  assert.match(article.innerHTML, /class="language-mermaid"/);
  assert.match(article.innerHTML, /class="language-unknown-language"/);
  assert.match(article.innerHTML, /\{\{ custom directive \}\}/);
});
