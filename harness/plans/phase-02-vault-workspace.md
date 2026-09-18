# Fase 2 — Workspace/Vault local-first

## 1. Objetivo e limites

Transformar a experiência standalone da Fase 1 em um workspace selecionável
representado por uma pasta comum de documentos Markdown. O workspace permite
descobrir e navegar arquivos `.md`, consultar metadados e relações, pesquisar
texto e manter um índice derivado atualizado. Os arquivos Markdown continuam
sendo a única fonte de verdade.

Não alterar o motor PDF → Markdown. Fora de escopo: IA, embeddings, RAG, grafo
visual sofisticado, alteração em massa de documentos, conversão/importação PDF,
identidade proprietária obrigatória, servidor ou serviço remoto.

## 2. Restrições arquiteturais e decisões herdadas

- Preservar D-014: CodeMirror 6 no WebEngine dedicado; Preview separado e sem
  QObject privilegiado; QWebChannel só no Editor; busca do editor permanece
  distinta da futura busca no workspace.
- Preservar D-015: Preview usa scheme/handler controlado, acesso local limitado
  à raiz autorizada. Ao operar em Vault, links/recursos continuam confinados ao
  workspace ou à regra documentada, sem conceder acesso genérico ao filesystem.
- `Document`/`DocumentSession` continuam representando edição de um arquivo.
  Não introduzir Vault, backlinks ou estado de índice nessas classes.
- `WorkspaceSession` pertence à aplicação e coordena raiz, descoberta,
  indexação e abertura/navegação de documentos por casos de uso/portas.
- UI chama casos de uso; domínio/aplicação não importam PySide6.
- SQLite é uma implementação substituível de índice derivado, nunca conteúdo
  autoritativo. Apagar `.pdf2md/` não pode apagar/alterar Markdown.
- Sem banco, abrir `.md` standalone mantém exatamente o caminho da Fase 1.
- Caminhos de links e assets são relativos/portáveis quando possível.
- Nenhuma etapa reescreve arquivos Markdown durante indexação. Mudanças
  externas são relidas/indexadas; conflitos de edição continuam seguindo o
  mecanismo de snapshots da Fase 1.

## 3. Decisões já resolvidas

1. Workspace é uma pasta comum selecionada pelo usuário, não um container.
2. Markdown é fonte de verdade; índices, caches e banco são descartáveis e
   reconstruíveis.
3. Sessão de workspace é separada da sessão de documento; documentos abertos
   podem continuar usando o mesmo `DocumentSession` e `DocumentStore`.
4. Índice deve ser acessado por porta e implementado por adapter; SQLite é a
   opção preferida já prevista em `AGENTS.md` e `docs/ARCHITECTURE.md`, sujeito
   à confirmação de adequação no desenho/implementação sem novo framework.
5. Parsing/extração de metadados é leitura-only e deve preservar source
   desconhecido. A UI não analisa Markdown.
6. Descoberta e indexação abrangem arquivos Markdown da raiz e subpastas, com
   política de exclusão explícita para estado/cache interno e diretórios
   ignorados; não seguir links simbólicos para fora da raiz.

## 4. Decisões abertas para implementação (não bloqueantes agora)

- Gramática e precedência do título: frontmatter `title`, primeiro heading
  nível 1, basename, nessa ordem; validar suporte atual a frontmatter e decidir
  sem normalizar source. Slugs e heading anchors devem ser apenas derivados.
- Escopo de descoberta de `.md` (case sensitivity por plataforma) e diretórios
  ignorados por padrão além de `.pdf2md`; usar comportamento portátil e
  documentado, sem esconder pastas de usuário arbitrariamente.
- Resolução de wikilinks ambíguos: usar caminho relativo explícito quando
  fornecido; para basename sem extensão, correspondência única resolve,
  múltiplas correspondências ficam ambíguas (não escolher silenciosamente).
- Sintaxe exata de tags e wikilinks/aliases/headings; começar com subconjunto
  documentado que não conflite com Markdown comum e preservar texto integral.
- Política sobre links Markdown com fragmento/query e URL externa: indexar
  relações locais resolvíveis; ignorar schemes externos para grafo/backlink.
- Local e formato do índice SQLite. Preferência: `.pdf2md/index.sqlite3` como
  dado derivado recriável, mas evitar configuração ou dados do usuário nessa
  pasta sem decisão explícita. Confirmar licenças/runtime (sqlite3 padrão
  Python não adiciona dependência).
