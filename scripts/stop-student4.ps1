#!/usr/bin/env pwsh
<#
.SYNOPSIS
Stops the Student 4 application containers.

.EXAMPLE
./scripts/stop-student4.ps1
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Stop-Student4Application {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is not installed or is not available on PATH."
    }

    $repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
    Push-Location -LiteralPath $repositoryRoot
    try {
        & docker compose stop shared-frontend student4-frontend student4-backend student4-database
        if ($LASTEXITCODE -ne 0) {
            throw "Student 4 services failed to stop."
        }
    }
    finally {
        Pop-Location
    }

    [PSCustomObject]@{ Status = "Stopped" }
}

if ($MyInvocation.InvocationName -ne ".") {
    Stop-Student4Application
}