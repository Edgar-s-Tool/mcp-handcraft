> 繁體中文版。原始文件：run_http.cmd（英文）

# run_http.cmd 解說

## 這個檔案做什麼
這個批次檔會在注入 Doppler secrets（機密）後啟動 `server_http.py`，用來提供 HTTP 型態的 MCP server（伺服器）。若要讓遠端 client（客戶端）透過 `https://mcp.whoasked.vip/mcp` 連進來，通常就是靠這個腳本啟動。

## 主要區塊說明

### `@echo off`
關閉畫面上的指令回顯。

### `setlocal`
將環境變數變更限制在此腳本執行範圍內。

### `doppler run --project handcraft-mcp --config prd -- py -3 "%~dp0server_http.py"`
核心行為如下：
- 用 `handcraft-mcp` / `prd` 讀取 secrets
- 呼叫 Python 3 執行 `server_http.py`
- `%~dp0` 確保無論從哪個目錄執行，都能正確找到腳本旁的 Python 檔

## 常用指令

```cmd
cd C:\Users\EdgarsTool\Projects\mcp-handcraft
run_http.cmd
```

```powershell
Invoke-RestMethod http://localhost:8765/health
```

## 注意事項
- 若 `8765` port（連接埠）已被占用，`server_http.py` 可能無法正常啟動。
- 啟動後若修改 Doppler secrets，必須重啟此腳本才能重新載入。
- 對外連線是否真的可用，還取決於 Cloudflare Tunnel 與 DNS 設定；⚠️ 此處需人工確認。