- Watcher: observar raiz/subárvores com debounce e reconciliação periódica/por
  demanda; tratar limitações de filesystem de rede/sincronizado e eventos
  duplicados/perdidos sem depender do watcher para consistência final.
- Busca: definir semântica inicial de texto (case-insensitive, substring ou
  FTS5) e ordenação estável; validar disponibilidade de FTS5 do SQLite antes
  de adotá-lo, mantendo fallback/adapter apropriado.

Essas decisões são escolhas de implementação compatíveis com a arquitetura
registrada; não exigem alterar D-014/D-015 nem bloqueiam o início. Se evidência
exigir dependência runtime nova ou mudança material na arquitetura, parar e
atualizar decisão antes de adotá-la.

## 5. Arquitetura alvo da fase

```text
UI (MainWindow + árvore + resultados)
  → casos de uso de workspace / navegação / busca
    → WorkspaceSession (orquestração) + portas
      → filesystem Markdown / parser read-only / SQLite derivado / watcher

WorkspaceSession ──abre documento──> open_document → DocumentSession
DocumentSession não conhece WorkspaceSession nem índice/grafo.
```

Estrutura sugerida, a adaptar aos módulos reais sem criar abstrações vazias:

```text
domain/       metadados e relações derivados (se necessário)
application/  WorkspaceSession e casos de uso de abrir/indexar/buscar
ports/        descoberta, índice e watcher, cada qual com necessidade real
adapters/     filesystem Markdown, SQLite, watcher
ui/desktop/   árvore e integração de navegação na janela
```

Definir DTOs pequenos e tipados para árvore, resultados, links e backlinks.
Não persistir cópias de conteúdo como fonte; índice pode guardar conteúdo
derivado para busca se for reconstruível e coerente com versão/hash do arquivo.

## 6. Entregas sequenciais

Cada entrega é vertical, testável e pode receber commit próprio após diff e
validações relevantes. Não iniciar a próxima se a atual não estiver validada.

### E1 — Contratos de workspace e sessão vazia

- Definir modelo/identidade de raiz e `WorkspaceSession` independente de
  `DocumentSession`; caso de uso de abrir/fechar workspace sem banco.
- Injetar dependências por interfaces/ports necessárias, sem mover política
  para `MainWindow`.
- Testes unitários de criação, raiz, estado fechado/aberto e isolamento de
  sessão de documento.
- Aceite: workspace pode ser aberto em memória e uma sessão standalone segue
  funcionando sem construir WorkspaceSession ou SQLite.

### E2 — Descoberta segura e árvore de Markdown

- Adapter lista `.md` recursivamente em ordem determinística, ignora `.pdf2md`
  e diretórios configurados, não segue symlinks para fora da raiz e trata
  erros/parcialidade de filesystem.
- DTO de árvore agrupa diretórios e arquivos sem carregar widgets no core.
- UI apresenta árvore e ação Abrir pasta; seleção abre/navega por caso de uso.
- Integração com dirty-state: salvar/descartar/cancelar antes de trocar arquivo;
  erro de abrir não substitui sessão atual.
- Testes de filesystem temporário, ordenação, filtros, paths unicode e falhas;
  teste UI/composição com doubles.
- Aceite: usuário abre diretório comum, vê Markdown e navega sem banco obrigatório.

### E3 — Extrator Markdown read-only e índice em memória

- Parser determinístico extrai título, headings/anchors, tags, links Markdown e
  wikilinks segundo gramática documentada; mantém posições/targets suficientes
  para resolução; não reescreve source.
- Construir snapshot completo em memória e referências locais com caminhos
  relativos; título usa precedência decidida em E3.
- Testes unitários + fixtures/goldens para Unicode, frontmatter, headings
  repetidos, tags inline/frontmatter conforme escopo, links escapados, aliases,
  fragmentos, sintaxe inválida/desconhecida e round-trip source intacto.
- Aceite: resultados são reproduzíveis e o parser nunca modifica arquivo.

### E4 — Resolução, links quebrados, ambiguidades e backlinks

- Resolver alvos locais de links Markdown e `[[wikilinks]]` a paths de notas;
  anchors resolvem a headings. Representar estado resolvido/quebrado/ambíguo.
