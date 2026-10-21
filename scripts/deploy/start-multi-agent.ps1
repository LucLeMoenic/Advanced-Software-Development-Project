[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Python,
    [string]$NativeHost = "127.0.0.1",
    [int]$Port = 5600
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$address = $null
if (-not [Net.IPAddress]::TryParse($NativeHost, [ref]$address) -or
    $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) {
    throw "Use a loopback or local private IPv4 address."
}
$bytes = $address.GetAddressBytes()
$private = $bytes[0] -eq 10 -or ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
    ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
if (-not [Net.IPAddress]::IsLoopback($address) -and
    (-not $private -or -not (Get-NetIPAddress -IPAddress $NativeHost -ErrorAction SilentlyContinue))) {
    throw "NativeHost must be a local private interface. Configure restricted firewall access separately."
}
if ($Port -lt 1024 -or $Port -gt 65535) { throw "Choose an unprivileged port." }
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location (Join-Path $root "ai-services\multi-agent-server")
try {
    Write-Host "Starting one native Multi-Agent Server. Ctrl+C stops only this process."
    Write-Host "Health: http://${NativeHost}:$Port/health"
    Write-Host "Run the existing Release 1 stack separately with MULTI_AGENT_ENABLED=true."
    & $Python -m uvicorn server:app --host $NativeHost --port $Port --workers 1
    if ($LASTEXITCODE -ne 0) { throw "Multi-Agent Server exited with code $LASTEXITCODE." }
}
finally { Pop-Location }
