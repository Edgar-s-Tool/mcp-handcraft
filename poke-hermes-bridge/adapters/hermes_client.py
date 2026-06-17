from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone

from config import BridgeConfig


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HermesClient:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.config.hermes_inbox_file.parent.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict:
        if self.config.hermes_mode == "file":
            return {
                "ok": True,
                "mode": "file",
                "inbox_file": str(self.config.hermes_inbox_file),
                "exists": self.config.hermes_inbox_file.exists(),
            }

        request = urllib.request.Request(
            self.config.hermes_status_url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8").strip()
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {"raw": body}
            return {"ok": True, "mode": "http", "status_code": response.status, "data": data}

    def send_inbox(self, title: str, body: str, source: str = "poke") -> dict:
        payload = {
            "title": title,
            "body": body,
            "source": source,
            "created_at": _utc_now(),
        }

        if self.config.hermes_mode == "file":
            with self.config.hermes_inbox_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            return {"ok": True, "mode": "file", "inbox_file": str(self.config.hermes_inbox_file)}

        request = urllib.request.Request(
            self.config.hermes_inbox_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8").strip()
            return {
                "ok": True,
                "mode": "http",
                "status_code": response.status,
                "data": json.loads(raw) if raw else {},
            }
