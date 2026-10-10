# Desenvolvimento local

## Requisitos

- Python 3.12 ou superior
- Git

## Clonar o projeto

```bash
git clone https://github.com/f2432/BolsaNext.git
cd BolsaNext
```

## Criar ambiente virtual

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

## Instalar o projeto

Instalação normal:

```bash
pip install -e .
```

Instalação para desenvolvimento, incluindo testes:

```bash
pip install -e ".[dev]"
```

## Executar a aplicação

```bash
bolsanext
```

Em alternativa:

```bash
python -m bolsa.main
```

Os dados persistentes usam uma diretoria estável do utilizador, independente da pasta a partir da qual a aplicação é arrancada.

Em Windows, a localização normal fica na área Local AppData, tipicamente:

```text
%LOCALAPPDATA%\\BolsaNext\\bolsanext.sqlite3
```

A aplicação cria explicitamente as pastas de dados, cache e backups através de `prepare_environment()`.

Para usar uma localização diferente:

```powershell
$env:BOLSANEXT_DATA_DIR = "C:\\caminho\\pretendido"
python -m bolsa.main
```

### Migração da base antiga

Se existir a antiga `data/bolsanext.sqlite3` no repositório e ainda não existir base na nova localização, o arranque pára sem criar uma base vazia.

Primeiro consulta o plano, sem alterar dados:

```powershell
python -m bolsa.tools.migrate_data_dir
```

Depois de confirmares origem, destino e backup, executa:

```powershell
python -m bolsa.tools.migrate_data_dir --execute
```

A ferramenta cria backup com SQLite Backup API, valida as bases com `PRAGMA quick_check`, preserva a base antiga e nunca sobrescreve uma base já existente no destino.

## Executar os testes

```bash
pytest
```

Modo resumido:

```bash
pytest -q
```

Com cobertura:

```bash
pytest --cov=bolsa --cov-report=term-missing
```

## Estrutura de trabalho

Mudanças de lógica devem ser feitas fora da interface gráfica.

Antes de integrar alterações:

1. executar os testes;
2. confirmar que não foram adicionados ficheiros pessoais ou gerados;
3. rever o diff;
4. atualizar a documentação quando a arquitetura ou comportamento mudar.

## GitHub Actions

O workflow `.github/workflows/tests.yml` executa os testes, a cobertura e o Ruff obrigatórios em Linux/Python 3.12 e Windows/Python 3.14, em pushes e pull requests destinados a `main` ou `dev`. Os artefactos de cobertura são separados por plataforma. Este parágrafo descreve a configuração vigente; os registos posteriores de B9.1/B9.2 documentam a evolução histórica.

O CI instala o projeto através de:

```bash
pip install -e ".[dev]"
```


## Execução rápida no Windows

Na raiz do projeto existe o script `run.ps1`.

Execução normal:

```powershell
.\run.ps1
```

O script executa, por esta ordem:

1. `git pull --ff-only`;
2. `python -m pip install -e ".[dev]"`;
3. `python -m pytest -q`;
4. `python -m bolsa.main`.

Se algum passo falhar, o script pára e não executa os seguintes.

Existem também opções para saltar passos quando necessário:

```powershell
.\run.ps1 -SkipPull
.\run.ps1 -SkipInstall
.\run.ps1 -SkipTests
```

As opções podem ser combinadas.

Exemplo para apenas testar e arrancar sem fazer `git pull` nem reinstalar dependências:

```powershell
.\run.ps1 -SkipPull -SkipInstall
```


## Fluxo com branches

O desenvolvimento corrente usa duas branches:

- `main`: versão validada;
- `dev`: trabalho em curso e versões para teste local.

O script `run.ps1` garante que os testes locais são feitos sobre `dev`. Se for executado estando noutra branch, tenta mudar automaticamente para `dev`.

A `main` só deve ser atualizada depois de validação explícita. A integração de um bloco validado deve ser feita por squash, para que várias alterações intermédias de `dev` resultem num único commit coerente em `main`.


## Protocolo do ciclo de estabilização V0.2

O ciclo atual segue obrigatoriamente `docs/stabilization-v0.2.md`.

