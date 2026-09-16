# Spike técnico — Editor + Preview (Fase 1)

## Objetivo

Comparar empiricamente um editor Qt nativo (A), CodeMirror em WebEngine com
preview separado (B1) e editor/preview no mesmo WebView (B2), preservando o
Markdown bruto e mantendo a execução offline.

Este artefato é descartável. Nenhum código foi movido para `src/` e nenhuma
decisão permanente foi adicionada a `docs/DECISIONS.md`.

## Ambiente

- Windows, `win32`, CPython 3.13.15.
- PySide6 6.11.2; Qt WebEngine disponível.
- Node.js 24.20.0 e npm 11.19.0 disponíveis localmente.
- Nenhum pacote npm foi incorporado ao projeto de produção.

## Experimentos realizados

`uv run python harness/spikes/phase-01-editor-preview/run_spike.py` executou:

1. `QPlainTextEdit` com fixture contendo frontmatter, GFM, TeX, Mermaid,
   wikilink, diretiva e fenced block desconhecidos.
2. Edição de heading, recuperação, undo e redo.
3. Modelo de bridge estreita com apenas `setContent`, `getContent` e
   `applyBold`, emitindo atualização de preview em cada alteração.
4. Documento sintético com 2.500 repetições da fixture.

A disponibilidade de WebEngine foi verificada importando
`QWebEngineView`. Não foi executado um CodeMirror 6 completo: isso exigiria
assets npm locais que ainda não pertencem ao projeto. Portanto, conclusões
específicas sobre extensões CodeMirror permanecem inferências apoiadas na
arquitetura documentada do editor.

## Código experimental

- `fixture.md`: documento de preservação e Unicode.
- `run_spike.py`: experimento Qt nativo e modelo executável da bridge.

Executar com:

```text
uv run python harness/spikes/phase-01-editor-preview/run_spike.py
```

## Resultados

### FATOS OBSERVADOS

- O `QPlainTextEdit` carregou e recuperou o texto Unicode sem perda aparente.
- A edição produziu evento `textChanged` e o undo/redo nativo restaurou os dois
  estados observados.
- A bridge experimental trafegou o documento como uma string e produziu duas
  atualizações de preview.
- A bridge expõe somente três operações no protótipo; não possui filesystem,
  subprocess, `QApplication` ou `MainWindow`.
- A operação Bold é trivial no lado Qt e também no modelo da bridge.
- O documento grande foi processado sem travamento no experimento sintético;
  esse tempo é apenas qualitativo, não benchmark.
- PySide6 fornece Qt WebEngine no ambiente, mas nenhum bundle CodeMirror foi
  instalado ou executado neste spike.

### INFERÊNCIAS ARQUITETURAIS

- O editor deve ser o dono do histórico undo/redo. Duplicá-lo em Python criaria
  estados divergentes sem benefício observado.
- A comunicação inicial deve enviar o documento inteiro após mudança, com
  debounce posterior se a experiência real demonstrar necessidade. O volume e
  a latência devem ser medidos novamente com CodeMirror real.
- A bridge deve transportar texto e comandos sem expor objetos Qt gerais.
- B1 é preferível a B2 para a primeira implementação: editor e preview têm
  ciclos de vida, segurança e testes separados, enquanto o split-view continua
  sendo responsabilidade Qt.
- A é a opção de menor risco de distribuição e bridge, mas exigirá trabalho
  próprio para highlighting, múltiplos cursores e extensões editoriais.
- B1 oferece melhor caminho para Markdown editorial rico e extensível; requer
  bundle frontend reprodutível e política rigorosa de WebEngine.

### HIPÓTESES NÃO COMPROVADAS

- A latência real de CodeMirror 6 e `markdown-it` em documentos grandes.
- A qualidade exata de múltiplos cursores, find/replace e syntax highlighting
  com a configuração final.
- A integração real de `QWebChannel` com dois WebViews e o custo de memória.
- A escolha final de MathJax/KaTeX, Mermaid e sanitizador HTML.

## Matriz comparativa

