import { basicSetup } from "codemirror";
import { defaultKeymap, history, historyKeymap, undo, redo } from "@codemirror/commands";
import { markdown } from "@codemirror/lang-markdown";
import { searchKeymap, openSearchPanel } from "@codemirror/search";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";

let view; let bridge;
const api = {
  getContent: () => view.state.doc.toString(),
  setContent: text => view.dispatch({changes: {from: 0, to: view.state.doc.length, insert: text}}),
  selection: () => { const s = view.state.selection.main; return {from: s.from, to: s.to}; },
  applyCommand: command => { const s = view.state.selection.main; const text = view.state.sliceDoc(s.from, s.to); const wraps = {bold: ["**", "**"], italic: ["*", "*"], code: ["`", "`"], link: ["[", "](url)"]}; if (command === "heading") { view.dispatch({changes: {from: s.from, insert: "# "}}); } else if (wraps[command] && s.from !== s.to) { const [a,b] = wraps[command]; view.dispatch({changes: {from: s.from, to: s.to, insert: a + text + b}}); } view.focus(); },
  select: (from, to) => view.dispatch({selection: {anchor: from, head: to}}),
  search: term => view.state.doc.toString().includes(term),
  undo: () => undo(view), redo: () => redo(view), find: () => openSearchPanel(view)
};
window.editorApi = api;
view = new EditorView({state: EditorState.create({doc: window.initialMarkdown || "", extensions: [basicSetup, markdown(), history(), keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap]), EditorView.updateListener.of(u => { if (u.docChanged && bridge) bridge.receiveContent(view.state.doc.toString()); })]}), parent: document.querySelector("#editor")});
new QWebChannel(qt.webChannelTransport, channel => { bridge = channel.objects.editorBridge; bridge.editorReady(); });
