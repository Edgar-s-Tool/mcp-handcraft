$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$runtimeBase = Join-Path $env:TEMP 'poke-hermes-bridge-smoke'
$runtimeDir = Join-Path $runtimeBase 'runtime'
$tempDir = Join-Path $runtimeBase 'tmp'
New-Item -ItemType Directory -Force $runtimeDir, $tempDir | Out-Null

if (-not $env:POKE_API_KEY) { $env:POKE_API_KEY = 'local-smoke-key' }
if (-not $env:POKE_NOTIFY_URL) { $env:POKE_NOTIFY_URL = 'https://poke.example.test/notify' }
if (-not $env:LINEAR_WEBHOOK_SECRET) { $env:LINEAR_WEBHOOK_SECRET = 'linear-local-secret' }
if (-not $env:TOOL_WEBHOOK_SECRET) { $env:TOOL_WEBHOOK_SECRET = 'tool-local-secret' }

$env:HERMES_MODE = 'file'
$env:HERMES_INBOX_FILE = Join-Path $runtimeDir 'hermes-inbox.jsonl'
$env:POKE_BRIDGE_TASK_STORE = Join-Path $runtimeDir 'tasks.json'
$env:POKE_BRIDGE_TEMP_DIR = $tempDir

$stdoutLog = Join-Path $runtimeDir 'smoke-server.out.log'
$stderrLog = Join-Path $runtimeDir 'smoke-server.err.log'
Remove-Item -LiteralPath $stdoutLog, $stderrLog -ErrorAction SilentlyContinue

$proc = Start-Process -FilePath python -ArgumentList '.\server.py' -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

try {
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod http://127.0.0.1:8788/health
            $ready = $true
            break
        }
        catch {
            if ($proc.HasExited) { break }
        }
    }

    if (-not $ready) {
        $stdout = if (Test-Path $stdoutLog) { Get-Content -Raw $stdoutLog } else { '' }
        $stderr = if (Test-Path $stderrLog) { Get-Content -Raw $stderrLog } else { '' }
        throw "Bridge server did not become ready. ExitCode=$($proc.ExitCode) STDOUT=$stdout STDERR=$stderr"
    }

    $toolsList = Invoke-RestMethod http://127.0.0.1:8788/mcp -Method Post -ContentType 'application/json' -Body (@{
        jsonrpc = '2.0'
        id = 1
        method = 'tools/list'
    } | ConvertTo-Json -Compress)

    $createTask = Invoke-RestMethod http://127.0.0.1:8788/mcp -Method Post -ContentType 'application/json' -Body (@{
        jsonrpc = '2.0'
        id = 2
        method = 'tools/call'
        params = @{
            name = 'create_pending_task'
            arguments = @{
                title = 'smoke task'
                details = 'created by smoke-local.ps1'
            }
        }
    } | ConvertTo-Json -Depth 8 -Compress)

    $sendInbox = Invoke-RestMethod http://127.0.0.1:8788/mcp -Method Post -ContentType 'application/json' -Body (@{
        jsonrpc = '2.0'
        id = 3
        method = 'tools/call'
        params = @{
            name = 'send_to_hermes_inbox'
            arguments = @{
                title = 'smoke inbox'
                body = 'hello from smoke-local.ps1'
            }
        }
    } | ConvertTo-Json -Depth 8 -Compress)

    [PSCustomObject]@{
        health = $health
        tools  = ($toolsList.result.tools | ForEach-Object { $_.name })
        task   = $createTask.result.content[0].text
        inbox  = $sendInbox.result.content[0].text
        runtimeBase = $runtimeBase
    } | ConvertTo-Json -Depth 8
}
finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
    }
}
