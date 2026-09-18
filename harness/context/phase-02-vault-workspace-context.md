# Fase 2 Workspace/Vault — Contexto de execução

## Objetivo

Dar suporte a uma pasta local-first de documentos Markdown, com navegação,
metadados e relações derivadas, busca e atualização incremental. Esta fase é
planejada. Retomada autônoma em 2026-09-17: E1 já existia e E2 estava
parcialmente implementada.

## Evidência herdada da Fase 1

- `domain/document.py`: `Document(path, content, utf8_bom)` é representação
  simples e preserva conteúdo bruto.
- `application/document_session.py`: sessão toolkit-independent rastreia
  baseline, dirty e token SHA-256 de bytes. Não contém conhecimento de workspace.
- `application/open_document.py` e `save_document.py`: casos de uso usam a
  porta `DocumentStore`.
- `adapters/filesystem_document_store.py`: UTF-8/BOM, escrita atômica e
  proteção otimista contra alteração externa.
- `ui/desktop/main_window.py`: hoje instancia store, mantém uma única
  `DocumentSession`, conecta Editor/Preview e aplica confirmação
  Save/Discard/Cancel para abrir/fechar. `open_document_at` é o ponto atual de
  integração de navegação.
- `EditorView` usa CodeMirror via QWebEngine; `EditorBridge` expõe superfície
  estreita; `PreviewView` é QWebEngine separado e sem bridge privilegiada.
- `AssetSessionRegistry` e `PreviewAssetHandler` implementam D-015; raiz atual
  do asset standalone é o diretório do documento.
- Não foram encontrados módulos atuais de workspace, parser para indexação,
  SQLite, árvore/navegação, busca de vault, links/backlinks ou watcher.

## Decisões vinculantes

- Markdown é fonte de verdade. Tudo em `.pdf2md/` é rebuildável; apagar esse
  diretório não pode remover informação do usuário.
- Standalone continua abrindo um `.md` sem construir/abrir workspace, banco ou
  conversor.
- `DocumentSession` não conhece workspace, backlinks, índices ou grafo.
- `WorkspaceSession` é orquestração de aplicação e reutiliza casos de uso de
  documento quando navega/abre uma nota.
- Persistência de índice acessada por porta. SQLite padrão Python é escolha
  preferida para adapter local, sem nova dependência, desde que FTS5 não seja
  pressuposto sem verificar disponibilidade.
- Resolução ambígua de wikilink não escolhe alvo arbitrariamente.
- Indexação é somente leitura, nunca canonicaliza/escreve Markdown.
- D-014 governa isolamento Editor/Preview; D-015 governa acesso a assets e
  restrição de raiz.

## Sequência autorizada pelo plano

E1 contratos/sessão → E2 descoberta/árvore → E3 extração → E4 resolução e
backlinks → E5 SQLite e rebuild → E6 busca → E7 atualização incremental →
E8 watcher/reconciliação → E9 integração e regressão. Cada incremento deve
ser pequeno, testado e commitável; nenhuma etapa requer permissão intermediária
em execução autônoma normal. Parar somente nos stop conditions de AGENTS.md.

Dependências detalhadas, critérios e testes estão em
`harness/plans/phase-02-vault-workspace.md`.

## E1 — Contratos de workspace e sessão vazia (2026-09-17)

Implementados `application/workspace_session.py` com `WorkspaceRoot` (caminho
absoluto e lexicalmente normalizado, sem exigir que exista) e
`WorkspaceSession.open/close`, sem persistência, acesso a arquivos ou imports de
UI/document session. `tests/test_workspace_session.py` cobre identidade,
ciclo e independência de `DocumentSession`.

Validação: `.venv/Scripts/python.exe -m pytest -p no:cacheprovider
tests/test_workspace_session.py` (3 passed), `.venv/Scripts/ruff.exe check src
tests` e `.venv/Scripts/mypy` passaram. `uv` e o diretório temporário global
deram acesso negado neste ambiente; a suíte focada foi executada pela venv local.

## Pontos a concretizar durante execução

- Precedência de título/frontmatter e política de headings/anchors.
- Gramática mínima de tags, links Markdown e wikilinks (incluindo alias,
  fragmento e extensão opcional).
- Regras portáveis de case e exclusões de descoberta.
- Esquema/versionamento do índice em `.pdf2md` e disponibilidade de FTS5.
- Semântica e ordenação da busca.
- Estratégia do watcher por plataforma, debounce e reconciliação.
- Aplicação da raiz permitida de asset quando nota faz parte do workspace,
  mantendo o princípio de menor privilégio de D-015.

## Retomada autônoma — estado E2–E9 (2026-09-17)

### E2 — descoberta/árvore

- `application/workspace_session.py`: descoberta `.md` recursiva, ordenação
  determinística (diretórios primeiro), exclusão `.pdf2md`/configuradas,
  caminhos relativos, tolerância a erro parcial e rejeição de symlinks.
- `MainWindow`: Open Folder, árvore em dock e abertura por
  `open_document_at`, preservando Save/Discard/Cancel e sessão atual em erro.
- `tests/test_workspace_discovery.py` cobre filtros, unicode, ordem e raízes
  inválidas; symlink foi `skip` por WinError 1314.
- Achado/correção de produto: ordem inicial não atendia o teste/UX esperado;
  diretórios agora aparecem antes de arquivos com ordenação casefold.

### E3 — extração e snapshot em memória

