# Arquitetura

## Objetivo

A nova aplicação deve evitar a concentração de responsabilidades existente na versão anterior, em particular a dependência excessiva da interface gráfica.

A arquitetura é organizada em quatro zonas principais:

```text
UI
↓
Application
↓
Domain
↓
Infrastructure
```

## UI

Responsável apenas por interação com o utilizador e apresentação.

Exemplos:

- janela principal;
- carteira;
- watchlist;
- análise de ativos;
- backtesting;
- investigação;
- IA.

A UI não deve aceder diretamente a `yfinance`, calcular PnL, treinar modelos diretamente, executar SQL ou implementar regras financeiras.

## Application

Coordena casos de uso.

Exemplos previstos:

- `MarketService`
- `PortfolioService`
- `WatchlistService`
- `AnalysisService`
- `BacktestService`
- `ResearchService`
- `AIService`

## Domain

Contém as regras e objetos centrais do projeto.

### Instruments

Representa ativos financeiros, incluindo ticker, nome, mercado, moeda e tipo de instrumento.

### Portfolio

A unidade base é a transação.

```text
Transaction
↓
Position
↓
Portfolio
↓
Exposure / PnL
```

Uma posição deve ser calculada a partir das transações.

### Watchlist

Permite acompanhar ativos sem os considerar automaticamente candidatos a compra.

### Strategies

Primeiras estratégias previstas:

- SMA Crossover;
- RSI + MACD.

### Backtest

Responsável por sinais, execução simulada, custos, slippage, posição, curva de capital, trades, métricas e benchmark.

### Research

Regista tese, riscos, catalisadores, invalidação, cenários e data de revisão.

### AI

Área dedicada a datasets, features, modelos, validação temporal, calibração, avaliação, previsões, ensembles, explicabilidade e planeamento.

## Infrastructure

Implementa dependências externas.

### Database

Inicialmente SQLite através de SQLAlchemy.

### Market Data

Inicialmente `yfinance`. A arquitetura deve permitir substituir ou acrescentar outras fontes no futuro.

### Repositories

Implementam persistência para transações, instrumentos, watchlists, teses, previsões, execuções de modelos e backtests.

## Modelo de dados inicial

### Instrument

```text
id
ticker
name
market
currency
asset_type
```

### Portfolio

```text
id
name
base_currency
```

### Transaction

```text
id
portfolio_id
instrument_id
datetime
type
quantity
price
currency
commission
fx_rate
notes
```

### Watchlist

```text
id
name
```

### WatchlistItem

```text
watchlist_id
instrument_id
state
notes
```

### InvestmentThesis

```text
id
instrument_id
created_at
state
thesis
risks
catalysts
invalidation
review_date
```

### ModelRun

```text
id
model_name
model_version
features
train_period
validation_period
parameters
metrics
created_at
```

### Prediction

```text
id
model_run_id
instrument_id
timestamp
horizon
predicted_value
probability
actual_outcome
```

### BacktestRun

```text
id
strategy
parameters
start_date
end_date
cost_model
benchmark
metrics
created_at
```

## Regras de arquitetura

- lógica financeira fora da UI;
- dependências externas atrás de interfaces;
- alterações pequenas e testáveis;
- testes unitários para cálculos;
- testes de integração para persistência e dados;
- nenhuma dependência do projeto antigo;
- migração apenas de conceitos ou código previamente revisto.


### Persistência atualmente implementada

A primeira persistência real do projeto usa SQLAlchemy e SQLite para:

- `instruments`;
- `watchlists`;
- `watchlist_items`.

A Watchlist é reconstruída a partir da base de dados no arranque. Alterações de composição e estado são persistidas através de `SqlAlchemyWatchlistRepository`.

A posição de mercado atual não é guardada na Watchlist. Preços continuam a ser obtidos através do `MarketDataProvider`.


### Preferências locais da interface

Preferências puramente visuais, como larguras e estado dos cabeçalhos das tabelas, são guardadas através de `QSettings`.

Estas preferências:

- pertencem ao utilizador local;
- não fazem parte da base de dados financeira;
- não entram no Git;
- são separadas da persistência de domínio;
- podem ser reutilizadas por novas tabelas da aplicação.

A Watchlist e a tabela de Universos já usam esta abordagem.


### Política de erros de Market Data

