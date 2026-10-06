# Estabilização final da V0.2 antes da V0.3

Última atualização canónica: 2026-10-05.

## Finalidade

Este é o plano canónico e sequencial do ciclo atual do BolsaNext.

O objetivo deste ciclo é **estabilizar definitivamente a V0.2 — Market Data antes de iniciar a V0.3 — Portfolio**.

A V0.3 **não está iniciada**. Nenhuma entidade `Portfolio`, `Transaction`, `Position`, `PortfolioService` ou funcionalidade de carteira deve ser implementada enquanto este ciclo não estiver fechado e validado pelo utilizador.

Este documento consolida os 16 pontos de incongruência, os blocos adicionais da segunda revisão, o plano `PLANO_PRE_V03.md` preparado pelo utilizador e as correções de execução acordadas posteriormente. O plano fonte é preservado integralmente no Anexo A. O ficheiro original de revisão `v02_erros.txt` é também preservado, sem reescrita, em `docs/reference/v02_erros.txt`.

## Regra absoluta de preservação

**Nenhuma informação canónica existente pode ser perdida por uma alteração posterior.**

1. Não apagar decisões, requisitos, problemas, justificações ou trabalho pendente apenas por reorganização.
2. Quando uma decisão for substituída, preservar a anterior como histórica/superseded, com motivo e data.
3. Quando um item for adiado, mantê-lo explicitamente registado com destino futuro.
4. Quando documentos forem consolidados, preservar rastreabilidade para a origem.
5. Antes de alterar um canónico, comparar com o estado anterior e garantir que nenhuma informação substantiva desapareceu.
6. Um item só sai de pendente quando estiver implementado/decidido e validado, conforme aplicável.
7. “Limpeza”, “simplificação” ou “refatoração documental” nunca autorizam eliminar informação.
8. Em conflito entre condensação e preservação, prevalece a preservação.

Esta regra aplica-se a todo o projeto.

## Estado de partida

- V0.1 concluída.
- V0.2 funcionalmente concluída, integrada na `main` e validada no fluxo já registado.
- Uma revisão posterior identificou hardening, incongruências e decisões técnicas a fechar antes da V0.3.
- `main` e `dev` têm o mesmo conteúdo funcional no início deste ciclo; `dev` conserva histórico técnico adicional.
- O trabalho deste ciclo é realizado em `dev`.
- `main` não é alterada sem pedido explícito do utilizador.
- A V0.3 permanece **POR INICIAR** até ao fecho deste documento.

## Reinterpretação canónica da antiga Faixa A

A Faixa A não é descartada. É dividida conforme o que realmente pertence ao saneamento da V0.2 e o que é especificação futura da V0.3.

### Entram já na estabilização da V0.2

#### D1 — A6 completa: semântica de `market` e proveniência dos metadados

Tem de ser decidida antes de B3/B8:

- significado exato de `market`;
- exchange/listing venue versus região;
- autoridade de metadados entre Yahoo e universos;
- responsabilidade dos universos;
- prioridade entre fontes;
- regra de atualização/substituição de metadados já preenchidos;
- tratamento de valores pouco precisos como `market="US"`.

#### D2 — A7.1: backup antes de operações destrutivas e migrações

Entra já porque B5/B6 mexem em localização e evolução da base:

- cópia de segurança mínima;
- localização conhecida do backup;
- procedimento de restauro;
- comportamento em falha;
- proteção da base antiga.

Os restantes pontos de A7 ficam preservados para V0.3.

#### D3 — Parte atual de A5: significado de `base_currency`

Neste ciclo decide-se apenas:

- `AppConfig.base_currency` não deve ser tratado como autoridade financeira global futura;
- avaliar renomeação para `default_base_currency`;
- não implementar ainda `Portfolio.base_currency`.

### Preservado para a futura especificação da V0.3, sem executar agora

- **A1** — âmbito da V0.3, tipos de transação, dividendos e corporate actions;
- **A2** — ledger e regras contabilísticas;
- **A3** — Decimal/Numeric, precisão e arredondamento;
- **A4** — convenção de câmbio e valuation em moeda base;
- **restante A5** — autoridade de `Portfolio.base_currency`;
- **restante A7** — exportação, importação, duplicados e relatório de importação;
- **A8** — reconciliação com broker e política pessoal de investimento.

A política pessoal real, quando existir, não expõe valores pessoais/sensíveis no repositório público; o Git pode conter apenas estrutura/template e regras não sensíveis.

## Correções ao plano fonte que governam a execução

1. A Faixa A contém A1 a A8; referências a “A1 a A9” são lapso documental.
2. “39 testes” é baseline inicial, não número fixo. O total pode aumentar e não deve diminuir sem justificação explícita.
3. “Ledger como origem da verdade” e “transações absolutamente imutáveis” são decisões distintas; a política de correção/anulação será decidida na futura A2.
4. B3 fica subordinada às decisões de D1/A6; a lógica de subunidades não é colocada antecipadamente no domínio se a decisão de proveniência indicar que pertence ao adapter/provider.
5. A tag `v0.2.0` só é criada no fecho B11, depois do saneamento e integração final.
6. B10.3 não deve concluir que a `main` recebeu todos os commits intermédios da `dev`. O histórico não é reescrito; corrige-se o procedimento futuro.
7. B2 e B8 são obrigatórios antes da V0.3.
8. Valores reais da política pessoal de investimento não entram no Git.
9. I5 não torna ambiente virtual obrigatório sem nova decisão explícita do utilizador. A decisão anterior de não exigir venv mantém-se.
10. B6 admite novas alterações de schema posteriores; depois da baseline, cada alteração estrutural é uma nova migração.
11. O foco exclusivo do ciclo atual é a V0.2. Discussões futuras de Portfolio não autorizam implementação da V0.3.
12. Tudo o que já existia nos canónicos permanece preservado salvo indicação explícita de que foi superseded.

## Ordem sequencial obrigatória

### S0 — Baseline

Antes de código:

- confirmar `dev`;
- registar SHA inicial;
- correr suite completa;
- medir cobertura real;
- confirmar ausência de dados pessoais/gerados;
- confirmar proteção de `main`;
- usar 39 testes apenas como baseline histórico.

Se falhar, parar.

#### Registo de execução S0 — 2026-10-05

Estado atual: **CONCLUÍDO E VALIDADO**.

Resultados confirmados:

- branch remota de trabalho: `dev`;
- SHA remoto de referência no arranque deste baseline: `d3796d76adfc0678cfcda6f8268a8dd5178a78e0`;
- `main` permanece em `d4bbe1113704754f0cb8fe8972d07957aa173ffb` e não foi alterada neste ciclo;
- CI GitHub Actions sobre a `dev`: sucesso;
- clone local confirmado limpo por `git status --short` sem saída;
- SHA local confirmado em `ced77dc23897603c8b68a908e946767793e4dffb`, igual ao HEAD remoto da `dev` após sincronização;
- suite local Windows: **39 testes passaram**;
- cobertura global local: **55%**;
- total medido: 957 statements, 429 não cobertos;
- ambiente local observado no relatório de cobertura: Windows, Python **3.14.5**;
- CI remoto continua em Python 3.12, pelo que o ciclo passa a ter duas referências reais de runtime: Python 3.12 em CI e Python 3.14.5 no PC local;
- foi observado um `ResourceWarning` relacionado com uma ligação SQLite não fechada durante `tests/integration/test_watchlist_repository.py::test_watchlist_persists_and_reloads`;
- esse warning não fez falhar a suite, mas fica registado como problema real de baseline e deve ser tratado no saneamento de persistência, em particular B4, sem ser perdido por omissão.

O valor de 55% passa a ser o baseline oficial de cobertura deste ciclo. Os 39 testes passam a ser o baseline inicial de contagem, não um número fixo.

S0 fica formalmente fechado. O passo seguinte é D1 — A6 completa: semântica de `market` e proveniência/prioridade dos metadados.

### D1 — A6 completa

Estado: **DECIDIDO E DOCUMENTADO** em 2026-10-05.

Decisão canónica:

1. O conceito atualmente chamado `market` deixa de representar mistura de região, país, grupo de mercado e bolsa. O significado canónico passa a ser **bolsa/local de cotação (exchange / listing venue)**.
2. A implementação deverá preferir o nome `exchange` no domínio e persistência quando essa alteração for executada. A UI deverá apresentar um rótulo simples como **Bolsa**. Região geográfica não é introduzida agora; se vier a ser necessária será um atributo separado.
3. Providers de universos, incluindo Wikipedia, são autoridade para **composição dos universos** e podem fornecer ticker e nome útil/provisório. Não são autoridade final para exchange, moeda ou tipo de ativo.
4. Yahoo é a fonte principal dos **metadados canónicos do instrumento** na V0.2: nome canónico quando disponível, exchange, moeda e tipo de ativo.
5. Informação vinda dos universos é considerada provisória/fallback. Valores pouco precisos como `market="US"` não devem continuar a ser tratados como metadados canónicos permanentes.
6. Um instrumento proveniente de um universo pode ser adicionado quando Yahoo estiver temporariamente indisponível, mas nesse caso apenas devem ser preservados dados que não sejam apresentados como confirmados pela fonte principal. Exchange/moeda desconhecidos ficam por completar em vez de serem inventados ou inferidos silenciosamente.
7. A ação explícita **Atualizar dados** deve voltar à fonte principal e atualizar metadados canónicos, mesmo quando nome/exchange/moeda já estejam preenchidos. A regra anterior “não consultar se todos os campos estão preenchidos” fica marcada como comportamento a substituir em B8.
8. A precedência entre fontes é responsabilidade da camada **Application/serviço**. Nem a UI nem o repository decidem qual origem vence.
9. O repository recebe um `Instrument` já considerado canónico para persistência; não arbitra proveniência.
10. Não é introduzido neste ciclo um campo persistente `metadata_source`, por não ser necessário para resolver corretamente a V0.2.
11. Esta decisão governa B3 (subunidades monetárias) e B8.2 (UniverseWidget/metadados). Em particular, lógica de moeda inferida pelo provider Wikipedia deve ser revista à luz desta decisão, e a normalização de convenções específicas do Yahoo deve ficar junto do adapter/provider de Market Data sempre que for uma característica da fonte.

Consequências esperadas para a implementação posterior:

- `Instrument.market` será migrado conceptualmente para `exchange`;
- a UI deixará de misturar `US`, `NASDAQ`, `AMSTERDAM`, `PARIS`, etc. no mesmo conceito;
- universos deixam de ser fonte autoritativa para moeda/exchange;
- `refresh_metadata` passa a significar atualização real a partir da fonte principal;
- instrumentos existentes com metadados imprecisos poderão ser corrigidos por atualização;
- B3 poderá remover ou reduzir mapas de moeda inferidos em Wikipedia e concentrar a conversão de convenções de cotação no adapter apropriado.

D1 fica fechado. Próximo passo: **D2 — A7.1: política de backup antes de movimentos e migrações da base**.

### D2 — A7.1

Estado: **DECIDIDO E DOCUMENTADO** em 2026-10-05.

Decisão canónica de backup/restauro para o ciclo V0.2:

