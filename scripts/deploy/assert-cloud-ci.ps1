param([Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$Sha)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repository = $env:GITHUB_REPOSITORY
if (-not $repository) { throw "GITHUB_REPOSITORY must identify the deployment repository." }
$json = gh api --paginate --slurp "repos/$repository/actions/runs?head_sha=$Sha&per_page=100"
if ($LASTEXITCODE -ne 0) { throw "Could not retrieve CI runs." }
$runs = @($json | ConvertFrom-Json | ForEach-Object { $_.workflow_runs })
$blocked = @()
foreach ($name in @("Student 1 CI", "Student 2 CI", "Student 3 CI", "Student 4 CI", "Student 5 CI", "Integrated Compose CI")) {
    $latest = $runs | Where-Object {
        $_.name -eq $name -and $_.head_sha -eq $Sha -and $_.head_branch -eq "main" -and $_.event -in @("push", "workflow_dispatch")
    } | Sort-Object run_number, run_attempt -Descending | Select-Object -First 1
    if (-not $latest -or $latest.status -ne "completed" -or $latest.conclusion -ne "success") {
        $blocked += $name
        continue
    }
    Write-Host "$name passed: $($latest.html_url)"
}
if ($blocked.Count) {
    throw "Required CI is missing, incomplete or unsuccessful for $Sha on main: $($blocked -join ', '). Run these workflows manually on main and wait for success before deploying. All six checks must pass for this exact revision; if main advances, validate the new revision instead. Missing/skipped checks cannot permit deployment."
}
