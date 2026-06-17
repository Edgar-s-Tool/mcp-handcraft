$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not $env:POKE_API_KEY) {
    throw "POKE_API_KEY is required in current environment."
}
python .\server.py
