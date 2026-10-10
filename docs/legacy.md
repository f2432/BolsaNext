# Projeto anterior — inventário

Este inventário é exclusivamente **histórico**: tecnologias e funcionalidades abaixo pertencem ao projeto anterior `Bolsa`, não à execução atual do BolsaNext V0.2.

## Repositório

Projeto anterior: `f2432/Bolsa`.

O repositório anterior permanece como referência histórica e não deve ser usado como base Git da nova implementação.

## Tecnologias

- Python
- PyQt5
- pandas
- NumPy
- yfinance
- matplotlib
- scikit-learn
- PyYAML

## Funcionalidades existentes

### Dados

Histórico OHLCV, preço atual, cache e universos S&P 500, NASDAQ 100, PSI20, Euronext 100, EuroStoxx 50, NYSE e listas personalizadas.

### Indicadores

SMA, EMA, RSI, MACD, Bollinger Bands, ADX, CCI, ATR, Stochastic, OBV, MFI, médias de volume, Bullish Engulfing e Bearish Engulfing.

### Estratégias

- SMA Crossover;
- RSI + MACD.

### Backtesting

Posição única, curva de capital, trades, retorno, drawdown, Sharpe e win rate.

### Portfolio

Posições guardadas em CSV, quantidade, preço de compra, data, preço atual, valor e PnL.

### Machine Learning

- Logistic Regression;
- Random Forest;
- MLP;
- Linear Regression;
- classificação binária e multiclasse;
- previsão a vários horizontes;
- feature importance;
- cross-validation;
- TimeSeriesSplit opcional;
- deteção básica de overfitting;
- gravação de previsões.

### Explore

Por ativo, a implementação treinava Logistic Regression, Random Forest e MLP a 1 e 3 dias, produzindo probabilidades, previsão de preço, sugestões, features, consenso e Top 25.

### Análises adicionais

- estatística;
- ACF/PACF;
- feature importance;
- análise de backtest;
- análise de trades;
- risco;
- PnL attribution;
- factor attribution;
- otimização SMA;
- otimização stop-loss/take-profit;
- planeamento IA experimental.

## Problemas identificados

### Arquitetura

`gui/main_window.py` acumulou mais de 1000 linhas e demasiadas responsabilidades.

### Duplicação

Existem duas implementações relacionadas com universos: `universe_utils.py` e `gui/universe_utils.py`.

### Portfolio

O modelo guarda posições diretamente. Não existe um ledger completo de transações e o preço médio pode ficar incorreto ao agregar compras.

### Backtest

A implementação é experimental, com execução simplificada, uma posição, capital integral e sem um modelo completo de custos, slippage, spread, câmbio, dividendos e benchmark.

### Machine Learning

Problemas identificados:

- `StandardScaler` ajustado antes do split;
- risco de leakage;
- `kfold` usado por defeito;
- exploração de ações sem `TimeSeriesSplit`;
- regressão sobre preço absoluto;
- previsões de preço redundantes entre classificadores;
- consenso por média simples de probabilidades não necessariamente calibradas;
- ranking sem validação estatística suficiente.

### Top 25

O score experimental combina probabilidade de subida, valorização prevista e Sharpe de SMA 50/200. Existem referências a horizonte de 2 dias apesar de o fluxo trabalhar principalmente com 1 e 3 dias.

### Indicadores

Os cálculos devem ser validados individualmente antes de migração. O ADX merece revisão específica.

### Planeamento IA

Existe como demonstração gráfica inicial. A ideia será mantida e reimplementada numa fase posterior.

## Decisão de migração

### Manter ou reaproveitar conceito

- dados de mercado;
- universos;
- indicadores;
- estratégias;
- métricas;
- análise de risco;
- análise de trades;
- PnL attribution;
- estatística;
- prediction log;
- método de trabalho;
- modelo de decisão;
- IA;
- planeamento IA.

### Refazer

- arquitetura;
- portfolio;
- persistência;
- backtester;
- pipeline de ML;
- ranking;
- cache;
- UI.

### Não migrar diretamente

- `main_window.py`;
- implementação atual do Top 25;
- score atual;
- consenso atual;
- regressão de preço na forma atual;
- estrutura PyQt5 atual;
- ficheiros pessoais ou gerados.
