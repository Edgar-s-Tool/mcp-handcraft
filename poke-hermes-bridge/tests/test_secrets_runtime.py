import os
import tempfile
import unittest
from pathlib import Path

from config import load_config, validate_runtime_secrets


class SecretsRuntimeTests(unittest.TestCase):
    def test_missing_poke_api_key_fails_closed(self) -> None:
        original = os.environ.pop("POKE_API_KEY", None)
        try:
            config = load_config()
            with self.assertRaisesRegex(RuntimeError, "POKE_API_KEY is required"):
                validate_runtime_secrets(config)
        finally:
            if original is not None:
                os.environ["POKE_API_KEY"] = original

    def test_task_store_uses_env_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_store = Path(temp_dir) / "store.json"
            original_key = os.environ.get("POKE_API_KEY")
            original_store = os.environ.get("POKE_BRIDGE_TASK_STORE")
            os.environ["POKE_API_KEY"] = "test-key"
            os.environ["POKE_BRIDGE_TASK_STORE"] = str(task_store)
            try:
                config = load_config()
                self.assertEqual(config.task_store_path, task_store.resolve())
            finally:
                if original_key is None:
                    os.environ.pop("POKE_API_KEY", None)
                else:
                    os.environ["POKE_API_KEY"] = original_key
                if original_store is None:
                    os.environ.pop("POKE_BRIDGE_TASK_STORE", None)
                else:
                    os.environ["POKE_BRIDGE_TASK_STORE"] = original_store


if __name__ == "__main__":
    unittest.main()
