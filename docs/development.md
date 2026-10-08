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
