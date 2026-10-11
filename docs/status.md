# Estado atual do projeto

> **Estado atual (2026-10-11):** V0.2.0 integrada na `main` e tag publicada; A1–A5, A7 e A8 especificados para V0.3, A6 fechado no D1. Consulte **«Síntese prevalecente pós-auditoria»**, no fim deste documento. A antiga leitura rápida de 2026-10-10 é histórica e não constitui o estado vigente.

Última atualização canónica: 2026-10-11.

Este documento regista o estado efetivo do projeto BolsaNext. O roadmap define o destino; este ficheiro define o ponto em que o projeto se encontra agora.


## Leitura rápida: registo histórico de 2026-10-10 (substituído pela síntese pós-auditoria de 2026-10-11 no fim do documento)

A V0.2 foi funcionalmente integrada anteriormente; o saneamento atual decorre **exclusivamente em `dev`**. S0, D1–D3, B1–B10 e I1–I5 estão concluídos e validados; **B11 está em auditoria final, ainda por validar e integrar**. Consultar `docs/b11-final-audit.md` para as evidências verificadas e as métricas ainda pendentes. A V0.3 não começou. A `main` não recebeu este saneamento e a tag `v0.2.0` ainda não existe. Informações posteriores nesta página com a indicação «pendente» para blocos já concluídos são registos de execução histórica e não prevalecem sobre este estado.

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

Clone local confirmado limpo por `git status --short` sem saída e SHA local sincronizado com a `dev` (`ced77dc23897603c8b68a908e946767793e4dffb`). **S0 está CONCLUÍDO E VALIDADO.** Próximo passo: D1/A6 — semântica de `market` e proveniência dos metadados.

### D1 — metadados e significado de market/exchange

Estado: **DECIDIDO E DOCUMENTADO**.

Decisão vigente:

- `market` deixa de significar mistura de região e bolsa; o conceito canónico passa a ser exchange/listing venue;
- a implementação deverá evoluir para `exchange` e a UI apresentará **Bolsa**;
- universos são autoridade para composição e apenas fornecem metadados provisórios/fallback;
- Yahoo é a fonte principal para nome canónico, exchange, moeda e tipo de ativo;
- falha temporária do Yahoo não obriga a inventar metadados: ticker/nome provisório podem ser preservados e exchange/moeda ficam por completar;
- `Atualizar dados` deverá voltar sempre à fonte principal;
- precedência entre fontes pertence à Application, não à UI nem ao repository;
- a decisão governa B3 e B8.2.

D2 e D3 estão decididos e documentados. Próximo passo: **B1 — Ports e direção das dependências**.

### D2 — backup antes de movimentos e migrações

Estado: **DECIDIDO E DOCUMENTADO**.

Decisão vigente:

- backup obrigatório antes de qualquer migração de schema ou mudança de localização da base;
- preferência pela SQLite Backup API para snapshots consistentes;
- backups imutáveis, timestamped e fora do Git;
- validação obrigatória do backup e da base resultante com `PRAGMA quick_check`;
- se o backup falhar, a operação não começa;
- em falha de migração/movimento, a base original e o backup permanecem preservados;
- restauro é sempre explícito, nunca automático;
- não há rotação automática de backups nesta fase;
- a política aplica-se a B5/B6; o backup/export/import funcional da futura carteira permanece adiado para A7/V0.3.

Próximo passo: **D3 — parte atual de A5: significado de `base_currency` na configuração**.

### D3 — moeda base por omissão

Estado: **DECIDIDO E DOCUMENTADO**.

Decisão vigente:

- `AppConfig.base_currency` é semanticamente apenas a moeda base por omissão;
- o nome preferido passa a ser `default_base_currency`;
- a configuração não é autoridade financeira global e não poderá alterar silenciosamente entidades persistidas;
- a futura `Portfolio.base_currency` será autoridade da própria carteira, mas permanece fora deste ciclo;
- não se iniciam cálculos financeiros nem FX nesta fase.

Próximo passo: **B1 — Ports e direção das dependências**.

### B1 — ports e direção das dependências

Estado: **CONCLUÍDO E VALIDADO**.

Implementado no commit `0f680d36a836c8add5893db0c65d6d3f32fab865`:

- contratos movidos para `src/bolsa/app/ports/`;
- services da Application deixaram de importar Infrastructure;
- erros de Market Data passaram a ser canónicos em `app/ports/errors.py`;
- `WatchlistRepository` passou para `app/ports/repositories.py`;
- caminhos antigos de provider/universe/errors mantidos como reexports de compatibilidade;
- criado teste arquitetural que impede regressão `Application → Infrastructure`;
- arquitetura canónica atualizada.

GitHub Actions: **40 testes passaram**. O 40.º teste é a nova proteção arquitetural.

Validação local concluída em Windows: `git pull --ff-only origin dev`, `python -m pytest -q` com **40 passed in 2.71s** e arranque da aplicação com `python -m bolsa.main`. **B1 está CONCLUÍDO E VALIDADO.** Próximo bloco: **B2 — erros externos**.

### B2 — erros externos unificados

Estado: **CONCLUÍDO E VALIDADO**.

Decisões e implementação:

