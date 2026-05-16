import unittest

from core.agent_session_context import build_agent_session_context


class AgentSessionContextTests(unittest.TestCase):
    def test_builds_default_asset_tool_context(self):
        seen = []

        def resolver(active_skills):
            seen.append(active_skills)
            return ["D:/skills/check-disk"]

        session_context = build_agent_session_context(
            "sid-1",
            {
                "host": "10.0.0.5",
                "port": 22,
                "username": "ops",
                "password": "secret",
                "active_skills": ["check-disk"],
                "allow_modifications": True,
                "target_scope": "tag",
                "scope_value": "prod",
            },
            skill_path_resolver=resolver,
        )

        self.assertEqual(seen, [["check-disk"]])
        self.assertEqual(session_context.agent_profile, "default")
        self.assertEqual(session_context.asset_type, "ssh")
        self.assertEqual(session_context.protocol, "ssh")
        self.assertFalse(session_context.local_skill_scripts_allowed)
        self.assertFalse(session_context.has_local_skill_scripts)

        self.assertEqual(
            session_context.tool_context(),
            {
                "session_id": "sid-1",
                "os_type": "linux",
                "allow_modifications": True,
                "session_mode": "readwrite",
                "active_skills": ["check-disk"],
                "active_skill_paths": [],
                "asset_type": "ssh",
                "protocol": "ssh",
                "host": "10.0.0.5",
                "port": 22,
                "username": "ops",
                "password": "secret",
                "extra_args": {},
                "target_scope": "tag",
                "scope_value": "prod",
                "memory_scope_ids": ["sid-1"],
            },
        )

    def test_virtual_context_exposes_skill_paths_and_background_metadata(self):
        session_context = build_agent_session_context(
            "sid-2",
            {
                "asset_type": "virtual",
                "protocol": "virtual",
                "host": "workspace",
                "active_skills": ["skill-creator"],
                "allow_modifications": True,
                "extra_args": {"login_protocol": "virtual"},
            },
            skill_path_resolver=lambda active_skills: [
                f"D:/skills/{name}" for name in active_skills
            ],
            allow_modifications=False,
        )

        self.assertTrue(session_context.local_skill_scripts_allowed)
        self.assertTrue(session_context.has_local_skill_scripts)
        self.assertEqual(
            session_context.tool_context(
                execution_mode="headless",
                trigger_source="background_agent",
            ),
            {
                "session_id": "sid-2",
                "os_type": "linux",
                "allow_modifications": False,
                "session_mode": "readonly",
                "active_skills": ["skill-creator"],
                "active_skill_paths": ["D:/skills/skill-creator"],
                "asset_type": "virtual",
                "protocol": "virtual",
                "host": "workspace",
                "port": "",
                "username": "",
                "password": None,
                "extra_args": {"login_protocol": "virtual"},
                "target_scope": "asset",
                "scope_value": None,
                "memory_scope_ids": ["sid-2"],
                "execution_mode": "headless",
                "trigger_source": "background_agent",
            },
        )

    def test_memory_scope_ids_ignore_asset_identity_and_are_session_only(self):
        session_context = build_agent_session_context(
            "SID-Oracle-A",
            {
                "asset_type": "oracle",
                "protocol": "oracle",
                "host": "172.17.8.150",
                "port": 1521,
                "username": "system",
                "extra_args": {
                    "service_name": "ORCL",
                    "asset_key": "oracle:172.17.8.150:1521",
                },
            },
            skill_path_resolver=lambda active_skills: [],
        )

        self.assertEqual(session_context.memory_scope_ids(), ["sid-oracle-a"])
        self.assertEqual(session_context.tool_context()["memory_scope_ids"], ["sid-oracle-a"])
        self.assertFalse(
            any(scope.startswith("asset") for scope in session_context.memory_scope_ids())
        )


if __name__ == "__main__":
    unittest.main()