### Regras de execução

- trabalhar apenas em `dev`;
- não iniciar V0.3;
- não criar `Portfolio`, `Transaction`, `Position` ou serviços de Portfolio;
- começar por S0 e avançar sequencialmente;
- não saltar itens silenciosamente;
- quando uma sessão exigir decisão do utilizador, parar antes de implementar;
- alterações de comportamento entram com testes sempre que forem testáveis;
- documentação canónica afetada é atualizada sem eliminar informação anterior;
- `main` só é alterada com pedido explícito do utilizador;
- a tag `v0.2.0` só pode ser criada depois do fecho B11.

### Baseline de testes

O início deste ciclo tem como referência histórica 39 testes. Esse valor é **baseline inicial**, não número fixo.

Em sessões posteriores:

- todos os testes existentes devem passar;
- o número de testes pode e deve aumentar quando houver comportamento novo ou corrigido;
- uma redução do número de testes exige justificação explícita;
- a cobertura deve ser medida no S0 e novamente no B11.

### Regra de completude

Cada item do plano termina num estado explícito:

- concluído e validado;
- decidido e documentado;
- adiado explicitamente, com destino e razão;
- não aplicável, com justificação.

Nenhum item pode desaparecer por omissão.

### Preservação documental

Antes de modificar qualquer documento canónico, deve ser verificado que nenhuma decisão, requisito, pendência ou justificação anteriormente registada é perdida. Quando uma decisão muda, a anterior permanece identificável como histórica/superseded.


## Nota Windows App Control e SQLAlchemy

Durante a validação B4 em Windows/Python 3.14.5, uma política de Windows App Control bloqueou a extensão C opcional `sqlalchemy.util._collections_cy`, impedindo o próprio import do SQLAlchemy.

A solução local validada foi reinstalar **a mesma versão** do SQLAlchemy em modo pure-Python, sem desativar nem enfraquecer o App Control:

```powershell
$saVersion = ((python -m pip show SQLAlchemy | Select-String '^Version:').Line -split ':',2)[1].Trim()
python -m pip uninstall -y SQLAlchemy
$env:DISABLE_SQLALCHEMY_CEXT="1"
python -m pip install --no-cache-dir --no-binary=SQLAlchemy --no-deps "SQLAlchemy==$saVersion"
Remove-Item Env:DISABLE_SQLALCHEMY_CEXT
```

Esta é uma exceção de ambiente local, não uma alteração funcional do BolsaNext nem uma exigência geral para todos os sistemas.

A política de dependências/ambientes será revista no B9.


### Migração real validada em Windows

Em 2026-10-08 foi executada a primeira migração real da base V0.2 para a nova diretoria estável do utilizador.

Resultado:

```text
Origem preservada:
C:\Users\Portatil\Documents\GitHub\BolsaNext\data\bolsanext.sqlite3

Backup:
C:\Users\Portatil\AppData\Local\BolsaNext\backups\bolsanext_before_move_20261008_010523.sqlite3

Nova base:
C:\Users\Portatil\AppData\Local\BolsaNext\bolsanext.sqlite3
```

A ferramenta de migração reportou sucesso depois de validar os ficheiros SQLite.

A base antiga deve permanecer intacta pelo menos até ao fecho do ciclo de estabilização V0.2.


### Validação funcional final B5

Em 2026-10-08 foi validado o uso efetivo da nova base em Windows:

- aplicação arrancou normalmente usando a base em Local AppData;
- Watchlist e estados anteriores estavam presentes;
- uma alteração de estado foi gravada;
- depois de fechar e reabrir, a alteração permaneceu.

B5 fica concluído. A antiga base `data/bolsanext.sqlite3` deve continuar preservada até ao fecho do ciclo de estabilização V0.2.

## Migrações de schema

Desde B6, Alembic é responsável pela criação e evolução do schema SQLite.

A baseline atual é `0001_v02_baseline`.

No arranque:

- uma base nova é criada através de `alembic upgrade head`;
- uma base V0.2 legacy compatível recebe backup e `stamp` da baseline;
- uma base versionada atrasada recebe backup antes de `upgrade head`;
- uma revisão desconhecida/incompatível bloqueia o arranque;
- nunca é feito downgrade automático.

