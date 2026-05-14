import asyncio
import shutil
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from fastapi import HTTPException

from api import alert_routes, routes
from api.schemas import AlertEventUpdateRequest


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class FakeWorkflowMemory:
    def __init__(self):
        self.messages = []

    def get_all_assets(self):
        return []

    def append_message(self, session_id, message):
        self.messages.append((session_id, message))


class TestAlertEvents(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_alert_events_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_alert_events_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "alerts.json"

    def test_alert_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/alerts", paths)
        self.assertIn("/alerts/policy", paths)
        self.assertIn("/alerts/policy/test", paths)
        self.assertIn("/alerts/{alert_id}/workflow", paths)
        self.assertIn("/alerts/{alert_id}/workflow/messages", paths)
        self.assertIn("/alerts/{alert_id}/workflow/run-readonly", paths)
        self.assertIn("/alerts/{alert_id}", paths)
        self.assertIn("/webhook/alert", paths)

    def test_webhook_alert_is_persisted_and_queryable(self):
        from core import alert_events, alert_workflows

        store_path = self._store_path("webhook")
        workflow_path = store_path.parent / "workflows.json"
        payload = {
            "host": "10.0.0.10",
            "alert_name": "DiskFull",
            "severity": "critical",
            "description": "disk usage above 95%",
        }
        with (
            patch.object(alert_events, "ALERT_STORE_PATH", store_path),
            patch.object(alert_workflows, "ALERT_WORKFLOW_STORE_PATH", workflow_path),
            patch.dict(alert_routes.ssh_manager.active_sessions, {}, clear=True),
        ):
            response = asyncio.run(alert_routes.receive_webhook_alert(FakeRequest(payload)))
            self.assertEqual(response.status, "success")
            alert_id = response.data["alert"]["id"]

            listed = asyncio.run(alert_routes.list_alert_events(status="open", severity="critical", host=None))
            self.assertEqual(len(listed.data["alerts"]), 1)
            self.assertEqual(listed.data["alerts"][0]["id"], alert_id)
            self.assertEqual(listed.data["alerts"][0]["host"], "10.0.0.10")

            detail = asyncio.run(alert_routes.get_alert_event(alert_id))
            self.assertEqual(detail.data["alert"]["payload"]["alert_name"], "DiskFull")

    def test_alertmanager_payload_expands_and_preserves_labels(self):
        from core import alert_events

        store_path = self._store_path("alertmanager")
        payload = {
            "receiver": "grafana",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "NodeDown",
                        "instance": "10.0.0.12:9100",
                        "severity": "critical",
                    },
                    "annotations": {
                        "summary": "node exporter target down",
                    },
                    "startsAt": "2026-05-13T08:00:00Z",
                    "fingerprint": "fp-node-down",
                }
            ],
        }

        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            created = alert_events.create_alert_events(payload)

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["source_type"], "alertmanager")
        self.assertEqual(created[0]["source"], "grafana")
        self.assertEqual(created[0]["host"], "10.0.0.12:9100")
        self.assertEqual(created[0]["alert_name"], "NodeDown")
        self.assertEqual(created[0]["fingerprint"], "fp-node-down")
        self.assertEqual(created[0]["labels"]["severity"], "critical")

    def test_alertmanager_zero_ends_at_keeps_firing_alert_open(self):
        from core import alert_events, alert_policy

        store_path = self._store_path("alertmanager_zero_end")
        policy_path = store_path.parent / "policy.json"
        payload = {
            "receiver": "alertmanager",
            "status": "firing",
            "alerts": [
                {
                    "labels": {
                        "alertname": "DiskFull",
                        "instance": "172.17.8.151:9100",
                        "severity": "warning",
                    },
                    "annotations": {
                        "description": "172.17.8.151:9100 挂载点 / 磁盘使用率超过 85%。",
                    },
                    "startsAt": "2026-05-13T10:38:02.33005722Z",
                    "endsAt": "0001-01-01T00:00:00Z",
                    "fingerprint": "fp-zero-end",
                }
            ],
        }

        with (
            patch.object(alert_events, "ALERT_STORE_PATH", store_path),
            patch.object(alert_policy, "ALERT_POLICY_CONFIG_PATH", policy_path),
        ):
            created = alert_events.create_alert_events(payload)

        self.assertEqual(created[0]["status"], "open")
        self.assertIsNone(created[0]["closed_at"])
        self.assertEqual(created[0]["automation_decision"]["rule_id"], "default-record-only")
        self.assertFalse(created[0]["automation_decision"]["run_ai"])

    def test_duplicate_fingerprint_merges_and_recovery_closes_event(self):
        from core import alert_events

        store_path = self._store_path("dedupe")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            first = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "warning",
                    "description": "disk 90%",
                    "fingerprint": "zbx-disk",
                }
            )
            second = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "critical",
                    "description": "disk 98%",
                    "fingerprint": "zbx-disk",
                }
            )
            recovered = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "ok",
                    "description": "disk recovered",
                    "status": "resolved",
                    "fingerprint": "zbx-disk",
                }
            )
            listed = alert_events.list_alert_events(limit=10)

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["id"], recovered["id"])
        self.assertEqual(recovered["repeat_count"], 3)
        self.assertEqual(recovered["status"], "closed")
        self.assertEqual(len(listed), 1)

    def test_duplicate_ai_alert_inside_cooldown_only_forwards_notification(self):
        from core import alert_events, alert_policy

        store_path = self._store_path("ai_cooldown")
        policy_path = store_path.parent / "alert_policy.json"
        custom_policy = {
            "version": 1,
            "rules": [
                {
                    "id": "disk-readonly-ai",
                    "name": "磁盘只读分析",
                    "enabled": True,
                    "conditions": {"source_families": ["prometheus"], "name_contains": ["disk"]},
                    "action": "analyze",
                    "notify": True,
                    "channels": ["wechat"],
                    "remediation_mode": "disabled",
                    "cooldown_minutes": 30,
                    "reason": "测试只读分析。",
                }
            ],
        }
        with (
            patch.object(alert_events, "ALERT_STORE_PATH", store_path),
            patch.object(alert_policy, "ALERT_POLICY_CONFIG_PATH", policy_path),
        ):
            alert_policy.save_alert_automation_policy(custom_policy)
            first = alert_events.create_alert_event(
                {
                    "source": "prometheus",
                    "host": "172.17.8.151:9100",
                    "alert_name": "DiskFull",
                    "severity": "warning",
                    "description": "disk 92%",
                    "fingerprint": "prom-disk-cooldown",
                }
            )
            second = alert_events.create_alert_event(
                {
                    "source": "prometheus",
                    "host": "172.17.8.151:9100",
                    "alert_name": "DiskFull",
                    "severity": "warning",
                    "description": "disk 93%",
                    "fingerprint": "prom-disk-cooldown",
                }
            )

        self.assertEqual(first["id"], second["id"])
        self.assertTrue(first["automation_decision"]["run_ai"])
        self.assertFalse(second["automation_decision"]["run_ai"])
        self.assertTrue(second["automation_decision"]["notify"])
        self.assertEqual(second["noise_action"], "cooldown_forward")
        self.assertTrue(second["automation_decision"]["ai_cooldown"]["suppressed"])
        self.assertEqual(second["notification_plan"]["when"], "received")

    def test_custom_policy_controls_ai_cooldown_minutes(self):
        from core import alert_events, alert_policy

        store_path = self._store_path("custom_cooldown")
        policy_path = store_path.parent / "alert_policy.json"
        custom_policy = {
            "version": 1,
            "rules": [
                {
                    "id": "short-cooldown",
                    "name": "短冷却测试",
                    "enabled": True,
                    "conditions": {"source_families": ["prometheus"], "name_contains": ["disk"]},
                    "action": "analyze",
                    "notify": True,
                    "channels": ["wechat"],
                    "remediation_mode": "suggest",
                    "cooldown_minutes": 7,
                    "reason": "测试短冷却。",
                }
            ],
        }
        with (
            patch.object(alert_events, "ALERT_STORE_PATH", store_path),
            patch.object(alert_policy, "ALERT_POLICY_CONFIG_PATH", policy_path),
        ):
            alert_policy.save_alert_automation_policy(custom_policy)
            first = alert_events.create_alert_event(
                {
                    "source": "prometheus",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "warning",
                    "description": "disk 92%",
                    "fingerprint": "prom-disk-short-cooldown",
                }
            )
            second = alert_events.create_alert_event(
                {
                    "source": "prometheus",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "warning",
                    "description": "disk 93%",
                    "fingerprint": "prom-disk-short-cooldown",
                }
            )

        self.assertEqual(first["automation_decision"]["cooldown_minutes"], 7)
        self.assertEqual(second["automation_decision"]["ai_cooldown"]["window_minutes"], 7)
        self.assertEqual(second["noise_action"], "cooldown_forward")

    def test_list_alert_events_filters_source_family_and_automation(self):
        from core import alert_events

        store_path = self._store_path("policy_filters")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            zabbix = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "critical",
                    "description": "disk above 95%",
                    "fingerprint": "zbx-critical",
                }
            )
            info = alert_events.create_alert_event(
                {
                    "source": "prometheus",
                    "host": "web.local",
                    "alert_name": "FYI",
                    "severity": "info",
                    "description": "informational alert",
                    "fingerprint": "prom-info",
                }
            )
            zabbix_items = alert_events.list_alert_events(source_family="zabbix", limit=10)
            ai_items = alert_events.list_alert_events(automation_mode="ai", limit=10)
            record_items = alert_events.list_alert_events(automation_mode="record_only", limit=10)

        self.assertEqual([item["id"] for item in zabbix_items], [zabbix["id"]])
        self.assertEqual(ai_items, [])
        self.assertEqual([item["id"] for item in record_items], [info["id"], zabbix["id"]])

    def test_custom_alert_policy_overrides_default_automation(self):
        from core import alert_events, alert_policy

        store_path = self._store_path("custom_policy")
        policy_path = store_path.parent / "alert_policy.json"
        custom_policy = {
            "version": 1,
            "rules": [
                {
                    "id": "zabbix-db-record",
                    "name": "Zabbix DB 仅记录",
                    "enabled": True,
                    "conditions": {"source_families": ["zabbix"], "host_contains": ["db"]},
                    "action": "record_only",
                    "notify": False,
                    "channels": [],
                    "reason": "测试策略命中。",
                }
            ],
        }
        with (
            patch.object(alert_events, "ALERT_STORE_PATH", store_path),
            patch.object(alert_policy, "ALERT_POLICY_CONFIG_PATH", policy_path),
        ):
            alert_policy.save_alert_automation_policy(custom_policy)
            created = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "critical",
                    "description": "disk above 95%",
                    "fingerprint": "zbx-db-record",
                }
            )

        self.assertEqual(created["automation_decision"]["rule_id"], "zabbix-db-record")
        self.assertEqual(created["automation_decision"]["rule_name"], "Zabbix DB 仅记录")
        self.assertFalse(created["automation_decision"]["run_ai"])
        self.assertFalse(created["automation_decision"]["notify"])

    def test_policy_does_not_treat_alertmanager_zero_end_as_recovery(self):
        from core import alert_policy

        policy_path = self._store_path("policy_zero_end") / "policy.json"
        with patch.object(alert_policy, "ALERT_POLICY_CONFIG_PATH", policy_path):
            result = alert_policy.explain_alert_policy_for_payload(
                {
                    "source_type": "alertmanager",
                    "host": "172.17.8.151:9100",
                    "alert_name": "DiskFull",
                    "severity": "warning",
                    "description": "172.17.8.151:9100 挂载点 / 磁盘使用率超过 85%。",
                    "ends_at": "0001-01-01T00:00:00Z",
                    "status_hint": "firing",
                    "labels": {"alertname": "DiskFull", "instance": "172.17.8.151:9100"},
                }
            )

        self.assertEqual(result["policy"]["noise_action"], "record_only")
        self.assertEqual(result["policy"]["automation_decision"]["rule_id"], "default-record-only")
        self.assertFalse(result["policy"]["automation_decision"]["run_ai"])

    def test_alert_workflow_links_active_session_and_records_manual_message(self):
        from core import alert_workflows

        workflow_path = self._store_path("workflow") / "workflows.json"
        alert = {
            "id": "alert-test-workflow",
            "host": "192.168.130.45",
            "alert_name": "DiskFull",
            "source_family": "prometheus",
            "alert_class": "capacity",
            "automation_decision": {
                "run_ai": True,
                "notify": True,
                "rule_name": "磁盘告警自动分析",
                "remediation_mode": "approval",
                "allowed_remediation_actions": ["cleanup_temp_files"],
            },
        }
        active_sessions = {
            "sid-linux": {
                "info": {
                    "host": "192.168.130.45",
                    "remark": "应用服务器",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "allow_modifications": False,
                    "active_skills": ["linux"],
                    "tags": ["生产"],
                }
            }
        }
        with patch.object(alert_workflows, "ALERT_WORKFLOW_STORE_PATH", workflow_path):
            workflow = alert_workflows.ensure_alert_workflow(alert, active_sessions=active_sessions, injected_count=1)
            updated = alert_workflows.append_alert_workflow_message(alert["id"], "user", "我已人工接管，先不要自动修复。")

        self.assertEqual(workflow["linked_sessions"][0]["session_id"], "sid-linux")
        self.assertEqual(workflow["steps"][2]["id"], "monitoring_context")
        self.assertTrue(workflow["steps"][2]["details"]["queries"])
        self.assertEqual(workflow["steps"][-1]["details"]["mode"], "approval")
        self.assertEqual(updated["messages"][-1]["content"], "我已人工接管，先不要自动修复。")

    def test_alert_workflow_manual_readonly_trigger_starts_linked_session(self):
        from core import alert_workflows

        workflow_path = self._store_path("workflow_run") / "workflows.json"
        alert = {
            "id": "alert-run-workflow",
            "host": "192.168.130.45",
            "alert_name": "DiskFull",
            "severity": "critical",
            "description": "disk full",
            "source_family": "prometheus",
            "alert_class": "capacity",
            "automation_decision": {"run_ai": True, "notify": False, "remediation_mode": "suggest"},
        }
        active_sessions = {"sid-linux": {"info": {"host": "192.168.130.45", "pending_messages": []}}}
        runner_calls = []
        scheduled = []

        def heartbeat_runner(*args, **kwargs):
            runner_calls.append((args, kwargs))

            async def noop():
                return "done"

            return noop()

        def task_factory(coro):
            scheduled.append(coro)
            return coro

        async def scenario():
            with patch.object(alert_workflows, "ALERT_WORKFLOW_STORE_PATH", workflow_path):
                result = await alert_workflows.trigger_alert_workflow_readonly_analysis(
                    alert,
                    active_sessions=active_sessions,
                    session_locks={},
                    memory_db=FakeWorkflowMemory(),
                    dispatcher="dispatcher",
                    heartbeat_runner=heartbeat_runner,
                    task_factory=task_factory,
                )
            for coro in scheduled:
                await coro
            return result

        result = asyncio.run(scenario())

        self.assertEqual(result["injected_count"], 1)
        self.assertTrue(active_sessions["sid-linux"]["info"]["heartbeat_in_progress"])
        self.assertEqual(runner_calls[0][0][0], "sid-linux")
        self.assertEqual(runner_calls[0][0][3], "dispatcher")
        self.assertIn("手动触发只读分析", runner_calls[0][1]["trigger_msg"])
        self.assertIn("node_filesystem_avail_bytes", runner_calls[0][1]["trigger_msg"])

    def test_alert_status_update_and_close_contract(self):
        from core import alert_events

        store_path = self._store_path("status")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            created = alert_events.create_alert_event(
                {
                    "host": "10.0.0.11",
                    "alert_name": "CPUHigh",
                    "severity": "warning",
                    "description": "cpu high",
                }
            )
            update = AlertEventUpdateRequest(
                status="acknowledged",
                assignee="ops",
                note="checking",
            )
            response = asyncio.run(alert_routes.update_alert_event(created["id"], update))
            self.assertEqual(response.data["alert"]["status"], "acknowledged")
            self.assertEqual(response.data["alert"]["assignee"], "ops")

            close = AlertEventUpdateRequest(status="closed", note="resolved")
            response = asyncio.run(alert_routes.update_alert_event(created["id"], close))
            self.assertEqual(response.data["alert"]["status"], "closed")
            self.assertTrue(response.data["alert"]["closed_at"])

    def test_missing_alert_raises_404(self):
        from core import alert_events

        store_path = self._store_path("missing")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(alert_routes.get_alert_event("missing"))

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
