> 繁體中文版。原始文件：OPS.md（英文）

# handcraft-mcp 操作手冊

> 適用版本：0.1.0

這份手冊聚焦在 `handcraft-mcp` 的日常維運（operations，維運）工作，包含架構、啟停、Doppler secrets（機密）、tool（工具）擴充、安全設定與連線測試。

## 1. 架構一覽

```
本機
├── server.py          ← stdio 模式（Claude Desktop / OpenClaw 本機呼叫）
├── server_http.py     ← HTTP 模式（遠端 / mcp.whoasked.vip）
├── run.cmd            ← 啟動 stdio server（透過 Doppler 注入 key）
└── run_http.cmd       ← 啟動 HTTP server（透過 Doppler 注入 key）

Doppler（雲端）
└── project: handcraft-mcp / config: prd
    └── 存放所有 API key，啟動時注入，不落地

Cloudflare Tunnel
└── mcp.whoasked.vip → 本機 :8765/mcp
```

### 兩個 server 的差異

| 項目 | `server.py`（stdio） | `server_http.py`（HTTP） |
|---|---|---|
| 用途 | 本機 agent（代理）直連 | 外網 / 遠端呼叫 |
| 啟動方式 | `run.cmd` | `run_http.cmd` |
| Port（連接埠） | 無 | `8765` |
| 工具數 | `echo` | 主要 HTTP 工具集合（目前 61 個工具） |
| Auth（驗證） | 不需要 | Bearer token |

## 2. 啟動 / 停止

### 啟動 HTTP server

```cmd
cd C:\Users\EdgarsTool\Projects\mcp-handcraft
run_http.cmd
```

### 啟動 stdio server

```cmd
run.cmd
```

### 停止
在執行中的視窗按 `Ctrl+C`。

### 確認是否在跑

```bash
netstat -ano | findstr :8765
```

## 3. Secret 管理（Doppler）

```bash
doppler secrets set MY_API_KEY=sk-xxxx
doppler secrets get MY_API_KEY
doppler secrets delete MY_API_KEY
doppler secrets
```

改完 secret（機密）後要重啟 server，因為 Doppler 是在啟動時把環境變數注入程序。

## 4. 在 `server_http.py` 讀取 key

```python
import os
MY_KEY = os.getenv("MY_API_KEY", "")
```

建議把 secrets 集中宣告在檔案前段，方便維護與盤點。

## 5. 新增 tool（工具）流程

1. 在 `TOOLS` 清單新增 schema（結構定義）
2. 在 `handle_tools_call` 中加入分支
3. 實作對應 handler（處理函式）

```python
if name == "my_tool":
    return handle_my_tool(req_id, arguments)
```

## 6. 可調環境變數

| 變數名稱 | 預設值 | 說明 |
|---|---|---|
| `MCP_AGENT_TIMEOUT_SECONDS` | `300` | 代理最長執行秒數 |
| `MCP_JOB_RETENTION_SECONDS` | `3600` | 背景 job（工作）保留秒數 |

## 7. 安全設定

- HTTP server 使用 Bearer token（權杖）驗證
- `MCP_API_TOKEN` 已由 Doppler 注入
- `ALLOWED_HOSTNAMES` 用來限制 origin（來源網域），避免 DNS rebinding 類風險

## 8. Cloudflare Tunnel

| 設定項目 | 值 |
|---|---|
| Tunnel 名稱 | `home-tunnel` |
| 對外網址 | `https://mcp.whoasked.vip` |
| 本機目標 | `http://localhost:8765` |

`cloudflared` 目前已設為 Windows Automatic service；`handcraft-mcp` 本體仍需手動啟動 `run_http.cmd`。

## 9. Log（記錄）查看

```cmd
run_http.cmd 2> C:\Users\EdgarsTool\Projects\mcp-handcraft\mcp.log
```

## 10. 連線測試

```bash
curl -X POST http://localhost:8765/mcp \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"},\"capabilities\":{}}}"
```

## 11. 常見問題

- **Doppler key 更新後沒生效**：停掉 server 再重跑 `run_http.cmd`
- **收到 403 Forbidden**：把來源網域加進 `ALLOWED_HOSTNAMES`
- **收到 401 Unauthorized**：補上 `Authorization: Bearer ...`
- **agent timeout**：考慮改成 `"async": true`
- **Doppler 登入過期**：執行 `doppler login`
