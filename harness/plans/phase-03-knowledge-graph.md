# Fase 3 — Knowledge Graph local-first

## Objetivo e limites

Construir uma visualização 2D navegável do grafo derivado do Workspace/Vault
Markdown da Fase 2. O Markdown é a fonte de verdade; snapshot do grafo, índice,
filtros e posições visuais são derivados e reconstruíveis. Esta fase não altera
`DocumentSession`, mantém o modo standalone da Fase 1 e preserva o workflow do
workspace da Fase 2.

Fora de escopo: motor PDF → Markdown, IA, RAG, embeddings, busca semântica,
graph database externo, colaboração/cloud, clustering avançado, layouts 3D,
animações sofisticadas e otimização GPU.

## Decisões arquiteturais resolvidas

- Markdown continua sendo o conteúdo canônico; apagar `.pdf2md/` não perde
  conhecimento (D-003, D-008).
- O grafo é DTO serializável no domínio/aplicação; renderizador é adaptador e
  estado específico do Cytoscape não vaza para domínio/índice (ARCHITECTURE §8).
- Visualização inicial 2D (D-009). Nó documental tem identidade estável baseada
  no caminho relativo normalizado dentro do workspace; links ordinários não
  exigem IDs proprietários (ARCHITECTURE §6).
- Arestas vêm das referências locais já extraídas/resolvidas pela Fase 2:
  wikilinks e links Markdown internos. Backlinks são a inversão derivada dessas
  arestas. Links externos não formam arestas internas.
- Links quebrados não criam nós de documento fictícios; ficam disponíveis como
  diagnóstico/dado derivado para filtros ou painel de detalhes. Documentos sem
  arestas são nós órfãos e continuam no grafo.
- Tags já existem no snapshot do workspace, mas não serão nós na primeira
  entrega: justificativa atual insuficiente para adicionar relações
  documento-tag, métricas e comportamento de navegação. Tags podem ser filtro.
- `WorkspaceSession` fornece/acessa snapshot/index e ciclo de atualização; não
  renderiza. `DocumentSession` permanece alheia ao grafo. UI não lê filesystem
  para montar ou renderizar o grafo e abre nós pelo fluxo
  `MainWindow.open_document_at`, que mantém Save/Discard/Cancel.
- Posições visuais são opcionais, derivadas e descartáveis. Nunca entram em
  Markdown nem são necessárias para reconstruir grafo navegável.
- Sem novo banco ou serviço. Preferir primeiro projetar DTO em memória a partir
  do índice da Fase 2; persistência de layout só se houver justificativa
  observável de UX, isolada e versionada em `.pdf2md/`.

## Decisões abertas e gates

1. Renderer web concreto: avaliar Cytoscape.js como primeira opção 2D, mantendo
   adaptador substituível. Antes de adicionar dependência de produção, verificar
   licença compatível com projeto open-source, funcionamento offline, tamanho,
   manutenção e integração com os bundles locais. Nenhuma dependência deve ser
   adicionada sem esse gate e evidência registrada.
2. Estratégia de layout inicial: usar layout simples incluído no renderer ou
   implementação local determinística; comparar legibilidade em vault pequeno e
   médio. Não adicionar plugin de layout avançado nesta fase.
3. Persistência de coordenadas: padrão é não persistir. Reconsiderar somente se
   teste manual mostrar perda recorrente de contexto; se adotada, guardar como
   cache por identidade do workspace/nó e permitir descarte/rebuild.
4. Escala/job: snapshot atual e rebuild da Fase 2 são síncronos. Primeiro medir
   com fixture representativa; se montagem/layout bloquear UI, mover projeção ou
   preparação para job em background conforme arquitetura, sem alterar
   consistência do índice.

As escolhas 2–4 são detalhes de implementação com padrão documentado e não
bloqueiam iniciar as entregas. O gate de nova dependência é stop condition caso
uma dependência de produção se torne necessária.

## Situação do código-base relevante

- `application/workspace_session.py` define `WorkspaceSnapshot` com notas,
  referências resolvidas (incluindo tipo/estado) e backlinks; contém extração,
  resolução e busca da Fase 2. Não duplicar parsing nem resolução.
- `ports/workspace_index.py` é a porta do índice; `adapters/sqlite_workspace_index.py`
  persiste snapshot reconstruível, notas, referências e backlinks.
- `WorkspaceSession` coordena descoberta, índice, eventos pendentes e rebuild.
- `MainWindow` contém dock/árvore, troca de workspace, busca e
  `open_document_at`; a integração inicial deve seguir esses fluxos e preservar
  a confirmação de alterações não salvas.
