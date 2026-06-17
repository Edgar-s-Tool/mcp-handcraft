import json
import unittest
import urllib.error
from io import BytesIO
from unittest import mock

import stdio_proxy


class StdioProxyPreflightTests(unittest.TestCase):
    def test_missing_token_aborts(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(stdio_proxy.PreflightError):
                stdio_proxy.run_preflight()

    def test_unreachable_endpoint_aborts(self):
        with mock.patch.dict("os.environ", {"MCP_API_TOKEN": "x"}, clear=True):
            with mock.patch("stdio_proxy.urllib.request.urlopen") as urlopen:
                urlopen.side_effect = urllib.error.URLError("connection refused")
                with self.assertRaises(stdio_proxy.PreflightError):
                    stdio_proxy.run_preflight()

    def test_preflight_timeout_value_used(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["timeout"] = timeout
            body = json.dumps({"jsonrpc": "2.0", "id": "stdio-preflight", "result": {}}).encode()
            class FakeResp:
                status = 200
                def __enter__(self_inner): return self_inner
                def __exit__(self_inner, *args): pass
                def read(self_inner): return body
            return FakeResp()

        with mock.patch.dict("os.environ", {"MCP_API_TOKEN": "x"}, clear=True):
            with mock.patch("stdio_proxy.urllib.request.urlopen", side_effect=fake_urlopen):
                stdio_proxy.run_preflight()
        self.assertEqual(stdio_proxy.PREFLIGHT_TIMEOUT_SECONDS, captured["timeout"])


if __name__ == "__main__":
    unittest.main()

