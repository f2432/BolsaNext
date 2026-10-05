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