- raiz comum `ExternalDataError`;
- famílias paralelas `MarketDataError` e `UniverseError`;
- preço atual deixa de devolver `None` ambiguamente e passa a usar exceções tipadas;
- distinguem-se ticker inexistente, fornecedor indisponível, ausência de cotação e formato inesperado;
- universos distinguem código não suportado, fonte indisponível e formato inválido;
- `UniverseLoadResult` expõe `LIVE`, `FRESH_CACHE` e `STALE_CACHE`;
- cache stale pode ser usada até 7 dias quando a fonte falha por indisponibilidade ou formato, sempre com aviso/timestamp;
- Watchlist preserva as restantes linhas quando um preço falha;
- UI mostra avisos de preço e frescura dos universos.

GitHub Actions: **58 testes passaram em 2.44s**.

Validação local confirmada pelo utilizador em 2026-10-06. **B2 está CONCLUÍDO E VALIDADO.** Próximo bloco: **B3 — moedas em subunidade**.

### B3 — subunidades monetárias

Estado: **CONCLUÍDO E VALIDADO**.

Implementado no commit `d27342efbb0665db2a44bb39a4da4d728eeaa19b`:

- convenções Yahoo ficam no adapter e não no Domain;
- `GBp/GBX → GBP × 0.01`, `ZAc → ZAR × 0.01`, `ILA → ILS × 0.01`;
- códigos canónicos de três letras em maiúsculas usam fator 1;
- convenções inesperadas produzem `MarketDataFormatError`;
- preço atual e OHLC + Adj Close são escalados; Volume não é alterado;
- convenção é mantida em cache de sessão por ticker;
- moeda do `Instrument` não é usada para inferir escala;
- regressão `12345 GBp → 123.45 GBP` coberta por teste.

GitHub Actions: **72 testes passaram em 1.01s**.

Validação local confirmada pelo utilizador em 2026-10-07. **B3 está CONCLUÍDO E VALIDADO.** Próximo bloco: **B4 — integridade SQLite**.

Nota para B9: CI emitiu aviso de depreciação do runtime Node.js 20 usado pelas versões atuais de checkout/setup-python; não bloqueia B3, mas fica preservado para revisão de CI.

### B4 — integridade SQLite

Estado: **CONCLUÍDO E VALIDADO**.

Implementado no commit `ec1c7eb3e3e1577daa08112d76c70858f979f5c0`:

- `PRAGMA foreign_keys = ON` em todas as ligações SQLite;
- `PRAGMA busy_timeout = 5000` ms;
- foreign keys inválidas são rejeitadas e o rollback deixa a base consistente;
- `ON DELETE CASCADE` foi testado diretamente na base;
- remover Watchlist/WatchlistItem não elimina `Instrument` órfão;
- testes de integração fazem `engine.dispose()`;
- `main()` liberta o engine em `finally`;
- WAL foi avaliado e fica deliberadamente desativado nesta fase;
- `create_all()` mantém-se temporariamente até B6.

GitHub Actions: **75 testes passaram em 1.71s**. O `ResourceWarning` SQLite do baseline S0 não apareceu neste CI.

Durante a primeira validação local, o Windows App Control bloqueou `sqlalchemy.util._collections_cy`. O problema foi resolvido sem enfraquecer a política de segurança, reinstalando a mesma versão do SQLAlchemy em modo pure-Python. A validação local foi depois concluída pelo utilizador em 2026-10-08. **B4 está CONCLUÍDO E VALIDADO.** Próximo bloco: **B5 — localização estável dos dados**.

### B5 — localização estável dos dados

Estado: **CONCLUÍDO E VALIDADO**.

Implementado no commit `66e257a75fa0deb0a9a6d3731b1ea79a79fc91f8`:

- dados deixam de depender de `Path("data")` relativo;
- localização normal por utilizador/SO através de `platformdirs`;
- override explícito com `BOLSANEXT_DATA_DIR`;
- `load_config()` deixa de criar diretórios;
- `prepare_environment()` cria data/cache/backups apenas quando necessário;
- `base_currency` passa a `default_base_currency` conforme D3;
- existência de base legacy bloqueia criação silenciosa de uma base vazia nova;
- ferramenta de migração em dry-run por omissão;
- migração efetiva usa SQLite Backup API + `PRAGMA quick_check`;
- origem é preservada e destino existente nunca é sobrescrito;
- cache antiga não é migrada.

GitHub Actions: **83 testes passaram em 1.47s**.

Falta executar a migração real no PC do utilizador e validar a aplicação sobre a nova localização. Próximo bloco depois disso: **B6 — migrações de schema**.

Primeira validação local B5 em Windows: o dry-run mostrou corretamente origem/destino/backup, mas um teste falhou com `WinError 32` porque ligações `sqlite3` permaneciam abertas após o context manager. A implementação e fixtures foram corrigidos com fecho explícito via `contextlib.closing`. Aguarda repetição da suite local e só depois migração real.