- Frontend local existente usa build de assets; graph view será superfície
  separada/adaptador UI, sem acesso Python/filesystem privilegiado pelo conteúdo.
- A Fase 2 documenta limitações ambientais: WebEngine offscreen pode abortar;
  `tmp_path` e symlink têm limitações do host. Cobrir lógica de domínio e
  integração por doubles onde possível; não depender de clique manual como única
  evidência.

## Entregas verticais

### E1 — Contrato do grafo e projeção em memória — CONCLUÍDA

- **Objetivo:** introduzir DTOs tipados/serializáveis para `GraphNode`,
  `GraphEdge`, estado/diagnóstico de referência e `KnowledgeGraph`; identidade
  do nó documental por caminho relativo POSIX normalizado; aresta dirigida e
  tipada (`wikilink` ou `markdown`) com relação inversa de backlinks derivável.
  Projetar grafo do `WorkspaceSnapshot` existente, incluindo nós órfãos e sem
  criar nós para alvo quebrado/externo/ambíguo.
- **Arquivos/camadas prováveis:** `domain/graph.py`,
  `application/build_graph.py` (ou projeção próxima ao modelo se simples),
  testes unitários novos. Ajustar tipos existentes somente se necessário.
- **Dependências:** snapshot/resolução Fase 2; nenhuma dependência runtime.
- **Testes:** nós/arestas determinísticos; dois tipos de link; links quebrados,
  externos e ambíguos; duplicidade de referências; self-link; órfãos; identidade
  em caminhos unicode/espaço; backlinks iguais à inversão; JSON/DTO sem objeto
  de UI/renderer.
- **Aceite:** mesmo snapshot produz grafo igual; alterar snapshot altera apenas
  grafo derivado e nenhuma nota/índice canônico é modificado.
- **Riscos:** identidade/path case em filesystems distintos; múltiplas referências
  entre o mesmo par precisam preservar tipo e contagem sem perder origem.
- **Resultado:** DTOs frozen/serializáveis e projeção implementados em
  `domain/graph.py` e `application/build_graph.py`; arestas contam ocorrências,
  issues retêm alvos quebrados/ambíguos, e backlinks derivam das arestas.
  Teste direcionado passou (6 casos de grafo ao final).
- **Commit pretendido:** `feat(graph): model workspace graph from indexed links`

### E2 — Consulta de vizinhança, filtros e seleção — CONCLUÍDA

- **Objetivo:** casos de uso puros para vizinhança por raio limitado, grau,
  tipo de aresta, estado de link e filtro de texto/tags existentes; seleção é
  identidade de nó, não estado visual persistido. Definir opção de grafo total,
  órfãos e documentos conectados sem alterar snapshot.
- **Arquivos/camadas prováveis:** `application/query_graph.py` ou extensão focada
  de `build_graph.py`; `domain/graph.py`; testes unitários.
- **Dependências:** E1.
- **Testes:** vizinhança direcionada/ambos sentidos, limite/raio, filtros
  combinados, nó selecionado ausente, órfãos incluídos/excluídos e ordenação
  determinística.
- **Aceite:** filtro produz subgrafo internamente consistente e manter/trocar
  seleção é previsível.
- **Riscos:** filtros excessivos podem ocultar contexto; defaults devem mostrar
  documentos e relações compreensíveis.
- **Commit pretendido:** `feat(graph): add neighborhood and graph filters`
- **Resultado:** `application/query_graph.py` implementa consultas puras por
  raio não direcionado, texto, tags, tipos, estado de issues e órfãos. Subgrafo
  é induzido e ordenado; testes cobrem raio, nó ausente e combinações básicas.

### E3 — Integração do grafo com WorkspaceSession — CONCLUÍDA

- **Objetivo:** expor snapshot/projeção do grafo no limite de aplicação a partir
  do índice/rebuild existente, sem parsing duplicado e sem renderer. Atualizações
  de save, mudança observada, remoção, rebuild e fechamento invalidam/atualizam
  grafo de modo coerente; falha mantém último estado consistente/reportável.
- **Arquivos/camadas prováveis:** `application/workspace_session.py`, caso de
  uso/porta existente de índice apenas se necessário, testes de sessão/index.
- **Dependências:** E1; eventos e indexação da Fase 2.
- **Testes:** integração com SQLite existente; alteração de link, criação/
  remoção/rename e rebuild; consistência com reconstrução do snapshot; fechar
  workspace limpa estado associado sem encerrar documento standalone aberto.
