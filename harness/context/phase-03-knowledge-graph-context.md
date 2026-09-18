# Fase 3 Knowledge Graph — Contexto

## Objetivo e limites

Adicionar grafo de conhecimento local-first sobre o Workspace/Vault da Fase 2.
Markdown permanece fonte de verdade. Não implementar conversão PDF → Markdown,
IA, RAG, embeddings, busca semântica, cloud, graph database externo nem
funcionalidades de clustering/layout avançadas.

## Evidência arquitetural e decisões herdadas

- `docs/DECISIONS.md`: D-001 produto é workspace Markdown; D-002 modo standalone
  obrigatório; D-003 Markdown autoritativo e índice derivado; D-007 PySide6 com
  superfícies web atrás de pontes estreitas; D-008 SQLite no workspace é
  derivado; D-009 grafo inicial 2D; D-014 separa Editor e Preview, que não deve
  receber bridge privilegiada; D-015 limita recursos locais do Preview.
- `docs/ARCHITECTURE.md` §8 já determina DTO serializável `Graph = nodes + edges`
  e adapter de renderização sem estado Cytoscape no domínio.
- O log ainda lista implementação exata do renderer como aberta. Fazer avaliação
  concreta no gate de UI; não adicionar runtime/frontend dependency antes de
  avaliar licença, offline, manutenção e impacto no build. Cytoscape.js é
  candidato, não decisão irrevogável.
- Identidade escolhida para esta fase: caminho relativo normalizado da nota no
  workspace; não exigir frontmatter ID nem alterar links ordinários.
- Tags ficam como filtro baseado nos metadados existentes, não como nós na
  primeira versão. A arquitetura não justifica ainda incidência documento-tag.
- Backlinks são apenas arestas invertidas derivadas; nenhum campo mutável novo
  vira fonte de verdade.

## Mapeamento do código existente

- `src/pdf2md_ondemand/application/workspace_session.py`
  - `WorkspaceNote` guarda caminho relativo, metadados e conteúdo indexado.
  - `WorkspaceSnapshot` contém notas, referências resolvidas e backlinks.
  - `build_workspace_snapshot` extrai título, headings, tags, wikilinks e links
    Markdown; `resolve_workspace_references` classifica referências e deriva
    backlinks. Reutilizar; não criar parser para graph view.
  - `WorkspaceSession` cuida do ciclo workspace, snapshot/index e reconciliação.
- `src/pdf2md_ondemand/ports/workspace_index.py` define interface do índice.
- `src/pdf2md_ondemand/adapters/sqlite_workspace_index.py` grava e lê estado
  derivado em `.pdf2md/index.sqlite3`; rebuild relê Markdown e publica snapshot.
- `src/pdf2md_ondemand/application/document_session.py` é independente; não
  adicionar dependência de grafo/workspace.
- `src/pdf2md_ondemand/ui/desktop/main_window.py` cria árvore/dock e controla
  lifecycle. `open_document_at(path)` é entrada vigente de navegação e
  preserva confirmação de dirty state. Busca/rebuild atuais acessam índice a
  partir da janela; evitar espalhar regra de negócio adicional para widgets.
- `tests/test_markdown_metadata.py`, `tests/test_sqlite_workspace_index.py`,
  `tests/test_workspace_session.py` e `tests/test_main_window.py` cobrem lógica e
  regressões relevantes a estender.
- Frontend editor existente usa assets locais/build; renderer do grafo precisa
  permanecer offline e não compartilhar bridge privilegiada com Preview.

## Contratos comportamentais para implementação

- Nós iniciais: documentos Markdown do snapshot, inclusive órfãos.
- Arestas: referências locais resolvidas, com tipo wikilink/Markdown, origem e
  destino por identidade estável. Backlink é aresta inversa consultável.
- Link quebrado/ambíguo: diagnosticável e filtrável/detalhável, sem nó fictício.
  Link externo não é aresta de conhecimento interna.
- Vizinhança/filtros são consultas puras sobre DTO e não modificam snapshot.
- A view recebe DTO/estado via aplicação; não varre diretório, não abre SQLite e
  não interpreta Markdown.
- Ativação de nó chama workflow de abertura já usado pela árvore, inclusive
  Cancel/Save/Discard. Seleção sincroniza árvore/editor/grafo na camada UI.
- Edição, eventos externos e rebuild atualizam/reprojetam a estrutura a partir
  do snapshot publicado; falha não publica estado parcial.
- Posições são estado visual opcional. Padrão não persistir até demonstração de
  necessidade; cache eventual vive em `.pdf2md/`, versionado e descartável.
