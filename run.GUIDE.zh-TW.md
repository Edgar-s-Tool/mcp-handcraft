> 繁體中文版。原始文件：run.cmd（英文）

# run.cmd 解說

## 這個檔案做什麼
這個批次檔（batch file，批次腳本）負責啟動 `server.py`。它會先用 `doppler run` 注入 secrets（機密），再用 Windows 的 `py -3` 執行與腳本同目錄的 Python 檔，因此適合 stdio（標準輸入/輸出）模式的 MCP client（客戶端）。

## 主要區塊說明

### `@echo off`
關閉指令回顯，讓啟動畫面更乾淨。

### `setlocal`
建立區域環境，避免此腳本內設定影響外部 shell（命令殼層）。

### `doppler run --project handcraft-mcp --config prd -- py -3 "%~dp0server.py"`
這一行是核心：
- `--project handcraft-mcp`：指定 Doppler project（專案）
- `--config prd`：指定 production config（正式環境設定）
- `py -3`：要求使用 Python 3
- `%~dp0server.py`：執行目前腳本所在目錄下的 `server.py`

## 常用指令

```cmd
cd C:\Users\EdgarsTool\Projects\mcp-handcraft
run.cmd
```

```cmd
doppler run --project handcraft-mcp --config prd -- py -3 server.py
```

## 注意事項
- 執行前必須先安裝並登入 Doppler。
- 若 `server.py` 依賴其他 secrets，需確認 `prd` config（設定）中已存在。
- 這個腳本只適合 stdio 模式；若要開 HTTP server，請改用 `run_http.cmd`。
