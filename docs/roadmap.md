# Roadmap

O roadmap é incremental. Cada versão deve produzir uma aplicação executável e testável.

## V0.1 — Fundação

- estrutura do projeto;
- configuração;
- logging;
- SQLite;
- SQLAlchemy;
- testes;
- arranque da aplicação;
- janela principal mínima;
- integração contínua básica.

## V0.2 — Market Data

- entidade `Instrument`;
- provider `yfinance`;
- histórico OHLCV;
- preço atual;
- normalização de dados;
- universos;
- watchlists;
- cache local controlada.

## V0.3 — Portfolio

- entidade `Portfolio`;
- entidade `Transaction`;
- compras;
- vendas;
- posição calculada;
- preço médio;
- PnL realizado;
- PnL não realizado;
- moeda base;
- comissões;
- importação e exportação.

## V0.4 — Analysis

- gráfico de preços;
- volume;
- SMA;
- EMA;
- RSI;
- MACD;
- Bollinger;
- ATR;
- análise estatística básica;
- validação matemática dos indicadores.

## V0.5 — Strategies

- interface comum de estratégias;
- SMA Crossover;
- RSI + MACD;
- parâmetros;
- testes de sinais;
- registo de estratégias.

## V0.6 — Backtesting

- motor de execução;
- controlo temporal;
- execução no momento correto;
- comissões;
- slippage;
- position sizing;
- trades;
- equity curve;
- retorno;
- volatilidade;
- drawdown;
- Sharpe;
- win rate;
- benchmark.

## V0.7 — Investment Research

- diário de decisão;
- tese;
- catalisadores;
- riscos;
- invalidação;
- valuation por cenários;
- data de revisão;
- ligação à watchlist e carteira.

## V0.8 — AI Foundation

- datasets reproduzíveis;
- feature engineering;
- targets;
- pipelines;
- split temporal;
- walk-forward validation;
- modelos baseline;
- `ModelRun`;
- `Prediction`;
- registo de resultados reais;
- métricas fora da amostra.

Modelos iniciais:

- Logistic Regression;
- Random Forest;
- MLP.

## V0.9 — AI Research

- calibração de probabilidades;
- ensembles;
- regressão de retornos;
- ranking experimental;
- permutation importance;
- SHAP;
- avaliação por regimes;
- avaliação por horizonte;
- comparação com baselines.

## V0.10 — AI Planning

Fase experimental.

- representação de estados;
- contexto de mercado;
- contexto de carteira;
- tese de investimento;
- risco;
- sinais;
- previsões;
- ações possíveis;
- transições;
- avaliação de planos;
- histórico de decisões simuladas.

O módulo deve poder evoluir sem depender de execução automática de ordens.

## V1.0 — Primeira versão estável

- integração dos módulos;
- testes;
- documentação;
- migrações de base de dados;
- tratamento de erros;
- configuração;
- instalação reproduzível;
- revisão de segurança e privacidade;
- limpeza final da interface.