1. A base SQLite é considerada dado persistente que nunca pode ser substituído, movido ou migrado sem existir primeiro uma cópia recuperável.
2. É obrigatório criar backup antes de qualquer migração de schema. Se o backup falhar, a migração não começa.
3. É obrigatório criar backup antes da mudança de localização da base. A base de origem não é apagada nem substituída durante a transição.
4. Nenhum movimento/migração de base é feito sem tornar explícitos ao utilizador a origem, o destino e o caminho do backup.
5. Backups nunca entram no Git e devem ficar fora do repositório ou em localização explicitamente ignorada.
6. Backups são imutáveis e nunca são sobrescritos. O nome inclui timestamp e, quando útil, o motivo, por exemplo `bolsanext_before_migration_YYYYMMDD_HHMMSS.sqlite3`.
7. A implementação deverá preferir a **SQLite Backup API** em vez de cópia cega do ficheiro, para obter snapshot consistente mesmo perante futuras utilizações de WAL ou ligações abertas.
8. Depois de criado, o backup tem de ser validado: existência, tamanho não nulo, abertura SQLite e `PRAGMA quick_check` com resultado `ok`.
9. Uma migração só é considerada concluída depois de a base migrada ser validada. Em falha, a base original e o backup permanecem preservados.
10. Restauro é explícito, não automático. A aplicação não escolhe sozinha um backup antigo para substituir a base ativa.
11. Num restauro, a base problemática também deve ser preservada antes de ser substituída.
12. Nesta fase não existe rotação automática de backups; backups de migração/movimento são mantidos.
13. Esta política destina-se a proteger B5/B6 e a V0.2 estabilizada. O sistema geral de backup/export/import da futura carteira continua preservado no restante A7 para a especificação da V0.3.

Fluxo mínimo obrigatório:

```text
base original
    ↓
backup via SQLite Backup API
    ↓
validar backup (quick_check)
    ↓
movimento/migração
    ↓
validar nova base
    ↓
continuar
```

Em falha:

```text
parar operação
preservar base original
preservar backup
não promover base parcialmente migrada
apresentar erro
```

D2 fica fechado. Próximo passo: **D3 — parte atual de A5: significado de `base_currency` na configuração**.

### D3 — parte atual de A5

Estado: **DECIDIDO E DOCUMENTADO** em 2026-10-05.

Decisão canónica:

1. O campo atual `AppConfig.base_currency` não representa uma autoridade financeira global da aplicação.
2. O significado correto é **moeda base por omissão para futuras entidades/funcionalidades que necessitem de uma moeda inicial**.
3. O nome preferido passa a ser `default_base_currency`, por ser semanticamente explícito.
4. A alteração deste valor de configuração no futuro não pode modificar silenciosamente dados persistentes já existentes.
5. A futura entidade `Portfolio`, quando vier a existir, terá a sua própria moeda base persistida e essa será a autoridade da carteira. Esta regra fica apenas preservada como especificação futura; **não é implementada neste ciclo**.
6. Não são introduzidos agora cálculos financeiros, conversão cambial, validação de Portfolio ou qualquer outra funcionalidade V0.3.
7. A implementação da renomeação de configuração pode ser feita durante o saneamento técnico quando for oportuno, preservando compatibilidade onde necessário.

D3 fica fechado. Próximo passo: **B1 — Ports e direção das dependências**.

### B1 — Ports e direção das dependências

Estado: **CONCLUÍDO E VALIDADO**.

Implementação em `dev`: commit `0f680d36a836c8add5893db0c65d6d3f32fab865` — `refactor: move application contracts to ports`.

Foi implementado o desenho previamente validado:

- criado `src/bolsa/app/ports/market_data.py` com `MarketDataProvider`;
- criado `src/bolsa/app/ports/universe.py` com `UniverseProvider`;
- criado `src/bolsa/app/ports/repositories.py` com `WatchlistRepository`;
- criado `src/bolsa/app/ports/errors.py` com `MarketDataError`, `InstrumentNotFoundError` e `MarketDataUnavailableError`;
- criado `src/bolsa/app/ports/__init__.py` como superfície explícita dos contratos;
- `MarketService`, `UniverseService` e `WatchlistService` deixaram de importar `bolsa.infrastructure`;
- `WatchlistRepository` saiu de dentro de `watchlist_service.py` e passou para o port de repositories;
- `YFinanceMarketDataProvider` passa a usar os erros canónicos dos ports;
- `CachedUniverseProvider` passa a tipar a fonte com o port canónico de universos;
- os antigos `infrastructure/market_data/provider.py`, `universe_provider.py` e `errors.py` ficam temporariamente como reexports de compatibilidade;
- criado `tests/unit/test_architecture.py`, que falha se qualquer ficheiro de `src/bolsa/app/` voltar a importar diretamente `bolsa.infrastructure`;
- `docs/architecture.md` documenta os caminhos reais, a direção das dependências e a compatibilidade transitória.

Resultado automático:

- GitHub Actions na `dev`: **SUCCESS**;
- suite automática após B1: **40 passed in 1.59s**;
- baseline anterior: 39 testes; o teste adicional é a proteção arquitetural;
- nenhuma asserção funcional anterior foi alterada;
- B1 não alterou comportamento de negócio, UI, Market Data ou persistência.

Validação local concluída em Windows:

- `git pull --ff-only origin dev` concluído por fast-forward;
- `python -m pytest -q`: **40 passed in 2.71s**;
- `python -m bolsa.main`: aplicação iniciou corretamente, conforme validação local do utilizador.

B1 fica **CONCLUÍDO E VALIDADO**.

Próximo passo: **B2 — Taxonomia e comportamento dos erros externos**.

### B2 — Taxonomia e comportamento dos erros externos

Estado: **CONCLUÍDO E VALIDADO**.

Decisões aprovadas em 2026-10-05:

1. Existe uma raiz comum `ExternalDataError`.
2. `MarketDataError` e `UniverseError` são famílias paralelas; erros de universos não herdam de Market Data.
3. A família Market Data distingue pelo menos:
   - `InstrumentNotFoundError`;
   - `MarketDataUnavailableError`;
   - `CurrentPriceUnavailableError`;
   - `MarketDataFormatError`.
4. A família Universe distingue:
   - `UnsupportedUniverseError`;
   - `UniverseSourceUnavailableError`;
   - `UniverseFormatError`.
5. `get_current_price()` passa a devolver `float` em sucesso ou a levantar erro tipado. O `None` ambíguo deixa de fazer parte do contrato.
6. Histórico vazio continua a ser um resultado válido e preserva o schema canónico; esta decisão anterior não é alterada.
7. Universos passam a devolver `UniverseLoadResult` na camada Application, com estados:
   - `LIVE`;
   - `FRESH_CACHE`;
   - `STALE_CACHE`.
8. Uma cache expirada pode ser usada como fallback degradado quando a fonte está indisponível ou muda de formato, desde que tenha no máximo **7 dias**.
9. O uso de cache stale é sempre explícito, com timestamp e aviso; nunca é apresentado como dado fresco.
10. Não existe fallback stale para universo não suportado.
11. Exceções internas de urllib, pandas ou yfinance não devem escapar dos adapters quando correspondem a falhas previsíveis.
12. A Watchlist preserva as restantes linhas quando um preço individual falha e mantém o motivo como aviso tipado/acionável.
13. A UI apresenta mensagens diferentes para ausência de cotação, falha do fornecedor e formato inesperado; universos mostram também a frescura dos dados.

Implementação realizada na `dev`:

- hierarquia unificada em `app/ports/errors.py`;
- contrato de preço atual atualizado em `app/ports/market_data.py`;
- `UniverseLoadResult` e `UniverseLoadStatus` em `app/ports/universe.py`;
- YFinance traduz falhas previsíveis para erros tipados;
- Wikipedia traduz indisponibilidade e alterações de formato para a família Universe;
- `CachedUniverseProvider` suporta cache fresca e fallback stale até 7 dias;
- `UniverseService` e `UniverseWidget` transportam/mostram proveniência e frescura;
- `WatchlistService` preserva a lista quando preços individuais falham e expõe avisos;
- `WatchlistWidget` mostra os avisos de preço;
- reexports de compatibilidade foram atualizados;
- testes de rede usam fontes simuladas e não dependem de Internet.

Validação automática:

- GitHub Actions na `dev`: **58 testes passaram em 2.44s**;
- o crescimento de 40 para 58 testes corresponde à cobertura adicional de erros de Market Data, erros de universos, fallback stale e comportamento da Watchlist.

Validação local confirmada pelo utilizador em 2026-10-06.

O fallback stale e os erros de fonte/formato ficam cobertos por testes automatizados, não exigindo provocar falhas reais de rede manualmente.

B2 fica **CONCLUÍDO E VALIDADO**.

Próximo passo: **B3 — Moedas em subunidade**.

### B3 — Moedas em subunidade

Estado: **IMPLEMENTADO E VALIDADO NO CI; AGUARDA VALIDAÇÃO LOCAL**.

Desenho aprovado em 2026-10-06 e subordinado a D1/A6:

1. O domínio conhece apenas moedas canónicas (`GBP`, `ZAR`, `ILS`, etc.).
2. Convenções de cotação específicas do Yahoo pertencem ao adapter Yahoo e não são persistidas no `Instrument`.
3. Convenções iniciais suportadas:
   - `GBp` → `GBP`, fator `0.01`;
   - `GBX` → `GBP`, fator `0.01`;
   - `ZAc` → `ZAR`, fator `0.01`;
   - `ILA` → `ILS`, fator `0.01`;
   - códigos canónicos de três letras em maiúsculas → fator `1.0`.
4. Uma convenção desconhecida ou malformada não é silenciosamente convertida; produz `MarketDataFormatError`.
5. O fator é aplicado ao preço atual e às colunas históricas `Open`, `High`, `Low`, `Close` e `Adj Close`.
6. `Volume` não é escalado.
7. O provider mantém uma pequena cache em memória por ticker com a convenção bruta, moeda canónica e fator. Esta cache é apenas da sessão e não é persistida.
8. `Instrument.currency` nunca é usado para inferir o fator, porque `GBP` persistido não permite distinguir GBP de uma cotação Yahoo em pence.
9. Wikipedia continua provisoriamente com os seus metadados atuais até B8.2; B3 garante que esses dados não são usados para decidir a escala dos preços Yahoo.
10. O caso crítico `12345 GBp → 123.45 GBP` fica protegido por teste explícito.

Implementação na `dev`: commit `d27342efbb0665db2a44bb39a4da4d728eeaa19b` — `fix: normalize Yahoo quote subunits`.

Foi implementado:

- objeto interno `_QuoteConvention` no adapter Yahoo;
- mapa explícito de subunidades;
- cache de convenção por ticker;
- normalização da moeda em `get_instrument_details()`;
- escala do preço atual;
- escala de OHLC + Adj Close no histórico, sem alterar Volume;
- erro tipado para convenções inesperadas;
- testes parametrizados para moedas canónicas/subunidades;
- teste de histórico com volume preservado;
- teste de cache da convenção;
- teste de regressão explícito para fator 100.

Validação automática:

- GitHub Actions na `dev`: **72 testes passaram em 1.01s**;
- baseline anterior a B3: 58 testes;
- os 14 testes adicionais cobrem convenções de moeda, rejeição de formatos inesperados, metadados canónicos, escala de preço/histórico e cache da sessão.

Falta para fechar B3 como **CONCLUÍDO E VALIDADO**:

- sincronizar o clone local;
- correr a suite local;
- abrir a aplicação;
- validar pelo menos um ticker cotado em subunidade, preferencialmente um título de Londres como `VOD.L`, confirmando que a moeda apresentada é `GBP` e que o preço não aparece 100 vezes acima do valor esperado.

