param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$Sha,
    [switch]$RunMissing,
    [ValidateRange(1, 7200)][int]$WaitSeconds = 3600
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repository = $env:GITHUB_REPOSITORY
if (-not $repository) { throw "GITHUB_REPOSITORY must identify the deployment repository." }
$workflows = [ordered]@{
    "Student 1 CI" = "student-1.yml"
    "Student 2 CI" = "student-2.yml"
    "Student 3 CI" = "student-3.yml"
    "Student 4 CI" = "student-4.yml"
    "Student 5 CI" = "student-5.yml"
    "Integrated Compose CI" = "integration-ci.yml"
}
$dispatched = @{}
$deadline = (Get-Date).AddSeconds($WaitSeconds)

function Assert-MainRevision {
    $mainSha = gh api "repos/$repository/git/ref/heads/main" --jq ".object.sha"
    if ($LASTEXITCODE -ne 0) { throw "Could not verify the current main revision." }
    if ($mainSha -ne $Sha) {
        throw "main has changed since this deployment was started. Start a new Cloud Deployment run on main; refusing to use CI for a different revision."
    }
}

while ($true) {
    if ($RunMissing) { Assert-MainRevision }
    $json = gh api --paginate --slurp "repos/$repository/actions/runs?head_sha=$Sha&per_page=100"
    if ($LASTEXITCODE -ne 0) { throw "Could not retrieve CI runs." }
    $runs = @($json | ConvertFrom-Json | ForEach-Object { $_.workflow_runs })
    $blocked = @()
    $missing = @()
    $failed = @()
    foreach ($name in $workflows.Keys) {
        $latest = $runs | Where-Object {
            $_.name -eq $name -and $_.head_sha -eq $Sha -and $_.head_branch -eq "main" -and $_.event -in @("push", "workflow_dispatch")
        } | Sort-Object run_number, run_attempt -Descending | Select-Object -First 1
        if (-not $latest) {
            $missing += $name
            $blocked += $name
        }
        elseif ($latest.status -ne "completed") {
            $blocked += $name
        }
        elseif ($latest.conclusion -ne "success") {
            $blocked += $name
            $failed += "$name ($($latest.conclusion)): $($latest.html_url)"
        }
        else {
            Write-Host "$name passed: $($latest.html_url)"
        }
    }
    if (-not $blocked.Count) { return }
    if (-not $RunMissing) {
        throw "Required CI is missing, incomplete or unsuccessful for $Sha on main: $($blocked -join ', '). Run Cloud Deployment to start missing checks automatically, or run these workflows manually on main. All six checks must pass for this exact revision. Missing/skipped checks cannot permit deployment."
    }
    if ($failed.Count) {
        throw "Required CI did not pass: $($failed -join '; '). Fix the failure or explicitly rerun the failed CI before retrying deployment; failures are not automatically retried."
    }
    if ((Get-Date) -ge $deadline) {
        throw "Timed out after $WaitSeconds seconds waiting for CI on ${Sha}: $($blocked -join ', '). No deployment was attempted. Check queued/running workflows before retrying Cloud Deployment."
    }
    foreach ($name in $missing) {
        if ($dispatched.ContainsKey($name)) { continue }
        Assert-MainRevision
        gh workflow run $workflows[$name] --repo $repository --ref main
        if ($LASTEXITCODE -ne 0) {
            throw "Could not start $name. The deployment token needs actions:write and the workflow must allow workflow_dispatch."
        }
        $dispatched[$name] = $true
        Write-Host "Started $name on main for $Sha."
    }
    Write-Host "Waiting for CI: $($blocked -join ', ')."
    Start-Sleep -Seconds 15
}
