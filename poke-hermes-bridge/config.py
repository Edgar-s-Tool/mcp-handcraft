from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TEMP_DIR = Path(tempfile.gettempdir()) / "poke-hermes-bridge"
DEFAULT_TASK_STORE = DEFAULT_TEMP_DIR / "tasks.json"
DEFAULT_INBOX_FILE = DEFAULT_TEMP_DIR / "hermes-inbox.jsonl"


@dataclass(frozen=True)
class BridgeConfig:
    host: str
    port: int
    poke_api_key: str
    poke_notify_url: str
    hermes_mode: str
    hermes_status_url: str
    hermes_inbox_url: str
    hermes_inbox_file: Path
    task_store_path: Path
    temp_dir: Path
    linear_webhook_secret: str
    tool_webhook_secret: str
    runtime_warnings: tuple[str, ...] = field(default_factory=tuple)


def _ensure_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _resolve_runtime_dir(env_name: str, default_path: Path, warnings: list[str]) -> Path:
    requested = Path(os.getenv(env_name, str(default_path))).resolve()
    if _ensure_writable_dir(requested):
        return requested

    fallback = DEFAULT_TEMP_DIR.resolve()
    if not _ensure_writable_dir(fallback):
        raise RuntimeError(f"Runtime temp dir is not writable: {fallback}")

    warnings.append(f"{env_name} fallback to {fallback} because requested path is not writable: {requested}")
    return fallback


def _resolve_runtime_file(env_name: str, default_path: Path, fallback_dir: Path, warnings: list[str]) -> Path:
    requested = Path(os.getenv(env_name, str(default_path))).resolve()
    if _ensure_writable_dir(requested.parent):
        return requested

    fallback = (fallback_dir / requested.name).resolve()
    if not _ensure_writable_dir(fallback.parent):
        raise RuntimeError(f"Runtime file parent is not writable: {fallback.parent}")

    warnings.append(f"{env_name} fallback to {fallback} because requested parent is not writable: {requested.parent}")
    return fallback


def load_config() -> BridgeConfig:
    warnings: list[str] = []
    temp_dir = _resolve_runtime_dir("POKE_BRIDGE_TEMP_DIR", DEFAULT_TEMP_DIR, warnings)
    task_store_path = _resolve_runtime_file("POKE_BRIDGE_TASK_STORE", DEFAULT_TASK_STORE, temp_dir, warnings)
    hermes_inbox_file = _resolve_runtime_file("HERMES_INBOX_FILE", DEFAULT_INBOX_FILE, temp_dir, warnings)

    return BridgeConfig(
        host=os.getenv("POKE_BRIDGE_HOST", "127.0.0.1"),
        port=int(os.getenv("POKE_BRIDGE_PORT", "8788")),
        poke_api_key=os.getenv("POKE_API_KEY", "").strip(),
        poke_notify_url=os.getenv("POKE_NOTIFY_URL", "").strip(),
        hermes_mode=os.getenv("HERMES_MODE", "http").strip().lower(),
        hermes_status_url=os.getenv("HERMES_STATUS_URL", "http://127.0.0.1:18789/health").strip(),
        hermes_inbox_url=os.getenv("HERMES_INBOX_URL", "http://127.0.0.1:18789/inbox").strip(),
        hermes_inbox_file=hermes_inbox_file,
        task_store_path=task_store_path,
        temp_dir=temp_dir,
        linear_webhook_secret=os.getenv("LINEAR_WEBHOOK_SECRET", "").strip(),
        tool_webhook_secret=os.getenv("TOOL_WEBHOOK_SECRET", "").strip(),
        runtime_warnings=tuple(warnings),
    )


def validate_runtime_secrets(config: BridgeConfig) -> None:
    if not config.poke_api_key:
        raise RuntimeError("POKE_API_KEY is required")