Observação preservada para B9: o GitHub Actions atual emitiu aviso de depreciação do runtime Node.js 20 nas versões usadas de `actions/checkout@v4` e `actions/setup-python@v5`; o workflow continua a passar, mas este aviso deve ser revisto no bloco de CI/qualidade.

Próximo passo depois da validação local: **B4 — Integridade SQLite**.

### B4 — Integridade SQLite

Ativar e testar foreign keys, rever cascatas, confirmar instrumentos órfãos intencionais, avaliar WAL sem ativação automática injustificada, preservar atomicidade e rollback.

### B5 — Localização estável dos dados

Depois de D2. Eliminar dependência de `Path("data")` relativo, usar diretoria estável por utilizador/SO e override adequado, separar leitura de configuração de criação de ambiente e proteger a base antiga.

### B6 — Migrações

Introduzir mecanismo de migrações, baseline V0.2, evolução controlada, comportamento no arranque, backup e testes de migração. Alterações futuras de schema são novas revisões.

### B7 — Fonte única de versão

Unificar package/UI/User-Agent. Não criar ainda tag.

### B8 — Hardening Watchlist/UI

Obrigatório antes da V0.3:

- B8.1 concorrência global;
- B8.2 UniverseWidget e decisão D1;
- B8.3 cache de preços da sessão;
- B8.4 validação realista de tickers;
- B8.5 estado desconhecido defensivo;
- coordenação UI + proteção de serviço;
- testes quando aplicável.

### B9 — CI, dependências e qualidade

Cobertura no CI, avaliar Windows CI, coerência de triggers, dependências utilizadas, dependências futuras fora do core, política de versões/constraints, avaliação do Ruff e estratégia de testes futura apenas documentada.

### B10 — Coerência canónica

Rever README, status, roadmap, architecture, development, ai-roadmap, legacy e AGENTS sem os transformar em duplicados. Propor prevenção de divergência e esperar escolha antes de implementar.

### Itens avulsos obrigatórios

- I1 — cache de universos com escrita atómica;
- I2 — instrumentos órfãos: preservar/documentar intenção;
- I3 — restringir `.gitignore` sem bloquear PDFs legítimos;
- I4 — LICENSE: apresentar opções e esperar decisão;
- I5 — `run.ps1`/venv: rever coerência, sem tornar venv obrigatório sem nova decisão.

### B11 — Fecho definitivo da V0.2 estabilizada

- suite completa;
- cobertura antes/depois;
- validação Windows e CI;
- diff desde S0;
- confirmação de completude;
- decisões vigentes registadas;
- adiamentos para V0.3 explícitos;
- validação final do utilizador;
- só depois integração autorizada em `main`;
- confirmar mensagem final;
- criar tag `v0.2.0` apenas depois da integração validada;
- só então abrir formalmente V0.3.

## Regra de completude

Cada item termina num destes estados:

- **CONCLUÍDO E VALIDADO**;
- **DECIDIDO E DOCUMENTADO**;
- **ADIADO EXPLICITAMENTE**, com destino e razão;
- **NÃO APLICÁVEL**, com justificação.

Nenhum item desaparece por omissão.

## Rastreabilidade

A matriz do plano fonte continua válida, com estas correções:

- todos os 16 pontos de `v02_erros` permanecem representados;
- todos os blocos adicionais permanecem representados;
- A6, A7.1 e parte atual de A5 entram no ciclo V0.2;
- A1–A4, restante A5, restante A7 e A8 ficam preservados para V0.3;
- B2 e B8 passam a obrigatórios antes da V0.3;
- tag/fecho passam para B11.

---

# Anexo A — Plano fonte preservado integralmente

O conteúdo abaixo é o plano fornecido pelo utilizador em 2026-10-05. É preservado integralmente para garantir que nenhuma informação, nuance, requisito, matriz ou justificação se perde. Quando houver diferença entre o anexo e as regras acima, as correções canónicas deste cabeçalho governam a execução, mas o texto original permanece para rastreabilidade.

---

# BolsaNext — Plano consolidado pré-V0.3

Documento de trabalho para sessões com o Claude Code.
Elaborado em 2026-10-05, a partir de verificação direta do repositório.

---

## Como usar este ficheiro

Este documento substitui integralmente as duas listas anteriores: os 16 pontos do
`v02_erros.txt` e os 11 blocos da análise inicial. Não uses nenhum dos dois em
paralelo com este, porque havia seis sobreposições entre eles e um agente que os
leia aos dois faz o mesmo trabalho duas vezes, de formas diferentes.

O trabalho está dividido em três faixas:

- **Faixa A — Decisões.** Nenhum ficheiro `.py` é tocado. O produto é texto nos
  documentos canónicos. É a especificação da V0.3.
- **Faixa B — Saneamento do código.** Por ordem. A ordem importa e está
  justificada em cada sessão.
- **Faixa C — V0.3.** Referência apenas. Não executar neste ciclo.

Cada sessão da Faixa A e B é um bloco independente para colar no Claude Code.
Antes de cada bloco, cola sempre a **Sessão 0**, porque uma sessão nova não se
lembra da anterior.

No fim do ficheiro há uma matriz de rastreio que diz onde foi parar cada ponto
das listas antigas, para confirmares que nada se perdeu.

---

## Estado verificado do repositório

Confirmado por execução direta em 2026-10-05, não por leitura.

**Git.** A `main` está em `d4bbe11` "feat: complete V0.2 market data". A `dev`
está em `cbad3d7` "chore: sync dev with validated main", que é um commit de
merge com dois pais. O conteúdo das duas branches é idêntico, o diff é vazio.
A `dev` está 24 commits à frente da `main` em histórico e zero em conteúdo. O
`d4bbe11` tem como pai o `72e38cb`, que já era um commit de `dev`, por isso a
`main` ficou com o histórico intermédio de `dev` lá dentro e não com o commit
único que o `AGENTS.md` descreve. Não existem tags no repositório.

**Testes.** 39 testes, todos a passar, 1,7 segundos. Cobertura global 55%. A
camada `ui/` tem 0% de cobertura em `widget.py` (151 linhas), `universe_widget.py`
(92 linhas), `window.py` (39 linhas) e `workers.py` (22 linhas).

**Histórico.** Limpo. Nenhum ficheiro pessoal, gerado, cache, log ou base de
dados em nenhum commit de nenhuma branch.

**Integridade SQLite.** `PRAGMA foreign_keys` está a `0`. Uma inserção manual em
`watchlist_items` com `instrument_id = 9999`, inexistente, foi aceite sem erro.
Os `ondelete="CASCADE"` dos modelos não estão a ser aplicados. O `busy_timeout`
já está em 5000 ms por omissão do driver.

**Camadas.** Três importações de `app` para `infrastructure`:
`market_service.py`, `universe_service.py` e `watchlist_service.py`. O domínio
não importa de `app` nem de `infrastructure`. A `ui` não importa de
`infrastructure`. Há uma única fronteira violada.

**Versões.** Quatro fontes independentes: `pyproject.toml` diz `0.1.0`,
`src/bolsa/__init__.py` diz `__version__ = "0.1.0"`, o User-Agent do provider
Wikipedia diz `BolsaNext/0.1`, e `window.py` tem a string `"V0.2 — Market Data"`
escrita à mão.

**Dependências.** `scikit-learn`, `matplotlib` e `PyYAML` não aparecem numa única
linha de `src/` ou `tests/`. Só existem nos metadados do pacote.

**Moedas.** `Instrument(ticker="TEST", currency="GBp").currency` devolve `'GBP'`.

**Tickers.** O regex `^[A-Z0-9.^=_-]+$` aceita `"..."`, `"^^^^"`, `"-"` e 32
hífenes seguidos.

---

# SESSÃO 0 — Contexto e regras permanentes

> Cola este bloco no início de **todas** as sessões, antes do bloco de trabalho.

```
Projeto: BolsaNext (f2432/BolsaNext). Trabalhamos na branch dev.
Fala comigo sempre em português de Portugal.

Antes de tocares em código, lê por esta ordem: README.md, AGENTS.md,
docs/status.md, docs/architecture.md, docs/roadmap.md, docs/development.md,
docs/ai-roadmap.md, docs/legacy.md. São fontes canónicas e a hierarquia entre
elas está definida no AGENTS.md.

Depois corre `pytest -q` e confirma o estado de partida. Devem passar 39 testes.
Se não passarem, para e diz-me antes de fazeres fosse o que fosse.

Estamos num ciclo de saneamento técnico e de definição de regras, antes de
iniciar a V0.3 Portfolio. NÃO inicies a V0.3. NÃO crias Transaction, Position,
Portfolio nem PortfolioService. NÃO acrescentes funcionalidades. NÃO
refactorizes nada que não esteja explicitamente no bloco desta sessão.

Regras obrigatórias, válidas em todas as sessões:

1. Commits pequenos e atómicos, um por correção, mensagem convencional
   (fix:, feat:, test:, docs:, chore:, refactor:). Nunca um commit grande.
2. Cada alteração de comportamento entra com teste na mesma alteração. Se achares
   que algo não é testável, dizes porquê antes de o fazeres.
3. `pytest -q` tem de passar depois de cada commit. Se partir, paras e corriges
   antes de seguir.
4. Nunca fazes push para main. Nunca fazes force push. Trabalhas em dev e só
   fazes push quando eu disser.
5. Nenhum dado pessoal, posição real, extrato, log, cache ou base de dados entra
   no Git. Verificas `git status` antes de cada commit.
6. Se encontrares um problema que não está no bloco desta sessão, PARAS,
   descreves e esperas por mim. Não corriges por iniciativa própria.
7. Quando uma alteração mudar comportamento documentado, atualizas o documento
   canónico correspondente no mesmo commit.
8. Sempre que o bloco disser "propõe e espera", apresentas opções com prós e
   contras e PARAS. Não implementas a tua preferência sem eu responder.
9. No fim da sessão, mostras o diff resumido, o resultado dos testes e a lista
   de commits, e esperas pela minha validação.

Confirma que leste tudo e diz-me o estado de partida antes de começares.
```

---

# FAIXA A — Decisões

Nenhum ficheiro `.py` é tocado em toda a Faixa A. O produto são secções novas nos
documentos canónicos. Esta faixa é a especificação da V0.3 e é o que destranca
tudo o resto. É também a mais rápida, porque não há testes a correr.

Podes dar as sessões A1 a A9 numa só sessão longa ou separadas. Recomendo
separadas a partir de A2, porque cada uma exige decisões tuas.

---

## A1 — Âmbito da V0.3 e o que fica deliberadamente de fora

