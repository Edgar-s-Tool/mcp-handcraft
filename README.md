# mcp-handcraft

這個資料夾有兩條不同的 MCP server 入口，請分開使用，不要混用。

## 入口分工

- `run.cmd`
  啟動 `server.py`
  給本地 `stdio` 方式的 MCP client 使用。
  適合 Ollama、龍蝦這類直接用標準輸入輸出溝通的本地流程。
  目前走 Windows `py -3` launcher，不綁死特定使用者路徑。

- `run_http.cmd`
  啟動 `server_http.py`
  給 HTTP 方式的 MCP client 使用。
  適合 MCP Inspector、瀏覽器測試、或其他會用 `POST /mcp` 連進來的 client。
  目前走 Windows `py -3` launcher，不綁死特定使用者路徑。

## 現況提醒

- `server.py` 是本地 `stdio` 入口
- `server_http.py` 是 HTTP 入口
- `server_http.py` 目前已接上 `codex_agent`
- `server_http.py` 目前也已接上 `claude_code_agent`

## Claude Code 前提

如果要用 `claude_code_agent`，本機需要先完成：

```powershell
winget install Anthropic.ClaudeCode
claude auth login
```

如果 `claude` 指令不在 PATH，HTTP tool call 會失敗。

`claude_code_agent` 會優先使用本機 Claude Code 的登入狀態；即使啟動 server 的環境裡有 `ANTHROPIC_API_KEY` 或 `ANTHROPIC_BASE_URL`，也不應再讓它覆蓋訂閱 OAuth。

## HTTP 版注意事項

- `server_http.py` 啟動前必須有非空白的 `MCP_API_TOKEN`。
- 若 `MCP_API_TOKEN` 未設定、空字串或只有空白，HTTP server 會 fail-fast，不會進入監聽狀態。
- 最小啟動範例：

```powershell
$env:MCP_API_TOKEN = "replace-with-a-long-random-token"
py -3 server_http.py
```

- `server_http.py` 目前預設會在 `90` 秒內等 agent 回覆。
- 這是為了避免 Cloudflare Tunnel 一類的 HTTP 代理先超時，外面只看到空白或中斷。
- 若要改長一點，可設定環境變數 `MCP_AGENT_TIMEOUT_SECONDS`。

## 本機 smoke test

```powershell
py -3 -m unittest test_server_http.py
```

目前 smoke test 會覆蓋 `claude_code_agent` 的 tool schema、缺少 `task`、命令不存在錯誤，以及一個不呼叫真實 Claude Code 的正常呼叫範例。
