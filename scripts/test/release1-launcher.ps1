[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$path = Join-Path $PSScriptRoot "../deploy/start-release1.ps1"
$ast = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }

foreach ($name in @("Set-NativeConfiguration", "Get-VenvPython", "Test-Url")) {
    $definition = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name
    }, $true)
    if (-not $definition) { throw "Missing launcher helper: $name" }
    Invoke-Expression $definition.Extent.Text
}

function Assert-Check([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Assert-Rejected([scriptblock]$Action, [string]$Message) {
    $rejected = $false
    try { & $Action | Out-Null } catch { $rejected = $true }
    Assert-Check $rejected $Message
}

$variables = @("APPLICATION_MODEL", "RAG_MODEL", "MCP_HOST", "MCP_PORT", "OLLAMA_HOST", "OLLAMA_URL",
    "MCP_SERVER_URL", "RAG_SERVER_URL", "LOCAL_AI_HOST", "AI_ENABLED", "MCP_ENABLED", "RAG_ENABLED")
$saved = @{}
foreach ($name in $variables) { $saved[$name] = [Environment]::GetEnvironmentVariable($name) }

try {
    function Get-NetIPAddress { param($AddressFamily, $IPAddress, $ErrorAction) @{ IPAddress = $IPAddress } }
    Set-NativeConfiguration "172.23.64.1" "fixture-model:latest"
    Assert-Check ($env:MCP_HOST -eq "172.23.64.1" -and $env:OLLAMA_HOST -eq "172.23.64.1:11434") "Private bind mismatch"
    Assert-Check ($env:OLLAMA_URL -eq "http://172.23.64.1:11434" -and $env:LOCAL_AI_HOST -eq "172.23.64.1") "Private origins mismatch"
    Assert-Check ($env:APPLICATION_MODEL -eq "fixture-model:latest" -and $env:RAG_MODEL -eq "fixture-model:latest") "Model propagation failed"
    Assert-Check ($env:AI_ENABLED -eq "true" -and $env:MCP_ENABLED -eq "true" -and $env:RAG_ENABLED -eq "true") "Mode propagation failed"
    Assert-Check ($env:MCP_SERVER_URL -eq "http://host.docker.internal:5400/mcp" -and $env:RAG_SERVER_URL -eq "http://host.docker.internal:5500") "Container URLs mismatch"
    Set-NativeConfiguration "127.0.0.1" "fixture-model:latest"
    Assert-Check ($env:LOCAL_AI_HOST -eq "host-gateway") "Container DNS must not resolve to container loopback"
    foreach ($address in @("0.0.0.0", "8.8.8.8", "::1", "localhost", "bad-address")) {
        Assert-Rejected { Set-NativeConfiguration $address "fixture" } "Unsafe address accepted: $address"
    }
    function Get-NetIPAddress { param($AddressFamily, $IPAddress, $ErrorAction) $null }
    Assert-Rejected { Set-NativeConfiguration "10.20.30.40" "fixture" } "Nonlocal private address accepted"

    function Invoke-WebRequest { param($Uri, $TimeoutSec, [switch]$SkipHttpErrorCheck) @{ StatusCode = $script:httpStatus } }
    foreach ($httpStatus in @(200, 400, 403, 404, 406, 500, 503)) {
        $script:httpStatus = $httpStatus
        Assert-Check ((Test-Url "http://fixture") -eq ($httpStatus -eq 200)) "Incorrect health status: $httpStatus"
        Assert-Check ((Test-Url "http://fixture" @(400, 406)) -eq ($httpStatus -in @(400, 406))) "Incorrect MCP status: $httpStatus"
    }
    function Invoke-WebRequest { throw "Connection refused" }
    Assert-Check (-not (Test-Url "http://fixture")) "Connection failure accepted"

    function Test-Path { $true }
    function Join-Path { "Invoke-FixturePython" }
    $binDirectory = "Scripts"
    $script:pipCalls = 0
    function Invoke-FixturePython {
        $script:pipCalls++
        Assert-Check (($args -join " ") -eq "-m pip install --quiet -r updated.txt") "Incorrect dependency arguments"
        $global:LASTEXITCODE = 0
        "Installer output must not become the interpreter path."
    }
    $python = Get-VenvPython "existing-venv" "updated.txt"
    Assert-Check ($script:pipCalls -eq 1 -and $python -eq "Invoke-FixturePython") "Existing environment not synchronized cleanly"
    function Invoke-FixturePython { $global:LASTEXITCODE = 1 }
    Assert-Rejected { Get-VenvPython "existing-venv" "updated.txt" } "Dependency installation failure ignored"
    function Invoke-FixturePython { $global:LASTEXITCODE = 0 }
    Assert-Check ((Get-VenvPython "existing-venv" "updated.txt") -eq "Invoke-FixturePython") "Partial-install retry failed"

    Write-Host "Release 1 launcher regression checks passed (isolated helpers; no services or packages changed)."
}
finally {
    foreach ($name in $variables) { [Environment]::SetEnvironmentVariable($name, $saved[$name]) }
}