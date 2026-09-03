#!/usr/bin/env pwsh
<#
.SYNOPSIS
Builds and smoke-tests the containerised Student 4 application without a live LLM.

.PARAMETER KeepRunning
Leaves the validated containers running after success.

.EXAMPLE
./scripts/validate-student4-docker.ps1
#>
[CmdletBinding()]
param(
    [switch]$KeepRunning
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

function Get-JsonArray {
    param(
        [Parameter(Mandatory)]
        [uri]$Uri
    )

    $response = Invoke-WebRequest -Uri $Uri
    return @($response.Content | ConvertFrom-Json)
}

function Test-Student4Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is not installed or is not available on PATH. Start Docker Desktop and try again."
    }

    Invoke-CheckedDocker @("info") "Docker Desktop is not running."
    $repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
    Push-Location -LiteralPath $repositoryRoot
    try {
        Invoke-CheckedDocker @("compose", "config", "--quiet") "Docker Compose configuration is invalid."
        Invoke-CheckedDocker @("compose", "build", "shared-frontend", "student4-frontend", "student4-backend", "student4-database") "Student 4 images failed to build."
        Invoke-CheckedDocker @("compose", "up", "--detach", "--no-deps", "--wait", "student4-database") "The database container failed to start."
        Invoke-CheckedDocker @("compose", "up", "--detach", "--no-deps", "--wait", "student4-backend") "The backend container failed to start."
        Invoke-CheckedDocker @("compose", "up", "--detach", "--no-deps", "--wait", "student4-frontend", "shared-frontend") "The frontend containers failed to start."

        Invoke-WebRequest -Uri "http://localhost:5100/health" | Out-Null
        Invoke-WebRequest -Uri "http://localhost:5104/health" | Out-Null
        Invoke-WebRequest -Uri "http://localhost:5204/health" | Out-Null
        Invoke-WebRequest -Uri "http://localhost:5304/health" | Out-Null

        $budgets = Get-JsonArray "http://localhost:5304/api/data/budgets"
        $expenses = Get-JsonArray "http://localhost:5304/api/data/expenses"
        if ($budgets.Count -lt 10 -or $expenses.Count -lt 10) {
            throw "Student 4 seed counts are below the required minimum."
        }

        $dashboard = Invoke-RestMethod -Uri "http://localhost:5204/api/dashboard?journeyLabel=Sydney%20Weekender"
        if ($dashboard.categories.Count -lt 1) {
            throw "The backend dashboard smoke test returned no categories."
        }

        $advice = Invoke-RestMethod `
            -Uri "http://localhost:5204/api/insights" `
            -Method Post `
            -ContentType "application/json" `
            -Body (@{ journeyLabel = "Sydney Weekender" } | ConvertTo-Json)
        if ($advice.source -ne "fallback") {
            throw "The Ollama-independent smoke test did not return fallback advice."
        }

        $page = Invoke-WebRequest -Uri "http://localhost:5100/budget/"
        if ($page.Content -notmatch "Budget &amp; Expense Tracker") {
            throw "The shared Student 4 route did not return the application."
        }

        [PSCustomObject]@{
            Status = "Passed"
            Budgets = $budgets.Count
            Expenses = $expenses.Count
            AdviceSource = $advice.source
        }
    }
    finally {
        if (-not $KeepRunning -and (Get-Command docker -ErrorAction SilentlyContinue)) {
            & docker compose rm --stop --force shared-frontend student4-frontend student4-backend student4-database
        }
        Pop-Location
    }
}

if ($MyInvocation.InvocationName -ne ".") {
    Test-Student4Docker
}