- Se projeção/layout tornar UI perceptivelmente lenta, usar infraestrutura de
  trabalho em background da aplicação, sem mover parsing para widgets.

## Entregas e execução

Plano autoritativo: `harness/plans/phase-03-knowledge-graph.md`. Ordem:

1. E1 DTO e projeção em memória;
2. E2 vizinhança e filtros puros;
3. E3 integração com sessão/índice;
4. E4 visualização 2D e gate do renderer/dependência;
5. E5 seleção e navegação sincronizadas;
6. E6 atualização/layout derivado e performance;
7. E7 documentação, regressão e aceite manual.

Cada entrega requer testes focados determinísticos e checkpoint pretendido
definido no plano. Antes de dependência de produção ou mudança arquitetural
material, aplicar stop condition e atualizar `docs/DECISIONS.md` com evidência.

## Riscos e validação

- Path identity e case podem variar por filesystem; manter representação
  portátil e evitar resolver ambiguidades automaticamente.
- Várias referências entre dois documentos podem ter tipos diferentes ou
  contagem múltipla; DTO deve definir deduplicação sem apagar semântica.
- Index/rebuild atual é síncrono/full scan; graph projection não deve duplicar
  leitura/parsing e deve ser medida antes de adicionar async mais amplo.
- Seleção sincronizada pode gerar loops de sinal ou contornar dirty-state.
- UI WebEngine pode falhar em host offscreen; usar lógica de domínio/doubles e
  registrar `DEFERRED_ENVIRONMENT_VALIDATION` se runner gráfico não disponível.
- Limitações de `tmp_path` e symlink descritas na Fase 2 persistem; preferir
  fixtures determinísticas compatíveis com o host e não mascarar falha produto.

## Execução concluída — 2026-09-17

### E1/E2 — domínio e consultas

- Adicionados `domain/graph.py`, `application/build_graph.py` e
  `application/query_graph.py`.
- DTOs imutáveis com conversão JSON-compatível; caminhos relativos são
  normalizados em POSIX e rejeitam absoluto/traversal. Arestas mantêm tipo,
  label, anchor status e contagem de ocorrências. Issues guardam links quebrados
  e ambíguos sem criar nós fictícios. Backlinks são calculados como inversão.
- Consultas suportam raio em ambas direções, texto, tags, tipo, status de issues
  e exclusão de órfãos; não alteram snapshot.

### E3 — sessão/índice

- `WorkspaceSession.open(root, index=...)` mantém o port do índice derivado;
  `knowledge_graph()` lê o snapshot publicado e projeta sem parser novo. `close`
  descarta o port e operações após close falham explicitamente.
- A view/MainWindow chama a sessão para rebuild e projeção. A criação do adapter
  acontece ao abrir o workspace; nenhum acesso SQLite foi colocado no widget.

### E4/E5 — UI e navegação

- `ui/desktop/graph_view.py` implementa canvas Qt nativo: layout circular
  determinístico, nodes selecionáveis, linhas direcionais coloridas por tipo,
  panning, zoom, filtros de texto/tags/tipos/órfãos e contagem de issues.
- `MainWindow` mostra o dock somente com Workspace aberto. Duplo clique usa
  `open_document_at`; árvore, documento atual e grafo sincronizam seleção.
  Cancelamento restaura a nota selecionada antes da tentativa de navegação.
  Atualização falha mantém grafo publicado e informa o problema.
- Renderer nativo usa dependência existente PySide6; não houve nova dependência
  frontend/runtime. Posições não são salvas.

### E6/E7 — atualizações, validação e residual

- Abrir Workspace cria/reconstrói o snapshot do índice antes da view. Save e
  Save As dentro do workspace fazem rebuild; saves standalone não o fazem.
  Rebuild manual atualiza o grafo após alterações externas. Não há watcher de SO
  herdado da Fase 2, então o refresh externo é explícito.
- Testes focados finais: 12 passaram, incluindo projeção determinística e JSON,
  filtros/vizinhança, session/index, cancelamento e canvas Qt com aresta.
- `ruff check src tests`: passou. `mypy`: passou. Build esbuild frontend: passou,
  mas os testes Node deram `spawn EPERM`. `uv run --offline pytest` falhou antes
  do runner por acesso negado ao cache global uv. Testes dependentes de `tmp_path`
  falham enumerando basetemp com WinError 5; a suíte WebEngine completa não foi
  repetida devido ao abort offscreen conhecido na Fase 2.
