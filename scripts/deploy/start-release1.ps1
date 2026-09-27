<#
.SYNOPSIS
Starts the complete Release 1 application: native Ollama, the shared MCP and RAG
servers, then every Docker Compose service with MCP and RAG enabled.

.DESCRIPTION
Ollama, MCP and RAG run natively on the host, as the Release 1 brief requires;
they are never Compose services. Native Ollama uses the GPU automatically when
one is available. docker-compose.gpu.yml is included for compatibility but
contains no services.

The first run creates the MCP and RAG Python virtual environments (outside the
repository by default) and pulls the application model if it is missing.
Native process IDs and logs are kept under $env:TEMP\asd-release1.

.EXAMPLE
pwsh -File scripts/deploy/start-release1.ps1

.EXAMPLE
pwsh -File scripts/deploy/start-release1.ps1 -Stop
#>
[CmdletBinding()]
param(
    [switch]$Stop,
    [string]$McpVenv = (Join-Path $PSScriptRoot "../../../venv-mcp"),
    [string]$RagVenv = (Join-Path $PSScriptRoot "../../../venv-rag"),
    [string]$Model = $(if ($env:APPLICATION_MODEL) { $env:APPLICATION_MODEL } else { "llama3.2:3b" })
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$stateDirectory = Join-Path $env:TEMP "asd-release1"
$stateFile = Join-Path $stateDirectory "processes.json"
$composeFiles = @("-f", "docker-compose.yml", "-f", "docker-compose.gpu.yml")
$binDirectory = if ($IsWindows) { "Scripts" } else { "bin" }

function Test-Url([string]$Url) {
    try {
        Invoke-WebRequest -Uri $Url -TimeoutSec 2 -SkipHttpErrorCheck | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Wait-Url([string]$Name, [string]$Url, [int]$Seconds = 30) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url) {
            Write-Host "  $Name is ready at $Url" -ForegroundColor Green
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name did not respond at $Url within $Seconds seconds. See the logs in $stateDirectory."
}

function Start-Native([string]$Name, [string]$FilePath, [string[]]$Arguments) {
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $repositoryRoot `
        -RedirectStandardOutput (Join-Path $stateDirectory "$Name.log") `
        -RedirectStandardError (Join-Path $stateDirectory "$Name.err.log") `
        -WindowStyle Hidden -PassThru
    return $process.Id
}

function Get-VenvPython([string]$Venv, [string]$Requirements) {
    $python = Join-Path $Venv "$binDirectory/python$(if ($IsWindows) { '.exe' })"
    if (-not (Test-Path $python)) {
        Write-Host "  Creating virtual environment $Venv"
        $launcher = if (Get-Command py -ErrorAction SilentlyContinue) { @("py", "-3") } else { @("python") }
        & $launcher[0] @($launcher | Select-Object -Skip 1) -m venv $Venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create $Venv. Install Python 3.11 or later." }
        & $python -m pip install --quiet -r $Requirements
        if ($LASTEXITCODE -ne 0) { throw "Could not install $Requirements." }
    }
    return $python
}

Push-Location $repositoryRoot
try {
    if ($Stop) {
        if (Test-Path $stateFile) {
            $started = Get-Content $stateFile -Raw | ConvertFrom-Json
            foreach ($entry in $started.PSObject.Properties) {
                Stop-Process -Id $entry.Value -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped $($entry.Name) (process $($entry.Value))."
            }
            Remove-Item $stateFile
        }
        docker compose @composeFiles down
        return
    }

    New-Item -ItemType Directory -Force -Path $stateDirectory | Out-Null
    if (Test-Path $stateFile) {
        throw "Release 1 native services may already be running. Run with -Stop first."
    }
    $started = [ordered]@{}

    Write-Host "Starting native services (not containerised)..."
    if (Test-Url "http://127.0.0.1:11434/api/tags") {
        Write-Host "  Ollama is already running." -ForegroundColor Green
    }
    elseif (Get-Command ollama -ErrorAction SilentlyContinue) {
        $started.ollama = Start-Native "ollama" "ollama" @("serve")
        Wait-Url "Ollama" "http://127.0.0.1:11434/api/tags"
    }
    else {
        Write-Warning "Ollama is not installed. The app runs, but lookup extraction, grounded answers and AI ranking return 'unavailable'."
    }

    if (Test-Url "http://127.0.0.1:11434/api/tags") {
        $installed = (Invoke-RestMethod "http://127.0.0.1:11434/api/tags").models.name
        if ($installed -notcontains $Model) {
            Write-Host "  Pulling $Model (first run only)..."
            ollama pull $Model
            if ($LASTEXITCODE -ne 0) { throw "Could not pull $Model." }
        }
        # Preload the model so the first request is not a cold load against the 12-20 s deadlines.
        Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:11434/api/generate" -TimeoutSec 120 `
            -ContentType "application/json" -Body (@{ model = $Model; keep_alive = "30m" } | ConvertTo-Json) | Out-Null
        Write-Host "  $Model is loaded." -ForegroundColor Green
    }

    $mcpPython = Get-VenvPython $McpVenv "ai-services/mcp-server/requirements.txt"
    $ragPython = Get-VenvPython $RagVenv "ai-services/rag-server/requirements.txt"
    $started.mcp = Start-Native "mcp" $mcpPython @("ai-services/mcp-server/server.py")
    $started.rag = Start-Native "rag" $ragPython @("-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "5500", "--app-dir", "ai-services/rag-server")
    $started | ConvertTo-Json | Set-Content $stateFile
    Wait-Url "MCP server" "http://127.0.0.1:5400/mcp"
    Wait-Url "RAG server" "http://127.0.0.1:5500/health"

    Write-Host "Starting all Docker Compose services with MCP and RAG enabled (first build takes a few minutes)..."
    $env:MCP_ENABLED = "true"
    $env:RAG_ENABLED = "true"
    docker compose @composeFiles up -d --build --wait
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed to start. Native services are still running; run with -Stop to shut them down."
    }

    docker compose @composeFiles exec -T student1-backend curl -sS -m 5 -o /dev/null http://host.docker.internal:5500/health
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "The backend container cannot reach the native services. See section 3 of student-1/docs/release-1-runbook.md (LOCAL_AI_HOST)."
    }

    Write-Host ""
    Write-Host "Release 1 is running:" -ForegroundColor Green
    Write-Host "  Shared entry page:  http://localhost:5100"
    Write-Host "  Accommodation:      http://localhost:5100/accommodation/"
    Write-Host "  MCP server:         http://127.0.0.1:5400/mcp"
    Write-Host "  RAG server:         http://127.0.0.1:5500/health"
    Write-Host "  Native logs:        $stateDirectory"
    Write-Host "  Stop everything:    pwsh -File scripts/deploy/start-release1.ps1 -Stop"
}
finally {
    Pop-Location
}
