# Arquitetura

## Objetivo

A nova aplicação deve evitar a concentração de responsabilidades existente na versão anterior, em particular a dependência excessiva da interface gráfica.

A arquitetura é organizada em quatro zonas principais. O esquema é conceptual: o Domain não depende da Infrastructure; a Application usa contratos/ports, implementados por adapters da Infrastructure:

```text
UI
↓
Application
↓
Domain
↓
Infrastructure
```

## UI

Responsável apenas por interação com o utilizador e apresentação.

Exemplos:

- janela principal;
- carteira;
- watchlist;
- análise de ativos;
- backtesting;
- investigação;
- IA.

A UI não deve aceder diretamente a `yfinance`, calcular PnL, treinar modelos diretamente, executar SQL ou implementar regras financeiras.

## Application

Coordena casos de uso.

Exemplos previstos:

- `MarketService`
- `PortfolioService`
- `WatchlistService`
- `AnalysisService`
- `BacktestService`
- `ResearchService`
- `AIService`

## Domain

Contém as regras e objetos centrais do projeto.

### Instruments

Representa ativos financeiros, incluindo ticker, nome, **bolsa (`exchange`)**, moeda e tipo de instrumento. A designação antiga `market` permanece apenas em registos históricos e na revisão inicial de migração.

### Portfolio

A unidade base é a transação.

```text
Transaction
↓
Position
↓
Portfolio
↓
Exposure / PnL
```

Uma posição deve ser calculada a partir das transações.

### Watchlist

Permite acompanhar ativos sem os considerar automaticamente candidatos a compra.

### Strategies

Primeiras estratégias previstas:

- SMA Crossover;
- RSI + MACD.

### Backtest

Responsável por sinais, execução simulada, custos, slippage, posição, curva de capital, trades, métricas e benchmark.

### Research

Regista tese, riscos, catalisadores, invalidação, cenários e data de revisão.

### AI

Área dedicada a datasets, features, modelos, validação temporal, calibração, avaliação, previsões, ensembles, explicabilidade e planeamento.

## Infrastructure

Implementa dependências externas.

### Database

Inicialmente SQLite através de SQLAlchemy.

### Market Data

Inicialmente `yfinance`. A arquitetura deve permitir substituir ou acrescentar outras fontes no futuro.

### Repositories

Implementam persistência para transações, instrumentos, watchlists, teses, previsões, execuções de modelos e backtests.

## Modelo de dados inicial

### Instrument

```text
id
ticker
name
market
currency
asset_type
```

### Portfolio

```text
id
name
base_currency
```

### Transaction

```text
id
portfolio_id
instrument_id
datetime
type
quantity
price
currency
commission
fx_rate
notes
```

### Watchlist

```text
id
name
```

### WatchlistItem

```text
watchlist_id
instrument_id
state
notes
```

### InvestmentThesis

```text
id
instrument_id
created_at
state
thesis
risks
catalysts
invalidation
review_date
```

### ModelRun

```text
id
model_name
model_version
features
train_period
validation_period
parameters
metrics
created_at
```

### Prediction

```text
id
model_run_id
instrument_id
timestamp
horizon
predicted_value
probability
actual_outcome
```

### BacktestRun

```text
id
strategy
parameters
start_date
end_date
cost_model
benchmark
metrics
created_at
```

## Regras de arquitetura

- lógica financeira fora da UI;
- dependências externas atrás de interfaces;
- alterações pequenas e testáveis;
- testes unitários para cálculos;
- testes de integração para persistência e dados;
- nenhuma dependência do projeto antigo;
- migração apenas de conceitos ou código previamente revisto.


### Persistência atualmente implementada

A primeira persistência real do projeto usa SQLAlchemy e SQLite para:

- `instruments`;
- `watchlists`;
- `watchlist_items`.

A Watchlist é reconstruída a partir da base de dados no arranque. Alterações de composição e estado são persistidas através de `SqlAlchemyWatchlistRepository`.

A posição de mercado atual não é guardada na Watchlist. Preços continuam a ser obtidos através do `MarketDataProvider`.


### Preferências locais da interface

Preferências puramente visuais, como larguras e estado dos cabeçalhos das tabelas, são guardadas através de `QSettings`.

Estas preferências:

- pertencem ao utilizador local;
- não fazem parte da base de dados financeira;
- não entram no Git;
- são separadas da persistência de domínio;
- podem ser reutilizadas por novas tabelas da aplicação.

A Watchlist e a tabela de Universos já usam esta abordagem.


### Política de erros de Market Data

Falhas previsíveis do fornecedor de dados são traduzidas para exceções próprias:

- `InstrumentNotFoundError`: o fornecedor respondeu, mas não reconheceu o ticker;
- `MarketDataUnavailableError`: o fornecedor não pôde ser consultado ou ocorreu uma falha de transporte;
- `MarketDataError`: base comum para erros previsíveis desta infraestrutura.

A UI não interpreta diretamente exceções internas de `yfinance`.

Na V0.2 não existem retries automáticos escondidos. Uma falha é apresentada ao utilizador e a repetição é explícita. Esta decisão evita pedidos repetidos inesperados e pode ser revista quando existirem várias fontes de dados.

Históricos sem dados são válidos e devolvem o schema OHLCV canónico vazio. Quando `Adj Close` não é fornecido, a coluna continua presente com valores em falta; `Close` não é usado silenciosamente como substituto.


## Governação do ciclo de estabilização V0.2

O ciclo atual não implementa Portfolio. O documento `docs/stabilization-v0.2.md` define a sequência e preserva integralmente o plano fonte.

Decisões arquiteturais que têm de ser tomadas neste ciclo antes da implementação correspondente:

- A6 completa: semântica de `Instrument.market`, eventual separação de conceitos e autoridade/proveniência dos metadados;
- A7.1: política mínima de backup antes de mover ou migrar a base;
- parte atual de A5: semântica da configuração `base_currency` e eventual renomeação para `default_base_currency`.

Decisões deliberadamente preservadas para a futura especificação da V0.3:

- âmbito funcional de Portfolio;
- ledger e regras contabilísticas;
- Decimal/Numeric e precisão financeira;
- convenção FX;
- autoridade de `Portfolio.base_currency`;
- importação/exportação/duplicados de transações;
- reconciliação com broker;
- política pessoal de investimento.

Estas decisões adiadas não devem ser inferidas nem implementadas durante o saneamento da V0.2.

### Regra de preservação arquitetural

Uma decisão arquitetural substituída não é apagada sem rasto. Deve ficar identificada como histórica/superseded, com a nova decisão e respetiva justificação.


## Metadados de instrumentos e autoridade das fontes

Decisão canónica D1 do ciclo de estabilização V0.2.

### Significado de market/exchange

O campo histórico `Instrument.market` é considerado semanticamente ambíguo porque foi usado para região, grupo de mercado e bolsa.

O conceito canónico passa a ser **exchange / listing venue**: a bolsa ou local de cotação do instrumento.

A implementação deverá evoluir de `market` para `exchange` quando a alteração de código/schema for executada. A UI deverá apresentar o conceito como **Bolsa**.

Região geográfica, país ou exposição regional não são sinónimos de exchange e, se vierem a ser necessários, serão atributos separados.

### Autoridade das fontes

A política de proveniência é:

- providers de universos, como Wikipedia, são autoridade para **composição do universo**;
- podem fornecer ticker e nome útil/provisório para apresentação;
- não são autoridade final para exchange, moeda ou tipo de ativo;
- Yahoo é a fonte principal dos metadados canónicos do instrumento na V0.2: nome quando disponível, exchange, moeda e asset type;
- informação de universos é provisória/fallback e não deve ser promovida silenciosamente a verdade canónica quando a fonte principal não a confirmou.

### Falha temporária da fonte principal

Uma falha temporária do Yahoo não deve impedir necessariamente a adição de um ticker vindo de um universo.

Nesse caso:

- preserva-se o ticker;
- pode preservar-se um nome provisório vindo do universo;
- exchange/moeda não confirmados ficam desconhecidos/em falta;
- não se inventam valores como `US`, `EURONEXT` ou moedas inferidas apenas para preencher campos.

Uma atualização posterior deve poder completar esses metadados.

### Atualização explícita de metadados

A ação `Atualizar dados` significa consultar novamente a fonte principal e atualizar os metadados canónicos, mesmo quando os campos já estejam preenchidos.

A otimização anterior que evitava consulta quando nome, market e currency estavam todos preenchidos fica superseded por esta política.

### Responsabilidade por precedência

A arbitragem entre fontes pertence à camada Application/serviço.

- a UI não decide qual fonte vence;
- o repository não decide qual fonte vence;
- o repository persiste um `Instrument` já considerado canónico pela Application.

Não é introduzido nesta fase um campo persistente `metadata_source`.

### Relação com subunidades monetárias

B3 deve obedecer a esta política. Convenções específicas de cotação de um fornecedor, como moedas/subunidades reportadas pelo Yahoo, devem ser normalizadas junto do adapter/provider apropriado antes de os dados serem expostos como valores canónicos ao resto da aplicação.


## Política de backup antes de movimentos e migrações

Decisão canónica D2 do ciclo de estabilização V0.2.

A base SQLite é dado persistente e não pode ser movida, substituída ou migrada sem existir primeiro uma cópia recuperável.

### Regras

