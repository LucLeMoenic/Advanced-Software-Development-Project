Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$sha = "a" * 40
$env:GITHUB_REPOSITORY = "example/integration"
$gate = Join-Path $PSScriptRoot "..\deploy\assert-cloud-ci.ps1"
$script:runs = @("Student 1 CI", "Student 2 CI", "Student 3 CI", "Student 4 CI", "Student 5 CI", "Integrated Compose CI") | ForEach-Object {
    @{ name=$_; head_sha=$sha; head_branch="main"; event="push"; run_number=1; run_attempt=1;
       status="completed"; conclusion="success"; html_url="https://example.invalid/run" }
}
function gh {
    $global:LASTEXITCODE = 0
    $env:ASD_TEST_RUNS
}
$env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=$script:runs }) -Depth 5
& $gate -Sha $sha
foreach ($field in @("conclusion", "head_sha", "head_branch", "status")) {
    $old = $script:runs[0][$field]
    $script:runs[0][$field] = "invalid"
    $env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=$script:runs }) -Depth 5
    $blocked = $false
    try { & $gate -Sha $sha } catch { $blocked = $true }
    if (-not $blocked) { throw "Gate did not reject mismatched $field." }
    $script:runs[0][$field] = $old
}
$script:runs = $script:runs | Select-Object -Skip 1
$env:ASD_TEST_RUNS = ConvertTo-Json -InputObject @(@{ workflow_runs=$script:runs }) -Depth 5
$blocked = $false
try { & $gate -Sha $sha } catch { $blocked = $true }
if (-not $blocked) { throw "Missing CI was treated as successful." }
Remove-Item Env:ASD_TEST_RUNS
Write-Host "PASS: same-revision cloud gate accepts six completed checks and rejects mismatches/missing runs."
