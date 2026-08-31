$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repositoryRoot

try {
    docker compose up -d --build --wait student1-frontend
    if ($LASTEXITCODE -ne 0) {
        throw "Student 1 services failed to start."
    }

    Write-Host ""
    Write-Host "Student 1 services are ready:" -ForegroundColor Green
    Write-Host "  Frontend:         http://localhost:5101"
    Write-Host "  Backend:          http://localhost:5201"
    Write-Host "  Backend health:   http://localhost:5201/health"
    Write-Host "  Database API:     http://localhost:5301"
    Write-Host "  Database health:  http://localhost:5301/health"
    Write-Host "  Ollama:           http://localhost:11434"
    Write-Host ""

    docker compose ps `
        student1-frontend `
        student1-backend `
        student1-database `
        ollama
}
finally {
    Pop-Location
}