- Backlinks são relação inversa derivada, sem campo mutável em `Document`.
- Testar links relativos, extensão opcional, aliases/fragmentos acordados,
  caminhos com espaços/Unicode, target ausente, headings ausentes, duplicatas e
  múltiplos candidatos. Externos não criam backlinks.
- Aceite: navegação/resumo de links e backlinks corretos em snapshot de vault.

### E5 — Índice SQLite derivado e rebuild

- Definir esquema/versionamento dentro de `.pdf2md`; gravar caminhos relativos,
  fingerprint/hash e metadados/relações derivados. Usar transação para publicar
  snapshot coerente; nenhuma alteração a notas.
- Porta de índice separa aplicação do SQLite. Reconstruir índice vazio, antigo,
  corrompido ou de versão desconhecida lendo Markdown; erro não impede modo
  standalone e deve ser reportável no workspace.
- Testes de integração com tmp_path: rebuild, consistência, fechamento/reabertura,
  exclusão de cache e equivalência com indexação em memória.
- Aceite: deletar `.pdf2md/` e reconstruir produz os mesmos resultados sem perda
  de conteúdo.

### E6 — Busca textual no workspace

- Caso de uso consulta conteúdo/metadados indexados, oferece correspondências
  com caminho/título e contexto suficiente para abrir documento.
- Busca local e offline; sem misturar com search do CodeMirror. Definir semântica
  mínima de caixa, frase, ordenação e limites. Se FTS5 não for garantido,
  fallback explícito sem dependência externa.
- Testes de precisão, Unicode/acentos conforme suporte, snippets, ordenação,
  consulta vazia e caminho de abrir resultado.
- Aceite: buscar texto no vault e abrir resultado preserva workflow dirty-state.

### E7 — Atualização incremental e consistência

- Reindexar arquivo alterado/criado/removido e atualizar relações afetadas;
  eventos concorrentes são coalescidos; falha de leitura não publica registro
  parcial nem apaga silenciosamente último estado consistente.
- Mudança da própria aplicação após save atualiza/revalida index sem criar
  conflito espúrio; arquivo aberto alterado externamente mantém proteção de
  `DocumentSession`.
- Testes de alterações individuais e em lote, remoção, rename observado como
  remove+create, erro transitório e consistência com rebuild integral.
- Aceite: resultado incremental equivale ao rebuild integral após sequência de
  eventos.

### E8 — Filesystem watcher e reconciliação

- Adapter de watcher envia eventos para a aplicação, não executa parsing/
  SQLite/UI no callback. Debounce/coalescing e shutdown seguro.
- Inicialização faz scan; watcher acelera atualização; reconciliação manual e
  após overflow/perda de eventos recupera estado. Operação deve tolerar
  filesystem com watcher limitado.
- Testes determinísticos com watcher fake; poucos testes de integração para
  watcher real quando plataforma permitir, sem timing frágil como única prova.
- Aceite: criar/editar/remover arquivo externamente atualiza árvore, índice,
  links/backlinks e busca; rebuild continua mecanismo de recuperação.

### E9 — Integração final, segurança e regressão

- MainWindow alterna contexto standalone/workspace e mantém `WorkspaceSession`
  separada; abrir arquivo do workspace reutiliza lifecycle Fase 1.
- Navegação interna para links resolvidos usa caso de uso de abrir documento;
  Preview não ganha permissões Python nem `file://` amplo. Assets em workspace
  continuam sob raiz da nota/workspace autorizada respeitando D-015.
- Testes de regressão standalone real, conflito externo, dirty-state, segurança
  Preview/asset, navegação na árvore e sem banco.
- Smoke offline e documentação de operação/rebuild/limitações do watcher.
- Aceite: todos os critérios abaixo passam sem funcionalidades PDF/IA/grafo
  visual avançado.

## 7. Dependências entre entregas

`E1 → E2 → E9` para lifecycle/UI; `E1 → E3 → E4`; `E3/E4 → E5` (persistir
metadados e relações); `E5 → E6`; `E5 + E4 → E7`; `E2 + E7 → E8`; `E2 + E4 +
E6 + E8 → E9`. E3 pode começar após E1 e não depende de UI. E5 pode ser
integrado antes de E4 estar finalizado apenas se schema aceitar atualização
versionada, mas sequência preferida evita duplicar schema.

## 8. Critérios globais de aceite

- Abrir pasta comum como workspace local-first, listar Markdown e navegar entre
  documentos; abertura respeita confirmação dirty-state.
