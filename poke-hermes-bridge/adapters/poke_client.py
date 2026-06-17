from __future__ import annotations

import json
import urllib.request

from config import BridgeConfig


class PokeClient:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config

    def notify(self, title: str, body: str, level: str = "info") -> dict:
        if not self.config.poke_notify_url:
            raise RuntimeError("POKE_NOTIFY_URL is required for notify_poke")

        payload = {"title": title, "body": body, "level": level}
        request = urllib.request.Request(
            self.config.poke_notify_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config.poke_api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8").strip()
            return {"ok": True, "status_code": response.status, "data": json.loads(raw) if raw else {}}