Falhas previsíveis do fornecedor de dados são traduzidas para exceções próprias:

- `InstrumentNotFoundError`: o fornecedor respondeu, mas não reconheceu o ticker;
- `MarketDataUnavailableError`: o fornecedor não pôde ser consultado ou ocorreu uma falha de transporte;
- `MarketDataError`: base comum para erros previsíveis desta infraestrutura.

A UI não interpreta diretamente exceções internas de `yfinance`.

Na V0.2 não existem retries automáticos escondidos. Uma falha é apresentada ao utilizador e a repetição é explícita. Esta decisão evita pedidos repetidos inesperados e pode ser revista quando existirem várias fontes de dados.

Históricos sem dados são válidos e devolvem o schema OHLCV canónico vazio. Quando `Adj Close` não é fornecido, a coluna continua presente com valores em falta; `Close` não é usado silenciosamente como substituto.


## Governação do ciclo de estabilização V0.2

O ciclo atual não implementa Portfolio. O documento `docs/stabilization-v0.2.md` define a sequência e preserva integralmente o plano fonte.

Decisões arquiteturais que têm de ser tomadas neste ciclo antes da implementação correspondente:

- A6 completa: semântica de `Instrument.market`, eventual separação de conceitos e autoridade/proveniência dos metadados;
- A7.1: política mínima de backup antes de mover ou migrar a base;
- parte atual de A5: semântica da configuração `base_currency` e eventual renomeação para `default_base_currency`.

Decisões deliberadamente preservadas para a futura especificação da V0.3:

- âmbito funcional de Portfolio;
- ledger e regras contabilísticas;
- Decimal/Numeric e precisão financeira;
- convenção FX;
- autoridade de `Portfolio.base_currency`;
- importação/exportação/duplicados de transações;
- reconciliação com broker;
- política pessoal de investimento.

Estas decisões adiadas não devem ser inferidas nem implementadas durante o saneamento da V0.2.

### Regra de preservação arquitetural

Uma decisão arquitetural substituída não é apagada sem rasto. Deve ficar identificada como histórica/superseded, com a nova decisão e respetiva justificação.


## Metadados de instrumentos e autoridade das fontes

Decisão canónica D1 do ciclo de estabilização V0.2.

### Significado de market/exchange

O campo histórico `Instrument.market` é considerado semanticamente ambíguo porque foi usado para região, grupo de mercado e bolsa.

O conceito canónico passa a ser **exchange / listing venue**: a bolsa ou local de cotação do instrumento.

A implementação deverá evoluir de `market` para `exchange` quando a alteração de código/schema for executada. A UI deverá apresentar o conceito como **Bolsa**.

Região geográfica, país ou exposição regional não são sinónimos de exchange e, se vierem a ser necessários, serão atributos separados.

### Autoridade das fontes

A política de proveniência é:

- providers de universos, como Wikipedia, são autoridade para **composição do universo**;
- podem fornecer ticker e nome útil/provisório para apresentação;
- não são autoridade final para exchange, moeda ou tipo de ativo;
- Yahoo é a fonte principal dos metadados canónicos do instrumento na V0.2: nome quando disponível, exchange, moeda e asset type;
- informação de universos é provisória/fallback e não deve ser promovida silenciosamente a verdade canónica quando a fonte principal não a confirmou.

### Falha temporária da fonte principal

Uma falha temporária do Yahoo não deve impedir necessariamente a adição de um ticker vindo de um universo.

Nesse caso:

- preserva-se o ticker;
- pode preservar-se um nome provisório vindo do universo;
- exchange/moeda não confirmados ficam desconhecidos/em falta;
- não se inventam valores como `US`, `EURONEXT` ou moedas inferidas apenas para preencher campos.

Uma atualização posterior deve poder completar esses metadados.

### Atualização explícita de metadados

A ação `Atualizar dados` significa consultar novamente a fonte principal e atualizar os metadados canónicos, mesmo quando os campos já estejam preenchidos.

A otimização anterior que evitava consulta quando nome, market e currency estavam todos preenchidos fica superseded por esta política.

### Responsabilidade por precedência

A arbitragem entre fontes pertence à camada Application/serviço.

- a UI não decide qual fonte vence;
- o repository não decide qual fonte vence;
- o repository persiste um `Instrument` já considerado canónico pela Application.

Não é introduzido nesta fase um campo persistente `metadata_source`.