- backup obrigatório antes de qualquer migração de schema;
- backup obrigatório antes de mudar a localização da base;
- se o backup falhar, a operação principal não começa;
- origem, destino e caminho do backup devem ser explícitos ao utilizador quando a operação alterar a base existente;
- backups não entram no Git;
- backups são imutáveis e timestamped, nunca sobrescritos;
- usar preferencialmente a SQLite Backup API para criar snapshot consistente;
- validar o backup com existência, tamanho não nulo, abertura SQLite e `PRAGMA quick_check`;
- validar também a base resultante depois de movimento/migração;
- em falha, preservar base original e backup e não promover uma base parcialmente migrada;
- restauro é explícito e nunca automático;
- ao restaurar, preservar também a base problemática antes de a substituir;
- não existe rotação automática de backups nesta fase.

Esta política protege especificamente B5 (localização dos dados) e B6 (migrações). O desenho de backup/export/import de dados de Portfolio permanece adiado para a futura especificação da V0.3.


## Moeda base por omissão

Decisão canónica D3 do ciclo de estabilização V0.2.

`AppConfig.base_currency` é semanticamente uma **moeda base por omissão**, não uma autoridade financeira global.

O nome preferido passa a ser `default_base_currency`.

Regras:

- serve apenas como valor inicial para funcionalidades futuras que precisem de escolher uma moeda base;
- alterar a configuração não pode alterar silenciosamente entidades persistidas;
- a futura `Portfolio.base_currency` será a autoridade da respetiva carteira, mas essa funcionalidade continua fora do ciclo atual;
- não são introduzidos agora cálculos financeiros ou conversão cambial.


## Ports e adapters da Application

Decisão e implementação B1 do ciclo de estabilização V0.2.

A direção canónica das dependências é:

```text
UI
 ↓
Application
 ├── services
 └── ports
 ↓
Domain

Infrastructure ──implementa──> Application ports
```

A Application não pode importar `bolsa.infrastructure`.

### Ports atuais

Os contratos vivem em `src/bolsa/app/ports/`:

- `market_data.py` — `MarketDataProvider`;
- `universe.py` — `UniverseProvider`;
- `repositories.py` — `WatchlistRepository`;
- `errors.py` — erros previsíveis que fazem parte do contrato externo conhecido pela Application.

Os services importam estes contratos exclusivamente através de `bolsa.app.ports`.

### Adapters atuais

A Infrastructure fornece as implementações:

- `YFinanceMarketDataProvider`;
- `WikipediaUniverseProvider`;
- `CachedUniverseProvider`;
- `SqlAlchemyWatchlistRepository`.

Os Protocols são estruturais: um adapter não precisa de herdar explicitamente do Protocol para o cumprir.

### Erros como parte do contrato

`MarketDataError`, `InstrumentNotFoundError` e `MarketDataUnavailableError` passam a viver canonicamente em `app/ports/errors.py`.

A razão é arquitetural: estes erros são conhecidos pela Application como parte do contrato com dados externos, mas não são regras de negócio do Domain nem devem obrigar a Application a depender de um adapter concreto da Infrastructure.

A taxonomia será expandida no B2 sem voltar a inverter dependências.

### Compatibilidade transitória

Os módulos históricos:

- `infrastructure/market_data/provider.py`;
- `infrastructure/market_data/universe_provider.py`;
- `infrastructure/market_data/errors.py`;

permanecem temporariamente como **reexports de compatibilidade**, mas deixam de ser a origem canónica das definições.

Código novo deve importar os contratos por `bolsa.app.ports`.

### Proteção automática da fronteira

Existe um teste arquitetural que percorre `src/bolsa/app/**/*.py` e falha se encontrar imports diretos de `bolsa.infrastructure`.

Assim, a regra deixa de depender apenas da documentação.


### Estado de validação B1

B1 concluído e validado em 2026-10-05:

- CI GitHub Actions: 40 testes passaram;
- validação local Windows: 40 testes passaram;
- aplicação iniciou corretamente após a refatoração;
- a fronteira `Application → Infrastructure` fica protegida por teste arquitetural.


## Política unificada de erros externos

Decisão e implementação B2 do ciclo de estabilização V0.2.

Esta secção expande e, onde necessário, substitui a política anterior limitada a Market Data, preservando-a como histórico da evolução.

### Hierarquia

```text
ExternalDataError
├── MarketDataError
│   ├── InstrumentNotFoundError
│   ├── MarketDataUnavailableError
│   ├── CurrentPriceUnavailableError
│   └── MarketDataFormatError
└── UniverseError
    ├── UnsupportedUniverseError
    ├── UniverseSourceUnavailableError
    └── UniverseFormatError
```

Universos e cotações são ambos dados externos, mas pertencem a famílias paralelas.

### Preço atual

O contrato canónico é:

```python
get_current_price(instrument) -> float
```

Em falha previsível, o provider levanta uma exceção tipada.

- ticker não reconhecido → `InstrumentNotFoundError`;
- fornecedor/rede indisponível → `MarketDataUnavailableError`;
- instrumento válido sem cotação utilizável → `CurrentPriceUnavailableError`;
- resposta estruturalmente inesperada → `MarketDataFormatError`.

`None` deixa de representar silenciosamente todas estas situações.

Histórico vazio continua deliberadamente válido e devolve o schema OHLCV canónico vazio.

### Universos

A Application recebe `UniverseLoadResult`, que transporta o `Universe` e a origem/frescura:

- `LIVE` — obtido da fonte;
- `FRESH_CACHE` — cache dentro do TTL normal;
- `STALE_CACHE` — cache expirada usada em modo degradado.

A fonte Wikipedia não deixa escapar exceções previsíveis de urllib/pandas:

- código não suportado → `UnsupportedUniverseError`;
- rede/timeout/HTTP → `UniverseSourceUnavailableError`;
- estrutura da página/tabela inválida → `UniverseFormatError`.

### Fallback stale

A cache normal mantém TTL de 24 horas.

Se a cache expirou e a fonte falha por indisponibilidade ou formato, pode ser usada cache com idade máxima de **7 dias**.

Esse fallback:

- é explícito;
- inclui timestamp da cache;
- inclui aviso do motivo;
- nunca se aplica a universo não suportado;
- não transforma dados antigos em dados aparentemente frescos.

Depois de 7 dias, a falha da fonte volta a ser apresentada e a cache não é utilizada.

### UI e serviços

A UI não interpreta exceções internas de providers.

A Watchlist trata falhas de preço por instrumento, preserva as restantes linhas e apresenta avisos com o motivo.

A UI de universos mostra se os dados vieram de cache fresca ou stale e, neste último caso, apresenta o aviso associado.

Testes dos caminhos de erro usam providers/fontes simulados; o CI não depende de Yahoo ou Wikipedia reais.


### Estado de validação B2

B2 concluído e validado em 2026-10-06:

- GitHub Actions na `dev`: 58 testes passaram;
- validação local confirmada pelo utilizador;
- a taxonomia de erros externos, o contrato de preço atual e o fallback stale dos universos ficam vigentes como política canónica.


## Convenções de cotação e subunidades monetárias

Decisão e implementação B3 do ciclo de estabilização V0.2.

### Separação de responsabilidades

O Domain conhece apenas a moeda canónica do instrumento.

Convenções específicas de cotação do fornecedor pertencem ao adapter correspondente. No adapter Yahoo, uma cotação em `GBp`, por exemplo, é convertida antes de o preço ser exposto ao resto da aplicação.

`Instrument.currency` não é usado para inferir a escala do preço.

### Convenções suportadas inicialmente

```text
GBp → GBP × 0.01
GBX → GBP × 0.01
ZAc → ZAR × 0.01
ILA → ILS × 0.01
USD/EUR/GBP/... canónico em três letras maiúsculas → × 1.0
```

A correspondência de subunidades é deliberadamente sensível à forma bruta recebida: `GBp` não é normalizado para `GBP` antes de identificar a convenção.

Uma moeda inesperada/malformada produz `MarketDataFormatError` em vez de assumir silenciosamente fator 1.

### Escala aplicada

O fator é aplicado a:

- preço atual;
- Open;
- High;
- Low;
- Close;
- Adj Close.

`Volume` não é alterado.

### Cache da sessão

`YFinanceMarketDataProvider` mantém por ticker uma convenção de cotação em memória, contendo:

- moeda bruta;
- moeda canónica;
- fator de preço.

Esta cache evita consultas repetidas durante a sessão e não é persistida em SQLite.

### Relação com universos

Por decisão D1, universos não são autoridade final para moeda/exchange. B3 não utiliza a moeda vinda da Wikipedia para escolher o fator de preços Yahoo.

A limpeza integral da proveniência no fluxo UniverseWidget → Watchlist fica para B8.2.


### Estado de validação B3

B3 concluído e validado em 2026-10-07:

- GitHub Actions na `dev`: 72 testes passaram;
- validação local confirmada pelo utilizador;
- a política de normalização de subunidades Yahoo fica vigente como comportamento canónico do adapter.


## Integridade e configuração SQLite

Decisão e implementação B4 do ciclo de estabilização V0.2.

### PRAGMAs obrigatórios

Cada nova ligação SQLite criada pelo engine recebe:

```text
PRAGMA foreign_keys = ON
PRAGMA busy_timeout = 5000
```

A configuração é aplicada no evento de ligação do SQLAlchemy, garantindo que não depende de uma única execução no arranque.

### Integridade referencial

As foreign keys declaradas nos modelos são consideradas efetivas apenas porque `foreign_keys=ON` é ativado e testado.

A suite verifica:

- foreign keys inválidas são rejeitadas com `IntegrityError`;
- depois da falha é feito rollback e não ficam alterações parciais;
- `ON DELETE CASCADE` remove `watchlist_items` quando a Watchlist é eliminada ao nível da base.

### Instrumentos órfãos

A existência de um `Instrument` não depende da sua presença numa Watchlist.

Remover um item da Watchlist:

- remove o `WatchlistItem`;
- preserva o `Instrument`.