- `WorkspaceSession` orquestra arquivos/índice e permanece separada de
  `DocumentSession` e do domínio documental.
- Títulos, headings, tags, links Markdown e wikilinks são derivados sem tocar
  source; resolução informa links quebrados/ambíguos e backlinks corretos.
- Busca textual funciona offline e seus resultados abrem documentos.
- Mudanças internas/externas atualizam incrementalmente; rebuild integral
  reproduz o mesmo índice. Watcher não é requisito de consistência.
- Excluir `.pdf2md/` não afeta Markdown e workspace pode reconstruir dados.
- Standalone `.md` continua sem banco/workspace e sem regressão no round-trip,
  BOM/CRLF, save, Save As e conflito externo.
- D-014/D-015 permanecem atendidas; nenhum acesso privilegiado é dado ao
  Preview; assets permanecem relativos/portáveis.
- Sem PDF → Markdown, IA, embeddings, RAG ou grafo visual sofisticado.

## 9. Plano de testes

- Unitários: parser/extrator, resolução/ambiguidade, DTOs, busca e casos de uso.
- Filesystem: árvore, exclusões, symlinks, falhas de permissão, rename/criação/
  remoção e unicode em `tmp_path`.
- SQLite adapter: rebuild, migração/version mismatch, transação, corrupção e
  equivalência em memória.
- Incremental: comparar toda mutação com rebuild integral; fake watcher para
  debounce, overflow, shutdown e reconciliação.
- UI: árvore/seleção, troca de workspace/documento e bloqueio por dirty-state,
  usando doubles onde possível.
- Regressão Fase 1: suíte existente completa, especialmente document session,
  MainWindow, integração WebEngine, preview policy/assets e golden.
- Validação final: `uv run pytest`, `uv run ruff check src tests`, `uv run mypy`,
  frontend `npm test` e build; executar smoke offline `uv run pdf2md`.

## 10. Riscos de regressão da Fase 1

1. Troca de arquivo via árvore pode contornar Save/Discard/Cancel.
2. Workspace e standalone podem ser acidentalmente acoplados por construção
   global de banco ou caminho obrigatório.
3. Watcher pode interpretar Save próprio como edição externa e deixar janela
   dirty/conflict incorreta.
4. Parser pode normalizar Markdown desconhecido ou gerar alterações apenas ao
   indexar; todos os fluxos devem ser read-only.
5. Mudança de raiz de assets pode abrir traversal/symlink ou quebrar D-015.
6. Caminhos relativos podem falhar com case sensitivity, unicode, espaços,
   drives/removíveis e filesystem de rede.
7. Índice desatualizado/corrompido pode ser confundido com fonte de verdade.
8. Watcher de sistema operacional pode perder eventos; reconciliação/rebuild é
   obrigatória e UI não pode bloquear durante indexação.
9. Integração pode quebrar debounce, Undo/Redo, preview ou busca do Editor.

## 11. Estado

E1–E9 concluídas no working tree para o escopo inicial descrito; detalhes por
entrega estão no contexto. Validações `DEFERRED_ENVIRONMENT_VALIDATION` estão
registradas abaixo e requerem execução fora deste host sandboxado:

- `tests/test_asset_paths.py` e suíte total: Qt WebEngine encerrou o processo
  com exceção fatal ao carregar conteúdo no host offscreen.
- testes com `tmp_path` (incluindo `test_main_window.py` e regressões Fase 1):
  pytest recebe `PermissionError` enumerando/limpando diretório basetemp sob a
  raiz do workspace; testes de workspace com diretórios próprios passam.
- criação de symlink: WinError 1314 por privilégio Windows indisponível; o
  teste fica skipped. A inspeção determinística confirma que symlinks são
  filtrados antes da recursão, faltando validar criação real neste host.
- watcher real: somente o contrato foi validado; teste em filesystem/runner com
  watcher operacional fica deferred, pois não foi adotada dependência runtime.

Checkpoints pretendidos (não executados conforme solicitação do usuário):
`feat(workspace): add safe markdown discovery and tree navigation`;
`feat(workspace): extract markdown metadata and resolve backlinks`;
`feat(workspace): add rebuildable sqlite index and search`;
`feat(workspace): reconcile workspace changes and integrate navigation`.

Nenhuma etapa altera o motor PDF → Markdown.
