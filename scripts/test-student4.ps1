#!/usr/bin/env pwsh
<#
.SYNOPSIS
Runs Student 4 tests and source builds.

.PARAMETER Area
Selects all checks or one service test suite.

.EXAMPLE
./scripts/test-student4.ps1 -Area All
#>
[CmdletBinding()]
param(
    [ValidateSet("All", "Backend", "Database")]
    [string]$Area = "All"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,

        [Parameter(Mandatory)]
        [string[]]$ArgumentList,

        [Parameter(Mandatory)]
        [string]$FailureMessage
    )

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

    function Install-NodeDependency {
        param(
            [Parameter(Mandatory)]
            [string]$Path,

            [Parameter(Mandatory)]
            [string]$FailureMessage
        )

        $isContinuousIntegration = $env:CI -eq "true"
        if (-not $isContinuousIntegration -and (Test-Path (Join-Path $Path "node_modules"))) {
            return
        }

        $installCommand = if ($isContinuousIntegration) { "ci" } else { "install" }
        Push-Location -LiteralPath $Path
        try {
            Invoke-CheckedCommand npm @($installCommand, "--workspaces=false") $FailureMessage
        }
        finally {
            Pop-Location
        }
    }

function Invoke-Student4Validation {
    $repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
    $frontendPath = Join-Path $repositoryRoot "student-4/frontend"
    $sharedFrontendPath = Join-Path $repositoryRoot "shared/vue-frontend"
    $backendTests = Join-Path $repositoryRoot "student-4/backend/tests/Backend.Tests.csproj"
    $databaseTests = Join-Path $repositoryRoot "student-4/database/tests/Database.Tests.csproj"

    if ($Area -eq "All") {
            Install-NodeDependency $frontendPath "Student 4 frontend dependency installation failed."
        Invoke-CheckedCommand npm @("test", "--prefix", $frontendPath) "Student 4 frontend tests failed."
        Invoke-CheckedCommand npm @("run", "build", "--prefix", $frontendPath) "Student 4 frontend build failed."
    }

    if ($Area -in @("All", "Backend")) {
        Invoke-CheckedCommand dotnet @("test", $backendTests, "--configuration", "Release") "Student 4 backend tests failed."
    }

    if ($Area -in @("All", "Database")) {
        Invoke-CheckedCommand dotnet @("test", $databaseTests, "--configuration", "Release") "Student 4 database tests failed."
    }

    if ($Area -eq "All") {
            Install-NodeDependency $sharedFrontendPath "Shared frontend dependency installation failed."
        Invoke-CheckedCommand npm @("run", "build", "--prefix", $sharedFrontendPath) "Shared frontend build failed."
    }

    [PSCustomObject]@{
        Area = $Area
        Status = "Passed"
    }
}

if ($MyInvocation.InvocationName -ne ".") {
    Invoke-Student4Validation
}