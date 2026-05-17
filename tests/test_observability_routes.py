import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api import observability_routes


class TestObservabilityRoutes(unittest.TestCase):
    def test_list_systems_returns_unknown_friendly_sample_profile(self):
        response = asyncio.run(observability_routes.list_observability_systems())

        self.assertEqual(response.status, "success")
        systems = response.data["systems"]
        self.assertEqual(len(systems), 1)
        self.assertEqual(systems[0]["system"]["name"], "集团global协作门户")
        self.assertGreaterEqual(systems[0]["unknown_count"], 1)

    def test_get_profile_returns_components_sources_and_unknowns(self):
        response = asyncio.run(
            observability_routes.get_observability_system_profile("global-portal-test")
        )

        profile = response.data["profile"]
        self.assertEqual(profile["system"]["environment"], "测试环境")
        self.assertTrue(profile["components"])
        self.assertTrue(profile["unknowns"])
        self.assertTrue(profile["observable_sources"])

    def test_missing_profile_maps_to_404(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(observability_routes.get_observability_system_profile("missing"))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_profile_packs_endpoint_exposes_prometheus_capabilities(self):
        response = asyncio.run(observability_routes.list_observability_profile_packs())

        packs = response.data["profile_packs"]
        prometheus = next(pack for pack in packs if pack["id"] == "prometheus-source")
        self.assertIn("query_promql", prometheus["capabilities"])

    def test_discovery_candidates_endpoint_exposes_pending_review_items(self):
        response = asyncio.run(observability_routes.list_observability_discovery_candidates())

        candidates = response.data["candidates"]
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["status"], "pending_review")
        self.assertTrue(candidates[0]["evidence_summary"])

    def test_investigations_endpoint_exposes_agent_plan(self):
        response = asyncio.run(observability_routes.list_observability_investigations())

        investigations = response.data["investigations"]
        self.assertEqual(investigations[0]["system_id"], "global-portal-test")
        self.assertTrue(investigations[0]["agent_plan"])

    def test_create_investigation_builds_read_only_agent_tasks(self):
        response = asyncio.run(
            observability_routes.create_observability_investigation(
                observability_routes.InvestigationCreateRequest(
                    system_id="global-portal-test",
                    title="测试环境门户慢",
                    symptom="页面响应时间升高",
                    time_window="最近 30 分钟",
                    severity="warning",
                )
            )
        )

        investigation = response.data["investigation"]
        self.assertEqual(investigation["status"], "draft")
        self.assertGreaterEqual(len(investigation["tasks"]), 2)
        self.assertTrue(all(task["input_json"].get("read_only") for task in investigation["tasks"]))

    def test_append_evidence_and_root_cause_updates_investigation(self):
        evidence_response = asyncio.run(
            observability_routes.append_observability_evidence(
                "inv-global-portal-slow",
                observability_routes.EvidenceAppendRequest(
                    title="Prometheus target 正常",
                    summary="up 指标为 1",
                    evidence_type="metric",
                    source_id="src-prometheus-session",
                    confidence="confirmed",
                ),
            )
        )
        root_response = asyncio.run(
            observability_routes.append_observability_root_cause(
                "inv-global-portal-slow",
                observability_routes.RootCauseAppendRequest(
                    title="等待更多证据",
                    description="当前证据不足以确认单一根因",
                    supporting_evidence_ids=[evidence_response.data["evidence"]["id"]],
                ),
            )
        )

        self.assertEqual(evidence_response.data["investigation"]["evidence_count"], 1)
        self.assertIn("等待更多证据", root_response.data["investigation"]["root_cause_candidates"])

    def test_create_investigation_route_returns_tasks(self):
        req = observability_routes.InvestigationCreateRequest(
            system_id="global-portal-test",
            title="系统慢",
            symptom="global 门户访问变慢",
            time_window="最近 2 小时",
            severity="warning",
        )

        response = asyncio.run(observability_routes.create_observability_investigation(req))

        investigation = response.data["investigation"]
        self.assertEqual(investigation["title"], "系统慢")
        self.assertTrue(investigation["tasks"])
        self.assertEqual(investigation["evidence_count"], 0)

    def test_append_evidence_route_updates_investigation_summary(self):
        create_req = observability_routes.InvestigationCreateRequest(
            system_id="global-portal-test",
            title="证据回收测试",
            symptom="排查事件需要挂证据",
            severity="warning",
        )
        create_response = asyncio.run(observability_routes.create_observability_investigation(create_req))
        investigation_id = create_response.data["investigation"]["id"]
        evidence_req = observability_routes.EvidenceAppendRequest(
            title="Prometheus 告警为空",
            summary="当前窗口没有 firing 告警。",
            evidence_type="metric",
            confidence="confirmed",
        )

        response = asyncio.run(
            observability_routes.append_observability_evidence(investigation_id, evidence_req)
        )

        self.assertEqual(response.data["evidence"]["title"], "Prometheus 告警为空")
        self.assertEqual(response.data["investigation"]["evidence_count"], 1)

    def test_append_evidence_route_preserves_tool_evidence_contract(self):
        create_response = asyncio.run(
            observability_routes.create_observability_investigation(
                observability_routes.InvestigationCreateRequest(
                    system_id="global-portal-test",
                    title="工具证据接入测试",
                    symptom="需要把会话工具结果转成观测证据",
                    severity="warning",
                )
            )
        )
        investigation_id = create_response.data["investigation"]["id"]
        tool_evidence = {
            "evidence_id": "tev-sid-1-call-1",
            "session_id": "sid-1",
            "tool_name": "db_execute_query",
            "tool_family": "database",
            "input_summary": "select 1 from dual",
            "output_preview": "1",
            "result_status": "done",
        }

        response = asyncio.run(
            observability_routes.append_observability_evidence(
                investigation_id,
                observability_routes.EvidenceAppendRequest(
                    title="数据库只读检查完成",
                    summary="select 1 返回正常",
                    evidence_type="tool_result",
                    tool_evidence=tool_evidence,
                    confidence="confirmed",
                ),
            )
        )

        evidence = response.data["evidence"]
        self.assertEqual(evidence["tool_evidence"], tool_evidence)
        self.assertEqual(evidence["raw_ref"], "tev-sid-1-call-1")
        self.assertEqual(evidence["raw_excerpt"], "1")
        self.assertEqual(response.data["investigation"]["evidence_count"], 1)

    def test_append_run_trace_evidence_route_hydrates_tool_evidence(self):
        create_response = asyncio.run(
            observability_routes.create_observability_investigation(
                observability_routes.InvestigationCreateRequest(
                    system_id="global-portal-test",
                    title="Run Trace 证据接入测试",
                    symptom="需要把会话运行证据挂到可观测排查",
                    severity="warning",
                )
            )
        )
        investigation_id = create_response.data["investigation"]["id"]
        trace_result = {
            "source": "run_trace",
            "trace": {
                "tool": "db_execute_query",
                "toolCallId": "call-db-1",
                "evidenceId": "tev-sid-db-call-db-1",
                "status": "success",
                "resultMeta": {"tool_policy": {"evidence_family": "database"}},
                "evidence": {
                    "evidence_id": "tev-sid-db-call-db-1",
                    "tool_family": "database",
                    "input_summary": "select count(*) from orders",
                    "output_preview": "42",
                    "result_status": "success",
                },
            },
            "run": {"run_id": "run-1", "event_type": "tool:after"},
        }

        with patch.object(observability_routes, "find_session_history_evidence_trace", return_value=trace_result):
            response = asyncio.run(
                observability_routes.append_observability_run_trace_evidence(
                    investigation_id,
                    observability_routes.RunTraceEvidenceAppendRequest(
                        session_id="sid-db",
                        evidence_id="tev-sid-db-call-db-1",
                    ),
                )
            )

        evidence = response.data["evidence"]
        self.assertEqual(evidence["evidence_type"], "run_trace_tool")
        self.assertEqual(evidence["raw_ref"], "tev-sid-db-call-db-1")
        self.assertEqual(evidence["raw_excerpt"], "42")
        self.assertEqual(evidence["tool_evidence"]["session_id"], "sid-db")
        self.assertEqual(evidence["tool_evidence"]["run_id"], "run-1")
        self.assertEqual(evidence["tool_evidence"]["tool_call_id"], "call-db-1")
        self.assertEqual(evidence["tool_evidence"]["tool_name"], "db_execute_query")
        self.assertEqual(evidence["tool_evidence"]["tool_family"], "database")
        self.assertIn("select count(*)", evidence["summary"])
        self.assertEqual(response.data["investigation"]["evidence_count"], 1)

    def test_bind_asset_and_session_routes_return_updated_profile(self):
        asset_response = asyncio.run(
            observability_routes.bind_observability_asset(
                "global-portal-test",
                observability_routes.AssetBindingRequest(
                    asset={
                        "id": 1,
                        "remark": "业务应用服务器",
                        "host": "172.17.8.10",
                        "asset_type": "linux",
                        "protocol": "ssh",
                    }
                ),
            )
        )
        self.assertGreaterEqual(asset_response.data["summary"]["bound_asset_count"], 1)

        session_response = asyncio.run(
            observability_routes.bind_observability_session(
                "global-portal-test",
                observability_routes.SessionBindingRequest(
                    session={
                        "id": "sid-1",
                        "remark": "业务系统总控会话",
                        "host": "localhost",
                        "asset_type": "linux",
                        "protocol": "virtual",
                    },
                    role="control_session",
                ),
            )
        )
        self.assertGreaterEqual(session_response.data["summary"]["bound_session_count"], 1)

    def test_unbind_component_route_removes_asset_binding(self):
        asset_response = asyncio.run(
            observability_routes.bind_observability_asset(
                "global-portal-test",
                observability_routes.AssetBindingRequest(
                    asset={
                        "id": "remove-me",
                        "remark": "待移除资产",
                        "host": "172.17.8.11",
                        "asset_type": "linux",
                        "protocol": "ssh",
                    }
                ),
            )
        )
        component = next(
            item for item in asset_response.data["profile"]["components"]
            if item["metadata"].get("asset_id") == "remove-me"
        )

        response = asyncio.run(
            observability_routes.unbind_observability_component("global-portal-test", component["id"])
        )

        component_ids = {item["id"] for item in response.data["profile"]["components"]}
        self.assertNotIn(component["id"], component_ids)

    def test_update_unknown_component_turns_it_into_known_profile_item(self):
        response = asyncio.run(
            observability_routes.update_observability_component(
                "global-portal-test",
                "unk-entry",
                observability_routes.ComponentUpdateRequest(
                    name="global 门户 nginx 入口",
                    component_type="load_balancer",
                    layer="entry",
                    workload_family="entry",
                    confidence="confirmed",
                    metadata={"source_note": "人工补充"},
                ),
            )
        )

        profile = response.data["profile"]
        component_names = {item["name"] for item in profile["components"]}
        unknown_ids = {item["id"] for item in profile["unknowns"]}
        self.assertIn("global 门户 nginx 入口", component_names)
        self.assertNotIn("unk-entry", unknown_ids)
