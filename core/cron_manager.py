import asyncio
import logging
import uuid
import os
from datetime import datetime, timezone
from typing import Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

logger = logging.getLogger(__name__)

# 配置基于 SQLite 的定时任务存储
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cron_jobs.sqlite")
jobstores = {
    'default': SQLAlchemyJobStore(url=f'sqlite:///{db_path}')
}

# 初始化异步调度器
scheduler = AsyncIOScheduler(jobstores=jobstores)
_PAUSED_JOB_IDS: set[str] = set()
_RUNNING_INSPECTIONS: dict[str, dict[str, Any]] = {}
_DEFAULT_INSPECTION_TIMEOUT_SECONDS = 600.0
_DATABASE_INSPECTION_TIMEOUT_SECONDS = 1200.0
_ORACLE_INSPECTION_TIMEOUT_SECONDS = 1800.0
_PAUSED_JOB_KWARG = "_opscore_paused"

_INSPECTION_CYCLE_PROFILES: dict[str, dict[str, str]] = {
    "daily": {
        "label": "日巡检",
        "focus": "当前运行健康、CPU/内存/磁盘/核心服务、最近错误日志、监听端口、立即需要处理的风险。",
        "lookback": "重点查看当前状态和最近 24 小时异常。",
    },
    "weekly": {
        "label": "周巡检",
        "focus": "最近 7 天容量趋势、错误趋势、备份与定时任务执行、慢 SQL/异常日志、潜在隐患和优化建议。",
        "lookback": "尽量基于最近 7 天数据做趋势判断。",
    },
    "monthly": {
        "label": "月巡检",
        "focus": "容量预测、账号与权限、安全基线、补丁版本、证书/授权到期、SLA 和整改建议。",
        "lookback": "尽量基于最近 30 天数据做治理复盘。",
    },
    "quarterly": {
        "label": "季度巡检",
        "focus": "高可用、容灾、备份恢复可用性、性能瓶颈、架构风险、版本生命周期和季度整改计划。",
        "lookback": "尽量结合最近 90 天风险和趋势。",
    },
    "yearly": {
        "label": "年度巡检",
        "focus": "资产盘点、架构生命周期、重大风险、合规审计、容量预算和下一年度规划。",
        "lookback": "尽量形成年度级风险清单和规划建议。",
    },
    "custom": {
        "label": "自定义巡检",
        "focus": "严格围绕用户自定义指令执行，只做必要的只读验证和报告归档。",
        "lookback": "时间范围以用户指令为准。",
    },
}

_INSPECTION_DEPTH_LABELS: dict[str, str] = {
    "quick": "快速巡检：优先检查高信号、低成本的健康项，报告保持简洁。",
    "standard": "标准巡检：覆盖核心健康项、风险项、证据和建议。",
    "deep": "深度巡检：在标准巡检基础上增加趋势、根因线索、容量预测和整改优先级。",
}


def _active_running_inspection(job_id: str) -> dict[str, Any] | None:
    running = _RUNNING_INSPECTIONS.get(job_id)
    if not running:
        return None
    task = running.get("task")
    if task is not None and not task.done():
        return running
    _RUNNING_INSPECTIONS.pop(job_id, None)
    return None


