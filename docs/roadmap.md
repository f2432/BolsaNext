# Roadmap

O roadmap é incremental. Cada versão deve produzir uma aplicação executável e testável.

O estado efetivo e detalhado do trabalho encontra-se em `docs/status.md`.

## V0.1 — Fundação

**Estado: CONCLUÍDA E VALIDADA.**

Implementado:

- estrutura do projeto;
- configuração;
- logging;
- SQLite;
- SQLAlchemy;
- testes iniciais;
- arranque da aplicação;
- janela principal mínima;
- integração contínua básica;
- empacotamento via `pyproject.toml`;
- comando `bolsanext`;
- documentação de desenvolvimento.

Validação concluída:

- instalação local validada em Windows;
- aplicação PySide6 abriu corretamente;
- 8 testes passaram localmente;
- base SQLite local criada;
- GitHub Actions confirmado com sucesso.

## V0.2 — Market Data

**Estado funcional: CONCLUÍDA E INTEGRADA. Em estabilização final antes da V0.3.**

A conclusão funcional de 2026-10-05 permanece registada. Uma revisão posterior abriu um ciclo de hardening e coerência que tem de fechar antes da V0.3.

Implementado até ao momento:

- entidade `Instrument`;
- provider `yfinance`;
- histórico OHLCV;
- preço atual;
- normalização de dados;
- política inicial de adjusted/unadjusted prices;
- timezone e datas;
- domínio e provider de universos;
- S&P 500, NASDAQ 100 e Euronext 100;
- integração dos universos na interface;
- seleção de instrumento de um universo e adição à Watchlist;
- domínio e serviço de watchlist;
- primeira interface funcional da watchlist;
- metadados automáticos de instrumentos adicionados manualmente;
- operações de rede em background para universos e atualização de preços;
- cache local de universos com TTL;
- persistência SQLite da watchlist;
- restauro automático no arranque;
- edição de estados;
- remoção de ativos;
- persistência das preferências de largura das tabelas;
- testes de domínio e infraestrutura.

Fecho técnico concluído:

- validação sintática e de existência de tickers;
- erros próprios para ticker inexistente e fornecedor indisponível;
- mensagens de erro melhoradas;
- casos de histórico vazio, `Adj Close` em falta e timezone cobertos por testes;
- decisão explícita de não fazer retries automáticos na V0.2;
- múltiplas Watchlists adiadas para uma fase posterior;
- edição de notas remetida para Research;
- cache de histórico remetida para V0.4 Analysis;
- CI executado também sobre pushes para `dev`.

A integração funcional da V0.2 em `main` já aconteceu. O trabalho atual é um ciclo adicional de estabilização, descrito em `docs/stabilization-v0.2.md`.

## Gate obrigatório entre V0.2 e V0.3 — Estabilização final

**Estado: EM CURSO.** B1–B9 concluídos e validados; B10 em revisão documental, com I1–I5 e B11 ainda por fechar.

Este gate não é uma nova versão funcional. Serve para estabilizar a V0.2 e preparar a base técnica sem iniciar Portfolio.

Abrange:

- decisões V0.2 retiradas da antiga Faixa A: A6 completa, A7.1 e parte atual de A5;
- B1 a B10;
- itens avulsos I1 a I5;
- B11 como fecho definitivo;
- preservação integral das decisões futuras A1–A4, restante A5, restante A7 e A8.

A V0.3 não pode começar até este gate estar fechado e validado pelo utilizador.

Plano detalhado e matriz de rastreio: `docs/stabilization-v0.2.md`.

## V0.3 — Portfolio

**Estado: POR INICIAR E BLOQUEADA PELO GATE DE ESTABILIZAÇÃO V0.2.**

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

**Estado: POR INICIAR.**

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

**Estado: POR INICIAR.**

- interface comum de estratégias;
- SMA Crossover;
- RSI + MACD;
- parâmetros;
- testes de sinais;
- registo de estratégias.

## V0.6 — Backtesting

**Estado: POR INICIAR.**

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

**Estado: POR INICIAR.**

- diário de decisão;
- tese;
- catalisadores;
- riscos;
- invalidação;
- valuation por cenários;
- data de revisão;
- ligação à watchlist e carteira.

## V0.8 — AI Foundation

**Estado: PLANEADA.**

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

**Estado: PLANEADA.**

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

**Estado: PLANEADA, COM ESPAÇO ARQUITETURAL JÁ RESERVADO.**

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

**Estado: FUTURA.**

- integração dos módulos;
- testes;
- documentação;
- migrações de base de dados;
- tratamento de erros;
- configuração;
- instalação reproduzível;
- revisão de segurança e privacidade;
- limpeza final da interface.
