# Roadmap de Inteligência Artificial

## Objetivo

A IA permanece uma área central de investigação do projeto, mas deve assentar numa base metodologicamente correta.

Não será removida nem tratada como funcionalidade secundária. A implementação será reconstruída progressivamente.

## Princípios

- preservar ordem temporal;
- evitar leakage;
- separar treino, validação e teste;
- ajustar transformações apenas no treino;
- usar pipelines reproduzíveis;
- registar versão dos dados e parâmetros;
- avaliar fora da amostra;
- comparar com baselines simples;
- medir calibração;
- distinguir classificação, regressão e ranking;
- separar previsão de decisão.

## Fase 1 — Fundação

Estrutura prevista:

```text
ai/
├── datasets/
├── features/
├── targets/
├── validation/
├── models/
├── evaluation/
├── predictions/
└── planning/
```

## Fase 2 — Baselines

Modelos iniciais:

- Logistic Regression;
- Random Forest;
- MLP.

Baselines adicionais:

- previsão da classe dominante;
- persistência;
- retorno médio;
- regra simples de momentum.

Nenhum modelo é considerado útil apenas por superar 50% de accuracy.

## Fase 3 — Targets

### Classificação

- subida/queda;
- subida/neutro/queda;
- movimento superior a um limiar;
- retorno relativo a benchmark.

### Regressão

Preferir retorno futuro, log-return ou excesso de retorno.

Evitar usar preço futuro absoluto como target principal.

## Fase 4 — Validação temporal

Aplicar holdout cronológico, TimeSeriesSplit, walk-forward validation e, quando necessário, purging/embargo.

```text
Treino
  ↓
Transformações ajustadas no treino
  ↓
Modelo
  ↓
Validação futura
```

## Fase 5 — Calibração

- reliability curve;
- Brier score;
- calibration error;
- Platt scaling;
- isotonic regression quando apropriado.

## Fase 6 — Ensembles

Só após validar modelos individuais:

- média ponderada por desempenho fora da amostra;
- voting;
- stacking;
- meta-model.

Evitar média simples sem calibração.

## Fase 7 — Explicabilidade

- permutation importance;
- SHAP;
- estabilidade de features;
- análise por regime;
- análise por horizonte.

Feature importance não deve ser interpretada como causalidade.

## Fase 8 — Ranking

Possíveis fatores:

- retorno esperado;
- probabilidade calibrada;
- incerteza;
- desempenho OOS;
- risco;
- liquidez;
- contexto de carteira.

O score deve ter significado documentado e ser testado historicamente.

## Fase 9 — Prediction Journal

Cada previsão deve guardar:

```text
model_run
ticker
timestamp
horizon
features_version
prediction
probability
market_price
actual_outcome
```

Isto permite avaliar accuracy, precision/recall, Brier score, calibração, erro de regressão, desempenho por ativo, mercado, regime e horizonte, bem como degradação do modelo.

## Fase 10 — Planeamento IA

O Planeamento IA fica preservado desde o início como módulo próprio.

Estados possíveis:

```text
IDEIA
↓
EM_ANALISE
↓
AGUARDAR
↓
CANDIDATO
↓
POSICAO
↓
REVER
↓
REDUZIR / REFORCAR / ENCERRAR
```

O estado poderá resultar de mercado, carteira, tese, valuation, risco, indicadores, modelos e eventos.

O planeador poderá futuramente representar ações possíveis, avaliar transições, comparar planos, registar decisões simuladas e explicar por que motivo uma transição foi considerada.

A primeira implementação será experimental e não dependerá de execução automática de ordens.
