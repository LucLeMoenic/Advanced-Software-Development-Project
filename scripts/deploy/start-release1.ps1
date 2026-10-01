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
Ollama is reused when reachable. MCP and RAG are refreshed on every start so
dependency, prompt and model changes take effect. NativeHost must be a local
loopback or private IPv4 address; no firewall changes are performed.
-Stop shuts down every Compose service, the MCP and RAG servers and Ollama
(installed models stay on disk). Native logs are kept under $env:TEMP\asd-release1.

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
    [ValidateNotNullOrEmpty()]
    [string]$Model = $(if ($env:APPLICATION_MODEL) { $env:APPLICATION_MODEL } else { "llama3.2:3b" }),
    [string]$NativeHost = $(if ($env:LOCAL_AI_HOST -and $env:LOCAL_AI_HOST -ne "host-gateway") { $env:LOCAL_AI_HOST } else { "127.0.0.1" })
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$stateDirectory = Join-Path $env:TEMP "asd-release1"
$composeFiles = @("-f", "docker-compose.yml", "-f", "docker-compose.gpu.yml")
$binDirectory = if ($IsWindows) { "Scripts" } else { "bin" }

function Set-NativeConfiguration([string]$Address, [string]$SelectedModel) {
    $parsed = $null
    if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$parsed) -or
        $parsed.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
        throw "NativeHost must be a local loopback or private IPv4 address."
    }
    $octets = $parsed.GetAddressBytes()
    $loopback = [System.Net.IPAddress]::IsLoopback($parsed)
    $private = $octets[0] -eq 10 -or ($octets[0] -eq 172 -and $octets[1] -ge 16 -and $octets[1] -le 31) -or
        ($octets[0] -eq 192 -and $octets[1] -eq 168)
    if (-not $loopback -and (-not $private -or -not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $Address -ErrorAction SilentlyContinue))) {
        throw "NativeHost must belong to a local private interface; wildcard/public binds are not allowed."
    }
    $env:APPLICATION_MODEL = $SelectedModel
    $env:RAG_MODEL = $SelectedModel
    $env:MCP_HOST = $Address
    $env:MCP_PORT = "5400"
    $env:OLLAMA_HOST = "${Address}:11434"
    $env:OLLAMA_URL = "http://${Address}:11434"
    $env:MCP_SERVER_URL = "http://host.docker.internal:5400/mcp"
    $env:RAG_SERVER_URL = "http://host.docker.internal:5500"
    $env:LOCAL_AI_HOST = if ($loopback) { "host-gateway" } else { $Address }
    $env:AI_ENABLED = "true"
    $env:MCP_ENABLED = "true"
    $env:RAG_ENABLED = "true"
}

function Test-Url([string]$Url, [int[]]$ExpectedStatus = @(200)) {
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -SkipHttpErrorCheck
        return [int]$response.StatusCode -in $ExpectedStatus
    }
    catch {
        return $false
    }
}

function Wait-Url([string]$Name, [string]$Url, [int]$Seconds = 30, [int[]]$ExpectedStatus = @(200)) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url $ExpectedStatus) {
            Write-Host "  $Name is ready at $Url" -ForegroundColor Green
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name did not respond at $Url within $Seconds seconds. See the logs in $stateDirectory."
}

