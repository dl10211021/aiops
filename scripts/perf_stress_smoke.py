from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Page, Route, TimeoutError as PlaywrightTimeoutError, sync_playwright


DEFAULT_URL = "http://127.0.0.1:8000/"
DEFAULT_ASSET_COUNT = 180
DEFAULT_SESSION_COUNT = 72
DEFAULT_HISTORY_MESSAGES = 160


@dataclass
class PerfStep:
    name: str
    ms: float


def response(data: dict[str, Any], *, message: str = "") -> dict[str, Any]:
    return {"status": "success", "message": message, "data": data}


def fulfill_json(route: Route, payload: dict[str, Any]) -> None:
    route.fulfill(
        status=200,
        content_type="application/json; charset=utf-8",
        body=json.dumps(payload, ensure_ascii=False),
    )


def asset_type_definitions() -> list[dict[str, Any]]:
    return [
        {
            "id": "linux",
            "label": "Linux / Unix",
            "category": "os",
            "protocol": "ssh",
            "default_port": 22,
            "capability": {
                "family": "infrastructure",
                "connector": "ssh",
                "operation_model": "shell",
                "tools": ["linux_execute_command"],
                "credential_fields": ["username", "password"],
                "maturity": "native",
                "risk_model": {
                    "read_only_default": True,
                    "approval_required_for_write": True,
                    "hard_block_supported": True,
                    "safety_category": "linux",
                },
                "standard_version": "stress",
            },
        },
        {
            "id": "windows",
            "label": "Windows Server",
            "category": "os",
            "protocol": "winrm",
            "default_port": 5985,
            "capability": {
                "family": "infrastructure",
                "connector": "winrm",
                "operation_model": "powershell",
                "tools": ["winrm_execute_command"],
                "credential_fields": ["username", "password"],
                "maturity": "native",
                "risk_model": {
                    "read_only_default": True,
                    "approval_required_for_write": True,
                    "hard_block_supported": True,
                    "safety_category": "windows",
                },
                "standard_version": "stress",
            },
        },
        {
            "id": "oracle",
            "label": "Oracle",
            "category": "db",
            "protocol": "oracle",
            "default_port": 1521,
            "capability": {
                "family": "database",
                "connector": "database_native",
                "operation_model": "sql",
                "tools": ["db_execute_query"],
                "credential_fields": ["username", "password", "database"],
                "maturity": "native",
                "risk_model": {
                    "read_only_default": True,
                    "approval_required_for_write": True,
                    "hard_block_supported": True,
                    "safety_category": "database",
                },
                "standard_version": "stress",
            },
        },
        {
            "id": "mysql",
            "label": "MySQL",
            "category": "db",
            "protocol": "mysql",
            "default_port": 3306,
            "capability": {
                "family": "database",
                "connector": "database_native",
                "operation_model": "sql",
                "tools": ["db_execute_query"],
                "credential_fields": ["username", "password", "database"],
                "maturity": "native",
                "risk_model": {
                    "read_only_default": True,
                    "approval_required_for_write": True,
                    "hard_block_supported": True,
                    "safety_category": "database",
                },
                "standard_version": "stress",
            },
        },
        {
            "id": "h3c_switch",
            "label": "华三通用交换机",
            "category": "network",
            "protocol": "ssh",
            "default_port": 22,
            "capability": {
                "family": "network",
                "connector": "network_cli",
                "operation_model": "cli",
                "tools": ["network_cli_execute_command"],
                "credential_fields": ["username", "password"],
                "maturity": "native",
                "risk_model": {
                    "read_only_default": True,
                    "approval_required_for_write": True,
                    "hard_block_supported": True,
                    "safety_category": "network",
                },
                "standard_version": "stress",
            },
        },
        {
            "id": "zstack",
            "label": "ZStack",
            "category": "virtualization",
            "protocol": "http_api",
            "default_port": 8080,
            "capability": {
                "family": "virtualization",
                "connector": "virtualization_api",
                "operation_model": "api",
                "tools": ["http_api_request"],
                "credential_fields": ["username", "password"],
                "maturity": "native",
                "risk_model": {
                    "read_only_default": True,
                    "approval_required_for_write": True,
                    "hard_block_supported": True,
                    "safety_category": "virtualization",
                },
                "standard_version": "stress",
            },
        },
    ]