### Relação com subunidades monetárias

B3 deve obedecer a esta política. Convenções específicas de cotação de um fornecedor, como moedas/subunidades reportadas pelo Yahoo, devem ser normalizadas junto do adapter/provider apropriado antes de os dados serem expostos como valores canónicos ao resto da aplicação.


## Política de backup antes de movimentos e migrações

Decisão canónica D2 do ciclo de estabilização V0.2.

A base SQLite é dado persistente e não pode ser movida, substituída ou migrada sem existir primeiro uma cópia recuperável.

### Regras

- backup obrigatório antes de qualquer migração de schema;
- backup obrigatório antes de mudar a localização da base;
- se o backup falhar, a operação principal não começa;
- origem, destino e caminho do backup devem ser explícitos ao utilizador quando a operação alterar a base existente;
- backups não entram no Git;
- backups são imutáveis e timestamped, nunca sobrescritos;
- usar preferencialmente a SQLite Backup API para criar snapshot consistente;
- validar o backup com existência, tamanho não nulo, abertura SQLite e `PRAGMA quick_check`;
- validar também a base resultante depois de movimento/migração;
- em falha, preservar base original e backup e não promover uma base parcialmente migrada;
- restauro é explícito e nunca automático;
- ao restaurar, preservar também a base problemática antes de a substituir;
- não existe rotação automática de backups nesta fase.

Esta política protege especificamente B5 (localização dos dados) e B6 (migrações). O desenho de backup/export/import de dados de Portfolio permanece adiado para a futura especificação da V0.3.


## Moeda base por omissão

Decisão canónica D3 do ciclo de estabilização V0.2.

`AppConfig.base_currency` é semanticamente uma **moeda base por omissão**, não uma autoridade financeira global.

O nome preferido passa a ser `default_base_currency`.

Regras:

- serve apenas como valor inicial para funcionalidades futuras que precisem de escolher uma moeda base;
- alterar a configuração não pode alterar silenciosamente entidades persistidas;
- a futura `Portfolio.base_currency` será a autoridade da respetiva carteira, mas essa funcionalidade continua fora do ciclo atual;
- não são introduzidos agora cálculos financeiros ou conversão cambial.


## Ports e adapters da Application

Decisão e implementação B1 do ciclo de estabilização V0.2.

A direção canónica das dependências é:

```text
UI
 ↓
Application
 ├── services
 └── ports
 ↓
Domain

Infrastructure ──implementa──> Application ports
```

A Application não pode importar `bolsa.infrastructure`.

### Ports atuais

Os contratos vivem em `src/bolsa/app/ports/`:

- `market_data.py` — `MarketDataProvider`;
- `universe.py` — `UniverseProvider`;
- `repositories.py` — `WatchlistRepository`;
- `errors.py` — erros previsíveis que fazem parte do contrato externo conhecido pela Application.

Os services importam estes contratos exclusivamente através de `bolsa.app.ports`.

### Adapters atuais

A Infrastructure fornece as implementações:

- `YFinanceMarketDataProvider`;
- `WikipediaUniverseProvider`;
- `CachedUniverseProvider`;
- `SqlAlchemyWatchlistRepository`.

Os Protocols são estruturais: um adapter não precisa de herdar explicitamente do Protocol para o cumprir.

### Erros como parte do contrato

`MarketDataError`, `InstrumentNotFoundError` e `MarketDataUnavailableError` passam a viver canonicamente em `app/ports/errors.py`.

A razão é arquitetural: estes erros são conhecidos pela Application como parte do contrato com dados externos, mas não são regras de negócio do Domain nem devem obrigar a Application a depender de um adapter concreto da Infrastructure.

A taxonomia será expandida no B2 sem voltar a inverter dependências.

### Compatibilidade transitória

Os módulos históricos:

- `infrastructure/market_data/provider.py`;
- `infrastructure/market_data/universe_provider.py`;
- `infrastructure/market_data/errors.py`;

permanecem temporariamente como **reexports de compatibilidade**, mas deixam de ser a origem canónica das definições.

Código novo deve importar os contratos por `bolsa.app.ports`.

### Proteção automática da fronteira

Existe um teste arquitetural que percorre `src/bolsa/app/**/*.py` e falha se encontrar imports diretos de `bolsa.infrastructure`.

Assim, a regra deixa de depender apenas da documentação.


