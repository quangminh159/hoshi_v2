# Chạy ngrok và in link public ra Terminal
# Cách dùng: .\start_ngrok.ps1
# (mặc định forward cổng 8000)

param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ngrok = Join-Path $PSScriptRoot "ngrok.exe"

if (-not (Test-Path $ngrok)) {
    Write-Host "Khong tim thay ngrok.exe trong $PSScriptRoot" -ForegroundColor Red
    exit 1
}

# Tat ngrok cu neu con treo
Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "Dang mo ngrok -> http://127.0.0.1:$Port ..." -ForegroundColor Cyan
Start-Process -FilePath $ngrok -ArgumentList @("http", "$Port") -WorkingDirectory $PSScriptRoot -WindowStyle Minimized

$url = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $tunnels = (Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2).tunnels
        $https = $tunnels | Where-Object { $_.public_url -like "https://*" } | Select-Object -First 1
        if (-not $https) {
            $https = $tunnels | Select-Object -First 1
        }
        if ($https.public_url) {
            $url = $https.public_url
            break
        }
    } catch {
        # cho ngrok khoi dong
    }
}

Write-Host ""
if ($url) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  LINK NGROK (copy dung link nay):" -ForegroundColor Green
    Write-Host "  $url" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Dashboard: http://127.0.0.1:4040" -ForegroundColor DarkGray
    Write-Host "Nho chay daphne o cong $Port truoc." -ForegroundColor DarkGray
    Write-Host ""
    try {
        Set-Clipboard -Value $url
        Write-Host "Da copy link vao clipboard." -ForegroundColor Cyan
    } catch {
        # bo qua neu khong copy duoc
    }
} else {
    Write-Host "Chua lay duoc link. Mo http://127.0.0.1:4040 de xem." -ForegroundColor Red
    exit 1
}
