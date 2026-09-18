import { basicSetup } from "codemirror";
import { defaultKeymap, history, historyKeymap, undo, redo } from "@codemirror/commands";
import { markdown } from "@codemirror/lang-markdown";
import { searchKeymap, openSearchPanel } from "@codemirror/search";
import { EditorState, Transaction } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { buildCommandTransaction } from "./editor_commands.js";
import "./editor.css";

let view; let bridge;
let activeDocumentKey = "__initial__";
let switchingDocument = false;
const documentStates = new Map();
const extensions = [basicSetup, markdown(), history(), keymap.of([
  ...defaultKeymap, ...historyKeymap, ...searchKeymap,
])];
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
  switchDocument: (key, text) => {
    if (key === activeDocumentKey) return false;
    if (activeDocumentKey !== null) {
      documentStates.set(activeDocumentKey, {
        state: view.state,
        scrollTop: view.scrollDOM.scrollTop,
        scrollLeft: view.scrollDOM.scrollLeft,
      });
    }
    const saved = documentStates.get(key);
    const next = saved || {
      state: EditorState.create({doc: text, extensions}),
      scrollTop: 0,
      scrollLeft: 0,
    };
    documentStates.set(key, next);
    activeDocumentKey = key;
    switchingDocument = true;
    view.setState(next.state);
    switchingDocument = false;
    view.focus();
    requestAnimationFrame(() => requestAnimationFrame(() => {
      view.scrollDOM.scrollTop = next.scrollTop;
      view.scrollDOM.scrollLeft = next.scrollLeft;
    }));
    return true;
  },
  closeDocument: key => {
    documentStates.delete(key);
    if (key !== activeDocumentKey) return false;
    activeDocumentKey = null;
    switchingDocument = true;
    view.setState(EditorState.create({extensions}));
    view.scrollDOM.scrollTop = 0;
    view.scrollDOM.scrollLeft = 0;
    switchingDocument = false;
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
extensions.push(EditorView.updateListener.of(update => {
  if (update.docChanged && bridge && !switchingDocument) {
    bridge.setDocumentContent(activeDocumentKey, view.state.doc.toString());
  }
}));
window.editorApi = api;
view = new EditorView({
  state: EditorState.create({extensions}),
  parent: document.querySelector("#editor"),
});
documentStates.set(activeDocumentKey, {
  state: view.state,
  scrollTop: 0,
  scrollLeft: 0,
});
if (typeof qt !== "undefined" && qt.webChannelTransport) {
  new QWebChannel(qt.webChannelTransport, (channel) => {
    bridge = channel.objects.editorBridge;
    bridge.documentContentChanged.connect((key, text) => {
      if (key === activeDocumentKey) api.setContent(text);
    });
    bridge.commandRequested.connect((command) => api.applyCommand(command));
    bridge.documentSwitchRequested.connect((key, text) => api.switchDocument(key, text));
    bridge.documentCloseRequested.connect(key => api.closeDocument(key));
    bridge.getDocumentKey(key => {
      bridge.getContent(text => {
        if (key) api.switchDocument(key, text);
        else api.setContent(text);
      });
    });
  });
}

