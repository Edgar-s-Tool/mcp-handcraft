# Thin wrapper — delegates to linear-orchestrator Windows scripts.
param(
    [ValidateSet("start", "stop", "check", "install")]
    [string]$Action = "check",
    [switch]$Public,
    [switch]$Wait
)

$OrchestratorRoot = "G:\AI_WORK_512\repos\linear-orchestrator"
$script = switch ($Action) {
    "start"   { "Start-LinearOrchestrator.ps1" }
    "stop"    { "Stop-LinearOrchestrator.ps1" }
    "check"   { "Check-LinearOrchestrator.ps1" }
    "install" { "Install-LinearOrchestratorWindows.ps1" }
}

$path = Join-Path $OrchestratorRoot "scripts\$script"
if (-not (Test-Path -LiteralPath $path)) {
    throw "Missing $path"
}

$args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $path)
if ($Wait -and $Action -eq "start") { $args += "-Wait" }
if ($Public -and $Action -eq "check") { $args += "-Public" }

& powershell.exe @args
