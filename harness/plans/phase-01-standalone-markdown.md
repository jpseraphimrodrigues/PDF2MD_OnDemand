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

**Concluída (2026-09-17).** Núcleo puro e adapter filesystem implementados e integrados às ações Open/Save/Save As na etapa 7.

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

**Concluída (2026-09-17, D-015).** Registrado `pdf2md-asset` via
`QWebEngineUrlSchemeHandler` antes do QApplication; handler instalado somente
no profile dedicado ao Preview. Sessões UUID autorizam somente a pasta do
Markdown ativo e são revogáveis. Resolver canônico rejeita absolute/drive/UNC,
file URLs, malformed encoding, traversal, destinos fora da raiz (inclusive
symlink), diretórios e tipos fora de PNG/JPG/JPEG/GIF/WebP. Preview desliga
acesso a arquivos locais/remotos, janelas JS e LocalStorage. O bundle confiável
do Preview é incorporado em shell com origem base QRC para não habilitar
`LocalContentCanAccessFileUrls`. Testes cobrem resolução, revogação, scheme
flags, isolamento/settings do profile e reescrita/bloqueio de imagens no renderer.
Uma execução Qt headless serviu um GIF real pelo handler; teste assíncrono
completo foi instável e não é critério automatizado nesta etapa. Symlink test
pula no Windows do ambiente quando criação não é permitida.

### 6 — Split UI

**Concluída (2026-09-17).** `MainWindow` compõe Editor e Preview em
`QSplitter` horizontal redimensionável. Alterações do Editor são agrupadas por
debounce single-shot de 200 ms; o Preview recebe o conteúdo mais recente.
Teste da composição verifica split, orientação e debounce. Integração usa
widgets substitutos no teste; testes QWebEngine dedicados cobrem Editor e o
bundle do Preview separadamente.

### 7 — Open/Save/Save As

**Concluída (2026-09-17).** Menu File oferece Open, Save e Save As integrados
aos casos de uso e ao `FilesystemDocumentStore`. Open atualiza Editor, sessão
e raiz de assets somente depois de leitura bem-sucedida. Save mantém proteção
por token de versão; Save As pede confirmação antes de overwrite e não substitui
destino alterado concorrentemente. Sessão pathless encaminha Save a Save As.
Testes cobrem round-trip UTF-8/BOM, raízes, cancelamento/confirmação e conflito
externo sem GUI clicks.

### 8 — Dirty/fechamento

**Concluída (2026-09-17).** Abrir outro arquivo e fechar a janela perguntam
Save/Discard/Cancel quando a sessão está dirty. Save ou falha de Save bloqueiam
a transição corretamente; Cancel preserva sessão/conteúdo. O título mostra nome
do arquivo e `*` enquanto houver alterações, e limpa após salvar. Testes cobrem
as decisões e os conflitos sem interação manual.

### 9 — Toolbar

**Concluída (2026-09-17).** Toolbar Qt oferece Bold, Italic, Heading, Link e
Code por whitelist estreita na bridge e transações únicas no CodeMirror. Seleções
vazias inserem marcadores com cursor interno; Link usa placeholders editáveis
`text`/`url`; Heading prefixa a linha atual. Undo/redo continuam no histórico
nativo CodeMirror; sincronizações de conteúdo não entram no histórico. Testes
Node cobrem specs e teste Qt headless prova formatação + Undo sobre Unicode.

### 10 — Segurança/links

**Concluída (2026-09-17).** Preview mantém raw HTML escapado, bloqueia downloads
e popups, desativa acesso remoto/file/localStorage e bloqueia schemes
desconhecidos/perigosos. Navegação interna é limitada aos recursos em subframes;
HTTP/HTTPS só emite pedido quando é link clicado no frame principal, abre
confirmação e usa QDesktopServices após Yes. Redirects, subframes externos e
assets em navegação principal são bloqueados sem abertura externa. Testes da
policy e diálogo confirmam os caminhos permitidos/bloqueados. Redirect/click real
no Chromium não foi automatizado; lógica 
headless foi validada.

### 11 — Regressão/golden

**Concluída (2026-09-17).** Fixture contém frontmatter, wikilink, math,
Mermaid, fence desconhecida, directive e Unicode. Golden compara HTML real do
bundle markdown-it, inclusive a renderização literal de extensões não
implementadas; teste do core comprova round-trip byte a byte sem normalizar
source. Não foram adicionadas extensões nem dependências.

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


## Stop condition — decisão de assets pendente (2026-09-17)

A execução autônoma pausa antes da etapa 5. O plano exige assets relativos
resolvidos sob contexto autorizado e lista duas alternativas de produção:
`QWebEngineUrlSchemeHandler` ou custom URL scheme; D-014 mantém a escolha aberta.
A política de base e permissões afeta diretamente `Open/Save`, pois o documento
pode ser standalone em qualquer diretório. Implementar sem decidir isso pode
abrir filesystem além do diretório do documento ou criar URLs não portáveis.
Nenhuma evidência atual seleciona uma alternativa ou define o contrato do
contexto autorizado. Retomar decidindo/registrando: (a) scheme/handler e (b) se
assets de uma nota standalone podem acessar somente o diretório pai do arquivo,
ou uma raiz selecionada separadamente.

Etapas completas nesta execução: 2 Frontend, 3 Editor/bridge, 4 Preview e 6
Split UI. Etapas 1 e 5, 7–12 permanecem incompletas; etapa 1 tem o núcleo
implementado, porém ainda não integrado à UI.

## Decisão de assets resolvida (D-015, 2026-09-17)

A etapa 5 usará o scheme `pdf2md-asset` servido por
`QWebEngineUrlSchemeHandler`, registrado no startup e instalado somente no
profile dedicado ao Preview. URLs carregam um `document-session-id`; cada sessão
autoriza somente o diretório que contém seu Markdown e pode ser invalidada.
Serão aceitos paths relativos cujo destino canônico permaneça sob essa raiz;
absolute/drive/UNC/file URLs, traversal e symlinks escapando da raiz são
rejeitados. Handler read-only, sem directory listing, somente arquivos regulares
PNG/JPEG/GIF/WebP; SVG arbitrário fica desabilitado. Ver D-015 em
`docs/DECISIONS.md` para a decisão normativa.