```
Sessão A1. Trabalho de documentação apenas. Não escreves código.

Objetivo: fixar por escrito o âmbito da V0.3 Portfolio, para não construirmos um
sistema contabilístico completo por acidente.

Escreve em docs/architecture.md uma secção nova "Âmbito da V0.3 — Portfolio" e
reflete o resumo em docs/roadmap.md e docs/status.md.

DENTRO do âmbito da V0.3:
- investimentos long-only simples, inicialmente ações e ETFs;
- transações do tipo BUY e SELL;
- quantidade, preço, comissão, moeda, câmbio;
- posição calculada a partir das transações;
- custo médio ponderado;
- PnL realizado e PnL não realizado;
- consulta do ledger completo de transações;
- recálculo integral da posição a partir do zero, a qualquer momento;
- persistência e recuperação.

FORA do âmbito da V0.3, salvo decisão posterior explícita:
- short selling e margem;
- opções, futuros, CFDs;
- impostos e lotes fiscais;
- dividendos automáticos (ver a ressalva abaixo);
- splits, fusões, spin-offs e outras corporate actions automáticas;
- juros;
- depósitos e levantamentos de caixa;
- integração direta com brokers;
- execução de ordens.

Ressalvas que quero discutidas nesta sessão, não decididas por ti:

R1. Dividendos. Excluir o tratamento automático faz sentido. Mas um tipo de
    transação DIVIDEND registado manualmente custa quase nada e, sem ele, o
    retorno de qualquer posição que pague fica errado desde o primeiro dia.
    Dá-me a tua opinião sobre incluir o tipo e a soma simples, sem automatismo,
    e espera pela minha decisão.

R2. Corporate actions. Excluir splits sem mitigação repete o erro do projeto
    anterior: um split acontece quer o software o preveja ou não, e a partir
    desse dia a posição calculada deixa de corresponder à realidade em silêncio.
    Quero uma de duas mitigações, e quero que me argumentes qual preferes:
    (a) um tipo de transação de ajuste manual que me permita corrigir quantidade
        e custo sem inventar uma compra falsa;
    (b) uma verificação de divergência que compare a posição calculada com uma
        referência e me avise.
    Espera pela minha decisão.

R3. TransactionType tem de ser desenhado para crescer. Documenta que o
    enumerado poderá vir a incluir DIVIDEND, FEE, SPLIT, ADJUSTMENT, CASH_IN e
    CASH_OUT, mesmo que a V0.3 implemente apenas os que eu decidir. Não
    implementes nenhum agora.

O critério de fecho da V0.3 fica escrito assim: um Portfolio simples,
matematicamente correto, persistente, recuperável, testado, e capaz de
representar fielmente compras e vendas reais sem inventar mecanismos
financeiros desnecessários.
```

---

## A2 — Regras contabilísticas e o invariante do ledger

```
Sessão A2. Documentação apenas. Não escreves código.

Objetivo: escrever as regras contabilísticas do Portfolio por extenso, com
exemplos numéricos exatos, antes de existir uma linha de código financeiro. Não
quero comportamento financeiro decidido implicitamente durante a programação.

PARTE 1 — O invariante. Esta é a parte mais importante da sessão.

Escreve em docs/architecture.md, como regra dura e não como funcionalidade:

  "O ledger de transações é a única origem da verdade. Transações nunca são
   agregadas, colapsadas, substituídas nem reescritas. Posições, custo médio e
   PnL são SEMPRE recalculados integralmente a partir do ledger, nunca
   atualizados incrementalmente."

A razão tem de ficar escrita: em Portugal a mais-valia realizada apura-se por
FIFO, e a V0.3 vai usar custo médio ponderado. Enquanto o ledger estiver intacto,
mudar de custo médio para FIFO mais tarde é recalcular. Se alguma vez se
guardar estado agregado, a decisão passa a ser irreversível e os números deixam
de poder ser reconciliados com o extrato do broker.

Documenta também que custo médio é a representação da POSIÇÃO, e que o método de
apuramento do PnL REALIZADO é uma decisão separada que a V0.3 toma como custo
médio mas que não fica fechada para sempre.

PARTE 2 — As regras, com exemplos exatos.

Escreve e confirma a aritmética de cada um:

- Compra. 10 unidades a 100 EUR com comissão de 5 EUR produz custo total 1005 EUR
  e custo unitário efetivo 100,50 EUR. A comissão de compra AUMENTA o custo da
  posição.
- Reforço. Segunda compra de 10 unidades a 120 EUR com comissão de 5 EUR eleva o
  custo acumulado para 2210 EUR e o custo médio das 20 unidades para 110,50 EUR.
- Venda parcial. Tem de ficar explícito como se calcula o custo atribuído às
  unidades vendidas, o produto líquido da venda e o PnL realizado. A comissão de
  venda REDUZ o valor recebido.
- Encerramento. Quando a posição chega a zero, o custo médio anterior deixa de
  influenciar qualquer compra futura. Uma nova entrada começa do zero.
- Sentido. quantity é SEMPRE positiva. O sentido vem de type=BUY/SELL. Não
  quero quantidades negativas misturadas com tipos.
- Sem short. Não é possível vender mais unidades do que as existentes. Define o
  que acontece quando se tenta: erro de domínio, qual, e com que mensagem.

PARTE 3 — Lacunas que nenhuma lista anterior cobriu e que decidimos aqui.

L1. Semântica da data da transação. Data de execução ou data de liquidação? Em
    que fuso horário é guardada e em que fuso é apresentada? Isto decide a
    ordenação do FIFO futuro, decide em que ano fiscal cai uma venda e decide se
    os meus números batem certo com o extrato da XTB. Dá-me opções e espera.

L2. Desempate de transações com o mesmo instante. Se duas transações partilham
    timestamp, a ordem entre elas tem de ser determinística, senão o custo médio
    e o PnL realizado mudam conforme a ordem em que a base as devolve. Propõe um
    critério secundário estável e espera pela minha decisão.

PARTE 4 — Testes. Não os escreves nesta sessão, mas deixas escrito em
docs/development.md que cada regra acima tem de ter teste numérico com resultado
exato antes de existir qualquer interface gráfica de Portfolio.
```

---

## A3 — Tipos numéricos e precisão

```
Sessão A3. Documentação apenas. Não escreves código.

Objetivo: decidir a representação dos valores financeiros antes de existirem
colunas na base de dados, porque mudar isto depois é migração com dados reais
lá dentro.

Decisão de partida, a confirmar comigo: Decimal no domínio financeiro e
Numeric(precision, scale) na persistência. Nunca float como representação
canónica de dinheiro, quantidade, comissão, câmbio ou PnL.

Fica explícito que dados de mercado e cálculos estatísticos CONTINUAM em float,
pandas e NumPy, porque é aí que esses tipos fazem sentido. A fronteira entre os
dois mundos tem de estar documentada: onde se converte, em que direção, e quem
é responsável pela conversão.

O que quero decidido e escrito:

1. Precisão e escala para cada campo: price, quantity, commission, fx_rate e
   valores monetários derivados. Dá-me propostas concretas com justificação, não
   números arbitrários.
2. Quantidade tem de suportar ações fracionadas, mesmo que eu não as use já. O
   projeto anterior morreu exatamente aqui, com quantidades inteiras
   incompatíveis com a XTB.
3. Política de arredondamento: em que pontos se arredonda, quantas casas se
   preservam internamente, quantas se apresentam. Um valor gravado, carregado e
   recalculado tem de manter consistência.
4. Os testes de domínio comparam Decimal diretamente. Nada de tolerâncias de
   vírgula flutuante quando se valida dinheiro. Deixa isto escrito em
   docs/development.md.

Escreve o resultado em docs/architecture.md, numa secção "Tipos financeiros e
precisão".
```

---

## A4 — Convenção de câmbio

```
Sessão A4. Documentação apenas. Não escreves código.

Objetivo: fixar o significado matemático de fx_rate antes de existir código que
o use. Esta é a decisão onde estes sistemas falham mais vezes.

Convenção proposta, a confirmar comigo:

  1 unidade da moeda da transação = fx_rate unidades da moeda base.

Exemplo a documentar: numa carteira em EUR, uma compra de 1000 USD com
fx_rate = 0,86 custa 860 EUR na moeda base. Confirma a aritmética.

Regra dura a escrever: a direção do câmbio NUNCA é inferida pelo nome da
variável nem pelo nome do símbolo. É sempre explícita.

O que quero decidido e escrito:

1. A convenção acima, documentada junto do domínio e não só na architecture.
2. A separação clara entre o câmbio histórico da transação, que é imutável, e o
   câmbio atual usado para valuation, que muda todos os dias. O PnL em moeda
   base resulta dos dois efeitos: variação do ativo na sua moeda e variação da
   moeda face à base. Documenta isto com um exemplo numérico.
3. Decide comigo se a V0.3 consegue apresentar valor atual em moeda base ou se
   declara explicitamente que ainda não consegue. As duas respostas são
   aceitáveis. O que não é aceitável é apresentar um total que parece válido e
   não é.
4. Se a resposta for que consegue, então é preciso uma fonte de cotações FX. Não
   existe nenhuma no projeto e não está em nenhuma versão do roadmap até à V1.0.
   Propõe: um provider próprio de câmbio, ou símbolos Yahoo do tipo EURUSD=X
   através do MarketDataProvider existente. Se for a segunda, a inversão da
   cotação tem de ser tratada de forma explícita e testada. Argumenta e espera
   pela minha decisão.
5. Se a resposta for que não consegue, então escreve em docs/roadmap.md em que
   versão passa a conseguir e o que é preciso para lá chegar.
```

---

## A5 — Propriedade da moeda base

```
Sessão A5. Documentação apenas. Não escreves código.

Problema. AppConfig tem base_currency = "EUR". A arquitetura prevê que cada
Portfolio tenha também base_currency. Quando existir um Portfolio persistido, só
uma das duas pode ser a origem da verdade.

Solução proposta, a confirmar comigo: a configuração passa a chamar-se
default_base_currency e serve apenas como valor inicial ao criar uma carteira
nova. Depois de criada, Portfolio.base_currency é a autoridade.

Consequências que têm de ficar escritas:

1. Alterar a configuração global NUNCA altera carteiras existentes,
   silenciosamente ou não.
2. Duas carteiras com moedas base diferentes, uma EUR e outra USD, têm de poder
   coexistir.
3. A moeda base de um Portfolio não é alterável sem uma operação explícita que
   considere as implicações nos dados já existentes. Documenta que implicações
   são essas.

Reflete o princípio em docs/architecture.md, no modelo de dados, e nota em
docs/status.md que a renomeação de AppConfig.base_currency fica agendada para a
Faixa B. Não a faças agora.
```

---

## A6 — Semântica de `market` e proveniência dos metadados

```
Sessão A6. Documentação apenas. Não escreves código.

Problema. Instrument.market contém hoje valores de naturezas diferentes
conforme a origem: "US" vindo do universo S&P 500, "NASDAQ" vindo do universo
NASDAQ 100, nomes de praça como AMSTERDAM ou PARIS vindos da coluna "Main
listing" do Euronext 100, e fullExchangeName vindo do Yahoo. Isto mistura
região, bolsa e praça de cotação.

Enquanto é informação visual não faz mal. Na fase de Portfolio, Analysis e
Research estes valores vão ser usados para filtros, exposição por mercado e
regras específicas, e aí a mistura passa a produzir números errados.

O que quero decidido:

1. O que significa market. Bolsa / exchange / listing venue, do tipo NASDAQ,
   NYSE, XPAR, XAMS? Ou região geográfica, do tipo US, EU? Se forem precisos os
   dois conceitos, então são dois campos distintos e não um. Dá-me as opções com
   consequências e espera.

2. Proveniência e prioridade dos metadados. Proposta a confirmar: o Yahoo é a
   fonte principal dos metadados de instrumento; os universos são fonte apenas
   para a composição do índice e nunca para moeda ou mercado. Se mantivermos
   metadados de várias origens, tem de ficar documentado qual vence e porquê.

3. Problema associado. O refresh_metadata atual não atualiza um instrumento se
   nome, mercado e moeda já estiverem preenchidos, mesmo quando market = "US" é
   um valor pouco preciso trazido do universo. Define a regra: o que conta como
   metadado por confirmar, e quando é que o botão "Atualizar dados" deve
   substituir um valor existente.

Escreve o resultado em docs/architecture.md. A implementação fica para a Faixa B,
na sessão B8.
```