- **Aceite:** grafo da sessão sempre corresponde ao snapshot publicado do
  índice, sem leitura de arquivos pela UI.
- **Riscos:** indexação atual faz full scan síncrono; evitar introduzir custo
  adicional duplicado em cada refresh e evitar snapshot parcial.
- **Commit pretendido:** `feat(graph): expose rebuildable graph from workspace session`
- **Resultado:** `WorkspaceSession` recebe o port do índice na abertura e expõe
  rebuild/projeção sem a view acessar adapter ou SQLite. Rebuild publica pelo
  índice existente; método rejeita sessão fechada. Sem schema novo.

### E4 — Superfície de UI, filtros básicos e seleção sincronizada — CONCLUÍDA

- **Objetivo:** adicionar acesso ao Knowledge Graph quando workspace aberto,
  visualização 2D funcional e legível, filtros mínimos (texto/tags/tipo,
  órfãos), seleção de nó e destaque do documento atual. Standalone não instancia
  grafo e permanece funcional.
- **Arquivos/camadas prováveis:** `ui/desktop/main_window.py` ou widget
  `ui/desktop/graph_view.py`; frontend local dedicado em `frontend/` e build
  manifest/configuração apenas após gate de dependência; testes UI com doubles.
- **Dependências:** E2/E3; renderer adapter. Gate de licença/offline/tamanho
  antes de pacote frontend/runtime novo.
- **Testes:** widget/conversão DTO sem GUI quando possível; integração de
  comandos e visibilidade com workspace aberto/fechado; filtros; atualização de
  payload; estado sem renderer; smoke com WebEngine em runner suportado.
- **Aceite:** nós/arestas legíveis em dataset representativo, pan/zoom ou
  navegação equivalente, empty state informativo; nenhuma consulta direta ao
  filesystem pela view; frontend local/offline; preview mantém isolamento D-014/
  D-015.
- **Riscos:** bloqueio UI durante layout em grafo grande; WebEngine/offscreen;
  dependência e bundle podem afetar build/runtime; não expor ponte Python ampla.
- **Commit pretendido:** `feat(graph): add local workspace graph view`
- **Resultado/gate do renderer:** implementado `ui/desktop/graph_view.py` com
  `QGraphicsView` nativo de PySide6, círculo determinístico, arestas dirigidas
  com cor/traço por tipo, pan, zoom, texto/tags, tipos e órfãos; issues aparecem
  em contagem. Não foi necessária nova dependência de produção ou frontend.
  Posições não são persistidas. Teste Qt headless validou render de um grafo
  pequeno; inspeção visual manual de vault médio segue pendente no host real.

### E5 — Navegação integrada e sincronização árvore/editor/grafo — CONCLUÍDA

- **Objetivo:** clique/ativação de nó abre documento via `open_document_at`,
  respeitando Save/Discard/Cancel. Seleção da árvore, documento corrente e
  seleção/destaque do grafo sincronizam quando nota existe no workspace; abrir
  arquivo externo/standalone não inventa nó. Backlink/navegação mantém fluxo
  existente.
- **Arquivos/camadas prováveis:** `ui/desktop/main_window.py`, widget de grafo,
  talvez coordenador de seleção pequeno na UI; regressões em `tests/test_main_window.py`.
- **Dependências:** E4; fluxo de navegação Fase 2.
- **Testes:** clique abre, cancelamento não muda documento/seleção, discard/save
  segue política existente, seleção pela árvore/editor destaca grafo, arquivo
  atual ausente do workspace não causa erro; regressão standalone.
- **Aceite:** todas as rotas usam workflow de abertura existente; `DocumentSession`
  continua sem referência ao grafo/workspace.
- **Riscos:** sinais recursivos de seleção; manter caminho relativo dentro da
  raiz e não contornar proteção de dirty-state.
- **Commit pretendido:** `feat(graph): synchronize workspace graph navigation`
- **Resultado:** dock aparece no contexto de workspace e se oculta ao fechar;
  abrir nó chama `open_document_at`; seleção de árvore/editor/grafo é refletida
  na UI. Cancelamento restaura seleção anterior. `DocumentSession` não mudou.

### E6 — Atualização, layout derivado e integração final — CONCLUÍDA

- **Objetivo:** atualizar visualização após save/editor e eventos/reconciliação
  externos; selecionar e reposicionar layout sem contaminar domínio. Medir
  performance. Coordenadas persistidas somente se justificadas no E4/E6; padrão
  sem persistência. Se persistidas, cache opcional, versionado, descartável,
  protegido contra path/root errado e fora dos documentos Markdown.
