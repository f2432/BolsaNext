# Estado atual do projeto

Última atualização canónica: 2026-10-05.

Este documento regista o estado efetivo do projeto BolsaNext. O roadmap define o destino; este ficheiro define o ponto em que o projeto se encontra agora.

## Estado global

Última versão funcional concluída e integrada: **V0.2 — Market Data**.

Ciclo de trabalho atual: **estabilização final e saneamento pós-V0.2**.

Estado da V0.1: **CONCLUÍDA E VALIDADA** localmente em Windows e no GitHub Actions.

Estado da V0.2: **conclusão funcional mantida**, mas uma revisão posterior identificou melhorias, correções e decisões técnicas que serão fechadas antes de iniciar a V0.3.

Estado da V0.3: **POR INICIAR**. Não existe autorização para implementar Portfolio durante o ciclo atual.

Próximo objetivo depois deste ciclo: iniciar a V0.3 — Portfolio, apenas após fecho e validação explícita da estabilização.

Plano sequencial canónico do ciclo atual: `docs/stabilization-v0.2.md`.

Nota histórica: em 2026-10-05 a V0.2 foi considerada concluída e integrada na `main`. Essa entrega funcional não é apagada; o ciclo atual acrescenta hardening e corrige incongruências identificadas numa revisão posterior.

## Ciclo atual — estabilização final da V0.2

Objetivo: fechar todas as melhorias, correções e decisões técnicas identificadas após a integração funcional da V0.2, **sem iniciar a V0.3**.

Ordem canónica resumida:

1. S0 — baseline;
2. D1 — A6 completa: semântica de `market` e proveniência dos metadados;
3. D2 — A7.1: backup antes de migrações/movimentos;
4. D3 — parte atual de A5: significado de `base_currency` na configuração;
5. B1 — ports e direção das dependências;
6. B2 — erros externos;
7. B3 — subunidades monetárias;
8. B4 — integridade SQLite;
9. B5 — localização dos dados;
10. B6 — migrações;
11. B7 — fonte única de versão, sem tag ainda;
12. B8 — hardening Watchlist/UI;
13. B9 — CI, dependências e qualidade;
14. B10 — coerência canónica;
15. itens avulsos I1–I5;
16. B11 — fecho, integração autorizada e tag `v0.2.0`.

A1–A4, restante A5, restante A7 e A8 permanecem preservados para a futura especificação da V0.3. Nada é descartado.

Ver detalhes, correções ao plano original e rastreabilidade completa em `docs/stabilization-v0.2.md`.

### Baseline S0 do ciclo atual

Medições já confirmadas:

- 39 testes locais passaram;
- cobertura global: 55%;
- execução local observada em Windows com Python 3.14.5;
- CI remoto da `dev` passou em Python 3.12;
- foi detetado um `ResourceWarning` por ligação SQLite não fechada num teste de integração da Watchlist; fica registado para correção no saneamento de persistência/B4.

Falta apenas confirmar visualmente o `git status --short` local e o SHA local para fechar formalmente S0.

## V0.1 — Fundação concluída

### Repositório e documentação

- repositório público `f2432/BolsaNext`;
- `README.md` com objetivo, princípios e estrutura geral;
- `docs/architecture.md` com separação UI / Application / Domain / Infrastructure;
- `docs/roadmap.md` com evolução V0.1 até V1.0;
- `docs/legacy.md` com inventário do projeto anterior;
- `docs/ai-roadmap.md` com continuidade da componente de IA e Planeamento IA;
- `docs/development.md` com instalação, execução e testes;
- `AGENTS.md` com regras para alterações por agentes;
- `.gitignore` preparado para excluir dados pessoais, bases locais, caches, logs e modelos treinados.

### Empacotamento e ambiente

- projeto configurado em `pyproject.toml`;
- Python mínimo 3.12;
- instalação editável através de `pip install -e .`;
- dependências de desenvolvimento através de `pip install -e ".[dev]"`;
- comando de consola `bolsanext`;
- suporte alternativo a `python -m bolsa.main`;
- script Windows `run.ps1` para atualizar, instalar dependências, testar e arrancar a aplicação com um único comando.

### Estrutura e infraestrutura

- pacote `src/bolsa`;
- camadas `app`, `domain`, `infrastructure` e `ui`;
- área reservada `domain/ai/planning`;
- configuração central através de `AppConfig`;
- logging centralizado;
- SQLite;
- SQLAlchemy;
- criação de engine;
- factory de sessões;
- inicialização de schema;
- base local em `data/bolsanext.sqlite3`.

### Interface

- PySide6;
- `MainWindow`;
- áreas Resumo, Watchlist, Carteira, Análise, Backtesting e IA;
- barra de estado;
- aplicação executável em Windows.

### Testes e CI

