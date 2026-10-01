[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$FailureMessage)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

Invoke-Checked "pip" @("install", "-r", "$repositoryRoot/student-5/database/requirements.txt") "Student 5 database dependency installation failed."
Invoke-Checked "pip" @("install", "-r", "$repositoryRoot/student-5/backend/requirements.txt") "Student 5 backend dependency installation failed."
Push-Location "$repositoryRoot/student-5/database"
try { Invoke-Checked "python" @("-m", "pytest", "tests") "Student 5 database tests failed." } finally { Pop-Location }
Push-Location "$repositoryRoot/student-5/backend"
try { Invoke-Checked "python" @("-m", "pytest", "tests") "Student 5 backend tests failed." } finally { Pop-Location }

# Release 1: Student 5's MCP tools and offline RAG retrieval checks on the
# shared servers. No model, MCP server or RAG server needs to be running.
Invoke-Checked "python" @("-m", "pip", "install", "--quiet", "-r", "$repositoryRoot/ai-services/mcp-server/requirements.txt", "-r", "$repositoryRoot/ai-services/rag-server/requirements.txt") "Shared MCP/RAG server dependency installation failed."
Push-Location "$repositoryRoot/ai-services/mcp-server"
try { Invoke-Checked "python" @("-m", "pytest", "tests/test_logistics_tools.py") "Student 5 MCP tool tests failed." } finally { Pop-Location }
Push-Location "$repositoryRoot/ai-services/rag-server"
try { Invoke-Checked "python" @("-m", "pytest", "tests/test_student5_retrieval.py") "Student 5 RAG retrieval tests failed." } finally { Pop-Location }
