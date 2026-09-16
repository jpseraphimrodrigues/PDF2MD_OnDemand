import { basicSetup } from "@codemirror/basic-setup";
import { defaultKeymap, history, historyKeymap, undo, redo } from "@codemirror/commands";
import { markdown } from "@codemirror/lang-markdown";
import { searchKeymap, openSearchPanel, findNext, findPrevious } from "@codemirror/search";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";

let bridge;
let editor;
const initial = window.initialMarkdown || "";

function announce() { bridge?.contentChanged(editor.state.doc.toString()); }
function bold() {
  const { from, to } = editor.state.selection.main;
  if (from !== to) editor.dispatch({ changes: { from, to, insert: `**${editor.state.sliceDoc(from, to)}**` } });
  editor.focus();
}
window.editorApi = {
  setContent(text) { editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: text }, userEvent: "remote" }); },
  getContent() { return editor.state.doc.toString(); },
  applyBold: bold,
  selection() { const s = editor.state.selection.main; return { from: s.from, to: s.to }; },
  cursor() { return editor.state.selection.main.head; },
  undo() { undo(editor); },
  redo() { redo(editor); },
  find() { openSearchPanel(editor); },
  findNext() { findNext(editor); },
  findPrevious() { findPrevious(editor); }
};

editor = new EditorView({
  state: EditorState.create({ doc: initial, extensions: [
    basicSetup, markdown(), history(), keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap]),
    EditorView.updateListener.of(update => { if (update.docChanged) announce(); })
  ]}),
  parent: document.querySelector("#editor")
});

new QWebChannel(qt.webChannelTransport, channel => {
  bridge = channel.objects.editorBridge;
  bridge.documentReady();
});
