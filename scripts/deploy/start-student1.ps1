$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Push-Location $repositoryRoot

try {
    $composeFiles = @("-f", "docker-compose.yml")
    Write-Host "AI Mode requires the shared native Ollama runtime on port 11434."

    Write-Host "Starting Student 1 services. Docker may take a few minutes to build images and pass health checks..."
    docker compose @composeFiles up -d --build --wait student1-frontend
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

    docker compose @composeFiles ps `
        student1-frontend `
        student1-backend `
        student1-database
}
finally {
    Pop-Location
}
