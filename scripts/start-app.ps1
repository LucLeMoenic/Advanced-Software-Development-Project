param(
    [switch]$Gpu
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$entryUrl = "http://localhost:5100"
Push-Location $repositoryRoot

try {
    $composeFiles = @("-f", "docker-compose.yml")
    if ($Gpu) {
        $dockerRuntimes = docker info --format "{{json .Runtimes}}"
        $gpuAvailable = (Get-Command nvidia-smi -ErrorAction SilentlyContinue) `
            -and $dockerRuntimes -match '"nvidia"'
        if (-not $gpuAvailable) {
            throw "GPU mode requires an NVIDIA GPU available through Docker."
        }

        $composeFiles += @("-f", "docker-compose.gpu.yml")
        Write-Host "Starting Ollama with NVIDIA GPU acceleration."
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
