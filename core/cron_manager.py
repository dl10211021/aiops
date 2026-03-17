import asyncio
import logging
import uuid
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from typing import Dict, Any

logger = logging.getLogger(__name__)

# 配置基于 SQLite 的定时任务存储
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cron_jobs.sqlite")
jobstores = {
    'default': SQLAlchemyJobStore(url=f'sqlite:///{db_path}')
}

# 初始化异步调度器
scheduler = AsyncIOScheduler(jobstores=jobstores)

async def _trigger_proactive_inspection(job_id: str, host: str, agent_profile: str, message: str, username: str, private_key_path: str = None, password: str = None):
    """
    定时任务的实际执行体：
    1. 后台悄悄建立 SSH 会话（模拟连通）。
    2. 将指定的巡检要求（message）发送给大模型处理。
    3. 大模型会自动去执行命令排查，最后根据系统设定，大模型会调用 send_notification 把报告发出去。
    4. 任务结束后清理后台会话。
    """
    logger.info(f"⏰ [CRON JOB {job_id}] 触发巡检任务 -> 目标: {host}, 角色: {agent_profile}")
    
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
             port=22,
             username=username,
             password=password,
             key_filename=private_key_path,
             allow_modifications=True, 
             active_skills=all_skills,
             agent_profile=agent_profile
         )
    
    if not conn_res.get("success"):
        logger.error(f"❌ [CRON JOB {job_id}] SSH 连接 {host} 失败，巡检任务终止。")
        # 此时可以发一个通知告知连接失败...
        return
        
    session_id = conn_res["session_id"]
    logger.info(f"✅ [CRON JOB {job_id}] 成功建立后台隐藏会话: {session_id}")
    
    # 2. 构造强制的系统要求，让 Agent 完成巡检并发送通知
    prompt = f"【系统定时巡检任务】现在是自动巡检时间。请你对当前服务器执行全面的健康检查（如磁盘、CPU、内存、僵尸进程等，或者按照你的角色要求去查）。巡检完毕后，**你必须**调用 `send_notification` 工具，将巡检总结报告发送给团队，渠道请随意选择一个模拟渠道即可。用户原始指令要求：{message}"
    
    # 3. 使用无头 Agent 后台执行巡检，无需消耗 SSE 流
    try:
        result = await asyncio.wait_for(headless_agent_chat(session_id, prompt), timeout=600.0)
        logger.info(f"✅ [CRON JOB {job_id}] AI 巡检完成，摘要: {result[:200] if result else 'N/A'}")
    except asyncio.TimeoutError:
        logger.error(f"❌ [CRON JOB {job_id}] AI 巡检执行超时 (10分钟)")
    except Exception as e:
         logger.error(f"❌ [CRON JOB {job_id}] AI 巡检执行过程中崩溃: {e}")
    finally:
         # 4. 无论成功与否，任务结束后自动销毁这个后台会话，释放服务器连接数
         await asyncio.to_thread(ssh_manager.disconnect, session_id)
         logger.info(f"🔚 [CRON JOB {job_id}] 后台会话 {session_id} 已安全销毁。")

class CronManager:
    """管理系统定时主动巡检任务的门面"""
    
    @staticmethod
    def add_inspection_job(cron_expr: str, host: str, username: str, agent_profile: str, message: str, password: str = None, private_key_path: str = None) -> str:
        """
        添加一个 Cron 定时任务
        :param cron_expr: 标准 cron 表达式，如 "0 9 * * *"
        """
        job_id = f"cron_{uuid.uuid4().hex[:8]}"
        
        # 解析 cron 表达式（APScheduler 格式解析）
        # 这里做个极其简单的拆解：0 9 * * * 对应 minute=0, hour=9
        parts = cron_expr.split()
        if len(parts) != 5:
             raise ValueError("无效的 Cron 表达式，必须是 5 位，例如 '0 9 * * *'")
             
        # APScheduler 的 CronTrigger 使用的是 kwargs，如 minute='0', hour='9', day='*', month='*', day_of_week='*'
        scheduler.add_job(
            _trigger_proactive_inspection,
            trigger='cron',
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            id=job_id,
            args=[job_id, host, agent_profile, message, username, private_key_path, password],
            replace_existing=True,
            misfire_grace_time=3600
        )
        logger.info(f"已注册定时巡检任务 {job_id}，计划：{cron_expr}")
        return job_id
        
    @staticmethod
    def get_all_jobs() -> list:
        jobs = []
        for job in scheduler.get_jobs():
             jobs.append({
                 "id": job.id,
                 "next_run_time": str(job.next_run_time) if job.next_run_time else "Paused",
                 "target_host": job.args[1] if job.args else "Unknown",
                 "agent_profile": job.args[2] if job.args else "Unknown"
             })
        return jobs
        
    @staticmethod
    def remove_job(job_id: str):
        scheduler.remove_job(job_id)

# 确保调度器在导入时已启动
if not scheduler.running:
    scheduler.start()
    logger.info("Cron Scheduler 已启动。")