Isto é comportamento intencional e protege reutilização futura do instrumento, incluindo futuras relações com Portfolio.

### Encerramento de recursos

Engines usados em testes de integração são libertados explicitamente com `engine.dispose()`.

A aplicação também liberta o engine em `main()` através de `try/finally`, incluindo quando o encerramento passa por exceção.

Esta decisão responde ao `ResourceWarning` SQLite detetado no baseline S0.

### Concorrência SQLite

`busy_timeout=5000` permite esperar até cinco segundos por um lock SQLite transitório antes de falhar.

Isto é independente da política de retries de Market Data e não introduz retries escondidos de rede.

### WAL

WAL foi avaliado no B4 e **não é ativado nesta fase**.

Razões:

- a concorrência atual não o exige;
- B5/B6 ainda vão alterar localização, backups e migrações;
- WAL acrescentaria ficheiros `-wal`/`-shm` e complexidade operacional sem benefício demonstrado.

Reavaliar WAL apenas se surgirem bloqueios reais ou necessidades de concorrência superiores.

### Evolução de schema

`Base.metadata.create_all()` continua temporariamente ativo no B4.

A sua substituição por migrações controladas pertence ao B6 e não é antecipada aqui.


### Estado de validação B4

B4 concluído e validado em 2026-10-08:

- GitHub Actions na `dev`: 75 testes passaram;
- validação local concluída pelo utilizador;
- o `ResourceWarning` SQLite identificado no S0 deixou de aparecer no CI B4;
- o bloqueio local do Windows App Control incidia sobre a extensão C opcional do SQLAlchemy e foi resolvido com instalação pure-Python da mesma versão, sem alterar o código da aplicação nem enfraquecer a política de segurança do Windows;
- a política SQLite deste bloco fica vigente como comportamento canónico.


## Localização estável dos dados

Decisão e implementação B5 do ciclo de estabilização V0.2.

### Diretoria de dados

Os dados persistentes deixam de depender do diretório de trabalho atual.

A localização normal é obtida por `platformdirs` com `appauthor=False` e sem criação implícita de diretórios.

Estrutura lógica:

```text
<user data dir>/BolsaNext/
├── bolsanext.sqlite3
├── cache/
│   └── universes/
└── backups/
```

Em Windows, a localização normal é a área Local AppData do utilizador. Em Linux/macOS são usados os locais convencionais do sistema.

### Override

`BOLSANEXT_DATA_DIR` permite definir explicitamente outra diretoria.

O override é deliberado e, quando usado, não ativa a proteção de migração legacy do repositório, porque a escolha de localização já foi explícita.

### Configuração sem efeitos laterais

`load_config()` apenas resolve configuração.

A criação física de diretórios pertence a:

```python
prepare_environment(config)
```

Assim, ler configuração não altera o disco.

### Moeda base por omissão

B5 materializa a decisão D3 e renomeia `AppConfig.base_currency` para `AppConfig.default_base_currency`.

Continua a ser apenas um valor por omissão. Não é autoridade financeira global e não introduz lógica de Portfolio.

### Proteção da base legacy

Se a localização nova ainda não contém base, mas existe `data/bolsanext.sqlite3` no repositório local, o arranque normal **não cria uma base vazia nova**.

Em vez disso, pára e exige migração explícita.

Isto evita a situação em que a aplicação aparenta ter perdido a Watchlist quando, na realidade, apenas mudou de ficheiro.

### Migração explícita

A ferramenta:

```text
python -m bolsa.tools.migrate_data_dir
```

mostra por omissão um dry-run com:

- origem;
- destino;
- caminho do backup;
- existência de cada um.

Nenhum dado é alterado sem `--execute`.

A execução efetiva:

1. valida a base de origem com `PRAGMA quick_check`;
2. cria backup imutável via SQLite Backup API;
3. valida o backup;
4. cria a nova base a partir do backup;
5. valida a nova base;
6. preserva sempre a base de origem.

Se o destino já existir, a operação pára e não sobrescreve nada.

### Cache

Cache de universos não é migrada. É dado derivado e pode ser recriada.

### Relação com B6

B5 trata apenas **localização física dos dados**.

Evolução de schema, baseline e revisões Alembic pertencem ao B6.


### Migração B5 executada no ambiente Windows

Em 2026-10-08 a migração real da base V0.2 foi executada e validada no ambiente Windows do utilizador.

Caminhos confirmados:

```text
Origem:
C:\Users\Portatil\Documents\GitHub\BolsaNext\data\bolsanext.sqlite3

Backup:
C:\Users\Portatil\AppData\Local\BolsaNext\backups\bolsanext_before_move_20261008_010523.sqlite3

Nova base ativa:
C:\Users\Portatil\AppData\Local\BolsaNext\bolsanext.sqlite3
```

A origem foi preservada. A nova base foi criada apenas depois do backup e da validação SQLite.

A validação funcional final da aplicação sobre a nova base permanece como último critério de fecho do B5.


### Estado de validação B5

B5 concluído e validado em 2026-10-08:

- GitHub Actions: 83 testes passaram;
- suite local Windows: 83 testes passaram;
- a migração real preservou origem, criou backup validado e criou a nova base na diretoria estável;
- a aplicação arrancou sobre a nova base;
- Watchlist e estados existentes foram preservados;
- uma alteração de estado persistiu depois de fechar e reabrir;
- a base antiga e o backup permanecem preservados.

A diretoria estável do utilizador passa a ser a origem operacional dos dados V0.2. A base legacy no repositório permanece apenas como cópia histórica de segurança até ao fecho do ciclo de estabilização.

## Migrações de schema com Alembic

Decisão e implementação B6 do ciclo de estabilização V0.2.

Alembic é a autoridade única para criação e evolução do schema persistente.

### Baseline V0.2

A revisão inicial é `0001_v02_baseline` e representa o schema V0.2 já existente, mantendo deliberadamente o campo `market`.

A alteração futura `market → exchange` não é incluída na baseline e deverá ser uma revisão posterior.

### Estados suportados no arranque

```text
DB inexistente/vazia
    → upgrade head

DB V0.2 válida sem alembic_version
    → validar baseline
    → backup
    → stamp baseline
    → upgrade head se existirem revisões posteriores

DB versionada em head
    → nenhuma alteração

DB versionada atrás de head
    → validar caminho
    → backup
    → upgrade head

DB incompatível / revisão desconhecida
    → parar
```

Não existe downgrade automático.

### Validação da base legacy

Antes de aceitar uma base não versionada como V0.2, são comparados:

- tabelas;
- colunas e tipos essenciais;
- NOT NULL relevantes;
- primary keys;
- unicidade de ticker, nome da Watchlist e par watchlist/instrument;
- foreign keys com `ON DELETE CASCADE`.

Só uma base compatível pode receber `stamp`.

### Backups

Qualquer escrita de adoção/migração sobre uma base com dados é precedida de snapshot SQLite validado.

Formato: `bolsanext_before_migration_<revision>_<timestamp>.sqlite3`.

A infraestrutura reutiliza `create_validated_database_backup()` de B5/D2.

### Falhas e runtime

Uma falha de `stamp` ou upgrade preserva a base e o backup existente. Não existe restauro automático.

`Base.metadata.create_all()` foi removido do mecanismo operacional. O arranque chama `ensure_database_schema()` antes de construir repositories.

Se o schema não puder ser validado ou migrado de forma conhecida, a aplicação termina com erro em vez de abrir sobre uma base ambígua.

### Testes

A suite inclui proteção contra reintrodução de `create_all()` no runtime e cenários de base nova/vazia, legacy V0.2, base corrente, incompatibilidade, revisão desconhecida, falha durante adoção e base versionada atrás de head com backup + upgrade orquestrado.


### Estado de validação B6

B6 concluído e validado em 2026-10-08: CI e suite local com 92 testes; adoção real da baseline `0001_v02_baseline` com backup prévio; dados preservados; segundo arranque em head sem backup redundante. Alembic fica como autoridade operacional do schema.


## Fonte única de versão

Decisão e implementação B7 do ciclo de estabilização V0.2.

A versão da aplicação tem uma única origem:

```text
src/bolsa/version.py
    __version__ = "0.2.0"
```

A partir desta origem derivam:

- `bolsa.__version__`;
- metadata do pacote Python através de setuptools dynamic metadata;
- User-Agent dos providers;
- rótulo de versão da interface.

A UI usa `version_label(stage)` para combinar a versão canónica com o nome funcional da fase, mantendo os dois conceitos separados.

Não devem ser introduzidas novas strings literais de versão em módulos funcionais.

A existência da versão `0.2.0` no código não autoriza a criação antecipada da tag Git `v0.2.0`. A tag continua reservada para B11, depois da integração final validada em `main`.


### Estado de validação B7

B7 concluído e validado em 2026-10-08:

- GitHub Actions: 97 testes passaram;
- validação local confirmou a versão canónica `0.2.0`;
- metadata instalado, User-Agent e UI usam a mesma fonte;
- a tag Git `v0.2.0` continua reservada para B11.


## Concorrência da Watchlist

Decisão e implementação B8.1.

A proteção contra concorrência existe em duas camadas complementares.

### Camada Application

`WatchlistService` possui um `threading.RLock` próprio.

O lock protege o agregado durante leituras e mutações relevantes, incluindo operações que consultam Market Data e a persistência subsequente.

Isto garante integridade mesmo quando o serviço é chamado fora da UI.

### Camada UI

`WatchlistOperationCoordinator` coordena uma única operação assíncrona da área Watchlist/Universos.

`MainWindow` cria uma instância e partilha-a entre:

- `WatchlistWidget`;
- `UniverseWidget`.