### Estado de validação B1

B1 concluído e validado em 2026-10-05:

- CI GitHub Actions: 40 testes passaram;
- validação local Windows: 40 testes passaram;
- aplicação iniciou corretamente após a refatoração;
- a fronteira `Application → Infrastructure` fica protegida por teste arquitetural.


## Política unificada de erros externos

Decisão e implementação B2 do ciclo de estabilização V0.2.

Esta secção expande e, onde necessário, substitui a política anterior limitada a Market Data, preservando-a como histórico da evolução.

### Hierarquia

```text
ExternalDataError
├── MarketDataError
│   ├── InstrumentNotFoundError
│   ├── MarketDataUnavailableError
│   ├── CurrentPriceUnavailableError
│   └── MarketDataFormatError
└── UniverseError
    ├── UnsupportedUniverseError
    ├── UniverseSourceUnavailableError
    └── UniverseFormatError
```

Universos e cotações são ambos dados externos, mas pertencem a famílias paralelas.

### Preço atual

O contrato canónico é:

```python
get_current_price(instrument) -> float
```

Em falha previsível, o provider levanta uma exceção tipada.

- ticker não reconhecido → `InstrumentNotFoundError`;
- fornecedor/rede indisponível → `MarketDataUnavailableError`;
- instrumento válido sem cotação utilizável → `CurrentPriceUnavailableError`;
- resposta estruturalmente inesperada → `MarketDataFormatError`.

`None` deixa de representar silenciosamente todas estas situações.

Histórico vazio continua deliberadamente válido e devolve o schema OHLCV canónico vazio.

### Universos

A Application recebe `UniverseLoadResult`, que transporta o `Universe` e a origem/frescura:

- `LIVE` — obtido da fonte;
- `FRESH_CACHE` — cache dentro do TTL normal;
- `STALE_CACHE` — cache expirada usada em modo degradado.

A fonte Wikipedia não deixa escapar exceções previsíveis de urllib/pandas:

- código não suportado → `UnsupportedUniverseError`;
- rede/timeout/HTTP → `UniverseSourceUnavailableError`;
- estrutura da página/tabela inválida → `UniverseFormatError`.

### Fallback stale

A cache normal mantém TTL de 24 horas.

Se a cache expirou e a fonte falha por indisponibilidade ou formato, pode ser usada cache com idade máxima de **7 dias**.

Esse fallback:

- é explícito;
- inclui timestamp da cache;
- inclui aviso do motivo;
- nunca se aplica a universo não suportado;
- não transforma dados antigos em dados aparentemente frescos.

Depois de 7 dias, a falha da fonte volta a ser apresentada e a cache não é utilizada.

### UI e serviços

A UI não interpreta exceções internas de providers.

A Watchlist trata falhas de preço por instrumento, preserva as restantes linhas e apresenta avisos com o motivo.

A UI de universos mostra se os dados vieram de cache fresca ou stale e, neste último caso, apresenta o aviso associado.

Testes dos caminhos de erro usam providers/fontes simulados; o CI não depende de Yahoo ou Wikipedia reais.


### Estado de validação B2

B2 concluído e validado em 2026-10-06:

- GitHub Actions na `dev`: 58 testes passaram;
- validação local confirmada pelo utilizador;
- a taxonomia de erros externos, o contrato de preço atual e o fallback stale dos universos ficam vigentes como política canónica.


## Convenções de cotação e subunidades monetárias

Decisão e implementação B3 do ciclo de estabilização V0.2.

### Separação de responsabilidades

O Domain conhece apenas a moeda canónica do instrumento.

Convenções específicas de cotação do fornecedor pertencem ao adapter correspondente. No adapter Yahoo, uma cotação em `GBp`, por exemplo, é convertida antes de o preço ser exposto ao resto da aplicação.

`Instrument.currency` não é usado para inferir a escala do preço.

### Convenções suportadas inicialmente

```text
GBp → GBP × 0.01
GBX → GBP × 0.01
ZAc → ZAR × 0.01
ILA → ILS × 0.01
USD/EUR/GBP/... canónico em três letras maiúsculas → × 1.0
```

A correspondência de subunidades é deliberadamente sensível à forma bruta recebida: `GBp` não é normalizado para `GBP` antes de identificar a convenção.

Uma moeda inesperada/malformada produz `MarketDataFormatError` em vez de assumir silenciosamente fator 1.

