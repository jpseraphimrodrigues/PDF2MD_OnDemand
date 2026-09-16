import { basicSetup } from "codemirror";
import { markdown } from "@codemirror/lang-markdown";
import { EditorState } from "@codemirror/state";
import { EditorView } from "@codemirror/view";

let editor;
let bridge;
window.editorApi = {
  getContent: () => editor.state.doc.toString(),
  setContent: text => editor.dispatch({changes: {from: 0, to: editor.state.doc.length, insert: text}})
};

editor = new EditorView({state: EditorState.create({doc: "", extensions: [basicSetup, markdown(), EditorView.updateListener.of(update => {
  if (update.docChanged && bridge) bridge.receiveContent(editor.state.doc.toString());
})]}), parent: document.querySelector("#editor")});

new QWebChannel(qt.webChannelTransport, channel => {
  bridge = channel.objects.bridge;
  bridge.editorReady();
});
