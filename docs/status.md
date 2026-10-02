# Estado atual do projeto

Última atualização canónica: 2026-10-02.

Este documento regista o estado efetivo do projeto BolsaNext. O roadmap define o destino; este ficheiro define o ponto em que o projeto se encontra agora.

## Estado global

Versão de trabalho atual: **V0.1 — Fundação**

Estado: **implementada como base inicial; falta validação local completa antes de a considerar fechada**.

Próxima versão de desenvolvimento: **V0.2 — Market Data**.

## Já implementado

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
- suporte alternativo a `python -m bolsa.main`.

### Estrutura de código

- pacote `src/bolsa`;
- camada `app`;
- camada `domain`;
- camada `infrastructure`;
- camada `ui`;
- área reservada `domain/ai/planning`;
- estrutura inicial para testes unitários e de integração.

### Configuração

- `AppConfig` imutável;
- nome da aplicação;
- moeda base inicial EUR;
- diretório local `data/`;
- caminho da base de dados;
- URL SQLite derivada da configuração.

### Logging

- configuração central de logging;
- formato uniforme;
- arranque da aplicação registado.

### Base de dados

- SQLAlchemy configurado;
- `DeclarativeBase`;
- criação de engine;
- factory de sessões;
- inicialização de schema;
- SQLite local em `data/bolsanext.sqlite3`;
- base de dados local excluída do Git.

Ainda não existem tabelas de domínio. Nesta fase a inicialização cria apenas a infraestrutura vazia.

### Interface

- migração conceptual de PyQt5 para PySide6;
- `MainWindow` mínima;
- separadores iniciais:
  - Resumo;
  - Watchlist;
  - Carteira;
  - Análise;
  - Backtesting;
  - IA;
- placeholders explícitos;
- barra de estado com indicação da V0.1.

### Testes

- teste unitário da configuração;
- teste de integração da inicialização SQLite em memória;
- `pytest` configurado;
- `pytest-cov` disponível em dependências de desenvolvimento.

### Integração contínua

- GitHub Actions em `.github/workflows/tests.yml`;
- Python 3.12;
- instalação automática do projeto;
- execução de `pytest -q`;
- execução em pushes para `main`;
- execução em pull requests para `main`.

## Falta validar para fechar V0.1

- clonar o repositório num ambiente local limpo;
- criar a `.venv`;
- executar `pip install -e ".[dev]"`;
- executar `pytest`;
- confirmar que o workflow do GitHub Actions termina com sucesso;
- executar `bolsanext`;
- confirmar criação de `data/bolsanext.sqlite3`;
- confirmar abertura da janela PySide6;
- verificar o comportamento inicial em Windows;
- corrigir qualquer problema de empacotamento, paths ou Qt encontrado nessa validação.

## Próxima fase — V0.2 Market Data

### Domínio

- criar entidade `Instrument`;
- definir identidade e normalização de ticker;
- definir mercado, moeda e tipo de instrumento;
- criar testes unitários do domínio.

### Infraestrutura de mercado

- criar interface/contrato de market data;
- implementar adapter `yfinance`;
- obter histórico OHLCV;
- obter preço atual;
- normalizar colunas e índices;
- definir timezone e política de datas;
- definir política de adjusted/unadjusted prices;
- tratar erros e dados em falta;
- criar testes sem depender permanentemente da rede.

### Universos

- consolidar a ideia de universos do projeto legacy;
- S&P 500;
- NASDAQ 100;
- Euronext 100;
- outros apenas depois da base estar estável;
- não duplicar lógica entre domínio e UI.

### Watchlist

- criar modelo de domínio;
- persistência apenas depois de `Instrument` estar definido;
- estados iniciais coerentes com o módulo Research.

### Cache

- desenhar cache local controlada;
- cache fora do Git;
- metadados de origem e instante de recolha;
- política explícita de expiração.

## Fases posteriores ainda por implementar

### V0.3 Portfolio

Portfolio e Transaction, compras/vendas, posições derivadas, preço médio, PnL realizado e não realizado, moeda base, comissões e import/export.

### V0.4 Analysis

Gráficos, volume, SMA, EMA, RSI, MACD, Bollinger, ATR, estatística e validação matemática dos indicadores.

### V0.5 Strategies

Interface comum, SMA Crossover, RSI + MACD, parâmetros e testes de sinais.

### V0.6 Backtesting

Motor temporal, execução, custos, slippage, position sizing, equity curve, métricas e benchmark.

### V0.7 Investment Research

Diário, tese, catalisadores, riscos, invalidação, cenários e revisão.

### V0.8 AI Foundation

Datasets, features, targets, pipelines, validação temporal, modelos baseline, `ModelRun`, `Prediction` e avaliação fora da amostra.

### V0.9 AI Research

Calibração, ensembles, regressão de retornos, ranking, explicabilidade e avaliação por regimes/horizontes.

### V0.10 AI Planning

Planeamento IA experimental com estados, contexto, ações possíveis, transições, avaliação de planos e histórico de decisões simuladas.

### V1.0

Integração, testes, documentação, migrações, tratamento de erros, instalação reproduzível, revisão de privacidade e estabilização da interface.

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
- dados pessoais, posições reais, credenciais, caches e modelos treinados não entram no Git.