`Base.metadata.create_all()` não é usado pelo runtime.

Os backups de migração ficam em `config.backups_dir` e seguem o formato:

```text
bolsanext_before_migration_<revision>_<timestamp>.sqlite3
```

A base antiga preservada em `data/bolsanext.sqlite3` continua fora deste mecanismo operacional e permanece apenas como cópia histórica até ao fecho do ciclo V0.2.


### Validação real B6

Em 2026-10-08, a base real foi validada como V0.2, recebeu backup e `stamp` em `0001_v02_baseline`. Watchlist/estados permaneceram intactos e um segundo arranque não criou novo backup. B6 fica concluído e validado.


## Versão canónica

A versão do BolsaNext é definida exclusivamente em:

```text
src/bolsa/version.py
```

O valor atual é `0.2.0`.

Não editar manualmente versões noutros ficheiros. `pyproject.toml` lê a versão dinamicamente de `bolsa.version.__version__`, e package/UI/User-Agent derivam da mesma origem.

A tag Git `v0.2.0` só será criada no fecho B11, depois da integração final validada em `main`.


### Validação real B7

Em 2026-10-08 foi confirmada localmente a fonte única de versão:

- package: `0.2.0`;
- metadata instalado: `0.2.0`;
- User-Agent: derivado da versão canónica;
- UI: `V0.2.0 — Market Data`.

B7 fica concluído e validado. A tag Git continua proibida até B11.


## Coordenação de operações Watchlist/UI

Desde B8.1, operações assíncronas da Watchlist e Universos usam um `WatchlistOperationCoordinator` partilhado pelo `MainWindow`.

Não criar flags busy independentes por botão/widget. A exclusão visual é global para esta área.

A integridade real do agregado é garantida adicionalmente por `RLock` dentro de `WatchlistService`.

Os imports de `bolsa.ui.watchlist` são lazy para que módulos baseados apenas em QtCore possam ser testados no CI headless sem carregar QtWidgets/libEGL.


### Validação real B8.1

Em 2026-10-08 foi confirmada localmente a coordenação global de operações:

- durante refresh/carregamento, os controlos mutáveis ficam desativados;
- o bloqueio é partilhado entre Watchlist e Universos;
- no fim das operações, os controlos voltam a ficar disponíveis.

B8.1 fica concluído e validado.


## B8.2 — metadados de instrumentos

Desde B8.2:

- usar `Instrument.exchange`, não `Instrument.market`;
- a UI chama ao campo **Bolsa**;
- Wikipedia/universos fornecem apenas ticker e nome provisório;
- Yahoo decide exchange, moeda e tipo canónicos;
- `UniverseWidget` deve manter os objetos `Instrument` recebidos, não reconstruí-los a partir de texto da tabela;
- a cache de universos usa formato v2 e não deve reintroduzir exchange/moeda;
- `refresh_metadata()` consulta sempre a fonte principal;
- alterações futuras do schema devem ser novas migrations Alembic.

Migration atual:

```text
0001_v02_baseline
        ↓
0002_market_to_exchange
```

No primeiro arranque com B8.2 sobre uma base em `0001_v02_baseline`, o runtime cria backup e executa automaticamente o upgrade para `0002_market_to_exchange`.


### Validação real B8.2

Em 2026-10-09 foram confirmados localmente:

- upgrade da base para `0002_market_to_exchange`;
- backup automático antes da migration;
- coluna **Bolsa** na Watchlist;
- Universos com apresentação apenas Ticker/Nome;
- enriquecimento de metadados via Yahoo;
- atualização explícita de metadados existentes;
- persistência após reinício.

B8.2 fica concluído e validado.

### Teste manual B8.3 (cache de preços de sessão)

Na branch `dev`, executar `git pull --ff-only origin dev`, `python -m pytest -q` e `python -m bolsa.main`. Atualizar preços na Watchlist, mudar para Universos e voltar; os valores devem manter-se sem novo pedido de preços. Atualizar dados e confirmar que não apaga os preços. Remover e readicionar um ativo e confirmar preço inicialmente desconhecido. Encerrar e reabrir a aplicação: preços devem começar sem valor. Em erro individual do provider, deve permanecer o último preço conhecido acompanhado de aviso. O bloco só será marcado validado após confirmação do utilizador.

