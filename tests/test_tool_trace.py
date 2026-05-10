from core.tool_trace import append_tool_trace_event, make_tool_trace_collector


def test_append_tool_trace_event_merges_end_into_running_start():
    trace = []
    append_tool_trace_event(
        trace,
        {
            "type": "tool_start",
            "tool": "db_execute_query",
            "args": "select 1 from dual",
            "startedAt": 100,
        },
        now=lambda: 1.0,
    )
    append_tool_trace_event(
        trace,
        {
            "type": "tool_end",
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
            "tool": "db_execute_query",
            "args": "select 1 from dual",
            "result": "1",
            "resultMeta": {"type": "database_statement"},
            "evidenceId": "tev-sid-call-1",
            "evidence": {"evidence_id": "tev-sid-call-1"},
            "status": "done",
            "startedAt": 100,
            "completedAt": 150,
        }
    ]


def test_make_tool_trace_collector_appends_unmatched_tool_end():
    trace = []
    collector = make_tool_trace_collector(trace, now=lambda: 3.0)

    collector({"type": "tool_end", "tool": "linux_execute_command", "result": "ok"})

    assert trace == [
        {
            "type": "tool_end",
            "tool": "linux_execute_command",
            "result": "ok",
            "resultMeta": {},
            "evidenceId": "",
            "evidence": {},
            "status": "done",
            "completedAt": 3000,
        }
    ]
