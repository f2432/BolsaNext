param(
    [switch]$SkipPull,
    [switch]$SkipInstall,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$DevelopmentBranch = "dev"

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

function Get-CurrentBranch {
    $branch = git branch --show-current
    Stop-On-ExitCode "leitura da branch atual"
    return $branch.Trim()
}

Write-Host ""
Write-Host "=== BolsaNext ===" -ForegroundColor Cyan

$currentBranch = Get-CurrentBranch
Write-Host "Branch atual: $currentBranch" -ForegroundColor Cyan

if ($currentBranch -ne $DevelopmentBranch) {
    Write-Host ""
    Write-Host "Este script de desenvolvimento trabalha na branch '$DevelopmentBranch'." -ForegroundColor Yellow
    Write-Host "A mudar automaticamente para '$DevelopmentBranch'..." -ForegroundColor Yellow

    git fetch origin $DevelopmentBranch
    Stop-On-ExitCode "git fetch origin $DevelopmentBranch"

    git show-ref --verify --quiet "refs/heads/$DevelopmentBranch"
    if ($LASTEXITCODE -eq 0) {
        git switch $DevelopmentBranch
        Stop-On-ExitCode "git switch $DevelopmentBranch"
    }
    else {
        git switch --track "origin/$DevelopmentBranch"
        Stop-On-ExitCode "git switch --track origin/$DevelopmentBranch"
    }

    $currentBranch = Get-CurrentBranch
    Write-Host "Branch ativa: $currentBranch" -ForegroundColor Green
}

if (-not $SkipPull) {
    Write-Host ""
    Write-Host "[1/4] A atualizar a branch de desenvolvimento..." -ForegroundColor Yellow
    git pull --ff-only origin $DevelopmentBranch
    Stop-On-ExitCode "git pull origin $DevelopmentBranch"
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
Write-Host "Branch em teste: $DevelopmentBranch" -ForegroundColor Cyan
python -m bolsa.main
Stop-On-ExitCode "arranque do BolsaNext"
