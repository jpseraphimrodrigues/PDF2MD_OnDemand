# Etapa 5 — UI/UX Progress

## Objetivo

Renovar a interface desktop em tema claro neutro, organizar navegação de workspace
e adicionar abas de documentos que preservem o estado completo do CodeMirror.
Persistir apenas a disposição da janela em preferências locais. O conteúdo Markdown
continua sendo a única fonte de verdade.

## Estado atual

- Implementação em andamento na branch `feature/ui-ux-progress`, criada de
  `main` em `aa9e579`.
- Navegação lateral com árvore/busca/resultados, barra de abas e painel central
  editor/preview já implementados; grafo segue em dock nativo recolhível.
- `DocumentTabs` mantém sessões distintas, deduplicação por caminho resolvido,
  ativação, reordenação, salvamento e resolução explícita ao fechar.
- CodeMirror agora guarda `EditorState` e scroll por chave, incluindo histórico,
  seleção e cursor; a troca suprime notificações de edição.
- QSS claro global, CSS do editor/preview e preferências QSettings locais já foram
  integrados. Tema permanece compatível com os rótulos existentes em inglês.
- Suíte completa Python: 77 passaram, 2 foram ignorados. Frontend: 11 passaram.
  Ruff e mypy focados também passaram após os ajustes.
- A inspeção manual em Windows ainda não foi executada.

## Decisões e limites

- Rótulos da interface permanecem em inglês; tema inicial claro, neutro e focado.
- Shell nativo recebe QSS. CodeMirror e Preview recebem CSS local coordenado pela
  mesma paleta. Não adicionar framework visual geral.
- Cada aba mantém sua `DocumentSession`, histórico, cursor, seleção e rolagem.
  Abrir caminho já aberto ativa a aba existente. Fechar aba alterada oferece
  Save/Discard/Cancel. Fechar o app resolve todas as abas alteradas antes da saída.
- Abrir outro workspace fecha abas pertencentes ao workspace anterior, depois de
  resolver todas as alterações; abas externas permanecem abertas. Cancelar mantém
  o workspace e todas as abas intactos.
- Árvore, busca, Preview e grafo abrem/ativam abas. O grafo destaca apenas a nota
  ativa pertencente ao workspace aberto.
- Persistência via `QSettings`: geometria, estado dos docks, visibilidade e splitter.
  Nenhuma configuração de interface será escrita dentro de workspace ou Markdown.
- Comparar Qt `QGraphicsView` e protótipo Plotly com o mesmo DTO e grafos de 100,
  500 e 1.000 nós. Qt continua padrão; Plotly só entra se houver ganho claro de
  legibilidade/interação sem rede, sem ponte Python ampla, e com carregamento e
  empacotamento aceitáveis. Prototipagem não adiciona dependência runtime.
- Não alterar contratos de domínio/aplicação nem fazer autosave.

## Entregas e validação

### 1. Estado de documento por aba

- Adicionar coordenador de abas à camada UI e API JS interna
  `editorApi.switchDocument(documentKey, content)`.
- Manter um `EditorState` CodeMirror por chave, com posição de rolagem separada;
  inibir notificações de conteúdo durante troca/restauração.
- Incluir aba em branco pathless (Save encaminha a Save As), ativação de existente,
  indicador dirty e fechamento unitário seguro.
- Testar isolamento de texto/histórico, restauração cursor/seleção/scroll, caminhos
  duplicados, Save/Discard/Cancel e falha de Save.

### 2. Navegação e ciclo de workspace

- Reorganizar a janela com barra de abas acima do editor/preview, sidebar Workspace
  contendo árvore e busca/resultados, docks recolhíveis e ações primárias acessíveis.
- Centralizar abertura das notas de árvore, busca, links e grafo no fluxo de abas.
- Implementar fechamento/troca de workspace em duas fases: resolver todas as abas
  internas primeiro; Cancelar ou erro mantém contexto/abas sem fechamento parcial.
- Testar workspace com abas internas e externas, cancelamento, notas duplicadas,
  sincronização da nota ativa com grafo e Preview, e modo standalone.

### 3. Tema e preferências locais

- Criar QSS claro para menus, toolbar, abas, docks, inputs, botões, splitters,
  árvore e status. Criar CSS compatível para editor, Preview, callouts e grafo.
