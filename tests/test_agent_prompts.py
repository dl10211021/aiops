import unittest
from unittest.mock import patch

from core.asset_protocols import get_asset_catalog
from core.agent_prompts import (
    build_headless_prompt_manifest,
    build_chat_prompt_manifest,
    render_chat_system_prompt,
    render_headless_system_prompt,
)
from core.agent_session_context import build_agent_session_context


class AgentPromptTests(unittest.TestCase):
    def _session_context(self, protocol: str = "ssh", asset_type: str | None = None):
        resolved_asset_type = asset_type or ("virtual" if protocol == "virtual" else "linux")
        return build_agent_session_context(
            "sid-prompt",
            {
                "asset_type": resolved_asset_type,
                "protocol": protocol,
                "host": "ops.local",
                "port": 22,
                "username": "ops",
                "allow_modifications": False,
                "active_skills": ["diagnose"],
                "extra_args": {"api_token": "secret-token", "region": "cn"},
            },
            skill_path_resolver=lambda active_skills: [
                f"D:/skills/{name}" for name in active_skills
            ],
        )

    def test_chat_prompt_manifest_records_modules_without_prompt_text(self):
        manifest = build_chat_prompt_manifest(
            session_context=self._session_context(),
            has_skill_instructions=True,
            has_asset_profile=True,
            has_rag_context=False,
            has_ltm_context=True,
        )

        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["surface"], "chat")
        self.assertEqual(manifest["asset_type"], "linux")
        self.assertEqual(manifest["protocol"], "ssh")
        self.assertIn("evidence_contract", manifest["modules"])
        self.assertIn("context_precedence", manifest["modules"])
        self.assertTrue(manifest["enabled"]["skill_instructions"])
        self.assertFalse(manifest["enabled"]["rag_context"])
        self.assertNotIn("BASE", str(manifest))
        self.assertNotIn("SKILL-INSTRUCTIONS", str(manifest))

    def test_headless_prompt_manifest_records_delegated_modules_without_prompt_text(self):
        manifest = build_headless_prompt_manifest(
            session_context=self._session_context(protocol="virtual"),
        )

        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["surface"], "headless")
        self.assertEqual(manifest["asset_type"], "virtual")
        self.assertEqual(manifest["protocol"], "virtual")
        self.assertEqual(manifest["mode"], "read_only")
        self.assertIn("delegated_task", manifest["modules"])
        self.assertIn("tool_catalog", manifest["modules"])
        self.assertTrue(manifest["enabled"]["skill_paths"])
        self.assertNotIn("BASE", str(manifest))
        self.assertNotIn("检查 Skills 工程结构", str(manifest))

    @patch("core.agent_prompts.protocol_tool_list")
    @patch("core.agent_prompts.protocol_tool_guidance")
    @patch("core.agent_prompts.format_extra_args_for_prompt")
    def test_chat_prompt_keeps_credentials_tools_skills_and_memory_sections(
        self,
        format_extra_args,
        protocol_guidance,
        protocol_tool_list,
    ):
        format_extra_args.return_value = "- api_token: (已托管，执行时自动注入)"
        protocol_guidance.return_value = "GUIDANCE"
        protocol_tool_list.return_value = "TOOLS"

        prompt = render_chat_system_prompt(
            session_context=self._session_context(),
            base_prompt="BASE",
            skill_instructions="<INSTRUCTIONS>check</INSTRUCTIONS>",
            ltm_context="LTM-CONTEXT",
        )

        self.assertTrue(prompt.startswith("\nBASE\n\n[当前会话上下文]"))
        self.assertIn("会话类型：SSH / Linux-Unix 终端会话", prompt)
        self.assertIn("资产识别：Linux / Unix（类型 linux，分类 操作系统，协议 ssh）", prompt)
        self.assertIn("不要假设所有会话都是 SSH", prompt)
        self.assertIn("一台通过SSH协议纳管的 LINUX 资产", prompt)
        self.assertIn("- api_token: (已托管，执行时自动注入)", prompt)
        self.assertIn("**只读巡检模式**", prompt)
        self.assertIn("[OpsCore 运维 OP 流程]", prompt)
        self.assertIn("先判断本轮 OP 类型", prompt)
        self.assertIn("只读巡检：先绑定当前资产/业务系统", prompt)
        self.assertIn("[工具证据契约]", prompt)
        self.assertIn("没有当前轮次的原生协议工具结果", prompt)
        self.assertIn("[当前已加载专业技能说明 (Skills)]", prompt)
        self.assertIn("<INSTRUCTIONS>check</INSTRUCTIONS>", prompt)
        self.assertIn("LTM-CONTEXT", prompt)
        self.assertIn("[Skill 联网安装流程]", prompt)
        self.assertIn("优先调用 `browser_navigate`", prompt)
        self.assertIn("[联网资料研究与浏览器流程]", prompt)
        self.assertIn("浏览器工具是联网研究主路径", prompt)
        self.assertIn("AIOps 资料、产品文档、故障案例、版本兼容、漏洞/补丁公告", prompt)
        self.assertIn("优先使用中文关键词和中国搜索入口", prompt)
        self.assertIn("至少核对 2 个可信来源", prompt)
        self.assertIn("先用 `browser_navigate` 打开可信搜索入口扩展候选来源", prompt)
        self.assertIn("不要停在“我再试试”这类半句话", prompt)
        self.assertIn("不要在只拿到标题片段时就让用户自己打开链接", prompt)
        self.assertIn("调用 `evolve_skill` 写入 `my_custom_skills/<skill_id>/SKILL.md`", prompt)
        self.assertIn("不要直接执行互联网上下载的脚本", prompt)
        self.assertIn("目标/会话不一致处理", prompt)
        self.assertIn("必须调用 `request_user_interaction`", prompt)
        self.assertIn("[上下文优先级]", prompt)
        self.assertIn("资产画像提示词", prompt)
        self.assertLess(prompt.index("LTM-CONTEXT"), prompt.index("[上下文优先级]"))
        protocol_tool_list.assert_called_once_with("ssh", False, "linux")

    def test_chat_prompt_declares_profile_and_current_evidence_over_ltm(self):
        prompt = render_chat_system_prompt(
            session_context=self._session_context(),
            base_prompt="BASE",
            skill_instructions="SKILL",
            asset_profile_prompt="[资产画像提示词]\n安全状态：UFW active",
            ltm_context="历史记忆：UFW 未启用",
        )

        self.assertIn("长期记忆只是历史经验", prompt)
        self.assertIn("当前原生协议工具结果", prompt)
        self.assertIn("资产画像提示词", prompt)
        self.assertLess(prompt.index("历史记忆：UFW 未启用"), prompt.index("[上下文优先级]"))

    def test_chat_prompt_uses_database_session_context_without_ssh_assumption(self):
        prompt = render_chat_system_prompt(
            session_context=self._session_context(protocol="oracle", asset_type="oracle"),
            base_prompt="BASE",
            skill_instructions="SKILL",
            ltm_context="",
        )

        self.assertIn("会话类型：Oracle 数据库会话", prompt)
        self.assertIn("资产识别：Oracle（类型 oracle，分类 数据库，协议 oracle）", prompt)
        self.assertIn("一台通过ORACLE协议纳管的 ORACLE 资产", prompt)
        self.assertNotIn("目前你正处于一个 SSH 终端会话", prompt)

    def test_chat_prompt_preserves_custom_asset_identity_fields(self):
        context = build_agent_session_context(
            "sid-custom-asset",
            {
                "asset_type": "nebula_graph_cluster",
                "protocol": "nebula_graph",
                "host": "graph.local",
                "port": 9669,
                "username": "graph",
                "allow_modifications": False,
                "active_skills": [],
                "extra_args": {
                    "category": "db",
                    "sub_type": "nebula_graph_cluster",
                    "vendor": "vesoft",
                    "engine": "graph",
                    "token": "secret-token",
                },
            },
            skill_path_resolver=lambda active_skills: [],
        )

        prompt = render_chat_system_prompt(
            session_context=context,
            base_prompt="BASE",
            skill_instructions="",
            ltm_context="",
        )

        self.assertIn("会话类型：Nebula Graph 数据库会话", prompt)
        self.assertIn(
            "资产识别：NebulaGraph集群（类型 nebula_graph_cluster，分类 数据库，协议 nebula_graph）",
            prompt,
        )
        self.assertIn("识别字段：category=db；sub_type=nebula_graph_cluster；vendor=vesoft；engine=graph", prompt)
        self.assertNotIn("secret-token", prompt)

    @patch("core.agent_prompts.protocol_tool_list")
    @patch("core.agent_prompts.protocol_tool_guidance")
    @patch("core.agent_prompts.format_extra_args_for_prompt")
    def test_headless_prompt_uses_task_and_virtual_skill_tool_visibility(
        self,
        format_extra_args,
        protocol_guidance,
        protocol_tool_list,
    ):
        format_extra_args.return_value = "- region: cn"
        protocol_guidance.return_value = "VIRTUAL-GUIDANCE"
        protocol_tool_list.return_value = "VIRTUAL-TOOLS"

        prompt = render_headless_system_prompt(
            session_context=self._session_context(protocol="virtual"),
            base_prompt="BASE",
            task_description="检查 Skills 工程结构",
        )

        self.assertTrue(prompt.startswith("BASE\n\n[当前会话上下文]"))
        self.assertIn("会话类型：虚拟/本地技能研发会话", prompt)
        self.assertIn("一台通过VIRTUAL协议纳管的 VIRTUAL 资产", prompt)
        self.assertIn("[上级指挥官委派的任务]", prompt)
        self.assertIn("[OpsCore 运维 OP 流程]", prompt)
        self.assertIn("[工具证据契约]", prompt)
        self.assertIn("检查 Skills 工程结构", prompt)
        self.assertIn("VIRTUAL-TOOLS", prompt)
        self.assertNotIn("[当前已加载专业技能说明 (Skills)]", prompt)
        protocol_tool_list.assert_called_once_with("virtual", True, "virtual")

    def test_chat_prompt_supports_all_catalog_assets_without_ssh_fallback(self):
        catalog = get_asset_catalog()
        self.assertGreater(len(catalog), 20)

        for item in catalog:
            asset_type = item["id"]
            protocol = item.get("protocol") or asset_type
            with self.subTest(asset_type=asset_type, protocol=protocol):
                context = build_agent_session_context(
                    f"sid-{asset_type}",
                    {
                        "asset_type": asset_type,
                        "protocol": protocol,
                        "host": f"{asset_type}.example.local",
                        "port": item.get("default_port") or 0,
                        "username": "ops",
                        "allow_modifications": False,
                        "active_skills": [],
                        "extra_args": {
                            "category": item.get("category"),
                            "sub_type": asset_type,
                            "api_token": "secret-token",
                        },
                    },
                    skill_path_resolver=lambda active_skills: [],
                )

                prompt = render_chat_system_prompt(
                    session_context=context,
                    base_prompt="BASE",
                    skill_instructions="",
                    ltm_context="",
                )

                self.assertIn("[当前会话上下文]", prompt)
                self.assertIn(f"类型 {asset_type}", prompt)
                self.assertIn(f"协议 {protocol}", prompt)
                self.assertIn("不要假设所有会话都是 SSH", prompt)
                self.assertNotIn("目前你正处于一个 SSH 终端会话", prompt)
                self.assertNotIn("secret-token", prompt)


if __name__ == "__main__":
    unittest.main()