Registo de validação B8.3 (2026-10-09): o utilizador confirmou que os testes locais e funcionais correram como esperado. **B8.3 CONCLUÍDO E VALIDADO**. Próximo passo B8.4, ainda não implementado. A `main` e a tag `v0.2.0` mantêm-se intocadas.

### Verificação local do B8.4

Na branch `dev`, executar `git pull --ff-only origin dev`, `python -m pytest -q` e `python -m bolsa.main`. Confirmar que símbolos conhecidos continuam aceites (`AAPL`, `^GSPC`, `ASML.AS`, `EURUSD=X` e `BRK-B`), e que entradas com pontuação isolada ou separadores inválidos são rejeitadas antes de consulta Yahoo. Confirmar que adicionar e atualizar instrumentos existentes mantém comportamento habitual. Só fechar o bloco depois de confirmação do utilizador.

Registo de validação B8.4 (2026-10-10): o utilizador confirmou que executou os testes e que o resultado foi correto. **B8.4 CONCLUÍDO E VALIDADO**. Mantêm-se os testes de regressão, a distinção entre sintaxe e existência real no provider e as decisões anteriores. Próximo sub-bloco: B8.5, ainda por implementar. `main` e tag `v0.2.0` não alteradas.

### Validação local do B8.5

Executar na branch `dev`: `git pull --ff-only origin dev`, `python -m pytest -q`, `python -m bolsa.main`. Na Watchlist, confirmar que os estados existentes aparecem e podem ser alterados/persistidos como antes. A suite inclui testes headless de valores desconhecidos e `None`; uma simulação de estado desconhecido no combo apresenta `Desconhecido` até seleção explícita de estado válido. Nenhuma migration é esperada. O bloco B8.5 só fica validado após confirmação local do utilizador.

Registo de validação B8.5 e fecho B8 (2026-10-10): o utilizador confirmou que executou todos os testes locais e que tudo funcionou. **B8.5 CONCLUÍDO E VALIDADO** e **B8 (B8.1 a B8.5) CONCLUÍDO E VALIDADO**. Preservam-se integralmente os registos históricos e decisões anteriores. O bloco seguinte é B9 (CI, dependências e qualidade), ainda por executar. Não houve integração em `main` nem criação da tag `v0.2.0`.

## B9.1 — Relatórios de cobertura no CI

O workflow `.github/workflows/tests.yml`, na branch `dev`, mede cobertura dos testes com `python -m pytest -q --cov=bolsa --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov`. No separador Actions do GitHub, abrir a execução de `tests` para o commit mais recente da `dev`, consultar o passo `Run tests with coverage` e descarregar, em `Artifacts`, `coverage-python-3.12-ubuntu`. Historicamente, o artefacto B9.1 continha `coverage.xml` e `htmlcov/index.html`. Desde B9.2 os artefactos correntes são `coverage-linux-py312` e `coverage-windows-py314` (abrir `htmlcov/index.html` localmente). Conservação: 14 dias. Não existe `fail-under`; cobertura inferior a 55% é observação a analisar, não bloqueio automático. Para reprodução local, usar o mesmo comando. Este registo é de implementação, ainda pendente de validação do utilizador.

## B9.2 — Testes de CI em Linux e Windows

O workflow `tests.yml` executa testes em duas combinações: `ubuntu-latest` com Python 3.12 e `windows-latest` com Python 3.14. Pushes em `main` e `dev`, bem como pull requests para ambas, disparam o workflow. `fail-fast: false` permite consultar os dois resultados mesmo em caso de falha de um deles. A cobertura é recolhida nos dois ambientes e os artefactos `coverage-linux-py312` e `coverage-windows-py314` são distintos. Em GitHub Actions, abrir a execução mais recente da `dev` e confirmar o sucesso dos dois jobs e a presença de ambos os artefactos. O Python 3.14 de CI aproxima-se do Python 3.14.5 local sem impor a mesma revisão de patch. A exceção local de SQLAlchemy pure-Python causada por Windows App Control mantém-se documentada separadamente. **B9.1 concluído e validado**, **B9.2 a aguardar confirmação do CI e validação do utilizador**.