def category_definitions() -> list[dict[str, Any]]:
    return [
        {"id": "os", "label": "操作系统", "group": "基础设施", "order": 10},
        {"id": "db", "label": "数据库", "group": "数据服务", "order": 20},
        {"id": "network", "label": "网络设备", "group": "基础设施", "order": 30},
        {"id": "virtualization", "label": "虚拟化与私有云", "group": "平台", "order": 40},
    ]


def connector_groups() -> list[dict[str, Any]]:
    return [
        {"id": "ssh", "label": "SSH", "group": "原生命令", "order": 10, "tools": ["linux_execute_command"]},
        {"id": "winrm", "label": "WinRM", "group": "原生命令", "order": 20, "tools": ["winrm_execute_command"]},
        {"id": "database_native", "label": "数据库原生驱动", "group": "数据库", "order": 30, "tools": ["db_execute_query"]},
        {"id": "network_cli", "label": "网络 CLI", "group": "网络", "order": 40, "tools": ["network_cli_execute_command"]},
        {"id": "virtualization_api", "label": "虚拟化 API", "group": "平台", "order": 50, "tools": ["http_api_request"]},
    ]


def build_assets(count: int) -> list[dict[str, Any]]:
    blueprints = [
        ("linux", "ssh", 22, "root", "核心 Linux", "核心系统"),
        ("windows", "winrm", 5985, "administrator", "Windows Server", "核心系统"),
        ("oracle", "oracle", 1521, "oracle", "Oracle 19c", "数据库"),
        ("mysql", "mysql", 3306, "mysql", "MySQL", "数据库"),
        ("h3c_switch", "ssh", 22, "admin", "H3C Switch", "网络"),
        ("zstack", "http_api", 8080, "admin", "ZStack", "云平台"),
    ]
    assets: list[dict[str, Any]] = []
    for index in range(count):
        asset_type, protocol, port, user, label, group = blueprints[index % len(blueprints)]
        host = f"10.{index // 250}.{(index // 10) % 24}.{10 + (index % 220)}"
        assets.append(
            {
                "id": index + 1,
                "remark": f"{label}-{index + 1:03d}",
                "host": host,
                "port": port,
                "username": user,
                "asset_type": asset_type,
                "protocol": protocol,
                "agent_profile": "default",
                "extra_args": {
                    "category": "db" if asset_type in {"oracle", "mysql"} else "network" if asset_type == "h3c_switch" else "virtualization" if asset_type == "zstack" else "os",
                    "sub_type": asset_type,
                },
                "skills": [asset_type] if asset_type in {"oracle", "mysql"} else [],
                "tags": [group, f"机房-{(index % 4) + 1}", "压测样本"],
            }
        )
    return assets


def build_verification_status(assets: list[dict[str, Any]]) -> dict[str, Any]:
    protocols: dict[str, int] = {}
    categories: dict[str, int] = {}
    matrix = []
    for asset in assets:
        protocol = str(asset.get("protocol") or "unknown")
        category = str(asset.get("extra_args", {}).get("category") or "other")
        protocols[protocol] = protocols.get(protocol, 0) + 1
        categories[category] = categories.get(category, 0) + 1
        ready = asset["id"] % 11 != 0
        matrix.append(
            {
                "asset": {"id": asset["id"]},
                "coverage": {"total": 5, "supported": 5 if ready else 4, "gaps": 0 if ready else 1},
                "status": "ready" if ready else "needs_attention",
            }
        )
    return {
        "summary": {
            "asset_total": len(assets),
            "protocols": protocols,
            "categories": categories,
            "steps_total": len(assets) * 5,
            "gaps_total": sum(1 for item in matrix if item["status"] != "ready"),
            "ready_assets": sum(1 for item in matrix if item["status"] == "ready"),
            "needs_attention": sum(1 for item in matrix if item["status"] != "ready"),
        },
        "matrix": matrix,
    }


