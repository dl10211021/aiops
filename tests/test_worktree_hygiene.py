import unittest

from scripts.worktree_audit import classify_path, commit_blockers, parse_porcelain_line


class TestWorktreeHygiene(unittest.TestCase):
    def test_classifies_sensitive_runtime_state(self):
        item = classify_path("D", ".fernet.key")

        self.assertEqual(item["category"], "sensitive_runtime_state")
        self.assertTrue(item["requires_human_review"])
        self.assertIn("do not commit", item["recommendation"].lower())

    def test_classifies_tracked_node_modules_as_dependency_artifact(self):
        item = classify_path("D", "frontend/node_modules/react/package.json")

        self.assertEqual(item["category"], "dependency_artifact")
        self.assertTrue(item["requires_human_review"])
        self.assertIn("git rm --cached", item["recommendation"])

    def test_classifies_logs_as_discardable_runtime_output(self):
        item = classify_path("D", "backend.uvicorn.err.log")

        self.assertEqual(item["category"], "runtime_output")
        self.assertFalse(item["requires_human_review"])

    def test_classifies_source_code_as_product_change(self):
        item = classify_path("M", "core/agent.py")

        self.assertEqual(item["category"], "product_change")
        self.assertTrue(item["requires_human_review"])

    def test_parses_staged_deletion(self):
        entry = parse_porcelain_line("D  .fernet.key")

        self.assertEqual(entry["path"], ".fernet.key")
        self.assertEqual(entry["index_status"], "D")
        self.assertEqual(entry["worktree_status"], " ")
        self.assertEqual(entry["stage"], "staged")

    def test_parses_unstaged_deletion(self):
        entry = parse_porcelain_line(" D static_react/assets/index-old.js")

        self.assertEqual(entry["path"], "static_react/assets/index-old.js")
        self.assertEqual(entry["index_status"], " ")
        self.assertEqual(entry["worktree_status"], "D")
        self.assertEqual(entry["stage"], "unstaged")

    def test_parses_untracked_file(self):
        entry = parse_porcelain_line("?? static_react/assets/index-new.js")

        self.assertEqual(entry["path"], "static_react/assets/index-new.js")
        self.assertEqual(entry["index_status"], "?")
        self.assertEqual(entry["worktree_status"], "?")
        self.assertEqual(entry["stage"], "untracked")

    def test_classification_includes_git_stage(self):
        item = classify_path(" D", "static_react/assets/index-old.js")

        self.assertEqual(item["category"], "frontend_build_artifact")
        self.assertEqual(item["index_status"], " ")
        self.assertEqual(item["worktree_status"], "D")
        self.assertEqual(item["stage"], "unstaged")

    def test_classifies_typescript_build_cache_as_frontend_artifact(self):
        item = classify_path("M", "frontend/tsconfig.tsbuildinfo")

        self.assertEqual(item["category"], "frontend_build_artifact")
        self.assertFalse(item["requires_human_review"])

    def test_classifies_protocol_verification_runs_as_runtime_state(self):
        item = classify_path("??", "protocol_verification_runs.json")

        self.assertEqual(item["category"], "runtime_state")
        self.assertTrue(item["requires_human_review"])

    def test_classifies_local_agents_directory_as_temporary_artifact(self):
        item = classify_path("??", ".agents/skills/example/SKILL.md")

        self.assertEqual(item["category"], "temporary_artifact")
        self.assertFalse(item["requires_human_review"])

    def test_classifies_hermes_source_as_external_source(self):
        item = classify_path("M ", ".research/hermes-agent/AGENTS.md")

        self.assertEqual(item["category"], "external_source")
        self.assertTrue(item["requires_human_review"])
        self.assertIn("read-only", item["recommendation"])

    def test_classifies_root_manual_chat_tests_as_temporary_artifact(self):
        item = classify_path("??", "test_chat.py")

        self.assertEqual(item["category"], "temporary_artifact")
        self.assertFalse(item["requires_human_review"])

    def test_commit_gate_blocks_staged_sensitive_and_added_dependency_artifacts(self):
        items = [
            classify_path("D ", ".fernet.key"),
            classify_path("A ", "frontend/node_modules/react/package.json"),
            classify_path("M ", "core/agent.py"),
        ]

        blockers = commit_blockers(items)

        self.assertEqual([item["path"] for item in blockers], [".fernet.key", "frontend/node_modules/react/package.json"])

    def test_commit_gate_allows_dependency_artifact_deletions(self):
        blockers = commit_blockers([classify_path("D ", "frontend/node_modules/react/package.json")])

        self.assertEqual(blockers, [])

    def test_commit_gate_allows_runtime_output_deletions(self):
        blockers = commit_blockers([classify_path("D ", "backend.log")])

        self.assertEqual(blockers, [])

    def test_commit_gate_allows_source_changes(self):
        blockers = commit_blockers([classify_path("M ", "core/agent.py")])

        self.assertEqual(blockers, [])

    def test_commit_gate_blocks_external_source_changes(self):
        blockers = commit_blockers([classify_path("M ", ".research/hermes-agent/AGENTS.md")])

        self.assertEqual([item["path"] for item in blockers], [".research/hermes-agent/AGENTS.md"])
        self.assertIn("Hermes", blockers[0]["block_reason"])

    def test_commit_gate_blocks_frontend_cache_even_when_built_assets_allowed(self):
        blockers = commit_blockers(
            [
                classify_path("A ", "static_react/assets/index-new.js"),
                classify_path("M ", "frontend/tsconfig.tsbuildinfo"),
            ],
            allow_built_assets=True,
        )

        self.assertEqual([item["path"] for item in blockers], ["frontend/tsconfig.tsbuildinfo"])

    def test_commit_gate_blocks_built_assets_by_default(self):
        blockers = commit_blockers([classify_path("A ", "static_react/assets/index-new.js")])

        self.assertEqual([item["path"] for item in blockers], ["static_react/assets/index-new.js"])

    def test_commit_gate_allows_sensitive_removal_only_when_explicit(self):
        item = classify_path("D ", ".fernet.key")

        self.assertEqual([blocked["path"] for blocked in commit_blockers([item])], [".fernet.key"])
        self.assertEqual(commit_blockers([item], allow_sensitive_removal=True), [])

    def test_commit_gate_allows_runtime_state_removal_only_when_explicit(self):
        item = classify_path("D ", "memory/test_1m_tokens.md")

        self.assertEqual([blocked["path"] for blocked in commit_blockers([item])], ["memory/test_1m_tokens.md"])
        self.assertEqual(commit_blockers([item], allow_runtime_removal=True), [])


if __name__ == "__main__":
    unittest.main()