- Extração sem dependência runtime de título (`frontmatter title` simples, H1,
  basename), headings/anchors slug repetidos, tags inline/frontmatter
  string/list, wikilinks e links Markdown com offsets.
- Ignora blocos fenced e inline code na extração. O frontmatter é deliberadamente
  limitado, sem parser YAML; source bruto acompanha snapshot e não é escrito.
- `tests/test_markdown_metadata.py`: precedência, Unicode, headings duplicados,
  código, tags, alvos/aliases/offsets e source intacto.

### E4 — resolução/backlinks

- Estado resolved/broken/ambiguous/external, links relativos, wikilink por
  basename único ou caminho explícito, âncora derivada e backlinks inversos.
- Caso coberto: resolvido com fragmento, quebrado, basename ambíguo e externo.

### E5 — SQLite derivado/rebuild

- `ports/workspace_index.py` + `adapters/sqlite_workspace_index.py`; banco em
  `.pdf2md/index.sqlite3`, schema version 1, fingerprint SHA-256, transação de
  publicação, metadados/relações derivadas e load/rebuild equivalentes.
- Corrigido durante teste: conexão SQLite não fechava e snapshot não era
  confirmado. Round-trip, exclusão do índice, rebuild e source inalterado
  passaram em `tests/test_sqlite_workspace_index.py`.

### E6 — busca

- Substring casefold Unicode, primeira ocorrência por linha, limite 100,
  snippets e ordenação relativa estável; helper valida path de resultado antes
  de abrir. Sem dependência externa.

### E7 — atualização/reconciliação

- `reindex(changed_paths)` atualmente faz scan integral determinístico e
  publicação atômica, garantindo equivalência com rebuild sem otimização por
  arquivo. Teste valida edição e remoção. Isso é residual de desempenho, não de
  correção.

### E8 — watcher/reconciliação

- Port opcional `WorkspaceWatcher`; `WorkspaceSession` coalesce paths, entrega
  lote pendente e limpa ao fechar; `reconcile` chama rebuild. Nenhum watcher
  concreto de SO foi adicionado: dependência runtime evitada; consistência vem
  de rebuild/reconciliação explícita.

### E9 — integração e regressão

- Teste com doubles em `test_main_window.py` valida árvore, cancelamento e
  abertura com discard; Preview continua sem bridge e asset root por diretório
  da nota (D-015).
- Menu oferece Open Folder, Close Workspace, busca sobre o índice existente e
  rebuild manual do índice. Close Workspace mantém documento aberto e confirma
  dirty state; título volta a standalone ou inclui workspace/documento.
- Busca inicial é síncrona e oferece o primeiro resultado confirmado pelo
  usuário; o índice precisa ter sido reconstruído manualmente antes da busca.
- Standalone não instancia índice automaticamente; abertura de `.md` segue
  workflow Fase 1.

### Validação e limitações ambientais

- Passou: suíte workspace/parser/SQLite: 11 passed, 1 skipped; Ruff completo;
  mypy completo. Teste UI novo e debounce por doubles passaram.
- `DEFERRED_ENVIRONMENT_VALIDATION`: testes baseados em `tmp_path` falham no
  setup/cleanup ao enumerar basetemp com `PermissionError`, inclusive após
  definir TMP/TEMP e `--basetemp` em pasta recém-criada. Teste core independente
  de `tmp_path` foi alternativa bem-sucedida.
- `DEFERRED_ENVIRONMENT_VALIDATION`: symlink real não pode ser criado (WinError
  1314). A suíte marca skip; não indica falha do algoritmo.
- `DEFERRED_ENVIRONMENT_VALIDATION`: suíte WebEngine abortou fatalmente no host
  offscreen carregando HTML confiável; exige runner GUI funcional.
- `DEFERRED_ENVIRONMENT_VALIDATION`: integração com watcher de sistema real não
  foi exercida; contrato/coalescing/rebuild são determinísticos.

Checkpoints pretendidos (não criados):

1. `feat(workspace): add safe markdown discovery and tree navigation`
2. `feat(workspace): extract markdown metadata and resolve backlinks`
3. `feat(workspace): add rebuildable sqlite index and search`
4. `feat(workspace): reconcile workspace changes and integrate navigation`

Risco residual: E8 não inclui watcher de SO; parser é subconjunto Markdown
conservador (YAML simples e padrões regex); reindexação é full scan; rebuild e
busca na UI são síncronos e podem bloquear em vaults grandes. O usuário pode
reconstruir o índice e Markdown permanece canônico.

Esses detalhes não são decisões arquiteturais impeditivas na elaboração do
plano. Se a execução revelar dependência nova, incompatibilidade de D-014/D-015
ou mudança material de arquitetura, atualizar `docs/DECISIONS.md` e parar para
decisão humana conforme o protocolo do repositório.

## Riscos residuais conhecidos

- O lifecycle atual está concentrado em `MainWindow`; integração precisa mover
  orquestração para casos de uso sem perder a confirmação de alterações não
  salvas.
- Watchers variam em confiabilidade em pastas sincronizadas/remotas/removíveis.
- Resolução case-insensitive não tem semântica uniforme em todos os filesystems.
- Symlink pode escapar da raiz se descoberta/resolução não canonizar e limitar.
- FTS5 depende da build SQLite disponível; prever fallback ou erro explícito.
- Testes WebEngine anteriores têm limitações de determinismo descritas no
  contexto da Fase 1 e não devem ser usados como única validação.
