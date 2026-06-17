# poke-hermes-bridge OPS

## 架構

```text
iPhone
-> Poke
-> Cloudflare
-> poke-hermes-bridge
-> Hermes inbox / Hermes localhost API
```

## 路由

- `GET /health`
- `POST /mcp`
- `POST /webhook/linear`
- `POST /webhook/tool`

## 啟動模式

- `HERMES_MODE=http`
  - 目標：直接打 `HERMES_STATUS_URL` / `HERMES_INBOX_URL`
  - 適用：Hermes localhost API 已常駐
- `HERMES_MODE=file`
  - 目標：直接寫 `HERMES_INBOX_FILE`
  - 適用：Hermes API 尚未起來，或先走最小 fallback 鏈路

## Runtime 建議

- Python runtime writable state 建議走系統 `TEMP`
- 不要把 task store / inbox file / temp log 綁在 `G:` repo 目錄
- bridge 目前已內建 fallback；若指定路徑不可寫，會自動退回系統 `TEMP`

關鍵 env：

- `POKE_API_KEY`
- `POKE_NOTIFY_URL`
- `LINEAR_WEBHOOK_SECRET`
- `TOOL_WEBHOOK_SECRET`
- `HERMES_MODE`
- `POKE_BRIDGE_TEMP_DIR`
- `POKE_BRIDGE_TASK_STORE`
- `HERMES_INBOX_FILE`

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
- 目前實際使用的 temp/task/inbox 路徑

## Smoke Test

```powershell
cd G:\AI_WORK_512\repos\mcp-handcraft\poke-hermes-bridge
python -m unittest discover -s tests -p "test_*.py"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-local.ps1
```

`scripts\smoke-local.ps1` 會：

- 用 `file` 模式起 bridge
- 驗證 `/health`
- 驗證 `tools/list`
- 驗證 `create_pending_task`
- 驗證 `send_to_hermes_inbox`

## 安全邊界

- 所有外送通知都只會打到固定的 `POKE_NOTIFY_URL`
- 所有 Hermes 存取都只會走固定的 env URL 或固定 inbox file
- `write_temp_log` 只能寫到 `POKE_BRIDGE_TEMP_DIR`
- webhook 必須驗 shared secret
- 不提供任意 shell、任意 URL、任意檔案操作
