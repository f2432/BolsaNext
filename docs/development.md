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