def build_sessions(count: int) -> dict[str, dict[str, Any]]:
    groups = ["核心系统", "数据库", "网络", "云平台", "中间件", "未分组"]
    asset_types = [("linux", "ssh", "root"), ("oracle", "oracle", "oracle"), ("mysql", "mysql", "mysql"), ("h3c_switch", "ssh", "admin")]
    sessions: dict[str, dict[str, Any]] = {}
    for index in range(count):
        asset_type, protocol, user = asset_types[index % len(asset_types)]
        sid = f"stress-sid-{index + 1:03d}"
        sessions[sid] = {
            "id": sid,
            "host": f"10.8.{index // 220}.{20 + (index % 220)}",
            "remark": f"压测会话-{index + 1:03d}",
            "isReadWriteMode": False,
            "skills": [asset_type] if asset_type in {"oracle", "mysql"} else [],
            "agentProfile": "default",
            "user": user,
            "asset_type": asset_type,
            "protocol": protocol,
            "extra_args": {"category": "db" if asset_type in {"oracle", "mysql"} else "network" if asset_type == "h3c_switch" else "os"},
            "heartbeatEnabled": index % 5 == 0,
            "tags": [groups[index % len(groups)], "压测会话"],
            "group_name": groups[index % len(groups)],
            "target_scope": "asset",
            "scope_value": None,
            "isStreaming": index % 13 == 0,
        }
    return sessions


def build_history(session_id: str, count: int) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    base_ts = int(time.time() * 1000) - count * 1000
    for index in range(count):
        if index % 2 == 0:
            messages.append(
                {
                    "role": "user",
                    "content": f"请对 {session_id} 执行只读巡检，并给出风险等级。样本消息 {index}.",
                    "_memory_id": 100000 + index,
                    "timestamp": base_ts + index * 1000,
                }
            )
            continue
        long_table = "\n".join(
            f"| 指标 {row} | normal | sample-{session_id}-{index}-{row} | 建议保持观察 |"
            for row in range(8)
        )
        messages.append(
            {
                "role": "assistant",
                "content": (
                    "### 巡检输出\n\n"
                    "关键健康状态：CPU、内存、连接、表空间或接口状态均为样本数据。\n\n"
                    "| 项目 | 状态 | 证据 | 建议 |\n|---|---|---|---|\n"
                    f"{long_table}\n\n"
                    "```sql\nSELECT tablespace_name, used_percent FROM dba_tablespace_usage_metrics;\n```\n\n"
                    "结论：这是压力烟测生成的长 Markdown，用于触发真实渲染路径。"
                ),
                "_memory_id": 100000 + index,
                "timestamp": base_ts + index * 1000,
                "exec_trace": [
                    {
                        "type": "tool_start",
                        "tool": "db_execute_query",
                        "args": "{\"sql\":\"SELECT ...\"}",
                        "status": "done",
                        "startedAt": base_ts + index * 1000,
                        "completedAt": base_ts + index * 1000 + 120,
                    },
                    {
                        "type": "tool_end",
                        "tool": "db_execute_query",
                        "result": "rows=8",
                        "status": "done",
                        "startedAt": base_ts + index * 1000,
                        "completedAt": base_ts + index * 1000 + 120,
                    },
                ],
            }
        )
    return messages


def build_session_tools_payload() -> dict[str, Any]:
    return {
        "toolsets": [
            {
                "id": "database",
                "label": "数据库工具",
                "enabled": True,
                "tools": [
                    {
                        "name": "db_execute_query",
                        "description": "执行只读 SQL 查询",
                        "toolset": "database",
                        "enabled": True,
                    }
                ],
            },
            {
                "id": "linux",
                "label": "Linux 工具",
                "enabled": True,
                "tools": [
                    {
                        "name": "linux_execute_command",
                        "description": "执行 Linux 只读命令",
                        "toolset": "linux",
                        "enabled": True,
                    }
                ],
            },
        ],
        "active_tools": ["db_execute_query", "linux_execute_command"],
        "active_tool_details": [],
        "context": {
            "target_scope": "asset",
            "asset_type": "linux",
            "protocol": "ssh",
            "host": "10.8.0.20",
            "port": 22,
        },
    }


