# poke-hermes-bridge

給 Poke 使用的白名單 MCP Bridge。

目標是把 Poke 可操作的能力縮到最小，只允許透過固定工具呼叫本地 Hermes，
不提供任意 shell、任意檔案、任意 URL、或直接公開 Hermes localhost port。

## 第一階段允許工具

- `hermes_status`
- `send_to_hermes_inbox`
- `create_pending_task`
- `get_task_status`
- `write_temp_log`
- `notify_poke`

## 第一階段禁止能力

- `run_powershell`
- `read_file_anywhere`
- `write_file_anywhere`
- `edit_obsidian_note`
- `edit_hermes_config`
- `scan_agent_kb`
- `scan_secret_folder`
- `call_any_url`

## 本機 fallback 與 writable state

本機目前可用的 fallback 是 `HERMES_MODE=file`。
當 Hermes HTTP `127.0.0.1:18789` 沒有啟動，或不想讓 bridge 直接依賴本機 Hermes API 時，
bridge 仍可先把 Hermes inbox 落到檔案，維持最小可用鏈路。

runtime writable state 建議走系統 `TEMP`，不要綁在 `G:` repo 內：

- `POKE_BRIDGE_TEMP_DIR`
- `POKE_BRIDGE_TASK_STORE`
- `HERMES_INBOX_FILE`

未指定時，程式目前也會預設落在 `TEMP\poke-hermes-bridge`。

## Diagnostics

先做本機診斷：

```powershell
cd G:\AI_WORK_512\repos\mcp-handcraft\poke-hermes-bridge
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
```

這支腳本會檢查：

- 必要 env 是否存在
- `127.0.0.1:8788` bridge port
- `127.0.0.1:18789` Hermes port
- `op` 1Password CLI 是否在 PATH

如果只是要確認 fallback 鏈路，本機 smoke 可直接跑：

```powershell
cd G:\AI_WORK_512\repos\mcp-handcraft\poke-hermes-bridge
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-local.ps1
```

## 啟動

直接用目前 shell env：

```powershell
cd G:\AI_WORK_512\repos\mcp-handcraft\poke-hermes-bridge
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-local.ps1
```

用 1Password CLI 注入 env：

```powershell
cd G:\AI_WORK_512\repos\mcp-handcraft\poke-hermes-bridge
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-with-op.ps1
```

若要明確指定 fallback 路徑，建議像這樣綁在 `TEMP` 底下，而不是 repo 目錄：

```powershell
$base = Join-Path $env:TEMP 'poke-hermes-bridge'
$env:HERMES_MODE = 'file'
$env:POKE_BRIDGE_TEMP_DIR = $base
$env:POKE_BRIDGE_TASK_STORE = Join-Path $base 'tasks.json'
$env:HERMES_INBOX_FILE = Join-Path $base 'hermes-inbox.jsonl'
```