Validação B9.2 (2026-10-10): o utilizador confirmou a conclusão da verificação solicitada do CI Linux/Windows. **B9.2 CONCLUÍDO E VALIDADO**. Segue-se B9.3, auditoria e decisão das dependências, sem alterações ao `pyproject.toml` antes da aprovação do desenho. `main` e tag `v0.2.0` continuam inalteradas.

## B9.3 — Dependências do projeto

Para trabalhar na V0.2, permanece suficiente `python -m pip install -e ".[dev]"`. As dependências essenciais de runtime são PySide6, pandas, SQLAlchemy, alembic, yfinance, platformdirs e lxml. Esta última é necessária à leitura de tabelas Wikipedia por `pandas.read_html`. Bibliotecas de investigação e IA futura (`numpy`, `scikit-learn`, `matplotlib`, `PyYAML`) ficam no extra opcional, instalável por `python -m pip install -e ".[analysis]"`, se necessário. As versões declaradas têm limites mínimos e não constituem lockfile ou prova de compatibilidade com todas as combinações possíveis. O workflow CI Linux/Windows regista versões efetivamente resolvidas por `pip list --format=freeze`. Validar instalação, suite e arranque no Windows; a solução local pure-Python de SQLAlchemy para Windows App Control permanece válida e não foi alterada. **B9.3 aguarda validação CI/local.**

Validação B9.3 (2026-10-10): testes e aplicação confirmados pelo utilizador. **B9.3 CONCLUÍDO E VALIDADO**. Próximo bloco B9.4 (Ruff), ainda não implementado. `main` e a tag `v0.2.0` permanecem intactas.

## B9.4 — Auditoria de qualidade com Ruff

Instalar dependências de desenvolvimento (`python -m pip install -e ".[dev]"`) e executar na branch `dev`: `python -m ruff check src tests`. Regras iniciais: `E4`, `E7`, `E9`, `F`; Python-alvo 3.12. A etapa `Ruff initial audit (non-blocking)` do GitHub Actions corre em Linux e Windows com `continue-on-error: true`, pelo que uma indicação amarela nessa etapa não prova sucesso de lint. Recolher e analisar as ocorrências antes de alterar código ou tornar a etapa obrigatória. Não executar `ruff format` nem `ruff check --fix` globalmente. **B9.4 ainda não está validado.**

### B9.4 — Ruff obrigatório no CI

Após a primeira auditoria foi removido o único import não utilizado (`F401`) identificado no teste de integração `test_schema_migrations.py`. O passo agora designado `Ruff lint` executa `python -m ruff check src tests` e **falha o job** caso existam violações; deixou de ter `continue-on-error`. Validar no GitHub Actions os jobs Linux e Windows, o passo Ruff e a suite pytest. Executar localmente `python -m ruff check src tests` e `python -m pytest -q`. A introdução do Ruff só será marcada CONCLUÍDA E VALIDADA após confirmação do utilizador.

Validação B9.4 (2026-10-10): GitHub Actions execução #336, commit `bc61f9dd`, concluída com sucesso em Linux/Python 3.12 e Windows/Python 3.14; em ambos, `Ruff lint` e `Run tests with coverage` terminaram com `success`. O utilizador apresentou a execução bem-sucedida. **B9.4 CONCLUÍDO E VALIDADO**. B9.5, estratégia futura de testes, é o próximo sub-bloco, ainda por implementar. `main` e tag `v0.2.0` permanecem inalteradas.

## B9.5 — Estratégia de testes para as próximas versões

Esta secção define critérios futuros; não implica implementar funcionalidades nem aumentar automaticamente o número de testes na V0.2. O estado da execução de cada bloco é registado em `docs/stabilization-v0.2.md` e `docs/status.md`.

### Base existente na V0.2

