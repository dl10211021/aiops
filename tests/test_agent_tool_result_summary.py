import json

from core.agent_runtime_config import (
    agent_max_steps,
    agent_step_limit_instruction,
)
from core.agent_tool_events import (
    build_tool_end_event,
    parse_tool_arguments,
    summarize_tool_result_for_sse,
)


def test_summarize_tool_result_for_sse_preserves_database_metadata_when_preview_is_truncated():
    result = {
        "success": True,
        "has_result_set": False,
        "statement_type": "alter",
        "committed": True,
        "affected_rows": -1,
        "message": "ALTER 已执行并提交",
        "data": ["x" * 1000],
    }

    summary = summarize_tool_result_for_sse(result, preview_limit=80)

    assert summary["status"] == "done"
    assert summary["preview"].endswith("...")
    assert summary["metadata"] == {
        "type": "database_statement",
        "statement_type": "alter",
        "has_result_set": False,
        "committed": True,
        "affected_rows": -1,
        "message": "ALTER 已执行并提交",
    }


def test_summarize_tool_result_for_sse_marks_blocked_result_as_error():
    summary = summarize_tool_result_for_sse({"status": "BLOCKED", "reason": "只读模式拦截"})

    assert summary["status"] == "error"
    assert "只读模式拦截" in summary["preview"]
    assert summary["metadata"]["status"] == "BLOCKED"
    assert summary["metadata"]["reason"] == "只读模式拦截"


def test_summarize_tool_result_for_sse_preserves_policy_action_metadata():
    action = {
        "id": "linux.service.change",
        "label": "变更服务状态",
        "description": "启动、停止、重启、启用或禁用系统服务。",
        "severity": "high",
    }

    summary = summarize_tool_result_for_sse(
        {
            "status": "BLOCKED",
            "reason": "只读安全模式，已拦截",
            "actions": [action],
            "primary_action": action,
            "policy_decision": "readonly_block",
            "tool_policy": {
                "name": "linux_execute_command",
                "operation_mode": "read_write",
                "approval_policy": "guarded_write",
                "evidence_family": "host_cli",
            },
        }
    )

    assert summary["status"] == "error"
    assert summary["metadata"]["type"] == "tool_result"
    assert summary["metadata"]["status"] == "BLOCKED"
    assert summary["metadata"]["reason"] == "只读安全模式，已拦截"
    assert summary["metadata"]["actions"] == [action]
    assert summary["metadata"]["primary_action"] == action
    assert summary["metadata"]["policy_decision"] == "readonly_block"
    assert summary["metadata"]["tool_policy"]["name"] == "linux_execute_command"
    assert summary["metadata"]["tool_policy"]["evidence_family"] == "host_cli"


def test_summarize_tool_result_for_sse_preserves_winrm_error_metadata():
    summary = summarize_tool_result_for_sse(
        {
            "success": False,
            "has_error": True,
            "exit_status": 1,
            "error_type": "permission_denied",
            "error": "当前 WinRM 账号缺少读取 Security 日志的权限。",
            "hint": "请把账号加入 Administrators 或 Event Log Readers 后重试。",
            "raw_error": "Get-WinEvent : Access is denied",
        },
        preview_limit=80,
    )

    assert summary["status"] == "error"
    assert summary["metadata"]["type"] == "tool_result"
    assert summary["metadata"]["has_error"] is True
    assert summary["metadata"]["exit_status"] == 1
    assert summary["metadata"]["error_type"] == "permission_denied"
    assert summary["metadata"]["error"] == "当前 WinRM 账号缺少读取 Security 日志的权限。"
    assert summary["metadata"]["hint"] == "请把账号加入 Administrators 或 Event Log Readers 后重试。"
    assert summary["metadata"]["raw_error"] == "Get-WinEvent : Access is denied"


def test_build_tool_end_event_includes_structured_error_metadata():
    message, safe_text = build_tool_end_event(
        "call-1",
        "winrm_execute_command",
        {
            "status": "ERROR",
            "error_type": "powershell_syntax",
            "error": "PowerShell 脚本语法错误。",
            "hint": "请检查括号和管道表达式。",
        },
    )

    payload = json.loads(message)

    assert payload["type"] == "tool_end"
    assert payload["id"] == "call-1"
    assert payload["tool"] == "winrm_execute_command"
    assert payload["result_status"] == "error"
    assert payload["result_meta"]["type"] == "tool_result"
    assert payload["result_meta"]["error_type"] == "powershell_syntax"
    assert payload["result_meta"]["hint"] == "请检查括号和管道表达式。"
    assert "PowerShell 脚本语法错误" in safe_text


def test_build_tool_end_event_includes_runtime_policy_error_metadata():
    runtime_policy = {
        "attempts": 1,
        "max_attempts": 2,
        "retry_delay_seconds": 0,
        "retry_on": ["timeout"],
        "timeout_seconds": 0.001,
    }
    message, _safe_text = build_tool_end_event(
        "call-1",
        "slow_tool",
        {
            "status": "ERROR",
            "error_type": "tool_timeout",
            "error": "工具执行超过 0.001 秒，已停止。",
            "runtime_policy": runtime_policy,
        },
    )

    payload = json.loads(message)

    assert payload["result_status"] == "error"
    assert payload["result_meta"]["type"] == "tool_result"
    assert payload["result_meta"]["error_type"] == "tool_timeout"
    assert payload["result_meta"]["runtime_policy"] == runtime_policy
    assert payload["result_meta"]["tool_policy"]["name"] == "slow_tool"


