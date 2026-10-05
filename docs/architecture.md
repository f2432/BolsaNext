# Arquitetura

## Objetivo

A nova aplicação deve evitar a concentração de responsabilidades existente na versão anterior, em particular a dependência excessiva da interface gráfica.

A arquitetura é organizada em quatro zonas principais:

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

Representa ativos financeiros, incluindo ticker, nome, mercado, moeda e tipo de instrumento.

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