### Escala aplicada

O fator é aplicado a:

- preço atual;
- Open;
- High;
- Low;
- Close;
- Adj Close.

`Volume` não é alterado.

### Cache da sessão

`YFinanceMarketDataProvider` mantém por ticker uma convenção de cotação em memória, contendo:

- moeda bruta;
- moeda canónica;
- fator de preço.

Esta cache evita consultas repetidas durante a sessão e não é persistida em SQLite.

### Relação com universos

Por decisão D1, universos não são autoridade final para moeda/exchange. B3 não utiliza a moeda vinda da Wikipedia para escolher o fator de preços Yahoo.

A limpeza integral da proveniência no fluxo UniverseWidget → Watchlist fica para B8.2.


### Estado de validação B3

B3 concluído e validado em 2026-10-07:

- GitHub Actions na `dev`: 72 testes passaram;
- validação local confirmada pelo utilizador;
- a política de normalização de subunidades Yahoo fica vigente como comportamento canónico do adapter.


## Integridade e configuração SQLite

Decisão e implementação B4 do ciclo de estabilização V0.2.

### PRAGMAs obrigatórios

Cada nova ligação SQLite criada pelo engine recebe:

```text
PRAGMA foreign_keys = ON
PRAGMA busy_timeout = 5000
```

A configuração é aplicada no evento de ligação do SQLAlchemy, garantindo que não depende de uma única execução no arranque.

### Integridade referencial

As foreign keys declaradas nos modelos são consideradas efetivas apenas porque `foreign_keys=ON` é ativado e testado.

A suite verifica:

- foreign keys inválidas são rejeitadas com `IntegrityError`;
- depois da falha é feito rollback e não ficam alterações parciais;
- `ON DELETE CASCADE` remove `watchlist_items` quando a Watchlist é eliminada ao nível da base.

### Instrumentos órfãos

A existência de um `Instrument` não depende da sua presença numa Watchlist.

Remover um item da Watchlist:

- remove o `WatchlistItem`;
- preserva o `Instrument`.

Isto é comportamento intencional e protege reutilização futura do instrumento, incluindo futuras relações com Portfolio.

### Encerramento de recursos

Engines usados em testes de integração são libertados explicitamente com `engine.dispose()`.

A aplicação também liberta o engine em `main()` através de `try/finally`, incluindo quando o encerramento passa por exceção.

Esta decisão responde ao `ResourceWarning` SQLite detetado no baseline S0.

### Concorrência SQLite

`busy_timeout=5000` permite esperar até cinco segundos por um lock SQLite transitório antes de falhar.

Isto é independente da política de retries de Market Data e não introduz retries escondidos de rede.

### WAL

WAL foi avaliado no B4 e **não é ativado nesta fase**.

Razões:

- a concorrência atual não o exige;
- B5/B6 ainda vão alterar localização, backups e migrações;
- WAL acrescentaria ficheiros `-wal`/`-shm` e complexidade operacional sem benefício demonstrado.

Reavaliar WAL apenas se surgirem bloqueios reais ou necessidades de concorrência superiores.

### Evolução de schema

`Base.metadata.create_all()` continua temporariamente ativo no B4.

A sua substituição por migrações controladas pertence ao B6 e não é antecipada aqui.


### Estado de validação B4

B4 concluído e validado em 2026-10-08:

- GitHub Actions na `dev`: 75 testes passaram;
- validação local concluída pelo utilizador;
- o `ResourceWarning` SQLite identificado no S0 deixou de aparecer no CI B4;
- o bloqueio local do Windows App Control incidia sobre a extensão C opcional do SQLAlchemy e foi resolvido com instalação pure-Python da mesma versão, sem alterar o código da aplicação nem enfraquecer a política de segurança do Windows;
- a política SQLite deste bloco fica vigente como comportamento canónico.


## Localização estável dos dados

Decisão e implementação B5 do ciclo de estabilização V0.2.

### Diretoria de dados

Os dados persistentes deixam de depender do diretório de trabalho atual.

A localização normal é obtida por `platformdirs` com `appauthor=False` e sem criação implícita de diretórios.

Estrutura lógica:

```text
<user data dir>/BolsaNext/
├── bolsanext.sqlite3
├── cache/
│   └── universes/
└── backups/
```