---

## A7 — Backup, exportação, importação e duplicados

```
Sessão A7. Documentação apenas. Não escreves código.

Objetivo: definir a política antes de a base deixar de ser descartável. A partir
do momento em que houver transações reais, perder a base é perder trabalho que
não se recupera.

O que quero decidido e escrito em docs/architecture.md e docs/development.md:

1. Backup. Não quero um sistema automático complexo. Quero garantia de cópia da
   base antes de qualquer operação destrutiva, migração de schema ou importação
   relevante, e uma forma documentada de restaurar. Propõe o mecanismo mais
   simples que cumpra isto.

2. Formato de exportação. Um formato canónico próprio do BolsaNext, completo o
   suficiente para reconstruir uma carteira do zero. Não quero adaptadores para
   brokers nesta fase. Primeiro um formato sólido nosso; a partir dele, no
   futuro, adaptadores para XTB, Degiro, IBKR e CSV externos.

3. Importação atómica. Validação antes de gravar, e tudo dentro de uma única
   transação de base de dados: ou entra tudo, ou não entra nada.

4. Duplicados. Importar o mesmo ficheiro duas vezes não pode criar duas cópias
   das mesmas compras. Propõe o mecanismo: campo source, external_id, ou
   fingerprint determinístico da transação. Dá-me prós e contras de cada um,
   incluindo o que acontece quando duas transações legítimas são genuinamente
   idênticas em todos os campos. Espera pela minha decisão.

5. Relatório de importação. Tem de dizer o que foi inserido, o que foi ignorado
   por já existir, e o que foi rejeitado por inválido, com a razão.

A implementação é V0.3. Esta sessão só produz a especificação.
```

---

## A8 — Reconciliação com o broker e política pessoal

```
Sessão A8. Documentação apenas. Não escreves código.

Duas lacunas que não estão em nenhuma versão do roadmap e que são a razão de ser
do projeto.

LACUNA 1 — Reconciliação com o extrato da XTB.

A V0.3 prevê "importação e exportação", que é mecânica de ficheiros. Não prevê o
passo que interessa: comparar o estado calculado pela aplicação com o extrato
real do broker e sinalizar divergências. Sem isso, a aplicação é uma verdade
paralela ao broker, que é exatamente o problema que o portfolio.csv do projeto
anterior tinha.

Quero decidido:
- se a reconciliação entra na V0.3 ou numa versão própria;
- o que é comparado: posições, quantidades, custo, PnL realizado, ou tudo;
- o que acontece quando diverge: aviso, relatório, bloqueio;
- que tolerância é aceitável, se alguma.

Escreve o resultado em docs/roadmap.md como item explícito.

LACUNA 2 — Política pessoal de investimento.

Objetivo financeiro principal, horizonte temporal dominante, capital disponível
para a experiência, limite máximo por posição, regras de reforço e de venda,
liquidez mínima, utilização admissível de produtos alavancados.

Nenhuma destas decisões está em nenhuma versão do roadmap, da V0.1 à V1.0. A
V0.7 Research cobre a tese por ativo, que é outra coisa: é análise de um ativo,
não regra de carteira. Sem a política, a V0.3 calcula números que não se comparam
com nada e a V0.6 otimiza estratégias sem restrição de risco.

Quero decidido:
- se a política pessoal fica num documento próprio do repositório, e com que
  nome;
- em que versão a aplicação passa a validar a carteira contra ela;
- se as regras ficam legíveis por código ou apenas em texto nesta fase.

NOTA IMPORTANTE: o conteúdo da política é meu e não teu. Não preenchas valores.
Cria a estrutura, as perguntas e o sítio onde vivem, e deixa-me responder.
```

---

# FAIXA B — Saneamento do código

Por esta ordem. A ordem está justificada em cada sessão e não deve ser alterada
sem razão.

---

## B1 — Ports e direção das dependências

> **Porquê primeiro.** Esta sessão define onde vivem os contratos e os erros.
> Tudo o que vem a seguir mexe neles. Feita depois, obriga a mover duas vezes o
> que as sessões B2 e B3 vão escrever. É uma refatoração pequena, três
> importações e dois ficheiros a mudar de sítio, e está coberta pelos testes
> atuais.

```
Sessão B1. Corrigir a direção das dependências arquiteturais.

Problema confirmado. A documentação diz que UI, Application, Domain e
Infrastructure são separadas, mas existem três importações de Application
diretamente para Infrastructure:

- app/services/market_service.py importa MarketDataProvider de
  infrastructure.market_data.provider
- app/services/universe_service.py importa UniverseProvider de
  infrastructure.market_data.universe_provider
- app/services/watchlist_service.py importa MarketDataError de
  infrastructure.market_data.errors

Confirma tu mesmo com grep antes de alterares.

Boa notícia que também confirmei: o domínio não importa de app nem de
infrastructure, e a ui não importa de infrastructure. Há uma única fronteira
violada e é a mais fácil de corrigir.

O padrão correto já existe no próprio projeto: WatchlistRepository está definido
como Protocol dentro da aplicação e implementado pela infraestrutura. É esse o
padrão a generalizar.

O que quero:

1. Propõe-me a localização dos ports e espera pela minha validação do desenho
   antes de mexeres. A minha inclinação é app/ports/market_data.py,
   app/ports/universe.py e app/ports/repositories.py, mas quero a tua opinião,
   incluindo se os Protocols devem ficar agrupados ou um por ficheiro.

2. Decide comigo onde vivem os erros que fazem parte do contrato. MarketDataError
   e família são hoje de infraestrutura, mas a aplicação precisa de os conhecer
   sem depender do adapter concreto. Argumenta entre pô-los nos ports, no
   domínio, ou num módulo de erros partilhado.

3. Depois de eu decidir, executa. A Application conhece os contratos. A
   Infrastructure fornece as implementações: YFinanceMarketDataProvider,
   WikipediaUniverseProvider, CachedUniverseProvider,
   SqlAlchemyWatchlistRepository.

4. Comportamento preservado na íntegra. Os 39 testes têm de continuar a passar
   sem alteração de lógica. Ajustar importações nos testes é aceitável; alterar
   asserções não é, e se precisares de alterar alguma, paras e dizes-me.

5. Isto tem de estar feito ANTES de criarem PortfolioRepository e
   TransactionRepository, para não repetirmos o padrão inconsistente em mais
   quatro sítios.

6. Atualiza a secção de regras de arquitetura de docs/architecture.md para
   descrever o padrão de ports e adapters com os caminhos reais.
```

---

## B2 — Taxonomia de erros unificada

> **Porquê aqui.** Os erros de universos e os erros de preço atual são o mesmo
> problema aplicado a dois sítios, e ambos assentam na decisão de localização
> tomada em B1. Tratados em conjunto resultam numa taxonomia coerente; tratados
> em separado resultam em duas famílias com filosofias diferentes.

```
Sessão B2. Unificar o tratamento de erros previsíveis.

Contexto. docs/architecture.md tem uma secção "Política de erros de Market Data"
que define MarketDataError, InstrumentNotFoundError e MarketDataUnavailableError,
e diz que a UI não interpreta exceções internas do fornecedor. Essa política está
bem desenhada mas só cobre metade do sistema.

PARTE 1 — Universos.

wikipedia_universe_provider.py levanta RuntimeError genérico quando o download
falha. Se a página mudar de formato, _find_constituents_table levanta ValueError
e _table_to_instruments também. Nada disto está na taxonomia. A UI acaba a
mostrar str(exc) ao utilizador através do sinal failed do FunctionThread.

Quero uma família de erros para universos que distinga pelo menos:
- universo pedido não suportado;
- fonte não contactável (rede, timeout, HTTP);
- fonte respondeu mas o conteúdo não é interpretável (tabela não encontrada,
  colunas mudaram, zero instrumentos válidos).

Decide comigo se essa família herda de MarketDataError ou é hierarquia paralela.
Universos não são exatamente market data. Argumenta e espera.

Nenhuma exceção da urllib ou do pandas pode sair do provider.

A UI passa a produzir mensagens diferentes conforme o tipo. Falha de rede é
acionável por mim; formato mudado é problema do projeto e tem de o dizer, para
eu perceber que tenho de ir ver a fonte.

PARTE 2 — Preço atual.

get_current_price() devolve None para praticamente qualquer problema. Para uma
Watchlist chega. Para uma carteira não chega, e a V0.3 está à porta.

Precisamos de distinguir pelo menos:
- não existe cotação válida neste momento;
- o fornecedor está indisponível ou houve erro de rede;
- o ticker não é reconhecido.

A razão é concreta: um Portfolio não pode apresentar um valor total que parece
válido quando uma das posições não pôde ser avaliada. A aplicação tem de
conseguir dizer que determinado total ou PnL está parcial.

Isto não significa transformar a UI num painel de erros. As falhas podem
continuar a ser tratadas de forma discreta. O que muda é que o domínio e a
aplicação passam a saber POR QUE RAZÃO não existe preço.

Propõe-me o desenho: tipos de resultado, exceções específicas, ou um objeto de
resultado com estado. Argumenta contra a regra de camadas e espera pela minha
decisão.

O contrato de Market Data tem de ficar coerente entre histórico, metadados e
preço atual. Hoje não está: histórico e metadados levantam exceções tipadas,
preço devolve None.

PARTE 3 — Fallback da cache de universos.

Hoje, se a cache expirou, o CachedUniverseProvider vai à fonte e, se a fonte
falhar, o erro propaga e eu fico sem nada, mesmo tendo uma cache de 25 horas no
disco. Propõe uma política de fallback degradado, com aviso explícito de que os
dados são antigos e de que instante são. Espera pela minha decisão.

PARTE 4.

Testes para cada tipo de erro, com a fonte simulada. Nenhum teste pode depender
de rede. Atualiza a secção de política de erros de docs/architecture.md para
cobrir universos e preço atual.
```

---

## B3 — Moedas em subunidade

> **Porquê aqui.** É o único problema da lista toda que produz números errados.
> Hoje o impacto é um rótulo errado, porque ainda não se calcula nada, mas tem
> de estar resolvido antes de existir qualquer cálculo de PnL. A sobreposição
> com B1 é mínima, o provider só muda a linha de importação.

