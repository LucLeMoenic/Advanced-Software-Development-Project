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
        $_.Exception.Message -notmatch "Run Cloud Deployment to start missing checks automatically") {
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

$deployment = Get-Content (Join-Path $PSScriptRoot "..\..\.github\workflows\cloud-deployment.yml") -Raw
if ($deployment -notmatch '(?m)^  actions: write\r?$' -or
    $deployment -notmatch 'assert-cloud-ci\.ps1 -Sha "\$GITHUB_SHA" -RunMissing' -or
    $deployment -notmatch 'timeout-minutes: 65') {
    throw "Cloud Deployment must enable bounded automatic CI with actions:write."
}
if ($deployment.IndexOf("cloud_auth.py check") -gt $deployment.IndexOf("-RunMissing")) {
    throw "Missing AI credentials must fail before dispatching expensive CI."
}

function Get-Date { $global:ASDCloudCiTest.now }
function Start-Sleep {
    param([int]$Seconds)
    $global:ASDCloudCiTest.now = $global:ASDCloudCiTest.now.AddSeconds($Seconds)
    $global:ASDCloudCiTest.poll++
    if ($global:ASDCloudCiTest.poll -gt 5) { throw "Test detected an unbounded wait." }
}
function gh {
    $state = $global:ASDCloudCiTest
    $global:LASTEXITCODE = 0
    if ($args[0] -eq "api" -and $args[1] -like "*/git/ref/heads/main") {
        $state.mainReads++
        if ($state.scenario -eq "ref-error") { $global:LASTEXITCODE = 1; return }
        if ($state.scenario -eq "moved-main" -or
            ($state.scenario -eq "moved-before-dispatch" -and $state.mainReads -gt 1) -or
            ($state.scenario -eq "moved-while-waiting" -and $state.poll -gt 0)) { return "b" * 40 }
        return $sha
    }
    if ($args[0] -eq "api" -and $args -contains "repos/example/integration/actions/runs?head_sha=$sha&per_page=100") {
        if ($state.scenario -eq "api-error") { $global:LASTEXITCODE = 1; return }
        $rows = @($passingRuns | ForEach-Object { $_.Clone() })
        switch ($state.scenario) {
            "missing" {
                if ($state.poll -lt 2) { $rows = @($rows | Where-Object { $_.name -notin @("Student 4 CI", "Student 5 CI") }) }
            }
            "pending" { if ($state.poll -eq 0) { $rows[1].status = "in_progress"; $rows[1].conclusion = $null } }
            "failed" { $rows[1].conclusion = "failure" }
            "skipped" { $rows[-1].conclusion = "skipped" }
            "cancelled" { $rows[-1].conclusion = "cancelled" }
            "failed-retry" {
                $retry = $rows[1].Clone()
                $retry.run_attempt = 2
                $retry.conclusion = "failure"
                $rows += $retry
            }
            "dispatch-error" { $rows = @() }
            "timeout" { $rows = @() }
            "moved-before-dispatch" { $rows = @() }
            "moved-while-waiting" { $rows = @() }
            "wrong-sha" { foreach ($row in $rows) { $row.head_sha = "b" * 40 } }
            "failed-after-dispatch" {
                if ($state.poll -eq 0) { $rows = @() } else { $rows[0].conclusion = "failure" }
            }
        }
        return ConvertTo-Json -InputObject @(@{ workflow_runs=$rows }) -Depth 5
    }
    if ($args[0] -eq "workflow" -and $args[1] -eq "run") {
        if ($args.Count -ne 7 -or $args[3] -ne "--repo" -or $args[4] -ne "example/integration" -or
            $args[5] -ne "--ref" -or $args[6] -ne "main") { throw "Dispatch must target this repository's main." }
        $state.dispatches += $args[2]
        if ($state.scenario -eq "dispatch-error") { $global:LASTEXITCODE = 1 }
        return
    }
    throw "Unexpected GitHub call in test: $args"
}
$cases = @(
    @{ name="passed"; dispatches=0; polls=0 },
    @{ name="missing"; dispatches=2; polls=2 },
    @{ name="pending"; dispatches=0; polls=1 },
    @{ name="failed"; error="Required CI did not pass"; dispatches=0 },
    @{ name="skipped"; error="Required CI did not pass"; dispatches=0 },
    @{ name="cancelled"; error="Required CI did not pass"; dispatches=0 },
    @{ name="failed-retry"; error="Required CI did not pass"; dispatches=0 },
    @{ name="failed-after-dispatch"; error="Required CI did not pass"; dispatches=6 },
    @{ name="dispatch-error"; error="Could not start Student 1 CI"; dispatches=1 },
    @{ name="api-error"; error="Could not retrieve CI runs"; dispatches=0 },
    @{ name="ref-error"; error="Could not verify the current main revision"; dispatches=0 },
    @{ name="moved-main"; error="main has changed"; dispatches=0 },
    @{ name="moved-before-dispatch"; error="main has changed"; dispatches=0 },
    @{ name="moved-while-waiting"; error="main has changed"; dispatches=6 },
    @{ name="timeout"; error="Timed out after 30 seconds"; dispatches=6 },
    @{ name="wrong-sha"; error="Timed out after 30 seconds"; dispatches=6 }
)
foreach ($case in $cases) {
    $global:ASDCloudCiTest = @{
        scenario = $case.name
        poll = 0
        mainReads = 0
        dispatches = @()
        now = [datetime]"2026-10-23T00:00:00Z"
    }
    $state = $global:ASDCloudCiTest
    $message = $null
    try { & $gate -Sha $sha -RunMissing -WaitSeconds 30 } catch { $message = $_.Exception.Message }
    if ($case.ContainsKey("error")) {
        if (-not $message -or $message -notmatch $case.error) { throw "$($case.name): expected '$($case.error)', received '$message'." }
    }
    elseif ($message) { throw "$($case.name) unexpectedly failed: $message" }
    if ($state.dispatches.Count -ne $case.dispatches -or
        @($state.dispatches | Select-Object -Unique).Count -ne $state.dispatches.Count) {
        throw "$($case.name): unexpected or duplicate dispatches: $($state.dispatches)"
    }
    if ($case.ContainsKey("polls") -and $state.poll -ne $case.polls) { throw "$($case.name): incorrect polling." }
    if ($case.name -eq "missing" -and ($state.dispatches -join ",") -ne "student-4.yml,student-5.yml") {
        throw "Only missing Student 4/5 workflows should be dispatched."
    }
    if ($case.dispatches -eq 6 -and ($state.dispatches -join ",") -ne
        "student-1.yml,student-2.yml,student-3.yml,student-4.yml,student-5.yml,integration-ci.yml") {
        throw "Dispatch must target the six existing CI workflow files, never deployment itself."
    }
    Remove-Variable ASDCloudCiTest -Scope Global
}
Write-Host "PASS: strict exact-revision CI checks and 16 automatic-dispatch/wait cases; failures, timeouts and main changes block deployment."
