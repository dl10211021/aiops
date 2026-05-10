import asyncio
import unittest
from unittest.mock import patch

from api import config_routes, routes
from api.schemas import (
    AgentRuntimeConfigRequest,
    EmbeddingConfigRequest,
    ProviderConfig,
    SafetyPolicyTestRequest,
    SafetyPolicyUpdateRequest,
    SessionRetentionConfigRequest,
)


class TestConfigRoutes(unittest.TestCase):
    def test_config_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/models", paths)
        self.assertIn("/config/llm", paths)
        self.assertIn("/config/agent-runtime", paths)
        self.assertIn("/config/session-retention", paths)
        self.assertIn("/config/session-retention/run", paths)
        self.assertIn("/config/embedding", paths)
        self.assertIn("/config/providers", paths)
        self.assertIn("/config/safety-policy", paths)
        self.assertIn("/config/safety-policy/test", paths)

    def test_get_models_preserves_response_shape(self):
        models = [{"id": "openai|gpt-4o", "name": "gpt-4o"}]

        with patch("api.config_routes.fetch_model_catalog", return_value=models):
            response = asyncio.run(config_routes.get_models(provider_id="openai", refresh=True))

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"models": models})

    def test_get_llm_config_preserves_response_shape(self):
        config = {"base_url": "https://api.example/v1", "api_key": "********"}

        with patch("api.config_routes.build_llm_config_payload", return_value=config):
            response = asyncio.run(config_routes.get_llm_config())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, config)

    def test_agent_runtime_config_routes_preserve_response_shape(self):
        config = {"chat_max_steps": 80, "headless_max_steps": 60}

        with patch("api.config_routes.get_agent_runtime_config_record", return_value=config):
            get_response = asyncio.run(config_routes.get_agent_runtime_config_endpoint())

        with patch("api.config_routes.save_agent_runtime_config_record", return_value=config):
            post_response = asyncio.run(
                config_routes.update_agent_runtime_config_endpoint(
                    AgentRuntimeConfigRequest(
                        chat_max_steps=80,
                        headless_max_steps=60,
                    )
                )
            )

        self.assertEqual(get_response.status, "success")
        self.assertEqual(get_response.data, {"config": config})
        self.assertEqual(post_response.status, "success")
        self.assertEqual(post_response.message, "Agent 执行保护配置已保存")
        self.assertEqual(post_response.data, {"config": config})

    def test_session_retention_config_routes_preserve_response_shape(self):
        config = {
            "enabled": True,
            "raw_result_days": 30,
            "compressed_history_days": 180,
            "audit_metadata_days": 365,
            "max_result_chars": 2000,
            "preview_chars": 1200,
            "preview": {"rows_scanned": 0},
        }

        with patch("api.config_routes.get_session_retention_config_record", return_value=config) as get_config:
            get_response = asyncio.run(config_routes.get_session_retention_config_endpoint(preview=False))

        request = SessionRetentionConfigRequest(
            enabled=True,
            raw_result_days=30,
            compressed_history_days=180,
            audit_metadata_days=365,
            max_result_chars=2000,
            preview_chars=1200,
        )
        with patch("api.config_routes.save_session_retention_config_record", return_value=config) as save_config:
            post_response = asyncio.run(
                config_routes.update_session_retention_config_endpoint(request)
            )

        get_config.assert_called_once_with(include_preview=False)
        save_config.assert_called_once_with(**request.model_dump())
        self.assertEqual(get_response.status, "success")
        self.assertEqual(get_response.data, {"config": config})
        self.assertEqual(post_response.status, "success")
        self.assertEqual(post_response.message, "会话保留策略已保存")
        self.assertEqual(post_response.data, {"config": config})

    def test_session_retention_run_route_preserves_response_shape(self):
        result = {"rows_scanned": 10, "rows_compacted": 1, "rows_deleted": 0}

        with patch("api.config_routes.run_session_retention_policy_record", return_value=result):
            response = asyncio.run(config_routes.run_session_retention_config_endpoint())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "会话保留策略已执行")
        self.assertEqual(response.data, {"result": result})

    def test_update_embedding_config_preserves_response_shape(self):
        with patch("api.config_routes.save_embedding_config_record") as save_embedding:
            response = asyncio.run(
                config_routes.update_embedding_config_endpoint(
                    EmbeddingConfigRequest(model="text-embedding", dim=1024)
                )
            )

        save_embedding.assert_called_once_with("text-embedding", 1024)
        self.assertEqual(response.status, "success")
        self.assertEqual(
            response.message,
            "Embedding 配置已更新: model=text-embedding, dim=1024",
        )

    def test_provider_config_routes_preserve_response_shape(self):
        providers = [{"id": "openai", "api_key": "********"}]
        request = [
            ProviderConfig(
                id="openai",
                name="OpenAI",
                protocol="openai",
                base_url="https://api.example/v1",
                api_key="********",
                models="gpt-4o",
            )
        ]

        with patch("api.config_routes.list_provider_config_records", return_value=providers):
            get_response = asyncio.run(config_routes.get_providers_endpoint())

        with patch("api.config_routes.save_provider_config_records") as save_providers:
            post_response = asyncio.run(config_routes.update_providers_endpoint(request))

        save_providers.assert_called_once_with([request[0].model_dump()])
        self.assertEqual(get_response.status, "success")
        self.assertEqual(get_response.data, {"providers": providers})
        self.assertEqual(post_response.status, "success")
        self.assertEqual(post_response.message, "供应商配置已保存")

    def test_safety_policy_routes_preserve_response_shape(self):
        policy = {"rules": []}
        result = {"action": "deny", "reason": "blocked"}

        with patch("api.config_routes.get_safety_policy_record", return_value=policy):
            get_response = asyncio.run(config_routes.get_safety_policy_endpoint())

        with patch("api.config_routes.save_safety_policy_record", return_value=policy):
            post_response = asyncio.run(
                config_routes.update_safety_policy_endpoint(
                    SafetyPolicyUpdateRequest(policy=policy)
                )
            )

        with patch("api.config_routes.explain_safety_policy_test", return_value=result):
            test_response = asyncio.run(
                config_routes.test_safety_policy_endpoint(
                    SafetyPolicyTestRequest(
                        tool_name="linux_execute_command",
                        command="rm -rf /",
                    )
                )
            )

        self.assertEqual(get_response.status, "success")
        self.assertEqual(get_response.data, {"policy": policy})
        self.assertEqual(post_response.status, "success")
        self.assertEqual(post_response.message, "安全策略已保存")
        self.assertEqual(post_response.data, {"policy": policy})
        self.assertEqual(test_response.status, "success")
        self.assertEqual(test_response.data, {"result": result})


if __name__ == "__main__":
    unittest.main()
