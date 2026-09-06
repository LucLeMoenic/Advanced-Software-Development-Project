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
Invoke-Checked "pip" @("install", "-r", "$repositoryRoot/student-2/backend/requirements.txt", "pytest") "Student 2 backend dependency installation failed."
Push-Location "$repositoryRoot/student-2/backend"
try { Invoke-Checked "python" @("-m", "pytest", "tests") "Student 2 backend tests failed." } finally { Pop-Location }
Invoke-Checked "pip" @("install", "-r", "$repositoryRoot/student-2/database/requirements.txt") "Student 2 database dependency installation failed."
Push-Location "$repositoryRoot/student-2/database"
try { Invoke-Checked "python" @("-m", "pytest", "tests") "Student 2 database tests failed." } finally { Pop-Location }