A árvore de testes da branch `dev` já separa `tests/unit/` e `tests/integration/`. Existem testes de domínio (`Instrument`, `Watchlist`, universos), serviços e providers simulados (`WatchlistService`, `MarketService`, Yahoo, Wikipedia, cache de universos), contratos/coordenação da interface, configuração e versão, além de integração de SQLite, repository, localização/migração de dados e Alembic. Estes ficheiros demonstram a existência dos cenários de teste, não comprovam cobertura total de cada funcionalidade. Parte da UI é verificada por contratos e componentes headless; não existe garantia de testes end-to-end completos de PySide6.

O CI executa `python -m ruff check src tests` e `python -m pytest -q --cov=bolsa --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov` em Linux/Python 3.12 e Windows/Python 3.14. Os artefactos de cobertura são separados por ambiente; não se impõe um limiar percentual. O ponto de partida histórico do gate era 39 testes e cerca de 55% de cobertura; não interpretar estes números como métricas atuais.

### Critérios gerais para novas funcionalidades

1. **Domínio e cálculos financeiros.** Preferir testes unitários determinísticos para invariantes, arredondamentos, moedas, valores nulos, erros e fronteiras. Na V0.3, posições devem resultar das transações e os cálculos de preço médio, PnL e comissões devem ser comparados com exemplos numéricos construídos manualmente. Não substituir testes com valores esperados por uma mera verificação de que o código executou.
2. **Persistência e migrações.** Testar integração com bases SQLite temporárias e isoladas: criar, ler, atualizar, reiniciar, rollback, integridade referencial e evolução de schema. Garantir sempre que bases e backups reais do utilizador nunca são usados pelos testes. Para cada nova migração Alembic, testar base nova, upgrade a partir da revisão anterior e recusa segura de revisão incompatível, quando aplicável. Não apagar instrumentos órfãos como efeito indireto de testes ou limpezas.
3. **Integração de serviços e fronteiras.** Testar com doubles/fakes que implementem os ports. Abranger sucesso, ausência de informação, formatos inesperados, indisponibilidade e recuperação, distinguindo falhas de provider de estados de negócio. Proibir dependência de respostas atuais do Yahoo/Wikipedia na suite obrigatória; testes reais de rede, se criados, devem ser opcionais e explicitamente separados do CI.
4. **Interface PySide6.** Manter testes headless para a lógica e contratos sem QtWidgets sempre que possível. Em futuras funcionalidades com risco de regressão visual ou de sinais, introduzir testes Qt específicos em ambiente controlado, verificando inicialização sem escrita, estados desconhecidos, seleção, bloqueio durante operações e comportamento de erros. Não adicionar teste de interface apenas para obter uma percentagem.
5. **Concorrência e cache.** Testar coordenação de tarefas em background, prevenção de atualizações concorrentes, preservação do último valor conhecido e ausência de alterações persistentes inesperadas. Usar sincronização determinística em vez de `sleep` ou temporizações frágeis.
6. **Análise, estratégias e backtesting (V0.4–V0.6).** Testar indicadores com séries artificiais e valores de referência, dados em falta, alinhamento temporal, custos, slippage e ausência de antecipação de dados. Um backtest não pode utilizar informação futura nas decisões anteriores.
7. **IA (V0.8 e posteriores).** Validar divisões cronológicas, ausência de leakage entre treino/validação/teste, ajuste de transformações apenas no treino, reprodutibilidade de seeds e versões, baselines, métricas fora da amostra e calibração. Nunca aceitar apenas accuracy agregada como demonstração de utilidade económica. Preservar a distinção entre previsão, classificação/ranking e decisão.
8. **Regressões.** Cada bug corrigido deve ganhar, quando viável, um teste que falhe antes da correção e passe depois. As novas funcionalidades devem contemplar cenários normais, limites e erros. Os testes não devem depender da ordem de execução nem modificar ficheiros do utilizador.

### Critérios de verificação por fase

