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
