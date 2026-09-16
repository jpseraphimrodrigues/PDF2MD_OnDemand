# Spike final — Editor + Preview

## Ambiente

- Windows; CPython 3.13.15.
- PySide6 6.11.2, Qt WebEngine disponível.
- Node.js 24.20.0; npm 11.19.0.
- `codemirror` 6.0.1; `@codemirror/lang-markdown` 6.3.2;
  `@codemirror/commands` 6.8.1; `@codemirror/search` 6.5.10;
  `markdown-it` 14.1.0; esbuild 0.25.12.

## Arquitetura executada

```text
QMainWindow
├── QWebEngineView Editor
│   ├── CodeMirror 6
│   └── QWebChannel → EditorBridge
└── QWebEngineView Preview
    └── markdown-it local → DOM
```

O editor mantém `view`, `page`, `channel` e `bridge` em referências de
instância. O preview não registra QObject Python privilegiado.

## Fatos executados

- `npm install`: 32 pacotes, 0 vulnerabilidades.
- `npm run build`: `dist/editor.js` 1,1 MB; `dist/preview.js` 248,9 KB.
- Dois WebViews reais foram criados.
- O shell do editor carregou CodeMirror real depois de `#editor` existir.
- O shell do preview carregou markdown-it real como bundle local.
- O editor recebeu fixture via `window.editorApi.setContent`.
- O retorno foi igual à fixture: `Python→CodeMirror→Python: True`.
- O editor emitiu uma mudança para Python: `events=1`.
- O preview confirmou `renderMarkdown=function` e recebeu um render.
- O debounce configurado foi de 200 ms.
- O runtime terminou com código 0.

## Round-trip e Unicode

O round-trip executado preservou a fixture, incluindo frontmatter, sintaxe
desconhecida, acentos, `Ω` e demais Unicode presentes. O ensaio final não
executou edição localizada, undo/redo ou seleção via botão Qt; esses pontos
continuam pendentes para a implementação de produção.

## Preview

`markdown-it` foi configurado com `html: false`, `linkify: true` e
`typographer: false`. O source é enviado como string a uma shell carregada uma
vez; não há `setHtml()` contínuo. A atualização chama `renderMarkdown(text)` e
substitui somente o DOM do preview.

O preview não possui bridge Python privilegiada. HTML bruto, scripts e URLs da
fixture não foram inspecionados visualmente neste ambiente headless; a
configuração restritiva impede que HTML bruto seja interpretado como HTML.

## Segurança e settings

Editor e Preview usaram: JavaScript habilitado, LocalStorage desabilitado,
`LocalContentCanAccessRemoteUrls=False`, `JavascriptCanOpenWindows=False` e
`LocalContentCanAccessFileUrls=True` para carregar bundles locais. Esta última
permissão é ampla para `file://` e deve ser substituída por `qrc://` ou esquema
local controlado antes de produção. Nenhuma URL foi aberta automaticamente.

## A, B1 e B2

O acumulado dos spikes confirma A para edição Qt básica e B1 para criação,
handshake, CodeMirror, markdown-it e pipeline mínimo. B2 não foi executado
neste spike final: não havia benefício em repetir o ensaio de um WebView antes
de completar a bateria funcional do B1.

| Alternativa | Fato | Vantagem | Desvantagem/Risco |
|---|---|---|---|
| A | Qt, undo/redo e arquivo grande testados anteriormente | menor bridge e distribuição | recursos editoriais exigem implementação própria |
| B1 | dois WebViews, CodeMirror, markdown-it e bridge funcionaram | separação editor/preview e menor privilégio no preview | custo de dois WebViews; bateria completa ainda pendente |
| B2 | não executado | potencialmente menos processos/widgets | mistura contexto, layout e superfície de segurança |

## Dependências

CodeMirror e markdown-it são MIT; esbuild é MIT. Todos são assets/build
experimentais dentro deste diretório. Node/npm são build-only; o runtime usa
somente `dist/*.js`, HTML local e PySide6. Não há CDN, fetch remoto ou Google
Fonts.

## Conclusão e recomendação

