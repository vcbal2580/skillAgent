# SkillAgent - Windows one-time setup script
# Usage: .\scripts\setup.ps1
# Run this once after cloning the repository.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n=== SkillAgent Setup ===" -ForegroundColor Cyan

# 1. Create virtual environment
if (-Not (Test-Path ".venv")) {
    Write-Host "`n[1/4] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "`n[1/4] Virtual environment already exists, skipping." -ForegroundColor Green
}

# 2. Activate
Write-Host "`n[2/4] Activating virtual environment..." -ForegroundColor Yellow
& ".venv\Scripts\Activate.ps1"

# 3. Install dependencies
Write-Host "`n[3/4] Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# 4. Install project in editable mode (generates hi.exe)
Write-Host "`n[4/4] Installing project (generates 'hi' command)..." -ForegroundColor Yellow
pip install -e .

# 5. Config file
if (-Not (Test-Path "config.yaml")) {
    Write-Host "`n[+] Copying config template..." -ForegroundColor Yellow
    Copy-Item "config.example.yaml" "config.yaml"
    Write-Host "    --> Please edit config.yaml and fill in your API key." -ForegroundColor Magenta
} else {
    Write-Host "`n[+] config.yaml already exists, skipping." -ForegroundColor Green
}

Write-Host "`n=== Setup complete! ===" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Edit config.yaml and set your API key" -ForegroundColor White
Write-Host "  2. Activate venv: .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  3. Run: hi vcbal" -ForegroundColor White