```
Sessão B3. Corrigir o tratamento de moedas em subunidade.

Problema confirmado. Em domain/instruments/instrument.py, o __post_init__ valida
a moeda com len(currency) == 3 and currency.isalpha() e faz .upper(). O Yahoo
devolve códigos de subunidade onde a letra minúscula final é significativa:

- GBp = pence esterlinos, 1/100 de GBP. Devolvido para praticamente todas as
  ações cotadas em Londres.
- ZAc = cêntimos de rand sul-africano, 1/100 de ZAR.
- ILA = agorot israelitas, 1/100 de ILS.

Verifica tu mesmo antes de alterar:

    Instrument(ticker="TEST", currency="GBp").currency

Devolve 'GBP'. São duas moedas diferentes com um fator de 100 entre elas. Na V0.3
isto é uma posição de Londres a valer cem vezes mais do que vale, com a origem do
erro invisível.

O que quero:

1. Uma tabela explícita de moedas de subunidade na camada de domínio, com moeda
   principal e fator. Começa com GBp->GBP (100), ZAc->ZAR (100), ILA->ILS (100).
   Tem de ser facilmente extensível e a comparação tem de ser SENSÍVEL a
   maiúsculas e minúsculas, porque é aí que está a informação.

2. O Instrument guarda sempre a moeda principal normalizada. Não quero GBp na
   base de dados nem na UI.

3. O instrumento tem de preservar a informação de que os preços do fornecedor
   para esse ticker vêm em subunidade, porque é isso que permite dividir. Propõe
   onde vive: um campo novo no Instrument, ou responsabilidade do adapter de
   market data que devolve preços já na moeda principal. Argumenta as duas
   opções contra a regra de camadas e contra a decisão de ports tomada em B1.
   Espera pela minha escolha.

4. Depois de eu escolher: os preços de get_current_price e as colunas de preço de
   get_historical_data (Open, High, Low, Close, Adj Close) passam a ser
   convertidos para a moeda principal. O Volume NUNCA é dividido.

5. Mapa de sufixos do provider de universos. _currency_for_ticker não tem ".L"
   (Londres) e tem ".DE", que é XETRA e não Euronext. Corrige: acrescenta ".L"
   com a moeda correta face à decisão do ponto 3, e revê se ".DE" deve continuar
   num provider de Euronext. Teste para cada sufixo do mapa.

6. Testes obrigatórios:
   - normalização de GBp, ZAc e ILA;
   - EUR, USD e outros códigos normais não são afetados;
   - código inválido continua a ser rejeitado;
   - conversão de preço atual com fornecedor falso a devolver GBp;
   - conversão das colunas de preço do histórico, com verificação EXPLÍCITA de
     que o Volume não foi alterado;
   - round-trip de persistência: instrumento em GBp guardado e recarregado da
     base mantém a moeda principal.

7. Secção "Política de moedas" em docs/architecture.md, dizendo explicitamente
   que a moeda guardada é sempre a principal e porquê.
```

---

## B4 — Integridade e configuração do SQLite

> **Porquê aqui.** Tem de estar feito antes de se tirar a revisão base do
> Alembic em B6, senão a base de referência é tirada de um schema com a
> configuração errada.

```
Sessão B4. Aplicar integridade referencial a sério no SQLite.

Problema confirmado por execução, não por leitura. Corre isto e confirma:

    PRAGMA foreign_keys  ->  devolve 0

E depois tenta inserir à mão, com SQL direto, uma linha em watchlist_items com
instrument_id = 9999, que não existe. É aceite sem erro.

Ou seja: os ForeignKey(..., ondelete="CASCADE") que estão em
infrastructure/database/models.py são decorativos. Não estão a ser aplicados.

Hoje é inofensivo porque só o repositório escreve e ele é disciplinado. Na V0.3,
com transactions a apontar para portfolios e instruments, isto é um ledger que
pode ficar com transações órfãs sem ninguém dar por nada. Um ledger financeiro
com integridade referencial desligada não é um ledger.

O que quero:

1. PRAGMA foreign_keys = ON aplicado em TODAS as ligações, não só na primeira.
   O sítio certo é um evento do SQLAlchemy no momento de criação da engine, para
   que nenhuma sessão escape. Propõe a implementação e confirma comigo antes de
   a aplicares.

2. Depois de ligares, corre a suite completa. Se alguma coisa partir, isso é um
   achado e não um problema: significa que já havia escrita a violar integridade.
   Para, mostra-me, e decidimos juntos.

3. busy_timeout. Confirmei que já está em 5000 ms por omissão do driver, por isso
   este sub-ponto é menos urgente do que parece. Confirma tu, e diz-me se achas
   que vale a pena torná-lo explícito em vez de depender de um valor por omissão
   de uma dependência.

4. WAL. Não quero complexidade prematura. Avalia e dá-me a tua opinião sobre se
   faz sentido agora, dado que já existem operações de rede em background, ou se
   deve esperar até existirem leituras e escritas verdadeiramente concorrentes.
   Espera pela minha decisão, não atives por iniciativa própria.

5. Política escrita em docs/architecture.md: foreign keys obrigatórias,
   transações atómicas, rollback em falha.

6. Testes que verifiquem INTEGRIDADE a sério, não apenas a existência das
   tabelas. Quero pelo menos: inserção órfã rejeitada, cascade a funcionar na
   remoção, e rollback a deixar a base no estado anterior.
```

---

## B5 — Localização dos dados da aplicação

> **Porquê aqui.** Tem de estar resolvido antes do Alembic em B6, senão a
> revisão base aponta para um sítio que vais mudar logo a seguir.

```
Sessão B5. Tornar a localização dos dados independente do diretório de trabalho.

Problema. config.py tem data_dir = Path("data"), relativo. O load_config() faz
mkdir desse caminho. O pyproject declara [project.scripts] bolsanext e o
docs/development.md documenta `bolsanext` como forma normal de arrancar.

Correr `bolsanext` de qualquer pasta que não a raiz do repositório cria uma
pasta data/ nova nesse sítio e uma base vazia. A watchlist parece ter
desaparecido. Só não dá problema hoje porque o run.ps1 corre sempre da raiz. Deixa
de ser seguro assim que houver atalhos, instalação do comando, execução a partir
de outro diretório ou distribuição da aplicação.

Segundo problema no mesmo ficheiro: load_config() cria diretórios como efeito
secundário de carregar configuração. Carregar configuração não deve escrever no
disco.

O que quero:

1. Decisão explícita sobre onde vivem os dados, apresentada antes de
   implementares. Opções: pasta de dados do utilizador do sistema operativo, em
   Windows algo sob %LOCALAPPDATA%\BolsaNext; variável de ambiente que sobrepõe;
   ou manter relativo mas resolvido face à raiz do projeto. Prós e contras de
   cada uma, incluindo efeito nos testes e efeito em ter várias cópias do
   repositório clonadas. Espera pela minha decisão.

2. Organização interna da área de dados: base, cache, logs, exports e backups em
   subdiretórios próprios, nunca misturados com o repositório Git. O repositório
   passa a conter apenas código e documentação, mais data/.gitkeep se ainda
   houver razão para manter a pasta. Diz-me se achas que há.

3. Sobreposição obrigatória por configuração ou variável de ambiente, para os
   testes e para eu poder ter uma base separada quando estiver a experimentar.

4. Separar criação de diretórios do carregamento de configuração. Uma função que
   lê, outra que prepara o ambiente, chamada explicitamente no arranque.

5. Transição da base existente. Já existe data/bolsanext.sqlite3 com a minha
   watchlist. Não a ignores. Dá-me três opções com prós e contras: migração
   automática na primeira execução, cópia controlada, ou transição explícita
   única feita por mim. Enquanto a base só contiver Watchlist, o custo de errar é
   baixo, o que torna este o melhor momento para mudar. NÃO MOVAS NADA
   AUTOMATICAMENTE sem eu decidir, e se a decisão implicar que a minha base atual
   fica para trás, diz-mo em texto claro com as instruções do que tenho de fazer.

6. Atualiza docs/development.md e docs/architecture.md com a localização nova e
   a forma de a sobrepor.

7. Testes: caminho resolvido corretamente, sobreposição a funcionar, e
   confirmação de que carregar configuração NÃO cria diretórios.
```

---

## B6 — Migrações de base de dados

> **Porquê aqui.** Depois de B4 e B5, para que a revisão base capture o schema
> já configurado e já na localização definitiva. Antes de B8 e das sessões
> seguintes, que não mexem no schema, e muito antes da V0.3, que mexe.

```
Sessão B6. Introduzir migrações antes de o schema começar a crescer.

Problema. O projeto usa Base.metadata.create_all(engine). Isso cria uma base
vazia mas NÃO evolui uma base existente. A V0.3 vai introduzir pelo menos
portfolios e transactions, e as versões seguintes vão acrescentar colunas,
constraints, índices e entidades. O roadmap deixa migrações para a V1.0, o que
é tarde: chego lá com meses de transações reais e nenhum caminho de migração.

O que quero:

1. Alembic, por já usarmos SQLAlchemy. Se tiveres argumento forte para outra
   coisa, apresenta-o, mas o ónus é teu.

2. A base existente da V0.2 passa a corresponder a uma revisão inicial conhecida.
   A revisão base tem de capturar o schema TAL COMO FICOU depois das sessões B4 e
   B5, não como estava antes. Confirma que essas sessões já foram aplicadas antes
   de gerares a revisão.

3. A partir daí, qualquer alteração estrutural é uma migração versionada.

4. A aplicação tem de distinguir uma base vazia de uma base antiga e elevá-la até
   à revisão atual SEM apagar dados. Propõe o comportamento no arranque: migra
   automaticamente, avisa e espera, ou recusa arrancar. Argumenta e espera pela
   minha decisão.

5. create_all() pode continuar útil em testes e no bootstrap inicial, mas deixa
   de ser o mecanismo oficial de evolução do schema. Deixa isso escrito.

6. Testes de migração, pelo menos para os caminhos que vão ser mesmo usados.
   Inclui pelo menos um teste com ficheiro SQLite temporário real e não
   exclusivamente :memory:, porque o comportamento difere.

7. Documenta em docs/development.md: como criar uma migração nova, como aplicá-la,
   e como verificar qual é a revisão atual da base. Sem isto a sessão não fecha.

8. Antes de qualquer migração que eu venha a correr sobre dados reais, tem de
   existir o backup definido na sessão A7. Se A7 ainda não estiver decidida,
   diz-mo e paramos aqui.
```

---

## B7 — Versão única e tag

```
Sessão B7. Eliminar as quatro fontes de versão e criar uma só.

Problema confirmado. Existem quatro números de versão independentes:

- pyproject.toml diz version = "0.1.0"
- src/bolsa/__init__.py diz __version__ = "0.1.0"
- o User-Agent de wikipedia_universe_provider.py diz "BolsaNext/0.1"
- window.py tem a string "V0.2 — Market Data" escrita à mão na barra de estado

E a documentação declara a V0.2 concluída. Nunca devemos ter três números de
versão independentes, quanto mais quatro.

O que quero:

1. Decisão sobre a política, apresentada antes de implementares: a versão do
   pacote acompanha a versão do roadmap, ou são coisas independentes e o roadmap
   usa outra nomenclatura? A minha inclinação é que a V0.2 concluída corresponde
   a 0.2.0. Argumenta e espera.

2. A versão passa a ser definida num ÚNICO local. Os restantes componentes leem-na
   desse local ou do metadata do pacote instalado. Propõe qual dos dois e porquê.

3. O User-Agent usa a versão real, obtida da fonte única.

4. A barra de estado mostra a versão real, sem string duplicada. Decide comigo o
   que mostra: só a versão, ou versão mais nome da fase.

5. Tag Git v0.2.0. Tem de apontar para o commit estável que queremos conservar
   como referência. Nota importante: a main está em d4bbe11 e o conteúdo é
   idêntico ao da dev, por isso o commit certo a marcar é o d4bbe11. Confirma
   isso antes de criares a tag, e NÃO a crias nem a publicas sem eu autorizar.

6. Uma release GitHub é opcional. A tag é que importa.

7. Política de versões escrita em docs/development.md, dizendo o que acontece
   durante o desenvolvimento da V0.3: versão de desenvolvimento superior, ou
   manter a anterior até ao próximo fecho. Decide comigo.
```

---

## B8 — Comportamento e interface

> Esta sessão agrupa cinco correções que partilham ficheiros. Um commit por
> item. Se achares que é demasiado para uma sessão, divide e diz-me onde cortas.

