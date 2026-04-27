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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_ms(started_at: str, completed_at: str) -> int:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(completed_at)
        return max(0, int((end - start).total_seconds() * 1000))
    except ValueError:
        return 0


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


def _target_from_asset(asset: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
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
    all_skills = list(dispatcher.skills_registry.keys())
    
    # 1. 自动建立特权会话：判断是否是要求连远程，还是只是在本地跑卓豪监控脚本
    if host.lower() in ["localhost", "local", "127.0.0.1"]:
         conn_res = await asyncio.to_thread(
             ssh_manager.connect_local,
             agent_profile=agent_profile,
             active_skills=all_skills
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
             active_skills=all_skills,
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
    
    # 2. 构造强制的系统要求，让 Agent 完成巡检并发送通知
    prompt = (
        "【系统定时巡检任务】现在是自动巡检时间。请你对当前服务器执行全面的健康检查"
        "（如磁盘、CPU、内存、僵尸进程等，或者按照你的角色要求去查）。"
        f"当前资产：{asset_type}/{protocol} {host}:{port}。"
        f"任务范围：{target_scope}；资产ID：{asset_id or 'N/A'}；模板：{template_id or '默认'}。"
        f"巡检完毕后，**你必须**调用 `send_notification` 工具，将巡检总结报告发送给团队，渠道：{notification_channel}。"
        f"用户原始指令要求：{message}"
    )
    
    # 3. 使用无头 Agent 后台执行巡检，无需消耗 SSE 流
    try:
        result = await asyncio.wait_for(headless_agent_chat(session_id, prompt), timeout=600.0)
        logger.info(f"✅ [CRON JOB {job_id}] AI 巡检完成，摘要: {result[:200] if result else 'N/A'}")
        return result
    except asyncio.TimeoutError:
        logger.error(f"❌ [CRON JOB {job_id}] AI 巡检执行超时 (10分钟)")
        return {"status": "timeout", "error": "AI 巡检执行超时"}
    except Exception as e:
         logger.error(f"❌ [CRON JOB {job_id}] AI 巡检执行过程中崩溃: {e}")
         return {"status": "error", "error": str(e)}
    finally:
         # 4. 无论成功与否，任务结束后自动销毁这个后台会话，释放服务器连接数
         await asyncio.to_thread(ssh_manager.disconnect, session_id)
         logger.info(f"🔚 [CRON JOB {job_id}] 后台会话 {session_id} 已安全销毁。")


async def _run_inspection_job(**kwargs) -> dict:
    from core.inspection_results import record_run

    started_at = _now()
    targets = _resolve_targets(kwargs)
    target_results: list[dict[str, Any]] = []
    retry_count = max(0, int(kwargs.get("retry_count") or 0))

    for target in targets:
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
                "tags": target.get("tags") or kwargs.get("tags") or [],
                "asset_id": target.get("asset_id"),
            }
        )
        target_started_at = _now()
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
        target_results.append(
            _safe_target_result(
                target,
                status="success" if success else "error",
                result=last_result,
                error=last_error,
                attempts=attempts,
                started_at=target_started_at,
                completed_at=target_completed_at,
            )
        )

    if not target_results:
        status = "empty"
    elif all(item["status"] == "success" for item in target_results):
        status = "completed"
    elif all(item["status"] == "error" for item in target_results):
        status = "failed"
    else:
        status = "partial"

    run = record_run(
        job_id=kwargs.get("job_id") or "",
        status=status,
        target_scope=kwargs.get("target_scope") or "asset",
        scope_value=kwargs.get("scope_value"),
        message=kwargs.get("message") or "",
        targets=target_results,
        started_at=started_at,
        completed_at=_now(),
    )
    return {
        "status": status,
        "job_id": kwargs.get("job_id"),
        "run_id": run["id"],
        "target_count": len(target_results),
        "targets": target_results,
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
            "next_run": str(getattr(job, "next_run_time", None)) if getattr(job, "next_run_time", None) else None,
            "next_run_time": str(getattr(job, "next_run_time", None)) if getattr(job, "next_run_time", None) else "Paused",
            "status": "paused" if job.id in _PAUSED_JOB_IDS else "scheduled",
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
                "username": username,
                "private_key_path": private_key_path,
                "password": password,
                "asset_id": asset_id,
                "target_scope": target_scope,
                "scope_value": scope_value,
                "template_id": template_id,
                "notification_channel": notification_channel,
                "retry_count": max(0, int(retry_count or 0)),
                "cron_expr": cron_expr,
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
        if not scheduler.get_job(job_id):
            raise KeyError(job_id)
        CronManager.add_inspection_job(job_id=job_id, **kwargs)
        return CronManager.get_job(job_id)

    @staticmethod
    def pause_job(job_id: str) -> dict:
        scheduler.pause_job(job_id)
        _PAUSED_JOB_IDS.add(job_id)
        return CronManager.get_job(job_id)

    @staticmethod
    def resume_job(job_id: str) -> dict:
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
    def remove_job(job_id: str):
        scheduler.remove_job(job_id)
        _PAUSED_JOB_IDS.discard(job_id)

# 调度器由 FastAPI lifespan 在事件循环内启动；单元测试/脚本导入不启动。