Enquanto o coordenador está busy, ficam desativados todos os controlos que podem iniciar outra operação de rede ou alterar a Watchlist, incluindo widgets embebidos nas células da tabela.

O estado busy é sempre libertado a partir de `QThread.finished`, incluindo em erro. Uma falha ao iniciar a thread liberta-o imediatamente.

A UI evita operações incompatíveis e bloqueios visíveis; o lock do serviço permanece a garantia final de integridade.

### Teste de concorrência

A suite executa duas threads Python contra o mesmo `WatchlistService`: uma atualização de metadados bloqueada deliberadamente no provider e uma remoção concorrente. A remoção espera pelo lock e o estado final é coerente, sem exceções.


### Estado de validação B8.1

B8.1 concluído e validado em 2026-10-08:

- GitHub Actions: 101 testes passaram;
- validação local confirmou o bloqueio global dos controlos mutáveis durante operações em curso;
- a coordenação foi confirmada entre Watchlist e Universos;
- os controlos foram libertados corretamente no fim das operações.

A política de duas camadas permanece vigente: coordenação visual na UI e `RLock` no serviço.


## Proveniência de metadados e UniverseWidget

Implementação B8.2 da decisão D1.

### Conceito canónico

O atributo canónico é `exchange`, entendido como bolsa/local de cotação.

`market` deixa de existir no domínio e no modelo operacional depois da migration `0002_market_to_exchange`.

A baseline histórica `0001_v02_baseline` conserva `market` por representar fielmente o schema V0.2 anterior; o validador de bases legacy também o mantém deliberadamente.

### Autoridade dos metadados

Providers de universos são autoridade apenas para composição.

Podem fornecer:

- ticker;
- nome provisório.

Não fornecem como dados canónicos:

- exchange;
- moeda;
- tipo de ativo.

Yahoo é a fonte principal destes metadados na V0.2.

### Fluxo Universe → Watchlist

```text
Universe provider
    ticker + nome provisório
        ↓
UniverseWidget mantém Instrument
        ↓
WatchlistService
        ↓
Yahoo instrument_details
        ↓
dados canónicos persistidos
```

Se Yahoo estiver temporariamente indisponível, a Application pode persistir um instrumento provisório com ticker/nome e exchange/moeda desconhecidos. Tipo = `OTHER`.

Se Yahoo declarar que o ticker não existe, a adição falha.

### Atualização explícita

`refresh_metadata()` consulta sempre a fonte principal para todos os instrumentos. O facto de um instrumento já ter campos preenchidos não impede a atualização.

Assim, dados históricos imprecisos podem ser corrigidos.

### Cache de universos

O formato de cache passa a versão 2 e guarda apenas composição/ticker/nome provisório.

Caches anteriores são ignoradas e reconstruídas.

### Migração

`0002_market_to_exchange` renomeia a coluna sem apagar valores.

A migration não tenta decidir semanticamente se valores antigos como `US` são válidos; essa correção é responsabilidade do refresh de metadados através da fonte principal.


### Estado de validação B8.2

B8.2 concluído e validado em 2026-10-09:

- GitHub Actions: 107 testes passaram;
- a base real foi atualizada para `0002_market_to_exchange` com backup prévio;
- a Watchlist passou a usar/apresentar **Bolsa**;
- Universos apresenta apenas Ticker/Nome;
- adição por universo usa Yahoo como fonte principal de metadados;
- `Atualizar dados` volta à fonte principal mesmo para campos já preenchidos;
- persistência confirmada depois de fechar e reabrir.

A decisão D1 fica assim implementada e validada no fluxo real.

### Cache efémera de preços (B8.3, implementação em validação)

O `WatchlistService` (Application) é dono de uma cache de sessão `dict[str, PriceSnapshot]` e mantém o respetivo acesso sob `RLock`. Um snapshot guarda preço `float` e instante UTC timezone-aware de obtenção. `WatchlistRow` expõe `price` e `price_updated_at` à UI. O Domain, a persistência e o provider de universos não conhecem esta cache. Falhas externas preservam o último snapshot e os avisos existentes. Preços não passam pelo repository nem pelo SQLite. A cache termina com a instância do serviço.

Registo de validação B8.3 (2026-10-09): o utilizador confirmou que os testes locais e funcionais correram como esperado. **B8.3 CONCLUÍDO E VALIDADO**. Próximo passo B8.4, ainda não implementado. A `main` e a tag `v0.2.0` mantêm-se intocadas.

### Validação sintática de tickers (B8.4, em validação)

`Instrument` normaliza e valida exclusivamente a sintaxe do símbolo, sem consulta de rede. Uma expressão regular aceita segmentos alfanuméricos com underscore, separados opcionalmente por ponto/hífen, prefixo `^` para índices e sufixo Yahoo `=` seguido de uma letra. Pelo menos um carácter alfanumérico é obrigatório. A existência e disponibilidade dos dados permanecem responsabilidade do provider de Market Data e dos erros tipados de Application. Não se introduz validação financeira específica de mercados no Domain.

Registo de validação B8.4 (2026-10-10): o utilizador confirmou que executou os testes e que o resultado foi correto. **B8.4 CONCLUÍDO E VALIDADO**. Mantêm-se os testes de regressão, a distinção entre sintaxe e existência real no provider e as decisões anteriores. Próximo sub-bloco: B8.5, ainda por implementar. `main` e tag `v0.2.0` não alteradas.

### Estado desconhecido na interface (B8.5)

O conjunto de `WatchlistState` do Domain não muda. A UI trata valores sem correspondência como apresentação temporária `Desconhecido` (`None`), sem corrigir automaticamente a persistência. A inicialização do `QComboBox` bloqueia sinais. O callback só envia ao serviço valores reconhecidos; a função pura `bolsa.ui.watchlist.state_selection.recognised_state()` viabiliza testes sem Qt. Nenhum estado `UNKNOWN` é adicionado ao domínio.

Registo de validação B8.5 e fecho B8 (2026-10-10): o utilizador confirmou que executou todos os testes locais e que tudo funcionou. **B8.5 CONCLUÍDO E VALIDADO** e **B8 (B8.1 a B8.5) CONCLUÍDO E VALIDADO**. Preservam-se integralmente os registos históricos e decisões anteriores. O bloco seguinte é B9 (CI, dependências e qualidade), ainda por executar. Não houve integração em `main` nem criação da tag `v0.2.0`.

### Matriz de compatibilidade do CI (B9.2, pendente de validação)

A suite automática preserva o runtime de referência Linux/Python 3.12 e acrescenta Windows/Python 3.14 com execução independente (`fail-fast: false`). São apenas ambientes de testes, sem alterar a arquitetura de aplicação ou impor alterações à plataforma de dados. O caso particular de Windows App Control do computador local não é uma característica exigida do runner de CI.

### Dependências runtime e opcionais (B9.3)

O conjunto mínimo declarado para executar V0.2 é PySide6, pandas, SQLAlchemy, alembic, yfinance, platformdirs e lxml. A análise de universos baseada em Wikipedia usa `pandas.read_html` e mantém lxml como dependência explícita. Bibliotecas previstas para análise/IA futura são organizadas no extra opcional `analysis` e não são importadas pelo fluxo principal da V0.2. A arquitetura e os modelos de dados não se alteram nesta sessão. Estado B9.3: implementação sujeita a confirmação dos testes Linux/Windows e execução local.

Validação B9.3 (2026-10-10): testes e aplicação confirmados pelo utilizador. **B9.3 CONCLUÍDO E VALIDADO**. Próximo bloco B9.4 (Ruff), ainda não implementado. `main` e a tag `v0.2.0` permanecem intactas.

### Escrita atómica da cache de universos (I1)

A cache local JSON v2 dos universos é escrita primeiro para um temporário no mesmo diretório e apenas substitui a versão anterior após fecho e sucesso da gravação, via `os.replace()`. Falhas anteriores à substituição conservam a cache válida existente; resíduos temporários são removidos em `finally`. Este mecanismo não altera TTL/fallback, não usa SQLite e não garante persistência física após corte de energia. I1 pendente de validação local e CI.

### Política vigente de instrumentos sem associação (I2, 2026-10-11)

**I2 CONCLUÍDO E VALIDADO POR DECISÃO EXPLÍCITA DO UTILIZADOR.** Um `InstrumentModel` sem `WatchlistItemModel` não é considerado erro de integridade nem deve ser apagado automaticamente. A remoção de um ticker da Watchlist elimina exclusivamente a associação correspondente em `watchlist_items`; a linha em `instruments` permanece disponível para reutilização. Esta separação evita a eliminação acidental de um instrumento que no futuro possa estar associado a transações, posições ou investigação. Não existe rotina de limpeza automática de órfãos. Qualquer proposta futura de eliminação definitiva terá de verificar todas as referências existentes, definir a semântica de retenção e obter decisão explícita antes da implementação. O teste `test_watchlist_repository_persists_removal` confirma a preservação. Sem alteração ao schema ou ao repository no I2.

## Âmbito da V0.3 — Portfolio (A1 validado, 2026-10-11)

**Decisão funcional aprovada pelo utilizador. Apenas especificação; sem implementação, migrações ou alteração à V0.2 publicada.** O A1 encerra o âmbito, não as fórmulas e contratos financeiros detalhados, que dependem de A2–A5, A7 e A8.

### Objetivo e âmbito

Portfolio pessoal simples para posições **long-only** em **ações e ETFs**, incluindo ações fracionadas, com várias carteiras, identificação própria e moeda base específica por carteira. Instrumentos são entidades reutilizáveis entre carteiras. Operações iniciais acordadas:

- **BUY** e **SELL**: compras e vendas reais, com quantidade positiva, preço, comissões, moeda, câmbio histórico, instante e notas; nunca permitir vendas acima da quantidade disponível.
- **DIVIDEND**: lançamento **manual** por carteira e instrumento, com valor **bruto**, **retenção na fonte**, **outros encargos**, **valor líquido recebido**, moeda, data e notas. Convenção de controlo: `líquido = bruto - retenção - encargos`. Não calcular automaticamente retenções/impostos nem obter dividendos automaticamente; não alterar a quantidade detida. O rendimento deve ser apresentado em separado do PnL de negociação, sem dupla contagem.
- **ADJUSTMENT**: ajuste **manual e auditável** de quantidade e/ou custo contabilístico, com motivo obrigatório, carteira, instrumento, data efetiva e rastreabilidade. Não lançar compras/vendas fictícias e não gerar PnL realizado automaticamente. As regras por causa de ajuste e efeitos matemáticos exatos ficam para A2.

O conjunto de tipos deve ser extensível, podendo acomodar futuramente `FEE`, `SPLIT`, `CASH_IN`, `CASH_OUT` e outros, **sem os implementar** nesta versão. O eventual detalhe técnico dos campos aplicáveis a cada tipo pertence ao desenho de domínio posterior, e não pressupõe quantidade/preço em DIVIDEND.

### Fonte de verdade e auditabilidade

O **ledger completo de transações e respetivo histórico** é a única fonte de verdade financeira. Posições, custo médio, PnL realizado/não realizado, dividendos e resultados agregados derivam de um recálculo reproduzível do histórico financeiramente válido, e nunca substituem o histórico por totais incrementais persistidos.

**Correção**: conservar a operação original identificada como substituída e criar uma nova versão válida associada à anterior. **Anulação**: invalidar logicamente a operação mantendo o registo e o rasto da decisão. Corrigir/anular são ações auditáveis sobre o histórico, **não tipos financeiros de transação**; operações substituídas/anuladas não contam nos cálculos, mas continuam disponíveis para auditoria. A estrutura de versionamento, a cadeia de substituições e a política exata de imutabilidade serão fixadas antes da implementação. Um ADJUSTMENT representa alteração económica real da posição e não serve para corrigir erros de introdução.

### Resultados e utilização

Por carteira/instrumento, consultar ledger, quantidade, custo acumulado, custo médio ponderado, cotação de mercado quando disponível, valorização, PnL realizado e não realizado, dividendos e resultado composto identificado por parcelas. A comissão de compra aumenta o custo e a de venda diminui o encaixe líquido, sujeitos às fórmulas A2. O custo médio é inicialmente o método de acompanhamento e de PnL realizado, **não o método fiscal obrigatório**; o ledger completo preserva a possibilidade de introduzir FIFO fiscal futuramente.

A valorização e os totais em moeda base **não devem ser apresentados como válidos sem os câmbios requeridos**, que serão definidos no A4. A persistência e recuperação serão feitas em SQLite/SQLAlchemy, observando migrações e backups anteriores à operação conforme política D2/A7.1. O formato canónico, importação atómica, duplicados e relatórios ficam para A7.

### Fora do âmbito

Sem short selling, margem, CFDs, opções, futuros, execução de ordens, ligação direta a brokers, impostos fiscais e lotes fiscais, automatização de dividendos ou corporate actions, juros, saldos de caixa ou depósitos/levantamentos. Reconciliação com broker e política pessoal de investimento continuam sujeitos à decisão A8; a exclusão de integração direta não impede projetar formatos canónicos próprios e reconciliação posterior.

### Decisões adiadas (não implícitas)

- **A2**: fórmulas de compras, reforços, vendas, encerramento e comissões; eventos de ajuste; datas execução/liquidação, fuso, desempate; mecanismos concretos de correção/anulação.
- **A3**: `Decimal`, precisão, escala, arredondamento e quantidades fracionadas.
- **A4**: direção e fontes de câmbio, taxa histórica versus atual e critérios para valorização em moeda base.
- **A5**: propriedade da moeda base após criação de Portfolio e transformação de `AppConfig.base_currency` em valor por defeito.
- **A7**: formato de exportação, importação atómica, idempotência/duplicados e relatório.
- **A8**: reconciliação com extratos XTB, tolerâncias e política pessoal de investimento. Não preencher limites financeiros do utilizador.

**Critério de aceitação da V0.3:** um Portfolio simples, matematicamente correto, persistente, recuperável, testado, capaz de representar compras/vendas reais sem mecanismos financeiros desnecessários.


## A2 — Regras contabilísticas (validado, 2026-10-11)

**A2 aprovado pelo utilizador; especificação apenas, sem implementação.** O ledger é a origem única da verdade: nunca substituir, agregar ou reescrever operações originais para guardar uma posição. A reconstrução do estado financeiro percorre, pela ordem aprovada, apenas as versões eficazes das operações. Cada correção/anulação conserva o histórico auditável; ajustes são eventos económicos, distintos da retificação de erros.

### Compras, vendas e custo médio móvel

Para BUY, quantidade `q > 0`, preço unitário `p` e comissão `f`, o custo de entrada é `q*p + f`. Na posição anterior de quantidade `Q` e custo acumulado `C`, após compra: `Q' = Q + q`, `C' = C + q*p + f`, `custo_médio' = C'/Q'`.

Para SELL, `0 < q <= Q`, `custo_atribuído = q*(C/Q)`, `encaixe_líquido = q*p - f` e `PnL_realizado = encaixe_líquido - custo_atribuído`. Remanescente: `Q' = Q-q` e `C' = C-custo_atribuído`; a venda parcial não altera o custo médio anterior. Na venda total, `Q'=0` e `C'=0` exatamente: qualquer entrada posterior reinicia o custo médio, sem eliminar o PnL histórico.

Exemplo exato, mesma moeda, sem câmbio: BUY 10 a 100 EUR com comissão 5 EUR => custo 1005 EUR e média 100,50; BUY 10 a 120 EUR com comissão 5 EUR => custo 2210 EUR, Q=20, média 110,50; SELL 8 a 130 EUR com comissão 4 EUR => encaixe líquido 1036 EUR, custo atribuído 884 EUR, **PnL realizado +152 EUR**, Q=12, C=1326 EUR, média 110,50 EUR.

Não permitir quantidade negativa, BUY/SELL com quantidade zero, nem short selling. Vendas superiores à quantidade disponível originam erro de domínio identificável e não alteram o ledger. Custo médio de acompanhamento e método inicial de PnL realizado não substituem o futuro apuramento fiscal, que poderá exigir FIFO. **As fórmulas acima pressupõem valores expressos numa moeda comum**; os passos para transações em outras moedas ficam para A4. Escalas e arredondamentos ficam para A3.

### Datas e ordenação

Guardar a data/hora de **execução** como referência de ordenação e, quando disponível, a data de **liquidação** opcional. Instantes conhecidos têm representação canónica UTC e apresentação em fuso local. Não inventar instantes/fusos quando a fonte fornece apenas uma data ou precisão parcial; preservar a precisão conhecida.

Ordenar primeiro pelo instante de execução disponível; para instantes coincidentes, aplicar a sequência real conhecida da corretora. Quando esta não existir, usar desempate estável e persistente, com alerta quando a ambiguidade puder alterar os cálculos. A ordem de inserção/importação não é automaticamente prova da ordem de execução. Nunca presumir BUY antes de SELL, nem depender da ordem arbitrária de resultados SQLite. O contrato exato para dados só com data será detalhado no desenho do domínio sem contrariar estes princípios.

### Dividendos e ajustes

DIVIDEND manual por carteira/instrumento: **líquido = bruto - retenção - outros encargos**, na moeda da operação, com todos os componentes individualizados e validados. O dividendo não modifica quantidade nem custo médio, e rendimento líquido não se confunde com PnL realizado nas vendas, nem pode ser somado duas vezes. Câmbio associado ao evento financeiro conforme A4. Exemplo: bruto 50 EUR, retenção 7,50 EUR e encargos 1 EUR => líquido 41,50 EUR.

ADJUSTMENT manual, justificado, tipificado, datado e auditável. Para split 2:1, quantidade duplica, custo acumulado mantém-se e custo médio unitário divide-se por dois, sem criar PnL realizado. Exemplo: 10 ações/C=1000 EUR => 20 ações/C=1000 EUR/média=50 EUR. Outros ajustes de quantidade e/ou custo **não partilham fórmula genérica**; só são aceites quando a categoria e a regra de cálculo estiverem explicitamente aprovadas e testadas.

### Correção, anulação e atomicidade

A correção não reescreve a operação original: liga-a a uma nova versão eficaz; a anulação retira a eficácia sem eliminar o original. Antes de confirmar correção, anulação ou ajuste que afete o histórico, reconstruir e validar **toda a sequência relevante**. Se alguma venda posterior exceder o saldo ou ocorrer outro invariante violado, rejeitar a operação inteira de forma **atómica**, manter inalterado o ledger previamente válido e emitir erro de domínio que identifica a operação e a causa. Exemplo: BUY 10, SELL 8; tentar corrigir a BUY para 5 é rejeitado, sem alterar o histórico eficaz.

Exemplo de recálculo, sem comissões: BUY 10 a 100, BUY 10 a 120, SELL 5 a 130 => custo médio 110 e PnL realizado 100; retificar a primeira BUY para 10 a 110 => custo médio 115 e PnL realizado 75, Q remanescente 15 e custo remanescente 1725. Recalcular, não ajustar PnL manualmente.

### Invariantes aprovados