Em Windows, a localização normal é a área Local AppData do utilizador. Em Linux/macOS são usados os locais convencionais do sistema.

### Override

`BOLSANEXT_DATA_DIR` permite definir explicitamente outra diretoria.

O override é deliberado e, quando usado, não ativa a proteção de migração legacy do repositório, porque a escolha de localização já foi explícita.

### Configuração sem efeitos laterais

`load_config()` apenas resolve configuração.

A criação física de diretórios pertence a:

```python
prepare_environment(config)
```

Assim, ler configuração não altera o disco.

### Moeda base por omissão

B5 materializa a decisão D3 e renomeia `AppConfig.base_currency` para `AppConfig.default_base_currency`.

Continua a ser apenas um valor por omissão. Não é autoridade financeira global e não introduz lógica de Portfolio.

### Proteção da base legacy

Se a localização nova ainda não contém base, mas existe `data/bolsanext.sqlite3` no repositório local, o arranque normal **não cria uma base vazia nova**.

Em vez disso, pára e exige migração explícita.

Isto evita a situação em que a aplicação aparenta ter perdido a Watchlist quando, na realidade, apenas mudou de ficheiro.

### Migração explícita

A ferramenta:

```text
python -m bolsa.tools.migrate_data_dir
```

mostra por omissão um dry-run com:

- origem;
- destino;
- caminho do backup;
- existência de cada um.

Nenhum dado é alterado sem `--execute`.

A execução efetiva:

1. valida a base de origem com `PRAGMA quick_check`;
2. cria backup imutável via SQLite Backup API;
3. valida o backup;
4. cria a nova base a partir do backup;
5. valida a nova base;
6. preserva sempre a base de origem.

Se o destino já existir, a operação pára e não sobrescreve nada.

### Cache

Cache de universos não é migrada. É dado derivado e pode ser recriada.

### Relação com B6

B5 trata apenas **localização física dos dados**.

Evolução de schema, baseline e revisões Alembic pertencem ao B6.


### Migração B5 executada no ambiente Windows

Em 2026-10-08 a migração real da base V0.2 foi executada e validada no ambiente Windows do utilizador.

Caminhos confirmados:

```text
Origem:
C:\Users\Portatil\Documents\GitHub\BolsaNext\data\bolsanext.sqlite3

Backup:
C:\Users\Portatil\AppData\Local\BolsaNext\backups\bolsanext_before_move_20261008_010523.sqlite3

Nova base ativa:
C:\Users\Portatil\AppData\Local\BolsaNext\bolsanext.sqlite3
```

A origem foi preservada. A nova base foi criada apenas depois do backup e da validação SQLite.

A validação funcional final da aplicação sobre a nova base permanece como último critério de fecho do B5.


### Estado de validação B5

B5 concluído e validado em 2026-10-08:

- GitHub Actions: 83 testes passaram;
- suite local Windows: 83 testes passaram;
- a migração real preservou origem, criou backup validado e criou a nova base na diretoria estável;
- a aplicação arrancou sobre a nova base;
- Watchlist e estados existentes foram preservados;
- uma alteração de estado persistiu depois de fechar e reabrir;
- a base antiga e o backup permanecem preservados.

A diretoria estável do utilizador passa a ser a origem operacional dos dados V0.2. A base legacy no repositório permanece apenas como cópia histórica de segurança até ao fecho do ciclo de estabilização.

## Migrações de schema com Alembic

Decisão e implementação B6 do ciclo de estabilização V0.2.

Alembic é a autoridade única para criação e evolução do schema persistente.

### Baseline V0.2

A revisão inicial é `0001_v02_baseline` e representa o schema V0.2 já existente, mantendo deliberadamente o campo `market`.

A alteração futura `market → exchange` não é incluída na baseline e deverá ser uma revisão posterior.

### Estados suportados no arranque

```text
DB inexistente/vazia
    → upgrade head

DB V0.2 válida sem alembic_version
    → validar baseline
    → backup
    → stamp baseline
    → upgrade head se existirem revisões posteriores

DB versionada em head
    → nenhuma alteração

DB versionada atrás de head
    → validar caminho
    → backup
    → upgrade head

DB incompatível / revisão desconhecida
    → parar
```

Não existe downgrade automático.

### Validação da base legacy

Antes de aceitar uma base não versionada como V0.2, são comparados:

