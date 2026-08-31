param(
    [string]$ImplementerModel,
    [string]$ReviewerModel,
    [string]$ApplicationModel
)

$ErrorActionPreference = "Stop"

function Get-ConfiguredModel {
    param(
        [string]$Name,
        [string]$Fallback
    )

    $environmentValue = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($environmentValue)) {
        return $environmentValue
    }

    if (Test-Path ".env") {
        $match = Get-Content ".env" |
            Where-Object { $_ -match "^\s*$Name\s*=" } |
            Select-Object -Last 1
        if ($match) {
            return ($match -split "=", 2)[1].Trim()
        }
    }

    return $Fallback
}

if ([string]::IsNullOrWhiteSpace($ImplementerModel)) {
    $ImplementerModel = Get-ConfiguredModel "IMPLEMENTER_MODEL" "qwen2.5-coder:7b"
}
if ([string]::IsNullOrWhiteSpace($ReviewerModel)) {
    $ReviewerModel = Get-ConfiguredModel "REVIEWER_MODEL" "llama3.2:3b"
}
if ([string]::IsNullOrWhiteSpace($ApplicationModel)) {
    $ApplicationModel = Get-ConfiguredModel "APPLICATION_MODEL" "llama3.2:3b"
}

if ($ImplementerModel -eq $ReviewerModel) {
    throw "ImplementerModel and ReviewerModel must be different."
}

docker compose up -d --wait ollama
if ($LASTEXITCODE -ne 0) {
    throw "Failed to start the Ollama service."
}

$missingModels = @()
@($ImplementerModel, $ReviewerModel, $ApplicationModel) |
    Select-Object -Unique |
    ForEach-Object {
        docker compose exec ollama ollama show $_ *> $null
        if ($LASTEXITCODE -ne 0) {
            $missingModels += $_
        }
    }

if ($missingModels.Count -gt 0) {
    throw "Required Ollama models are not installed: $($missingModels -join ', '). No models were downloaded."
}

docker compose exec ollama ollama list
if ($LASTEXITCODE -ne 0) {
    throw "Failed to list installed Ollama models."
}
