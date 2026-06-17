from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import load_config, validate_runtime_secrets
from service import BridgeService

CONFIG = load_config()
SERVICE = BridgeService(CONFIG)


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "poke-hermes-bridge/0.1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(200, SERVICE.health_payload())
            return
        self._write_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b""
        try:
            if self.path == "/mcp":
                payload = json.loads(body.decode("utf-8"))
                status, response = SERVICE.handle_mcp(payload)
                self._write_json(status, response)
                return
            if self.path == "/webhook/linear":
                status, response = SERVICE.handle_webhook("linear", body, dict(self.headers))
                self._write_json(status, response)
                return
            if self.path == "/webhook/tool":
                status, response = SERVICE.handle_webhook("tool", body, dict(self.headers))
                self._write_json(status, response)
                return
            self._write_json(404, {"ok": False, "error": "Not found"})
        except Exception as exc:
            self._write_json(500, {"ok": False, "error": str(exc)})


def main() -> None:
    validate_runtime_secrets(CONFIG)
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), BridgeHandler)
    print(f"poke-hermes-bridge listening on http://{CONFIG.host}:{CONFIG.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