- tabelas;
- colunas e tipos essenciais;
- NOT NULL relevantes;
- primary keys;
- unicidade de ticker, nome da Watchlist e par watchlist/instrument;
- foreign keys com `ON DELETE CASCADE`.

Só uma base compatível pode receber `stamp`.

### Backups

Qualquer escrita de adoção/migração sobre uma base com dados é precedida de snapshot SQLite validado.

Formato: `bolsanext_before_migration_<revision>_<timestamp>.sqlite3`.

A infraestrutura reutiliza `create_validated_database_backup()` de B5/D2.

### Falhas e runtime

Uma falha de `stamp` ou upgrade preserva a base e o backup existente. Não existe restauro automático.

`Base.metadata.create_all()` foi removido do mecanismo operacional. O arranque chama `ensure_database_schema()` antes de construir repositories.

Se o schema não puder ser validado ou migrado de forma conhecida, a aplicação termina com erro em vez de abrir sobre uma base ambígua.

### Testes

A suite inclui proteção contra reintrodução de `create_all()` no runtime e cenários de base nova/vazia, legacy V0.2, base corrente, incompatibilidade, revisão desconhecida, falha durante adoção e base versionada atrás de head com backup + upgrade orquestrado.


### Estado de validação B6

B6 concluído e validado em 2026-10-08: CI e suite local com 92 testes; adoção real da baseline `0001_v02_baseline` com backup prévio; dados preservados; segundo arranque em head sem backup redundante. Alembic fica como autoridade operacional do schema.


## Fonte única de versão

Decisão e implementação B7 do ciclo de estabilização V0.2.

A versão da aplicação tem uma única origem:

```text
src/bolsa/version.py
    __version__ = "0.2.0"
```

A partir desta origem derivam:

- `bolsa.__version__`;
- metadata do pacote Python através de setuptools dynamic metadata;
- User-Agent dos providers;
- rótulo de versão da interface.

A UI usa `version_label(stage)` para combinar a versão canónica com o nome funcional da fase, mantendo os dois conceitos separados.

Não devem ser introduzidas novas strings literais de versão em módulos funcionais.

A existência da versão `0.2.0` no código não autoriza a criação antecipada da tag Git `v0.2.0`. A tag continua reservada para B11, depois da integração final validada em `main`.


### Estado de validação B7

B7 concluído e validado em 2026-10-08:

- GitHub Actions: 97 testes passaram;
- validação local confirmou a versão canónica `0.2.0`;
- metadata instalado, User-Agent e UI usam a mesma fonte;
- a tag Git `v0.2.0` continua reservada para B11.


## Concorrência da Watchlist

Decisão e implementação B8.1.

A proteção contra concorrência existe em duas camadas complementares.

### Camada Application

`WatchlistService` possui um `threading.RLock` próprio.

O lock protege o agregado durante leituras e mutações relevantes, incluindo operações que consultam Market Data e a persistência subsequente.

Isto garante integridade mesmo quando o serviço é chamado fora da UI.

### Camada UI

`WatchlistOperationCoordinator` coordena uma única operação assíncrona da área Watchlist/Universos.

`MainWindow` cria uma instância e partilha-a entre:

- `WatchlistWidget`;
- `UniverseWidget`.

Enquanto o coordenador está busy, ficam desativados todos os controlos que podem iniciar outra operação de rede ou alterar a Watchlist, incluindo widgets embebidos nas células da tabela.

O estado busy é sempre libertado a partir de `QThread.finished`, incluindo em erro. Uma falha ao iniciar a thread liberta-o imediatamente.

A UI evita operações incompatíveis e bloqueios visíveis; o lock do serviço permanece a garantia final de integridade.

### Teste de concorrência

A suite executa duas threads Python contra o mesmo `WatchlistService`: uma atualização de metadados bloqueada deliberadamente no provider e uma remoção concorrente. A remoção espera pelo lock e o estado final é coerente, sem exceções.


### Estado de validação B8.1

B8.1 concluído e validado em 2026-10-08:

- GitHub Actions: 101 testes passaram;
- validação local confirmou o bloqueio global dos controlos mutáveis durante operações em curso;
- a coordenação foi confirmada entre Watchlist e Universos;
- os controlos foram libertados corretamente no fim das operações.

A política de duas camadas permanece vigente: coordenação visual na UI e `RLock` no serviço.
