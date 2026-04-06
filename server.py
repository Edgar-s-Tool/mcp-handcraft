import sys
import json
import os
import glob
import datetime

VAULT_PATH = r"D:\Edgar'sObsidianVault"

# ── Windows: 確保 stdin/stdout 是 binary 模式再包裝成 utf-8 文字流 ──────────
# 不做這步，Windows 會把 \n 轉成 \r\n、或插入 BOM，導致 JSON parse 失敗。
if sys.platform == "win32":
    import msvcrt, os
    msvcrt.setmode(sys.stdin.fileno(),  os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    sys.stdin  = open(sys.stdin.fileno(),  "r", encoding="utf-8", newline="\n", closefd=False)
    sys.stdout = open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", closefd=False)


def log(msg):
    print(f"[MCP] {msg}", file=sys.stderr, flush=True)

def send(response):
    line = json.dumps(response, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    log(f"SEND → {line}")

def send_response(req_id, result):
    send({"jsonrpc": "2.0", "id": req_id, "result": result})

def send_error(req_id, code, message):
    send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})

def handle_initialize(msg):
    log("initialize received")
    send_response(msg["id"], {
        "protocolVersion": "2025-11-25",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "handcraft-mcp", "version": "0.1.0"}
    })

TOOLS = [
    {"name": "vault_read",   "description": "Read a note from the Obsidian vault.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "vault_write",  "description": "Create or overwrite a note in the Obsidian vault.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "vault_move",   "description": "Move or rename a note in the Obsidian vault.", "inputSchema": {"type": "object", "properties": {"source_path": {"type": "string"}, "destination_path": {"type": "string"}}, "required": ["source_path", "destination_path"]}},
    {"name": "vault_delete", "description": "Delete a note from the Obsidian vault.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "vault_list",   "description": "List notes/folders in the vault.", "inputSchema": {"type": "object", "properties": {"folder": {"type": "string"}}}},
    {"name": "vault_search", "description": "Full-text search across vault notes.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]}},
    {"name": "vault_today",  "description": "Get or create today's Daily Note.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "echo",         "description": "Echoes back the input message.", "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}},
]

def handle_tools_list(msg):
    log("tools/list received")
    send_response(msg["id"], {"tools": TOOLS})

def normalize_vault_relative_path(path):
    raw = (path or "").strip()
    if not raw:
        return None, "Path is required"
    if os.path.isabs(raw):
        return None, f"Path must be relative to the vault: {raw}"
    rel = os.path.normpath(raw.lstrip("/\\"))
    if rel in {"", "."}:
        return None, "Path is required"
    if rel == ".." or rel.startswith(f"..{os.sep}"):
        return None, f"Path escapes the vault: {path}"
    return rel, None

def resolve_vault_path(path):
    rel, error = normalize_vault_relative_path(path)
    if error:
        return None, None, error
    root = os.path.abspath(VAULT_PATH)
    full = os.path.abspath(os.path.join(root, rel))
    try:
        if os.path.commonpath([root, full]) != root:
            return None, None, f"Path escapes the vault: {path}"
    except ValueError:
        return None, None, f"Path escapes the vault: {path}"
    return rel, full, None

def vault_read(path):
    rel, full, error = resolve_vault_path(path)
    if error:
        return error, True
    if not os.path.isfile(full):
        matches = glob.glob(os.path.join(VAULT_PATH, "**", os.path.basename(rel)), recursive=True)
        if matches: full = matches[0]
        else: return f"File not found: {rel}", True
    with open(full, "r", encoding="utf-8") as f: content = f.read()
    return f"# {os.path.relpath(full, VAULT_PATH)}\n\n{content}", False

def vault_write(path, content):
    rel, full, error = resolve_vault_path(path)
    if error:
        return error, True
    parent = os.path.dirname(full)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f: f.write(content)
    return f"Written: {rel}", False

def vault_move(source_path, destination_path):
    source_rel, source_full, error = resolve_vault_path(source_path)
    if error:
        return error, True
    dest_rel, dest_full, error = resolve_vault_path(destination_path)
    if error:
        return error, True
    if not os.path.isfile(source_full):
        return f"File not found: {source_rel}", True
    if os.path.exists(dest_full):
        return f"Destination already exists: {dest_rel}", True
    dest_parent = os.path.dirname(dest_full)
    if dest_parent:
        os.makedirs(dest_parent, exist_ok=True)
    os.replace(source_full, dest_full)
    return f"Moved: {source_rel} -> {dest_rel}", False

def vault_delete(path):
    rel, full, error = resolve_vault_path(path)
    if error:
        return error, True
    if not os.path.isfile(full):
        return f"File not found: {rel}", True
    os.remove(full)
    return f"Deleted: {rel}", False

def vault_list(folder=""):
    if folder:
        _, base, error = resolve_vault_path(folder)
        if error:
            return error, True
    else:
        base = VAULT_PATH
    if not os.path.isdir(base): return f"Not found: {folder}", True
    lines = [("📁 " if e.is_dir() else "📄 ") + e.name for e in sorted(os.scandir(base), key=lambda e: (not e.is_dir(), e.name.lower())) if not e.name.startswith(".")]
    return "\n".join(lines) or "(empty)", False

def vault_search(query, max_results=10):
    q = query.lower()
    results = []
    for p in glob.glob(os.path.join(VAULT_PATH, "**", "*.md"), recursive=True):
        try:
            lines = open(p, encoding="utf-8", errors="ignore").readlines()
            for i, line in enumerate(lines):
                if q in line.lower():
                    ctx = "".join(lines[max(0,i-1):i+2]).strip()
                    results.append(f"**{os.path.relpath(p, VAULT_PATH)}** (line {i+1}):\n```\n{ctx}\n```")
                    break
        except: continue
        if len(results) >= max_results: break
    return ("\n\n".join(results) if results else f"No results for: {query}"), False

def vault_today():
    today = datetime.date.today().strftime("%Y-%m-%d")
    full = os.path.join(VAULT_PATH, "Daily Notes", f"{today}.md")
    if os.path.isfile(full):
        return f"# Daily Notes/{today}.md\n\n" + open(full, encoding="utf-8").read(), False
    tmpl = os.path.join(VAULT_PATH, "Templates", "Daily Note.md")
    content = open(tmpl, encoding="utf-8").read().replace('<% tp.date.now("YYYY-MM-DD") %>', today).replace('<% tp.date.now("YYYY-MM-DD dddd") %>', today) if os.path.isfile(tmpl) else f"---\ndate: {today}\ntags: [daily]\n---\n\n# {today}\n\n## 今日重點\n-\n\n## 任務\n- [ ]\n"
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)
    return f"# Daily Notes/{today}.md (created)\n\n{content}", False

