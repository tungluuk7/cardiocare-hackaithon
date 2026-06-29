# Tai va cai ngrok cho demo (Windows amd64)
# Chay 1 lan:  .\setup_ngrok.ps1
# Sau do them authtoken (lay mien phi tai https://dashboard.ngrok.com/get-started/your-authtoken):
#   .\ngrok.exe config add-authtoken <TOKEN_CUA_BAN>
# Roi chay:  .\run.ps1 -Share

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path ".\ngrok.exe") {
    Write-Host "ngrok.exe da co san trong thu muc nay." -ForegroundColor Green
} else {
    $url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
    $zip = "$env:TEMP\ngrok.zip"
    Write-Host "==> Tai ngrok..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $url -OutFile $zip
    Write-Host "==> Giai nen vao thu muc du an..." -ForegroundColor Cyan
    Expand-Archive -Path $zip -DestinationPath $PSScriptRoot -Force
    Remove-Item $zip -Force
    Write-Host "ngrok.exe da san sang." -ForegroundColor Green
}

Write-Host ""
Write-Host "BUOC TIEP THEO:" -ForegroundColor Yellow
Write-Host "  1. Dang ky tai khoan mien phi: https://dashboard.ngrok.com/signup"
Write-Host "  2. Copy authtoken tai: https://dashboard.ngrok.com/get-started/your-authtoken"
Write-Host "  3. Chay:  .\ngrok.exe config add-authtoken <TOKEN_CUA_BAN>"
Write-Host "  4. Chay demo:  .\run.ps1 -Share"
Write-Host ""
Write-Host "KHONG MUON DANG KY? Dung Cloudflare Tunnel (khong can tai khoan) - xem DEMO.md" -ForegroundColor DarkGray