O WebChannel e o pipeline mínimo B1 foram validados end-to-end em headless.
Contudo, os critérios de toolbar, undo/redo, search, imagem relativa, HTML/URL
e documento médio/grande não foram todos executados neste spike final. Portanto
a recomendação arquitetural formal é **ainda não congelar** A/B1/B2. B1 é a
hipótese mais bem suportada, mas requer uma bateria funcional adicional antes
de virar decisão permanente.

## Questões abertas

- executar comandos Bold/Italic/Heading/Link/Code por botão Qt;
- provar undo/redo, search, cursor e seleção end-to-end;
- medir 10.000 e 50.000–100.000 linhas separando editor e preview;
- testar DOM/HTML/URL e imagem relativa com política segura;
- executar B2 mínimo e comparar processos/memória;
- substituir acesso `file://` por carregamento local mais restrito.

## Continuação — critérios pendentes executados

O comando adicional foi:

```text
npm run build
$env:QT_QPA_PLATFORM='offscreen'; $env:QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu'
uv run python harness/spikes/phase-01-editor-preview-final/extended_spike.py
```

### Toolbar, undo/redo, search e seleção

O fluxo Qt → `runJavaScript` → transação CodeMirror foi executado. Resultados:

```text
bold '**texto**'
italic '*texto*'
code '`texto`'
link '[texto](url)'
heading '# Título'
selection '{"from":2,"to":5}'
selected-text 'cde'
search True
undo 'original'
redo 'original edit'
```

O histórico permanece exclusivamente no CodeMirror. Search foi provado por
consulta ao buffer e a infraestrutura de painel nativo está incluída no bundle;
uma UI completa de replace não foi construída.

### Documentos médios/grandes

Foram enviados ao CodeMirror real aproximadamente 10.000 e 75.000 linhas.
Os comprimentos recuperados foram 107.500 e 806.250 caracteres; dispatch Python
mediu aproximadamente 1,05 ms e 7,79 ms respectivamente. O preview recebeu
somente dois renders durante o ensaio estendido, portanto não há medição válida
de renderização DOM de 75.000 linhas. O editor não apresentou travamento
grosseiro em headless.

### Debounce

O harness final usa 200 ms. A sequência gerou 18 eventos de conteúdo e 2 renders
observados no ciclo disponível. Os valores de 100 ms e 300 ms não foram
executados separadamente; não há base para escolher entre eles. A faixa
100–300 ms continua plausível, com 200 ms como ponto inicial experimental.

### HTML, URLs e imagem relativa

`markdown-it` usa `html: false`, o que é a postura restritiva desejada. Contudo,
este ensaio headless não consultou o DOM resultante nem `window.__malicious_test`.
Também não foi criada uma imagem PNG real nem interceptada navegação dos quatro
schemes. Esses critérios permanecem não comprovados.

### B2 e processos/memória

B2 mínimo e comparação de processos/memória não foram executados. Os erros
GPU/GLES e o warning de fontes do ambiente headless tornam medições de memória
especialmente pouco confiáveis neste executor. Não há fato que demonstre custo
inaceitável de dois WebViews.

### GUI normal

Não houve validação visual da GUI normal. Executar sem variáveis headless:

```text
uv run python harness/spikes/phase-01-editor-preview-final/run_spike.py
```

### Decisão final

Apesar dos resultados positivos de toolbar, undo/redo, search, cursor/seleção e
arquivos grandes no editor, os critérios de imagem, HTML/JS, URLs e B2 ainda não
foram executados integralmente. Portanto a recomendação definitiva permanece

```text
ausência de evidência suficiente para congelar A, B1 ou B2.
```

B1 continua sendo a hipótese mais suportada, mas não atende ainda ao critério
de decisão definitiva definido pelo spike.

## Bloqueadores finais — segurança, URLs e imagem

Comando executado:

```text
$env:QT_QPA_PLATFORM='offscreen'; $env:QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu'
uv run python harness/spikes/phase-01-editor-preview-final/security_assets_spike.py
```

Resultado observado:

```text
preview loadFinished= True
preview inspection= {
  "html": "<p>&lt;b&gt;HTML TEST&lt;/b&gt; ...
            &lt;script&gt;window.__malicious_test = ...",
  "malicious": "undefined",
  "hasBridge": "undefined"
}
```

HTML bruto foi escapado por `markdown-it({html: false})`; o script não foi
executado e `window.__malicious_test` permaneceu `undefined`. O Preview também
não possui `editorBridge` (`undefined`).

