from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from adapters.hermes_client import HermesClient
from adapters.poke_client import PokeClient
from config import BridgeConfig
from policy import TOOLS, is_allowed_tool
from task_store import TaskStore


def make_text_result(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


class BridgeService:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.hermes = HermesClient(config)
        self.poke = PokeClient(config)
        self.tasks = TaskStore(config.task_store_path)
        self.config.temp_dir.mkdir(parents=True, exist_ok=True)

    def health_payload(self) -> dict:
        return {
            "ok": True,
            "service": "poke-hermes-bridge",
            "tools": len(TOOLS),
            "host": self.config.host,
            "port": self.config.port,
            "hermes_mode": self.config.hermes_mode,
            "temp_dir": str(self.config.temp_dir),
            "task_store_path": str(self.config.task_store_path),
            "hermes_inbox_file": str(self.config.hermes_inbox_file),
            "runtime_warnings": list(self.config.runtime_warnings),
        }

    def handle_mcp(self, payload: dict) -> tuple[int, dict]:
        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params", {})

        if method == "initialize":
            return 200, {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2025-11-25",
                    "serverInfo": {"name": "poke-hermes-bridge", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                },
            }
        if method == "tools/list":
            return 200, {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
        if method != "tools/call":
            return 400, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not supported"}}

        name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}
        if not is_allowed_tool(name):
            return 403, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Tool not allowed: {name}"}}

        try:
            result = self._call_tool(name, arguments)
            return 200, {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as exc:
            return 500, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(exc)}}

    def _call_tool(self, name: str, arguments: dict) -> dict:
        if name == "hermes_status":
            result = self.hermes.status()
            result["runtime_warnings"] = list(self.config.runtime_warnings)
            return make_text_result(json.dumps(result, ensure_ascii=False, indent=2))
        if name == "send_to_hermes_inbox":
            title = self._require_text(arguments, "title", 200)
            body = self._require_text(arguments, "body", 4000)
            source = self._optional_text(arguments, "source", 120, "poke")
            return make_text_result(json.dumps(self.hermes.send_inbox(title=title, body=body, source=source), ensure_ascii=False, indent=2))
        if name == "create_pending_task":
            title = self._require_text(arguments, "title", 200)
            details = self._optional_text(arguments, "details", 4000, "")
            source = self._optional_text(arguments, "source", 120, "poke")
            return make_text_result(json.dumps(self.tasks.create_task(title=title, details=details, source=source), ensure_ascii=False, indent=2))
        if name == "get_task_status":
            task_id = self._require_text(arguments, "task_id", 120)
            task = self.tasks.get_task(task_id)
            if not task:
                raise RuntimeError(f"Task not found: {task_id}")
            return make_text_result(json.dumps(task, ensure_ascii=False, indent=2))
        if name == "write_temp_log":
            filename = self._safe_filename(self._require_text(arguments, "filename", 120))
            message = self._require_text(arguments, "message", 8000)
            log_path = self.config.temp_dir / filename
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(message + "\n")
            return make_text_result(json.dumps({"ok": True, "path": str(log_path)}, ensure_ascii=False, indent=2))
        if name == "notify_poke":
            title = self._require_text(arguments, "title", 200)
            body = self._require_text(arguments, "body", 4000)
            level = self._optional_text(arguments, "level", 50, "info")
            return make_text_result(json.dumps(self.poke.notify(title=title, body=body, level=level), ensure_ascii=False, indent=2))
        raise RuntimeError(f"Unhandled tool: {name}")

    def handle_webhook(self, kind: str, body_bytes: bytes, headers: dict) -> tuple[int, dict]:
        secret = self.config.linear_webhook_secret if kind == "linear" else self.config.tool_webhook_secret
        self._verify_webhook(secret, body_bytes, headers)
        payload = json.loads(body_bytes.decode("utf-8"))
        source = f"{kind}_webhook"
        title = payload.get("title") or f"{kind} webhook event"
        body = json.dumps(payload, ensure_ascii=False)
        task = self.tasks.create_task(title=title, details=body, source=source)
        self.hermes.send_inbox(title=title, body=body, source=source)
        should_notify = payload.get("notify_poke", kind == "linear")
        notify_result = None
        if should_notify and self.config.poke_notify_url:
            notify_result = self.poke.notify(
                title=f"{kind} webhook received",
                body=f"task_id={task['task_id']}",
                level="info",
            )
        return 202, {
            "ok": True,
            "accepted": True,
            "kind": kind,
            "task_id": task["task_id"],
            "notify_result": notify_result,
        }

    def _verify_webhook(self, secret: str, body_bytes: bytes, headers: dict) -> None:
        if not secret:
            raise RuntimeError("Webhook secret is not configured")
        provided = headers.get("X-Bridge-Secret", "")
        if provided:
            if not hmac.compare_digest(provided, secret):
                raise RuntimeError("Webhook secret rejected")
            return
        signature = headers.get("X-Bridge-Signature", "")
        if not signature:
            raise RuntimeError("Webhook signature missing")
        expected = hashlib.sha256((secret + body_bytes.decode("utf-8")).encode("utf-8")).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise RuntimeError("Webhook signature rejected")

    def _require_text(self, arguments: dict, key: str, max_length: int) -> str:
        value = str(arguments.get(key, "")).strip()
        if not value:
            raise RuntimeError(f"{key} is required")
        if len(value) > max_length:
            raise RuntimeError(f"{key} exceeds max length {max_length}")
        return value

    def _optional_text(self, arguments: dict, key: str, max_length: int, default: str) -> str:
        value = str(arguments.get(key, default)).strip()
        if len(value) > max_length:
            raise RuntimeError(f"{key} exceeds max length {max_length}")
        return value or default

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name
        if name in {"", ".", ".."}:
            raise RuntimeError("Invalid filename")
        return name
