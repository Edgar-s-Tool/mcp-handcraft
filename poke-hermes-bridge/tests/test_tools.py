import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import BridgeConfig
from service import BridgeService


class ToolTests(unittest.TestCase):
    def make_config(self, temp_dir: str) -> BridgeConfig:
        return BridgeConfig(
            host="127.0.0.1",
            port=8788,
            poke_api_key="test-key",
            poke_notify_url="https://poke.example.test/notify",
            hermes_mode="file",
            hermes_status_url="http://127.0.0.1:18789/health",
            hermes_inbox_url="http://127.0.0.1:18789/inbox",
            hermes_inbox_file=Path(temp_dir) / "inbox.jsonl",
            task_store_path=Path(temp_dir) / "tasks.json",
            temp_dir=Path(temp_dir) / "tmp",
            linear_webhook_secret="linear-secret",
            tool_webhook_secret="tool-secret",
        )

    def test_tools_list_only_whitelist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = BridgeService(self.make_config(temp_dir))
            status, response = service.handle_mcp({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertEqual(status, 200)
            self.assertEqual(len(response["result"]["tools"]), 6)

    def test_create_and_read_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = BridgeService(self.make_config(temp_dir))
            _, created = service.handle_mcp({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "create_pending_task", "arguments": {"title": "test task"}}})
            task_payload = json.loads(created["result"]["content"][0]["text"])
            task_id = task_payload["task_id"]
            _, fetched = service.handle_mcp({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_task_status", "arguments": {"task_id": task_id}}})
            fetched_payload = json.loads(fetched["result"]["content"][0]["text"])
            self.assertEqual(fetched_payload["task_id"], task_id)

    def test_write_temp_log_stays_in_temp_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = BridgeService(self.make_config(temp_dir))
            _, result = service.handle_mcp({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "write_temp_log", "arguments": {"filename": "..\\escape.log", "message": "hello"}}})
            payload = json.loads(result["result"]["content"][0]["text"])
            self.assertTrue(payload["path"].endswith("escape.log"))
            self.assertTrue(Path(payload["path"]).exists())

    def test_rejects_non_whitelisted_tool(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = BridgeService(self.make_config(temp_dir))
            status, response = service.handle_mcp({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "run_powershell", "arguments": {}}})
            self.assertEqual(status, 403)
            self.assertIn("Tool not allowed", response["error"]["message"])

    def test_notify_poke_uses_fixed_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = BridgeService(self.make_config(temp_dir))
            captured = {}

            class FakeResponse:
                status = 200
                def read(self):
                    return b'{"ok": true}'
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc, tb):
                    return False

            def fake_urlopen(request, timeout=10):
                captured["url"] = request.full_url
                captured["auth"] = request.get_header("Authorization")
                return FakeResponse()

            with patch("adapters.poke_client.urllib.request.urlopen", side_effect=fake_urlopen):
                status, _ = service.handle_mcp({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "notify_poke", "arguments": {"title": "hello", "body": "world"}}})
            self.assertEqual(status, 200)
            self.assertEqual(captured["url"], "https://poke.example.test/notify")
            self.assertEqual(captured["auth"], "Bearer test-key")


if __name__ == "__main__":
    unittest.main()
