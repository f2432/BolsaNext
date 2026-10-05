# Instruções para agentes

Lê antes de alterar código:

- `README.md`
- `docs/status.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/ai-roadmap.md`
- `docs/legacy.md`
- `docs/development.md`

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


## Hierarquia canónica

Usa estas fontes conforme o tipo de decisão:

1. `docs/status.md` — o que está efetivamente feito e qual é o próximo trabalho;
2. `docs/architecture.md` — como o sistema deve ser estruturado;
3. `docs/roadmap.md` — ordem e âmbito das versões;
4. `docs/ai-roadmap.md` — decisões específicas da área de IA;
5. `docs/legacy.md` — referência histórica, nunca autoridade sobre a nova arquitetura;
6. `docs/development.md` — execução e desenvolvimento local;
7. `pyproject.toml` — dependências executáveis e configuração do pacote.

O `README.md` resume e encaminha para estas fontes. Não duplicar informação detalhada no README quando já existir num documento canónico.


## Fluxo Git

- `main` representa apenas estados validados pelo utilizador;
- trabalho intermédio é feito na branch `dev`;
- não escrever, fazer merge, squash ou atualizar `main` sem pedido explícito do utilizador;
- correções, experiências, testes e documentação intermédia ficam em `dev`;
- quando o utilizador disser que um bloco está validado e pedir passagem para `main`, integrar esse bloco através de squash para manter um único commit coerente em `main`;
- depois da integração, continuar o desenvolvimento seguinte a partir de `dev`.
