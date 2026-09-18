import markdownit from "markdown-it";
import katex from "katex";
import "katex/dist/katex.min.css";

const md = markdownit({html: false, linkify: true, typographer: false});
let assetSessionId = null;
let renderRevision = 0;

if (window.mermaid) {
  window.mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    maxTextSize: 100000,
    maxEdges: 500,
    suppressErrorRendering: true,
    flowchart: {htmlLabels: false},
  });
}

function renderMath(source, displayMode = false) {
  return katex.renderToString(source, {
    displayMode,
    output: "htmlAndMathml",
    throwOnError: false,
    trust: false,
    maxExpand: 1000,
    maxSize: 20,
  });
}

md.inline.ruler.before("escape", "math_inline", (state, silent) => {
  const start = state.pos;
  const source = state.src;
  let closing;
  let expressionStart;

  if (source.startsWith("\\(", start)) {
    closing = "\\)";
    expressionStart = start + 2;
  } else if (source[start] === "$" && source[start + 1] !== "$" &&
      source[start + 1] && !/\s/.test(source[start + 1])) {
    closing = "$";
    expressionStart = start + 1;
  } else {
    return false;
  }

  const end = findInlineMathEnd(source, expressionStart, closing);
  if (end < 0 || end === expressionStart || /\s/.test(source[end - 1])) return false;
  if (!silent) {
    const token = state.push("html_inline", "", 0);
    token.content = renderMath(source.slice(expressionStart, end));
  }
  state.pos = end + closing.length;
  return true;
});

md.block.ruler.before("fence", "math_block", (state, startLine, endLine, silent) => {
  const lineStart = state.bMarks[startLine] + state.tShift[startLine];
  const firstLine = state.src.slice(lineStart, state.eMarks[startLine]).trim();
  let closing;
  let expression = "";
  let nextLine = startLine + 1;

  if (firstLine === "$$" || firstLine.startsWith("$$ ")) {
    closing = "$$";
    expression = firstLine.slice(2).trim();
  } else if (firstLine === "\\[" || firstLine.startsWith("\\[ ")) {
    closing = "\\]";
    expression = firstLine.slice(2).trim();
  } else {
    return false;
  }

  if (expression.endsWith(closing)) {
    expression = expression.slice(0, -closing.length).trim();
  } else {
    const lines = [];
    let foundClosing = false;
    for (; nextLine < endLine; nextLine += 1) {
      const currentStart = state.bMarks[nextLine] + state.tShift[nextLine];
      const line = state.src.slice(currentStart, state.eMarks[nextLine]).trim();
      if (line === closing) {
        foundClosing = true;
        nextLine += 1;
        break;
      }
      lines.push(line);
    }
    if (!foundClosing) return false;
    expression = [expression, ...lines].filter(Boolean).join("\n");
  }

  if (silent) return true;
  state.line = nextLine;
  const token = state.push("html_block", "", 0);
  token.content = `${renderMath(expression, true)}\n`;
  return true;
});

function findInlineMathEnd(source, start, delimiter) {
  for (let index = start; index < source.length; index += 1) {
    if (source[index] === "\n") return -1;
    if (source[index] === "\\") {
      index += 1;
      continue;
    }
    if (source.startsWith(delimiter, index)) {
      if (delimiter === "$" && source[index + 1] === "$") continue;
      return index;
    }
  }
  return -1;
}

function decorateCallouts(preview) {
  if (typeof preview.querySelectorAll !== "function") return;
  const calloutTypes = new Set([
    "note", "tip", "important", "warning", "caution", "abstract", "info",
    "success", "question", "failure", "danger", "bug", "example", "quote",
  ]);
  for (const blockquote of preview.querySelectorAll("blockquote")) {
    const paragraph = blockquote.querySelector("p");
    const text = paragraph?.firstChild;
    const marker = text?.textContent?.match(/^\s*\[!([a-z]+)\](?:[ \t]+([^\n]*))?/i);
    if (!marker) continue;
    const type = marker[1].toLowerCase();
    if (!calloutTypes.has(type)) continue;

    text.textContent = text.textContent.slice(marker[0].length);
    if (!text.textContent) text.remove();
    blockquote.classList.add("callout", `callout-${type}`);
    const title = document.createElement("p");
    title.className = "callout-title";
    title.textContent = marker[2]?.trim() || type[0].toUpperCase() + type.slice(1);
    blockquote.insertBefore(title, paragraph);
  }
}