- **Antes de integrar mudanças em `dev`:** executar os testes relevantes, `python -m ruff check src tests` e rever o diff.
- **Antes de declarar um bloco validado:** suite completa e CI Linux/Windows aprovados, mais validação funcional Windows do utilizador quando houver comportamento da aplicação; documentar exceções e testes não executados.
- **No fecho B11:** recolher número efetivo de testes e percentagem de cobertura, comparar com o baseline S0, identificar módulos pouco testados e confirmar que não houve perda injustificada de cobertura. A cobertura é indicador diagnóstico, não objetivo isolado.
- **Antes de cada versão futura:** atualizar a matriz de risco e respetivos testes quando surgirem novas operações de carteira, cálculos, migrações, UI ou modelos; evitar mecanismos de teste complexos antes de serem necessários.

### Adoção de ferramentas

O conjunto atual `pytest`, `pytest-cov` e `ruff` é suficiente para este ciclo. `pytest-qt`, testes de propriedades ou bibliotecas adicionais poderão ser avaliados apenas quando uma funcionalidade concreta justificar o custo. Não se introduzem dependências, testes nem alterações funcionais neste B9.5.

### Situações pendentes e fronteiras

O B9.5 documenta a estratégia, mas **não** declara cobertura completa de UI, cargas de rede, sistemas operativos ou dados de produção. A avaliação das advertências GitHub Actions relativas a Node.js 20 e à mudança de `ubuntu-latest` permanece uma ação de manutenção/fecho a acompanhar, sem a confundir com validação de código Python. A revisão global de coerência dos documentos cabe ao B10, e a medição final com valores efetivos cabe ao B11.

Validação B9.5 e fecho B9 (2026-10-10): o utilizador aprovou expressamente a estratégia documental de testes. **B9.5 CONCLUÍDO E VALIDADO** e **B9 (B9.1–B9.5) CONCLUÍDO E VALIDADO**. Próximo bloco: B10, auditoria de coerência canónica; primeiro analisar e propor correções sem alterar documentos antes da validação do desenho. Os itens avulsos I1–I5 e o fecho B11 continuam obrigatórios. A `main` e a tag `v0.2.0` permanecem intocadas.

Validação B10 (2026-10-11): o utilizador confirmou expressamente a revisão documental. **B10 CONCLUÍDO E VALIDADO**. Os itens avulsos I1–I5 permanecem obrigatórios antes do fecho B11. Próximo passo: analisar o I1 (escrita atómica da cache de universos), sem implementar antes da validação do desenho. `main` e tag `v0.2.0` permanecem intocadas.

### Verificação I1 — Escrita atómica da cache

Na `dev`, executar `git pull --ff-only origin dev`, `python -m ruff check src tests` e `python -m pytest -q`; verificar jobs Linux/Windows. Em funcionamento normal, os universos devem carregar e reutilizar cache como antes. Os testes de regressão em `tests/unit/test_cached_universe_provider.py` simulam falhas na gravação e na substituição, exigindo preservação do JSON anterior e ausência de ficheiros temporários residuais. I1 só fica validado depois da confirmação do utilizador.

Validação I1 (2026-10-11): o utilizador confirmou os testes locais e autorizou avançar. **I1 — ESCRITA ATÓMICA DA CACHE DE UNIVERSOS CONCLUÍDO E VALIDADO.** Próximo item I2: analisar a política de preservação dos instrumentos órfãos; primeiro apresentar o desenho, sem alterações funcionais antes da aprovação. I3–I5 e B11 continuam pendentes; `main` e tag `v0.2.0` intactas.

### I2 — Regra de persistência de instrumentos

Remover um ticker da Watchlist elimina apenas a associação em `watchlist_items`. A entidade em `instruments` permanece intencionalmente, mesmo sem associações, para possível reutilização e para evitar perdas com as futuras relações de Portfolio. Não realizar limpeza automática de órfãos. O teste de integração `test_watchlist_repository_persists_removal` verifica esta regra. Decisão I2 validada pelo utilizador em 2026-10-11, sem alteração funcional ou migração.

### I3 — Inclusão responsável de PDFs

A regra global `*.pdf` foi removida do `.gitignore` para permitir documentação técnica legítima em PDF. Continuam ignoradas pastas `statements/`, `extracts/`, `extratos/` e os padrões financeiros privados já existentes. Antes de adicionar PDFs, confirmar que não contêm informação pessoal, credenciais ou posições reais. Decisão de desenho aprovada em 2026-10-11; implementação à espera de validação final.
