<#
.SYNOPSIS
Makes sure the Docker Desktop engine is running, recovering from stale sockets.

.DESCRIPTION
After sleep, a crash or an unclean shutdown, Docker Desktop on Windows can leave
Unix socket files (for example sailor-ingest.sock or engine.sock) that Windows
will not let it rename or delete. Docker Desktop then shows "An unexpected error
occurred" on start-up, and every docker command fails with
"failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine".

If the engine is not answering, this script quits Docker Desktop, moves each
socket-only runtime folder aside (Docker recreates it), starts Docker Desktop and
waits for the engine. It never touches images, containers or volumes.

.EXAMPLE
pwsh -File scripts/deploy/start-docker.ps1
#>
[CmdletBinding()]
param([int]$TimeoutSeconds = 180)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-DockerEngine {
    # The docker CLI can hang while the engine is half started, so bound the check.
    $job = Start-Job { docker version --format "{{.Server.Version}}" 2>$null; $LASTEXITCODE -eq 0 }
    $finished = Wait-Job $job -Timeout 15
    $result = if ($finished) { (Receive-Job $job | Select-Object -Last 1) -eq $true } else { $false }
    Remove-Job $job -Force
    return $result
}

if (Test-DockerEngine) {
    Write-Host "Docker engine is running." -ForegroundColor Green
    return
}
if (-not $IsWindows) {
    throw "The Docker engine is not running. Start it and try again."
}

$dockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
if (-not (Test-Path $dockerDesktop)) {
    throw "Docker Desktop is not installed at $dockerDesktop."
}

Write-Host "Docker engine is not running. Restarting Docker Desktop and clearing stale sockets..."
Get-Process "Docker Desktop", "com.docker.backend", "com.docker.build" -ErrorAction SilentlyContinue |
    Stop-Process -Force
Start-Sleep -Seconds 3

$suffix = Get-Date -Format "yyyyMMddHHmmss"
foreach ($folder in @((Join-Path $env:LOCALAPPDATA "Docker\run"), (Join-Path $env:LOCALAPPDATA "docker-secrets-engine"))) {
    if (-not (Test-Path $folder)) { continue }
    $items = @(Get-ChildItem $folder -Force)
    # Only move folders that hold nothing but sockets (reparse points), so no real data is displaced.
    if ($items.Count -gt 0 -and -not ($items | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) })) {
        Rename-Item $folder "$(Split-Path $folder -Leaf).stale-$suffix"
        Write-Host "  Moved stale sockets out of $folder"
    }
}

# Folders moved aside earlier can usually be deleted once Windows releases the sockets (after a reboot).
Get-ChildItem $env:LOCALAPPDATA, (Join-Path $env:LOCALAPPDATA "Docker") -Directory -Filter "*.stale-*" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }

Start-Process $dockerDesktop
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    if (Test-DockerEngine) {
        Write-Host "Docker engine is running." -ForegroundColor Green
        return
    }
    Start-Sleep -Seconds 5
}
throw "Docker engine did not start within $TimeoutSeconds seconds. See $env:LOCALAPPDATA\Docker\log\host\com.docker.backend.exe.log."
