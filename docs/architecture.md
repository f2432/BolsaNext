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
