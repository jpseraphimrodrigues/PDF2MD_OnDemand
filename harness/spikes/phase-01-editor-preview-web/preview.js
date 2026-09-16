import markdownit from "markdown-it";

const md = markdownit({ html: false, linkify: true, typographer: false });
let bridge;
window.renderMarkdown = text => { document.querySelector("#preview").innerHTML = md.render(text); };

new QWebChannel(qt.webChannelTransport, channel => {
  bridge = channel.objects.previewBridge;
  bridge.previewReady();
});