Migração real B5 concluída em 2026-10-08: suite local com **83 testes passados**, origem preservada em `C:\Users\Portatil\Documents\GitHub\BolsaNext\data\bolsanext.sqlite3`, backup criado em `C:\Users\Portatil\AppData\Local\BolsaNext\backups\bolsanext_before_move_20261008_010523.sqlite3` e nova base ativa em `C:\Users\Portatil\AppData\Local\BolsaNext\bolsanext.sqlite3`. A ferramenta confirmou migração e validação com sucesso. A aplicação foi depois aberta sobre a nova base, a Watchlist/estados foram confirmados, foi alterado um estado e, após fechar/reabrir, a alteração permaneceu. **B5 está CONCLUÍDO E VALIDADO.** Próximo bloco: **B6 — migrações de schema**.

### B6 — migrações de schema

Estado: **CONCLUÍDO E VALIDADO**.

Implementado:

- Alembic passa a ser autoridade do schema;
- baseline V0.2: `0001_v02_baseline`;
- `create_all()` removido do runtime;
- bases novas usam `upgrade head`;
- base V0.2 existente é validada, recebe backup e só depois `stamp baseline`;
- bases atrasadas recebem backup + upgrade;
- revisões desconhecidas/incompatíveis são bloqueadas;
- não existe downgrade automático;
- backups reutilizam a infraestrutura D2/B5;
- `market → exchange` permanece para uma migration posterior real.

GitHub Actions: **92 testes passaram em 1.99s**.

Validação local concluída em 2026-10-08: 92 testes passaram; a base real recebeu a baseline `0001_v02_baseline` com backup prévio; os dados foram preservados; e um segundo arranque em head não criou novo backup. **B6 está CONCLUÍDO E VALIDADO.** Próximo bloco: **B7 — fonte única de versão**.

### B7 — fonte única de versão

Estado: **CONCLUÍDO E VALIDADO**.

Implementado no commit `090c1ccea0300292dd69f96dd22a4189c553bb81`:

- versão canónica em `src/bolsa/version.py`;
- valor canónico atual: `0.2.0`;
- `bolsa.__version__` reexporta essa fonte;
- `pyproject.toml` usa metadata dinâmico em vez de versão literal;
- User-Agent usa a versão canónica;
- UI apresenta a versão através de `version_label()`;
- tag `v0.2.0` continua proibida até B11.

GitHub Actions: **97 testes passaram em 1.81s**.

Validação local concluída em 2026-10-08: versão canónica, metadata instalado, User-Agent e UI confirmados em `0.2.0`. **B7 está CONCLUÍDO E VALIDADO.** Próximo bloco: **B8 — Hardening Watchlist/UI**.

### B8.1 — concorrência global

Estado: **CONCLUÍDO E VALIDADO**.

Implementado:

- `WatchlistService` protegido por `RLock`;
- coordenador global partilhado entre WatchlistWidget e UniverseWidget;
- uma única operação assíncrona da área de cada vez;
- alterações de estado, remoção, adição, refresh de preços/metadados e carregamento de universo coordenados;
- libertação do busy no sinal `finished`, incluindo caminhos de erro;
- teste real de concorrência entre duas threads;
- imports lazy de `bolsa.ui.watchlist` para manter os testes do coordenador headless.

GitHub Actions final: **101 testes passaram em 2.04s**. A primeira execução falhou apenas por import eager de QtWidgets/libEGL no runner headless e foi corrigida sem alterar o desenho funcional.

Validação local concluída em 2026-10-08: os controlos mutáveis ficaram bloqueados durante as operações e foram libertados no fim, incluindo coordenação entre Watchlist e Universos. **B8.1 está CONCLUÍDO E VALIDADO.** Próximo sub-bloco: **B8.2 — UniverseWidget e decisão D1**.

### B8.2 — UniverseWidget e D1

Estado: **CONCLUÍDO E VALIDADO**.

Implementado:

- `market` passa a `exchange` no domínio, repository e persistência;
- nova migration `0002_market_to_exchange` preserva os valores existentes;
- Watchlist apresenta **Bolsa**;
- Wikipedia fica limitada a composição + ticker/nome provisório;
- exchange/moeda/tipo deixam de ser inferidos pelo universo;
- cache de universos v2 invalida caches antigas;
- UniverseWidget conserva os objetos `Instrument` e não os reconstrói a partir das células;
- Yahoo é a autoridade dos metadados canónicos;
- fallback de universo perante indisponibilidade Yahoo preserva apenas ticker/nome e deixa exchange/moeda desconhecidos;
- ticker inexistente no Yahoo não é adicionado;
- **Atualizar dados** volta sempre ao Yahoo, mesmo para instrumentos já completos.

GitHub Actions: **107 testes passaram em 2.61s**.

Validação local concluída em 2026-10-09: migration `0002_market_to_exchange`, coluna **Bolsa**, tabela de Universos apenas Ticker/Nome, enriquecimento Yahoo, atualização de metadados e persistência foram confirmados. **B8.2 está CONCLUÍDO E VALIDADO.** Próximo sub-bloco: **B8.3 — cache de preços da sessão**.

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

### Estabilização V0.2, B8.3 (2026-10-09)

**Implementado em `dev`, por validar localmente.** O `WatchlistService` mantém preços e respetivos instantes UTC apenas em memória durante a sessão. Refreshes posteriores da tabela/metadados conservam preços; erros individuais mantêm a última cotação válida com aviso; remover um ticker limpa a entrada da cache. A UI identifica a atualização e a memória da sessão. Não existe persistência de preços nem nova migração. Testes de regressão acrescentados. B8.3 permanece **PENDENTE DE VALIDAÇÃO**, B8.4/B8.5 ainda por iniciar; V0.3 continua bloqueada.