- **Arquivos/camadas prováveis:** `application/workspace_session.py`, adapter de
  layout dentro de `.pdf2md/` apenas com justificativa, widget/frontend, testes
  de atualização e reconstrução.
- **Dependências:** E3–E5.
- **Testes:** editar referência atualiza arestas/backlinks; criação/remoção e
  reconciliação; falha de refresh não apaga estado íntegro; layout ausente,
  inválido/versão antiga recupera defaults; descarte de `.pdf2md/` reconstrói
  mesma estrutura navegável; teste de escala com fixture determinística.
- **Aceite:** grafo converge ao índice atualizado, posição nunca altera Markdown,
  cache opcional pode ser removido e operação comum não bloqueia interface de
  forma perceptível no workspace de referência.
- **Riscos:** corrida entre refresh e seleção, inconsistência após eventos
  perdidos, UI responsiva em vault grande; se bloqueio for observado, job
  cancelável/progressivo passa a requisito desta entrega.
- **Commit pretendido:** `feat(graph): refresh workspace graph from derived index`
- **Resultado:** abertura de workspace reconstrói/publica índice antes da
  projeção; save/Save As dentro do workspace e rebuild manual atualizam o grafo.
  Falha mantém último grafo íntegro e reporta erro. Save standalone não reindexa
  workspace. Mudança externa é refletida após ação existente “Rebuild Workspace
  Index”; Fase 2 não fornece watcher concreto. Performance é síncrona/full scan
  como a sessão de índice atual; não foi observado bloqueio em fixture pequena.
  Nenhuma posição/cache é persistida.

### E7 — Verificação manual e regressão de aceite — CONCLUÍDA COM VALIDAÇÃO MANUAL PENDENTE

- **Objetivo:** consolidar documentação operacional, roteiro manual e regressão
  de funcionalidades Workspace e standalone.
- **Arquivos/camadas prováveis:** docs de arquitetura/decisões se houver mudança
  material; plano/contexto; testes de integração existentes.
- **Dependências:** E1–E6.
- **Testes:** suite direcionada de grafo/workspace, Ruff, mypy e build frontend;
  suite relevante de UI em ambiente GUI disponível.
- **Aceite manual:** abrir workspace comum; construir/reconstruir índice; ver
  documentos, links Markdown e wikilinks; distinguir órfãos; aplicar filtros;
  selecionar nó pela árvore/editor/grafo; abrir alvo clicado preservando
  Save/Discard/Cancel; alterar link dentro e fora da aplicação e confirmar
  atualização; apagar `.pdf2md/` e recuperar estrutura; fechar workspace e
  continuar editor standalone; confirmar operação offline e ausência de IA/
  embeddings/PDF converter no caminho do grafo.
- **Riscos:** diferenças entre host Qt/WebEngine e filesystem sincronizado;
  documentar validações ambientais adiadas sem bloquear entrega se houver
  alternativas determinísticas aprovadas pelo AGENTS.md.
- **Commit pretendido:** `test(graph): verify workspace graph acceptance and regressions`
- **Resultado:** teste de integração verifica grafo presente ao abrir workspace,
  falha de refresh preserva snapshot visual publicado, cancelamento da
  navegação e render Qt pequeno. Ruff/mypy e testes direcionados passaram.
  `uv run` e testes frontend/runner Qt completo tiveram limitações ambientais;
  itens exatos constam no registro final abaixo e no contexto.

## Ordem e critérios globais

Sequência: `E1 → E2 → E3 → E4 → E5 → E6 → E7`. E4 é o gate do renderer e da
dependência; E5 pode começar após protótipo do widget E4. Nenhuma UI deve
duplicar parsing ou ler filesystem. SQLite segue índice derivado da Fase 2; não
introduzir graph database. Tags são filtro opcional, não entidade/nó nesta
versão.

Aceite global: DTO determinístico reconstruível das relações do índice; nós
estáveis por caminho relativo; links internos tipados e backlinks derivados;
links quebrados diagnosticáveis e órfãos navegáveis; vizinhança/filtros úteis;
integração bidirecional da seleção; abertura pelo fluxo existente; updates
coerentes com save/eventos/rebuild; standalone e Workspace Fase 2 sem regressão;
frontend local/offline; nenhuma dependência de IA, nuvem, serviço ou grafo
externo; toda persistência opcional é derivada e descartável.

