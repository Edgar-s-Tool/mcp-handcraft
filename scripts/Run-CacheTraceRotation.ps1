[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$logsDir = Join-Path $repoRoot "logs"
$logPath = Join-Path $logsDir "cache-trace.jsonl"
$archiveDir = Join-Path $logsDir "archive\cache-trace"
$statusPath = Join-Path $logsDir "cache-trace-rotation-status.json"
$rotationScript = Join-Path $repoRoot "scripts\Rotate-CacheTrace.ps1"

if (-not (Test-Path -LiteralPath $logsDir -PathType Container)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

& $rotationScript -LogPath $logPath -ArchiveDir $archiveDir |
    Set-Content -LiteralPath $statusPath -Encoding UTF8