def test_build_tool_end_event_attaches_tool_policy_metadata_to_success_result():
    message, safe_text = build_tool_end_event(
        "call-1",
        "linux_execute_command",
        {"success": True, "stdout": "ok"},
    )

    payload = json.loads(message)

    assert payload["result_status"] == "done"
    assert payload["result_meta"]["type"] == "tool_result"
    assert payload["result_meta"]["tool_policy"]["name"] == "linux_execute_command"
    assert payload["result_meta"]["tool_policy"]["operation_mode"] == "read_write"
    assert payload["result_meta"]["tool_policy"]["approval_policy"] == "guarded_write"
    assert payload["result_meta"]["tool_policy"]["evidence_family"] == "host_cli"
    assert "ok" in safe_text


def test_build_tool_end_event_can_attach_standard_tool_evidence():
    message, _safe_text = build_tool_end_event(
        "call-1",
        "db_execute_query",
        {"success": True, "data": [{"one": 1}]},
        session_id="sid-db",
        context={
            "target_scope": "asset",
            "asset_type": "oracle",
            "protocol": "oracle",
            "host": "db.local",
            "port": 1521,
        },
        input_summary="select 1 from dual",
        started_at=100,
        finished_at=150,
    )

    payload = json.loads(message)

    assert payload["evidence_id"] == "tev-sid-db-call-1"
    assert payload["started_at"] == 100
    assert payload["finished_at"] == 150
    assert payload["evidence"]["session_id"] == "sid-db"
    assert payload["evidence"]["tool_name"] == "db_execute_query"
    assert payload["evidence"]["tool_family"] == "database"
    assert payload["evidence"]["input_summary"] == "select 1 from dual"
    assert payload["evidence"]["asset_ref"]["host"] == "db.local"
    assert payload["evidence"]["result_meta"]["tool_policy"]["name"] == "db_execute_query"
    assert (
        payload["evidence"]["result_meta"]["tool_policy"]["evidence_family"]
        == "database"
    )
    assert payload["evidence"]["started_at"] == 100
    assert payload["evidence"]["finished_at"] == 150


def test_build_tool_end_event_records_session_mode_variants_from_context():
    message_readwrite, _safe_text_rw = build_tool_end_event(
        "call-1",
        "db_execute_query",
        {"success": True},
        context={"allow_modifications": True},
    )
    payload_readwrite = json.loads(message_readwrite)
    assert payload_readwrite["result_meta"]["session_mode"] == "readwrite"

    message_readonly, _safe_text_ro = build_tool_end_event(
        "call-2",
        "db_execute_query",
        {"success": True},
        context={"session_mode": "readonly"},
    )
    payload_readonly = json.loads(message_readonly)
    assert payload_readonly["result_meta"]["session_mode"] == "readonly"

    message_contextless, _safe_text_unknown = build_tool_end_event(
        "call-3",
        "db_execute_query",
        {"success": True},
        context={"allow_modifications": False},
    )
    payload_contextless = json.loads(message_contextless)
    assert payload_contextless["result_meta"]["session_mode"] == "readonly"


def test_agent_max_steps_defaults_and_bounds(monkeypatch):
    monkeypatch.delenv("OPSCORE_AGENT_MAX_STEPS", raising=False)
    monkeypatch.delenv("OPSCORE_HEADLESS_AGENT_MAX_STEPS", raising=False)

    assert agent_max_steps("chat") == 80
    assert agent_max_steps("headless") == 60

    monkeypatch.setenv("OPSCORE_AGENT_MAX_STEPS", "5")
    assert agent_max_steps("chat") == 10

    monkeypatch.setenv("OPSCORE_AGENT_MAX_STEPS", "999")
    assert agent_max_steps("chat") == 200

    monkeypatch.setenv("OPSCORE_AGENT_MAX_STEPS", "abc")
    assert agent_max_steps("chat") == 80

    monkeypatch.setenv("OPSCORE_AGENT_MAX_STEPS", "90")
    monkeypatch.setenv("OPSCORE_HEADLESS_AGENT_MAX_STEPS", "70")
    assert agent_max_steps("headless") == 70


def test_agent_step_limit_instruction_forces_summary_without_tools():
    instruction = agent_step_limit_instruction(80)

    assert "80 步执行保护上限" in instruction
    assert "停止继续调用任何工具" in instruction
    assert "阶段性运维报告" in instruction
    assert "未完成项目" in instruction


def test_parse_tool_arguments_repairs_complex_powershell_command_quotes():
    raw_arguments = (
        '{"command": "Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | '
        'Where-Object {$_.FreeSpace -gt 0} | '
        'Select-Object DeviceID,@{Name=\'FreeGB\';Expression={[math]::Round($_.FreeSpace/1GB,2)}}" }'
    )

    parsed = parse_tool_arguments(raw_arguments)

    assert parsed["command"] == (
        "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | "
        "Where-Object {$_.FreeSpace -gt 0} | "
        "Select-Object DeviceID,@{Name='FreeGB';Expression={[math]::Round($_.FreeSpace/1GB,2)}}"
    )


def test_parse_tool_arguments_accepts_already_parsed_dict():
    parsed = parse_tool_arguments(
        {
            "command": "Get-Service | Where-Object {$_.Status -ne 'Running'}",
        }
    )

    assert parsed["command"] == "Get-Service | Where-Object {$_.Status -ne 'Running'}"
