$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $asyncResult = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $asyncResult.AsyncWaitHandle.WaitOne(1000, $false)) {
            $client.Close()
            return $false
        }
        $client.EndConnect($asyncResult)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Add-Result {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [bool]$Ok,
        [Parameter(Mandatory = $true)]
        [string]$Details
    )

    [PSCustomObject]@{
        Check   = $Name
        Status  = if ($Ok) { "OK" } else { "WARN" }
        Details = $Details
    }
}

$requiredEnv = @(
    "POKE_API_KEY",
    "POKE_NOTIFY_URL",
    "LINEAR_WEBHOOK_SECRET",
    "TOOL_WEBHOOK_SECRET"
)

$results = @()

$configuredTempDir = if ($env:POKE_BRIDGE_TEMP_DIR) { $env:POKE_BRIDGE_TEMP_DIR } else { Join-Path $env:TEMP "poke-hermes-bridge" }
$configuredTaskStore = if ($env:POKE_BRIDGE_TASK_STORE) { $env:POKE_BRIDGE_TASK_STORE } else { Join-Path $configuredTempDir "tasks.json" }
$configuredInboxFile = if ($env:HERMES_INBOX_FILE) { $env:HERMES_INBOX_FILE } else { Join-Path $configuredTempDir "hermes-inbox.jsonl" }
$hermesMode = if ($env:HERMES_MODE) { $env:HERMES_MODE } else { "http" }

foreach ($name in $requiredEnv) {
    $item = Get-Item -Path "Env:$name" -ErrorAction SilentlyContinue
    $isSet = $null -ne $item -and -not [string]::IsNullOrWhiteSpace([string]$item.Value)
    $results += Add-Result -Name "env:$name" -Ok $isSet -Details ($(if ($isSet) { "set" } else { "missing" }))
}

$results += Add-Result -Name "env:HERMES_MODE" -Ok $true -Details $hermesMode
$results += Add-Result -Name "env:POKE_BRIDGE_TEMP_DIR" -Ok $true -Details $configuredTempDir
$results += Add-Result -Name "env:POKE_BRIDGE_TASK_STORE" -Ok $true -Details $configuredTaskStore
$results += Add-Result -Name "env:HERMES_INBOX_FILE" -Ok $true -Details $configuredInboxFile

$bridgePortOk = Test-TcpPort -HostName "127.0.0.1" -Port 8788
$results += Add-Result -Name "tcp:127.0.0.1:8788" -Ok $bridgePortOk -Details ($(if ($bridgePortOk) { "bridge port reachable" } else { "bridge port not reachable" }))

$hermesPortOk = Test-TcpPort -HostName "127.0.0.1" -Port 18789
$results += Add-Result -Name "tcp:127.0.0.1:18789" -Ok $hermesPortOk -Details ($(if ($hermesPortOk) { "hermes port reachable" } else { "hermes port not reachable" }))

$opCommand = Get-Command op -ErrorAction SilentlyContinue
$results += Add-Result -Name "tool:op" -Ok ($null -ne $opCommand) -Details ($(if ($opCommand) { $opCommand.Source } else { "1Password CLI not found in PATH" }))

$summary = [PSCustomObject]@{
    root = $root
    timestamp = (Get-Date).ToString("s")
    hermes_mode = $hermesMode
    all_ok = -not ($results | Where-Object { $_.Status -ne "OK" })
    results = $results
}

$summary | ConvertTo-Json -Depth 4
