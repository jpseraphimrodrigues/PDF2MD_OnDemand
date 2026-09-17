# Fase 1 — Standalone Markdown

## 1. Objetivo

Entregar `Open .md → Edit → Preview → Save` sem Workspace/Vault, banco, projeto,
login ou IA.

## 2. Estado existente

A Fase 0 fornece shell PySide6, entrypoint `uv` e testes smoke. Os spikes
`phase-01-*` validaram CodeMirror 6, markdown-it, QWebChannel no Editor, dois
WebViews, toolbar experimental, undo/redo, search, Unicode, preview local,
debounce e preservação. A arquitetura B1 está registrada em D-014.

## 3. Restrições

- Markdown bruto é a fonte de verdade; sintaxe desconhecida é preservada.
- Standalone não depende de Workspace/Vault/SQLite.
- UI não possui política de filesystem nem lógica de documento.
- CodeMirror/QWebEngine ficam na UI; domain/application não importam Qt.
- QWebChannel existe somente no Editor; Preview não recebe QObject privilegiado.
- Raw HTML e JavaScript do Markdown ficam desabilitados inicialmente.
- `javascript:`, `data:`, `file:` arbitrário e schemes desconhecidos são
  bloqueados; HTTP/HTTPS exigem ação explícita.
- Assets não liberam filesystem indiscriminadamente.
- Node/npm/esbuild são build-only; runtime usa bundles locais/offline.
- Fora desta fase: Workspace, graph, PDF, OCR, operators, AI, SQLite, tabs,
  autosave sofisticado e rich extensions.

## 4. Riscos e incógnitas

### Fatos confirmados

B1 e a bridge funcionam nos spikes; CodeMirror é dono do undo/redo; markdown-it
restritivo escapa HTML bruto.

### Inferências

`Document` e `DocumentSession` cobrem conteúdo/path e estado aberto/dirty.
Timestamp, tamanho e hash fornecem detecção inicial de alteração externa.

### Hipóteses abertas

Scheme final de assets, CSS/tema/acessibilidade, scroll sync, links externos,
UX de conflito e empacotamento Windows/Linux.

## 5. Desenho proposto

Criar somente responsabilidades justificadas:

```text
src/pdf2md_ondemand/
├── domain/document.py
├── application/document_session.py
├── application/open_document.py
├── application/save_document.py
├── ports/document_store.py
├── adapters/filesystem_document_store.py
└── ui/desktop/
    ├── main_window.py
    ├── editor_view.py
    ├── preview_view.py
    └── editor_bridge.py
frontend/
├── package.json
├── package-lock.json
├── src/
└── dist/
```

`Document` é puro e contém `path`, `content`, `encoding` e metadados mínimos.
`DocumentSession` contém documento aberto, dirty e snapshot externo. QWebEngine
e CodeMirror não são modelo de domínio.

## 6. Estado do documento

Usar path, content bruto, encoding UTF-8, dirty e snapshot com `mtime_ns`, tamanho
e SHA-256. UTF-8 é padrão; BOM UTF-8 e erros de decoding devem ter tratamento
explícito, sem editor universal de encodings.

## 7. Salvamento e alteração externa

Escrever temporário no mesmo diretório, flush e replace/rename atômico quando
suportado. Save As usa o mesmo mecanismo. Falha não pode truncar o original.

Antes de sobrescrever, comparar snapshot externo. Se mudou, não sobrescrever
silenciosamente; informar e permitir cancelar. Merge avançado fica fora da fase.

## 8. Assets e links

Assets internos devem preferir `qrc://`. Assets relativos do documento devem usar
handler/custom scheme controlado, resolver no diretório autorizado, rejeitar
path traversal e impedir caminhos absolutos/escape do contexto. Não usar amplo
`file://` como arquitetura final.

Centralizar navegação do Preview: HTTP/HTTPS podem futuramente abrir fora após
ação explícita; file/javascript/data/desconhecidos são bloqueados.

