# Instruções para agentes

Lê antes de alterar código:

- `README.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/legacy.md`
- `docs/ai-roadmap.md`

## Regras gerais

- faz mudanças pequenas;
- não copiar módulos do projeto legacy sem revisão;
- mantém UI, domínio, aplicação e infraestrutura separados;
- adiciona testes para lógica financeira, matemática e temporal;
- não guardar dados pessoais ou posições reais no Git;
- não versionar caches, modelos treinados, logs ou bases de dados locais;
- preservar ordem temporal em backtesting e machine learning;
- transformações de ML são ajustadas apenas com treino;
- documenta pressupostos financeiros;
- evita regras automáticas de compra/venda escondidas em componentes de UI.

## Portfolio

A origem da verdade são as transações.

Não atualizar posições diretamente quando o resultado puder ser derivado do ledger de transações.

## Backtesting

Considerar explicitamente instante do sinal, instante de execução, custos, slippage, posição e benchmark.

Evitar look-ahead bias.

## IA

A IA é parte prevista da arquitetura desde o início.

O módulo `ai/planning` deve permanecer reservado para evolução do Planeamento IA.

Não usar accuracy isolada como prova de capacidade preditiva.

Registar experiências e resultados fora da amostra.