Registo de validação B8.3 (2026-10-09): o utilizador confirmou que os testes locais e funcionais correram como esperado. **B8.3 CONCLUÍDO E VALIDADO**. Próximo passo B8.4, ainda não implementado. A `main` e a tag `v0.2.0` mantêm-se intocadas.

### B8.4 — Validação sintática realista (2026-10-10)

**Implementado em `dev`, a aguardar validação local.** O domínio `Instrument` rejeita símbolos constituídos apenas por pontuação e estruturas manifestamente malformadas sem rejeitar os formatos Yahoo já previstos (`^GSPC`, `BRK-B`, `ASML.AS`, `EURUSD=X`). Acrescentados testes de regressão parametrizados. Nenhum provider ou schema alterado. O bloco permanece pendente de validação e B8.5 ainda não foi iniciado.

Registo de validação B8.4 (2026-10-10): o utilizador confirmou que executou os testes e que o resultado foi correto. **B8.4 CONCLUÍDO E VALIDADO**. Mantêm-se os testes de regressão, a distinção entre sintaxe e existência real no provider e as decisões anteriores. Próximo sub-bloco: B8.5, ainda por implementar. `main` e tag `v0.2.0` não alteradas.

### B8.5 — Estado desconhecido defensivo (2026-10-10)

**Implementado em `dev`, pendente de validação local.** Combobox do estado apresenta `Desconhecido` quando recebe valor sem correspondência, sem escolher outro estado automaticamente. Inicialização bloqueia sinais, e a conversão defensiva evita persistir valores inválidos. Regressões headless adicionadas. Sem alteração de schema ou domínio. B8 aguarda fecho local de B8.5.

Registo de validação B8.5 e fecho B8 (2026-10-10): o utilizador confirmou que executou todos os testes locais e que tudo funcionou. **B8.5 CONCLUÍDO E VALIDADO** e **B8 (B8.1 a B8.5) CONCLUÍDO E VALIDADO**. Preservam-se integralmente os registos históricos e decisões anteriores. O bloco seguinte é B9 (CI, dependências e qualidade), ainda por executar. Não houve integração em `main` nem criação da tag `v0.2.0`.

### B9.1 — Cobertura dos testes no GitHub Actions (2026-10-10)

**Implementado em `dev`, por validar.** Workflow Linux/Python 3.12 mede cobertura com `pytest-cov` e produz relatório no log, `coverage.xml` e `htmlcov/` arquivados no GitHub Actions. Sem limiar obrigatório. Cobertura e número de testes efetivos devem ser recolhidos do novo run; não foram inventados. Próximo passo após validação: B9.2.

### Progresso B9 (2026-10-10)

**B9.1 CONCLUÍDO E VALIDADO** após confirmação do utilizador de que os testes e cobertura correram como esperado. Métricas numéricas ainda não registadas por não terem sido fornecidas. **B9.2 IMPLEMENTADO EM `dev`, AGUARDA VALIDAÇÃO**: matriz Ubuntu/Python 3.12 e Windows/Python 3.14, PR para `main`/`dev`, relatórios de cobertura separados por ambiente. B9.3 a B9.5 permanecem pendentes.

Validação B9.2 (2026-10-10): o utilizador confirmou a conclusão da verificação solicitada do CI Linux/Windows. **B9.2 CONCLUÍDO E VALIDADO**. Segue-se B9.3, auditoria e decisão das dependências, sem alterações ao `pyproject.toml` antes da aprovação do desenho. `main` e tag `v0.2.0` continuam inalteradas.

### B9.3 — Dependências e versões (2026-10-10)

**IMPLEMENTADO EM `dev`, PENDENTE DE VALIDAÇÃO.** Core reduzido a sete dependências diretas necessárias à V0.2, preservando explicitamente `lxml` para `pandas.read_html`. `numpy`, `scikit-learn`, `matplotlib` e `PyYAML` agrupadas em `analysis` opcional. Adicionados limites mínimos conservadores em `pyproject.toml` e registo das versões instaladas no CI. Não introduzidos limites máximos arbitrários nem lockfile. Validar jobs Linux/Windows e arranque local antes do fecho; B9.4 ainda por iniciar.

Validação B9.3 (2026-10-10): testes e aplicação confirmados pelo utilizador. **B9.3 CONCLUÍDO E VALIDADO**. Próximo bloco B9.4 (Ruff), ainda não implementado. `main` e a tag `v0.2.0` permanecem intactas.

### B9.4 — Introdução gradual do Ruff (2026-10-10)

**EM AUDITORIA, por validar.** Ruff incluído só nas dependências `dev` com regras `E4`, `E7`, `E9`, `F`; GitHub Actions recolhe resultados Linux/Windows de modo não bloqueante. Não foi aplicada reformatação automática nem corrigidos problemas ainda não medidos. É necessário verificar o log da etapa Ruff, corrigir apenas problemas reais e repetir CI antes de tornar lint obrigatório.

### B9.4 — Correção da ocorrência Ruff (2026-10-10)

