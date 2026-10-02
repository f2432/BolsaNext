# BolsaNext

Plataforma pessoal de análise de investimentos em Python.

O projeto tem como objetivo reunir, numa aplicação única, a gestão de carteira, análise de ativos, investigação, backtesting e experimentação de modelos de inteligência artificial, mantendo separadas a evidência, a análise e a decisão final.

## Estado do projeto

O projeto está numa fase inicial de reconstrução a partir de uma aplicação anterior.

A versão anterior provou vários conceitos, incluindo:

- obtenção de dados de mercado;
- indicadores técnicos;
- estratégias SMA Crossover e RSI + MACD;
- backtesting;
- gestão de carteira;
- análise de risco;
- modelos de machine learning;
- exploração de universos de ações;
- registo de previsões;
- ranking experimental de ações;
- experiências iniciais de planeamento com IA.

A nova versão não pretende copiar diretamente a implementação antiga. As funcionalidades serão reintroduzidas progressivamente sobre uma arquitetura mais modular, testável e consistente.

## Princípios

1. A carteira é construída a partir de transações, não de posições introduzidas manualmente.
2. Dados, lógica de negócio, interface e infraestrutura permanecem separados.
3. O backtesting deve respeitar a sequência temporal e evitar look-ahead bias.
4. Modelos de machine learning devem ser avaliados fora da amostra.
5. Transformações e normalizações são ajustadas apenas com dados de treino.
6. A IA é uma ferramenta de análise e investigação, não um mecanismo de execução automática.
7. O projeto deve preservar espaço para evolução futura de IA, ensembles, explicabilidade e planeamento.
8. Dados pessoais, posições reais, credenciais, caches e modelos treinados não são versionados.

## Tecnologias previstas

- Python 3.12+
- PySide6
- pandas
- NumPy
- SQLAlchemy
- SQLite
- yfinance
- scikit-learn
- matplotlib
- pytest
- PyYAML

## Estrutura prevista

```text
src/bolsa/
├── app/
├── domain/
│   ├── instruments/
│   ├── portfolio/
│   ├── watchlist/
│   ├── strategies/
│   ├── backtest/
│   ├── research/
│   └── ai/
│       └── planning/
├── infrastructure/
│   ├── database/
│   ├── market_data/
│   └── repositories/
├── ui/
└── main.py

tests/
docs/
data/
```

## Roadmap

Consulta `docs/roadmap.md`.

## Arquitetura

Consulta `docs/architecture.md`.

## Projeto anterior

O inventário da implementação anterior encontra-se em `docs/legacy.md`.

## IA

A evolução prevista dos módulos de inteligência artificial encontra-se em `docs/ai-roadmap.md`.


## Desenvolvimento local

As instruções para instalar, executar e testar o projeto estão em `docs/development.md`.

Resumo rápido:

```bash
git clone https://github.com/f2432/BolsaNext.git
cd BolsaNext
python -m venv .venv
pip install -e ".[dev]"
pytest
bolsanext
```

O projeto possui integração contínua através de GitHub Actions. Os testes são executados automaticamente em pushes e pull requests para `main`.
