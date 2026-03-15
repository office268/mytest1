# Commit and push - run from project folder (e.g. right-click -> Run)
Set-Location $PSScriptRoot

Write-Host "Committing staged files..." -ForegroundColor Cyan
git commit -m "Add local PostgreSQL setup"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Commit failed or nothing to commit." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "Pushing to remote..." -ForegroundColor Cyan
git push

if ($LASTEXITCODE -eq 0) {
    Write-Host "Done." -ForegroundColor Green
}
