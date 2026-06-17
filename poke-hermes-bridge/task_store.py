from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, payload: dict) -> None:
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_task(self, title: str, details: str = "", source: str = "poke") -> dict:
        with self._lock:
            payload = self._read()
            task_id = str(uuid.uuid4())
            task = {
                "task_id": task_id,
                "title": title,
                "details": details,
                "source": source,
                "status": "pending",
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            payload[task_id] = task
            self._write(payload)
            return task

    def get_task(self, task_id: str) -> dict | None:
        with self._lock:
            return self._read().get(task_id)