function internalNoteUrl(target, kind) {
  return `pdf2md-note://open?kind=${encodeURIComponent(kind)}&target=${encodeURIComponent(target)}`;
}

md.inline.ruler.before("link", "wikilink", (state, silent) => {
  const start = state.pos;
  if (state.src.slice(start, start + 2) !== "[[" || state.linkLevel > 0) return false;
  const end = state.src.indexOf("]]", start + 2);
  if (end < 0 || state.src.slice(start, end).includes("\n")) return false;
  const body = state.src.slice(start + 2, end);
  const separator = body.indexOf("|");
  const target = (separator < 0 ? body : body.slice(0, separator)).trim();
  const label = (separator < 0 ? body : body.slice(separator + 1)).trim() || target;
  if (!target) return false;
  if (!silent) {
    const open = state.push("link_open", "a", 1);
    open.attrs = [["href", internalNoteUrl(target, "wikilink")], ["class", "wikilink"]];
    const text = state.push("text", "", 0);
    text.content = label;
    state.push("link_close", "a", -1);
  }
  state.pos = end + 2;
  return true;
});

const defaultLinkOpen = md.renderer.rules.link_open || ((tokens, index, options, env, renderer) =>
  renderer.renderToken(tokens, index, options));
md.renderer.rules.link_open = (tokens, index, options, env, renderer) => {
  const token = tokens[index];
  const href = token.attrGet("href") || "";
  if (isInternalMarkdownTarget(href)) {
    token.attrSet("href", internalNoteUrl(href, "markdown"));
    token.attrSet("class", "internal-link");
  }
  return defaultLinkOpen(tokens, index, options, env, renderer);
};

function isInternalMarkdownTarget(href) {
  if (!href || href.startsWith("#") || /^(?:[a-z][a-z\d+.-]*:|\/|\\)/i.test(href)) return false;
  const path = href.split(/[?#]/, 1)[0];
  return path.toLowerCase().endsWith(".md");
}

const defaultImageRenderer = md.renderer.rules.image || ((tokens, index, options, env, renderer) =>
  renderer.renderToken(tokens, index, options));
md.renderer.rules.image = (tokens, index, options, env, renderer) => {
  const token = tokens[index];
  const source = token.attrGet("src");
  if (source && isRelativeAssetPath(source)) {
    if (assetSessionId) {
      const encodedPath = source.split("/").map(part =>
        encodeURIComponent(decodeURIComponent(part))).join("/");
      token.attrSet("src", `pdf2md-asset://${assetSessionId}/${encodedPath}`);
    } else {
      token.attrSet("src", "about:blank");
    }
  } else if (source && !/^https?:\/\//i.test(source)) {
    token.attrSet("src", "about:blank");
  }
  return defaultImageRenderer(tokens, index, options, env, renderer);
};

function isRelativeAssetPath(source) {
  if (/^(?:[a-z][a-z\d+.-]*:|\/|\\)/i.test(source) || /[?#]/.test(source)) {
    return false;
  }
  try {
    const parts = source.split("/").map(decodeURIComponent);
    return parts.every(part => part && part !== "." && part !== ".." && !/[\\/\0]/.test(part));
  } catch {
    return false;
  }
}

window.renderMarkdown = async text => {
  const revision = ++renderRevision;
  const preview = document.querySelector("#preview");
  preview.innerHTML = md.render(text);
  decorateCallouts(preview);
  if (!window.mermaid) return;

  const blocks = Array.from(preview.querySelectorAll("pre > code.language-mermaid"));
  for (const [index, code] of blocks.entries()) {
    if (revision !== renderRevision) return;
    try {
      const {svg} = await window.mermaid.render(
        `pdf2md-mermaid-${revision}-${index}`,
        code.textContent,
      );
      if (revision !== renderRevision) return;
      const diagram = document.createElement("div");
      diagram.className = "mermaid-diagram";
      diagram.innerHTML = svg;
      code.parentElement.replaceWith(diagram);
    } catch {
      // Keep the Markdown-rendered fenced source visible on diagram errors.
    }
  }
};
window.setAssetSessionId = id => { assetSessionId = id || null; };