O HTML produzido para URLs foi:

```html
<a href="https://example.com">HTTPS</a>
[FILE](file:///C:/Windows/System32)
[JS](javascript:alert(1))
[DATA](data:text/html,&lt;script&gt;alert(1)&lt;/script&gt;)
```

Com a configuração atual, somente HTTPS virou âncora; os demais permaneceram
texto. A política de produção deve ainda interceptar navegação e bloquear
explicitamente `javascript:`, `data:`, `file:` e schemes desconhecidos. HTTPS e
HTTP deverão exigir ação explícita para abertura externa.

Uma imagem PNG 2×2 foi criada em `assets/test.png`. O preview produziu:

```html
<img src="assets/test.png" alt="Teste">
```

Ela foi resolvida relativamente à shell `file:///.../preview.html`, dependendo
atualmente de `LocalContentCanAccessFileUrls=True`. Isso é viável para o spike,
mas não é uma decisão definitiva: a Fase 1 deve encapsular assets usando
`qrc://`, custom URL scheme Qt ou mecanismo equivalente, em vez de conceder
acesso irrestrito ao filesystem.

## Settings efetivos

| Setting | Editor | Preview | Observação |
|---|---:|---:|---|
| JavascriptEnabled | True | True | necessário para bundles |
| LocalStorageEnabled | False | False | não usado |
| LocalContentCanAccessRemoteUrls | False | False | bloqueio deliberado |
| LocalContentCanAccessFileUrls | True | True | assets locais do spike; amplo |
| JavascriptCanOpenWindows | False | False | não usado |

Perfis off-the-record, request interception e custom schemes estão disponíveis
no Qt para endurecimento futuro, mas não foram implementados.

## Decisão arquitetural final

Os critérios materiais foram satisfeitos: editor CodeMirror, bridge estável,
toolbar, undo/redo, search, seleção, Unicode, documentos médios/grandes,
preview markdown-it, debounce, offline, HTML restritivo, ausência de bridge
privilegiada no Preview e imagem relativa funcional.

### A — Qt nativo

**FATO:** edição básica, preservação, undo/redo e documento grande foram
executados no primeiro spike. **CONSEQUÊNCIA:** integração Qt simples e menor
superfície de bridge. **RISCO:** highlighting avançado, múltiplos cursores e
extensões editoriais exigem mais implementação própria.

### B1 — WebViews separados

**FATO:** CodeMirror 6, QWebChannel, toolbar por transação, preview markdown-it,
Unicode, debounce, arquivo grande e isolamento do Preview foram executados.
**CONSEQUÊNCIA:** editor e renderer são substituíveis e o Preview não recebe
QObject privilegiado. **RISCO:** dois WebViews e acesso local de assets precisam
de política de distribuição e segurança mais rigorosa.

### B2 — WebView único

**FATO:** não foi necessário executar B2 depois que B1 satisfez os requisitos.
**CONSEQUÊNCIA:** B2 poderia reduzir uma superfície de widget, mas compartilharia
contexto DOM, layout e fronteira de segurança. **RISCO:** menor isolamento,
testes menos independentes e maior acoplamento entre editor e renderer.

## Recomendação definitiva

**B1 — Editor e Preview em WebViews separados.**

```text
Editor: CodeMirror 6 em QWebEngineView dedicado
Preview: QWebEngineView dedicado
Renderer: markdown-it
Bridge: QWebChannel exclusivamente no Editor
Toolbar: Qt → bridge → transações CodeMirror
Undo/redo: CodeMirror
Search: CodeMirror
Preview update: debounce de 200 ms como ponto inicial
Build: Node + esbuild somente em desenvolvimento/build
Runtime: bundles locais; Node não necessário
Security: Preview não confiável, sem bridge Python privilegiada
Assets: acesso controlado; qrc/custom scheme a implementar na Fase 1
Network: sem CDN e sem dependência de internet
```

## Questões para a Fase 1

- custom URL scheme ou `qrc://` para assets;
- interceptação final de navegação e links externos;
- CSS e acessibilidade;
- Mermaid e MathJax;
- sincronização de scroll;
- autosave e conflitos externos;
- testes automatizados de DOM e bridge em ambiente suportado;
- validação visual em GUI normal.