def _cron_run_state(job_id: str, schedule_status: str) -> dict[str, Any]:
    running = _active_running_inspection(job_id)
    try:
        from core.inspection_results import list_runs

        latest_runs = list_runs(job_id=job_id, limit=1)
    except Exception:
        logger.exception("读取巡检运行摘要失败: job=%s", job_id)
        latest_runs = []
    latest = latest_runs[0] if latest_runs else {}
    latest_status = latest.get("status")
    effective_status = latest_status
    if latest_status == "running" and not running:
        effective_status = "orphaned"
    targets = list(latest.get("targets") or [])
    success_count = sum(1 for target in targets if target.get("status") == "success")
    error_count = sum(1 for target in targets if target.get("status") == "error")
    notification = latest.get("notification") if isinstance(latest.get("notification"), dict) else {}
    return {
        "schedule_status": schedule_status,
        "running": bool(running),
        "running_run_id": running.get("run_id") if running else None,
        "started_at": running.get("started_at") if running else None,
        "effective_status": effective_status,
        "latest_run_id": latest.get("id"),
        "latest_status": latest_status,
        "latest_message": latest.get("message"),
        "latest_started_at": latest.get("started_at"),
        "latest_completed_at": latest.get("completed_at"),
        "latest_duration_ms": latest.get("duration_ms") or 0,
        "target_count": len(targets),
        "success_count": success_count,
        "error_count": error_count,
        "notification_status": notification.get("status"),
        "notification_message": notification.get("message"),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inspection_event(
    event_type: str,
    message: str,
    *,
    status: str | None = None,
    target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "time": _now(),
        "type": event_type,
        "message": message,
    }
    if status:
        event["status"] = status
    if target:
        event["target"] = {
            "asset_id": target.get("asset_id"),
            "host": target.get("host"),
            "asset_type": target.get("asset_type"),
            "protocol": target.get("protocol"),
        }
    return event


def _duration_ms(started_at: str, completed_at: str) -> int:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(completed_at)
        return max(0, int((end - start).total_seconds() * 1000))
    except ValueError:
        return 0


def _normalize_skill_ids(skills: Any) -> list[str]:
    if not isinstance(skills, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        skill_id = str(skill or "").strip()
        if not skill_id or skill_id in seen:
            continue
        normalized.append(skill_id)
        seen.add(skill_id)
    return normalized


def _inspection_timeout_seconds(protocol: str | None, asset_type: str | None, extra_args: dict | None = None) -> float:
    extra_args = extra_args or {}
    configured = extra_args.get("inspection_timeout_seconds") or extra_args.get("ai_inspection_timeout_seconds")
    if configured is not None:
        try:
            return max(60.0, min(float(configured), 3600.0))
        except (TypeError, ValueError):
            pass

    kind = f"{protocol or ''} {asset_type or ''}".lower()
    if "oracle" in kind:
        return _ORACLE_INSPECTION_TIMEOUT_SECONDS
    if any(token in kind for token in ("mysql", "postgres", "postgresql", "mongo", "tidb", "database", "db2", "sqlserver")):
        return _DATABASE_INSPECTION_TIMEOUT_SECONDS
    return _DEFAULT_INSPECTION_TIMEOUT_SECONDS


def _normalize_inspection_cycle(value: str | None) -> str:
    normalized = str(value or "daily").strip().lower()
    return normalized if normalized in _INSPECTION_CYCLE_PROFILES else "custom"


def _normalize_inspection_depth(value: str | None) -> str:
    normalized = str(value or "standard").strip().lower()
    return normalized if normalized in _INSPECTION_DEPTH_LABELS else "standard"


def _inspection_cycle_prompt(cycle: str | None, depth: str | None) -> str:
    normalized_cycle = _normalize_inspection_cycle(cycle)
    normalized_depth = _normalize_inspection_depth(depth)
    profile = _INSPECTION_CYCLE_PROFILES[normalized_cycle]
    return (
        f"巡检周期：{profile['label']}。"
        f"巡检深度：{_INSPECTION_DEPTH_LABELS[normalized_depth]}"
        f"周期重点：{profile['focus']}"
        f"时间范围：{profile['lookback']}"
        "请按该周期组织检查项、证据、风险等级、整改建议和报告结构。"
    )


def _safe_target_result(
    target: dict[str, Any],
    *,
    status: str,
    result: Any = None,
    error: str | None = None,
    attempts: int = 1,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    started = started_at or _now()
    completed = completed_at or _now()
    data = {
        "asset_id": target.get("asset_id"),
        "host": target.get("host"),
        "port": target.get("port"),
        "username": target.get("username"),
        "asset_type": target.get("asset_type"),
        "protocol": target.get("protocol"),
        "status": status,
        "attempts": attempts,
        "started_at": started,
        "completed_at": completed,
        "duration_ms": _duration_ms(started, completed),
    }
    if result is not None:
        data["result"] = str(result)
    if error:
        data["error"] = error
    return data


def _cancelled_target_result(target: dict[str, Any], started_at: str | None = None) -> dict[str, Any]:
    return _safe_target_result(
        target,
        status="cancelled",
        result={"status": "cancelled", "message": "巡检已被用户取消"},
        error="巡检已被用户取消",
        started_at=started_at,
        completed_at=_now(),
    )


def _target_from_asset(asset: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    fallback_skills = _normalize_skill_ids(fallback.get("active_skills"))
    return {
        "asset_id": asset.get("id"),
        "host": asset.get("host") or fallback.get("host") or "",
        "port": asset.get("port") or fallback.get("port") or 22,
        "username": asset.get("username") or fallback.get("username") or "",
        "password": asset.get("password") or fallback.get("password"),
        "private_key_path": asset.get("private_key_path") or fallback.get("private_key_path"),
        "agent_profile": asset.get("agent_profile") or fallback.get("agent_profile") or "default",
        "asset_type": asset.get("asset_type"),
        "protocol": asset.get("protocol"),
        "extra_args": asset.get("extra_args") or {},
        "active_skills": fallback_skills or _normalize_skill_ids(asset.get("skills")),
        "tags": asset.get("tags") or [],
    }


def _asset_matches_scope(asset: dict[str, Any], target_scope: str, scope_value: str | None, asset_id: int | None) -> bool:
    scope = (target_scope or "asset").lower()
    value = str(scope_value or "").strip()
    if scope == "asset":
        return bool(asset_id and int(asset.get("id") or -1) == int(asset_id))
    if scope == "tag":
        return value in [str(tag) for tag in asset.get("tags", [])]
    if scope == "category":
        return str((asset.get("extra_args") or {}).get("category") or "") == value
    if scope == "protocol":
        return str(asset.get("protocol") or asset.get("asset_type") or "") == value
    if scope in {"type", "asset_type"}:
        return str(asset.get("asset_type") or "") == value
    if scope in {"all", "*"}:
        return True
    return False


def _resolve_targets(kwargs: dict[str, Any]) -> list[dict[str, Any]]:
    target_scope = kwargs.get("target_scope") or "asset"
    scope_value = kwargs.get("scope_value")
    asset_id = kwargs.get("asset_id")
    fallback = {
        "host": kwargs.get("host") or "",
        "username": kwargs.get("username") or "",
        "password": kwargs.get("password"),
        "private_key_path": kwargs.get("private_key_path"),
        "agent_profile": kwargs.get("agent_profile") or "default",
        "active_skills": _normalize_skill_ids(kwargs.get("active_skills")),
    }
    if target_scope == "asset" and not asset_id:
        return [{
            "asset_id": None,
            "host": fallback["host"],
            "port": 22,
            "username": fallback["username"],
            "password": fallback["password"],
            "private_key_path": fallback["private_key_path"],
            "agent_profile": fallback["agent_profile"],
            "asset_type": None,
            "protocol": None,
            "extra_args": {},
            "active_skills": _normalize_skill_ids(fallback.get("active_skills")),
            "tags": [],
        }]

    from core.memory import memory_db

    assets = memory_db.get_all_assets()
    targets = [
        _target_from_asset(asset, fallback)
        for asset in assets
        if _asset_matches_scope(asset, target_scope, scope_value, asset_id)
    ]
    if not targets and fallback["host"]:
        targets.append({
            "asset_id": asset_id,
            "host": fallback["host"],
            "port": 22,
            "username": fallback["username"],
            "password": fallback["password"],
            "private_key_path": fallback["private_key_path"],
            "agent_profile": fallback["agent_profile"],
            "asset_type": None,
            "protocol": None,
            "extra_args": {},
            "active_skills": _normalize_skill_ids(fallback.get("active_skills")),
            "tags": [],
        })
    return targets

async def _trigger_proactive_inspection(
    job_id: str,
    host: str,
    agent_profile: str,
    message: str,
    username: str,
    port: int = 22,
    private_key_path: str = None,
    password: str = None,
    asset_type: str = "linux",
    protocol: str | None = "ssh",
    extra_args: dict | None = None,
    tags: list[str] | None = None,
    asset_id: int | None = None,
    target_scope: str = "asset",
    scope_value: str | None = None,
    template_id: str | None = None,
    notification_channel: str = "auto",
    cron_expr: str | None = None,
    inspection_cycle: str | None = "daily",
    inspection_depth: str | None = "standard",
    active_skills: list[str] | None = None,
):
    """
    定时任务的实际执行体：
    1. 后台悄悄建立 SSH 会话（模拟连通）。
    2. 将指定的巡检要求（message）发送给大模型处理。
    3. 大模型会自动去执行命令排查，最后根据系统设定，大模型会调用 send_notification 把报告发出去。
    4. 任务结束后清理后台会话。
    """
    logger.info(f"⏰ [CRON JOB {job_id}] 触发巡检任务 -> 目标: {host}, 角色: {agent_profile}")
    if extra_args is None:
        extra_args = {}
    if tags is None:
        tags = []
    
    from connections.ssh_manager import ssh_manager
    from core.agent import headless_agent_chat
    
    from core.dispatcher import dispatcher
    available_skill_ids = set(dispatcher.skills_registry.keys())
    selected_skills = [
        skill_id
        for skill_id in _normalize_skill_ids(active_skills)
        if skill_id in available_skill_ids
    ]
    
    # 1. 自动建立特权会话：判断是否是要求连远程，还是只是在本地跑卓豪监控脚本
    if host.lower() in ["localhost", "local", "127.0.0.1"]:
         conn_res = await asyncio.to_thread(
             ssh_manager.connect_local,
             agent_profile=agent_profile,
             active_skills=selected_skills
         )
    else:
         conn_res = await asyncio.to_thread(
             ssh_manager.connect,
             host=host,
             port=port,
             username=username,
             password=password,
             key_filename=private_key_path,
             allow_modifications=False,
             active_skills=selected_skills,
             agent_profile=agent_profile,
             asset_type=asset_type,
             protocol=protocol,
             extra_args=extra_args,
             tags=tags,
             target_scope=target_scope,
             scope_value=scope_value,
         )
    
    if not conn_res.get("success"):
        logger.error(f"❌ [CRON JOB {job_id}] SSH 连接 {host} 失败，巡检任务终止。")
        return {"status": "connection_failed", "error": conn_res.get("message", "连接失败")}
        
    session_id = conn_res["session_id"]
    logger.info(f"✅ [CRON JOB {job_id}] 成功建立后台隐藏会话: {session_id}")
    
    # 2. 构造系统要求，让 Agent 完成巡检报告；通知由后端统一兜底发送
    cycle_prompt = _inspection_cycle_prompt(inspection_cycle, inspection_depth)
    prompt = (
        "【系统定时巡检任务】现在是自动巡检时间。请你对当前资产执行只读巡检。"
        f"{cycle_prompt}"
        f"当前资产：{asset_type}/{protocol} {host}:{port}。"
        f"任务范围：{target_scope}；资产ID：{asset_id or 'N/A'}；模板：{template_id or '默认'}。"
        "巡检完毕后只需要返回完整总结报告；后端会根据巡检计划统一发送通知，请不要自行调用 `send_notification`。"
        f"用户原始指令要求：{message}"
    )
    
    # 3. 使用无头 Agent 后台执行巡检，无需消耗 SSE 流
    try:
        timeout_seconds = _inspection_timeout_seconds(protocol, asset_type, extra_args)
        result = await asyncio.wait_for(headless_agent_chat(session_id, prompt), timeout=timeout_seconds)
        logger.info(f"✅ [CRON JOB {job_id}] AI 巡检完成，摘要: {result[:200] if result else 'N/A'}")
        return result
    except asyncio.TimeoutError:
        timeout_seconds = _inspection_timeout_seconds(protocol, asset_type, extra_args)
        timeout_minutes = int(timeout_seconds // 60)
        logger.error(f"❌ [CRON JOB {job_id}] AI 巡检执行超时 ({timeout_minutes}分钟)")
        return {"status": "timeout", "error": f"AI 巡检执行超时（已等待{timeout_minutes}分钟）"}
    except Exception as e:
         logger.error(f"❌ [CRON JOB {job_id}] AI 巡检执行过程中崩溃: {e}")
         return {"status": "error", "error": str(e)}
    finally:
         # 4. 无论成功与否，任务结束后自动销毁这个后台会话，释放服务器连接数
         await asyncio.to_thread(ssh_manager.disconnect, session_id)
         logger.info(f"🔚 [CRON JOB {job_id}] 后台会话 {session_id} 已安全销毁。")


def _notification_status_label(status: str) -> str:
    return {
        "completed": "完成",
        "partial": "部分完成",
        "failed": "失败",
        "empty": "无目标",
        "cancelled": "已取消",
    }.get(status, status or "未知")


def _build_inspection_notification(job_kwargs: dict[str, Any], run: dict[str, Any], targets: list[dict[str, Any]]) -> tuple[str, str]:
    status = str(run.get("status") or "unknown")
    success_count = sum(1 for target in targets if target.get("status") == "success")
    error_count = sum(1 for target in targets if target.get("status") == "error")
    cancelled_count = sum(1 for target in targets if target.get("status") == "cancelled")
    first_target = targets[0] if targets else {}
    title_target = first_target.get("host") or job_kwargs.get("host") or job_kwargs.get("scope_value") or "巡检目标"
    title = f"巡检{_notification_status_label(status)}：{title_target}"
    lines = [
        f"- 计划: `{run.get('job_id') or job_kwargs.get('job_id') or '-'}`",
        f"- 状态: `{_notification_status_label(status)}`",
        f"- 范围: `{run.get('target_scope') or job_kwargs.get('target_scope') or 'asset'}` / `{run.get('scope_value') or '-'}`",
        f"- 目标数: {len(targets)}，成功: {success_count}，失败: {error_count}，取消: {cancelled_count}",
        f"- 开始: `{run.get('started_at') or '-'}`",
        f"- 完成: `{run.get('completed_at') or '-'}`",
    ]
    if first_target:
        lines.extend(
            [
                "",
                "## 首个目标",
                f"- 资产: `{first_target.get('asset_id') or '-'}`",
                f"- 地址: `{first_target.get('host') or '-'}`",
                f"- 类型/协议: `{first_target.get('asset_type') or '-'}` / `{first_target.get('protocol') or '-'}`",
                f"- 结果: `{first_target.get('status') or '-'}`",
            ]
        )
        if first_target.get("error"):
            lines.append(f"- 错误: `{first_target.get('error')}`")
        result = str(first_target.get("result") or "").strip()
        if result:
            lines.extend(["", "## 摘要", result[:1800]])
    return title, "\n".join(lines)


async def _send_inspection_completion_notification(job_kwargs: dict[str, Any], run: dict[str, Any], targets: list[dict[str, Any]]) -> dict[str, Any]:
    channel = str(job_kwargs.get("notification_channel") or "auto")
    if channel.lower() in {"", "none", "disabled", "off"}:
        return {"status": "SKIPPED", "message": "巡检计划未启用通知渠道。"}
    title, content = _build_inspection_notification(job_kwargs, run, targets)

    def notify() -> dict[str, Any]:
        from core.notifier import send_notification

        return send_notification(channel, title, content)

    result = await asyncio.to_thread(notify)
    logger.info(
        "巡检完成通知已处理: job=%s run=%s channel=%s result=%s",
        job_kwargs.get("job_id"),
        run.get("id"),
        channel,
        result,
    )
    return result


async def _run_inspection_job(**kwargs) -> dict:
    from core.inspection_results import record_run, update_run

    started_at = _now()
    job_id = kwargs.get("job_id") or ""
    if job_id:
        running = _active_running_inspection(job_id)
        if running:
            return {
                "status": "running",
                "job_id": job_id,
                "run_id": running.get("run_id"),
                "target_count": 0,
                "targets": [],
                "message": "该计划已有巡检正在执行。",
            }
    targets = _resolve_targets(kwargs)
    progress_targets = [
        _safe_target_result(target, status="pending", started_at=started_at, completed_at=started_at)
        for target in targets
    ]
    events = [
        _inspection_event(
            "run_started",
            f"巡检运行已启动，等待处理 {len(targets)} 个目标。",
            status="running",
        )
    ]
    run = record_run(
        job_id=kwargs.get("job_id") or "",
        status="running",
        target_scope=kwargs.get("target_scope") or "asset",
        scope_value=kwargs.get("scope_value"),
        message=kwargs.get("message") or "",
        targets=progress_targets,
        events=events,
        started_at=started_at,
        completed_at=None,
    )
    current_task = asyncio.current_task()
    if current_task is not None and job_id:
        _RUNNING_INSPECTIONS[job_id] = {
            "task": current_task,
            "run_id": run["id"],
            "started_at": started_at,
        }
    target_results: list[dict[str, Any]] = []
    retry_count = max(0, int(kwargs.get("retry_count") or 0))
    current_target: dict[str, Any] | None = None
    current_target_started_at: str | None = None

    try:
        for target_index, target in enumerate(targets):
            current_target = target
            call_kwargs = dict(kwargs)
            call_kwargs.update(
                {
                    "host": target.get("host") or "",
                    "port": int(target.get("port") or 22),
                    "username": target.get("username") or "",
                    "password": target.get("password"),
                    "private_key_path": target.get("private_key_path"),
                    "agent_profile": target.get("agent_profile") or kwargs.get("agent_profile") or "default",
                    "asset_type": target.get("asset_type") or kwargs.get("asset_type") or "linux",
                    "protocol": target.get("protocol") or kwargs.get("protocol") or "ssh",
                    "extra_args": target.get("extra_args") or kwargs.get("extra_args") or {},
                    "active_skills": _normalize_skill_ids(target.get("active_skills") or kwargs.get("active_skills")),
                    "tags": target.get("tags") or kwargs.get("tags") or [],
                    "asset_id": target.get("asset_id"),
                }
            )
            call_kwargs.pop("retry_count", None)
            call_kwargs.pop(_PAUSED_JOB_KWARG, None)
            target_started_at = _now()
            current_target_started_at = target_started_at
            progress_targets[target_index] = _safe_target_result(
                target,
                status="running",
                attempts=0,
                started_at=target_started_at,
                completed_at=target_started_at,
            )
            events.append(
                _inspection_event(
                    "target_started",
                    f"开始巡检目标 {target.get('host') or target.get('asset_id') or '-'}。",
                    status="running",
                    target=target,
                )
            )
            update_run(run["id"], status="running", targets=progress_targets, events=events)
            attempts = 0
            last_result: Any = None
            last_error: str | None = None
            success = False
            for attempt in range(retry_count + 1):
                attempts = attempt + 1
                try:
                    result = await _trigger_proactive_inspection(**call_kwargs)
                    last_result = result
                    if isinstance(result, dict) and result.get("status") in {"connection_failed", "timeout", "error"}:
                        last_error = str(result.get("error") or result.get("status"))
                    else:
                        success = True
                        last_error = None
                        break
                except Exception as e:
                    logger.exception("Inspection target failed: job=%s host=%s", kwargs.get("job_id"), target.get("host"))
                    last_result = None
                    last_error = str(e)
                if attempt < retry_count:
                    logger.info("Retrying inspection target: job=%s host=%s attempt=%s", kwargs.get("job_id"), target.get("host"), attempt + 2)
            target_completed_at = _now()
            target_result = _safe_target_result(
                target,
                status="success" if success else "error",
                result=last_result,
                error=last_error,
                attempts=attempts,
                started_at=target_started_at,
                completed_at=target_completed_at,
            )
            target_results.append(target_result)
            progress_targets[target_index] = target_result
            events.append(
                _inspection_event(
                    "target_completed" if success else "target_failed",
                    f"目标 {target.get('host') or target.get('asset_id') or '-'} 巡检{'完成' if success else '失败'}。",
                    status=target_result["status"],
                    target=target,
                )
            )
            update_run(run["id"], status="running", targets=progress_targets, events=events)
            current_target = None
            current_target_started_at = None

        if not target_results:
            status = "empty"
        elif all(item["status"] == "success" for item in target_results):
            status = "completed"
        elif all(item["status"] == "error" for item in target_results):
            status = "failed"
        else:
            status = "partial"
    except asyncio.CancelledError:
        completed_assets = {item.get("asset_id") for item in target_results if item.get("asset_id") is not None}
        if current_target is not None and current_target.get("asset_id") not in completed_assets:
            target_results.append(_cancelled_target_result(current_target, current_target_started_at or started_at))
            completed_assets.add(current_target.get("asset_id"))
        for target in targets:
            asset_id = target.get("asset_id")
            if asset_id is not None and asset_id in completed_assets:
                continue
            if target is current_target:
                continue
            target_results.append(_cancelled_target_result(target, started_at))
        status = "cancelled"
        events.append(
            _inspection_event(
                "run_cancelled",
                "巡检运行已取消。",
                status=status,
            )
        )
        logger.info("Inspection run cancelled: job=%s run=%s", job_id, run["id"])
    finally:
        running = _RUNNING_INSPECTIONS.get(job_id)
        if running and running.get("run_id") == run["id"]:
            _RUNNING_INSPECTIONS.pop(job_id, None)

    completed_at = _now()
    if status != "cancelled":
        events.append(
            _inspection_event(
                "run_completed",
                f"巡检运行结束，状态：{_notification_status_label(status)}。",
                status=status,
            )
        )
    updated_run = update_run(
        run["id"],
        status=status,
        targets=target_results,
        events=events,
        completed_at=completed_at,
    )
    run = updated_run or run
    try:
        notification_result = await _send_inspection_completion_notification(kwargs, run, target_results)
    except Exception as exc:
        logger.exception("巡检完成通知发送异常: job=%s run=%s", kwargs.get("job_id"), run["id"])
        notification_result = {"status": "ERROR", "message": str(exc)}
    events.append(
        _inspection_event(
            "notification_completed",
            f"通知处理完成：{notification_result.get('message') or notification_result.get('status') or '-'}",
            status=str(notification_result.get("status") or "UNKNOWN"),
        )
    )
    updated_run = update_run(run["id"], notification=notification_result, events=events)
    run = updated_run or run
    return {
        "status": status,
        "job_id": kwargs.get("job_id"),
        "run_id": run["id"],
        "target_count": len(target_results),
        "targets": target_results,
        "notification": notification_result,
    }

class CronManager:
    """管理系统定时主动巡检任务的门面"""

    @staticmethod
    def start_scheduler():
        if scheduler.running:
            return
        try:
            asyncio.get_running_loop()
            scheduler.start()
            logger.info("Cron Scheduler 已启动。")
        except RuntimeError:
            logger.debug("Cron Scheduler 未启动：当前没有运行中的 asyncio event loop。")

    @staticmethod
    def _parse_cron(cron_expr: str) -> list[str]:
        parts = str(cron_expr or "").split()
        if len(parts) != 5:
            raise ValueError("无效的 Cron 表达式，必须是 5 位，例如 '0 9 * * *'")
        return parts

    @staticmethod
    def _job_to_dict(job) -> dict:
        kwargs = dict(getattr(job, "kwargs", {}) or {})
        args = list(getattr(job, "args", []) or [])
        next_run_time = getattr(job, "next_run_time", None)
        is_paused = bool(kwargs.get(_PAUSED_JOB_KWARG)) or job.id in _PAUSED_JOB_IDS or (scheduler.running and next_run_time is None)
        schedule_status = "paused" if is_paused else "scheduled"
        if not kwargs and args:
            kwargs = {
                "job_id": args[0] if len(args) > 0 else job.id,
                "host": args[1] if len(args) > 1 else "",
                "agent_profile": args[2] if len(args) > 2 else "default",
                "message": args[3] if len(args) > 3 else "",
                "username": args[4] if len(args) > 4 else "",
                "private_key_path": args[5] if len(args) > 5 else None,
                "password": args[6] if len(args) > 6 else None,
            }
        return {
            "id": job.id,
            "cron_expr": kwargs.get("cron_expr", ""),
            "message": kwargs.get("message", ""),
            "inspection_cycle": _normalize_inspection_cycle(kwargs.get("inspection_cycle")),
            "inspection_depth": _normalize_inspection_depth(kwargs.get("inspection_depth")),
            "host": kwargs.get("host") or kwargs.get("target_host") or "",
            "target_host": kwargs.get("host") or "",
            "username": kwargs.get("username", ""),
            "agent_profile": kwargs.get("agent_profile", "default"),
            "asset_id": kwargs.get("asset_id"),
            "target_scope": kwargs.get("target_scope", "asset"),
            "scope_value": kwargs.get("scope_value"),
            "template_id": kwargs.get("template_id"),
            "notification_channel": kwargs.get("notification_channel", "auto"),
            "retry_count": kwargs.get("retry_count", 0),
            "active_skills": _normalize_skill_ids(kwargs.get("active_skills")),
            "next_run": str(next_run_time) if next_run_time else None,
            "next_run_time": str(next_run_time) if next_run_time else "Paused",
            "status": schedule_status,
            "run_state": _cron_run_state(job.id, schedule_status),
        }
    
    @staticmethod
    def add_inspection_job(
        cron_expr: str,
        host: str,
        username: str,
        agent_profile: str,
        message: str,
        password: str = None,
        private_key_path: str = None,
        job_id: str | None = None,
        asset_id: int | None = None,
        target_scope: str = "asset",
        scope_value: str | None = None,
        template_id: str | None = None,
        notification_channel: str = "auto",
        retry_count: int = 0,
        inspection_cycle: str = "daily",
        inspection_depth: str = "standard",
        active_skills: list[str] | None = None,
    ) -> str:
        """
        添加一个 Cron 定时任务
        :param cron_expr: 标准 cron 表达式，如 "0 9 * * *"
        """
        job_id = job_id or f"cron_{uuid.uuid4().hex[:8]}"
        
        parts = CronManager._parse_cron(cron_expr)
        if scheduler.get_job(job_id):
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass
             
        # APScheduler 的 CronTrigger 使用的是 kwargs，如 minute='0', hour='9', day='*', month='*', day_of_week='*'
        scheduler.add_job(
            _run_inspection_job,
            trigger='cron',
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            id=job_id,
            kwargs={
                "job_id": job_id,
                "host": host,
                "agent_profile": agent_profile,
                "message": message,
                "inspection_cycle": _normalize_inspection_cycle(inspection_cycle),
                "inspection_depth": _normalize_inspection_depth(inspection_depth),
                "username": username,
                "private_key_path": private_key_path,
                "password": password,
                "asset_id": asset_id,
                "target_scope": target_scope,
                "scope_value": scope_value,
                "template_id": template_id,
                "notification_channel": notification_channel,
                "retry_count": max(0, int(retry_count or 0)),
                "active_skills": _normalize_skill_ids(active_skills),
                "cron_expr": cron_expr,
                _PAUSED_JOB_KWARG: False,
            },
            replace_existing=True,
            misfire_grace_time=3600
        )
        _PAUSED_JOB_IDS.discard(job_id)
        logger.info(f"已注册定时巡检任务 {job_id}，计划：{cron_expr}")
        return job_id
        
    @staticmethod
    def get_all_jobs() -> list:
        return [CronManager._job_to_dict(job) for job in scheduler.get_jobs()]

    @staticmethod
    def get_job(job_id: str) -> dict:
        job = scheduler.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        return CronManager._job_to_dict(job)

    @staticmethod
    def update_job(job_id: str, **kwargs) -> dict:
        job = scheduler.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        existing = CronManager._job_to_dict(job)
        CronManager.add_inspection_job(job_id=job_id, **kwargs)
        if existing.get("status") == "paused":
            CronManager.pause_job(job_id)
        return CronManager.get_job(job_id)

    @staticmethod
    def pause_job(job_id: str) -> dict:
        job = scheduler.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        kwargs = dict(getattr(job, "kwargs", {}) or {})
        kwargs[_PAUSED_JOB_KWARG] = True
        scheduler.modify_job(job_id, kwargs=kwargs)
        scheduler.pause_job(job_id)
        _PAUSED_JOB_IDS.add(job_id)
        return CronManager.get_job(job_id)

    @staticmethod
    def resume_job(job_id: str) -> dict:
        job = scheduler.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        kwargs = dict(getattr(job, "kwargs", {}) or {})
        kwargs[_PAUSED_JOB_KWARG] = False
        scheduler.modify_job(job_id, kwargs=kwargs)
        scheduler.resume_job(job_id)
        _PAUSED_JOB_IDS.discard(job_id)
        return CronManager.get_job(job_id)

    @staticmethod
    async def run_job_now(job_id: str) -> dict:
        job = scheduler.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        kwargs = dict(getattr(job, "kwargs", {}) or {})
        kwargs.pop("cron_expr", None)
        return await _run_inspection_job(**kwargs)

    @staticmethod
    async def start_job_now(job_id: str) -> dict:
        job = scheduler.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        running = _active_running_inspection(job_id)
        if running:
            return {
                "status": "running",
                "job_id": job_id,
                "run_id": running.get("run_id"),
                "target_count": 0,
                "targets": [],
                "message": "该计划已有巡检正在执行。",
            }
        kwargs = dict(getattr(job, "kwargs", {}) or {})
        kwargs.pop("cron_expr", None)
        task = asyncio.create_task(_run_inspection_job(**kwargs))

        def _log_background_result(done: asyncio.Task) -> None:
            try:
                done.result()
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("后台巡检任务异常退出: job=%s", job_id)

        task.add_done_callback(_log_background_result)
        await asyncio.sleep(0)
        if task.done():
            return task.result()
        running = _active_running_inspection(job_id)
        return {
            "status": "accepted",
            "job_id": job_id,
            "run_id": running.get("run_id") if running else None,
            "target_count": 0,
            "targets": [],
            "message": "巡检已在后台启动。",
        }

    @staticmethod
    def cancel_running_job(job_id: str) -> dict:
        running = _RUNNING_INSPECTIONS.get(job_id)
        if not running:
            raise KeyError(job_id)
        task = running.get("task")
        if task is not None and not task.done():
            task.cancel()
        return {
            "job_id": job_id,
            "run_id": running.get("run_id"),
            "status": "cancelling",
        }
        
    @staticmethod
    def remove_job(job_id: str):
        scheduler.remove_job(job_id)
        _PAUSED_JOB_IDS.discard(job_id)

# 调度器由 FastAPI lifespan 在事件循环内启动；单元测试/脚本导入不启动。
