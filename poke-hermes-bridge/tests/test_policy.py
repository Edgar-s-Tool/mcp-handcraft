import unittest

from policy import ALLOWED_TOOL_NAMES, TOOLS, is_allowed_tool


class PolicyTests(unittest.TestCase):
    def test_only_expected_tools_are_exposed(self) -> None:
        self.assertEqual(
            ALLOWED_TOOL_NAMES,
            {
                "hermes_status",
                "send_to_hermes_inbox",
                "create_pending_task",
                "get_task_status",
                "write_temp_log",
                "notify_poke",
            },
        )
        self.assertEqual({tool["name"] for tool in TOOLS}, ALLOWED_TOOL_NAMES)

    def test_rejects_non_whitelisted_tool(self) -> None:
        self.assertFalse(is_allowed_tool("run_powershell"))
        self.assertFalse(is_allowed_tool("call_any_url"))


if __name__ == "__main__":
    unittest.main()
