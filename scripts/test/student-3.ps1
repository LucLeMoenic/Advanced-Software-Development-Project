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

Invoke-Checked "pip" @("install", "-r", "$repositoryRoot/student-3/backend/requirements.txt") "Student 3 backend dependency installation failed."
Invoke-Checked "pip" @("install", "-r", "$repositoryRoot/student-3/database/requirements.txt", "pytest") "Student 3 database dependency installation failed."
Push-Location "$repositoryRoot/student-3"
try { Invoke-Checked "python" @("-m", "pytest", "tests") "Student 3 tests failed." } finally { Pop-Location }