- **INV-01**: ledger como única origem da verdade.
- **INV-02**: quantidade long-only nunca negativa.
- **INV-03**: BUY e SELL com quantidade estritamente positiva.
- **INV-04**: proibição de SELL acima do disponível no instante da operação.
- **INV-05**: após encerramento, quantidade e custo acumulado exatamente zero.
- **INV-06**: custo médio integralmente recalculado do histórico eficaz, sem depender de posição agregada persistida.
- **INV-07**: venda parcial não altera o custo médio unitário remanescente.
- **INV-08**: split simples altera quantidade e conserva custo total, sem PnL realizado.
- **INV-09**: dividendo não altera quantidade ou média nem se confunde com PnL de vendas.
- **INV-10**: versões anuladas/substituídas auditáveis mas sem efeito financeiro.
- **INV-11**: reconstrução determinística com mesmos eventos e mesma ordem.
- **INV-12**: totais que dependem de valores/câmbios indisponíveis não são apresentados como válidos (detalhar em A4).

**Fronteiras pendentes:** A3 fixa Decimal, precisão, persistência e arredondamento; A4 resolve câmbio histórico/atual e moeda base; A5 define autoridade da moeda da carteira; A7 importação/exportação; A8 reconciliação XTB. Nenhum valor implícito deve antecipar estas decisões.

## A3 — Tipos financeiros e precisão (validado, 2026-10-11)

**Especificação aprovada; sem implementação.** O domínio financeiro usa exclusivamente `decimal.Decimal` para quantidades, preços de execução, comissões, retenções, dividendos, montantes, taxas de câmbio, custos e PnL. Os dados de mercado estatísticos continuam em `float`/pandas/NumPy. A fronteira Market Data → Portfolio deve validar valores finitos e converter explicitamente, preferencialmente `Decimal(str(valor_float))` quando a fonte só disponibiliza float; esta conversão **não restitui** precisão já perdida. Entradas decimais textuais de utilizador e extratos são convertidas diretamente para Decimal, sem float intermédio. A exportação para float destina-se somente a visualizações/estatística, nunca à persistência financeira.

### Escalas e limites aprovados

- Quantidade, preço unitário, comissão, retenção, encargos e montantes monetários de entrada: no máximo **8 casas decimais**.
- Taxa de câmbio: no máximo **12 casas decimais**.
- Magnitude dos valores de entrada: no máximo **18 algarismos na parte inteira**, com validação explícita de sinal e intervalo por campo. BUY/SELL e câmbio estritamente positivos; comissões/retenções/encargos não negativos; valores NaN e infinitos proibidos.
- O custo médio é sempre **derivado**, não um valor financeiro de referência persistido nem limitado artificialmente a 8 casas; o custo acumulado e o ledger preservam os dados necessários ao recálculo.
- A escala máxima não exige preencher zeros até essa escala; excedê-la nunca desencadeia truncagem/arredondamento silenciosos. Um valor do broker confirmado deve ser conservado tal como recebido no registo de origem e eventuais discrepâncias identificadas.

### Persistência SQLite e fronteira de domínio

Persistir valores financeiros em **TEXT decimal canónico no SQLite**, com mapeamento explícito através de adaptador/tipo SQLAlchemy que devolve Decimal no domínio. Nunca converter os campos financeiros para SQLite REAL nem assumir exatidão decimal nativa de Numeric em SQLite; não usar casts/aritmética textual SQL como substitutos do motor financeiro. Garantir ida e volta com igualdade numérica exata; zeros finais podem ser normalizados na forma canónica, mas o texto original da corretora pode ser conservado separadamente para auditoria.

### Precisão e arredondamentos

Os cálculos internos utilizam contexto Decimal de **50 algarismos significativos**, com **ROUND_HALF_EVEN por defeito** nas quantizações explicitamente definidas, não depois de cada operação. Nunca reutilizar valores arredondados apenas para apresentação como entrada de cálculos. Divisões periódicas, custos médios derivados e resíduos requerem testes; no encerramento total da posição, o custo remanescente deve tornar-se exatamente zero segundo o A2. A apresentação respeita as casas usuais de cada moeda e o detalhe necessário para preços/câmbio, sem modificar dados guardados.

Montantes efetivamente confirmados pela XTB são preservados como factos de origem. Desvios entre estes e montantes matematicamente reconstruídos devem ser **sinalizados**, não substituídos silenciosamente. O efeito contabilístico dos desvios (incluindo eventuais conversões) fica reservado para **A4/A8**, sem revogar as fórmulas já aprovadas em A2.

**Gate A3:** regras funcionais validadas; não implica criação de campos, migrações, dependências ou código. A4 define a convenção FX, taxa histórica/atual e critérios de valorização; A5 trata da moeda base por carteira.


## A4 — Convenção FX (validado, 2026-10-11)

**Especificação funcional aprovada pelo utilizador, sem implementação.** Para converter da moeda original da operação/cotação para a moeda base da carteira, `fx_rate` significa sempre **número de unidades da moeda base por uma unidade da moeda original**: `valor_base = valor_original * fx_rate`. Exemplo: 1000 USD, carteira EUR, `fx_rate = 0.86 EUR/USD` => 860 EUR. Com moedas iguais a taxa é exatamente `Decimal("1")`; não se pede cotação remota.

Cada transação financeira guarda o **câmbio histórico efetivo que lhe foi atribuído**, imutável para fins de reconstrução. O câmbio atual é distinto, tem data/hora, proveniência e validade próprias, e serve para valorização corrente; nunca substitui o histórico. Sempre que a XTB forneça câmbio e montantes efetivos, conservam-se esses factos e compara-se com a taxa de referência sem substituir valores ou presumir que as diferenças são comissões, spreads ou erros. A política de reconciliação contabilística destas discrepâncias continua reservada para A8.

### Contrato de fornecimento de taxas

Definir futuramente um **port `FxRateProvider`**, com implementação inicial por infraestrutura yfinance/Market Data existente, mas sem dependência do Yahoo no domínio financeiro. Cada resposta normalizada identifica moeda original, moeda base, taxa positiva finita, instante/precisão temporal, proveniência, e estado de disponibilidade/validade. Símbolos como `EURUSD=X` podem representar USD por EUR, a direção inversa da conversão USD → EUR necessária na carteira EUR: o adaptador **inverte explicitamente** `1 / cotacao` com Decimal, validando e testando o sentido. O domínio recebe apenas a convenção normalizada; nunca infere a direção do ticker. Se a taxa de câmbio for zero, negativa, não finita ou indisponível, falha a conversão (exceto identidade monetária).

### Valorização atual

A valorização atual em moeda base integra a V0.3 quando existem todos os dados necessários: `valor_mercado_base = quantidade * cotacao_atual_moeda_instrumento * FX_atual(moeda_instrumento→moeda_base)`. O PnL não realizado na moeda base compara esta estimativa com o **custo remanescente histórico na moeda base**, nos termos dos cálculos A2/A3; a cotação atual não altera custo nem FX históricos. Exemplo de uma posição: 1 ação comprada a 100 USD com FX 0,90 EUR/USD custou 90 EUR; cotação atual 110 USD com FX 0,85 EUR/USD => 93,50 EUR, PnL não realizado +3,50 EUR sem taxas/comissões. Ganho de 10% em USD não equivale a ganho de 10% em EUR. A decomposição matemática do efeito-preço e efeito-câmbio exige regra adicional testada se vier a ser apresentada.

### Atualidade e indisponibilidade

Usar a última cotação da sessão de negociação válida conhecida para cada mercado/instrumento e a última sessão cambial pertinente; não declarar uma taxa desatualizada apenas devido ao fecho em fins de semana/feriados. Se faltar um calendário fiável, usar fallback **configurável de 72 horas corridas**, com sinalização explícita de dados eventualmente obsoletos. Mostrar data, fonte e antiguidade; uma cotação aceite não é necessariamente tempo real. Dados antigos podem ser apresentados como referência histórica, mas não como valorização atual válida. Esta política será aplicada a preço e FX.

Se faltar preço atual, FX necessário ou outro dado indispensável, mostrar a posição afetada como indisponível e, quando possível, **subtotal conhecido claramente identificado**; nunca apresentar subtotal como total consolidado, nem PnL consolidado como completo. Não imputar taxas artificiais nem usar `1` para moedas diferentes. Erros no provider não modificam valores históricos persistidos. A valorização de mercado é estimativa, não montante garantido de venda.

### Decisões relacionadas

A5: autoridade de `Portfolio.base_currency`, com `AppConfig.default_base_currency` apenas como predefinição de criação; alteração de moeda numa carteira existente exige operação explícita e controlada, jamais implícita (decisões iniciais A5 já confirmadas, restantes efeitos por decidir). A7: import/export e metadados de origem. A8: divergências com XTB e reconciliação; sem classificação presumida. O A4 não adiciona código, migrações nem campos.

## A5 — Autoridade e imutabilidade da moeda base (validado, 2026-10-11)

**Especificação funcional aprovada, sem implementação.** A propriedade `Portfolio.base_currency` é a **única autoridade** sobre a moeda base de uma carteira persistida. A configuração global `AppConfig.default_base_currency` serve **exclusivamente para preencher o valor inicial no formulário de criação**; o utilizador pode escolher outra moeda antes de guardar. Uma mudança posterior da predefinição global nunca modifica carteiras existentes nem reavalia os seus custos/resultados.

A V0.3 permite coexistirem carteiras com moedas base diferentes. Os códigos de moeda devem ser normalizados e validados segundo **ISO 4217**, com catálogo extensível e controlo de moedas efetivamente suportadas. Um código reconhecido não garante que o fornecedor FX tenha cotação para esse par; nessa situação aplicam-se os estados de indisponibilidade do A4, sem totais inválidos.