- As validações de ambiente indisponíveis estão marcadas
  `DEFERRED_ENVIRONMENT_VALIDATION` no plano. A validação manual restante inclui
  vault de tamanho médio no host Qt, filtro e navegação completos, alteração
  externa com rebuild, exclusão do `.pdf2md/` e regressões standalone/Preview.
- Risco residual: rebuild/full scan é síncrono e pode bloquear em vault grande;
  medir em ambiente real antes de introduzir job em background. Nenhuma
  coordenada/layout persistido, dependência nova, commit ou alteração de
  `DocumentSession`.

Checkpoints pretendidos, não criados por solicitação do usuário:

1. `feat(graph): model workspace graph from indexed links`
2. `feat(graph): add neighborhood and graph filters`
3. `feat(graph): expose rebuildable graph from workspace session`
4. `feat(graph): add local workspace graph view`
5. `feat(graph): synchronize workspace graph navigation`
6. `feat(graph): refresh workspace graph from derived index`
7. `test(graph): verify workspace graph acceptance and regressions`

## Rodada de estabilização e workflow mínimo — 2026-09-18

### Correções dos problemas manuais

- `MainWindow._rebuild_workspace_index` agora chama `WorkspaceSession.reconcile`
  uma vez, redescobre e repopula a árvore, atualiza o grafo do snapshot já
  publicado e informa contagem de arquivos. Teste cria/remove Markdown fora da
  aplicação e verifica árvore + grafo.
- `GraphView` calcula órfãos pelo grau no grafo original. Checkbox mostra
  contagem; desmarcar remove nós; marcar exibe nodes isolados em amarelo
  tracejado, com badge/path/tooltip. Nodes conectados mantêm estilo neutro.
- `graph_view.py` agora usa título + caminho em cada node, destaque de seleção,
  labels `Wikilink`/`Markdown` e alias/ocorrências nas arestas. Anchor quebrado
  fica vermelho/tracejado. Issues quebradas/ambíguas têm contador na view.
- `frontend/src/preview.js` adiciona regra inline markdown-it para wikilinks com
  alias e reescreve links Markdown relativos `.md`. Ambos viram URL interna
  `pdf2md-note://`; `PreviewPage` aceita somente navegação principal decorrente
  de clique, emite target/tipo e bloqueia o scheme. `PreviewView` reemite sinal
  para MainWindow; não existe QWebChannel no Preview.
- A camada application resolve links usando `resolve_workspace_references`
  existente sobre metadados/snapshot (ou snapshot em memória do diretório da
  nota standalone); paths de destino precisam ser Markdown e permanecer dentro
  da raiz autorizada. Escapes URI são decodificados na resolução existente.
  MainWindow navega com `open_document_at`, mantendo dirty state. Um documento
  standalone continua resolvendo links locais quando um workspace está aberto.
  Links externos continuam no fluxo HTTP de confirmação.

### Workflow mínimo adicional

- `New Markdown File…` cria arquivo vazio com modo exclusivo na raiz do
  workspace, reconcilia índice, atualiza árvore/grafo e abre nota.
- `Close Note` fecha só a DocumentSession ativa após Save/Discard/Cancel,
  mantém workspace aberto e revoga asset session do Preview.
- `View → Show Preview` oculta/mostra a view sem encerrar a sessão.

### Validação desta rodada

- `ruff check src tests`: passou.
- `mypy`: passou.
- Pytest direcionado (metadata/resolução, navegação Preview, grafo, sessão,
  SQLite, rebuild UI, canvas, roteamento de link, New/Close Note e Preview
  toggle e links standalone durante sessão Workspace): 27 passed.
- `npm run build`: passou. `node test/preview.test.cjs`: 2 passed;
  `node test/editor_commands.test.cjs`: 3 passed. `node --test` falha com
  `spawn EPERM`, contornado executando cada arquivo diretamente.
- Nenhuma nova dependência, banco, cache de posição, mudança no PDF engine,
  DocumentSession ou contrato D-014/D-015.

### Dívida de UX remanescente

- Sem autocomplete de links (explicitamente fora desta rodada).
- Preview ainda não navega para fragmento/heading após abrir o documento.
- Markdown link relativo só é roteado como link de nota quando termina em
  `.md`; imagens continuam sob o handler de assets e externos exigem confirmação.
- Broken/ambiguous links geram feedback textual, sem popover contextual.
- Layout circular pode ficar espaçado e refresh/rebuild segue síncrono em vault
  grande; escala precisa de nova observação em host real.

Checkpoint pretendido, não criado: `fix(graph): stabilize rebuild, orphan
visibility, and internal navigation`.
