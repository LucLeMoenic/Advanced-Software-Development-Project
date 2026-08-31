$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$entryUrl = "http://localhost:5100"
Push-Location $repositoryRoot

try {
    docker compose up -d --build --wait
    if ($LASTEXITCODE -ne 0) {
        throw "The integrated application failed to start."
    }

    Write-Host ""
    Write-Host "The integrated application is ready:" -ForegroundColor Green
    Write-Host "  Shared entry page: $entryUrl"
    Write-Host "  Accommodation:     $entryUrl/accommodation/"
    Write-Host ""

    docker compose ps
    Start-Process $entryUrl
}
finally {
    Pop-Location
}
