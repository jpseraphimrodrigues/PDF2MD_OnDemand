# Spike 1B — CodeMirror 6 + markdown-it + QWebChannel

## Ambiente

- Windows, CPython 3.13.15.
- PySide6 6.11.2; `QWebEngineView` disponível.
- Node.js 24.20.0; npm 11.19.0.
- CodeMirror: `@codemirror/basic-setup` 0.20.0, `@codemirror/commands` 6.8.1,
  `@codemirror/lang-markdown` 6.3.2, `@codemirror/language` 6.11.0,
  `@codemirror/search` 6.5.10, `@codemirror/state` 6.5.2 e
  `@codemirror/view` 6.36.5.
- markdown-it 14.1.0.
- esbuild 0.25.12.

## Dependências e licenças

CodeMirror 6, markdown-it e esbuild foram usados somente no diretório do spike.
CodeMirror e markdown-it são MIT; esbuild é MIT. Node/npm são ferramentas de
build, não runtime. O bundle resultante é local; não há CDN.

## Arquitetura B1 executada

O protótipo contém dois `QWebEngineView` reais, duas páginas locais e dois
`QWebChannel` Python. O editor usa CodeMirror 6 real e o preview usa markdown-it
real. O fluxo pretendido é:

```text
Qt ↔ QWebChannel ↔ CodeMirror 6
CodeMirror change → Python debounce 150 ms → QWebChannel/JS → markdown-it → DOM
```

## Fatos observados

- `npm install` resolveu 63 pacotes e não reportou vulnerabilidades.
- `npm run build` gerou `dist/editor.js` de 2,7 MB e `dist/preview.js` de 249 KB.
- Ambas as shells locais carregaram (`editor shell loaded: True` e `preview shell
  loaded: True`).
- Dois WebViews e dois canais Python foram criados sem erro de construção.
- O editor não emitiu `documentReady` e o preview não emitiu `previewReady`.
- O contador de renders foi 1 após renderização direta de fallback; o handshake
  QWebChannel não foi comprovado.
- O runtime headless emitiu erros de GPU/Skia e warning de fontes do PySide6.
- Nenhuma inspeção gráfica foi possível.

## Interpretação

CodeMirror 6 e markdown-it foram realmente empacotados, mas a integração
end-to-end ainda não está validada. O bootstrap `qrc:///qtwebchannel/qwebchannel.js`
não completou o handshake no ambiente testado, mesmo usando `file://` local em
vez de `setHtml()`. Isso impede declarar B1 aprovada.

O uso de `setHtml()` foi removido do fluxo contínuo; as shells são carregadas
como arquivos locais e o preview seria atualizado por DOM após o handshake.
Assim, o limite aproximado de 2 MB do `setHtml()` não é usado para renders.

## O que não foi comprovado

Por causa do handshake ausente, não foram validados end-to-end: set/get content,
edição CodeMirror, undo/redo, seleção, Bold externo, search, Unicode atravessando
a bridge, preservação após recuperação, preview markdown-it, HTML/URLs e debounce
real de eventos. O código frontend contém essas operações, mas isso não é
evidência de execução.

## Segurança configurada

O editor habilita JavaScript, desabilita LocalStorage, bloqueia acesso a URLs
remotas e permite acesso a arquivos locais apenas para carregar assets locais.
O preview usa a mesma política de JavaScript para o parser local, desabilita
LocalStorage, bloqueia URLs remotas e não recebe bridge privilegiada. A política
definitiva ainda deve desabilitar HTML bruto no markdown-it, sanitizar o DOM e
validar esquemas de links (`https`, `file`, `javascript`, `data`) antes de
navegação.

## B1 × B2

B2 não foi executado: B1 não alcançou o handshake mínimo necessário para uma
comparação válida. A hipótese permanece que B1 oferece isolamento melhor entre
editor confiável e preview com Markdown não confiável; B2 poderia reduzir um
WebView, mas compartilharia contexto, layout e superfície de segurança.

## Recomendação

Nenhuma decisão arquitetural deve ser congelada. A stack CodeMirror/markdown-it
continua plausível, mas B1 deve ser considerada **não validada** até o handshake
real funcionar e os testes end-to-end acima passarem. O próximo ensaio deve
isolar a causa do carregamento do `qwebchannel.js` e adicionar captura explícita
de console JavaScript.

## Comandos

```text
npm install
npm run build
$env:QT_QPA_PLATFORM='offscreen'; $env:QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu'
uv run python harness/spikes/phase-01-editor-preview-web/run_spike.py
```

## Questões abertas

- Por que o recurso `qrc:///qtwebchannel/qwebchannel.js` não completa o handshake
  no WebEngine 6.11.2 deste ambiente.
- Política final de HTML, URLs e sandbox.
- Medição real de 10.000 e 50.000–100.000 linhas após o canal funcionar.
- Comparação de processos/memória entre B1 e B2.
- Versões finais dos pacotes e estratégia de distribuição dos bundles.