def handle_tools_call(msg):
    log("tools/call received")
    args = msg.get("params", {}).get("arguments", {})
    name = msg.get("params", {}).get("name", "")
    text, is_error = "", False
    if name == "echo":
        text = f"echo: {args.get('message', '')}"
    elif name == "vault_read":
        text, is_error = vault_read(args.get("path", ""))
    elif name == "vault_write":
        text, is_error = vault_write(args.get("path", ""), args.get("content", ""))
    elif name == "vault_move":
        text, is_error = vault_move(args.get("source_path", ""), args.get("destination_path", ""))
    elif name == "vault_delete":
        text, is_error = vault_delete(args.get("path", ""))
    elif name == "vault_list":
        text, is_error = vault_list(args.get("folder", ""))
    elif name == "vault_search":
        text, is_error = vault_search(args.get("query", ""), args.get("max_results", 10))
    elif name == "vault_today":
        text, is_error = vault_today()
    else:
        send_error(msg["id"], -32601, f"Tool not found: {name}")
        return
    send_response(msg["id"], {"content": [{"type": "text", "text": text}], "isError": is_error})

def handle_ping(msg):
    log("ping received")
    send_response(msg["id"], {})

def handle_request(msg):
    method = msg.get("method", "")
    log(f"request: {method}")
    if method == "initialize":
        handle_initialize(msg)
    elif method == "tools/list":
        handle_tools_list(msg)
    elif method == "tools/call":
        handle_tools_call(msg)
    elif method == "ping":
        handle_ping(msg)
    else:
        send_error(msg.get("id"), -32601, f"Method not found: {method}")

def handle_notification(msg):
    log(f"notification: {msg.get('method')} (ignored)")

def dispatch(msg):
    if "id" in msg:
        handle_request(msg)
    else:
        handle_notification(msg)

def main():
    log("handcraft-mcp server started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            dispatch(msg)
        except json.JSONDecodeError as e:
            log(f"parse error: {e}")
            send_error(None, -32700, "Parse error")

if __name__ == "__main__":
    main()
