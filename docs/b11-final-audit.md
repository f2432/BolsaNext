# B11 — Auditoria pré-integração V0.2 estabilizada

> **DOCUMENTO HISTÓRICO — anterior à publicação.** As frases abaixo sobre `main`/`v0.2.0` intocadas, aprovação e integração pendentes descrevem o estado na altura desta auditoria B11, **não o estado atual**. A V0.2.0 foi integrada por squash na `main` (commit `a26852232c93cdd593fe179b4393fb2abb171d26`) e a tag `v0.2.0` foi publicada. Para o estado vigente, consultar `docs/status.md`.


Data: 2026-10-11. Branch de auditoria: `dev`. **Estado: AUDITORIA DOCUMENTADA; MEDIÇÃO FINAL DE COBERTURA E APROVAÇÃO FINAL PENDENTES.**

Este relatório não autoriza por si só integração em `main`, squash ou criação da tag `v0.2.0`.

## 1. Escopo e validações

O utilizador confirmou a validação sequencial de S0, D1–D3, B1–B10 e I1–I5, incluindo o arranque funcional no Windows através de `run.cmd`. A documentação das validações e respetivas decisões conserva-se em `docs/stabilization-v0.2.md` e `docs/status.md`.

- Aplicação V0.2 Market Data, sem implementação antecipada de Portfolio.
- Cache JSON dos universos escrita atomicamente (I1), política de preservação de instrumentos sem associação (I2), ajuste de `.gitignore` (I3), GPL-3.0-only (I4), arranque Windows opcionalmente com `.venv`, Ruff/pytest e `run.cmd` (I5).
- A V0.3 continua **POR INICIAR**, não devendo ser desbloqueada antes da validação e integração finais.

## 2. Comparação Git main...dev

Consulta via GitHub Compare durante esta auditoria: `dev` **291 commits à frente** de `main`, **zero atrás**, antes deste relatório. As alterações abrangem CI, dependências, run scripts, documentação, arquitetura de ports/adapters, SQLite/migrações, integridade, cache, Watchlist/UI e testes. A listagem é histórica e não representa uma contagem fixa após novos commits de documentação.

As duas revisões Alembic presentes na `dev` são:
- `0001_v02_baseline` — baseline do esquema V0.2 legado;
- `0002_market_to_exchange` — migração para a semântica operacional `exchange`.

O registo de validação funcional e de preservação de dados durante migrações encontra-se nos documentos canónicos e nos testes de integração; esta auditoria de API GitHub não executou migração sobre dados reais.

## 3. CI e qualidade estática

Execução GitHub Actions **#390**, commit `8a006791`: conclusão `success` em Linux/Python 3.12 e Windows/Python 3.14; nos dois jobs, os passos obrigatórios `Ruff lint` e `Run tests with coverage` foram `success`. Execuções subsequentes de documentação (#391–#393) encontravam-se em curso no momento da primeira consulta. Confirmar o resultado do job mais recente antes de fazer a integração final.

`tests/` contém **20 ficheiros Python de testes**. Isto não é o número de testes individuais. O CI produz relatórios de cobertura por plataforma. O texto desses artefactos não esteve acessível através da conexão GitHub nesta auditoria; não estimar nem inventar a contagem atual de testes ou a percentagem de cobertura.

## 4. Comparação com baseline S0 — medição obrigatória pendente

Baseline histórica confirmada: **39 testes** e **55% de cobertura global** no S0.

Preencher com saída reproduzível da branch `dev` atual:

```powershell
git switch dev
git pull --ff-only origin dev
python -m pytest -q --cov=bolsa --cov-report=term-missing --cov-report=xml:coverage.xml
python -m ruff check src tests
```

Se existir `.venv` local, preferir `.venv\Scripts\python.exe` como interpretador destes comandos. Registar a contagem efetiva, a cobertura global e as áreas não cobertas; comparar numericamente com 39/55%. Não estabelecer limiar arbitrário.

## 5. Decisões e fronteiras preservadas

- Portfolio, ledger de transações, câmbio, cálculos financeiros e importação/exportação/reconciliação da carteira permanecem para V0.3, nos termos de A1–A4, restante A5, restante A7 e A8.
- Analysis, Strategies, Backtesting e IA permanecem nas versões futuras do roadmap. `ai/planning` conserva a reserva arquitetural, não é funcionalidade de execução automática.
- Preservar integralmente o Anexo A e a rastreabilidade documental das decisões substituídas.
- SQLAlchemy pure-Python para Windows App Control é uma solução local documentada, não alteração do runtime comum.
- Advertências sobre versões Node.js das ações GitHub e futura imagem `ubuntu-latest` requerem acompanhamento de manutenção; não são erros de Ruff confirmados.

## 6. Gate final e autorização

**Para propor integração**, ainda é obrigatório:
1. recolher contagem atual de testes e percentagem de cobertura e comparar com S0;
2. confirmar o último CI da `dev` com Ruff e pytest aprovados em Linux e Windows;
3. confirmar que não há dados pessoais/sensíveis a integrar e rever o diff final;
4. apresentar ao utilizador o relatório final preenchido e obter validação;
5. pedir autorização **explícita e separada** para o squash/integração em `main`;
6. apenas depois da integração confirmada e aprovada, pedir/obter autorização para criar a tag `v0.2.0`.

**B11 não foi marcado como CONCLUÍDO E VALIDADO.** Não foi modificada `main`, não foi criada a tag nem iniciada V0.3.

## 7. Medição final recolhida no Windows (2026-10-11)

O utilizador apresentou a saída real de `python -m pytest -q --cov=bolsa --cov-report=term-missing`, sobre a versão de desenvolvimento em Windows:

- **161 testes aprovados em 6,46 segundos**;
- **61% de cobertura global** (1 754 statements, 679 miss);
- baseline S0: **39 testes e 55%**;
- evolução: **+122 testes e +6 pontos percentuais**.

A distribuição da cobertura continua desigual: os módulos de entrada e UI PySide6 apresentados no relatório têm 0% em vários casos; scripts Alembic `0001` e `0002` têm 0% por instrumentação da execução, apesar de `schema_migrations.py` apresentar 91%. A cache de universos apresenta 93%, provider Wikipedia 87%, provider yfinance 82% e repository da watchlist 90%. Isto constitui dívida de testes futura e não demonstra, isoladamente, erro funcional. O B9.5 define a estratégia para a endereçar; não ampliar agora o âmbito da V0.2 apenas para aumentar cobertura.

A medição final exigida pelo B11 fica **recolhida e comparada**. Antes da integração final, confirmar o último CI no commit final e obter aprovação explícita do utilizador. **[HISTÓRICO, PRÉ-PUBLICAÇÃO]** `main` e `v0.2.0` permanecem intocadas. **[Posteriormente integradas/publicadas.]** **B11 aguarda validação final/autorização separada, sem integração automática.**

B11, validação final do utilizador (2026-10-11): o utilizador confirmou expressamente a aceitação do relatório B11, **161 testes aprovados e 61% de cobertura** (+122 testes e +6 pontos percentuais face a S0), incluindo as lacunas de UI documentadas para evolução futura. **B11 — AUDITORIA E VALIDAÇÃO DO UTILIZADOR CONCLUÍDAS; INTEGRAÇÃO/PUBLICAÇÃO PENDENTES DE AUTORIZAÇÃO SEPARADA.** Na última consulta, o CI #400 relativo ao commit anterior à validação ainda estava em curso; verificar novamente o CI do estado final antes de integrar. Não efetuar squash/merge em `main` nem criar tag `v0.2.0` sem pedido explícito. V0.3 mantém-se por iniciar.
