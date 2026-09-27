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

Invoke-Checked "npm" @("ci", "--prefix", "$repositoryRoot/student-2/frontend") "Student 2 frontend dependency installation failed."
Invoke-Checked "npm" @("test", "--prefix", "$repositoryRoot/student-2/frontend") "Student 2 frontend tests failed."
Invoke-Checked "python" @("-m", "pip", "install", "-r", "$repositoryRoot/student-2/backend/requirements.txt", "pytest") "Student 2 backend dependency installation failed."
Push-Location "$repositoryRoot/student-2/backend"
try { Invoke-Checked "python" @("-m", "pytest", "tests") "Student 2 backend tests failed." } finally { Pop-Location }
Invoke-Checked "python" @("-m", "pip", "install", "-r", "$repositoryRoot/student-2/database/requirements.txt") "Student 2 database dependency installation failed."
Push-Location "$repositoryRoot/student-2/database"
try { Invoke-Checked "python" @("-m", "pytest", "tests") "Student 2 database tests failed." } finally { Pop-Location }
Invoke-Checked "python" @("-m", "pip", "install", "-r", "$repositoryRoot/ai-services/mcp-server/requirements.txt", "-r", "$repositoryRoot/ai-services/rag-server/requirements.txt") "Shared test dependency installation failed."
foreach ($service in @("mcp-server", "rag-server")) {
    Push-Location "$repositoryRoot/ai-services/$service"
    try { Invoke-Checked "python" @("-m", "pytest", "tests") "Shared $service tests failed." } finally { Pop-Location }
}