def build_session_commands_payload() -> dict[str, Any]:
    command = {
        "id": "readonly-health",
        "label": "/health 只读健康检查",
        "description": "压测快捷指令样本",
        "category": "压测",
        "prompt": "请使用当前会话原生工具执行只读健康检查。",
        "prompt_template": "请使用当前会话原生工具执行只读健康检查。",
        "pinned": True,
    }
    return {
        "commands": [command],
        "builtin_commands": [command],
        "custom_commands": [],
        "context": {"asset_type": "linux", "protocol": "ssh"},
    }


def build_catalog_payload() -> dict[str, Any]:
    categories = category_definitions()
    return {
        "types": asset_type_definitions(),
        "categories": categories,
        "connector_groups": connector_groups(),
        "category_labels": {item["id"]: item["label"] for item in categories},
    }


def install_stress_routes(page: Page, *, asset_count: int, session_count: int, history_messages: int) -> None:
    assets = build_assets(asset_count)
    sessions = build_sessions(session_count)
    verification_status = build_verification_status(assets)
    catalog = build_catalog_payload()

    page.route(
        "**/api/v1/assets/saved",
        lambda route: fulfill_json(route, response({"assets": assets})),
    )
    page.route(
        "**/api/v1/verification/protocols/status",
        lambda route: fulfill_json(route, response(verification_status)),
    )
    page.route(
        "**/api/v1/assets/types/summary**",
        lambda route: fulfill_json(route, response(catalog)),
    )
    page.route(
        "**/api/v1/assets/types/form-catalog**",
        lambda route: fulfill_json(route, response(catalog)),
    )
    page.route(
        "**/api/v1/sessions/active",
        lambda route: fulfill_json(route, response({"sessions": sessions})),
    )
    page.route(
        "**/api/v1/sessions/poll_all",
        lambda route: fulfill_json(route, response({"updates": {}})),
    )

    def history(route: Route) -> None:
        match = re.search(r"/session/([^/]+)/history", route.request.url)
        session_id = match.group(1) if match else "stress-sid-001"
        fulfill_json(route, response({"messages": build_history(session_id, history_messages)}))

    page.route("**/api/v1/session/*/history**", history)
    page.route(
        "**/api/v1/session/*/tools",
        lambda route: fulfill_json(route, response(build_session_tools_payload())),
    )
    page.route(
        "**/api/v1/session/*/commands",
        lambda route: fulfill_json(route, response(build_session_commands_payload())),
    )


def install_long_task_probe(page: Page) -> None:
    page.add_init_script(
        """
        (() => {
          window.__opscorePerfLongTasks = [];
          if (!('PerformanceObserver' in window)) return;
          try {
            const observer = new PerformanceObserver((list) => {
              for (const entry of list.getEntries()) {
                window.__opscorePerfLongTasks.push({
                  name: entry.name,
                  startTime: entry.startTime,
                  duration: entry.duration,
                });
              }
            });
            observer.observe({ type: 'longtask', buffered: true });
          } catch (_) {}
        })();
        """
    )


def measure(name: str, action) -> PerfStep:
    started = time.perf_counter()
    action()
    return PerfStep(name=name, ms=(time.perf_counter() - started) * 1000)


def click_nav_button(page: Page, text: str) -> None:
    page.locator("button").filter(has_text=text).first.click(timeout=10_000)


def wait_for_text(page: Page, text: str, timeout: int = 20_000) -> None:
    page.get_by_text(text, exact=False).first.wait_for(timeout=timeout)


def wait_for_chat_composer(page: Page, timeout: int = 20_000) -> None:
    page.get_by_placeholder("输入消息", exact=False).first.wait_for(timeout=timeout)


