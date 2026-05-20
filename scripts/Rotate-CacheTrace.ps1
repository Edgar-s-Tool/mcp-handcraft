[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$LogPath = (Join-Path (Get-Location) "logs\cache-trace.jsonl"),
    [string]$ArchiveDir = (Join-Path (Get-Location) "logs\archive\cache-trace"),
    [double]$MaxSizeMB = 128,
    [int]$MaxAgeDays = 1,
    [int]$RetainArchives = 14,
    [switch]$Force,
    [switch]$PassThru
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-FullPath {
    param([Parameter(Mandatory = $true)][string]$PathValue)
    return [System.IO.Path]::GetFullPath($PathValue)
}

function Test-ForbiddenArchivePath {
    param([Parameter(Mandatory = $true)][string]$FullPath)

    $normalized = $FullPath.TrimEnd("\")
    $forbiddenFragments = @(
        "\Desktop",
        "\Edgars_secret",
        "\AI-Cache",
        "\AI_WORK_512",
        "\AppData\Local\Temp",
        "\.openclaw\workspace"
    )

    foreach ($fragment in $forbiddenFragments) {
        if ($normalized.IndexOf($fragment, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $true
        }
    }

    return $false
}

if ($MaxSizeMB -le 0) {
    throw "MaxSizeMB must be greater than 0."
}

if ($MaxAgeDays -lt 0) {
    throw "MaxAgeDays must be 0 or greater."
}

if ($RetainArchives -lt 1) {
    throw "RetainArchives must be 1 or greater."
}

$logFullPath = Get-FullPath $LogPath
$archiveFullPath = Get-FullPath $ArchiveDir

if (Test-ForbiddenArchivePath $archiveFullPath) {
    throw "ArchiveDir is in a forbidden location. Do not archive cache trace logs to Desktop, secrets, runtime workspace, or AI cache paths."
}

$result = [ordered]@{
    log_path = $logFullPath
    archive_dir = $archiveFullPath
    rotated = $false
    reason = ""
    archive_path = $null
    checkpoint_path = $null
    retained_archives = @()
    retired_archives = @()
}

if (-not (Test-Path -LiteralPath $logFullPath -PathType Leaf)) {
    $result.reason = "log_missing"
    $output = [pscustomobject]$result
    if ($PassThru) { return $output }
    $output | ConvertTo-Json -Depth 5
    return
}

$logItem = Get-Item -LiteralPath $logFullPath
$maxBytes = [int64]($MaxSizeMB * 1MB)
$sizeExceeded = $logItem.Length -ge $maxBytes
$ageExceeded = $false

if ($MaxAgeDays -gt 0) {
    $ageThresholdUtc = (Get-Date).ToUniversalTime().AddDays(-1 * $MaxAgeDays)
    $ageExceeded = $logItem.LastWriteTimeUtc -lt $ageThresholdUtc
}

if (-not $Force -and -not $sizeExceeded -and -not $ageExceeded) {
    $result.reason = "below_threshold"
    $output = [pscustomobject]$result
    if ($PassThru) { return $output }
    $output | ConvertTo-Json -Depth 5
    return
}

if (-not (Test-Path -LiteralPath $archiveFullPath -PathType Container) -and
    $PSCmdlet.ShouldProcess($archiveFullPath, "Create cache trace archive directory")) {
    New-Item -ItemType Directory -Path $archiveFullPath -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archivePath = Join-Path $archiveFullPath "cache-trace-$timestamp.jsonl"
$checkpointPath = Join-Path $archiveFullPath "cache-trace-$timestamp.checkpoint.json"

$checkpoint = [ordered]@{
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    log_path = $logFullPath
    archive_path = $archivePath
    size_bytes = $logItem.Length
    last_write_time_utc = $logItem.LastWriteTimeUtc.ToString("o")
    max_size_mb = $MaxSizeMB
    max_age_days = $MaxAgeDays
    retain_archives = $RetainArchives
    trigger = if ($Force) { "force" } elseif ($sizeExceeded) { "size" } else { "age" }
}

if ($PSCmdlet.ShouldProcess($logFullPath, "Rotate cache trace log to $archivePath")) {
    $checkpoint | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $checkpointPath -Encoding UTF8
    Move-Item -LiteralPath $logFullPath -Destination $archivePath
    New-Item -ItemType File -Path $logFullPath -Force | Out-Null
}

if (Test-Path -LiteralPath $archiveFullPath -PathType Container) {
    $archives = Get-ChildItem -LiteralPath $archiveFullPath -Filter "cache-trace-*.jsonl" -File |
        Sort-Object LastWriteTimeUtc -Descending
} else {
    $archives = @()
}

$surplusArchives = @($archives | Select-Object -Skip $RetainArchives)
$retiredArchives = @()

if ($surplusArchives.Count -gt 0) {
    $retiredDir = Join-Path $archiveFullPath "retired"
    if (-not (Test-Path -LiteralPath $retiredDir -PathType Container) -and
        $PSCmdlet.ShouldProcess($retiredDir, "Create retired archive directory")) {
        New-Item -ItemType Directory -Path $retiredDir -Force | Out-Null
    }

    foreach ($archive in $surplusArchives) {
        $retiredArchivePath = Join-Path $retiredDir $archive.Name
        if ($PSCmdlet.ShouldProcess($archive.FullName, "Retire cache trace archive to $retiredArchivePath")) {
            Move-Item -LiteralPath $archive.FullName -Destination $retiredArchivePath
            $retiredArchives += $retiredArchivePath

            $checkpointName = [System.IO.Path]::GetFileNameWithoutExtension($archive.Name) + ".checkpoint.json"
            $checkpointSource = Join-Path $archiveFullPath $checkpointName
            if (Test-Path -LiteralPath $checkpointSource -PathType Leaf) {
                Move-Item -LiteralPath $checkpointSource -Destination (Join-Path $retiredDir $checkpointName)
            }
        }
    }
}

if (Test-Path -LiteralPath $archiveFullPath -PathType Container) {
    $archives = Get-ChildItem -LiteralPath $archiveFullPath -Filter "cache-trace-*.jsonl" -File |
        Sort-Object LastWriteTimeUtc -Descending
} else {
    $archives = @()
}

$result.rotated = $true
$result.reason = $checkpoint.trigger
$result.archive_path = $archivePath
$result.checkpoint_path = $checkpointPath
$result.retained_archives = @($archives | Select-Object -First $RetainArchives | ForEach-Object { $_.FullName })
$result.retired_archives = $retiredArchives

$output = [pscustomobject]$result
if ($PassThru) { return $output }
$output | ConvertTo-Json -Depth 5
