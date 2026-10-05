param(
    [switch]$SkipPull,
    [switch]$SkipInstall,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

function Stop-On-ExitCode {
    param(
        [string]$Step
    )

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Erro em: $Step" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "=== BolsaNext ===" -ForegroundColor Cyan

if (-not $SkipPull) {
    Write-Host ""
    Write-Host "[1/4] A atualizar o repositorio..." -ForegroundColor Yellow
    git pull --ff-only
    Stop-On-ExitCode "git pull"
} else {
    Write-Host ""
    Write-Host "[1/4] git pull ignorado." -ForegroundColor DarkGray
}

if (-not $SkipInstall) {
    Write-Host ""
    Write-Host "[2/4] A instalar/atualizar dependencias..." -ForegroundColor Yellow
    python -m pip install -e ".[dev]"
    Stop-On-ExitCode "instalacao das dependencias"
} else {
    Write-Host ""
    Write-Host "[2/4] instalacao de dependencias ignorada." -ForegroundColor DarkGray
}

if (-not $SkipTests) {
    Write-Host ""
    Write-Host "[3/4] A executar testes..." -ForegroundColor Yellow
    python -m pytest -q
    Stop-On-ExitCode "testes"
} else {
    Write-Host ""
    Write-Host "[3/4] testes ignorados." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[4/4] A iniciar BolsaNext..." -ForegroundColor Green
python -m bolsa.main
Stop-On-ExitCode "arranque do BolsaNext"