## Registro de execução

Execução concluída em 2026-09-17. E1–E7 implementadas; nenhuma alteração no
motor PDF → Markdown, sem dependência adicionada e sem commit (solicitação
explícita). O mapeamento existente foi suficiente; pdf2md_explorer não foi
necessário. Checkpoints pretendidos por entrega permanecem registrados acima.

Validação final disponível: `ruff check src tests` passou; `mypy` passou;
12 testes focados passaram (grafo, sessão, SQLite, MainWindow/navigation e
GraphView). Build frontend via `npm test` executou esbuild com sucesso, mas os
dois testes Node falharam com `spawn EPERM` ao criar subprocessos; frontend não
foi alterado. `uv run --offline pytest` não iniciou porque o cache global uv
retornou acesso negado. Suíte mais ampla com `tmp_path` não pode enumerar
`C:\Users\Admin\AppData\Local\Temp\pytest-of-Admin` (WinError 5); o host
também tem a limitação WebEngine offscreen já documentada pela Fase 2.
Classificar estes itens como `DEFERRED_ENVIRONMENT_VALIDATION`.

Aceite manual pendente no host Qt real: inspecionar legibilidade e pan/zoom em
vault pequeno/médio; confirmar update após rebuild externo; percorrer filtros e
seleção árvore/editor/grafo incluindo Save/Discard/Cancel; apagar `.pdf2md/` e
reconstruir; validar standalone e Preview/Editor D-014/D-015. Não há dependência
de produção adicional. Risco residual principal: full scan/rebuild síncrono da
Fase 2 pode bloquear em vaults grandes; medir no host real antes de exigir job
em background.

## Rodada de estabilização — 2026-09-18

Escopo autorizado: corrigir quatro gaps reportados no teste manual; em seguida,
adicionar workflow mínimo de criação/fechamento de nota e visibilidade do
Preview. Nenhuma nova fase foi iniciada.

- **Rebuild:** agora faz uma reconciliação SQLite uma vez, redescobre a árvore,
  atualiza grafo do snapshot publicado e informa quantidade de Markdown.
  Corrige tanto conteúdo do índice quanto árvore visual para criação/remoção
  externa observada. Teste de regressão cobre adicionar e remover arquivo.
- **Órfãos:** checkbox informa contagem, remove nós quando desligado e, quando
  ligado, nós isolados recebem preenchimento/contorno amarelo tracejado, label
  `Orphan` e caminho/estado no tooltip.
- **Preview:** markdown-it converte `[[target|alias]]` e links relativos `.md`
  em links internos locais. Qt intercepta apenas clique de link principal e
  encaminha target/kind por sinal; o Preview não recebe bridge Python. A
  resolução reutiliza parser/resolver existente, restringe destinos a Markdown
  dentro da raiz, decodifica escapes URI antes da resolução e usa
  `open_document_at` com política dirty-state preservada. Documento standalone
  também resolve links locais mesmo que um workspace esteja aberto.
- **Grafo:** nós mostram título e caminho; seleção tem destaque ampliado;
  órfãos têm estado próprio; arestas mostram direção, tipo, label/ocorrências;
  anchors quebrados ficam vermelhos/tracejados e links quebrados/ambíguos têm
  contagem visível.
- **Workflow:** `New Markdown File…` cria nota vazia exclusiva na raiz do
  workspace, atualiza índice/árvore/grafo e abre no editor; `Close Note` fecha
  apenas documento com confirmação de dirty-state; `View → Show Preview`
  alterna Preview.
- **Arquivos principais:** aplicação `workspace_session.py`; UI
  `main_window.py`, `preview_view.py`, `graph_view.py`; frontend
  `preview.js`/`preview.html`; testes de metadata, navegação Preview e UI.
- **Validação:** 27 testes Python direcionados passaram; Ruff e mypy passaram.
  Build frontend passou; invocação direta Node passou 2 testes de Preview e 3
  de Editor. `node --test` continuou bloqueado por `spawn EPERM`; invocar testes
  diretamente foi alternativa válida.
- **Checkpoint pretendido (não criado):**
  `fix(graph): stabilize rebuild, orphan visibility, and internal navigation`.
- **Dívida UX:** wikilinks não têm autocomplete; links relativos sem `.md` não
  são tratados como documentos; clique em fragmento abre o documento mas não
  faz scroll para heading; diálogo de link quebrado é textual; layout do grafo
  é circular determinístico e pode ficar espaçado em vault maior; operações de
  rebuild continuam síncronas.