Confirmado pelo log CI fornecido pelo utilizador: uma ocorrência `F401`, import `BASELINE_REVISION` não utilizado em `tests/integration/test_schema_migrations.py`. Import removido e lint tornado obrigatório em Linux e Windows. **PENDENTE DE VALIDAÇÃO DO NOVO CI**; B9.5 ainda por iniciar. Avisos sobre versões Node.js das GitHub Actions registados separadamente.

Validação B9.4 (2026-10-10): GitHub Actions execução #336, commit `bc61f9dd`, concluída com sucesso em Linux/Python 3.12 e Windows/Python 3.14; em ambos, `Ruff lint` e `Run tests with coverage` terminaram com `success`. O utilizador apresentou a execução bem-sucedida. **B9.4 CONCLUÍDO E VALIDADO**. B9.5, estratégia futura de testes, é o próximo sub-bloco, ainda por implementar. `main` e tag `v0.2.0` permanecem inalteradas.

### B9.5 — Estratégia futura de testes (2026-10-10)

**IMPLEMENTADO DOCUMENTALMENTE EM `dev`, POR VALIDAR PELO UTILIZADOR.** `docs/development.md` passa a explicitar a base de testes existente, políticas para domínio/cálculos, SQLite/Alembic, ports/providers, UI PySide6, concorrência, backtesting e IA temporal, critérios de regressão e gates para CI/fecho B11. Não foram criados testes, dependências ou funcionalidades. As métricas atuais da cobertura não foram inferidas da baseline histórica. B9 só fecha formalmente após validação deste sub-bloco.

Validação B9.5 e fecho B9 (2026-10-10): o utilizador aprovou expressamente a estratégia documental de testes. **B9.5 CONCLUÍDO E VALIDADO** e **B9 (B9.1–B9.5) CONCLUÍDO E VALIDADO**. Próximo bloco: B10, auditoria de coerência canónica; primeiro analisar e propor correções sem alterar documentos antes da validação do desenho. Os itens avulsos I1–I5 e o fecho B11 continuam obrigatórios. A `main` e a tag `v0.2.0` permanecem intocadas.

### B10 — Revisão de coerência documental (2026-10-10)

**ALTERAÇÕES IMPLEMENTADAS EM `dev`, PENDENTES DE VALIDAÇÃO DO UTILIZADOR.** Após aprovação do desenho, foram feitas correções pontuais nos oito documentos canónicos e no plano de estabilização: síntese de estado vigente no início dos documentos operacionais, atualização do âmbito de CI (Linux 3.12, Windows 3.14, cobertura e Ruff), distinção entre dependências do núcleo e opcionais, clarificação de `exchange` versus `market`, identificação explícita de material histórico de legacy e de funcionalidades IA futuras, e esclarecimento da hierarquia documental para agentes. Registos históricos de decisões e testes são conservados; B9 está concluído, enquanto I1–I5 e B11 continuam pendentes. Não foi alterado código funcional, configuração de CI nem schemas. **Não fechar B10 sem validação do utilizador.** `main` e tag `v0.2.0` continuam intocadas.

Validação B10 (2026-10-11): o utilizador confirmou expressamente a revisão documental. **B10 CONCLUÍDO E VALIDADO**. Os itens avulsos I1–I5 permanecem obrigatórios antes do fecho B11. Próximo passo: analisar o I1 (escrita atómica da cache de universos), sem implementar antes da validação do desenho. `main` e tag `v0.2.0` permanecem intocadas.

### Item I1 — Cache de universos (2026-10-11)

**Implementado na `dev`, por validar.** Cache JSON de universos passa a ser substituída atomicamente por `os.replace` após escrita em ficheiro temporário no mesmo diretório e fecho do handle. Em falha, o original é conservado e o temporário limpo. Testes de regressão acrescentados. I2–I5 e B11 continuam obrigatórios. Sem alteração funcional à UI, schema ou metadados.

Validação I1 (2026-10-11): o utilizador confirmou os testes locais e autorizou avançar. **I1 — ESCRITA ATÓMICA DA CACHE DE UNIVERSOS CONCLUÍDO E VALIDADO.** Próximo item I2: analisar a política de preservação dos instrumentos órfãos; primeiro apresentar o desenho, sem alterações funcionais antes da aprovação. I3–I5 e B11 continuam pendentes; `main` e tag `v0.2.0` intactas.

### I2 — Preservação de instrumentos órfãos (2026-10-11)

**CONCLUÍDO E VALIDADO.** O utilizador aprovou a política de preservar na tabela `instruments` os ativos removidos da Watchlist; apenas a associação em `watchlist_items` é eliminada. O comportamento já estava implementado e protegido por `tests/integration/test_watchlist_repository.py::test_watchlist_repository_persists_removal`. O I2 formaliza a decisão sem alterar código, testes, dados ou migrações. Não se adiciona limpeza automática. I1 e I2 concluídos; I3–I5 e B11 pendentes. `main` e tag `v0.2.0` intocadas.

### I3 — Regra de PDFs no .gitignore (2026-10-11)