```
Sessão B8. Correções de comportamento na camada de interface e serviços.

B8.1 — Concorrência na Watchlist.

Existem três operações a correr em FunctionThread: _add_ticker
(add_ticker_enriched), _start_metadata_refresh (refresh_metadata) e
_start_price_refresh (rows(refresh_prices=True)). Todas tocam no mesmo objeto de
domínio Watchlist e todas podem escrever na mesma base através de _persist().

O que está errado:
- _start_price_refresh desativa apenas o botão "Atualizar preços". Os botões
  "Remover" de cada linha, o combo de estado e o botão "Atualizar dados" ficam
  todos ativos. Remover um ticker durante uma atualização de preços muta
  self._watchlist.items enquanto a thread o percorre dentro de rows().
- _add_ticker desativa só a caixa de texto e o botão Adicionar.
- _start_metadata_refresh desativa só o próprio botão.
- Logo, duas operações de rede podem correr em simultâneo sobre o mesmo agregado
  e ambas chamam _persist().

Confirmei que a escrita SQLite a partir de outra thread funciona, porque o
SQLAlchemy trata disso. Não rebenta hoje. O padrão é que está errado, e a V0.3
vai multiplicar as operações concorrentes sobre o mesmo agregado.

Quero:
- um mecanismo único de "operação em curso", não três flags independentes;
- enquanto qualquer operação de rede decorre, toda a interação que muta a
  watchlist fica bloqueada, INCLUINDO os widgets dentro das células da tabela,
  que hoje escapam;
- o bloqueio tem de abranger também o UniverseWidget, porque o botão "Adicionar
  selecionado à Watchlist" escreve no mesmo agregado a partir de outro separador.
  Propõe como ligar os dois sem meter lógica de domínio na UI e espera pela minha
  validação do desenho;
- estado visual claro, e nenhum botão permanentemente desativado se a thread
  falhar. O reestabelecimento acontece no sinal finished, incluindo no caminho
  de erro;
- avalia se o WatchlistService deve ganhar um lock próprio em vez de depender da
  disciplina da UI. A minha inclinação é que sim, porque o architecture.md diz
  que a UI não implementa regras, e "não corromper o agregado" é uma regra. Dá-me
  a tua opinião fundamentada e espera;
- teste que exercite acessos concorrentes ao serviço a partir de duas threads e
  confirme estado final coerente sem exceções. Se o lock ficar só na UI, diz-me
  como tencionas testar.

B8.2 — O UniverseWidget reconstrói domínio a partir de texto.

_add_selected lê self._table.item(row, 0).text() e os três seguintes, e passa
strings para watchlist_service.add_ticker(). O objeto Instrument que já existe em
memória, validado, com asset_type, é deitado fora e reconstruído a partir de
texto que passou por uma tabela.

Consequências reais: o asset_type perde-se, e o mesmo ticker fica com metadados
diferentes conforme o caminho de entrada. Isto viola a regra do architecture.md
de que a UI não constrói domínio.

Quero:
- o UniverseWidget guarda os objetos Instrument do universo carregado e passa o
  objeto, não texto. A tabela passa a ser só apresentação;
- o WatchlistService ganha forma de aceitar um Instrument já construído, distinta
  de add_ticker(ticker, name=..., market=...), mantendo a validação de duplicados;
- aplica aqui a decisão de proveniência de metadados tomada na sessão A6. Não
  decidas de novo, consulta o que ficou escrito em docs/architecture.md;
- aplica também a decisão de moeda da sessão B3. A moeda adivinhada por sufixo
  entra exatamente por aqui, e as duas correções têm de ser coerentes;
- testes: adicionar por universo preserva ticker, nome, mercado, moeda e
  asset_type; duplicado continua rejeitado; round-trip na base mantém asset_type.

B8.3 — Preços perdidos ao mudar de separador.

O currentChanged do QTabWidget em window.py chama watchlist_widget.refresh(), que
chama rows() sem refresh_prices, devolve price=None e a coluna volta a "—".
Resultado: atualizas preços, vais aos Universos, voltas, perdeste-os.
A decisão do status.md de não persistir preço mantém-se e não quero contrariá-la
na base. O que quero é que o último preço sobreviva em memória durante a sessão.

Quero:
- últimos preços conhecidos em memória, com o instante em que foram obtidos.
  Decide comigo onde: no widget, ou no WatchlistService como cache de sessão. Se
  for no serviço, não pode ser persistido nem escrito na base;
- ao reconstruir a tabela sem atualizar preços, mostra o último preço conhecido.
  Um ticker nunca atualizado continua a mostrar "—";
- forma discreta de distinguir preço fresco de preço antigo, por exemplo a hora
  da última atualização na barra de estado. Nada de indicadores complicados;
- ticker removido não deixa preço na cache; ticker adicionado entra sem preço;
- testes: guarda, lê, remoção limpa a entrada, e confirmação explícita de que
  nada disto chega à base de dados.

B8.4 — Validação sintática de tickers.

O regex é ^[A-Z0-9.^=_-]+$. Confirma que aceita "...", "^^^^", "-" e 32 hífenes
seguidos. Aceita. O status.md descreve isto como "validação sintática de tickers",
o que não corresponde ao que existe. Quero que o código cumpra o que o documento
promete, não o contrário.

Quero:
- pelo menos um carácter alfanumérico obrigatório;
- não começar nem acabar com separador (ponto, hífen, underscore). O circunflexo
  inicial continua válido porque identifica índices no Yahoo;
- sem separadores repetidos consecutivamente;
- sem partir nenhum formato já suportado. Confirma com: ^GSPC, BRK-B, EURUSD=X,
  ASML.AS, BRK.B antes da normalização, 005930.KS, RDS-A, BTC-USD, GC=F;
- manter o limite de 32 caracteres e a rejeição de espaços e vazio;
- testes parametrizados com lista de válidos e lista de inválidos. Quero ver o
  teste a falhar com o regex antigo antes de o corrigires, para confirmar que
  está mesmo a testar.

B8.5 — Combo de estado com índice -1.

_render_rows faz state_combo.setCurrentIndex(state_combo.findData(row.state.value)).
Se o valor não for encontrado, findData devolve -1 e a célula fica em branco sem
aviso nenhum. Ou garantes que é impossível por construção, ou registas aviso no
log e assumes um estado por omissão visível. Diz-me qual escolhes e porquê.
```

---

## B9 — CI, dependências e qualidade estática

```
Sessão B9. Aproximar a validação automática da realidade de utilização.

B9.1 — Matriz de sistemas operativos.

Eu desenvolvo e valido em Windows. O CI corre só em ubuntu-latest. Toda a
validação da V0.2 assenta em sessões manuais em Windows e nada automático cobre
essa plataforma.

Acrescenta windows-latest à matriz. É gratuito em repositórios públicos. Confirma
que os testes passam lá, em especial os de preferências de tabela, que tocam em
QSettings, e tudo o que envolva caminhos de ficheiros, sobretudo depois das
alterações da sessão B5. Se algum falhar em Windows, isso é um ACHADO e não um
problema do CI: para, mostra-me, e corrigimos.

B9.2 — Testes em pull requests para dev.

O workflow corre em pushes para main e dev, mas pull requests só para main.
Acrescenta pull_request para dev.

B9.3 — Cobertura visível.

Acrescenta pytest-cov ao CI, apenas para dar visibilidade. NÃO imponhas um limiar
de percentagem nesta fase. Quero ver o número evoluir, não quero um portão
artificial que me obrigue a escrever testes maus para passar.

B9.4 — Política de versões das dependências.

O pyproject não tem uma única restrição de versão. O yfinance é a dependência
mais instável deste ecossistema e parte APIs com regularidade. Sem limites, uma
instalação daqui a uns meses usa versões diferentes das testadas e eu não
consigo distinguir se parti eu, se foi o upstream, ou se é diferença entre a
minha máquina e o CI.

O roadmap adia "instalação reproduzível" para a V1.0, o que é tarde demais para a
dependência mais frágil do projeto, ainda por cima quando a V0.3 vai introduzir
dados financeiros reais. A partir do momento em que existem dados reais, tenho de
poder reconstruir o ambiente que os manipula.

Propõe uma política concreta: limites inferiores em tudo, limite superior pelo
menos em yfinance, pandas, SQLAlchemy e PySide6, e eventualmente um ficheiro de
constraints separado para o CI reproduzir o conjunto exato. Argumenta o equilíbrio
entre travar versões e ficar preso a bibliotecas desatualizadas. Define também
como se atualiza uma dependência: alteração própria, correr testes, só depois
integrar. Espera pela minha decisão antes de editares o pyproject.

B9.5 — Dependências instaladas sem utilização.

Confirmei por grep que scikit-learn, matplotlib e PyYAML não aparecem numa única
linha de src/ ou tests/. Só existem nos metadados do pacote. São três
dependências instaladas em todas as máquinas e em todas as corridas de CI para
servir zero linhas de código.

Confirma tu mesmo e mostra-me a evidência. Depois propõe movê-las para extras
opcionais até às versões que as precisem de facto: matplotlib na V0.4,
scikit-learn na V0.8, PyYAML quando houver configuração em ficheiro. Espera pela
minha decisão.

B9.6 — Qualidade estática.

Não há linter nem formatador. Propõe ruff, com configuração mínima e sem regras
agressivas, a correr como passo SEPARADO do pytest, para eu distinguir falha de
estilo de falha de teste. Antes de eu decidir, corre-o sobre o código atual e
diz-me quantos problemas encontra e de que tipo.

B9.7 — Estratégia de testes para a V0.3.

Deixa escrito em docs/development.md, sem implementar nada agora:
- os testes de Market Data mantêm-se isolados da Internet. Testes de CI
  dependentes de Yahoo ou Wikipedia seriam instáveis e não se tornam requisito
  de commit;
- os testes SQLite incluem casos com ficheiro temporário real, não só :memory:,
  sobretudo depois das migrações;
- cada regra financeira do Portfolio terá vários testes numéricos: uma compra,
  várias compras, venda parcial, encerramento, nova entrada, comissões, várias
  moedas, arredondamento, tentativa de venda superior à posição, e
  persistência com recarregamento;
- os testes de domínio não dependem da UI nem da Internet.
```

---

## B10 — Coerência dos documentos canónicos

> **Porquê último.** Tudo o que vem antes muda comportamento documentado.
> Corrigir os canónicos a meio do ciclo é garantir que ficam outra vez errados.

