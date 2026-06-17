from __future__ import annotations

ALLOWED_TOOL_NAMES = {
    "hermes_status",
    "send_to_hermes_inbox",
    "create_pending_task",
    "get_task_status",
    "write_temp_log",
    "notify_poke",
}

TOOLS = [
    {"name": "hermes_status", "description": "Read Hermes health/status through the local bridge.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "send_to_hermes_inbox", "description": "Send a bounded message into Hermes inbox.", "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}, "source": {"type": "string"}}, "required": ["title", "body"]}},
    {"name": "create_pending_task", "description": "Create a local pending task tracked by the bridge.", "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "details": {"type": "string"}, "source": {"type": "string"}}, "required": ["title"]}},
    {"name": "get_task_status", "description": "Read a pending task status by task id.", "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "write_temp_log", "description": "Write a temporary bridge log entry inside the bridge temp directory only.", "inputSchema": {"type": "object", "properties": {"filename": {"type": "string"}, "message": {"type": "string"}}, "required": ["filename", "message"]}},
    {"name": "notify_poke", "description": "Send a bounded notification to Poke through the configured notification endpoint.", "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}, "level": {"type": "string"}}, "required": ["title", "body"]}},
]


def is_allowed_tool(name: str) -> bool:
    return name in ALLOWED_TOOL_NAMES