def summarize_long_tasks(page: Page) -> dict[str, Any]:
    tasks = page.evaluate("window.__opscorePerfLongTasks || []")
    durations = [float(item.get("duration", 0)) for item in tasks]
    if not durations:
        return {"count": 0, "max_ms": 0, "p95_ms": 0, "total_ms": 0}
    return {
        "count": len(durations),
        "max_ms": round(max(durations), 1),
        "p95_ms": round(statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations), 1),
        "total_ms": round(sum(durations), 1),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    steps: list[PerfStep] = []
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        install_long_task_probe(page)
        install_stress_routes(
            page,
            asset_count=args.assets,
            session_count=args.sessions,
            history_messages=args.history_messages,
        )

        steps.append(
            measure(
                "initial_load",
                lambda: page.goto(args.url, wait_until="networkidle", timeout=60_000),
            )
        )
        wait_for_text(page, "会话")
        initial_body = page.locator("body").inner_text(timeout=10_000)

        steps.append(
            measure(
                "open_chat_view",
                lambda: (click_nav_button(page, "会话"), wait_for_chat_composer(page)),
            )
        )
        page.wait_for_timeout(400)
        wait_for_text(page, "AI 输出报告")
        chat_body = page.locator("body").inner_text(timeout=10_000)

        session_search = page.get_by_label("搜索会话")
        steps.append(
            measure(
                "session_search_fill",
                lambda: (session_search.fill("oracle"), page.wait_for_timeout(250)),
            )
        )

        steps.append(
            measure(
                "open_assets_view",
                lambda: (click_nav_button(page, "资产"), wait_for_text(page, "资产列表")),
            )
        )
        asset_search = page.get_by_placeholder("搜索资产、地址、账号、类型、主接入")
        steps.append(
            measure(
                "asset_search_fill",
                lambda: (asset_search.fill("oracle"), page.wait_for_timeout(250)),
            )
        )
        group_select = page.locator("select").filter(has_text="按资产组").first
        steps.append(
            measure(
                "asset_group_select_type",
                lambda: (group_select.select_option("type"), page.wait_for_timeout(250)),
            )
        )

        body = page.locator("body").inner_text(timeout=10_000)
        long_tasks = summarize_long_tasks(page)
        browser.close()

    step_payload = [{"name": step.name, "ms": round(step.ms, 1)} for step in steps]
    return {
        "url": args.url,
        "scenario": {
            "assets": args.assets,
            "sessions": args.sessions,
            "history_messages": args.history_messages,
            "viewport": {"width": args.width, "height": args.height},
        },
        "steps": step_payload,
        "long_tasks": long_tasks,
        "console_error_count": len(console_errors),
        "page_error_count": len(page_errors),
        "console_errors": console_errors[:5],
        "page_errors": page_errors[:5],
        "assertions": {
            "initial_shell_rendered": "会话" in initial_body and "资产" in initial_body,
            "assets_rendered": "资产列表" in body,
            "sessions_rendered": "会话组" in chat_body or "Session Ops" in chat_body,
            "history_rendered": "AI 输出报告" in chat_body,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a mocked OpsCore frontend stress smoke test.")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"OpsCore base URL, default: {DEFAULT_URL}")
    parser.add_argument("--assets", type=int, default=DEFAULT_ASSET_COUNT, help="Mocked saved asset count.")
    parser.add_argument("--sessions", type=int, default=DEFAULT_SESSION_COUNT, help="Mocked active session count.")
    parser.add_argument("--history-messages", type=int, default=DEFAULT_HISTORY_MESSAGES, help="Mocked history messages for selected sessions.")
    parser.add_argument("--width", type=int, default=1440, help="Browser viewport width.")
    parser.add_argument("--height", type=int, default=900, help="Browser viewport height.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run(args)
    except PlaywrightTimeoutError as exc:
        print(json.dumps({"status": "error", "error": f"timeout: {exc}"}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"status": "success", "result": result}, ensure_ascii=False, indent=2))
    if result["console_error_count"] or result["page_error_count"]:
        return 1
    if not all(result["assertions"].values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