```
Sessão B10. Pôr os documentos canónicos de acordo com a realidade.

O AGENTS.md define uma hierarquia canónica precisamente para evitar duplicação e
contradição. A regra está quebrada em vários sítios. Corrige todos e, no fim,
propõe uma forma de impedir que volte a acontecer.

B10.1 — Triggers do CI.
O workflow corre em pushes para main e dev, e em PRs para main (mais o que a
sessão B9 acrescentar). Mas docs/development.md diz que corre em pushes para main
e PRs para main, e o README.md repete o mesmo. Só o status.md tinha a informação
certa. O development.md é a fonte canónica para CI segundo a tua própria
hierarquia, por isso a fonte canónica é que está errada. Corrige o development.md
para refletir o workflow real e faz o README apenas APONTAR para ele, em vez de
repetir o facto.

B10.2 — Integração da V0.2 já aconteceu.
O roadmap.md ainda diz que a V0.2 "está pronta para integração por squash em
main". Já foi integrada: a main está em d4bbe11 e o conteúdo é idêntico ao da dev.
Corrige. O status.md deve passar a indicar com clareza que a V0.2 foi fechada,
integrada e validada, com a data.

B10.3 — Divergência de histórico entre main e dev.
Nota técnica a registar e a resolver: a dev está 24 commits à frente da main em
HISTÓRICO e zero em CONTEÚDO, porque o cbad3d7 é um merge de sincronização. Além
disso, o d4bbe11 tem como pai o 72e38cb, que já era um commit de dev, pelo que a
main ficou com o histórico intermédio lá dentro em vez do commit único que o
AGENTS.md descreve. O fluxo documentado e o fluxo real não coincidem. Diz-me se
achas que devemos ajustar o texto do AGENTS.md para descrever o que fazemos de
facto, ou ajustar o procedimento para cumprir o que está escrito. Argumenta e
espera pela minha decisão. NÃO reescrevas histórico.

B10.4 — Ambiguidade no status.md.
O documento abre com "Versão de trabalho atual: V0.2" e três linhas abaixo diz
que a V0.2 está concluída e que o próximo objetivo é a V0.3. Um documento cujo
propósito é dizer onde estou não pode ser ambíguo sobre onde estou. Reescreve o
cabeçalho com três campos sem ambiguidade: última versão concluída e validada,
versão em curso, próximo objetivo.

B10.5 — Honestidade sobre a validação.
"CONCLUÍDA E VALIDADA" aparece em maiúsculas no status.md e no roadmap.md. Essa
validação foi manual, numa sessão em Windows. O CI corre apenas em Ubuntu (até à
sessão B9). A camada de UI, que são cerca de 300 linhas e é o código mais
arriscado do projeto por combinar threads com Qt, tem 0% de cobertura. Confirma
com `pytest --cov=bolsa --cov-report=term-missing`.

Não quero fingir uma certeza que os testes não sustentam. Reescreve as duas
afirmações distinguindo o que foi validado automaticamente do que foi validado
manualmente, com data e plataforma. Mantém a afirmação de que a versão está
pronta, mas assente em factos verificáveis.

B10.6 — Docstring do provider de universos.
A docstring de WikipediaUniverseProvider ainda diz "Nesta fase são suportados
S&P 500 e NASDAQ 100", com o Euronext 100 implementado por baixo. Corrige.

B10.7 — Varredura final.
Revê README.md, status.md, roadmap.md, architecture.md, development.md,
ai-roadmap.md, legacy.md e AGENTS.md à procura de frases que já não representam o
estado atual, incluindo tudo o que as sessões A1 a B9 mudaram.

Não transformes os documentos em cópias uns dos outros. Cada um responde a uma
pergunta: status responde "onde estamos", roadmap responde "para onde vamos",
architecture responde "como construímos", development responde "como
trabalhamos". Depois da limpeza, um agente que leia apenas os canónicos tem de
conseguir compreender o estado real sem depender do histórico de nenhum chat.

B10.8 — Prevenção.
Depois de corrigires tudo, propõe um mecanismo para impedir a divergência futura.
Opções que vejo: uma regra no AGENTS.md do tipo "cada facto vive num documento,
os outros ligam"; um teste ou passo de CI que verifique coerência entre
documentos e workflow; uma checklist de fecho de versão. Dá-me as opções com o
custo de cada uma e espera que eu escolha. Não implementes sem a minha escolha.
```

---

## B11 — Fecho do ciclo

```
Sessão B11. Fecho, só depois de A1 a B10 estarem validadas por mim.

1. Corre a suite completa com cobertura e mostra-me o antes e o depois.
   Partimos de 39 testes e 55% de cobertura global, medidos em 2026-10-05.

2. Acrescenta ao docs/status.md uma secção que descreva este ciclo: o que foi
   corrigido, o que foi decidido e porquê, e o que ficou deliberadamente por
   fazer. Todas as decisões que eu tomei durante as sessões têm de ficar
   registadas como DECISÕES VIGENTES, não como notas soltas. Lista mínima:
   localização dos ports e dos erros; política de moedas em subunidade;
   integridade SQLite e WAL; localização dos dados e destino da base antiga;
   mecanismo de migrações e comportamento no arranque; fonte única de versão;
   lock da watchlist; proveniência de metadados; semântica de market; cache de
   preços; política de dependências; adoção ou não do ruff; e todas as decisões
   da Faixa A.

3. Mostra-me o diff completo contra o estado inicial da dev, organizado por
   sessão, e o resumo dos commits.

4. Espera pela minha validação final.

5. Só depois de eu dizer explicitamente que valido, e nunca antes, propões a
   passagem para main. Nota importante: ao contrário do ciclo anterior, a main e
   a dev têm hoje conteúdo idêntico, por isso a passagem é só deste ciclo de
   saneamento. Diz-me se achas que deve ser um único commit "Saneamento
   pré-V0.3" ou dois, separando as decisões documentais do saneamento de código.
   Argumenta.

6. Confirma comigo a mensagem de cada commit antes de o criares. Não fazes push
   para main sem eu autorizar.

7. Depois do fecho, abre a V0.3 a partir da especificação produzida na Faixa A.
   Não antes.
```

---

# FAIXA C — V0.3 (referência, não executar)

Esta faixa fica aqui apenas para contexto. Não a dês ao Claude Code neste ciclo.

A V0.3 implementa o que a Faixa A especificou: entidades Portfolio e Transaction,
posições calculadas a partir do ledger, custo médio ponderado, PnL realizado e
não realizado, moeda base, comissões, câmbio, importação e exportação no formato
canónico, prevenção de duplicados e backup antes de operações destrutivas.

O critério de fecho é o definido em A1: um Portfolio simples, matematicamente
correto, persistente, recuperável, testado, e capaz de representar fielmente
compras e vendas reais.

---

# Prioridades, se o tempo apertar

Dos itens deste documento, dez são genuinamente bloqueantes, no sentido de que
fazê-los depois obriga a refazer trabalho ou corrompe dados:

A1 (âmbito), A2 (contabilidade e o invariante do ledger), A3 (Decimal),
A4 (câmbio), A5 (moeda base), B1 (ports), B3 (moedas em subunidade),
B4 (integridade SQLite), B5 (localização dos dados), B6 (migrações).

Mais A6 como semi-bloqueante, porque a semântica de `market` entra no schema e na
exposição da carteira.

O resto é necessário e deve ser feito, mas pode andar a par com a V0.3 ou logo a
seguir: A7, A8, B2, B7, B8, B9, B10.

Vinte e um blocos com discussão em cada passo são muitas sessões. Fazer tudo
antes de abrir a V0.3 arrisca gastar semanas em saneamento e perder o fio ao
projeto, que foi o que matou o Bolsa. A sugestão é fechar a Faixa A inteira, que
é conversa e não código, mais B1 a B6, e abrir a V0.3 a seguir, deixando o resto
para o intervalo seguinte.

---

# Matriz de rastreio

Onde foi parar cada ponto das listas antigas. Serve para confirmares que nada se
perdeu na consolidação.

| Origem | Ponto | Destino neste documento |
|---|---|---|
| v02_erros | 1. Localização dos dados | B5 |
| v02_erros | 2. Migrações | B6 |
| v02_erros | 3. Integridade SQLite | B4 |
| v02_erros | 4. Regras contabilísticas | A2 |
| v02_erros | 5. Decimal e Numeric | A3 |
| v02_erros | 6. Convenção de câmbio | A4 |
| v02_erros | 7. base_currency | A5 |
| v02_erros | 8. Direção das dependências | B1 |
| v02_erros | 9. Semântica de market | A6 (decisão) + B8.2 (implementação) |
| v02_erros | 10. Erros de preço | B2 parte 2 |
| v02_erros | 11. Versão única e tag | B7 |
| v02_erros | 12. Incongruências documentais | B10 |
| v02_erros | 13. Política de dependências | B9.4 e B9.5 |
| v02_erros | 14. Estratégia de testes | B9.1, B9.3, B9.7 |
| v02_erros | 15. Backup, import, export, duplicados | A7 (decisão), V0.3 (implementação) |
| v02_erros | 16. Âmbito da V0.3 | A1 |
| Blocos | 1. Moedas em subunidade | B3 |
| Blocos | 2. Validação de tickers | B8.4 |
| Blocos | 3. Concorrência na Watchlist | B8.1 |
| Blocos | 4. Preços perdidos | B8.3 |
| Blocos | 5. UniverseWidget | B8.2 |
| Blocos | 6. Caminho da base | B5 (fundido com v02_erros 1) |
| Blocos | 7. Erros de universos | B2 parte 1 e 3 |
| Blocos | 8.1 Cache atómica | B2 parte 3 (política) e abaixo |
| Blocos | 8.2 Combo índice -1 | B8.5 |
| Blocos | 8.3 Instrumentos órfãos | B4 (documentar como intencional) |
| Blocos | 8.4 .gitignore | abaixo |
| Blocos | 8.5 LICENSE | abaixo |
| Blocos | 8.6 run.ps1 e venv | abaixo |
| Blocos | 9. Documentação canónica | B10 |
| Blocos | 10. CI e dependências | B9 |
| Blocos | 11. Fecho e squash | B11, reescrito porque a integração já aconteceu |

## Itens pequenos que não justificam sessão própria

Dá este bloco quando houver uma sessão curta, ou junta-o a B9.

```
Itens avulsos. Um commit por item.

I1. Escrita atómica da cache de universos.
cached_universe_provider.py faz _save_cache com path.write_text() direto. Um
crash ou falta de espaço a meio deixa um JSON truncado. A leitura trata o caso e
volta à fonte, por isso não é grave, mas a escrita deve ser atómica: ficheiro
temporário no mesmo diretório e substituição atómica. Garante que funciona em
Windows, onde a substituição tem regras diferentes de POSIX. Teste que confirme
que uma escrita interrompida não destrói a cache anterior.

I2. Instrumentos órfãos no repositório.
Quando se remove o último WatchlistItem que referenciava um InstrumentModel, o
instrumento fica na tabela para sempre. Hoje é inofensivo e provavelmente
desejável, porque na V0.3 as transações vão referenciar instrumentos que já não
estão na watchlist. NÃO APAGUES NADA. Documenta esta decisão em
docs/architecture.md como intencional, para não ser "corrigida" por engano mais
tarde. Nota que esta decisão interage com a integridade referencial ligada na
sessão B4: confirma que ligar as foreign keys não provoca remoção em cascata
indesejada de instrumentos.

I3. .gitignore demasiado largo.
A regra `*.pdf` é global e vai bloquear documentação legítima que eu queira
versionar. A intenção era bloquear extratos. Restringe a regra mantendo a
proteção de extratos, e explica em comentário, no próprio ficheiro, porque é que
a regra existe.

I4. LICENSE.
O repositório é público e não tem licença. Sem licença, por omissão, ninguém tem
direitos sobre o código, o que é uma posição válida mas deve ser deliberada.
Diz-me as opções razoáveis para um projeto pessoal público, com consequências de
cada uma. NÃO adiciones ficheiro nenhum sem a minha escolha.

I5. run.ps1 e ambiente virtual.
O docs/development.md manda criar um venv. O run.ps1 não verifica que está ativo
e corre `python -m pip install -e ".[dev]"` no interpretador que estiver à mão, o
que pode instalar o projeto no Python global do sistema. Acrescenta verificação:
sem ambiente virtual ativo, o script avisa claramente e pára, com instrução de
como ativar. Dá-me um switch para forçar, para os casos em que eu saiba o que
estou a fazer. Confirma também que o script continua coerente com a alteração de
localização de dados da sessão B5.
```