import markdownit from "markdown-it";
const md = markdownit({html: false, linkify: true, typographer: false});
let assetSessionId = null;

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
