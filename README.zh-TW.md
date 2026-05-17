> 繁體中文版。原始文件：README.md（英文）

# mcp-handcraft

`mcp-handcraft` 是 Edgar 的本地 MCP（Model Context Protocol）server（伺服器）。
它讓支援 MCP 的 AI client（客戶端），例如 Claude、OpenClaw 等，可以透過 HTTP 直接操作本機環境，涵蓋檔案系統、Git、系統指令、瀏覽器、自動化代理、Obsidian Vault、Linear、Notion 與多媒體生成能力。

**目前工具數量：61 個**

---

## 架構

```
mcp-handcraft/
├── server_http.py      ← 主 HTTP MCP Server（port 8765，所有工具都在這）
├── server.py           ← stdio 入口（供本地 stdio client 使用）
├── mmx_handlers.py     ← MiniMax 媒體生成 handlers
├── run.cmd             ← 啟動 stdio server（透過 Doppler 注入 secrets）
├── run_http.cmd        ← 啟動 HTTP server（透過 Doppler 注入 secrets）
└── test_server_http.py ← smoke test
```

## 啟動方式

### 正常啟動（透過 Doppler 注入 secrets）

```powershell
cd C:\Users\EdgarsTool\Projects\mcp-handcraft
doppler run --project handcraft-mcp --config prd -- py -3 server_http.py
```

### 背景啟動

```powershell
Start-Process powershell -ArgumentList '-NoProfile','-Command',
  'cd "C:\Users\EdgarsTool\Projects\mcp-handcraft"; doppler run --project handcraft-mcp --config prd -- py -3 server_http.py' -WindowStyle Minimized
```

### 確認運作中

```powershell
Get-NetTCPConnection -LocalPort 8765
# 或
Invoke-RestMethod http://localhost:8765/health
```

### 停止

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8765).OwningProcess -Force
```

## 環境需求

| 項目 | 說明 |
|---|---|
| Python | 3.11+ |
| Doppler | secrets（機密）管理，使用 `handcraft-mcp` / `prd` |
| Playwright | `playwright install chromium`，供 browser tools（瀏覽器工具）使用 |
| Claude Code | `winget install Anthropic.ClaudeCode` 後再 `claude auth login` |
| Ollama | 本地模型執行環境 |
| mmx CLI | MiniMax 媒體生成工具 |

## 認證

所有請求都必須帶 Bearer token（權杖）：

```
Authorization: Bearer <MCP_API_TOKEN>
```

`MCP_API_TOKEN` 由 Doppler 管理。

## 工具總覽

### AI agents（代理）
- `codex_agent`：委派程式碼實作與檔案編輯
- `gemini_agent`：處理快速通用任務
- `claude_code_agent`：執行複雜重構與多檔操作
- `ollama_agent`：使用本地模型離線執行
- `smart_agent`：依情境自動選擇代理
- `agent_job_status` / `agent_job_list` / `agent_job_cleanup`：管理背景工作

> 長任務建議加上 `"async": true`，先拿 `job_id`，再輪詢 `agent_job_status`。

### File system（檔案系統）
- `fs_list`
- `fs_read`
- `fs_write`
- `fs_move`
- `fs_delete`
- `fs_search`
- `fs_disk_info`

### System（系統）
- `sys_run`
- `sys_info`
- `sys_processes`

### Git
- `git_status`
- `git_log`
- `git_diff`
- `git_commit`

### Browser（瀏覽器）
- `browser_screenshot`
- `browser_get_text`
- `browser_run_script`

### 其他整合
- `web_search`：Perplexity 搜尋
- `linear_*`：Linear 任務管理
- `notion_*`：Notion 讀取與搜尋
- `image_generate_free`：免費圖片生成
- `mmx_*`：MiniMax 媒體生成
- `vault_*`：Obsidian Vault 操作

## Vault（知識庫）補充

預設 Vault 路徑：`D:\Edgar'sObsidianVault`

這組工具支援讀寫筆記、建立模板、整理 Inbox、列出未完成任務與標籤，並採用 PARA（Projects, Areas, Resources, Archive）方法整理內容。

## Smoke Test

```powershell
cd C:\Users\EdgarsTool\Projects\mcp-handcraft
doppler run -- python -m unittest test_server_http.py -v
```

## 環境變數

| 變數 | 說明 |
|---|---|
| `MCP_API_TOKEN` | Bearer token（權杖） |
| `PERPLEXITY_API_KEY` | `web_search` 使用 |
| `OPENAI_API_KEY` | 備援金鑰 |
| `LINEAR_API_KEY` | Linear 操作 |
| `NOTION_API_KEY` | Notion 讀取 |
| `MCP_AGENT_TIMEOUT_SECONDS` | 代理等待上限 |
| `MCP_BASE_URL` | 公開 URL |

## 公開端點

```
https://mcp.whoasked.vip/mcp
```

此端點透過 Cloudflare Tunnel 對外提供服務；對外入口是 `https://mcp.whoasked.vip/mcp`，本機服務是 `http://localhost:8765`。
目前 `cloudflared` 已設為 Windows Automatic service；`handcraft-mcp` 本體仍需手動啟動。
