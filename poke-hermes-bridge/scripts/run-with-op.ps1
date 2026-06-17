$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Get-Command op -ErrorAction SilentlyContinue)) {
    throw "1Password CLI 'op' is not installed or not in PATH."
}
if (-not $env:OP_RUN_NO_MASKING) {
    $env:OP_RUN_NO_MASKING = "true"
}
op run -- python .\server.py
