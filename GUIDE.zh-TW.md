> 繁體中文版。原始文件：GUIDE.md（英文）

# handcraft-mcp 使用指南

這份文件說明如何把支援 MCP 的 AI client（客戶端）連到 `handcraft-mcp`，以使用遠端工具、代理委派與自動化能力。

## 快速連接

### MCP Server 資訊

| 項目 | 內容 |
|---|---|
| 端點 | `https://mcp.whoasked.vip/mcp` |
| 協議版本 | `2025-11-25` |
| 傳輸方式 | Streamable HTTP（可串流 HTTP） |

## 各客戶端設定方式

### Claude Code

在 `~/.claude.json` 的 `mcpServers` 加入：

```json
{
  "mcpServers": {
    "handcraft-mcp": {
      "type": "http",
      "url": "https://mcp.whoasked.vip/mcp"
    }
  }
}
```

或直接執行：

```bash
npx mcp-add \
  --name handcraft-mcp \
  --type http \
  --url "https://mcp.whoasked.vip/mcp" \
  --clients "claude code"
```

### Claude Desktop

在 `claude_desktop_config.json` 加入：

```json
{
  "mcpServers": {
    "handcraft-mcp": {
      "type": "http",
      "url": "https://mcp.whoasked.vip/mcp"
    }
  }
}
```

**設定檔位置：**
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`
- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`

### Cursor

進入 `Settings > MCP` 後新增：

```json
{
  "handcraft-mcp": {
    "type": "http",
    "url": "https://mcp.whoasked.vip/mcp"
  }
}
```

### Windsurf

在 `~/.codeium/windsurf/mcp_config.json` 加入：

```json
{
  "mcpServers": {
    "handcraft-mcp": {
      "type": "http",
      "url": "https://mcp.whoasked.vip/mcp"
    }
  }
}
```

### VS Code（Copilot）

在 `.vscode/mcp.json` 加入：

```json
{
  "servers": {
    "handcraft-mcp": {
      "type": "http",
      "url": "https://mcp.whoasked.vip/mcp"
    }
  }
}
```

## 可用工具摘要

### `echo`
用來驗證連線是否成功，會回傳你傳入的訊息。

### `codex_agent`
把任務委派給本機 Codex agent（代理）。適合程式碼實作、檔案建立與腳本操作。

### `claude_code_agent`
把複雜的程式任務交給 Claude Code agent（代理），適合分析大型程式碼與多檔重構。

## 驗證連線

```bash
curl -X POST https://mcp.whoasked.vip/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","clientInfo":{"name":"test","version":"1.0"},"capabilities":{}}}'
```

若回應中包含 `"serverInfo": { "name": "handcraft-mcp" }`，代表初始化成功。

## 常見問題

- **連不上端點**：先用 `curl` 測試，再確認 server（伺服器）是否啟動。
- **工具沒顯示**：重啟 Claude Code、Cursor 等 client（客戶端），讓它重新載入 MCP 設定。
- **任務執行很慢**：代理工具的 timeout（逾時）較長，複雜任務可考慮改用背景模式。
