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

Na primeira execução é criada a pasta `data/` e a base de dados local:

```text
data/bolsanext.sqlite3
```

A base de dados é local e está excluída do Git.

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
