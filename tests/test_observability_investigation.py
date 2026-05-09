import unittest

from core.observability.service import ObservabilityCatalogService


class TestObservabilityInvestigationService(unittest.TestCase):
    def test_create_investigation_builds_readonly_agent_plan(self):
        service = ObservabilityCatalogService()

        investigation = service.create_investigation(
            system_id="global-portal-test",
            title="系统慢",
            symptom="global 门户响应慢，先按最近 2 小时排查。",
            time_window="最近 2 小时",
            severity="warning",
        )

        self.assertIsNotNone(investigation)
        assert investigation is not None
        self.assertEqual(investigation.system_id, "global-portal-test")
        self.assertGreaterEqual(len(investigation.tasks), 2)
        self.assertTrue(all(task.input_json.get("read_only") for task in investigation.tasks))
        self.assertIn("Summary Agent", {task.agent_role for task in investigation.tasks})

    def test_append_evidence_and_root_cause_keeps_evidence_first_class(self):
        service = ObservabilityCatalogService()
        investigation = service.create_investigation(
            system_id="global-portal-test",
            title="系统慢",
            symptom="用户反馈门户慢。",
            time_window="最近 2 小时",
            severity="warning",
        )
        assert investigation is not None

        evidence = service.append_evidence(
            investigation.id,
            title="Prometheus target up 正常",
            summary="Prometheus 会话返回 target 全部 up，但 K8s 重启指标仍需确认。",
            evidence_type="metric",
            source_id="src-prometheus-session",
            confidence="inferred",
        )
        self.assertIsNotNone(evidence)
        assert evidence is not None

        root_cause = service.append_root_cause(
            investigation.id,
            title="K8s 工作负载重启导致短时慢",
            description="该候选只被 Prometheus 指标间接支持，需要继续拉取 K8s events。",
            likelihood="medium",
            impact="medium",
            confidence="pending_review",
            supporting_evidence_ids=[evidence.id],
            recommended_next_steps=["检查 Pod restart 和 events", "确认发布窗口"],
        )

        self.assertIsNotNone(root_cause)
        refreshed = service.get_investigation(investigation.id)
        assert refreshed is not None
        self.assertEqual(refreshed.evidence_count, 1)
        self.assertEqual(refreshed.evidence[0].id, evidence.id)
        self.assertEqual(refreshed.root_causes[0].supporting_evidence_ids, [evidence.id])
        self.assertIn("K8s 工作负载重启导致短时慢", refreshed.root_cause_candidates)

    def test_missing_system_does_not_create_investigation(self):
        service = ObservabilityCatalogService()

        investigation = service.create_investigation(
            system_id="missing",
            title="系统慢",
            symptom="缺少业务画像。",
        )

        self.assertIsNone(investigation)

    def test_bind_asset_and_session_updates_business_profile(self):
        service = ObservabilityCatalogService()

        profile = service.bind_asset(
            "global-portal-test",
            {
                "id": 151,
                "remark": "MySQL 测试库",
                "host": "172.17.8.151",
                "port": 3306,
                "asset_type": "mysql",
                "protocol": "mysql",
                "username": "root",
            },
        )
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.summary()["bound_asset_count"], 1)
        self.assertIn("database", profile.layer_counts())

        profile = service.bind_session(
            "global-portal-test",
            {
                "id": "sid-prom",
                "remark": "Prometheus 会话",
                "host": "192.168.130.45",
                "asset_type": "prometheus",
                "protocol": "http_api",
                "user": "",
            },
            role="control_session",
        )
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.summary()["bound_session_count"], 1)
        self.assertTrue(any(source.session_id == "sid-prom" for source in profile.observable_sources))
