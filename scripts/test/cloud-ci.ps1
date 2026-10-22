Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$sha = "a" * 40
$env:GITHUB_REPOSITORY = "example/integration"
$gate = Join-Path $PSScriptRoot "..\deploy\assert-cloud-ci.ps1"
foreach ($workflow in @("student-1", "student-2", "student-3", "student-4", "student-5", "integration-ci")) {
    $path = Join-Path $PSScriptRoot "..\..\.github\workflows\$workflow.yml"
    if ((Get-Content $path -Raw) -notmatch '(?m)^  workflow_dispatch:\s*$') {
        throw "$workflow must support manual runs when path filters skip a deployment revision."
    }
}
$script:runs = @("Student 1 CI", "Student 2 CI", "Student 3 CI", "Student 4 CI", "Student 5 CI", "Integrated Compose CI") | ForEach-Object {
    @{ name=$_; head_sha=$sha; head_branch="main"; event="push"; run_number=1; run_attempt=1;
       status="completed"; conclusion="success"; html_url="https://example.invalid/run" }
}
$passingRuns = @($script:runs | ForEach-Object { $_.Clone() })
function gh {
    $global:LASTEXITCODE = 0
    $env:ASD_TEST_RUNS
}
$env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=$script:runs }) -Depth 5
& $gate -Sha $sha
foreach ($field in @("conclusion", "head_sha", "head_branch", "status", "event")) {
    $old = $script:runs[0][$field]
    $script:runs[0][$field] = "invalid"
    $env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=$script:runs }) -Depth 5
    $blocked = $false
    try { & $gate -Sha $sha } catch { $blocked = $true }
    if (-not $blocked) { throw "Gate did not reject mismatched $field." }
    $script:runs[0][$field] = $old
}
$script:runs[0].event = "workflow_dispatch"
$env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=$script:runs }) -Depth 5
& $gate -Sha $sha
$failedRetry = $script:runs[0].Clone()
$failedRetry.run_attempt = 2
$failedRetry.conclusion = "failure"
$env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=@($script:runs) + @($failedRetry) }) -Depth 5
$blocked = $false
try { & $gate -Sha $sha } catch { $blocked = $true }
if (-not $blocked) { throw "An older success concealed a failed latest retry." }
$script:runs = $script:runs | Where-Object { $_.name -notin @("Student 4 CI", "Student 5 CI") }
$env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=$script:runs }) -Depth 5
$blocked = $false
try { & $gate -Sha $sha } catch {
    $blocked = $true
    if ($_.Exception.Message -notmatch "Student 4 CI, Student 5 CI" -or
        $_.Exception.Message -notmatch "Run these workflows manually on main") {
        throw "Missing-CI error must identify every blocked workflow and explain recovery."
    }
}
if (-not $blocked) { throw "Missing CI was treated as successful." }
foreach ($scenario in @("missing-all", "pending-all", "failed-all", "missing-last", "failed-last")) {
    $candidates = @($passingRuns | ForEach-Object { $_.Clone() })
    switch ($scenario) {
        "missing-all" { $candidates = @() }
        "pending-all" { $candidates | ForEach-Object { $_.status = "in_progress"; $_.conclusion = $null } }
        "failed-all" { $candidates | ForEach-Object { $_.conclusion = "failure" } }
        "missing-last" { $candidates = $candidates[0..4] }
        "failed-last" { $candidates[-1].conclusion = "failure" }
    }
    $env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=$candidates }) -Depth 5
    $blocked = $false
    try { & $gate -Sha $sha } catch { $blocked = $true }
    if (-not $blocked) { throw "Gate accepted $scenario without all six successful checks." }
}
Remove-Item Env:ASD_TEST_RUNS
Write-Host "PASS: all six workflows support manual runs; cloud gate accepts exact-revision push/manual success, rejects mismatches, retries, absent/pending/failed runs and a missing/failed final check, and reports all missing checks."
