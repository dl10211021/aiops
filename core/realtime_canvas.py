from __future__ import annotations

import asyncio
import datetime
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from connections.ssh_manager import ssh_manager
from connections.winrm_manager import winrm_executor
from core.asset_protocols import SQL_PROTOCOLS


SUPPORTED_METRICS = {
    "cpu": "CPU 使用率",
    "memory": "内存使用率",
    "disk": "根分区/系统盘占用",
    "load": "系统负载",
    "top_process": "Top 进程",
    "network": "网络连接",
    "ports": "监听端口",
    "disk_io": "磁盘 IO",
    "service_status": "关键服务状态",
    "db_connections": "数据库连接数",
    "db_sessions": "数据库会话",
    "db_latency": "数据库响应延迟",
    "db_qps": "数据库吞吐",
    "db_cache_hit": "缓存命中率",
}

DEFAULT_INTERVAL_SECONDS = 5
DEFAULT_DURATION_SECONDS = 30 * 60
MAX_DURATION_SECONDS = 6 * 60 * 60
MAX_POINTS = 720
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REALTIME_CANVAS_STORE_PATH = PROJECT_ROOT / "realtime_canvases.json"

CANVAS_KINDS = {
    "metrics": "指标画板",
    "topology": "拓扑画板",
    "database_topology": "数据库拓扑",
    "inspection_report": "巡检报告",
    "incident_analysis": "故障分析",
    "risk_evidence": "风险证据链",
    "capacity_trend": "容量趋势",
    "service_dependency": "服务依赖",
    "fault_story": "故障说明",
    "custom_html": "自由 HTML",
}

CANVAS_MODES = {
    "realtime": "动态实时刷新",
    "window": "时间窗口采样",
    "static": "静态报告/快照",
}

DEFAULT_CANVAS_AI_PROMPT = """
你是 OpsCore Canvas Studio 生成器。请根据用户目标、资产类型、协议和探测结果，生成一个可审计、可导出、可删除的画板定义。

你必须输出严格 JSON，不要 Markdown。字段包括：
- kind: metrics/topology/database_topology/inspection_report/incident_analysis/risk_evidence/capacity_trend/service_dependency/fault_story/custom_html
- mode: realtime/window/static
- title
- canvas_spec: 安全画板配置，可包含 widgets、nodes、edges、timeline、risk_cards、theme。
- html: 仅静态画板可用，自包含 HTML Artifact；动态画板禁止生成 html。禁止外链脚本、禁止访问 localStorage/cookie、禁止请求任意后端接口。
- scripts: 仅动态画板可选，用于规划平台可执行的只读采集命令模板，例如 scripts.linux、scripts.windows。脚本不能常驻，不能写入业务目录，不能修改系统状态。
- data_schema: 采集结果标准字段说明。

语言要求：
- 所有可见页面内容必须使用简体中文，包括标题、模块名、指标解释、风险描述、建议动作、按钮文案、空状态、错误提示和证据说明。
- 保留必要的技术原文，例如 Linux 命令、SQL、进程名、协议名、字段名和产品名；除此之外不要输出英文报告。
- 如果用户没有明确要求英文，禁止生成英文 UI 或英文分析段落。

采集器规则：
- 所有采集必须是只读。
- AI 可以为动态画板编写只读采集脚本，但不直接执行；真实执行、超时、暂停和回收由 OpsCore 平台通过当前在线会话完成。
- 动态画板 mode=realtime/window：AI 先识别资产类型、协议和用户目标，再规划“采什么、脚本怎么采、怎么展示、阈值是什么”；平台持续追加真实 points/latest/tables/evidence，前端原生画布展示最近值、采样时间、时间窗口、趋势、异常点、证据和指标运行状态。动态禁止生成 HTML。
- 静态画板 mode=static：输入就是当前会话的只读巡检内容，目标是把 inspection/checks/evidence 转成中文 HTML 巡检/故障/风险分析报告。参考会话里的“只读巡检”指令，不要重新设计采集流程；真实巡检数据是唯一事实来源。
- 静态报告要清晰但不要堆砌提示词。根据已有证据自然组织资产概况、检查项、发现问题、风险等级、证据链、原因分析、建议动作和复查项；没有采集到的内容要写“未采集到/未覆盖”，不能当作事实。
- 动态画板 mode=realtime/window：主要展示指标数据、趋势曲线、状态刷新、动态拓扑、实时告警和采样时间线；可以有简短 AI 解释，但核心是持续变化的数据。
- 动态默认要覆盖更完整的持续监控指标，并且必须带时间维度：采样时间、最近值、时间窗口、趋势、异常点。系统资产默认关注 CPU、内存、磁盘容量、负载、Top 进程、网络连接/端口、磁盘 IO、关键服务状态；数据库资产默认关注连接数、活跃会话、等待/锁、QPS/吞吐、缓存命中率、慢查询摘要。
- 严禁伪造实时数据、随机曲线、模拟指标或看起来真实的假拓扑；除非用户明确要求演示样例，否则所有指标、节点、边、风险结论必须来自真实采集结果或明确标注为“待采集/未知”。
- 动态画板必须遵循真实数据闭环：AI 规划只读采集配置，平台已有会话/脚本负责真实采样、入库和刷新，前端原生画布负责渲染，不生成 HTML。
- 动态画板如果用户要监控 SQL，AI 不能执行 SQL，但可以在 canvas_spec.monitor_queries 中给出只读 SQL 监控配置：name、sql、chart、description。平台会校验并通过当前数据库会话执行。
- monitor_queries 示例：[{"name":"活跃会话","sql":"SELECT status, COUNT(*) AS count FROM v$session GROUP BY status","chart":"bar"}]。
- 如果采集失败，返回 status=error、error、evidence，不允许用假数据补齐。
- 每个关键结论都要能追踪 evidence：包括工具名、SQL/命令摘要、采集时间、资产会话、原始输出摘要或结构化结果。
- 不允许在目标资产留下不可回收的常驻脚本。
- 系统资产可以输出 scripts.linux 或 scripts.windows。脚本必须只读、短命令、一次执行即退出，不能常驻，不能写文件，不能修改系统状态。
- scripts.linux/scripts.windows 最好直接是字符串；如果输出数组，每项必须包含 command 字段。不要把 JSON、Markdown、解释文字混进脚本字符串。
- Linux 脚本必须通过一段 shell 输出标准 key=value：cpu=... memory=... disk=... load=... top_process=pid:name:cpu:mem; ports=proto:addr:proc; network=state:count; disk_io=... service_status=name:status;
- Windows 脚本必须通过一段 PowerShell 输出同样的 key=value 字段。
- 必须支持超时、暂停、到期回收。

动态画布配置契约：
- 动态模式不是 HTML 生成任务，不要输出 html、css、script、iframe。
- 动态模式应输出 scripts、canvas_spec、data_schema。canvas_spec 可包含 widgets、metrics、monitor_queries、monitor_commands、topology_plan、tables、thresholds、refresh_hint 等配置。不要输出 html。
- 如果没有可规划的采集项，要返回“等待真实采样/需要选择资产或指标”的中文说明，不要伪造 CPU、连接数、QPS 或拓扑。
- 静态 HTML 可以内嵌一次巡检的真实证据；动态展示由平台原生实时画布根据 points/latest/tables/evidence 渲染。

画板视觉要求：
- 画面要有 AIOps 指挥中心质感，避免普通表格堆叠。
- 平台采集到数据后，平台原生实时画布会基于真实 data_schema 和 points/latest 渲染看板；AI 只规划要展示哪些指标、表格、拓扑和阈值。
- 华丽效果由平台画布完成，AI 不要为动态模式输出视觉 HTML。
- 不要把画板固定理解成 CPU/内存/磁盘监控。画板可以是巡检报告、故障根因、风险证据链、容量趋势、网络拓扑、数据库拓扑、服务依赖、变更影响、应急处置说明或自由 HTML。
- 同一类画板要同时支持动态和静态：动态用于持续观测、曲线、状态灯、实时拓扑；静态用于审计报告、故障复盘、巡检结论、拓扑快照和离线导出。
- 拓扑图要突出主机、端口、服务、数据库、中间件、外联关系。
- Linux/Windows 网络拓扑可以生成赛博朋克风格节点图、流量链路、端口服务、进程关系和风险光效。
- 数据库拓扑必须作为一等场景处理：展示数据库实例、库/Schema、业务连接来源、客户端程序、会话状态、慢查询/锁等待、复制/主从/集群关系、容量和连接曲线。
- 数据库画板不要只生成普通表格；优先用“数据库核心节点 + 应用/主机连接节点 + 风险链路 + 时间曲线 + SQL/命令证据”的布局。
- 巡检报告画板要包含资产概况、检查项、发现问题、风险等级、证据、建议动作和复查状态。
- 故障分析画板要包含时间线、症状、影响范围、可能根因、证据链、处置建议、回滚/止血方案。
- 风险证据链画板要把命令输出、SQL 查询结果、配置片段和 AI 判断分层展示，能追踪每个结论来自哪条证据。
- 服务依赖画板要展示入口、进程、端口、数据库、中间件、外部 API、上游/下游和异常链路。
- 容量趋势画板要展示时间窗口、曲线、峰值、阈值、预测和扩容建议。
- 时间窗口模式要展示曲线图、采样时间段、异常点和 AI 解释。

数据库只读采集建议：
- SQL 数据库动态监控优先生成 canvas_spec.monitor_queries，由平台通过当前数据库会话执行只读 SQL，按协议选择 Oracle/MySQL/PostgreSQL/MSSQL/ClickHouse/Hive/IoTDB 等安全查询。数据库资产不要默认生成 CPU/内存/磁盘视图，除非用户明确要求主机资源。
- Oracle 可采样 v$instance、v$database、v$session、v$process、v$system_event；避免 DDL/DML。
- MySQL/MariaDB 可采样 SHOW PROCESSLIST、SHOW GLOBAL STATUS、information_schema 只读视图。
- PostgreSQL 可采样 pg_stat_activity、pg_stat_database、pg_locks、pg_stat_replication。
- MSSQL 可采样 sys.dm_exec_sessions、sys.dm_exec_requests、sys.databases、sys.dm_os_performance_counters。
- Redis 使用 redis_execute_command 读取 INFO、CLIENT LIST、DBSIZE、SLOWLOG GET。
- MongoDB 使用 mongodb_find 或平台只读接口读取集合样例、索引和状态摘要。
- Memcached 使用 memcached_execute_command 读取 stats。
- 如果用户要求数据库拓扑或数据库巡检，kind 必须使用 database_topology，除非明确要求纯指标或纯 HTML。
""".strip()

