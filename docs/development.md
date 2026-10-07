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
