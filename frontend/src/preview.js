import markdownit from "markdown-it";
const md = markdownit({html: false, linkify: true, typographer: false});
window.renderMarkdown = text => {
  document.querySelector("#preview").innerHTML = md.render(text);
};