| Critério | A — Qt nativo | B1 — dois WebViews | B2 — um WebView |
|---|---|---|---|
| Edição Markdown | básica e comprovada | rica, depende de CodeMirror | rica, depende de CodeMirror |
| Highlighting/extensões | implementação própria | ecossistema CodeMirror | ecossistema CodeMirror |
| Toolbar | seleção Qt direta | bridge estreita | JS/local ou bridge |
| Find/replace | Qt disponível | editor possui comandos | editor possui comandos |
| Undo/redo | comprovado nativo | editor deve possuir | editor deve possuir |
| Cursor/seleção | API Qt direta | API CodeMirror via bridge | API CodeMirror local/bridge |
| Múltiplos cursores | limitado/trabalho próprio | forte potencial | forte potencial |
| Grandes arquivos | simples, risco UI Qt | precisa medir bundle/render | precisa medir render compartilhado |
| Preview/extensões | WebView separado | WebView separado | mesma página |
| Bridge | nenhuma para edição | texto/comandos por WebChannel | menor distância local, mas mais acoplamento |
| Segurança | superfície web só no preview | editor confiável separado do documento | editor e conteúdo compartilham contexto |
| Performance/memória | menor stack | dois WebViews, maior custo | menor custo que B1, ainda WebEngine |
| Offline/distribuição | simples | bundles estáticos locais | bundles estáticos locais |
| Node | não necessário | build-only para assets | build-only para assets |
| Testes | Qt + testes puros | bridge + frontend + Qt | página integrada mais difícil de isolar |
| Preservação do source | natural com texto | natural se preview for somente leitura | natural se preview não mutar editor |
| Lock-in | Qt | CodeMirror/WebEngine | CodeMirror/WebEngine e página acoplada |
| Split-view | Qt nativo | Qt nativo, claro | layout interno + Qt |
| Evolução futura | mais código próprio | melhor separação | maior acoplamento |

## Dependências

| Nome | Versão | Licença | Finalidade | Tipo | Obrigatória | Impacto |
|---|---|---|---|---|---|---|
| PySide6 | 6.11.2 | LGPL-3.0/GPL-3.0 | shell Qt/WebEngine | runtime | já aprovada | já presente |
| CodeMirror 6 | não instalado | MIT | editor web | build/runtime asset | experimental | bundle local a distribuir |
| markdown-it | não instalado | MIT | parser CommonMark/GFM | build/runtime asset | experimental | bundle local a distribuir |
| Node.js/npm | 24.20.0/11.19.0 | licença própria | gerar bundles | build only | não | não exigido ao usuário |

Mermaid e MathJax/KaTeX não foram adicionados nem escolhidos neste spike.

## Segurança

HTML/JavaScript do Markdown deve ser tratado como não confiável. O preview
precisará sanitizar HTML ou desabilitá-lo por padrão, bloquear esquemas
`javascript:`, `data:` e `file:` conforme política futura, e controlar links
externos. O conteúdo renderizado não pode acessar uma bridge privilegiada.

O `QWebChannel` futuro deve expor um objeto dedicado com métodos de texto,
comandos e eventos; nunca filesystem, subprocessos, `QApplication`, janela
principal ou objetos globais. O editor frontend confiável e o HTML derivado do
documento devem ter contextos e permissões separados tanto quanto o WebEngine
permitir.

## Distribuição offline

A recomendação é source JS modular → build determinístico em desenvolvimento →
assets estáticos versionados ou empacotados junto do aplicativo. O runtime não
deve executar Node, chamar CDN, Google Fonts, `fetch` remoto ou API externa.

## Recomendação técnica

Para a Fase 1, recomendo B1:

- Editor: CodeMirror 6 em `QWebEngineView` dedicado.
- Preview: `QWebEngineView` separado.
- Parser inicial: `markdown-it` local, com plugins apenas quando justificados.
- Bridge: `QWebChannel` com API mínima de texto/comandos/eventos.
- Undo/redo e seleção: responsabilidade do CodeMirror.
- Layout/split-view/toolbar Qt: responsabilidade da camada Qt.
- Frontend: bundle estático produzido em build; Node somente build/dev.
- Math e Mermaid: decisões em spike posterior, sempre com assets locais.

B1 mantém o documento bruto como fonte, isola o conteúdo não confiável do
editor e deixa o preview substituível. B2 é aceitável para um protótipo rápido,
mas mistura editor, conteúdo renderizado e segurança no mesmo documento. A
continua sendo fallback caso a medição de CodeMirror/WebEngine real revele
latência, consumo ou distribuição inadequados.

## Decisões ainda abertas

- bundle e versões exatas de CodeMirror/markdown-it;
- plugins GFM e sanitização HTML;
- debounce e estratégia de atualização incremental;
- MathJax versus KaTeX;
- renderer Mermaid e tratamento de falhas;
- política de links externos e imagens locais;
- medição real de arquivos grandes;
- packaging final dos assets.
