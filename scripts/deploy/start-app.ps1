param(
    [switch]$Gpu
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$entryUrl = "http://localhost:5100"
Push-Location $repositoryRoot

try {
    $composeFiles = @("-f", "docker-compose.yml")
    if ($Gpu) {
        Write-Host "Release 1 uses native Ollama; configure GPU acceleration in the host runtime."
    }

    docker compose @composeFiles up -d --build --wait
    if ($LASTEXITCODE -ne 0) {
        throw "The integrated application failed to start."
    }

    Write-Host ""
    Write-Host "The integrated application is ready:" -ForegroundColor Green
    Write-Host "  Shared entry page: $entryUrl"
    Write-Host "  Accommodation:     $entryUrl/accommodation/"
    Write-Host ""

    docker compose @composeFiles ps
    Start-Process $entryUrl
}
finally {
    Pop-Location
}
