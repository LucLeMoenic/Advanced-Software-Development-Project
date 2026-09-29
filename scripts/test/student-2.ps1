[CmdletBinding()]
param(
    [switch]$Smoke,
    [string]$ApiBaseUrl = "http://localhost:5102/itinerary-api"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$FailureMessage)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

if ($Smoke) {
    function Invoke-SmokeRequest {
        param([string]$Method, [string]$Path, [object]$Body = $null, [int]$ExpectedStatus = 200)
        $request = @{
            Uri = "$($ApiBaseUrl.TrimEnd('/'))$Path"
            Method = $Method
            TimeoutSec = 30
            SkipHttpErrorCheck = $true
        }
        if ($null -ne $Body) {
            $request.ContentType = "application/json"
            $request.Body = $Body | ConvertTo-Json -Depth 10
        }
        $response = Invoke-WebRequest @request
        if ([int]$response.StatusCode -ne $ExpectedStatus) {
            throw "$Method $Path returned $($response.StatusCode); expected $ExpectedStatus."
        }
        if ($response.Content) { return $response.Content | ConvertFrom-Json -AsHashtable }
    }

    function Assert-Smoke([bool]$Condition, [string]$Message) {
        if (-not $Condition) { throw $Message }
    }

    $modes = Invoke-SmokeRequest GET "/capabilities"
    Assert-Smoke ($modes.aiEnabled -eq $false -and $modes.mcpEnabled -eq $false -and $modes.ragEnabled -eq $false) `
        "Smoke checks require AI_ENABLED=false, MCP_ENABLED=false and RAG_ENABLED=false; no trips were changed."
    $baseline = @(Invoke-SmokeRequest GET "/trips")
    Assert-Smoke ($baseline.Count -ge 10) "Expected at least ten saved trips."
    foreach ($path in @("/trips/$($baseline[0].id)/mcp-summary", "/itinerary-advice")) {
        $disabled = Invoke-SmokeRequest POST $path @{} 503
        Assert-Smoke ($disabled.error.code -eq "mode_disabled") "$path did not report mode_disabled."
    }

    $tripId = $null
    $fixtureUser = "R1 smoke $([guid]::NewGuid().ToString('N'))"
    Push-Location $repositoryRoot
    try {
        $criteria = @{
            user = $fixtureUser
            destination = "Osaka"
            startDate = (Get-Date).Date.AddDays(7).ToString("yyyy-MM-dd")
            endDate = (Get-Date).Date.AddDays(8).ToString("yyyy-MM-dd")
            budget = 900
            interests = "food, museums"
        }
        $trip = Invoke-SmokeRequest POST "/trips" $criteria 201
        $tripId = $trip.id
        Assert-Smoke ($trip.generationMode -eq "fallback" -and $trip.stops.Count -eq 4) "Disabled AI did not produce a complete fallback itinerary."
        $criteria.budget = 1200
        $updated = Invoke-SmokeRequest PUT "/trips/$tripId" $criteria
        Assert-Smoke ($updated.budget -eq 1200) "Trip update was not persisted."

        $stop = Invoke-SmokeRequest POST "/trips/$tripId/stops" @{ day = 1; activity = "Smoke test stop"; notes = "Temporary fixture" } 201
        $edited = Invoke-SmokeRequest PUT "/stops/$($stop.id)" @{ day = 2; activity = "Updated smoke stop"; notes = "Temporary fixture" }
        Assert-Smoke ($edited.day -eq 2 -and $edited.activity -eq "Updated smoke stop") "Stop update was not persisted."
        $regenerated = Invoke-SmokeRequest POST "/stops/$($stop.id)/regenerate"
        Assert-Smoke ($regenerated.generationMode -eq "fallback" -and $regenerated.stop.day -eq 2) "Stop regeneration failed."
        Invoke-SmokeRequest DELETE "/stops/$($stop.id)" $null 204
        $regeneratedTrip = Invoke-SmokeRequest POST "/trips/$tripId/regenerate"
        Assert-Smoke ($regeneratedTrip.generationMode -eq "fallback" -and $regeneratedTrip.stops.Count -eq 4) "Whole-trip regeneration failed."

        $beforeRestart = Invoke-SmokeRequest GET "/trips/$tripId"
        Invoke-Checked "docker" @("compose", "restart", "student2-database") "Database restart failed."
        Invoke-Checked "docker" @("compose", "up", "--detach", "--no-deps", "--wait", "student2-database") "Database did not become healthy."
        $afterRestart = Invoke-SmokeRequest GET "/trips/$tripId"
        Assert-Smoke (($beforeRestart | ConvertTo-Json -Depth 10 -Compress) -eq ($afterRestart | ConvertTo-Json -Depth 10 -Compress)) `
            "Saved itinerary changed after database restart."
        Invoke-SmokeRequest DELETE "/trips/$tripId" $null 204
        Invoke-SmokeRequest GET "/trips/$tripId" $null 404 | Out-Null
        $tripId = $null
        $remaining = @(Invoke-SmokeRequest GET "/trips")
        Assert-Smoke ($remaining.Count -eq $baseline.Count) "Smoke checks changed the saved-trip count."
        Write-Host "Student 2 smoke checks passed: disabled modes, fallback, trip/stop CRUD, regeneration and restart persistence."
    }
    finally {
        try {
            $fixtures = @(Invoke-SmokeRequest GET "/trips") | Where-Object { $_.user -eq $fixtureUser }
            foreach ($fixture in $fixtures) {
                Invoke-SmokeRequest DELETE "/trips/$($fixture.id)" $null 204
            }
        }
        finally { Pop-Location }
    }
    return
}

Invoke-Checked "npm" @("ci", "--prefix", "$repositoryRoot/student-2/frontend") "Student 2 frontend dependency installation failed."
Invoke-Checked "npm" @("test", "--prefix", "$repositoryRoot/student-2/frontend") "Student 2 frontend tests failed."
Invoke-Checked "npm" @("run", "build", "--prefix", "$repositoryRoot/student-2/frontend") "Student 2 frontend build failed."
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