**IMPLEMENTADO CONFORME DESENHO APROVADO; AGUARDA VALIDAÇÃO DO RESULTADO.** Removida exclusivamente a regra global `*.pdf` de `.gitignore`, permitindo acrescentar PDFs técnicos legítimos, nomeadamente em `docs/`. Mantidas as regras para `statements/`, `extracts/`, `extratos/`, ficheiros de transações/posições e restantes dados pessoais. A remoção de uma exclusão não autoriza versionar documentos sensíveis: rever sempre os ficheiros antes de `git add`. I4 (LICENSE) necessita de decisão explícita antes de implementação.

### I4 — Licença do projeto (2026-10-11)

O utilizador escolheu **GPL-3.0**. Criado na branch `dev` o ficheiro `LICENSE` com o texto oficial da GNU General Public License versão 3, usando o identificador SPDX `GPL-3.0-only` (sem autorização automática para versões posteriores). O `README.md` identifica a licença. **IMPLEMENTADO, PENDENTE DE CONFIRMAÇÃO FINAL DO UTILIZADOR**. Nenhuma alteração de código ou dependências. I3 permanece implementado mas ainda sem confirmação final expressa; I5 e B11 pendentes.

Validação expressa I3 e I4 (2026-10-11): o utilizador confirmou concordância com a alteração restrita do `.gitignore` (permitir PDFs técnicos, mantendo exclusões sensíveis) e com a licença **GPL-3.0-only**. **I3 CONCLUÍDO E VALIDADO; I4 CONCLUÍDO E VALIDADO**. I1–I4 fechados. I5 (`run.ps1` e ambiente virtual) passa à fase de auditoria e desenho; nenhuma alteração ao script sem aprovação do utilizador. B11 permanece pendente, sem alterações à `main` ou à tag `v0.2.0`.

### I5 — run.ps1 e ambiente virtual opcional (2026-10-11)

**IMPLEMENTADO EM `dev`, PENDENTE DE VALIDAÇÃO FUNCIONAL WINDOWS.** O script procura primeiro `.venv/Scripts/python.exe` na raiz do projeto; se não existir, usa `python` do PATH, sem criar nem impor ambiente virtual. Mostra o interpretador escolhido, que é usado consistentemente para `pip`, Ruff, pytest e arranque. Ruff e pytest integram a etapa de testes e ambos são omitidos ao usar `-SkipTests`. Mantidos `-SkipPull`, `-SkipInstall`, a seleção automática de `dev` e a política de parar perante erros. Sem alterações a dependências, schema ou funcionalidades. B11 só começa após validação do I5. `main` e tag `v0.2.0` intactas.

I5, complemento de arranque Windows (2026-10-11): criado `run.cmd` na raiz da `dev`, que chama `run.ps1` via PowerShell com `-NoProfile -ExecutionPolicy Bypass -File` no processo filho e encaminha argumentos. Não altera a política persistente do Windows, mas essa sessão usa Bypass e políticas organizacionais podem impedir a execução. `run.ps1` mantém o fluxo, venv opcional e Ruff. **I5 continua por validar localmente.**

Validação I5 (2026-10-11): o utilizador confirmou que `run.cmd` executou corretamente no Windows. **I5 CONCLUÍDO E VALIDADO**; o arranque via `run.cmd`, seleção opcional da `.venv` e sequência Ruff/pytest/aplicação foram aceites no teste funcional. **I1–I5 CONCLUÍDOS E VALIDADOS.** Abre-se B11 para revisão final de suite, cobertura, CI, diff desde S0, documentação, pendências e autorização final. Não integrar na `main`, nem criar `v0.2.0`, sem autorização explícita posterior.

B11, auditoria de fecho (2026-10-11): relatório verificável em `docs/b11-final-audit.md`. Comparação `main...dev`: 291 commits à frente, zero atrás na consulta anterior aos commits deste relatório; CI #390 Linux 3.12 e Windows 3.14, Ruff e pytest aprovados. Baseline S0: 39 testes e 55%; **contagem e cobertura atuais ainda por recolher**. A auditoria está documentada, **B11 ainda não está CONCLUÍDO E VALIDADO**; a `main` e `v0.2.0` permanecem intactas.

B11, medição final recebida do utilizador (2026-10-11): **161 testes aprovados em 6,46 s e 61% de cobertura** (1754 statements, 679 miss) no Windows; baseline S0 **39 testes e 55%**. Evolução **+122 testes e +6 pontos percentuais**. Distribuição de cobertura não uniforme, sobretudo UI e pontos de entrada, documentada como limitação; ver `docs/b11-final-audit.md`. Falta confirmar o último CI após os commits documentais e obter validação explícita do utilizador antes de qualquer integração na `main` e criação de `v0.2.0`. **B11 em pré-fecho, não integrado.**

B11, validação final do utilizador (2026-10-11): o utilizador confirmou expressamente a aceitação do relatório B11, **161 testes aprovados e 61% de cobertura** (+122 testes e +6 pontos percentuais face a S0), incluindo as lacunas de UI documentadas para evolução futura. **B11 — AUDITORIA E VALIDAÇÃO DO UTILIZADOR CONCLUÍDAS; INTEGRAÇÃO/PUBLICAÇÃO PENDENTES DE AUTORIZAÇÃO SEPARADA.** Na última consulta, o CI #400 relativo ao commit anterior à validação ainda estava em curso; verificar novamente o CI do estado final antes de integrar. Não efetuar squash/merge em `main` nem criar tag `v0.2.0` sem pedido explícito. V0.3 mantém-se por iniciar.

