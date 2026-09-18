const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

test("preview renders Markdown, escapes raw HTML, and leaves editor source alone", () => {
  const article = {innerHTML: ""};
  const editorSource = "# Título Ω\n\n**forte**\n\n[[folder/note#Heading|alias]] [Markdown](other.md)\n\n![ok](photos/a%20b.png) ![escape](../secret.png) ![remote](https://example.test/x.png)\n\n<script>alert(1)</script>";
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
  assert.match(article.innerHTML, /href="pdf2md-note:\/\/open\?kind=wikilink&amp;target=folder%2Fnote%23Heading" class="wikilink">alias<\/a>/);
  assert.match(article.innerHTML, /href="pdf2md-note:\/\/open\?kind=markdown&amp;target=other\.md" class="internal-link">Markdown<\/a>/);
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

  assert.equal(article.innerHTML.replace(/\r\n/g, "\n"), golden.replace(/\r\n/g, "\n"));
  assert.equal(fixture.toString("utf8"), source);
  assert.match(article.innerHTML, /class="wikilink">nota-relacionada<\/a>/);
  assert.match(article.innerHTML, /class="katex"/);
  assert.match(article.innerHTML, /class="language-mermaid"/);
  assert.match(article.innerHTML, /class="language-unknown-language"/);
  assert.match(article.innerHTML, /\{\{ custom directive \}\}/);
});

test("preview renders inline and block TeX locally and preserves bad input", () => {
  const article = {innerHTML: ""};
  const context = {
    document: {querySelector: selector => selector === "#preview" ? article : null},
    window: {},
  };
  vm.runInNewContext(fs.readFileSync("dist/preview.js", "utf8"), context);
  const source = "Inline $x^2$ and \\(\\frac{1}{2}\\).\n\n$$\n\\int_0^1 x\\,dx\n$$\n\nBad $\\unknowncommand{$";
  context.window.renderMarkdown(source);

  assert.equal(source.includes("$x^2$"), true);
  assert.match(article.innerHTML, /class="katex"/);
  assert.match(article.innerHTML, /class="katex-display"/);
  assert.match(article.innerHTML, /katex-error/);
});

test("Mermaid rendering is strict and keeps source when diagram parsing fails", async () => {
  const code = {textContent: "graph TD\n  A --> B"};
  const article = {
    innerHTML: "",
    querySelectorAll: selector => selector.startsWith("pre") ? [code] : [],
  };
  let configuration;
  const context = {
    document: {
      querySelector: selector => selector === "#preview" ? article : null,
      createElement: () => ({className: "", innerHTML: ""}),
    },
    window: {
      mermaid: {
        initialize: options => { configuration = options; },
        render: async () => { throw new Error("invalid diagram"); },
      },
    },
  };
  vm.runInNewContext(fs.readFileSync("dist/preview.js", "utf8"), context);
  await context.window.renderMarkdown("```mermaid\ngraph TD\n  A --> B\n```");

  assert.equal(configuration.securityLevel, "strict");
  assert.equal(configuration.startOnLoad, false);
  assert.equal(configuration.maxTextSize, 100000);
  assert.equal(configuration.maxEdges, 500);
  assert.equal(configuration.flowchart.htmlLabels, false);
  assert.match(article.innerHTML, /language-mermaid/);
  assert.match(article.innerHTML, /A --&gt; B/);
});

test("Mermaid diagrams are replaced with renderer output", async () => {
  const code = {
    textContent: "graph LR\n  A --> B",
    parentElement: {replaceWith: value => { article.replacement = value; }},
  };
  const article = {
    innerHTML: "",
    querySelectorAll: selector => selector.startsWith("pre") ? [code] : [],
  };
  const context = {
    document: {
      querySelector: selector => selector === "#preview" ? article : null,
      createElement: () => ({className: "", innerHTML: ""}),
    },
    window: {
      mermaid: {
        initialize: () => {},
        render: async (_id, source) => ({svg: `<svg>${source}</svg>`}),
      },
    },
  };
  vm.runInNewContext(fs.readFileSync("dist/preview.js", "utf8"), context);
  await context.window.renderMarkdown("```mermaid\ngraph LR\n  A --> B\n```");

  assert.equal(article.replacement.className, "mermaid-diagram");
  assert.match(article.replacement.innerHTML, /<svg>graph LR/);
});

test("a late Mermaid render cannot replace a newer preview", async () => {
  let finishOldRender;
  let queryCount = 0;
  const replacements = [];
  const firstCode = {
    textContent: "old diagram",
    parentElement: {replaceWith: value => replacements.push(value)},
  };
  const article = {
    innerHTML: "",
    querySelectorAll: selector => selector.startsWith("pre") && ++queryCount === 1
      ? [firstCode]
      : [],
  };
  const context = {
    document: {
      querySelector: selector => selector === "#preview" ? article : null,
      createElement: () => ({className: "", innerHTML: ""}),
    },
    window: {
      mermaid: {
        initialize: () => {},
        render: () => new Promise(resolve => { finishOldRender = resolve; }),
      },
    },
  };
  vm.runInNewContext(fs.readFileSync("dist/preview.js", "utf8"), context);
  const oldRender = context.window.renderMarkdown("```mermaid\nold diagram\n```");
  await context.window.renderMarkdown("new content");
  finishOldRender({svg: "<svg></svg>"});
  await oldRender;

  assert.match(article.innerHTML, /new content/);
  assert.equal(replacements.length, 0);
});

test("documented blockquote callouts get a safe title and styling class", () => {
  const marker = {textContent: "[!WARNING] Disk nearly full", remove() { this.removed = true; }};
  const paragraph = {firstChild: marker};
  const inserted = [];
  const classes = [];
  const blockquote = {
    querySelector: () => paragraph,
    classList: {add: (...values) => classes.push(...values)},
    insertBefore: (title, before) => inserted.push({title, before}),
  };
  const article = {
    innerHTML: "",
    querySelectorAll: selector => selector === "blockquote" ? [blockquote] : [],
  };
  const context = {
    document: {
      querySelector: selector => selector === "#preview" ? article : null,
      createElement: () => ({className: "", textContent: ""}),
    },
    window: {},
  };
  vm.runInNewContext(fs.readFileSync("dist/preview.js", "utf8"), context);
  context.window.renderMarkdown("> [!WARNING] Disk nearly full");

  assert.deepEqual(classes, ["callout", "callout-warning"]);
  assert.equal(inserted[0].title.className, "callout-title");
  assert.equal(inserted[0].title.textContent, "Disk nearly full");
  assert.equal(marker.textContent, "");

  marker.textContent = "[!CUSTOM] keep this marker";
  context.window.renderMarkdown("> [!CUSTOM] keep this marker");
  assert.deepEqual(classes, ["callout", "callout-warning"]);
  assert.equal(marker.textContent, "[!CUSTOM] keep this marker");
});
