# Run project with PostgreSQL (start Docker first)
Set-Location $PSScriptRoot

Write-Host "Starting PostgreSQL..." -ForegroundColor Cyan
docker compose up -d

Write-Host "Starting app..." -ForegroundColor Cyan
python app.py