**Imutabilidade:** após a criação, a moeda base da carteira não é editável na V0.3, mesmo que não haja operações. UI, domínio e repositórios devem impedir a alteração acidental; a autoridade não pode depender só de um campo bloqueado na interface. Uma eventual mudança de moeda requer funcionalidade **futura, explícita, controlada e auditável**, com backup e recálculo/reconciliação do histórico; não é implementada na V0.3. A moeda de cada transação mantém o significado e os câmbios históricos imutáveis do A4. Ao abrir uma carteira, utilizar sempre a moeda persistida, nunca reler a predefinição para a substituir.

### Compatibilidade com a configuração V0.2

Renomear futuramente `AppConfig.base_currency` para `AppConfig.default_base_currency`, preservando o valor anterior quando existir e for válido. Na ausência de valor anterior, usar **EUR** como predefinição. Configuração anterior inválida: erro identificado, **sem substituir silenciosamente por EUR**. Não manter em paralelo duas origens de verdade, não criar nem alterar carteiras ao migrar esta configuração. O mecanismo concreto de compatibilidade depende da inspeção da implementação existente antes de escrever código.

### Critérios de aceitação

Criar carteiras com moedas distintas; alteração global só afeta novas criações; persistência e recuperação conservam a moeda; tentativa de edição de carteira existente falha sem mutação; validação de ISO 4217 e moeda suportada; migração de configuração antiga válida conserva o valor; configuração antiga inválida não é silenciosamente ignorada; câmbio para posições respeita a moeda base persistida.

**Estado:** A5 validado como especificação. A7 (import/export/backup e duplicados) e A8 (reconciliação) continuam sujeitos a decisão. Sem alteração de código, esquema SQLite ou dados nesta sessão.

## A7 — Formato canónico e importação (validado, 2026-10-11)

**Especificação funcional aprovada pelo utilizador; sem implementação.** Mantém-se a política de backup prévio D2/A7.1, validada na estabilização V0.2, antes de operações destrutivas/migrações. Um backup completo SQLite e uma exportação de carteira são operações distintas: a exportação não substitui necessariamente o backup integral da aplicação.

### Exportação e identidade

O formato canónico de portabilidade de Portfolio será **JSON estruturado e versionado**, sem dependência do formato da XTB ou de outras corretoras. Deve permitir reconstruir integralmente a carteira, incluindo identidade/moeda base, instrumentos, ledger completo (BUY, SELL, DIVIDEND, ADJUSTMENT), correções, anulações, relações de auditoria, instantes/ordem de execução, câmbios históricos, proveniência e identificadores externos. Valores financeiros `Decimal` são serializados como **strings decimais exatas**; não passar por float. Identificadores técnicos SQLite não são identidades portáveis. Validar `format_version`, referências e integridade do histórico antes de importar. A estrutura JSON concreta e a compatibilidade entre versões serão desenhadas e testadas antes da implementação.

Cada operação terá um **UUID canónico persistente** (`transaction_uid`) e, quando fornecida, identidade externa composta e contextualizada (origem, conta e `external_id`). UUIDs e ligações entre versões substituídas/anuladas sobrevivem a exportação/restauro. Transações economicamente idênticas podem ser legítimas e distintas: **fingerprints dos valores financeiros não provam duplicação** e apenas apoiam avisos. Coincidência de identidade com divergência de conteúdo é **conflito**, nunca autorização para substituição silenciosa. A identidade das operações é interpretada no âmbito correto de cada carteira, incluindo cópias independentes.

### Importação e transação atómica

A importação é obrigatoriamente **duas fases**: (1) validação integral e pré-visualização, sem mutações; (2) confirmação pelo utilizador e aplicação dentro de **uma única transação SQLite**, com reconstrução e verificação de todas as invariantes A1–A5 antes do commit. Erro, conflito não resolvido ou ledger inválido => **rollback total**, sem inserções parciais. Duplicados **comprovados** são ignorados e reportados, sem provocar inserções; conflitos são rejeitados, não resolvidos por sobreescrita.

O relatório de pré-visualização e o relatório final distinguem **inseridas, ignoradas por duplicação comprovada, conflitos, rejeitadas com motivo e estado final** (concluída/sem alterações/rejeitada com rollback). Se ocorrer rollback, a contagem de inserções efetivamente confirmadas é zero. Uma segunda importação do mesmo ficheiro não duplica operações: **idempotência**. Informar casos em que duas transações com todos os valores iguais são legítimas e não devem ser colapsadas.

### Restauro e cópias independentes

- **Restauro numa carteira nova:** reconstruir integralmente ledger e auditoria. Se já existir UUID da carteira, resolver explicitamente a identidade antes da confirmação; nomes repetidos não provam mesma identidade.
- **Importação complementar numa carteira existente:** exigir confirmação da carteira de destino, compatibilidade da moeda base imutável A5 e identificadores, sem eliminar ou reescrever operações existentes.
- **Cópia independente:** atribuir **novo UUID à carteira**, registar a referência à origem e preservar identidade/proveniência histórica das operações no contexto da cópia. As cópias evoluem independentemente, nunca inserem movimentos adicionais na carteira original nem confundem duplicação entre carteiras.
- **Substituição destrutiva integral de uma carteira existente:** explicitamente **excluída da V0.3**; qualquer recuperação integral da aplicação segue procedimento separado de backup e restauro controlado.

### Validação, segurança e compatibilidade

O JSON pode conter informação financeira pessoal: não exportar credenciais, tokens ou palavras-passe. Rejeitar conteúdo executável, formatos/versões não suportados, tamanhos incompatíveis, campos inconsistentes, relações de auditoria inválidas ou referências pendentes; nunca executar conteúdo importado. A importação não pode criar short selling, alterar moedas base persistidas nem violar os invariantes A2. A reconciliação com broker XTB e adaptadores de formatos externos ficam para decisões de A8 ou versões subsequentes, sem desvirtuar este formato canónico.

**A7 CONCLUÍDO E VALIDADO como especificação.** Não foram criadas tabelas, migrações, testes nem funcionalidades de importação nesta fase.


## A8 — Reconciliação interna e política de investimento (validado funcionalmente, 2026-10-11)

**Âmbito aprovado para V0.3; ainda sem implementação.**

### Integridade e reconciliação

A V0.3 valida internamente a consistência do ledger como origem de verdade: operações eficazes, posições, custos, dividendos, câmbios históricos e resultados reconstruídos segundo A1–A5; produz relatórios internos de discrepâncias com identificação e motivo, sem alterar automaticamente os lançamentos. Distinguir inconsistência efetiva de dados indisponíveis e não corrigir silenciosamente. Manter os identificadores de origem, conta e operação externa, câmbio aplicado e montantes originais da corretora para uma futura comparação. **Importar extratos reais da XTB e efetuar reconciliação automática com os movimentos/posições da corretora fica fora da V0.3**, para versão posterior. Divergências entre cálculo teórico e valores efetivos XTB não são automaticamente classificadas como comissão, spread ou erro.

### Política de investimento por carteira

Cada Portfolio pode ter **política opcional e configurável**, sem valores, percentagens ou metas impostos pela aplicação. As políticas são **versionadas**, com apenas uma versão ativa em cada momento, preservando versões anteriores e datas de vigência/alteração. As análises e alertas atuais utilizam a versão ativa; versões anteriores servem para rastreabilidade. Não é obrigatório persistir histórico de cada alerta calculado: avaliar sob pedido, de acordo com os dados válidos então disponíveis.

Indicadores iniciais: (1) concentração por instrumento; (2) exposição por setor; (3) exposição por moeda; (4) ganhos, perdas e PnL realizado/não realizado com nomenclatura explícita; (5) desvios relativamente a objetivos/limites configurados. Exibir indicadores descritivos mesmo sem política; **não assinalar violação de limites inexistentes**. Metadados setoriais ausentes são classificados como **não determinado**, não inferidos.

Concentração e exposição usam valores atuais na moeda base da carteira, obtidos apenas com cotações e FX compatíveis com A4. Se o total necessário não estiver integralmente disponível, os indicadores que exigem denominador global são **não avaliáveis**, podendo apenas mostrar subtotais claramente identificados; **dados desconhecidos nunca significam conformidade**. Estado de cada alerta: dentro do limite (avaliável), limite ultrapassado (avaliável), não avaliável (dados insuficientes). Objetivos de rentabilidade podem ser registados, mas não calcular/apresentar rentabilidade anualizada ou comparação temporal como se metodologicamente definida antes da aprovação de fórmula, período e tratamento de fluxos relevantes.

Os avisos da política são **informativos**, não bloqueiam BUY/SELL legítimas; continuam obrigatórias as invariantes de integridade do ledger, como impedir vendas em excesso. A V0.3 **não dá recomendações automáticas de compra/venda**, não transmite ordens à XTB nem executa operações. O cálculo dos alertas é feito quando necessário; a persistência das versões da política é obrigatória, ao contrário do histórico de alertas.

**A8 aprovado como especificação funcional**, não como código, modelo físico ou decisão sobre métricas futuras não especificadas. Segue-se, apenas após autorização separada do utilizador, auditoria global A1–A8 das especificações perante a arquitetura/código existentes.


## Auditoria pré-implementação V0.3 — resolução técnica AUD-001 a AUD-012 (2026-10-11)

Esta secção é um **aditamento normativo** às especificações A1–A8, após revisão independente e autorização do utilizador. Em caso de conflito técnico com descrições anteriores, prevalece este aditamento **apenas nos assuntos explicitamente aqui resolvidos**. Não representa implementação nem execução de testes.

### AUD-001 — Identidade, versões e anulações do ledger (decisão)

