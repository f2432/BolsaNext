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

**Estado: EM CURSO.** S0, D1–D3, B1–B10 e I1–I5 concluídos e validados; **B11 em auditoria final**, ainda sem autorização de integração em `main` ou criação da tag `v0.2.0`.

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

**Estado: ESPECIFICAÇÃO EM CURSO.** A V0.2.0 foi integrada e publicada; **A1 (âmbito funcional) concluído e validado em 2026-10-11**. A2–A5, A7 e A8 aguardam decisões, sem código Portfolio implementado.

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

### Decisões A1 validadas (2026-10-11)

Ações e ETFs long-only, incluindo quantidades fracionadas; ledger íntegro como origem da verdade; BUY/SELL; DIVIDEND manual com bruto/retenção/encargos/líquido; ADJUSTMENT manual auditável; correção por substituição rastreável e anulação lógica sem apagar originais. Sem derivados, margem, automatismos societários/fiscais, caixa nem ligação direta a brokers nesta fase. Modelos extensíveis para tipos futuros sem implementação prematura. Consultar `docs/architecture.md`, secção **Âmbito da V0.3 — Portfolio**, para contratos e questões a fechar no A2–A5, A7 e A8.

### Progresso da especificação V0.3 (2026-10-11)

**A1, A2 e A3 CONCLUÍDOS E VALIDADOS funcionalmente, sem implementação.** A3 fixa Decimal no domínio, TEXT decimal canónico na persistência SQLite, escalas de entrada 8/12 casas (FX), limite 18 algarismos inteiros, cálculo 50 algarismos significativos, ROUND_HALF_EVEN, fronteira explícita de dados de mercado float e preservação de montantes originais da corretora. A4 (câmbio), A5 (moeda base), A7 (importação/exportação) e A8 (reconciliação) continuam pendentes. A V0.2.0 publicada mantém-se como referência estável.


### Progresso A4 e A5 da V0.3 (2026-10-11)

A4 **CONCLUÍDO E VALIDADO na especificação**: direção FX explícita, separação histórico/atual, `FxRateProvider` implementável inicialmente com yfinance, inversão testável, valores XTB preservados, valorização em moeda base, controlo de antiguidade e indisponibilidade sem totais falsamente completos. **A5 EM DISCUSSÃO**: aprovado que a moeda base pertence à carteira e que a configuração global apenas a predefine; mudanças de moeda exigem operação controlada, ainda por especificar. A1–A4 não representam implementação. A7/A8 pendentes. `main` e tag `v0.2.0` mantêm a versão publicada.

### Progresso A5 da V0.3 (2026-10-11)

**A5 CONCLUÍDO E VALIDADO funcionalmente**, sem implementação: `Portfolio.base_currency` é a autoridade por carteira, com moeda imutável após criação na V0.3; `AppConfig.default_base_currency` apenas preenche a criação de novas carteiras. Moedas normalizadas ISO 4217, múltiplas carteiras em moedas distintas e migração da antiga configuração com preservação e validação explícita. **Próximo: A7** (backup e recuperação, exportação canónica, importação atómica, duplicados e relatório); A6 resolvido na V0.2; A8 ainda por discutir. A V0.2.0 publicada em `main` permanece intacta.

### Progresso A7 da V0.3 (2026-10-11)

**A7 CONCLUÍDO E VALIDADO ao nível de especificação, não implementação.** JSON de carteira canónico e versionado, exportação integral do histórico e auditoria, identidade UUID e proveniência externa, importação atómica/idempotente com pré-visualização e relatório de conflitos, restauro seguro/cópias independentes e exclusão da substituição destrutiva; backup integral distinto da exportação funcional (D2/A7.1). **A8 é o próximo bloco**, centrado em reconciliação com a XTB e estrutura da política pessoal de investimento. A V0.2.0 permanece publicada e intacta.


### V0.3 — Fecho da especificação A8 (2026-10-11)

**A8 VALIDADO FUNCIONALMENTE**, sem código: integridade/reconciliação interna do ledger, mantendo reconciliação automática de extratos XTB para fase posterior; política opcional e versionada por carteira, indicadores de concentração/exposição, ganhos/perdas e desvios de objetivos, alertas informativos avaliáveis apenas com dados completos, sem sugestões nem operações automáticas. Com A1–A5 e A7 validados e A6 já resolvido na V0.2, **a especificação funcional A1–A8 está concluída**. Próxima etapa possível: **auditoria global das especificações versus código/arquitetura**, condicionada a autorização futura do utilizador; **não iniciar agora**. V0.2.0 publicada em `main` e respetiva tag permanecem intactas.


### V0.3 — Resolução técnica da auditoria (2026-10-11)

Auditoria documental realizada e decisões técnicas AUD-001 a AUD-012 consolidadas em `docs/architecture.md` e `docs/development.md`, sem execução de testes nem alteração de código. Principais contratos: identidade económica/versões e anulação, cálculo multimoeda por componente e divergências pendentes da corretora, sincronização das escritas do ledger/revisão para importações, clones no âmbito da carteira, replay e caches derivados, metadados de risco, backup e migrações. `AppConfig.default_base_currency` já consta do código V0.2, dispensando renomeação fictícia. Corrigida por aditamento a prioridade do estado Git: `main` e tag `v0.2.0` publicadas; texto histórico preservado.

**Próxima etapa possível:** plano técnico da implementação incremental V0.3 com testes de invariantes e migração validada em base descartável, seguido de desenvolvimento quando o utilizador o solicitar. Não começar implementação neste registo. Versão estável `main`/`v0.2.0` não foi modificada.