- `pytest`;
- `pytest-cov`;
- testes unitários e de integração;
- GitHub Actions em pushes e pull requests para `main`;
- V0.1 validada localmente com aplicação a abrir corretamente;
- GitHub Actions confirmado com sucesso.

## V0.2 — Market Data

### Instrumentos

- entidade de domínio `Instrument`;
- enum `AssetType` com stock, ETF, index e other;
- normalização de ticker, mercado e moeda;
- validação básica de ticker e código de moeda;
- metadados persistentes: nome, mercado, moeda e tipo de ativo.

### Dados de mercado

- contrato `MarketDataProvider`;
- adapter `YFinanceMarketDataProvider`;
- `MarketService`;
- histórico OHLCV;
- preço atual;
- fallback para preço intradiário quando necessário;
- enriquecimento de instrumentos com metadados Yahoo;
- colunas canónicas:
  - `Open`;
  - `High`;
  - `Low`;
  - `Close`;
  - `Adj Close`;
  - `Volume`;
- `auto_adjust=False`;
- preservação separada de `Close` e `Adj Close`;
- ordenação cronológica;
- remoção de datas duplicadas;
- normalização de `DatetimeIndex`;
- conversão de timestamps com timezone para UTC timezone-naive.

### Universos

- domínio `Universe`;
- contrato `UniverseProvider`;
- `UniverseService`;
- `WikipediaUniverseProvider`;
- S&P 500;
- NASDAQ 100;
- Euronext 100;
- correção de HTTP 403 através de User-Agent explícito;
- correção da fonte dedicada de constituintes do NASDAQ 100;
- normalização de tickers norte-americanos para formato Yahoo;
- preservação de sufixos Yahoo nos mercados europeus;
- mapeamento inicial de moeda por praça;
- integração na interface;
- adição de ativos de um universo diretamente à Watchlist;
- carregamento em background para não bloquear a UI;
- validação local em Windows de S&P 500, NASDAQ 100 e Euronext 100.

### Cache de universos

- `CachedUniverseProvider`;
- cache JSON em `data/cache/universes`;
- validade inicial de 24 horas;
- metadados de origem e instante de recolha;
- fallback automático para a fonte quando o cache está ausente, expirado ou inválido;
- cache excluída do Git;
- utilização real validada localmente.

### Watchlist

- domínio `Watchlist`, `WatchlistItem` e `WatchlistState`;
- estados:
  - Ideia;
  - Em análise;
  - Candidato;
  - Rejeitado;
  - Em revisão;
- adição manual por ticker;
- enriquecimento automático de metadados para tickers adicionados manualmente;
- botão `Atualizar dados` para completar metadados antigos;
- adição através dos universos;
- prevenção de duplicados;
- remoção com confirmação;
- atualização de preços;
- atualização de preços em background;
- colunas de ticker, nome, mercado, moeda, estado, preço atual e ações;
- sincronização imediata entre Universos e Watchlist;
- persistência SQLite;
- restauro automático no arranque;
- persistência do estado selecionado;
- correção da normalização dos estados vindos da UI;
- preço atual deliberadamente não persistido, por ser dado transitório de mercado;
- composição e estado validados localmente após fechar e reabrir a aplicação.

### Persistência atualmente implementada

Tabelas:

- `instruments`;
- `watchlists`;
- `watchlist_items`.

Acesso através de `SqlAlchemyWatchlistRepository`.

A origem da verdade para a Watchlist é a base local SQLite.

### Preferências da interface

- larguras e estado dos cabeçalhos das tabelas da Watchlist e dos Universos são persistidos por utilizador através de `QSettings`;
- alterações feitas manualmente às larguras das colunas são restauradas no arranque seguinte;
- a implementação é reutilizável para outras tabelas que venham a ser adicionadas.

### Validações locais concluídas

- adição manual de AAPL, MSFT e NVDA;
- atualização de preços;
- rejeição correta de tickers duplicados;
- S&P 500 carregado;
- NASDAQ 100 carregado;
- Euronext 100 carregado;
- AMD adicionada a partir do NASDAQ 100;
- sincronização visual Universos → Watchlist;
- persistência de composição da Watchlist;
- persistência do estado;
- carregamento assíncrono dos universos;
- atualização assíncrona de preços;
- enriquecimento automático de metadados;
- cache de universos;
- persistência das larguras das colunas validada localmente na Watchlist e nos Universos.

### Fecho técnico da V0.2