## Estado vigente após publicação da V0.2.0 e validação A1 (2026-10-11)

A versão **V0.2.0 está publicada**: PR #1 integrado por squash na `main`, commit `a26852232c93cdd593fe179b4393fb2abb171d26`, tag anotada `v0.2.0` verificada a apontar para esse commit. S0, D1–D3, B1–B11 e I1–I5 concluídos e validados. Registos anteriores relativos a B11 pendente ou tag inexistente são históricos, não estado atual.

**V0.3 Portfolio: especificação A1 CONCLUÍDA E VALIDADA pelo utilizador**, documentada em `docs/architecture.md`. Ações/ETFs long-only, BUY/SELL, dividendos manuais com bruto/retenção/encargos/líquido, ajustes manuais auditáveis, correção por substituição rastreável, anulação lógica com histórico preservado. Ledger como origem da verdade; várias carteiras com moeda base própria. A2–A5, A7 e A8 por decidir/validar. **Não houve implementação de Portfolio, alteração de schema ou alteração da `main` ou tag** durante o A1. Próximo passo proposto: especificação contabilística **A2** em conversa, com exemplos numéricos e decisões explícitas antes de alterar a documentação.


## V0.3 Portfolio — A2 concluído e validado (2026-10-11)

O utilizador confirmou a especificação funcional **A2 — Regras contabilísticas**, após validação sequencial: BUY/SELL com custo médio ponderado móvel e comissões; execução/UTC/liquidação opcional; desempate determinístico com alerta de ambiguidades; dividendos líquidos separados do PnL de vendas; splits simples preservando custo total; outros ajustes sujeitos a categorias/fórmulas específicas; invariantes INV-01 a INV-12; correções/anulações com reconstrução completa e rejeição atómica quando invalidam operações posteriores. Fórmulas, exemplos numéricos e invariantes encontram-se em `docs/architecture.md`; critérios de testes em `docs/development.md`.

**Estado vigente:** A1 e A2 CONCLUÍDOS E VALIDADOS **como especificação**; próxima sessão **A3 — Tipos numéricos e precisão** (ainda não validada). Nenhum código Portfolio, teste, migração ou alteração de schema implementado neste bloco. `main` e tag `v0.2.0` intactas.

## V0.3 Portfolio — A3 concluído e validado (2026-10-11)

O utilizador aprovou integralmente a especificação funcional **A3 — Tipos numéricos e precisão**: `Decimal` no domínio; valores financeiros persistidos em SQLite como `TEXT` decimal canónico; 8 casas decimais de entrada para quantidade/preço/montantes, 12 para FX, 18 algarismos inteiros de limite; 50 algarismos significativos de cálculo; `ROUND_HALF_EVEN` por defeito sem arredondamento prematuro; custo médio derivado; fronteira explícita entre market data float e domínio Decimal; preservação dos montantes reais da XTB e sinalização de discrepâncias. Os detalhes estão em `docs/architecture.md` e os critérios de teste em `docs/development.md`.

**Estado vigente:** A1, A2 e A3 concluídos e validados **como especificação funcional**, não como implementação. **A4 — Convenção de câmbio** é o próximo bloco para discussão e validação. Nenhuma alteração de código/schema, nem a `main` ou a tag `v0.2.0`, decorre deste registo.


## V0.3 — A4 validado e decisões iniciais A5 (2026-10-11)

**A4 — Convenção de câmbio CONCLUÍDA E VALIDADA como especificação, não implementação.** Convenção de FX como moeda base por unidade original, câmbio histórico imutável, atual separado, identidade 1, `FxRateProvider` desacoplado com implementação inicial yfinance e inversão normalizada/testada. Preservar câmbio/montantes originais XTB; valor atual em moeda base com cotações de mercado válidas, última sessão relevante e fallback configurável de 72 horas se faltar calendário; sem totais consolidados enganosos perante dados ausentes. Ver `docs/architecture.md` e `docs/development.md`.

**A5 — EM DISCUSSÃO. Duas decisões iniciais aprovadas:** `Portfolio.base_currency` é a autoridade após criação e `AppConfig.default_base_currency` só define o valor inicial de novas carteiras. Alterar moeda de carteira existente exige **operação explícita e controlada**, nunca alteração silenciosa decorrente da configuração global. Efeitos sobre histórico/custos, requisitos de conversão, validade, backup e eventual imutabilidade da moeda **ainda não decididos**. Não declarar A5 validado neste momento.

**Estado vigente:** A1–A4 concluídos e validados a nível de especificação; A5 em análise; A7/A8 posteriores. Nenhum código Portfolio, migração ou schema alterado, e `main`/`v0.2.0` intactas.

## V0.3 — A5 concluído e validado (2026-10-11)

O utilizador aprovou **A5 — Propriedade da moeda base**, ao nível da especificação: `Portfolio.base_currency` é a autoridade persistente; `AppConfig.default_base_currency` apenas sugere o valor inicial de novas carteiras, permitindo a escolha pelo utilizador. Na V0.3, a moeda base é imutável **após criação**, e qualquer futura migração será explícita, controlada e auditável; mudar a configuração global nunca altera carteiras existentes. Moedas ISO 4217 normalizadas, com validação de códigos suportados. Migração da configuração antiga preserva valor válido; EUR somente se ausente; erro identificável em valor inválido. Detalhes em `docs/architecture.md` e plano de testes em `docs/development.md`.

