# CardioCare — script khởi động cho demo hackathon
# Chạy:  .\run.ps1            (khởi động server)
#        .\run.ps1 -Seed      (reset + seed dữ liệu demo rồi khởi động)
#        .\run.ps1 -Share     (khởi động server + ngrok public URL)
param(
    [switch]$Seed,
    [switch]$Share
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = ".\.venv\Scripts\python.exe"

# 1. Kiểm tra venv
if (-not (Test-Path $py)) {
    Write-Host "==> Tao virtualenv..." -ForegroundColor Cyan
    python -m venv .venv
}

# 2. Cai dependencies (chi khi thieu)
Write-Host "==> Kiem tra dependencies..." -ForegroundColor Cyan
& $py -m pip install -q -r requirements.txt

# 3. UTF-8 cho console (tieng Viet khong loi)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# 4. Seed du lieu demo neu yeu cau
if ($Seed) {
    Write-Host "==> Seed du lieu demo..." -ForegroundColor Cyan
    & $py seed_demo.py --reset
}

# 5. ngrok (tuy chon) — chay nen
if ($Share) {
    # Uu tien .\ngrok.exe trong thu muc du an (do setup_ngrok.ps1 tai ve), roi moi den PATH
    $ngrokPath = $null
    if (Test-Path ".\ngrok.exe") { $ngrokPath = ".\ngrok.exe" }
    elseif (Get-Command ngrok -ErrorAction SilentlyContinue) { $ngrokPath = "ngrok" }

    if ($null -eq $ngrokPath) {
        Write-Host "!! ngrok chua cai. Chay '.\setup_ngrok.ps1' truoc, hoac xem DEMO.md (muc 'Public URL')." -ForegroundColor Yellow
    } else {
        Write-Host "==> Mo ngrok tunnel port 8000..." -ForegroundColor Cyan
        Start-Process $ngrokPath -ArgumentList "http", "8000"
        Start-Sleep -Seconds 3
        try {
            $u = (Invoke-RestMethod http://127.0.0.1:4040/api/tunnels).tunnels[0].public_url
            Write-Host ""
            Write-Host "  PUBLIC URL : $u" -ForegroundColor Green
            Write-Host "  Dashboard  : $u/static/index.html" -ForegroundColor Green
            Write-Host "  ngrok UI   : http://127.0.0.1:4040" -ForegroundColor Green
            Write-Host ""
        } catch {
            Write-Host "  (Mo http://127.0.0.1:4040 de lay public URL)" -ForegroundColor Yellow
        }
    }
}

# 6. Khoi dong server
Write-Host "==> CardioCare chay tai http://localhost:8000" -ForegroundColor Green
Write-Host "    Dashboard : http://localhost:8000/static/index.html" -ForegroundColor Green
Write-Host "    API docs  : http://localhost:8000/docs" -ForegroundColor Green
Write-Host "    (Ctrl+C de dung)" -ForegroundColor DarkGray
Write-Host ""
& $py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