- validação sintática de tickers, preservando formatos comuns do Yahoo como `^GSPC`, `BRK-B`, `EURUSD=X` e `ASML.AS`;
- distinção explícita entre ticker inexistente e indisponibilidade do fornecedor;
- mensagens de erro de metadados mais claras para a UI;
- ticker inexistente não é adicionado à Watchlist;
- atualização de metadados continua para os restantes ativos mesmo que um deles falhe;
- atualização de preços identifica na barra de estado os tickers cujo preço ficou indisponível;
- histórico vazio mantém o schema canónico;
- `Adj Close` em falta permanece explicitamente em falta e não é substituído por `Close`;
- timestamps com timezone são testados com conversão efetiva para UTC timezone-naive;
- erros de download de histórico são convertidos para `MarketDataUnavailableError`;
- política V0.2: sem retries automáticos escondidos; o utilizador pode repetir a operação;
- edição de notas fica para a fase Research;
- múltiplas Watchlists ficam fora da V0.2 e serão reavaliadas quando houver necessidade funcional;
- cache de histórico fica para V0.4 Analysis;
- GitHub Actions passa a executar testes também em pushes para `dev`.

## Validação final da V0.2 concluída

Validação local concluída em Windows através de `dev` e `run.ps1`.

Foram confirmados:

- testes locais sem falhas;
- adição manual de tickers válidos com metadados;
- rejeição de tickers sintaticamente inválidos;
- rejeição de tickers inexistentes sem os adicionar à Watchlist;
- atualização de preços sem bloquear a interface;
- funcionamento de S&P 500, NASDAQ 100 e Euronext 100;
- persistência da Watchlist e dos estados;
- persistência das larguras das colunas.

A comparação periódica da composição do Euronext 100 com a fonte oficial passa a ser manutenção e não bloqueia o fecho da V0.2.

## Fases posteriores

### V0.3 — Portfolio

- entidade `Portfolio`;
- entidade `Transaction`;
- compras e vendas;
- posições calculadas a partir das transações;
- preço médio;
- PnL realizado e não realizado;
- moeda base;
- comissões;
- importação e exportação.

### V0.4 — Analysis

- gráficos;
- volume;
- SMA;
- EMA;
- RSI;
- MACD;
- Bollinger;
- ATR;
- estatística;
- validação matemática dos indicadores.

### V0.5 — Strategies

- interface comum de estratégias;
- SMA Crossover;
- RSI + MACD;
- parâmetros;
- testes de sinais.

### V0.6 — Backtesting

- motor temporal;
- execução;
- custos;
- slippage;
- position sizing;
- equity curve;
- métricas;
- benchmark.

### V0.7 — Investment Research

- diário;
- tese;
- catalisadores;
- riscos;
- invalidação;
- cenários;
- revisão.

### V0.8 — AI Foundation

- datasets;
- features;
- targets;
- pipelines;
- validação temporal;
- modelos baseline;
- `ModelRun`;
- `Prediction`;
- avaliação fora da amostra.

### V0.9 — AI Research

- calibração;
- ensembles;
- regressão de retornos;
- ranking;
- explicabilidade;
- avaliação por regimes e horizontes.

### V0.10 — AI Planning

- Planeamento IA experimental;
- estados;
- contexto;
- ações possíveis;
- transições;
- avaliação de planos;
- histórico de decisões simuladas.

### V1.0

- integração;
- testes;
- documentação;
- migrações;
- tratamento de erros;
- instalação reproduzível;
- revisão de privacidade;
- estabilização da interface.

## Decisões vigentes

- o projeto legacy permanece privado e apenas como referência;
- não copiar código legacy sem revisão;
- Python mantém-se como linguagem;
- PySide6 substitui PyQt5;
- SQLite é a persistência inicial;
- SQLAlchemy abstrai a persistência;
- transações serão a origem da verdade da carteira;
- IA mantém-se no plano desde o início;
- Planeamento IA mantém-se como componente prevista;
- nenhuma execução automática de ordens é objetivo da fase atual;
- dados pessoais, posições reais, credenciais, caches e modelos treinados não entram no Git;
- preferências visuais do utilizador podem ser persistidas localmente com `QSettings`, separadas dos dados financeiros.


## Fluxo Git canónico

O desenvolvimento corrente usa duas branches:

- `main`: contém apenas estados validados pelo utilizador;
- `dev`: contém trabalho em curso, correções, testes e documentação intermédia.

Regras:

- todo o desenvolvimento novo é feito em `dev`;
- o utilizador testa localmente a branch `dev` através de `run.ps1`;
- `run.ps1` muda para `dev` quando necessário, atualiza a branch, instala dependências, executa os testes e arranca a aplicação;
- nenhuma alteração deve ser integrada em `main` sem pedido explícito do utilizador;
- quando um bloco estiver validado e o utilizador pedir passagem para `main`, a integração é feita por squash para produzir um único commit coerente;
- depois da integração, o trabalho seguinte continua em `dev`;
- commits intermédios de `dev` são considerados técnicos e não fazem parte do histórico final pretendido da `main`.
