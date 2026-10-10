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
