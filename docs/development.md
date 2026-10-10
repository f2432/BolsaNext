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

O workflow `.github/workflows/tests.yml` executa os testes automaticamente em:

- pushes para `main`;
- pull requests para `main`.

O CI usa Python 3.12 e instala o projeto através de:

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

O workflow `.github/workflows/tests.yml`, na branch `dev`, mede cobertura dos testes com `python -m pytest -q --cov=bolsa --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov`. No separador Actions do GitHub, abrir a execução de `tests` para o commit mais recente da `dev`, consultar o passo `Run tests with coverage` e descarregar, em `Artifacts`, `coverage-python-3.12-ubuntu`. O artefacto contém `coverage.xml` e `htmlcov/index.html` (abrir localmente). Conservação: 14 dias. Não existe `fail-under`; cobertura inferior a 55% é observação a analisar, não bloqueio automático. Para reprodução local, usar o mesmo comando. Este registo é de implementação, ainda pendente de validação do utilizador.

## B9.2 — Testes de CI em Linux e Windows

O workflow `tests.yml` executa testes em duas combinações: `ubuntu-latest` com Python 3.12 e `windows-latest` com Python 3.14. Pushes em `main` e `dev`, bem como pull requests para ambas, disparam o workflow. `fail-fast: false` permite consultar os dois resultados mesmo em caso de falha de um deles. A cobertura é recolhida nos dois ambientes e os artefactos `coverage-linux-py312` e `coverage-windows-py314` são distintos. Em GitHub Actions, abrir a execução mais recente da `dev` e confirmar o sucesso dos dois jobs e a presença de ambos os artefactos. O Python 3.14 de CI aproxima-se do Python 3.14.5 local sem impor a mesma revisão de patch. A exceção local de SQLAlchemy pure-Python causada por Windows App Control mantém-se documentada separadamente. **B9.1 concluído e validado**, **B9.2 a aguardar confirmação do CI e validação do utilizador**.

Validação B9.2 (2026-10-10): o utilizador confirmou a conclusão da verificação solicitada do CI Linux/Windows. **B9.2 CONCLUÍDO E VALIDADO**. Segue-se B9.3, auditoria e decisão das dependências, sem alterações ao `pyproject.toml` antes da aprovação do desenho. `main` e tag `v0.2.0` continuam inalteradas.
