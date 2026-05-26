@echo off
setlocal
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    doppler run --project handcraft-mcp --config prd -- py -3 "%~dp0server_http.py"
) else (
    doppler run --project handcraft-mcp --config prd -- python "%~dp0server_http.py"
)
