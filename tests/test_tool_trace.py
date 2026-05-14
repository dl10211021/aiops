from core.tool_trace import append_tool_trace_event, make_tool_trace_collector


def test_append_tool_trace_event_merges_end_into_running_start():
    trace = []
    append_tool_trace_event(
        trace,
        {
            "type": "tool_start",
            "toolCallId": "call-db-1",
            "tool": "db_execute_query",
            "args": "select 1 from dual",
            "resultMeta": {"tool_policy": {"evidence_family": "database"}},
            "startedAt": 100,
        },
        now=lambda: 1.0,
    )
    append_tool_trace_event(
        trace,
        {
            "type": "tool_end",
            "toolCallId": "call-db-1",
            "tool": "db_execute_query",
            "result": "1",
            "resultMeta": {"type": "database_statement"},
            "evidenceId": "tev-sid-call-1",
            "evidence": {"evidence_id": "tev-sid-call-1"},
            "status": "done",
            "completedAt": 150,
        },
        now=lambda: 2.0,
    )

    assert trace == [
        {
            "type": "tool_end",
            "toolCallId": "call-db-1",
            "tool": "db_execute_query",
            "args": "select 1 from dual",
            "result": "1",
            "resultMeta": {
                "tool_policy": {"evidence_family": "database"},
                "type": "database_statement",
            },
            "evidenceId": "tev-sid-call-1",
            "evidence": {"evidence_id": "tev-sid-call-1"},
            "status": "done",
            "startedAt": 100,
            "completedAt": 150,
        }
    ]


def test_append_tool_trace_event_end_meta_overrides_start_meta_keys():
    trace = []
    append_tool_trace_event(
        trace,
        {
            "type": "tool_start",
            "toolCallId": "call-db-2",
            "tool": "db_execute_query",
            "args": "select 1",
            "resultMeta": {"type": "tool_start", "tool_policy": {"name": "old"}},
            "startedAt": 100,
        },
        now=lambda: 1.0,
    )
    append_tool_trace_event(
        trace,
        {
            "type": "tool_end",
            "toolCallId": "call-db-2",
            "tool": "db_execute_query",
            "result": "1",
            "resultMeta": {"type": "database_statement"},
            "completedAt": 120,
        },
        now=lambda: 2.0,
    )

    assert trace[0]["resultMeta"] == {
        "type": "database_statement",
        "tool_policy": {"name": "old"},
    }


def test_append_tool_trace_event_uses_call_id_to_avoid_wrong_merge():
    trace = []
    append_tool_trace_event(
        trace,
        {
            "type": "tool_start",
            "toolCallId": "call-a",
            "tool": "linux_execute_command",
            "args": "uptime",
            "startedAt": 100,
        },
        now=lambda: 1.0,
    )
    append_tool_trace_event(
        trace,
        {
            "type": "tool_start",
            "toolCallId": "call-b",
            "tool": "db_execute_query",
            "args": "select 1",
            "startedAt": 110,
        },
        now=lambda: 1.1,
    )
    append_tool_trace_event(
        trace,
        {
            "type": "tool_end",
            "toolCallId": "call-a",
            "tool": "linux_execute_command",
            "result": "ok",
            "completedAt": 130,
        },
        now=lambda: 1.3,
    )

    assert trace[0]["type"] == "tool_end"
    assert trace[0]["toolCallId"] == "call-a"
    assert trace[0]["result"] == "ok"
    assert trace[1]["type"] == "tool_start"
    assert trace[1]["toolCallId"] == "call-b"
    assert trace[1]["status"] == "running"


def test_make_tool_trace_collector_appends_unmatched_tool_end():
    trace = []
    collector = make_tool_trace_collector(trace, now=lambda: 3.0)

    collector({"type": "tool_end", "tool": "linux_execute_command", "result": "ok"})

    assert trace == [
        {
            "type": "tool_end",
            "toolCallId": "",
            "tool": "linux_execute_command",
            "result": "ok",
            "resultMeta": {},
            "evidenceId": "",
            "evidence": {},
            "status": "done",
            "completedAt": 3000,
        }
    ]


def test_tool_start_trace_preserves_result_metadata():
    trace = []
    append_tool_trace_event(
        trace,
        {
            "type": "tool_start",
            "toolCallId": "call-linux-1",
            "tool": "linux_execute_command",
            "args": "uptime",
            "resultMeta": {
                "tool_policy": {
                    "name": "linux_execute_command",
                    "evidence_family": "host_cli",
                }
            },
            "startedAt": 100,
        },
        now=lambda: 1.0,
    )

    assert trace == [
        {
            "type": "tool_start",
            "toolCallId": "call-linux-1",
            "tool": "linux_execute_command",
            "args": "uptime",
            "resultMeta": {
                "tool_policy": {
                    "name": "linux_execute_command",
                    "evidence_family": "host_cli",
                }
            },
            "status": "running",
            "startedAt": 100,
        }
    ]
