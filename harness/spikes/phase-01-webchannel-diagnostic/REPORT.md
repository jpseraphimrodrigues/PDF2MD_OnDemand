# Spike — Diagnóstico QWebChannel

## Estado anterior

O Spike 1B criava `EditorBridge`, `PreviewBridge`, dois `QWebChannel` e os
registrava antes de carregar páginas locais. Porém `editor.html` executava o
bundle antes de criar `#editor`; o CodeMirror falhava antes de alcançar
`new QWebChannel(...)`. Depois de corrigir esse ponto, surgiu também o erro de
tratar o sinal Python `contentChanged` como função JavaScript.

## Causa raiz

### FATO

O diagnóstico mínimo com `#editor` criado antes dos scripts completou o
handshake. O editor CodeMirror então emitiu conteúdo para Python e Python
recuperou o conteúdo de volta.

### INFERÊNCIA CONFIRMADA

O primeiro bloqueio do Spike 1B era a ordem do DOM: o bundle criava o editor
com `parent: document.querySelector("#editor")` quando o elemento ainda não
existia. A execução parava antes de iniciar o WebChannel.

O segundo bloqueio era semântico: sinais expostos pelo QWebChannel são sinais
JavaScript, não métodos. O frontend deve chamar um `@Slot(str)` como
`receiveContent(text)`; sinais JS devem usar `.connect(...)`.

### HIPÓTESE NÃO TESTADA

Não foi necessário atribuir a falha a garbage collection, QRC ou ao WebEngine
headless. O canal e o bridge foram mantidos vivos explicitamente e funcionaram.

## Lifetime e ordem

`Diagnostic` mantém referências de instância para `view`, `page`, `channel` e
`bridge`. O bridge recebe o channel como parent. A sequência executada foi:

1. `QApplication`;
2. `QWebEngineView`;
3. `DiagnosticPage(view)`;
4. `QWebChannel(page)`;
5. `Bridge(channel)`;
6. `registerObject("bridge", bridge)`;
7. `page.setWebChannel(channel)`;
8. carregar HTML local;
9. HTML cria `#editor`;
10. carregar `qrc:///qtwebchannel/qwebchannel.js` e bundle CodeMirror;
11. `new QWebChannel(qt.webChannelTransport, ...)`;
12. Python recebe `editorReady()`.

## Console e valores observados

Execução headless real:

```text
JS -> Python: editorReady()
HTML loadFinished=True
CodeMirror -> Python: 'ação Ω '
Python -> CodeMirror -> Python: 'ação Ω '
typeof qt -> object
typeof QWebChannel -> function
typeof qt.webChannelTransport -> object
document.readyState -> complete
location.href -> file:///.../editor.html
event loop exit=0
```

Não houve erro JavaScript no diagnóstico final.

## QRC versus arquivo local

`qrc:///qtwebchannel/qwebchannel.js` funcionou no diagnóstico mínimo e na
integração CodeMirror corrigida. O recurso copiado para arquivo local não foi
necessário e não foi testado; portanto não há conclusão comparativa sobre essa
alternativa.

## Prova Python ↔ JavaScript

- JavaScript → Python: `editorReady()` e `receiveContent("ação Ω ")`.
- Python → JavaScript: `runJavaScript` chamou `window.editorApi.setContent`.
- JavaScript → Python novamente: `getContent()` retornou `'ação Ω '`.
- Unicode foi preservado nesse round-trip.

## CodeMirror

Foi usada a linha atual `codemirror` 6.0.1, sem o pacote deprecated
`@codemirror/basic-setup` 0.x. A integração mínima usa CodeMirror real,
`@codemirror/lang-markdown`, `@codemirror/state` e `@codemirror/view`.

Não foram testados preview, search, undo/redo, toolbar, B2 ou arquivos grandes;
eles estão deliberadamente fora deste diagnóstico.

## Headless versus GUI normal

O handshake funcionou em `QT_QPA_PLATFORM=offscreen`, com os flags Chromium
`--no-sandbox --disable-gpu`. O ambiente emitiu warnings de fontes e erros de
GPU/GLES, mas não impediu a comunicação. A GUI normal não foi validada
visualmente neste executor. Comando manual:

```text
uv run python harness/spikes/phase-01-webchannel-diagnostic/run_diagnostic.py
```

sem definir as variáveis headless.

## Conclusão

**QWebChannel validado** para o caso mínimo e para a integração mínima com
CodeMirror 6 no WebEngine local, em headless.

Isso valida a mecânica Python QObject ↔ QWebChannel ↔ JavaScript. Não valida
ainda B1 completa, preview markdown-it, segurança definitiva ou decisão
arquitetural.

## Dependências

- `codemirror` 6.0.1 — MIT — editor — build/runtime asset experimental.
- `@codemirror/lang-markdown` 6.3.2 — MIT — linguagem Markdown — build/runtime
  asset experimental.
- `esbuild` 0.25.12 — MIT — build only.
- Node.js/npm — ferramentas build only; não necessárias no runtime.

## Arquivos

- `diagnostic.html`
- `editor.html`
- `editor.js`
- `editor.bundle.js`
- `run_diagnostic.py`
- `package.json`
- `package-lock.json`
- este relatório