function Start-Native([string]$Name, [string]$FilePath, [string[]]$Arguments) {
    Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $repositoryRoot `
        -RedirectStandardOutput (Join-Path $stateDirectory "$Name.log") `
        -RedirectStandardError (Join-Path $stateDirectory "$Name.err.log") `
        -WindowStyle Hidden | Out-Null
}

# Stops whatever is listening on the port, with its child processes. Stopping by port rather
# than by a saved process ID also catches services left over from an earlier session, and the
# venv python launcher's child interpreter.
function Stop-Port([string]$Name, [int]$Port) {
    $owners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($owner in $owners) {
        taskkill /T /F /PID $owner *> $null
        Write-Host "  Stopped $Name (port $Port)."
    }
}

function Get-VenvPython([string]$Venv, [string]$Requirements) {
    $python = Join-Path $Venv "$binDirectory/python$(if ($IsWindows) { '.exe' })"
    if (-not (Test-Path $python)) {
        Write-Host "  Creating virtual environment $Venv"
        $launcher = if (Get-Command py -ErrorAction SilentlyContinue) { @("py", "-3") } else { @("python") }
        & $launcher[0] @($launcher | Select-Object -Skip 1) -m venv $Venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create $Venv. Install Python 3.11 or later." }
    }
    & $python -m pip install --quiet -r $Requirements | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Could not install $Requirements." }
    return $python
}

Push-Location $repositoryRoot
try {
    & (Join-Path $PSScriptRoot "start-docker.ps1")

    if ($Stop) {
        Write-Host "Stopping Docker Compose services..."
        docker compose @composeFiles down
        if ($LASTEXITCODE -ne 0) { throw "docker compose down failed." }

        Write-Host "Stopping native services..."
        Stop-Port "MCP server" 5400
        Stop-Port "RAG server" 5500
        # Stop the Ollama tray app first so it cannot restart the server.
        Get-Process "ollama app" -ErrorAction SilentlyContinue | Stop-Process -Force
        Stop-Port "Ollama" 11434
        Write-Host "Release 1 is stopped. Installed Ollama models stay on disk." -ForegroundColor Green
        return
    }

    New-Item -ItemType Directory -Force -Path $stateDirectory | Out-Null

    Set-NativeConfiguration $NativeHost $Model
    $ollamaUrl = $env:OLLAMA_URL
    $mcpUrl = "http://${NativeHost}:5400/mcp"
    $ragUrl = "http://${NativeHost}:5500"
    $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
    $ollama = if ($ollamaCommand) { $ollamaCommand.Source } else { Join-Path $env:LOCALAPPDATA "Programs/Ollama/ollama.exe" }
    Write-Host "Starting native services (not containerised)..."
    if (Test-Url "$ollamaUrl/api/tags") {
        Write-Host "  Ollama is already running." -ForegroundColor Green
    }
    elseif (Test-Path $ollama) {
        # The tray app can be running with a server that failed to start; it would hold the port.
        Get-Process "ollama app" -ErrorAction SilentlyContinue | Stop-Process -Force
        Stop-Port "unresponsive Ollama" 11434
        Start-Native "ollama" $ollama @("serve")
        Wait-Url "Ollama" "$ollamaUrl/api/tags"
    }
    else {
        throw "Ollama is not installed. Install it before starting Release 1."
    }

    if (Test-Url "$ollamaUrl/api/tags") {
        $installed = @((Invoke-RestMethod "$ollamaUrl/api/tags").models | ForEach-Object { $_.name })
        if ($installed -notcontains $Model) {
            Write-Host "  Pulling $Model (first run only)..."
            & $ollama pull $Model
            if ($LASTEXITCODE -ne 0) { throw "Could not pull $Model." }
        }
        # Preload the model so the first request is not a cold load against the 12-20 s deadlines.
        Invoke-RestMethod -Method Post -Uri "$ollamaUrl/api/generate" -TimeoutSec 120 `
            -ContentType "application/json" -Body (@{ model = $Model; keep_alive = "30m" } | ConvertTo-Json) | Out-Null
        Write-Host "  $Model is loaded." -ForegroundColor Green
    }

    Stop-Port "MCP server" 5400
    Stop-Port "RAG server" 5500
    $mcpPython = Get-VenvPython $McpVenv "ai-services/mcp-server/requirements.txt"
    $ragPython = Get-VenvPython $RagVenv "ai-services/rag-server/requirements.txt"
    Start-Native "mcp" $mcpPython @("ai-services/mcp-server/server.py")
    Wait-Url "MCP server" $mcpUrl -ExpectedStatus @(400, 406)
    Start-Native "rag" $ragPython @("-m", "uvicorn", "server:app", "--host", $NativeHost, "--port", "5500", "--app-dir", "ai-services/rag-server")
    Wait-Url "RAG server" "$ragUrl/health"

    Write-Host "Starting all Docker Compose services with MCP and RAG enabled (first build takes a few minutes)..."
    docker compose @composeFiles up -d --build --wait
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed to start. Native services are still running; run with -Stop to shut them down."
    }

    docker compose @composeFiles exec -T student1-backend curl --fail -sS -m 5 -o /dev/null http://host.docker.internal:5500/health
    if ($LASTEXITCODE -ne 0) { throw "Student 1 cannot reach RAG. Check NativeHost and trusted-host network access." }
    $probe = @'
import os, requests
from ai_clients import McpClient, validate_summary
backend = 'http://127.0.0.1:8080/api'
response = requests.get(backend + '/capabilities', timeout=5)
response.raise_for_status()
assert response.json() == dict(aiEnabled=True, mcpEnabled=True, ragEnabled=True)
response = requests.get(os.environ['RAG_SERVER_URL'] + '/health', timeout=5)
response.raise_for_status()
assert response.json()['status'] == 'ok'
response = requests.post(os.environ['OLLAMA_URL'] + '/api/generate', json=dict(model=os.environ['APPLICATION_MODEL'], stream=False, keep_alive='30m'), timeout=20)
response.raise_for_status()
assert response.json()['done'] is True
response = requests.get(backend + '/trips', timeout=5)
response.raise_for_status()
trips = response.json()
assert trips, 'A saved trip is required for the read-only MCP check'
trip_id = trips[0]['id']
validate_summary(McpClient(os.environ['MCP_SERVER_URL']).summary(trip_id), trip_id)
print('Student 2: enabled modes, RAG health, configured model and real MCP tool result verified; no saved data changed.')
'@
    docker compose @composeFiles exec -T student2-backend python -c $probe
    if ($LASTEXITCODE -ne 0) { throw "Student 2 native-service validation failed. Check NativeHost and trusted-host network access. No firewall rules were changed." }

    Write-Host ""
    Write-Host "Release 1 is running:" -ForegroundColor Green
    Write-Host "  Shared entry page:  http://localhost:5100"
    Write-Host "  Accommodation:      http://localhost:5100/accommodation/"
    Write-Host "  MCP server:         $mcpUrl"
    Write-Host "  RAG server:         $ragUrl/health"
    Write-Host "  Native logs:        $stateDirectory"
    Write-Host "  Stop everything:    pwsh -File scripts/deploy/start-release1.ps1 -Stop"
}
finally {
    Pop-Location
}