## 9. Frontend/build

Frontend terá fontes, lockfile e build reproduzível via npm/esbuild. Node não é
runtime. Este plano escolhe produzir bundles durante build/package, mantendo
fonte e lockfile versionados; não versionar `dist` até decisão de distribuição.
Runtime Python não executa npm e não depende de rede/CDN.

## 10. Etapas verificáveis

### 1 — Document/session/filesystem

**Em andamento — núcleo implementado; validação parcial registrada abaixo.**

Criar tipos puros, protocolo e adapter UTF-8. Testar open/save/save-as, dirty,
BOM, erros e snapshot. Conclusão: funciona sem Qt.

### 2 — Frontend

**Concluída (2026-09-17).** Fontes CodeMirror e markdown-it organizadas em
`frontend/src/`, com páginas independentes para Editor e Preview, lockfile npm
e build reproduzível via esbuild. `npm ci` e `npm run build` passaram a partir
de `frontend/`; os bundles gerados e `node_modules/` são ignorados pelo Git.
Auditoria das fontes e bundles não encontrou carregamento remoto de código ou
chamadas de rede; URLs HTTP(S) presentes pertencem a comentários, ao parser
Markdown ou a strings incorporadas. Node/npm permanecem somente ferramentas de
build. O runtime Python ainda precisa empacotar/servir esses recursos quando a
UI for integrada.

### 3 — Editor/bridge

**Concluída (2026-09-17).** `EditorView` carrega o shell local CodeMirror em
QWebEngineView e mantém QWebChannel com `EditorBridge`, expondo somente
`setContent`, `getContent` e `contentChanged`. O Editor sincroniza o texto UTF-8
com a bridge; Preview ainda não recebe nenhum QObject. Testes cobrem contrato
da superfície invocável e round-trip headless Unicode. Limitações: seleção e
cursor ainda não foram exercitados por integração Qt, e produção deve executar
`npm run build` antes de iniciar para gerar o bundle ignorado `frontend/dist`.

### 4 — Preview

**Concluída (2026-09-17).** `PreviewView` usa QWebEngineView separado, sem
QWebChannel ou QObject Python, e renderiza por `markdown-it` local com `html:false`.
A interface Python envia texto JSON-serializado a `window.renderMarkdown`;
source não é modificado. Teste com bundle real verifica Markdown básico, escape
de HTML bruto/script e imutabilidade da entrada. Cobertura Qt end-to-end,
navegação e assets ficam para etapas 5/10.

### 5 — Assets

Implementar resolução controlada de imagens, path traversal e contexto. Avaliar
qrc para internos e custom scheme/handler para documentos.

### 6 — Split UI

**Concluída (2026-09-17).** `MainWindow` compõe Editor e Preview em
`QSplitter` horizontal redimensionável. Alterações do Editor são agrupadas por
debounce single-shot de 200 ms; o Preview recebe o conteúdo mais recente.
Teste da composição verifica split, orientação e debounce. Integração usa
widgets substitutos no teste; testes QWebEngine dedicados cobrem Editor e o
bundle do Preview separadamente.

### 7 — Open/Save/Save As

Adicionar diálogos e integração dos casos de uso; testar path atual e UTF-8.

### 8 — Dirty/fechamento

Atualizar título/estado e confirmação antes de fechar/abrir outro arquivo.

### 9 — Toolbar

Implementar Bold, Italic, Heading, Link e Code via Qt → Python → bridge →
transação CodeMirror.

### 10 — Segurança/links

Aplicar settings, HTML restritivo, bloqueio de schemes e ação explícita para
links externos.

### 11 — Regressão/golden

Adicionar fixtures de frontmatter, wikilink, math, Mermaid, unknown fence,
directive e Unicode; comparar source salvo e HTML esperado.

### 12 — Integração

Executar `uv run pdf2md`, fluxo manual e suíte completa offline.

