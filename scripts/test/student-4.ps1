#!/usr/bin/env pwsh
<#
.SYNOPSIS
Runs Student 4 tests and source builds.

.PARAMETER Area
Selects all checks, a service test suite, or one shared validation suite.

.EXAMPLE
./scripts/test/student-4.ps1 -Area All
#>
[CmdletBinding()]
param(
    [ValidateSet("All", "Backend", "Database", "Shared", "Loop", "Mcp", "Rag")]
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

function Resolve-Student4Python {
    param(
        [Parameter(Mandatory)]
        [ValidateSet("Mcp", "Rag")]
        [string]$Service,

        [Parameter(Mandatory)]
        [string]$RepositoryRoot
    )

    $overrideName = "STUDENT4_$($Service.ToUpperInvariant())_PYTHON"
    $pythonPath = [Environment]::GetEnvironmentVariable($overrideName)
    if ([string]::IsNullOrWhiteSpace($pythonPath)) {
        $pythonPath = $env:STUDENT4_PYTHON
    }
    if (-not [string]::IsNullOrWhiteSpace($pythonPath)) {
        if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
            throw "$overrideName/STUDENT4_PYTHON does not point to a Python executable: $pythonPath"
        }
        return [IO.Path]::GetFullPath($pythonPath)
    }

    $candidatePaths = @(
        (Join-Path $RepositoryRoot "../venv-$($Service.ToLowerInvariant())/Scripts/python.exe"),
        (Join-Path $RepositoryRoot "../venv-$($Service.ToLowerInvariant())/bin/python"),
        (Join-Path $RepositoryRoot "ai-services/venv-$($Service.ToLowerInvariant())/Scripts/python.exe"),
        (Join-Path $RepositoryRoot "ai-services/venv-$($Service.ToLowerInvariant())/bin/python")
    )
    foreach ($candidatePath in $candidatePaths) {
        if (Test-Path -LiteralPath $candidatePath -PathType Leaf) {
            return [IO.Path]::GetFullPath($candidatePath)
        }
    }

    foreach ($commandName in @("python3", "python")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return $command.Source
        }
    }

    throw "No Python interpreter found for the $Service validation suite. Set $overrideName or STUDENT4_PYTHON."
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
    $repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../.."))
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

    if ($Area -in @("All", "Shared", "Loop")) {
        $loopTests = Join-Path $repositoryRoot "ai-services/agentic-loop/tests/AgenticLoop.Tests.csproj"
        Invoke-CheckedCommand dotnet @("test", $loopTests, "--configuration", "Release") "Shared agentic-loop tests failed."
    }

    if ($Area -in @("All", "Shared", "Mcp")) {
        $mcpPath = Join-Path $repositoryRoot "ai-services/mcp-server"
        $mcpPython = Resolve-Student4Python -Service Mcp -RepositoryRoot $repositoryRoot
        Push-Location -LiteralPath $mcpPath
        try {
            Invoke-CheckedCommand -FilePath $mcpPython -ArgumentList @("-m", "pytest", "-q") -FailureMessage "Shared MCP tests failed."
        }
        finally {
            Pop-Location
        }
    }

    if ($Area -in @("All", "Shared", "Rag")) {
        $ragPath = Join-Path $repositoryRoot "ai-services/rag-server"
        $ragPython = Resolve-Student4Python -Service Rag -RepositoryRoot $repositoryRoot
        Push-Location -LiteralPath $ragPath
        try {
            Invoke-CheckedCommand -FilePath $ragPython -ArgumentList @("-m", "pytest", "-q") -FailureMessage "Shared RAG tests failed."
        }
        finally {
            Pop-Location
        }
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