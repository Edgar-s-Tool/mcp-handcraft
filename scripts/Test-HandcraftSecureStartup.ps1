param(
    [int]$Port = 18765,
    [int]$TimeoutSec = 20
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$serverPath = Join-Path $repoRoot "server_http.py"
$invokeScript = Join-Path $repoRoot "scripts\Invoke-HandcraftMcp.ps1"
$logDir = Join-Path $repoRoot "logs"
$outLog = Join-Path $logDir "secure-startup-test.out.log"
$errLog = Join-Path $logDir "secure-startup-test.err.log"
$baseUrl = "http://127.0.0.1:$Port"
$healthUrl = "$baseUrl/health"
$mcpUrl = "$baseUrl/mcp"
$testToken = "test-token-for-secure-startup"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

try {
    Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 1 | Out-Null
    throw "Port $Port is already serving health. Choose another -Port for an isolated startup test."
} catch {
    if ($_.Exception.Message -like "Port $Port is already serving health*") {
        throw
    }
}

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
$pythonArgs = @("-3", $serverPath)
if (-not $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction Stop
    $pythonArgs = @($serverPath)
}

$env:MCP_API_TOKEN = $testToken
$env:MCP_BASE_URL = $baseUrl
$env:MCP_PORT = [string]$Port

$process = Start-Process `
    -FilePath $pythonCommand.Source `
    -ArgumentList $pythonArgs `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru

try {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        if ($process.HasExited) {
            throw "server_http.py exited during secure startup test. See $errLog"
        }

        try {
            $health = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 1
            if ([int]$health.StatusCode -eq 200) {
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)

    if ((Get-Date) -ge $deadline) {
        throw "Timed out waiting for $healthUrl"
    }

    $response = & $invokeScript -McpUrl $mcpUrl -TimeoutSec 5
    if (-not $response.result.tools) {
        throw "MCP tools/list did not return tools through the env-based wrapper."
    }

    [ordered]@{
        ok = $true
        health_url = $healthUrl
        mcp_url = $mcpUrl
        tool_count = @($response.result.tools).Count
    } | ConvertTo-Json -Depth 4
} finally {
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
    }
    Remove-Item Env:\MCP_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:\MCP_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\MCP_PORT -ErrorAction SilentlyContinue
}
