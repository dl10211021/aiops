import asyncio
import unittest
from unittest.mock import patch

from core.session_commands import (
    SessionCommandError,
    build_session_commands_payload_for_session,
    build_session_commands_response,
    clear_custom_slash_command_cache,
    list_custom_slash_command_records,
    list_custom_slash_commands,
    remove_custom_slash_command_record,
    remove_custom_slash_command,
    save_custom_slash_command_record,
    save_custom_slash_command,
)
from core.tool_registry import tool_registry


class FakeCommandStore:
    def __init__(self):
        self.commands = [{"id": "cmd-1", "label": "/cmd"}]
        self.saved = []
        self.deleted = []

    def list_slash_commands(self):
        return self.commands

    def save_slash_command(self, payload):
        self.saved.append(payload)
        return payload

    def delete_slash_command(self, command_id):
        self.deleted.append(command_id)
        return command_id == "cmd-1"


class TestSessionCommands(unittest.TestCase):
    def setUp(self):
        clear_custom_slash_command_cache()

    def tearDown(self):
        clear_custom_slash_command_cache()

    def test_build_session_commands_response_uses_tool_payload_context(self):
        payload = build_session_commands_response(
            {
                "active_tools": ["linux_execute_command"],
                "context": {
                    "target_scope": "asset",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "host": "10.0.0.10",
                    "port": 22,
                },
            },
            [],
        )

        command_ids = {item["id"] for item in payload["commands"]}
        self.assertIn("inspect", command_ids)
        self.assertIn("linux-services", command_ids)
        tools_command = next(item for item in payload["commands"] if item["id"] == "tools")
        self.assertIn("Linux/Unix 命令", tools_command["prompt"])
        self.assertNotIn("linux_execute_command", tools_command["prompt"])
        self.assertEqual(payload["context"]["protocol"], "ssh")
        self.assertEqual(payload["custom_commands"], [])

    def test_build_session_commands_response_keeps_builtin_overrides(self):
        payload = build_session_commands_response(
            {
                "active_tools": ["linux_execute_command"],
                "context": {
                    "target_scope": "asset",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "host": "10.0.0.10",
                    "port": 22,
                },
            },
            [
                {
                    "id": "inspect",
                    "label": "/inspect 自定义",
                    "prompt_template": "检查 {host}",
                    "enabled": True,
                }
            ],
        )

        inspect = next(item for item in payload["commands"] if item["id"] == "inspect")
        self.assertEqual(inspect["label"], "/inspect 自定义")
        self.assertEqual(inspect["prompt"], "检查 10.0.0.10")
        self.assertTrue(inspect["is_override"])

    def test_build_session_commands_payload_for_session_loads_tools_and_custom_commands(self):
        sessions = {
            "sid-1": {
                "info": {
                    "host": "10.0.0.10",
                    "port": 22,
                    "asset_type": "linux",
                    "protocol": "ssh",
                }
            }
        }
        store = FakeCommandStore()

        payload = asyncio.run(
            build_session_commands_payload_for_session(
                sessions,
                tool_registry,
                "sid-1",
                memory_db=store,
            )
        )

        command_ids = {item["id"] for item in payload["commands"]}
        self.assertIn("inspect", command_ids)
        self.assertEqual(payload["custom_commands"], store.commands)
        self.assertEqual(payload["context"]["protocol"], "ssh")

    def test_custom_slash_command_store_helpers_delegate_to_memory_db(self):
        store = FakeCommandStore()

        self.assertEqual(list_custom_slash_commands(store), store.commands)
        created = save_custom_slash_command(store, {"label": "/new"})
        updated = save_custom_slash_command(store, {"label": "/newer"}, "cmd-1")
        remove_custom_slash_command(store, "cmd-1")

        self.assertEqual(created, {"label": "/new"})
        self.assertEqual(updated, {"label": "/newer", "id": "cmd-1"})
        self.assertEqual(
            store.saved,
            [{"label": "/new"}, {"label": "/newer", "id": "cmd-1"}],
        )
        self.assertEqual(store.deleted, ["cmd-1"])

    def test_custom_slash_command_record_helpers_delegate_to_memory_db_async(self):
        store = FakeCommandStore()

        async def exercise():
            commands = await list_custom_slash_command_records(memory_db=store)
            created = await save_custom_slash_command_record({"label": "/new"}, memory_db=store)
            updated = await save_custom_slash_command_record(
                {"label": "/newer"},
                "cmd-1",
                memory_db=store,
            )
            await remove_custom_slash_command_record("cmd-1", memory_db=store)
            return commands, created, updated

        commands, created, updated = asyncio.run(exercise())

        self.assertEqual(commands, [{"id": "cmd-1", "label": "/cmd"}])
        self.assertEqual(created, {"label": "/new"})
        self.assertEqual(updated, {"label": "/newer", "id": "cmd-1"})
        self.assertEqual(store.deleted, ["cmd-1"])

    def test_custom_slash_command_cache_uses_global_store_clone(self):
        store = FakeCommandStore()

        async def exercise():
            first = await list_custom_slash_command_records()
            first[0]["label"] = "/mutated"
            store.commands.append({"id": "cmd-2", "label": "/new"})
            second = await list_custom_slash_command_records()
            return first, second

        with patch("core.memory.memory_db", store):
            first, second = asyncio.run(exercise())

        self.assertEqual(first[0]["label"], "/mutated")
        self.assertEqual(second, [{"id": "cmd-1", "label": "/cmd"}])

    def test_remove_custom_slash_command_raises_typed_404_when_missing(self):
        store = FakeCommandStore()

        with self.assertRaises(SessionCommandError) as ctx:
            remove_custom_slash_command(store, "missing")

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "快捷命令不存在")
