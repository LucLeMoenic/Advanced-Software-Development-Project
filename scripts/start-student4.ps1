#!/usr/bin/env pwsh
<#
.SYNOPSIS
Starts the Student 4 application through Docker Compose.

.PARAMETER NoBuild
Starts existing images without rebuilding them.

.EXAMPLE
./scripts/start-student4.ps1
#>
[CmdletBinding()]
param(
    [switch]$NoBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-CheckedDocker {
    param(
        [Parameter(Mandatory)]
        [string[]]$ArgumentList,

        [Parameter(Mandatory)]
        [string]$FailureMessage
    )

    & docker @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Start-Student4Application {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is not installed or is not available on PATH. Start Docker Desktop and try again."
    }

    Invoke-CheckedDocker @("info") "Docker Desktop is not running."
    $repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
    $environmentPath = Join-Path $repositoryRoot ".env"
    if (-not (Test-Path $environmentPath)) {
        Copy-Item (Join-Path $repositoryRoot ".env.example") $environmentPath
    }

    Push-Location -LiteralPath $repositoryRoot
    try {
        $buildArgument = if ($NoBuild) { @() } else { @("--build") }
        Invoke-CheckedDocker (@("compose", "up", "--detach") + $buildArgument + @("--wait", "student4-frontend")) "Student 4 services failed to start."
        Invoke-CheckedDocker (@("compose", "up", "--detach", "--no-deps") + $buildArgument + @("--wait", "shared-frontend")) "The shared frontend failed to start."
    }
    finally {
        Pop-Location
    }

    [PSCustomObject]@{
        Application = "http://localhost:5100/budget/"
        Frontend = "http://localhost:5104"
        Backend = "http://localhost:5204"
        DatabaseApi = "http://localhost:5304"
        Status = "Started"
    }
}

if ($MyInvocation.InvocationName -ne ".") {
    Start-Student4Application
}