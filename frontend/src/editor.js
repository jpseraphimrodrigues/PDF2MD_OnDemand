import { basicSetup } from "codemirror";
import { defaultKeymap, history, historyKeymap, undo, redo } from "@codemirror/commands";
import { markdown } from "@codemirror/lang-markdown";
import { searchKeymap, openSearchPanel } from "@codemirror/search";
import { EditorState, Transaction } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { buildCommandTransaction } from "./editor_commands.js";

let view; let bridge;
const api = {
  getContent: () => view.state.doc.toString(),
  setContent: text => {
    if (text === view.state.doc.toString()) return false;
    view.dispatch({
      changes: {from: 0, to: view.state.doc.length, insert: text},
      annotations: Transaction.addToHistory.of(false),
    });
    return true;
  },
  selection: () => { const s = view.state.selection.main; return {from: s.from, to: s.to}; },
  applyCommand: command => {
    const selection = view.state.selection.main;
    const transaction = buildCommandTransaction(
      view.state.doc.toString(), selection.anchor, selection.head, command
    );
    if (!transaction) return false;
    view.dispatch({
      changes: {
        from: transaction.from,
        to: transaction.to,
        insert: transaction.insert,
      },
      selection: transaction.selection,
      userEvent: "format",
    });
    view.focus();
    return true;
  },
  select: (from, to) => view.dispatch({selection: {anchor: from, head: to}}),
  search: term => view.state.doc.toString().includes(term),
  undo: () => undo(view), redo: () => redo(view), find: () => openSearchPanel(view)
};
window.editorApi = api;
view = new EditorView({state: EditorState.create({extensions: [basicSetup, markdown(), history(), keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap]), EditorView.updateListener.of(u => { if (u.docChanged && bridge) bridge.setContent(view.state.doc.toString()); })]}), parent: document.querySelector("#editor")});
if (typeof qt !== "undefined" && qt.webChannelTransport) {
  new QWebChannel(qt.webChannelTransport, (channel) => {
    bridge = channel.objects.editorBridge;
    bridge.contentChanged.connect((text) => api.setContent(text));
    bridge.commandRequested.connect((command) => api.applyCommand(command));
    bridge.getContent((text) => api.setContent(text));
  });
}

