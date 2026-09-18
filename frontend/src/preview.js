import markdownit from "markdown-it";
const md = markdownit({html: false, linkify: true, typographer: false});
let assetSessionId = null;

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

window.renderMarkdown = text => {
  document.querySelector("#preview").innerHTML = md.render(text);
};
window.setAssetSessionId = id => { assetSessionId = id || null; };