Separar **identidade económica** `transaction_uid` (UUID estável no âmbito da carteira) de **identidade de versão** `transaction_version_uid` (UUID único por registo versionado). Cada versão contém número de versão monotónico, referência à versão anterior (exceto primeira), tipo económico e valores completos, data/hora de execução e respetiva precisão/fuso conhecidos, instante de registo/alteração, motivo obrigatório de correção/anulação, proveniência e autoria local disponível. Os campos financeiros de uma versão confirmada são imutáveis. Correção acrescenta versão completa sucessora; anulação acrescenta **evento auditável terminal sem impacto financeiro**, sem apagar versões. Estado efetivo é **derivado da cadeia**: no máximo uma versão eficaz por `transaction_uid`, ou nenhuma se anulada; não depender de flags contraditórias como únicas fontes de verdade. Nunca contar várias versões como diferentes BUY/SELL.

Impor unicidade `(portfolio_uid, transaction_uid, version_number)` e unicidade global de `transaction_version_uid`; impedir ramificações, ciclos, sucessores duplicados e versões com carteira diferente, através de restrições e validação de domínio. Uma correção/anulação é anexada atomicamente sob controlo de concorrência; rejeitar pedidos que partam de versão entretanto substituída (**expected head/version**). Não permitir reativar automaticamente operação anulada na V0.3; reintrodução requer nova operação económica auditavelmente relacionada, nunca mutação retroativa. Exportação A7 guarda a cadeia e estado derivados.

Toda a sequência efetiva afetada é reproduzida após correção/anulação antes de commit; se qualquer venda posterior exceder a quantidade disponível, rejeitar integralmente o pedido. Exemplo: BUY10, SELL8, correção do BUY para 5 => rejeição atómica. Recalcular desde primeiro evento afetado e conservar ordem determinística com chave persistente para empates temporais; a data de correção **não substitui** a data económica da operação corrigida. Uma cadeia de versões não pode alterar o passado sem revalidar consequências futuras.

### AUD-002 e AUD-005 — Origem, moedas e montantes da corretora (decisão conservadora)

Separar **factos originais** (valores efetivamente debitados/creditados, moedas, taxas aplicadas, referência externa, comissões/taxas discriminadas, se disponíveis) de **valores derivados** (cálculo pela fórmula, taxa de referência e valorização de mercado). Montantes e câmbios observados não devem ser substituídos por preços yfinance ou presumidos encargos. Cada componente monetária (preço de execução e seu montante, comissão, retenção, outros encargos, dividendo) transporta moeda própria e, quando exige conversão, taxa **histórica explícita** para a moeda base; não aplicar o FX de uma componente a outra sem evidência da mesma taxa.

Para operações manuais, custo/proveitos contabilísticos derivam de componentes normalizadas para moeda base segundo A2/A4 e taxas históricas explicitadas. Se houver **montante líquido efetivo fornecido pela corretora** e divergente do derivado, conservar o observado, calcular a diferença e marcar operação como **pendente de reconciliação**, sem incorporá-la automaticamente como comissão, spread, ajuste ou PnL. Não apresentar custo/PnL dessa operação como definitivamente conciliado enquanto a diferença material não for resolvida. Resolução requer lançamento/componentização explícita e rastreável ou aceitação motivada de tolerância definida, mantendo os valores originais imutáveis; não inventar entradas financeiras. A contabilização de diferenças não discriminadas **não é automatizada na V0.3**. Valores necessários de moedas/FX ausentes => operação não confirmável quando impede o ledger determinístico; sem fallback fictício a 1.

Dividendos mantêm bruto, retenção, outros encargos e líquido na moeda de cada parcela, com conversão histórica individual quando necessária. Rejeitar dupla conversão. Manter distinção entre moeda de cotação do instrumento, execução, liquidação e moeda base. Esta decisão é uma política prudencial de sinalização, não uma alegação de que os montantes da XTB seguem sempre a mesma semântica; especificar no adaptador futuro.

### AUD-003 — Concorrência e atomicidade financeira

O `WatchlistOperationCoordinator` da V0.2 **não** constitui bloqueio de escrita de Portfolio. Serializar mutações do ledger da mesma carteira através de serviço de aplicação/repositório com transação SQLite e verificação **optimista de revisão** (`portfolio_ledger_revision`) ou exclusão mútua equivalente verificável. UI pode avisar sobre ocupação, mas não é a barreira de integridade. Análises/leitura de mercado não obtêm permissão para alterar o ledger; cotações concorrentes não mudam transações históricas. A pré-visualização de importação A7 contém revisão observada; **revalidar revisão, duplicados, relações e invariantes dentro da transação imediatamente antes do commit**. Se a revisão mudou, abortar e exigir nova pré-visualização; nunca confirmar plano obsoleto. Não partilhar uma sessão SQLAlchemy entre threads. Testar duas compras/vendas/correções/importações concorrentes sobre a mesma carteira e recuperação de falhas.

### AUD-004 — Cópias independentes e idempotência

A identidade de uma operação económica usada na deduplicação é **`(portfolio_uid, transaction_uid)`**, não apenas o UUID isolado quando há cópias independentes. Um clone recebe novo `portfolio_uid`, referencia `origin_portfolio_uid`, conserva `transaction_uid`, `transaction_version_uid` e proveniência como IDs históricos **no âmbito da cópia**, sem escrever na original. IDs técnicos de linhas SQLite podem diferir. Identificador externo composto `(source, account_ref, external_id)` identifica uma execução dentro do âmbito da fonte/conta, sendo associado ao contexto da carteira e recusando colisões contraditórias. Não deduplicar exclusivamente por quantidade, preço e instante. Diferenciar: (a) restauro da mesma carteira, (b) importação complementar, (c) clone deliberado; exigir escolha explícita e pré-visualização A7.

### AUD-006 — Configuração existente

Inspeção de `src/bolsa/config.py` na `dev` confirma **`AppConfig.default_base_currency: str = "EUR"` já existente**. Logo, a renomeação `base_currency` → `default_base_currency` nos textos A5 **não é trabalho pendente da implementação atual**. Antes de qualquer migração de instalações legadas, verificar empiricamente se existe configuração persistida com chave antiga; só construir compatibilidade se essa origem existir. Não criar migração fictícia, não alterar carteiras, manter autoridade em `Portfolio.base_currency`.

### AUD-008 — Replay, desempenho e caches

Ledger eficaz permanece verdade. Permitir snapshots/posições derivados **apenas como caches invalidadas por revisão e reconstituíveis**; nunca tratá-los como autoridade ou ignorar evento anterior. Criar testes de equivalência entre replay integral e replay a partir de snapshot válido, e de invalidação após correções retroativas. Medir tempo/memória em históricos longos (incluindo 10 000 eventos) e manter a interface responsiva, com processamento fora do ciclo UI sem violar limites de sessão SQLAlchemy. Não impor já um SLA numérico não medido.

### AUD-009 — Precisão na fronteira de Market Data

`src/bolsa/infrastructure/market_data/yfinance_provider.py` utiliza `float` para fatores de subunidades, e o port atual retorna `float`. Isso é compatível com preços de mercado aproximados na V0.2, **não** com factos financeiros de execução exata. Converter de forma explícita e validada na fronteira A3, sem alegar precisão recuperada; considerar refatorar o adaptador para fator decimal antes de cálculos de Portfolio caso testes revelem discrepâncias relevantes. Nunca enviar valores de execução originais XTB por esta via.

### AUD-010 — Indicadores e metodologia

Os indicadores de concentração só são calculáveis com **denominador integral disponível**. Peso por instrumento = valor de mercado do instrumento / valor de mercado total positivo e completo; sem denominador positivo, marcar não avaliável. Exposição por setor deve distinguir instrumento desconhecido e ETFs multissetoriais, **não presumir automaticamente a exposição subjacente de um ETF**. Exposição por moeda indica claramente se significa **moeda de cotação** (implementável inicialmente) ou risco económico cambial subjacente (não inferível diretamente de ETF multinacional). Sem rótulo explícito, não apresentar como risco cambial económico total. Objetivos anualizados continuam sem cálculo até metodologia aprovada. PnL e rendibilidade são conceitos distintos; evitar percentagens de retorno para portefólios com fluxos sem método definido.

### AUD-011 — Persistência, migração e backup

O projeto tem revisões Alembic `0001_v02_baseline` e `0002_market_to_exchange`. Antes de implementar A1–A8, definir revisão seguinte de schema Portfolio (provável `0003`, sujeita a inspeção da sequência corrente), restrições de integridade, tipos DECIMAL TEXT, índices por carteira/ordem/referências, tratamento de sessões e backup pré-migração D2. Não executar migração de produção sem prova de upgrade em base de teste com cópia de dados V0.2 e validação pós-upgrade. Documentar estratégia explícita de downgrade ou de **restauro por backup** quando downgrade sem perda for impossível; nunca prometer reversibilidade de uma migração destrutiva. Portfolio inicialmente novo, sem migração de posições legadas presumida.

### AUD-007 e AUD-012 — Estado canónico e higiene de Git

Uma secção antiga de `docs/status.md` afirma incorretamente que `main` não foi integrada e `v0.2.0` não existe. Registar adiante o estado real como **prevalecente** e marcar a síntese antiga como histórica, sem apagar rastreabilidade. Integração squash explica `dev` estar à frente e um commit atrás de `main`; isso não implica, isoladamente, desvio de conteúdo. Para desenvolvimento futuro, preferir commits por unidade de trabalho com resumo claro; não reescrever o histórico de 328 commits para melhorar a aparência de Git.

**Fecho da auditoria documental:** as decisões acima resolvem as ambiguidades de contrato relevantes, mas **não substituem verificação de implementação**, testes concorrentes, migração em base descartável, benchmark ou validação da semântica real de extratos da corretora. Iniciar código só depois de plano de incrementos com testes por invariante.
