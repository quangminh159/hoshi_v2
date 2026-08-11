# Backup Postgres local (Docker) — giữ 14 bản gần nhất
# Chạy: powershell -File .\scripts\backup_postgres.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Root) { $Root = "c:\hoshi_v2" }
$BackupDir = Join-Path $Root "backups"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $BackupDir "hoshi_$stamp.sql.gz"

Write-Host "Backing up moora-postgres -> $out"
docker exec moora-postgres pg_dump -U hoshi -d hoshi | Out-File -Encoding utf8 (Join-Path $BackupDir "hoshi_$stamp.sql")
# Nén nếu có gzip; không thì giữ .sql
if (Get-Command gzip -ErrorAction SilentlyContinue) {
  gzip -f (Join-Path $BackupDir "hoshi_$stamp.sql")
  Write-Host "OK $out"
} else {
  Write-Host "OK $($BackupDir)\hoshi_$stamp.sql (cài gzip để nén)"
}

Get-ChildItem $BackupDir -Filter "hoshi_*.sql*" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip 14 |
  Remove-Item -Force

Write-Host "Done. Restore ví dụ:"
Write-Host '  Get-Content backups\hoshi_XXXX.sql -Raw | docker exec -i moora-postgres psql -U hoshi -d hoshi'
