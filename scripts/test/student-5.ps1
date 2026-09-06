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