**Estado vigente:** A1–A5 concluídos e validados **como especificação**, A6 já tratado na estabilização da V0.2; **A7 — Backup, exportação, importação e duplicados** é o próximo bloco, mantendo a política D2/A7.1 já validada. A8 continua pendente. Nenhum código Portfolio/schema ou ficheiro na `main`/`v0.2.0` alterado neste bloco.

## V0.3 — A7 concluído e validado (2026-10-11)

O utilizador aprovou integralmente a **especificação funcional A7 — Backup, exportação, importação e duplicados**: JSON canónico versionado com carteira, instrumentos, transações e histórico completo/auditável; montantes Decimal como texto; UUID persistente por transação e identidade externa composta (origem, conta e external_id), sem usar fingerprint financeiro como prova única; importação com pré-validação, confirmação atómica e rollback total perante falhas; duplicados comprovados ignorados, conflitos explicitamente rejeitados; pré-visualização e relatório final de inseridas/ignoradas/conflitos/rejeitadas. Restauro para carteira nova e importação complementar validada, cópias independentes com novo UUID de carteira e proveniência preservada, substituição destrutiva excluída. D2/A7.1 mantém a política anterior de backup. Ver detalhes em `docs/architecture.md` e testes futuros em `docs/development.md`.

**Estado vigente:** A1–A5 e A7 concluídos e validados **como especificação**, A6 resolvido na estabilização V0.2; **A8 — Reconciliação XTB e política pessoal de investimento** é o próximo bloco pendente. Sem código Portfolio, migração, mudança de schema, integração em `main` ou alteração da tag `v0.2.0` nesta consolidação.


## V0.3 — A8 validado; especificação funcional A1–A8 concluída (2026-10-11)

**A8 — Reconciliação interna e política pessoal de investimento VALIDADO FUNCIONALMENTE:** a V0.3 realiza verificações internas de integridade e relatórios de discrepâncias do ledger; reconciliação automática com extratos reais XTB só numa versão futura. Políticas de risco opcionais, próprias e versionadas por carteira; indicadores de concentração por instrumento/setor/moeda, ganhos/perdas e desvios de objetivos; limites não impostos, alertas informativos sob pedido; dados essenciais ausentes ⇒ não avaliável, nunca conformidade presumida; métricas de rentabilidade anualizada exigem metodologia futura; sem sugestões automáticas de compras/vendas nem execução na XTB. Consulte `docs/architecture.md` e `docs/development.md`.

**Estado vigente:** A1–A5, A7 e A8 validados **como especificações funcionais**; A6 tratado na estabilização V0.2. A fase de especificação funcional está concluída, não a implementação. **Auditoria técnica global A1–A8 recomendada, mas explicitamente NÃO autorizada nesta etapa e NÃO iniciada.** Nesta atualização apenas documentação na `dev`; sem código/schema/testes alterados e sem alteração à `main` ou tag `v0.2.0`.


## Síntese prevalecente pós-auditoria — 2026-10-11

**ESTE BLOCO PREVALECE sobre a antiga secção «Leitura rápida: estado vigente (2026-10-10)», que permanece abaixo por rastreabilidade histórica, mas está desatualizada.** A V0.2 estabilizada foi integrada por squash na `main`, commit `a26852232c93cdd593fe179b4393fb2abb171d26`, e a tag `v0.2.0` existe e aponta para esse commit. A `dev` diverge em histórico por causa desse squash; a comparação GitHub à data da auditoria indicou 328 commits à frente e 1 atrás, não sendo prova de desvio funcional por si só.

**Especificação V0.3:** A1–A5, A7 e A8 funcionalmente aprovados e documentados; A6 absorvido pelo D1 da estabilização V0.2. A auditoria documental detetou e resolveu em aditamento técnico AUD-001 a AUD-012 (em `docs/architecture.md` e testes previstos em `docs/development.md`): versões e anulações, FX por componente, diferenças de corretora, concorrência, identidade de clones, dados de mercado float, replay/caches, indicadores, migração e estado Git. `AppConfig.default_base_currency` já existe no código, pelo que a renomeação prevista no A5 não é tarefa pendente sem evidência de configuração legada.

**Estado de execução:** revisão e documentação apenas; sem implementação Portfolio, sem novos testes executados, sem alteração de schema ou migração. O relatório externo mencionou 161 testes e 61% de cobertura, **não reproduzidos nesta auditoria**. Permanecem por verificar os contratos na implementação e o comportamento real de extratos XTB futuros. A próxima fase técnica deve ser planeada em incrementos testáveis, sem declarar funcionalidade V0.3 já entregue.

## Nota de rastreabilidade da síntese antiga

A secção «Leitura rápida: estado vigente (2026-10-10)» mais acima diz que a tag ainda não existe e que `main` não recebeu o saneamento. **Estas afirmações deixaram de ser verdadeiras após a integração e publicação da V0.2.0**, e já não devem orientar agentes. Não se eliminam linhas históricas para preservar a cronologia; a síntese prevalecente é a datada de 2026-10-11 no fim deste documento.
