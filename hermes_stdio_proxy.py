import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

# Hermes stdio MCP proxy for handcraft HTTP MCP.
# Token is read only inside this child process. It is never printed.
URL = os.getenv("HANDCRAFT_MCP_URL", "http://127.0.0.1:8765/mcp")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(PROJECT_DIR, "hermes_handcraft_http.log")


def _get_token() -> str:
    token = os.getenv("MCP_API_TOKEN", "").strip()
    if token:
        return token
    try:
        # Keep the secret inside this process; do not log stdout/stderr.
        out = subprocess.check_output(
            ["doppler", "secrets", "get", "MCP_API_TOKEN", "--plain", "--project", "handcraft-mcp", "--config", "prd"],
            cwd=PROJECT_DIR,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=20,
        )
        return out.strip()
    except Exception:
        return ""


TOKEN = _get_token()

# Do not force Windows binary stdio here. Under Git Bash/MSYS + Doppler,
# msvcrt.setmode() can break stdout pipes with OSError 22. Plain UTF-8 JSONL
# is enough for Hermes's stdio MCP client.
try:
    sys.stdin.reconfigure(encoding="utf-8", newline="\n")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
except Exception:
    pass


def log(msg: str) -> None:
    print(f"[handcraft-proxy] {msg}", file=sys.stderr, flush=True)


def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def forward(msg: dict) -> dict | None:
    # Notifications do not need a response. Forward initialized best-effort.
    is_notification = "id" not in msg
    body = json.dumps(msg).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(URL, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        if is_notification:
            log(f"notification forward failed HTTP {e.code}: {raw[:200]}")
            return None
        return error(msg.get("id"), -32000, f"HTTP {e.code}: {raw[:500]}")
    except Exception as e:
        if is_notification:
            log(f"notification forward failed: {type(e).__name__}: {e}")
            return None
        return error(msg.get("id"), -32000, f"Proxy error: {type(e).__name__}: {e}")

    # Streamable HTTP may return SSE. Extract JSON data events.
    raw_strip = raw.strip()
    if not raw_strip:
        return None if is_notification else error(msg.get("id"), -32000, "Empty response from HTTP MCP")
    if raw_strip.startswith("data:") or "\ndata:" in raw_strip:
        events = []
        for line in raw_strip.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    events.append(data)
        raw_strip = events[-1] if events else ""
    if not raw_strip:
        return None if is_notification else error(msg.get("id"), -32000, "No JSON data in SSE response")
    try:
        return json.loads(raw_strip)
    except Exception:
        return error(msg.get("id"), -32700, f"Bad JSON from HTTP MCP: {raw_strip[:500]}")


def _http_running() -> bool:
    try:
        req = urllib.request.Request(URL, data=b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}', method="POST", headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {TOKEN}",
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _ensure_http_server() -> None:
    if _http_running():
        return
    try:
        log("HTTP server not detected; starting it in background")
        with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as logf:
            subprocess.Popen(
                ["doppler", "run", "--project", "handcraft-mcp", "--config", "prd", "--", sys.executable, "server_http.py"],
                cwd=PROJECT_DIR,
                stdin=subprocess.DEVNULL,
                stdout=logf,
                stderr=logf,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        for _ in range(20):
            time.sleep(0.5)
            if _http_running():
                return
    except Exception as exc:
        log(f"failed to auto-start HTTP server: {type(exc).__name__}: {exc}")


def main() -> None:
    if not TOKEN:
        log("MCP_API_TOKEN missing; HTTP server will likely reject requests")
    _ensure_http_server()
    log(f"proxy started -> {URL}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            send(error(None, -32700, "Parse error"))
            continue
        resp = forward(msg)
        if resp is not None:
            send(resp)


if __name__ == "__main__":
    main()