DEFAULT_PYTHON_COLLECTOR = """
def collect(ctx):
    \"\"\"OpsCore 托管 Python 采集器模板。
    ctx 由平台提供，负责按当前会话协议执行只读采集。
    返回结构必须能序列化为 JSON。
    \"\"\"
    # 示例：
    # - Linux/Windows: ctx.run("current_protocol", "collect_resource_snapshot")
    # - SQL 数据库: ctx.tool("db_execute_query", {"sql": "SELECT ..."})
    # - Redis: ctx.tool("redis_execute_command", {"command": "INFO"})
    # - MongoDB: ctx.tool("mongodb_find", {"collection": "...", "filter": {}})
    raw = ctx.run("current_protocol", "collect_resource_snapshot")
    return {
        "metrics": {},
        "series": {},
        "topology": {"nodes": [], "edges": []},
        "database": {
            "instances": [],
            "schemas": [],
            "sessions": [],
            "slow_queries": [],
            "replication": [],
            "capacity": {},
        },
        "events": [],
        "raw": raw,
    }
""".strip()


def _now_iso() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip().replace("%", "")
        if not text:
            return default
        return round(float(text), 2)
    except Exception:
        return default


def _clamp_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = default
    return max(min_value, min(max_value, number))


def _parse_key_values(output: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in re.finditer(r"(\w+)=([^\n]+?)(?=\s+\w+=|$)", str(output or "").strip()):
        result[match.group(1)] = match.group(2).strip()
    return result


def _parse_top_process(raw: str) -> list[dict[str, Any]]:
    rows = []
    for item in str(raw or "").split(";"):
        parts = item.strip().split(":", 3)
        if len(parts) != 4:
            continue
        pid, name, cpu, mem = parts
        rows.append(
            {
                "pid": pid,
                "name": name,
                "cpu": _safe_float(cpu),
                "memory": _safe_float(mem),
            }
        )
    return rows[:8]


def _parse_semicolon_pairs(raw: str) -> list[dict[str, str]]:
    rows = []
    for item in str(raw or "").split(";"):
        text = item.strip()
        if not text:
            continue
        parts = text.split(":", 2)
        rows.append(
            {
                "name": parts[0] if parts else text,
                "value": parts[1] if len(parts) > 1 else "",
                "extra": parts[2] if len(parts) > 2 else "",
            }
        )
    return rows[:20]


def _metric_status(value: float, warn: float | None = None, critical: float | None = None) -> str:
    if critical is not None and value >= critical:
        return "critical"
    if warn is not None and value >= warn:
        return "warning"
    return "ok"


def _metric_thresholds(key: str) -> dict[str, float]:
    defaults = {
        "cpu": {"warning": 70, "critical": 90},
        "memory": {"warning": 75, "critical": 90},
        "disk": {"warning": 80, "critical": 92},
        "load": {"warning": 4, "critical": 8},
        "ports_count": {"warning": 80, "critical": 160},
        "network_states": {"warning": 500, "critical": 1200},
        "service_failures": {"warning": 1, "critical": 3},
        "table_rows": {"warning": 200, "critical": 800},
    }
    return defaults.get(key, {})


def _metric_label(key: str) -> str:
    labels = {
        "cpu": "CPU 使用率",
        "memory": "内存使用率",
        "disk": "磁盘使用率",
        "load": "系统负载",
        "top_process_count": "Top 进程数量",
        "ports_count": "监听端口数量",
        "network_states": "网络状态数量",
        "service_failures": "异常服务数量",
        "table_count": "数据表数量",
        "table_rows": "表格行数",
    }
    return labels.get(key, key)


def _metric_unit(key: str) -> str:
    if key in {"cpu", "memory", "disk"}:
        return "%"
    if key == "load":
        return ""
    if key.endswith("_ms"):
        return "ms"
    return "count"


def _extract_metric_snapshot(point: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(point, dict):
        return []
    time_value = str(point.get("time") or _now_iso())
    source = "OpsCore 动态采样"
    evidence = point.get("evidence")
    if isinstance(evidence, list) and evidence and isinstance(evidence[0], dict):
        source = str(evidence[0].get("source") or source)

    metrics: list[dict[str, Any]] = []

    def add_metric(key: str, value: Any, label: str | None = None, unit: str | None = None) -> None:
        try:
            number = round(float(value), 4)
        except Exception:
            return
        thresholds = _metric_thresholds(key)
        metrics.append(
            {
                "key": key,
                "label": label or _metric_label(key),
                "value": number,
                "unit": unit if unit is not None else _metric_unit(key),
                "status": _metric_status(number, thresholds.get("warning"), thresholds.get("critical")),
                "thresholds": thresholds,
                "time": time_value,
                "source": source,
            }
        )

    for key in ("cpu", "memory", "disk", "load"):
        add_metric(key, point.get(key))

    for key, field in (
        ("top_process_count", "top_process"),
        ("ports_count", "ports"),
        ("network_states", "network"),
        ("service_failures", "service_status"),
    ):
        value = point.get(field)
        if isinstance(value, list):
            add_metric(key, len(value))

    tables = point.get("tables")
    if isinstance(tables, list):
        add_metric("table_count", len(tables))
        total_rows = 0
        for table in tables:
            if isinstance(table, dict) and isinstance(table.get("rows"), list):
                total_rows += len(table["rows"])
        add_metric("table_rows", total_rows)

    data = point.get("data")
    if isinstance(data, dict):
        for key, value in list(data.items())[:24]:
            safe_key = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(key))[:80]
            add_metric(f"data.{safe_key}", value, str(key), "")

    return metrics


def _build_metric_series(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for point in points[-MAX_POINTS:]:
        for metric in _extract_metric_snapshot(point):
            key = str(metric.get("key") or "")
            if not key:
                continue
            bucket = grouped.setdefault(
                key,
                {
                    "key": key,
                    "label": metric.get("label") or key,
                    "unit": metric.get("unit") or "",
                    "thresholds": metric.get("thresholds") or {},
                    "source": metric.get("source") or "OpsCore 动态采样",
                    "points": [],
                },
            )
            bucket["points"].append(
                {
                    "time": metric.get("time"),
                    "value": metric.get("value"),
                    "status": metric.get("status"),
                }
            )

    series: list[dict[str, Any]] = []
    for bucket in grouped.values():
        values = [float(p["value"]) for p in bucket["points"] if p.get("value") is not None]
        if not values:
            continue
        current = values[-1]
        bucket["current"] = round(current, 4)
        bucket["min"] = round(min(values), 4)
        bucket["max"] = round(max(values), 4)
        bucket["avg"] = round(sum(values) / len(values), 4)
        bucket["samples"] = len(values)
        thresholds = bucket.get("thresholds") if isinstance(bucket.get("thresholds"), dict) else {}
        bucket["status"] = _metric_status(current, thresholds.get("warning"), thresholds.get("critical"))
        series.append(bucket)
    return sorted(series, key=lambda item: (0 if item["key"] in {"cpu", "memory", "disk", "load"} else 1, item["key"]))


def _rows_from_db_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("rows", "data", "result", "records"):
        value = result.get(key)
        if isinstance(value, list):
            return [row if isinstance(row, dict) else {"value": row} for row in value[:200]]
    return []


def _numeric_summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, float]:
    summary: dict[str, float] = {}
    if not rows:
        return summary
    first = rows[0]
    for key, value in first.items():
        try:
            summary[str(key)] = round(float(value), 4)
        except Exception:
            continue
    return summary


def _default_sql_monitor_queries(db_type: str) -> list[dict[str, str]]:
    key = str(db_type or "").lower()
    if key == "mysql":
        return [
            {"name": "连通性", "sql": "SELECT 1 AS value", "chart": "stat", "description": "数据库连通性"},
            {"name": "线程状态", "sql": "SHOW GLOBAL STATUS LIKE 'Threads_%'", "chart": "table", "description": "连接线程状态"},
            {"name": "运行时间", "sql": "SHOW GLOBAL STATUS LIKE 'Uptime'", "chart": "stat", "description": "实例运行时间"},
            {"name": "数据库容量概览", "sql": "SELECT table_schema, COUNT(*) AS table_count FROM information_schema.tables GROUP BY table_schema", "chart": "table", "description": "Schema 表数量"},
        ]
    if key == "oracle":
        return [
            {"name": "实例状态", "sql": "SELECT instance_name, status, database_status FROM v$instance", "chart": "table", "description": "Oracle 实例状态"},
            {"name": "会话状态", "sql": "SELECT status, COUNT(*) AS count FROM v$session GROUP BY status", "chart": "bar", "description": "会话状态分布"},
            {"name": "锁等待", "sql": "SELECT blocking_session, sid, event, seconds_in_wait FROM v$session WHERE blocking_session IS NOT NULL", "chart": "table", "description": "锁等待会话"},
        ]
    if key in {"postgresql", "pg"}:
        return [
            {"name": "数据库连接", "sql": "SELECT datname, numbackends FROM pg_stat_database", "chart": "bar", "description": "数据库连接数"},
            {"name": "会话状态", "sql": "SELECT state, COUNT(*) AS count FROM pg_stat_activity GROUP BY state", "chart": "bar", "description": "会话状态分布"},
            {"name": "锁等待", "sql": "SELECT mode, granted, COUNT(*) AS count FROM pg_locks GROUP BY mode, granted", "chart": "table", "description": "锁状态"},
        ]
    if key in {"mssql", "sqlserver", "sql_server"}:
        return [
            {"name": "会话数", "sql": "SELECT status, COUNT(*) AS count FROM sys.dm_exec_sessions GROUP BY status", "chart": "bar", "description": "会话状态分布"},
            {"name": "数据库状态", "sql": "SELECT name, state_desc FROM sys.databases", "chart": "table", "description": "数据库状态"},
        ]
    return [{"name": "连通性", "sql": "SELECT 1 AS value", "chart": "stat", "description": "数据库连通性"}]


def _network_monitor_commands(asset_type: str) -> list[dict[str, str]]:
    return [
        {"name": "接口摘要", "command": "show ip interface brief", "description": "接口 IP 与状态"},
        {"name": "接口状态", "command": "show interfaces status", "description": "交换机接口状态"},
        {"name": "邻居信息", "command": "show cdp neighbors", "description": "邻居拓扑信息"},
        {"name": "路由摘要", "command": "show ip route summary", "description": "路由表摘要"},
    ]


def _linux_metrics_command() -> str:
    return r"""
CPU=$(vmstat 1 2 2>/dev/null | tail -1 | awk '{ if ($15 ~ /^[0-9.]+$/) printf "%.1f", 100-$15; else printf "0" }')
MEM=$(free 2>/dev/null | awk '/Mem:/ { if ($2 > 0) printf "%.1f", $3*100/$2; else printf "0" }')
DISK=$(df -P / 2>/dev/null | awk 'NR==2 { gsub("%","",$5); print $5 }')
LOAD=$(awk '{print $1}' /proc/loadavg 2>/dev/null)
TOP=$(ps -eo pid,comm,%cpu,%mem --sort=-%cpu 2>/dev/null | head -6 | tail -5 | awk '{printf "%s:%s:%s:%s;",$1,$2,$3,$4}')
PORTS=$(ss -lntup 2>/dev/null | awk 'NR>1 {print $1":"$5":"$7}' | head -10 | tr '\n' ';')
NET=$(ss -ant 2>/dev/null | awk 'NR>1 {state[$1]++} END {for (s in state) printf "%s:%s;",s,state[s]}')
DISKIO=$(awk 'NR>2 {r+=$6; w+=$10} END {printf "read=%s write=%s", r+0, w+0}' /proc/diskstats 2>/dev/null)
SERVICES=$(systemctl --failed --no-legend --plain 2>/dev/null | head -8 | awk '{printf "%s:%s;",$1,$2}')
FILESYSTEMS=$(df -hP 2>/dev/null | awk 'NR>1 && $1 !~ /tmpfs|devtmpfs/ {printf "%s:%s/%s:%s;",$6,$3,$2,$5}' | head -c 2000)
DOCKER=$(docker ps --format '{{.Names}}|{{.Status}}|{{.Ports}}|{{.Image}}' 2>/dev/null | head -8 | awk -F'|' '{gsub(":","_",$0); printf "%s:%s:%s;",$1,$2,$4}')
LOGINS=$(last -n 8 2>/dev/null | grep -v 'wtmp begins' | awk '{printf "%s:%s:%s;",$1,$3,$4" "$5" "$6" "$7}' | head -8)
MEMTOP=$(ps -eo pid,comm,%cpu,%mem --sort=-%mem 2>/dev/null | head -6 | tail -5 | awk '{printf "%s:%s:%s:%s;",$1,$2,$3,$4}')
ROUTES=$(ip route 2>/dev/null | head -8 | awk '{gsub(":","_",$0); printf "route:%s;",$0}')
IFACES=$(ip -br addr 2>/dev/null | head -8 | awk '{gsub(":","_",$0); printf "%s:%s:%s;",$1,$2,$3}')
AUTHFAIL=$(lastb -n 8 2>/dev/null | grep -v 'btmp begins' | awk '{printf "%s:%s:%s;",$1,$3,$4" "$5" "$6" "$7}' | head -8)
DOCKERDF=$(docker system df 2>/dev/null | tail -n +2 | head -8 | awk '{printf "%s:%s:%s;",$1,$2,$4}')
echo "cpu=${CPU:-0} memory=${MEM:-0} disk=${DISK:-0} load=${LOAD:-0} top_process=${TOP} ports=${PORTS} network=${NET} disk_io=${DISKIO} service_status=${SERVICES} filesystems=${FILESYSTEMS} docker=${DOCKER} logins=${LOGINS} mem_process=${MEMTOP} routes=${ROUTES} interfaces=${IFACES} auth_failures=${AUTHFAIL} docker_df=${DOCKERDF}"
""".strip()


def _windows_metrics_command() -> str:
    return r"""
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples.CookedValue
$os = Get-CimInstance Win32_OperatingSystem
$mem = 0
if ($os.TotalVisibleMemorySize -gt 0) { $mem = (($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) * 100 / $os.TotalVisibleMemorySize) }
$diskObj = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object -First 1
$disk = 0
if ($diskObj -and $diskObj.Size -gt 0) { $disk = (($diskObj.Size - $diskObj.FreeSpace) * 100 / $diskObj.Size) }
$top = Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 | ForEach-Object { "$($_.Id):$($_.ProcessName):$([math]::Round(($_.CPU -as [double]),2)):0" }
$ports = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object -First 10 | ForEach-Object { "$($_.LocalAddress):$($_.LocalPort):$($_.OwningProcess)" }
$net = Get-NetTCPConnection -ErrorAction SilentlyContinue | Group-Object State | ForEach-Object { "$($_.Name):$($_.Count)" }
$services = Get-Service | Where-Object { $_.Status -ne 'Running' } | Select-Object -First 8 | ForEach-Object { "$($_.Name):$($_.Status)" }
Write-Output ("cpu={0:N1} memory={1:N1} disk={2:N1} load=0 top_process={3} ports={4} network={5} disk_io=unavailable service_status={6}" -f $cpu,$mem,$disk,($top -join ';'),($ports -join ';'),($net -join ';'),($services -join ';'))
""".strip()


def _escape_html(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _extract_json_object(text: str) -> dict[str, Any] | None:
    candidate = str(text or "").strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?", "", candidate, flags=re.I).strip()
        candidate = re.sub(r"```$", "", candidate).strip()
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(candidate[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _coerce_script_command(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("command", "script", "code"):
            command = value.get(key)
            if isinstance(command, str) and command.strip():
                return command.strip()
        return ""
    if isinstance(value, list):
        commands: list[str] = []
        for item in value[:8]:
            command = _coerce_script_command(item)
            if command:
                commands.append(command)
        return "\n".join(commands).strip()
    return ""


def _looks_like_inspection_report(text: str) -> bool:
    content = str(text or "")
    if len(content) < 900:
        return False
    keywords = ("只读巡检", "巡检报告", "关键健康", "异常项", "风险等级", "建议下一步", "证据", "健康状态")
    return sum(1 for keyword in keywords if keyword in content) >= 3


def _latest_session_inspection_report(session_id: str) -> dict[str, Any] | None:
    try:
        from core import memory as memory_module

        messages = memory_module.memory_db.get_messages(session_id, for_ui=True)
    except Exception:
        return None
    latest_user = ""
    for msg in reversed(messages[-40:]):
        if msg.get("role") == "user":
            latest_user = str(msg.get("content") or "")
            break
    for msg in reversed(messages[-40:]):
        if msg.get("role") != "assistant":
            continue
        content = str(msg.get("content") or "").strip()
        if not _looks_like_inspection_report(content):
            continue
        return {
            "content": content[:80000],
            "message_id": msg.get("id"),
            "timestamp": msg.get("timestamp"),
            "matched_user_goal": latest_user[:2000],
        }
    return None


def _markdownish_report_html(item: dict[str, Any], report: dict[str, Any]) -> str:
    content = str(report.get("content") or "")
    session = item.get("session") if isinstance(item.get("session"), dict) else {}
    escaped = _escape_html(content)
    escaped = re.sub(r"^### (.+)$", r"<h3>\1</h3>", escaped, flags=re.M)
    escaped = re.sub(r"^## (.+)$", r"<h2>\1</h2>", escaped, flags=re.M)
    escaped = re.sub(r"^# (.+)$", r"<h1>\1</h1>", escaped, flags=re.M)
    escaped = escaped.replace("\n", "<br />\n")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(item.get("title") or "OpsCore 巡检报告")}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#050b16; --panel:#0b1a2e; --line:#20e3d2; --gold:#f7b955; --text:#e7f6ff; --muted:#8aa4c7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Segoe UI","Microsoft YaHei",sans-serif; color:var(--text); background:radial-gradient(circle at 15% 8%,rgba(32,227,210,.18),transparent 28%),radial-gradient(circle at 88% 18%,rgba(247,185,85,.16),transparent 30%),linear-gradient(135deg,#06111f,#020712 72%); }}
    main {{ padding:30px; }}
    .hero,.report {{ border:1px solid rgba(32,227,210,.28); border-radius:26px; background:rgba(11,26,46,.76); box-shadow:0 28px 90px rgba(0,0,0,.38); }}
    .hero {{ padding:24px; margin-bottom:18px; }}
    .eyebrow {{ color:var(--line); font-size:12px; letter-spacing:.22em; text-transform:uppercase; }}
    h1 {{ margin:8px 0 10px; font-size:34px; }}
    h2 {{ margin:28px 0 12px; color:var(--line); }}
    h3 {{ margin:20px 0 8px; color:var(--gold); }}
    .muted {{ color:var(--muted); line-height:1.8; }}
    .meta {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:16px; }}
    .card {{ border:1px solid rgba(138,164,199,.18); border-radius:16px; padding:14px; background:rgba(2,7,17,.42); }}
    .label {{ color:var(--muted); font-size:12px; }}
    .value {{ margin-top:6px; color:var(--line); font-weight:900; font-size:18px; word-break:break-all; }}
    .report {{ padding:26px; line-height:1.86; font-size:15px; }}
    table {{ width:100%; border-collapse:collapse; margin:12px 0; }}
    th,td {{ border-top:1px solid rgba(138,164,199,.18); padding:10px; text-align:left; }}
    code,pre {{ color:#bdefff; white-space:pre-wrap; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">OpsCore 静态 HTML · 会话巡检报告原文增强版</div>
      <h1>{_escape_html(item.get("title") or "资产完整只读巡检报告")}</h1>
      <p class="muted">本报告优先采用当前会话中已经生成的完整 AI 巡检报告，再包装为可导出的 HTML，保留会话报告里的大量结论、表格、风险和建议。</p>
      <div class="meta">
        <div class="card"><div class="label">资产</div><div class="value">{_escape_html(session.get("host") or item.get("session_id"))}</div></div>
        <div class="card"><div class="label">协议</div><div class="value">{_escape_html(session.get("protocol") or "")}</div></div>
        <div class="card"><div class="label">资产类型</div><div class="value">{_escape_html(session.get("asset_type") or "")}</div></div>
        <div class="card"><div class="label">报告长度</div><div class="value">{len(content)} 字符</div></div>
      </div>
    </section>
    <article class="report">{escaped}</article>
  </main>
</body>
</html>"""


def _extract_html_field_text(text: str) -> str:
    candidate = str(text or "")
    match = re.search(r'"html"\s*:\s*"', candidate)
    if not match:
        return ""
    index = match.end()
    escaped = False
    chars: list[str] = []
    while index < len(candidate):
        char = candidate[index]
        if escaped:
            chars.append("\\" + char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            break
        else:
            chars.append(char)
        index += 1
    raw = "".join(chars)
    try:
        return json.loads(f'"{raw}"')
    except Exception:
        return raw.replace("\\n", "\n").replace('\\"', '"').replace("\\/", "/")


def _coerce_canvas_html(value: Any) -> str:
    html = str(value or "").strip()
    if not html:
        return ""
    if html.lstrip().startswith("{"):
        parsed = _extract_json_object(html)
        if parsed and parsed.get("html"):
            return str(parsed.get("html") or "")
        extracted = _extract_html_field_text(html)
        if extracted:
            return extracted
    return html


def _canvas_runtime_payload(item: dict[str, Any]) -> dict[str, Any]:
    points = item.get("points") if isinstance(item.get("points"), list) else []
    latest = item.get("latest") if isinstance(item.get("latest"), dict) else (points[-1] if points else None)
    return {
        "session": item.get("session") or {},
        "status": item.get("status"),
        "latest": latest or {},
        "points": points[-MAX_POINTS:],
        "topology": item.get("topology") or {},
        "events": item.get("events") or [],
        "evidence": item.get("evidence") or [],
        "inspection": item.get("inspection") or {},
        "last_error": item.get("last_error") or "",
        "updated_at": item.get("generated_at") or item.get("last_collect_at") or item.get("updated_at") or item.get("created_at") or "",
    }


def _inject_canvas_payload(html: str, item: dict[str, Any]) -> str:
    html = str(html or "")
    if not html.strip():
        return html
    payload_json = json.dumps(_canvas_runtime_payload(item), ensure_ascii=False, default=str)
    script = f"""
<script>
window.__OPSCORE_CANVAS_PAYLOAD__ = {payload_json};
try {{
  if (typeof window.renderOpsCoreCanvas === 'function') {{
    window.renderOpsCoreCanvas(window.__OPSCORE_CANVAS_PAYLOAD__);
  }}
}} catch (error) {{
  console.error('OpsCore canvas payload render failed', error);
}}
</script>
"""
    if "</body>" in html.lower():
        return re.sub(r"</body>", script + "</body>", html, count=1, flags=re.I)
    return html + script


def _pending_canvas_html(item: dict[str, Any]) -> str:
    goal = ""
    spec = item.get("canvas_spec")
    if isinstance(spec, dict):
        goal = str(spec.get("goal") or "")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(item.get("title") or "AI 画板生成中")}</title>
  <style>
    :root {{ color-scheme: dark; --cyan:#20e3d2; --blue:#6ea8ff; --text:#e7f6ff; --muted:#8aa4c7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; display:grid; place-items:center; font-family:"Segoe UI","Microsoft YaHei",sans-serif; color:var(--text); background:
      radial-gradient(circle at 20% 15%, rgba(32,227,210,.22), transparent 28%),
      radial-gradient(circle at 80% 20%, rgba(110,168,255,.2), transparent 30%),
      linear-gradient(135deg,#06111f,#020711 70%); }}
    .card {{ width:min(760px, calc(100vw - 36px)); border:1px solid rgba(32,227,210,.35); border-radius:28px; padding:32px; background:rgba(7,17,31,.72); box-shadow:0 30px 100px rgba(0,0,0,.48), inset 0 0 40px rgba(32,227,210,.06); }}
    .orb {{ width:74px; height:74px; border-radius:22px; border:1px solid rgba(32,227,210,.55); background:linear-gradient(135deg,rgba(32,227,210,.3),rgba(110,168,255,.14)); box-shadow:0 0 52px rgba(32,227,210,.3); animation:pulse 1.6s ease-in-out infinite; }}
    .eyebrow {{ margin-top:22px; color:var(--cyan); font-size:12px; letter-spacing:.24em; text-transform:uppercase; }}
    h1 {{ margin:10px 0 8px; font-size:34px; }}
    p {{ margin:0; color:var(--muted); line-height:1.8; }}
    .goal {{ margin-top:18px; padding:16px; border:1px solid rgba(138,164,199,.18); border-radius:18px; background:rgba(2,7,17,.55); }}
    @keyframes pulse {{ 0%,100% {{ transform:scale(1); opacity:.8; }} 50% {{ transform:scale(1.08); opacity:1; }} }}
  </style>
</head>
<body>
  <main class="card">
    <div class="orb"></div>
    <div class="eyebrow">OpsCore AI Canvas</div>
    <h1>AI 正在生成画板</h1>
    <p>辅助模型正在根据当前资产会话生成 HTML 看板、采集器和数据结构。生成完成后这里会自动刷新为真实结果。</p>
    <div class="goal"><p><strong>目标：</strong>{_escape_html(goal or "未填写")}</p></div>
  </main>
</body>
</html>"""


def _error_canvas_html(item: dict[str, Any], error: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(item.get("title") or "AI 画板生成失败")}</title>
  <style>
    :root {{ color-scheme: dark; --danger:#ff5c8a; --text:#f6eafa; --muted:#b39ab5; }}
    body {{ margin:0; min-height:100vh; display:grid; place-items:center; font-family:"Segoe UI","Microsoft YaHei",sans-serif; color:var(--text); background:radial-gradient(circle at 20% 10%,rgba(255,92,138,.18),transparent 30%),linear-gradient(135deg,#160712,#05030a); }}
    .card {{ width:min(760px, calc(100vw - 36px)); border:1px solid rgba(255,92,138,.36); border-radius:26px; padding:28px; background:rgba(24,8,18,.76); box-shadow:0 30px 90px rgba(0,0,0,.45); }}
    .eyebrow {{ color:var(--danger); font-size:12px; letter-spacing:.22em; text-transform:uppercase; }}
    h1 {{ margin:10px 0; }}
    pre {{ white-space:pre-wrap; color:var(--muted); background:rgba(0,0,0,.25); border-radius:16px; padding:16px; }}
  </style>
</head>
<body>
  <main class="card">
    <div class="eyebrow">OpsCore AI Canvas</div>
    <h1>AI 画板生成失败</h1>
    <pre>{_escape_html(error)}</pre>
  </main>
</body>
</html>"""


def _fallback_ai_canvas_html(item: dict[str, Any], payload: dict[str, Any], ai_text: str = "") -> str:
    safe_payload = json.dumps(payload, ensure_ascii=False, default=str)
    goal = ""
    spec = item.get("canvas_spec")
    if isinstance(spec, dict):
        goal = str(spec.get("goal") or "")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(item.get("title") or "OpsCore AI Canvas")}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#05101d; --panel:#0b1a2e; --cyan:#20e3d2; --blue:#77a7ff; --text:#e9f8ff; --muted:#8aa4c7; --warn:#f7b955; --danger:#ff5c8a; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; font-family:"Segoe UI","Microsoft YaHei",sans-serif; color:var(--text); background:
      radial-gradient(circle at 14% 10%, rgba(32,227,210,.24), transparent 28%),
      radial-gradient(circle at 82% 18%, rgba(119,167,255,.2), transparent 32%),
      linear-gradient(135deg,#06111f,#020712 72%); }}
    .shell {{ padding:28px; }}
    .hero {{ border:1px solid rgba(32,227,210,.32); border-radius:28px; padding:26px; background:rgba(11,26,46,.72); box-shadow:0 28px 100px rgba(0,0,0,.45); }}
    .eyebrow {{ color:var(--cyan); font-size:12px; letter-spacing:.24em; text-transform:uppercase; }}
    h1 {{ margin:10px 0 6px; font-size:34px; }}
    .muted {{ color:var(--muted); line-height:1.75; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin-top:18px; }}
    .card {{ border:1px solid rgba(138,164,199,.18); border-radius:18px; padding:16px; background:rgba(2,7,17,.48); }}
    .label {{ color:var(--muted); font-size:12px; }}
    .value {{ margin-top:6px; color:var(--cyan); font-size:30px; font-weight:900; font-family:Consolas,monospace; }}
    .status-ok {{ color:var(--cyan); }}
    .status-error {{ color:var(--danger); }}
    pre {{ max-height:280px; overflow:auto; white-space:pre-wrap; color:#b9c9e8; background:rgba(0,0,0,.28); border-radius:16px; padding:16px; }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">OpsCore AI Canvas · Real Data</div>
      <h1>{_escape_html(item.get("title") or "AI 画板")}</h1>
      <p class="muted">{_escape_html(goal or "基于当前在线会话的真实采集结果生成。")}</p>
      <div class="grid">
        <div class="card"><div class="label">采集状态</div><div id="status" class="value">--</div></div>
        <div class="card"><div class="label">采样点</div><div id="count" class="value">0</div></div>
        <div class="card"><div class="label">最近采集</div><div id="time" class="value" style="font-size:18px">--</div></div>
      </div>
      <div class="grid">
        <div class="card"><div class="label">CPU</div><div id="cpu" class="value">--</div></div>
        <div class="card"><div class="label">内存</div><div id="memory" class="value">--</div></div>
        <div class="card"><div class="label">磁盘/容量</div><div id="disk" class="value">--</div></div>
      </div>
      <details class="card" style="margin-top:18px" open><summary>真实采集 Payload</summary><pre id="payload"></pre></details>
      {('<details class="card" style="margin-top:14px"><summary>AI 原始输出</summary><pre>' + _escape_html(ai_text[:12000]) + '</pre></details>') if ai_text else ''}
    </section>
  </main>
  <script>
    const initialPayload = {safe_payload};
    function renderOpsCoreCanvas(payload) {{
      const latest = payload.latest || (payload.points && payload.points[payload.points.length - 1]) || {{}};
      const points = payload.points || [];
      const status = latest.status || payload.status || 'unknown';
      document.getElementById('status').textContent = status;
      document.getElementById('status').className = 'value ' + (status === 'ok' ? 'status-ok' : status === 'error' ? 'status-error' : '');
      document.getElementById('count').textContent = points.length;
      document.getElementById('time').textContent = latest.time || '--';
      document.getElementById('cpu').textContent = Number.isFinite(Number(latest.cpu)) ? latest.cpu + '%' : '--';
      document.getElementById('memory').textContent = Number.isFinite(Number(latest.memory)) ? latest.memory + '%' : '--';
      document.getElementById('disk').textContent = Number.isFinite(Number(latest.disk)) ? latest.disk + '%' : '--';
      document.getElementById('payload').textContent = JSON.stringify(payload, null, 2);
    }}
    window.renderOpsCoreCanvas = renderOpsCoreCanvas;
    renderOpsCoreCanvas(initialPayload);
  </script>
</body>
</html>"""


def _fallback_static_report_html(item: dict[str, Any], payload: dict[str, Any], error: str = "") -> str:
    inspection = payload.get("inspection") if isinstance(payload.get("inspection"), dict) else {}
    checks = inspection.get("checks") if isinstance(inspection.get("checks"), list) else []
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    failed = [check for check in checks if isinstance(check, dict) and check.get("status") not in {"success", "ok"}]
    rows = []
    for check in checks[:24]:
        if not isinstance(check, dict):
            continue
        rows.append(
            f"<tr><td>{_escape_html(check.get('title') or check.get('name') or '检查项')}</td>"
            f"<td>{_escape_html(check.get('status') or '')}</td>"
            f"<td><code>{_escape_html(check.get('command') or '')}</code></td>"
            f"<td>{_escape_html(str(check.get('output') or '')[:900])}</td></tr>"
        )
    evidence_items = "".join(
        f"<li><strong>{_escape_html(item.get('source') if isinstance(item, dict) else '证据')}</strong>："
        f"{_escape_html((item.get('summary') if isinstance(item, dict) else str(item)) or '')}</li>"
        for item in evidence[:8]
    )
    risk = "高风险" if len(failed) >= 3 else ("关注" if failed else "正常")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(item.get("title") or "OpsCore 巡检报告")}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#06111f; --panel:#0c1b30; --line:#20e3d2; --text:#e7f6ff; --muted:#8aa4c7; --warn:#f7b955; --danger:#ff5c8a; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Segoe UI","Microsoft YaHei",sans-serif; color:var(--text); background:radial-gradient(circle at 18% 10%,rgba(32,227,210,.18),transparent 28%),linear-gradient(135deg,#06111f,#020712 75%); }}
    main {{ padding:28px; }}
    section {{ margin-top:16px; border:1px solid rgba(138,164,199,.18); border-radius:20px; background:rgba(12,27,48,.75); padding:18px; }}
    .hero {{ border-color:rgba(32,227,210,.35); box-shadow:0 28px 90px rgba(0,0,0,.38); }}
    .eyebrow {{ color:var(--line); font-size:12px; letter-spacing:.22em; text-transform:uppercase; }}
    h1 {{ margin:8px 0; font-size:32px; }}
    h2 {{ margin:0 0 12px; }}
    .muted {{ color:var(--muted); line-height:1.75; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .card {{ border:1px solid rgba(32,227,210,.16); border-radius:16px; padding:14px; background:rgba(2,7,17,.42); }}
    .value {{ color:var(--line); font-size:24px; font-weight:900; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ border-top:1px solid rgba(138,164,199,.18); padding:10px; vertical-align:top; text-align:left; }}
    th {{ color:var(--muted); }}
    code,pre {{ color:#bdefff; white-space:pre-wrap; }}
    li {{ margin:8px 0; color:var(--muted); }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">OpsCore 静态巡检 · AI 生成失败证据页</div>
      <h1>{_escape_html(item.get("title") or "资产巡检证据页")}</h1>
      <p class="muted">本页不是最终静态画板报告。AI 未能在限定时间内完成 HTML 分析报告生成，平台仅保留本次完整只读巡检证据，便于排查和重新生成。</p>
      {f'<p class="muted">生成异常：{_escape_html(error)}</p>' if error else ''}
    </section>
    <section>
      <h2>一、资产概况</h2>
      <div class="grid">
        <div class="card"><div class="muted">资产</div><div class="value">{_escape_html((item.get("session") or {}).get("host") or item.get("session_id"))}</div></div>
        <div class="card"><div class="muted">协议</div><div class="value">{_escape_html((item.get("session") or {}).get("protocol") or "")}</div></div>
        <div class="card"><div class="muted">检查项</div><div class="value">{len(checks)}</div></div>
        <div class="card"><div class="muted">风险等级</div><div class="value">{_escape_html(risk)}</div></div>
      </div>
    </section>
    <section><h2>二、巡检结论</h2><p class="muted">{_escape_html(inspection.get("summary") or inspection.get("message") or "平台已完成只读巡检，详见检查项与证据。")}</p></section>
    <section><h2>三、发现问题与影响范围</h2><p class="muted">{'发现异常检查项，请优先查看失败项输出并结合业务窗口复核。' if failed else '当前真实巡检结果未发现明确失败项，但仍建议结合业务指标持续观察。'}</p></section>
    <section><h2>四、检查项明细与证据</h2><table><thead><tr><th>检查项</th><th>状态</th><th>命令/SQL</th><th>输出摘要</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="4">未采集到检查项明细。</td></tr>'}</tbody></table></section>
    <section><h2>五、证据链摘要</h2><ul>{evidence_items or '<li>未采集到额外证据摘要。</li>'}</ul></section>
    <section><h2>六、原因分析</h2><p class="muted">本节基于真实检查项输出进行初步判断。若存在失败项，请优先确认账号权限、协议支持、命令兼容性、服务状态和目标资产负载。</p></section>
    <section><h2>七、建议动作与优先级</h2><ul><li>P0：复核失败检查项和关键服务状态。</li><li>P1：补充业务侧指标、日志、端口和容量趋势采集。</li><li>P2：将本次巡检结果纳入后续动态观察窗口。</li></ul></section>
    <section><h2>八、复查项与巡检盲区</h2><p class="muted">如报告中存在“未采集到”，说明当前会话或模板暂未覆盖对应指标，建议补充专用只读命令、SQL 或监控接口。</p></section>
  </main>
</body>
</html>"""


def render_canvas_export_html(item: dict[str, Any]) -> str:
    html = _coerce_canvas_html(item.get("html"))
    if html:
        return html
    points = item.get("points") if isinstance(item.get("points"), list) else []
    latest = points[-1] if points else {}
    spec = item.get("canvas_spec") if isinstance(item.get("canvas_spec"), dict) else {}
    data_json = json.dumps(
        {
            "item": {k: v for k, v in item.items() if k not in {"html"}},
            "latest": latest,
            "points": points,
            "canvas_spec": spec,
        },
        ensure_ascii=False,
        default=str,
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(item.get("title") or "OpsCore Canvas")}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#07111f; --panel:#0d1b2f; --line:#20e3d2; --text:#dcefff; --muted:#8ba4c7; --warn:#f7b955; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; background:
      radial-gradient(circle at 18% 8%, rgba(32,227,210,.25), transparent 28%),
      radial-gradient(circle at 90% 20%, rgba(86,130,255,.18), transparent 30%),
      linear-gradient(135deg,#07111f,#030812 72%); color:var(--text); }}
    .shell {{ padding:28px; }}
    .hero {{ border:1px solid rgba(32,227,210,.28); background:rgba(13,27,47,.76); border-radius:22px; padding:22px; box-shadow:0 24px 80px rgba(0,0,0,.38); }}
    .eyebrow {{ color:var(--line); font-size:12px; letter-spacing:.22em; text-transform:uppercase; }}
    h1 {{ margin:8px 0 6px; font-size:30px; }}
    .meta {{ color:var(--muted); font-size:13px; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin-top:18px; }}
    .card {{ border:1px solid rgba(139,164,199,.18); background:rgba(4,10,20,.52); border-radius:16px; padding:16px; }}
    .value {{ margin-top:8px; color:var(--line); font-size:34px; font-family:Consolas,monospace; font-weight:900; }}
    svg {{ width:100%; height:230px; margin-top:18px; border-radius:18px; background:rgba(4,10,20,.42); border:1px solid rgba(139,164,199,.14); }}
    pre {{ white-space:pre-wrap; color:var(--muted); font-size:12px; }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">OpsCore Canvas Export</div>
      <h1>{_escape_html(item.get("title") or "实时画板")}</h1>
      <div class="meta">类型：{_escape_html(CANVAS_KINDS.get(str(item.get("kind")), str(item.get("kind") or "metrics")))} · 模式：{_escape_html(CANVAS_MODES.get(str(item.get("mode")), str(item.get("mode") or "realtime")))} · 导出时间：{_now_iso()}</div>
      <div class="grid">
        <div class="card"><div class="meta">CPU</div><div class="value">{_escape_html(latest.get("cpu", "--"))}%</div></div>
        <div class="card"><div class="meta">内存</div><div class="value">{_escape_html(latest.get("memory", "--"))}%</div></div>
        <div class="card"><div class="meta">磁盘</div><div class="value">{_escape_html(latest.get("disk", "--"))}%</div></div>
      </div>
      <svg viewBox="0 0 900 230" role="img" aria-label="Canvas topology">
        <defs><filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
        <line x1="160" y1="116" x2="450" y2="72" stroke="#20e3d2" stroke-width="2" opacity=".65"/>
        <line x1="450" y1="72" x2="740" y2="116" stroke="#20e3d2" stroke-width="2" opacity=".65"/>
        <line x1="450" y1="72" x2="450" y2="176" stroke="#f7b955" stroke-width="2" opacity=".55"/>
        <circle cx="160" cy="116" r="48" fill="#0d1b2f" stroke="#20e3d2" stroke-width="3" filter="url(#glow)"/>
        <circle cx="450" cy="72" r="54" fill="#0d1b2f" stroke="#8aa4ff" stroke-width="3" filter="url(#glow)"/>
        <circle cx="740" cy="116" r="48" fill="#0d1b2f" stroke="#20e3d2" stroke-width="3" filter="url(#glow)"/>
        <circle cx="450" cy="176" r="36" fill="#0d1b2f" stroke="#f7b955" stroke-width="3"/>
        <text x="160" y="112" text-anchor="middle" fill="#dcefff" font-size="16">资产</text>
        <text x="160" y="134" text-anchor="middle" fill="#8ba4c7" font-size="12">{_escape_html((item.get("session") or {}).get("host") or item.get("session_id"))}</text>
        <text x="450" y="70" text-anchor="middle" fill="#dcefff" font-size="16">Canvas</text>
        <text x="450" y="92" text-anchor="middle" fill="#8ba4c7" font-size="12">{_escape_html(item.get("status"))}</text>
        <text x="740" y="112" text-anchor="middle" fill="#dcefff" font-size="16">数据</text>
        <text x="740" y="134" text-anchor="middle" fill="#8ba4c7" font-size="12">{len(points)} samples</text>
        <text x="450" y="181" text-anchor="middle" fill="#f7b955" font-size="13">审计</text>
      </svg>
      <details class="card"><summary>数据快照 JSON</summary><pre id="data"></pre></details>
    </section>
  </main>
  <script>
    const data = {data_json};
    document.getElementById('data').textContent = JSON.stringify(data, null, 2);
  </script>
</body>
</html>"""


class RealtimeCanvasManager:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = self._load_items()
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def _load_items(self) -> dict[str, dict[str, Any]]:
        if not REALTIME_CANVAS_STORE_PATH.exists():
            return {}
        try:
            raw = json.loads(REALTIME_CANVAS_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
        items: dict[str, dict[str, Any]] = {}
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            if item.get("status") == "running":
                item["status"] = "paused"
                item["stop_reason"] = "服务重启后已自动暂停，避免后台采集任务失控。"
            item.setdefault("points", [])
            item.setdefault("command_audit", [])
            item.setdefault("scripts", {"linux": _linux_metrics_command(), "windows": _windows_metrics_command()})
            item.setdefault("kind", "metrics")
            item.setdefault("mode", "realtime")
            item.setdefault("collector_language", "python")
            item.setdefault("collector_code", DEFAULT_PYTHON_COLLECTOR)
            item.setdefault("canvas_spec", {})
            item.setdefault("data_schema", {})
            item.setdefault("html", "")
            item.setdefault("ai_prompt_template", DEFAULT_CANVAS_AI_PROMPT)
            items[str(item["id"])] = item
        return items

    def _persist(self) -> None:
        REALTIME_CANVAS_STORE_PATH.write_text(
            json.dumps(list(self._items.values()), ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    def _snapshot(self, item: dict[str, Any]) -> dict[str, Any]:
        visible = dict(item)
        visible["points"] = list(item.get("points") or [])
        visible["latest"] = visible["points"][-1] if visible["points"] else None
        visible["remaining_seconds"] = max(0, int(item.get("expires_at_ts", 0) - time.time()))
        visible["html"] = _inject_canvas_payload(_coerce_canvas_html(visible.get("html")), visible)
        return visible

    def _session_summary(self, session_id: str) -> dict[str, Any]:
        session = ssh_manager.active_sessions.get(session_id)
        info = dict(session.get("info", {})) if session else {}
        return {
            "session_id": session_id,
            "host": info.get("host") or "",
            "port": info.get("port") or "",
            "username": info.get("username") or "",
            "asset_type": info.get("asset_type") or "",
            "protocol": info.get("protocol") or info.get("asset_type") or "",
            "remark": info.get("remark") or "",
        }

    async def list_items(self) -> list[dict[str, Any]]:
        async with self._lock:
            return [self._snapshot(item) for item in sorted(self._items.values(), key=lambda x: x.get("created_at", ""), reverse=True)]

    async def get_item(self, canvas_id: str) -> dict[str, Any] | None:
        async with self._lock:
            item = self._items.get(canvas_id)
            return self._snapshot(item) if item else None

    async def start(
        self,
        *,
        session_id: str,
        metrics: list[str],
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        duration_seconds: int = DEFAULT_DURATION_SECONDS,
        title: str | None = None,
        stop_existing: bool = True,
        scripts: dict[str, str] | None = None,
        kind: str = "metrics",
        mode: str = "realtime",
        collector_code: str | None = None,
        canvas_spec: dict[str, Any] | None = None,
        data_schema: dict[str, Any] | None = None,
        html: str | None = None,
        ai_prompt_template: str | None = None,
    ) -> dict[str, Any]:
        if session_id not in ssh_manager.active_sessions:
            raise ValueError("目标会话不在线，无法创建实时画板。")

        safe_metrics = [m for m in metrics if m in SUPPORTED_METRICS]
        if not safe_metrics:
            safe_metrics = ["cpu", "memory", "disk", "top_process"]

        interval = _clamp_int(interval_seconds, DEFAULT_INTERVAL_SECONDS, 5, 300)
        duration = _clamp_int(duration_seconds, DEFAULT_DURATION_SECONDS, 60, MAX_DURATION_SECONDS)
        canvas_id = f"rt_{uuid.uuid4().hex[:12]}"
        now = time.time()
        session = self._session_summary(session_id)
        item_scripts = {
            "linux": _linux_metrics_command(),
            "windows": _windows_metrics_command(),
        }
        if isinstance(scripts, dict):
            for key in ("linux", "windows"):
                if scripts.get(key):
                    item_scripts[key] = str(scripts[key])[:12000]
        needs_ai_generation = bool(ai_prompt_template) and not str(html or "").strip()
        initial_status = "generating" if needs_ai_generation else ("stopped" if mode == "static" else "running")
        item = {
            "id": canvas_id,
            "title": title or f"{session.get('host') or session_id} 实时资源画板",
            "kind": kind if kind in CANVAS_KINDS else "metrics",
            "mode": mode if mode in CANVAS_MODES else "realtime",
            "session_id": session_id,
            "session": session,
            "status": initial_status,
            "metrics": safe_metrics,
            "metric_labels": {key: SUPPORTED_METRICS[key] for key in safe_metrics},
            "interval_seconds": interval,
            "duration_seconds": duration,
            "started_at": _now_iso(),
            "created_at": _now_iso(),
            "expires_at": datetime.datetime.fromtimestamp(now + duration).strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at_ts": now + duration,
            "last_collect_at": "",
            "last_error": "",
            "stop_reason": "",
            "stop_existing": stop_existing,
            "scripts": item_scripts,
            "script_mode": "platform_managed_short_command",
            "collector_language": "python",
            "collector_code": (collector_code or DEFAULT_PYTHON_COLLECTOR)[:24000],
            "canvas_spec": canvas_spec if isinstance(canvas_spec, dict) else {},
            "data_schema": data_schema if isinstance(data_schema, dict) else {},
            "html": (str(html or "") if str(html or "").strip() else _pending_canvas_html(item={"title": title or f"{session.get('host') or session_id} AI 画板", "canvas_spec": canvas_spec or {}}))[:300000],
            "ai_prompt_template": str(ai_prompt_template or DEFAULT_CANVAS_AI_PROMPT)[:12000],
            "command_audit": [],
            "cleanup_note": "当前版本不在目标资产保留常驻脚本或后台进程；每次采集都是短只读命令，到期由 OpsCore 后端自动停止。",
            "points": [],
        }
        async with self._lock:
            if stop_existing:
                for old_id, old_item in list(self._items.items()):
                    if old_item.get("session_id") == session_id and old_item.get("status") == "running":
                        old_item["status"] = "replaced"
                        old_item["stop_reason"] = "生成新画板，自动停止旧画板。"
                        old_item["stopped_at"] = _now_iso()
                        old_task = self._tasks.pop(old_id, None)
                        if old_task:
                            old_task.cancel()
            self._items[canvas_id] = item
            if item["status"] == "running":
                self._tasks[canvas_id] = asyncio.create_task(self._collect_loop(canvas_id))
            if needs_ai_generation:
                asyncio.create_task(self._generate_canvas_with_ai(canvas_id))
            self._persist()
            return self._snapshot(item)

    async def schedule_ai_generation(self, canvas_id: str) -> dict[str, Any] | None:
        async with self._lock:
            item = self._items.get(canvas_id)
            if not item:
                return None
            item["status"] = "generating"
            item["last_error"] = ""
            item["stop_reason"] = "AI 正在根据目标生成画板。"
            item["html"] = _pending_canvas_html(item)
            self._persist()
            snapshot = self._snapshot(item)
        asyncio.create_task(self._generate_canvas_with_ai(canvas_id))
        return snapshot

    async def _generate_canvas_with_ai(self, canvas_id: str) -> None:
        async with self._lock:
            item = dict(self._items.get(canvas_id) or {})
        if not item:
            return

        try:
            from core.assistant_model_config import assistant_thinking_mode, resolve_assistant_model_id
            from core.llm_execution import execute_chat_stream

            model_name = resolve_assistant_model_id()
            messages = [
                {
                    "role": "system",
                    "content": str(item.get("ai_prompt_template") or DEFAULT_CANVAS_AI_PROMPT),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "instruction": "请严格输出 JSON，不要 Markdown。必须至少包含 html 字段；动态画板还要包含 collector_code 和 data_schema。",
                            "canvas": {
                                "id": item.get("id"),
                                "title": item.get("title"),
                                "kind": item.get("kind"),
                                "mode": item.get("mode"),
                                "metrics": item.get("metrics"),
                                "canvas_spec": item.get("canvas_spec"),
                            },
                            "session": item.get("session"),
                            "available_payload_fields": ["latest", "points", "topology", "events", "evidence", "errors"],
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ]
            if str(item.get("mode") or "") == "static":
                from core.session_inspection_service import inspect_active_session_record

                inspection = await inspect_active_session_record(str(item.get("session_id") or ""))
                real_payload = {
                    "session": item.get("session"),
                    "status": inspection.get("status") or "unknown",
                    "inspection": inspection,
                    "latest": {},
                    "points": [],
                    "topology": inspection.get("topology") or {},
                    "events": inspection.get("events") or [],
                    "evidence": [
                        {
                            "time": _now_iso(),
                            "source": "OpsCore 只读巡检",
                            "summary": json.dumps(inspection, ensure_ascii=False, default=str)[:4000],
                        }
                    ],
                }
                async with self._lock:
                    current = self._items.get(canvas_id)
                    if current:
                        current["inspection"] = inspection
                        current["evidence"] = real_payload["evidence"]
                        current["last_collect_at"] = _now_iso()
                        current["last_error"] = "" if inspection.get("status") in {"success", "warning"} else str(inspection.get("message") or "")
                        current["status"] = "generating"
                        current["stop_reason"] = "本次完整只读巡检已完成，AI 正在基于真实证据生成 HTML 分析报告。"
                        self._persist()
            else:
                sample_point = await asyncio.to_thread(self._collect_once, str(item.get("session_id") or ""), canvas_id)
                async with self._lock:
                    current = self._items.get(canvas_id)
                    if current:
                        current.setdefault("points", []).append(sample_point)
                        current["points"] = current["points"][-MAX_POINTS:]
                        current["latest"] = sample_point
                        current["last_collect_at"] = _now_iso()
                        current["last_error"] = str(sample_point.get("error") or "") if sample_point.get("status") == "error" else ""
                        self._persist()
                current_points = []
                async with self._lock:
                    current = self._items.get(canvas_id) or {}
                    current_points = list(current.get("points") or [])
                real_payload = {
                    "session": item.get("session"),
                    "status": sample_point.get("status"),
                    "latest": sample_point,
                    "points": current_points[-60:],
                    "topology": sample_point.get("topology") or {},
                    "events": sample_point.get("events") or [],
                    "evidence": sample_point.get("evidence") or [
                        {
                            "time": sample_point.get("time"),
                            "source": "OpsCore 平台采集脚本",
                            "summary": sample_point.get("error") or sample_point.get("command") or "平台已有会话采集结果",
                        }
                    ],
                }
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "instruction": "下面是真实平台 payload。静态模式必须基于本次 inspection/checks/evidence 写完整中文 HTML 分析报告，包含关键健康状态、异常项、风险等级、证据链和建议下一步；不要输出兜底摘要，不要只罗列命令输出，不要伪造缺失字段。动态模式请生成只读采集脚本/SQL/CLI 规划和 canvas_spec，不要生成 HTML。",
                            "real_payload": real_payload,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                }
            )
            chunks: list[str] = []
            async def _collect_model_content() -> str:
                async for event in execute_chat_stream(
                    model_name,
                    messages,
                    thinking_mode=assistant_thinking_mode(),
                    tools=None,
                ):
                    if event.get("type") == "content":
                        chunks.append(str(event.get("content") or ""))
                return "".join(chunks).strip()

            model_timeout = 90 if str(item.get("mode") or "") == "static" else 60
            content = await asyncio.wait_for(_collect_model_content(), timeout=model_timeout)
            parsed = _extract_json_object(content)
            if not parsed:
                extracted_html = _extract_html_field_text(content)
                html_from_text = extracted_html or (
                    content if "<html" in content.lower() and not content.lstrip().startswith("{") else _fallback_ai_canvas_html(item, real_payload, content)
                )
                parsed = {
                    "html": html_from_text,
                    "data_schema": {
                        "latest": "最近一次平台真实采集点",
                        "points": "平台真实采样点列表",
                        "evidence": "采集来源和证据摘要",
                    },
                    "canvas_spec": {"ai_output_format": "fallback_html_from_non_json"},
                }

            requested_mode = str(item.get("mode") or parsed.get("mode") or "static")
            mode = str(parsed.get("mode") or item.get("mode") or "static")
            if mode not in CANVAS_MODES:
                mode = str(item.get("mode") or "static")
            if requested_mode in {"realtime", "window"}:
                mode = requested_mode
            kind = str(parsed.get("kind") or item.get("kind") or "custom_html")
            if kind not in CANVAS_KINDS:
                kind = str(item.get("kind") or "custom_html")
            html = ""
            if mode == "static":
                html = str(parsed.get("html") or "").strip()
                if not html:
                    html = _fallback_ai_canvas_html(item, real_payload, content)

            async with self._lock:
                current = self._items.get(canvas_id)
                if not current:
                    return
                current["html"] = html[:300000]
                current["collector_code"] = str(current.get("collector_code") or DEFAULT_PYTHON_COLLECTOR)[:24000]
                current["collector_language"] = "platform_script"
                current["data_schema"] = parsed.get("data_schema") if isinstance(parsed.get("data_schema"), dict) else current.get("data_schema", {})
                if isinstance(parsed.get("canvas_spec"), dict):
                    current["canvas_spec"] = {**dict(current.get("canvas_spec") or {}), **parsed["canvas_spec"]}
                if isinstance(parsed.get("scripts"), dict):
                    scripts = dict(current.get("scripts") or {})
                    for key in ("linux", "windows"):
                        if key in parsed["scripts"]:
                            command = _coerce_script_command(parsed["scripts"][key])
                            if command:
                                scripts[key] = command[:12000]
                    current["scripts"] = scripts
                if mode in {"realtime", "window"}:
                    spec = dict(current.get("canvas_spec") or {})
                    for key in ("monitor_queries", "monitor_commands", "widgets", "metrics", "thresholds", "topology_plan", "refresh_hint"):
                        if key in parsed and key not in spec:
                            spec[key] = parsed[key]
                    current["canvas_spec"] = spec
                current["kind"] = kind
                current["mode"] = mode
                current["last_error"] = ""
                current["stop_reason"] = ""
                current["generated_at"] = _now_iso()
                current["status"] = "running" if mode in {"realtime", "window"} else "stopped"
                if current["status"] == "running" and canvas_id not in self._tasks:
                    self._tasks[canvas_id] = asyncio.create_task(self._collect_loop(canvas_id))
                self._persist()
        except Exception as exc:
            error = str(exc)
            async with self._lock:
                current = self._items.get(canvas_id)
                if not current:
                    return
                if str(current.get("mode") or "") == "static":
                    payload = locals().get("real_payload")
                    if not isinstance(payload, dict):
                        payload = {"session": current.get("session"), "inspection": current.get("inspection") or {}, "evidence": current.get("evidence") or []}
                    current["status"] = "error"
                    current["html"] = _fallback_static_report_html(current, payload, error)[:300000]
                    current["generated_at"] = _now_iso()
                    current["stop_reason"] = "AI 静态 HTML 分析报告生成失败，已保留本次只读巡检证据供排查。"
                else:
                    current["status"] = "running"
                    current["html"] = ""
                    current["generated_at"] = _now_iso()
                    current["stop_reason"] = "AI 动态采集规划失败，已回落到平台默认只读采集配置。"
                    if canvas_id not in self._tasks:
                        self._tasks[canvas_id] = asyncio.create_task(self._collect_loop(canvas_id))
                current["last_error"] = error
                current["updated_at"] = _now_iso()
                self._persist()

    async def stop(self, canvas_id: str, status: str = "paused", reason: str = "人工暂停。") -> dict[str, Any] | None:
        async with self._lock:
            item = self._items.get(canvas_id)
            if not item:
                return None
            item["status"] = status
            item["stop_reason"] = reason
            item["stopped_at"] = _now_iso()
            task = self._tasks.pop(canvas_id, None)
            if task:
                task.cancel()
            self._persist()
            return self._snapshot(item)

    async def update(self, canvas_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        async with self._lock:
            item = self._items.get(canvas_id)
            if not item:
                return None
            if "title" in patch:
                item["title"] = str(patch.get("title") or item.get("title") or "实时画板")[:120]
            if "metrics" in patch and isinstance(patch.get("metrics"), list):
                metrics = [metric for metric in patch["metrics"] if metric in SUPPORTED_METRICS]
                if metrics:
                    item["metrics"] = metrics
                    item["metric_labels"] = {key: SUPPORTED_METRICS[key] for key in metrics}
            if "interval_seconds" in patch:
                item["interval_seconds"] = _clamp_int(patch.get("interval_seconds"), int(item.get("interval_seconds") or DEFAULT_INTERVAL_SECONDS), 5, 300)
            if "duration_seconds" in patch:
                duration = _clamp_int(patch.get("duration_seconds"), int(item.get("duration_seconds") or DEFAULT_DURATION_SECONDS), 60, MAX_DURATION_SECONDS)
                item["duration_seconds"] = duration
                if item.get("status") == "running":
                    item["expires_at_ts"] = time.time() + duration
                    item["expires_at"] = datetime.datetime.fromtimestamp(item["expires_at_ts"]).strftime("%Y-%m-%d %H:%M:%S")
            if "stop_existing" in patch:
                item["stop_existing"] = bool(patch.get("stop_existing"))
            if "kind" in patch:
                kind = str(patch.get("kind") or "")
                if kind in CANVAS_KINDS:
                    item["kind"] = kind
            if "mode" in patch:
                mode = str(patch.get("mode") or "")
                if mode in CANVAS_MODES:
                    item["mode"] = mode
            if "collector_code" in patch:
                item["collector_code"] = str(patch.get("collector_code") or DEFAULT_PYTHON_COLLECTOR)[:24000]
                item["collector_language"] = "python"
            if "canvas_spec" in patch and isinstance(patch.get("canvas_spec"), dict):
                item["canvas_spec"] = patch["canvas_spec"]
            if "data_schema" in patch and isinstance(patch.get("data_schema"), dict):
                item["data_schema"] = patch["data_schema"]
            if "html" in patch:
                item["html"] = str(patch.get("html") or "")[:300000]
            if "ai_prompt_template" in patch:
                item["ai_prompt_template"] = str(patch.get("ai_prompt_template") or DEFAULT_CANVAS_AI_PROMPT)[:12000]
            if "scripts" in patch and isinstance(patch.get("scripts"), dict):
                scripts = dict(item.get("scripts") or {})
                for key in ("linux", "windows"):
                    if key in patch["scripts"]:
                        scripts[key] = str(patch["scripts"][key] or "")[:12000]
                item["scripts"] = scripts
            item["updated_at"] = _now_iso()
            self._persist()
            return self._snapshot(item)

    async def delete(self, canvas_id: str) -> bool:
        async with self._lock:
            if canvas_id not in self._items:
                return False
            task = self._tasks.pop(canvas_id, None)
            if task:
                task.cancel()
            del self._items[canvas_id]
            self._persist()
            return True

    async def extend(self, canvas_id: str, duration_seconds: int) -> dict[str, Any] | None:
        async with self._lock:
            item = self._items.get(canvas_id)
            if not item:
                return None
            add_seconds = _clamp_int(duration_seconds, 10 * 60, 60, MAX_DURATION_SECONDS)
            item["expires_at_ts"] = max(float(item.get("expires_at_ts") or time.time()), time.time()) + add_seconds
            item["expires_at"] = datetime.datetime.fromtimestamp(item["expires_at_ts"]).strftime("%Y-%m-%d %H:%M:%S")
            if item.get("status") != "running":
                item["status"] = "running"
                item["stop_reason"] = ""
                self._tasks[canvas_id] = asyncio.create_task(self._collect_loop(canvas_id))
            self._persist()
            return self._snapshot(item)

    async def _collect_loop(self, canvas_id: str) -> None:
        while True:
            async with self._lock:
                item = self._items.get(canvas_id)
                if not item or item.get("status") != "running":
                    return
                if time.time() >= float(item.get("expires_at_ts") or 0):
                    item["status"] = "expired"
                    item["stop_reason"] = "到达配置时间，自动暂停并回收采集任务。"
                    item["stopped_at"] = _now_iso()
                    self._tasks.pop(canvas_id, None)
                    self._persist()
                    return
                interval = int(item.get("interval_seconds") or DEFAULT_INTERVAL_SECONDS)
                session_id = str(item.get("session_id") or "")

            point = await asyncio.to_thread(self._collect_once, session_id, canvas_id)
            async with self._lock:
                item = self._items.get(canvas_id)
                if not item:
                    return
                item["last_collect_at"] = _now_iso()
                if point.get("status") == "error":
                    item["last_error"] = str(point.get("error") or "采集失败")
                else:
                    item["last_error"] = ""
                item.setdefault("points", []).append(point)
                item["points"] = item["points"][-MAX_POINTS:]
                item["latest"] = point
                item["latest_metrics"] = _extract_metric_snapshot(point)
                item["metric_series"] = _build_metric_series(item["points"])
                command = point.get("command")
                if command:
                    audit = item.setdefault("command_audit", [])
                    audit.append({"time": point["time"], "command": command, "status": point.get("status")})
                    item["command_audit"] = audit[-20:]
                self._persist()

            await asyncio.sleep(interval)

    def _collect_once(self, session_id: str, canvas_id: str) -> dict[str, Any]:
        session = ssh_manager.active_sessions.get(session_id)
        if not session:
            return {"time": _now_iso(), "status": "error", "error": "会话已断开，采集暂停。"}

        info = session.get("info", {})
        protocol = str(info.get("protocol") or info.get("asset_type") or "").lower()
        asset_type = str(info.get("asset_type") or "").lower()
        if protocol in SQL_PROTOCOLS or asset_type in SQL_PROTOCOLS:
            sql_point = self._collect_sql_monitor_once(info, protocol, asset_type, canvas_id)
            if sql_point:
                return sql_point
        if asset_type in {"switch", "router", "firewall", "network_device"}:
            return self._collect_network_device_once(session_id, info, asset_type, canvas_id)

        is_windows = protocol == "winrm" or asset_type == "windows"
        matching_item = self._items.get(canvas_id) or {}
        scripts = matching_item.get("scripts") if isinstance(matching_item.get("scripts"), dict) else {}
        command = str(scripts.get("windows" if is_windows else "linux") or "")
        if not command.strip():
            command = _windows_metrics_command() if is_windows else _linux_metrics_command()

        if is_windows:
            result = winrm_executor.execute_command(
                host=str(info.get("host") or ""),
                port=int(info.get("port") or 5985),
                username=str(info.get("username") or ""),
                password=info.get("password"),
                command=command,
                extra_args=info.get("extra_args") or {},
            )
        else:
            result = ssh_manager.execute_command(session_id, command, timeout=12)

        if not result.get("success"):
            return {
                "time": _now_iso(),
                "status": "error",
                "error": result.get("error") or result.get("output") or "采集命令执行失败",
                "command": command,
            }

        parsed = _parse_key_values(str(result.get("output") or ""))
        raw_output = str(result.get("output") or "")[:6000]
        filesystem_rows = _parse_semicolon_pairs(parsed.get("filesystems", ""))
        docker_rows = _parse_semicolon_pairs(parsed.get("docker", ""))
        login_rows = _parse_semicolon_pairs(parsed.get("logins", ""))
        mem_process_rows = _parse_top_process(parsed.get("mem_process", ""))
        route_rows = _parse_semicolon_pairs(parsed.get("routes", ""))
        interface_rows = _parse_semicolon_pairs(parsed.get("interfaces", ""))
        auth_failure_rows = _parse_semicolon_pairs(parsed.get("auth_failures", ""))
        docker_df_rows = _parse_semicolon_pairs(parsed.get("docker_df", ""))
        tables = []
        if filesystem_rows:
            tables.append({"name": "文件系统容量", "chart": "table", "rows": filesystem_rows})
        if docker_rows:
            tables.append({"name": "Docker 容器", "chart": "table", "rows": docker_rows})
        if docker_df_rows:
            tables.append({"name": "Docker 磁盘", "chart": "table", "rows": docker_df_rows})
        if login_rows:
            tables.append({"name": "最近登录记录", "chart": "table", "rows": login_rows})
        if auth_failure_rows:
            tables.append({"name": "认证失败记录", "chart": "table", "rows": auth_failure_rows})
        if mem_process_rows:
            tables.append({"name": "内存 Top 进程", "chart": "table", "rows": mem_process_rows})
        if interface_rows:
            tables.append({"name": "网卡地址", "chart": "table", "rows": interface_rows})
        if route_rows:
            tables.append({"name": "路由摘要", "chart": "table", "rows": route_rows})
        return {
            "time": _now_iso(),
            "status": "ok",
            "cpu": _safe_float(parsed.get("cpu")),
            "memory": _safe_float(parsed.get("memory")),
            "disk": _safe_float(parsed.get("disk")),
            "load": _safe_float(parsed.get("load")),
            "top_process": _parse_top_process(parsed.get("top_process", "")),
            "ports": _parse_semicolon_pairs(parsed.get("ports", "")),
            "network": _parse_semicolon_pairs(parsed.get("network", "")),
            "disk_io": parsed.get("disk_io", ""),
            "service_status": _parse_semicolon_pairs(parsed.get("service_status", "")),
            "tables": tables,
            "command": command,
            "raw_output": raw_output,
            "evidence": [
                {
                    "time": _now_iso(),
                    "source": "OpsCore 平台会话采集脚本",
                    "summary": raw_output[:1200] or "命令执行成功但未返回文本。",
                }
            ],
        }

    def _collect_sql_monitor_once(
        self,
        info: dict[str, Any],
        protocol: str,
        asset_type: str,
        canvas_id: str,
    ) -> dict[str, Any] | None:
        item = self._items.get(canvas_id) or {}
        spec = item.get("canvas_spec") if isinstance(item.get("canvas_spec"), dict) else {}
        queries = spec.get("monitor_queries") or spec.get("queries")
        from connections.db_manager import db_executor, normalize_database_driver_key
        from core.safety_policy import check_readonly_block

        extra_args = info.get("extra_args") or {}
        db_type = normalize_database_driver_key(str(protocol or asset_type or extra_args.get("db_type") or "").lower())
        if not isinstance(queries, list) or not queries:
            queries = _default_sql_monitor_queries(db_type)
        database = (
            extra_args.get("SID")
            or extra_args.get("service_name")
            or extra_args.get("database")
            or extra_args.get("db_name")
            or ""
        )
        tables: list[dict[str, Any]] = []
        data: dict[str, Any] = {}
        evidence: list[dict[str, Any]] = []
        errors: list[str] = []

        for query in queries[:6]:
            if not isinstance(query, dict):
                continue
            sql = str(query.get("sql") or query.get("command") or "").strip()
            name = str(query.get("name") or query.get("title") or "SQL 监控项")[:80]
            if not sql:
                continue
            blocked, reason = check_readonly_block("db_execute_query", {"sql": sql}, {
                "asset_type": asset_type,
                "protocol": protocol,
                "host": info.get("host"),
                "port": info.get("port"),
                "username": info.get("username"),
                "extra_args": extra_args,
            })
            if blocked:
                errors.append(f"{name}: {reason}")
                continue
            result_text = db_executor.execute_query(
                db_type,
                info.get("host"),
                info.get("port"),
                info.get("username"),
                info.get("password"),
                database,
                sql,
                extra_args,
            )
            try:
                result = json.loads(result_text)
            except Exception:
                result = {"success": False, "error": result_text}
            rows = _rows_from_db_result(result)
            tables.append(
                {
                    "name": name,
                    "chart": query.get("chart") or "table",
                    "sql": sql,
                    "rows": rows,
                    "success": bool(result.get("success")),
                    "error": result.get("error") or "",
                }
            )
            data.update({f"{name}.{key}": value for key, value in _numeric_summary_from_rows(rows).items()})
            if not result.get("success"):
                errors.append(f"{name}: {result.get('error') or '执行失败'}")
            evidence.append(
                {
                    "time": _now_iso(),
                    "source": "OpsCore 数据库动态监控",
                    "summary": f"{name} | SQL: {sql[:300]} | 结果: {str(result)[:900]}",
                }
            )

        if not tables and errors:
            return {"time": _now_iso(), "status": "error", "error": "；".join(errors), "tables": [], "data": {}, "evidence": evidence}
        return {
            "time": _now_iso(),
            "status": "error" if errors and not any(table.get("success") for table in tables) else "ok",
            "data": data,
            "tables": tables,
            "evidence": evidence,
            "error": "；".join(errors),
        }

    def _collect_network_device_once(
        self,
        session_id: str,
        info: dict[str, Any],
        asset_type: str,
        canvas_id: str,
    ) -> dict[str, Any]:
        item = self._items.get(canvas_id) or {}
        spec = item.get("canvas_spec") if isinstance(item.get("canvas_spec"), dict) else {}
        commands = spec.get("monitor_commands")
        if not isinstance(commands, list) or not commands:
            commands = _network_monitor_commands(asset_type)
        tables: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        errors: list[str] = []
        for command_item in commands[:6]:
            if not isinstance(command_item, dict):
                continue
            command = str(command_item.get("command") or "").strip()
            name = str(command_item.get("name") or command or "网络监控项")[:80]
            if not command:
                continue
            result = ssh_manager.execute_network_cli_command(session_id, command, timeout=15)
            output = str(result.get("output") or result.get("error") or "")
            rows = [{"line": line} for line in output.splitlines()[:120] if line.strip()]
            tables.append(
                {
                    "name": name,
                    "chart": command_item.get("chart") or "table",
                    "command": command,
                    "rows": rows,
                    "success": bool(result.get("success")),
                    "error": result.get("error") or "",
                }
            )
            if not result.get("success"):
                errors.append(f"{name}: {result.get('error') or '执行失败'}")
            evidence.append(
                {
                    "time": _now_iso(),
                    "source": "OpsCore 网络设备动态监控",
                    "summary": f"{name} | 命令: {command} | 输出: {output[:900]}",
                }
            )
        return {
            "time": _now_iso(),
            "status": "error" if errors and not any(table.get("success") for table in tables) else "ok",
            "tables": tables,
            "evidence": evidence,
            "error": "；".join(errors),
        }

    async def stop_all(self) -> None:
        for canvas_id in list(self._tasks):
            await self.stop(canvas_id, "stopped")


realtime_canvas_manager = RealtimeCanvasManager()
