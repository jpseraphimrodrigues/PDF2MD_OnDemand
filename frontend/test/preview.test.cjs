const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

test("preview renders Markdown, escapes raw HTML, and leaves editor source alone", () => {
  const article = {innerHTML: ""};
  const editorSource = "# Título Ω\n\n**forte**\n\n<script>alert(1)</script>";
  const originalSource = editorSource;
  const context = {
    document: {querySelector: selector => selector === "#preview" ? article : null},
    window: {},
  };
  vm.runInNewContext(fs.readFileSync("dist/preview.js", "utf8"), context);
  context.window.renderMarkdown(editorSource);

  assert.match(article.innerHTML, /<h1>Título Ω<\/h1>/);
  assert.match(article.innerHTML, /<strong>forte<\/strong>/);
  assert.match(article.innerHTML, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.equal(editorSource, originalSource);
});
