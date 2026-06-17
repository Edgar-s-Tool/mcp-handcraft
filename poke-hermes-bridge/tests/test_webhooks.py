import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import BridgeConfig
from service import BridgeService


class WebhookTests(unittest.TestCase):
    def make_service(self, temp_dir: str) -> BridgeService:
        config = BridgeConfig(
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
        return BridgeService(config)

    def test_linear_webhook_accepts_valid_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            body = json.dumps({"title": "linear event", "notify_poke": False}).encode("utf-8")
            status, response = service.handle_webhook("linear", body, {"X-Bridge-Secret": "linear-secret"})
            self.assertEqual(status, 202)
            self.assertTrue(response["accepted"])

    def test_tool_webhook_rejects_bad_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            body = json.dumps({"title": "tool event"}).encode("utf-8")
            with self.assertRaisesRegex(RuntimeError, "Webhook secret rejected"):
                service.handle_webhook("tool", body, {"X-Bridge-Secret": "wrong"})

    def test_linear_webhook_can_notify_poke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)

            class FakeResponse:
                status = 200
                def read(self):
                    return b'{"ok": true}'
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc, tb):
                    return False

            with patch("adapters.poke_client.urllib.request.urlopen", return_value=FakeResponse()):
                status, response = service.handle_webhook("linear", json.dumps({"title": "linear event", "notify_poke": True}).encode("utf-8"), {"X-Bridge-Secret": "linear-secret"})
            self.assertEqual(status, 202)
            self.assertIsNotNone(response["notify_result"])


if __name__ == "__main__":
    unittest.main()