- Usar contraste legível para texto, foco, seleção, hover, dirty e estados de grafo.
- Restaurar/salvar geometria, dock state e splitter usando QSettings isolado por
  aplicação; testar round-trip sem depender do registro/configuração real do usuário.
- Não incluir seletor de tema escuro nesta etapa.

### 4. Comparação de renderers do grafo

- Gerar fixture determinística compartilhada de 100/500/1.000 nós; prototipar
  Plotly em ambiente de avaliação separado e manter os assets locais/offline.
- Registrar legibilidade, pan/zoom, seleção/abertura, tempo frio de carga, tempo
  de renderização, uso de memória observado e tamanho distribuído.
- Integrar Plotly somente se superar claramente QGraphicsView nesses critérios;
  caso contrário, manter e tematizar o renderer nativo. Registrar resultado e
  justificativa neste plano/contexto.
- Qualquer integração web mantém dados escapados, navegação restrita e nenhuma
  exposição genérica de objetos Python.

## Compatibilidade e segurança

- `DocumentSession`, gravação otimista e detecção de modificação externa continuam
  por documento. Salvar uma aba atua somente sobre sua sessão ativa.
- Caminhos são deduplicados após `resolve()`; associação ao workspace também usa
  caminhos resolvidos.
- Cada mudança de aba atualiza raiz de assets do Preview, conteúdo renderizado,
  título da janela e seleção do grafo sem alterar source.
- Operações em arquivos continuam explícitas; layout e tema são preferências locais.

## Aceite final

- Testes Python e Node relevantes, Ruff e mypy passam.
- Smoke Qt/WebEngine confirma troca entre pelo menos duas abas sem contaminação de
  conteúdo/histórico e Preview correspondente à aba ativa.
- Inspeção manual Windows em standalone e workspace confirma tema, docks, busca,
  abas, fechamento de dirty tabs e restauração de layout.
- Plano/contexto registram renderer escolhido, evidência, comandos e validações
  eventualmente adiadas por limitações ambientais.

## Checkpoints previstos

- `feat(ui): add independent document tabs`
- `feat(ui): reorganize workspace navigation`
- `feat(ui): add light design system and saved layout`
- `feat(graph): polish native renderer` (ou alternativa somente se os critérios
  Plotly forem satisfeitos)

## Progresso e evidência (2026-09-18)

- Implementados: estado independente por aba, tabs para arquivos/Untitled, busca e
  árvore no dock Workspace, ativação por links/grafo, fechamento seguro de dirty
  tabs, ciclo de workspace preservando documentos externos, QSettings, QSS/CSS e
  inclusão dos novos assets no pacote Python/sdist.
- `uv run --no-sync pytest -q`: 77 passed, 2 skipped; inclui smoke Qt/WebEngine que
  edita duas notas, alterna, valida undo independente, seleção/scroll restaurados e
  nenhuma edição falsa durante a troca.
- O bridge inclui a chave original em atualizações editor→Python. A janela aplica
  uma atualização tardia à sessão de origem se ela ainda estiver aberta; o JS não
  injeta conteúdo dessa chave na aba ativa diferente.
- `npm test` em `frontend`: 11 passed; build local incluiu os novos estilos.
- Ruff e mypy focados nos módulos e testes tocados: passaram.
- Avaliação QGraphicsView com um grafo determinístico de ciclo (N nós e N arestas),
  medindo `set_graph` mais `processEvents`, offscreen Windows: 100 nós/400 itens
  de cena = 21,25 ms; 500/2.000 = 92,29 ms; 1.000/4.000 = 184,86 ms.
- Plotly não está instalado (`importlib.util.find_spec('plotly')` retornou `None`).
  Não foi adicionado como dependência. Por isso a avaliação com protótipo Plotly,
  HTML autocontido, tamanho de bundle, carga fria e comparação visual equivalente
  está marcada `DEFERRED_ENVIRONMENT_VALIDATION`; Qt permanece renderer padrão.
- `npm test` precisa ser executado com `frontend` como diretório de trabalho.
- Inspeção visual manual Windows (standalone/workspace) e comparação de legibilidade
  Plotly/Qt continuam pendentes, pois não foi possível executar uma sessão visual e
  Plotly não está instalado no ambiente.

Checkpoint proposto após fechar a etapa: `feat(ui): complete UI/UX progress`.