**Etapa 2 — registro de execução:** arquivos `frontend/package.json`,
`frontend/package-lock.json`, `frontend/src/editor.js`, `editor.html`,
`preview.js`, `preview.html` e `frontend/.gitignore`. Dependências já aceitas
nos spikes: CodeMirror 6 (MIT), markdown-it 14 (MIT) e esbuild (MIT). Critério
de conclusão: fontes separadas, instalação determinística, bundles locais e
nenhuma referência remota necessária ao runtime — atendido. Comandos:
`npm ci` e `npm run build` em `frontend/`.

Cada etapa deve registrar objetivo, arquivos prováveis, dependências, testes e
critério de conclusão antes de ser considerada completa.

### Evidência parcial da etapa 1 (2026-09-17)

Implementados `Document`, `DocumentSession`, casos de uso open/save, porta
`DocumentStore` e adapter de filesystem. O adapter preserva BOM UTF-8 e conteúdo
textual (incluindo CRLF e sintaxe desconhecida), escreve via temporário no mesmo
diretório e impede salvamento normal quando o snapshot mudou. Save As grava no
destino selecionado e atualiza a sessão. Testes e verificações atuais: `uv run
pytest` (5 passed), `uv run ruff check src tests` e `uv run mypy` (sem problemas).

Limite conhecido: a detecção de alteração externa e `os.replace` não formam uma
operação CAS atômica portátil; o token é revalidado imediatamente antes da
substituição, reduzindo a janela de corrida. Em Save As sem overwrite, a criação
de destino novo usa hard-link atômico para impedir que um arquivo criado
concorrentemente seja substituído. `overwrite=True` autoriza `os.replace` para
destino existente, com validação do token observado antes da escrita. A etapa
permanece parcial: integração GUI continua pendente.

### Atualização de concorrência e Save As (2026-09-17)

Save As agora recebe `overwrite=False` por padrão e lança
`DestinationExistsError` sem modificar arquivo/sessão quando o destino já
existe. Com `overwrite=True`, o adapter substitui atomicamente o destino apenas
se a versão observada no início da gravação não mudou. A versão otimista da
sessão é um token SHA-256 dos bytes completos (incluindo BOM); mtime/tamanho não
são usados como identidade da versão. Save normal compara o token no caso de uso
e novamente no adapter antes do replace. Testes direcionados cobrem destino
existente, overwrite explícito, BOM/CRLF/sintaxe desconhecida e mudanças entre
checagem e gravação. Validação: `uv run pytest tests/test_document_session.py`
(6 passed), Ruff direcionado e `uv run mypy` passaram.

## 11. Testes

Core: open UTF-8/BOM, save, save as, dirty, round-trip, preservação, Unicode,
conflito externo e erros de leitura/escrita.

Editor/bridge: set/retrieve, contentChanged, seleção/cursor sob demanda,
toolbar, undo/redo pertencente ao CodeMirror e search.

Preview/security: headings, emphasis, strong, listas, fenced code, links,
tabelas quando naturais, raw HTML escapado, script não executado, schemes
perigosos bloqueados e imagem relativa controlada.

GUI: criação, split redimensionável, diálogos e confirmação de fechamento;
lógica deve ser testada sem cliques.

## 12. Critérios de aceite

`uv run pdf2md` deve permitir selecionar `note.md`, ver o conteúdo no CodeMirror
e Preview, editar, atualizar preview com debounce e salvar o source esperado.
Toolbar mínima, undo/redo, search, Unicode, preservação, segurança HTML/JS,
links bloqueados, imagens controladas e execução offline também devem funcionar.

## 13. Fora da fase

Workspace/Vault, SQLite, backlinks, graph, tags, PDF, OCR, operators, AI,
embeddings, Mermaid/math renderizados, autosave sofisticado, multi-tab, recents
complexos e framework de settings.

## 14. Evidência de conclusão

Registrar comandos, resultados de fixtures e validação manual. Não declarar
sucesso sem execução real.

