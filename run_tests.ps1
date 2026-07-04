# CardioCare — chạy test tự động bằng 1 lệnh (Windows).  .\run_tests.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "==> Tao virtualenv..." -ForegroundColor Cyan
    python -m venv .venv
}
Write-Host "==> Cai dependencies..." -ForegroundColor Cyan
& $py -m pip install -q -r requirements.txt

$env:PYTHONUTF8 = "1"
Write-Host "==> Chay pytest..." -ForegroundColor Green
& $py -m pytest
