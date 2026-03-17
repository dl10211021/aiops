import asyncio
import logging
import time
import json

logger = logging.getLogger(__name__)

async def run_single_heartbeat(sid, info, memory_db, dispatcher, trigger_msg=None):
    from core.agent import headless_agent_chat
    try:
        custom_hb_prompt = info.get("extra_args", {}).get("heartbeat_prompt", "")
        protocol = info.get("protocol", "ssh")
        agent_profile = info.get("agent_profile", "default")
        
        if trigger_msg:
            system_alert = trigger_msg
        elif custom_hb_prompt:
            system_alert = f"用户指定了专有的维护/巡检指令：\n{custom_hb_prompt}\n\n请严格执行该指令，并在彻底完成后返回最终结果。"
        else:
            system_alert = f"""当前处于系统的闲置后台时间。作为高级 AIOps 专家，请你利用这段时间进行**深度的自主运维与自我进化**，而不仅仅是简单的“健康巡检”。

当前资产类型：{protocol.upper()} ({agent_profile})

【自主运维与进化要求 (极其重要)】：
1. **深度发掘与诊断**：主动探测潜在隐患、性能瓶颈、错误日志。如果发现异常，不要急于汇报，而是**深入挖掘根本原因**。
2. **主动响应与修复**：如果你确认了具体的故障或优化点，并且当前权限允许，请**直接利用你的技能执行修复或优化操作**。
3. **未知识别与自适应进化**：如果你面临的是未知类型的设备（如未适配的安全设备、交换机、数据库或监控平台）：
   - 绝不轻言放弃！你有 `local_execute_script` 工具，允许在本地运行任意的 Python/Shell 脚本。
   - 请**当场编写临时探测脚本**（例如使用 `python -c` 配合 `requests`/`pymysql` 等，或者解析监控网页内容），用该工具执行并分析返回数据。
   - 脚本中请务必使用上下文中提供的目标IP、端口、账号和密码。
   - 如果探测成功，事后请务必主动调用 `evolve_skill` 将这次探索固化成一个新的“技能”，实现自我进化！
4. **重大告警通报**：如果你发现了严重且无法自动修复的故障，请务必使用 `send_notification` 工具立刻向人类管理员发送告警！

请在你认为全部的深度分析、诊断、修复、告警或自我进化都已彻底完成后，以极简的 Markdown 格式输出一份《后台运维摘要》。
**警告：你必须至少调用一次工具（如 linux_execute_command 或 local_execute_script）来获取真实数据，绝不能凭空猜测！** 
说明你刚刚执行了哪些检查、当前的健康状态数据（如 CPU/内存利用率等）。如果不需汇报，请仅输出“【无需汇报】”。"""

        await headless_agent_chat(sid, system_alert)

    except Exception as e:
        logger.error(f"Heartbeat execution failed for {sid}: {e}")
            
    finally:
        info["heartbeat_in_progress"] = False
        info["last_active"] = time.time()

async def heartbeat_worker():
    """后台常驻的巡检任务"""
    from connections.ssh_manager import ssh_manager
    from core.memory import memory_db
    from core.dispatcher import dispatcher
    
    logger.info("Heartbeat worker started polling loop.")

    while True:
        try:
            current_time = time.time()
            logger.info(f"[Heartbeat Tick] active_sessions: {len(ssh_manager.active_sessions)}")
            for sid, sdata in list(ssh_manager.active_sessions.items()):
                info = sdata.get("info", {})
                client = sdata.get("client")
                
                idle_time = current_time - info.get("last_active", 0)

                # 【连接健康检测】: 检查真实 SSH 连接是否仍然存活
                if client is not None and not info.get("is_virtual"):
                    transport = client.get_transport()
                    if transport is None or not transport.is_active():
                        logger.warning(f"💀 [Connection Lost] Session {sid} ({info.get('host')}) SSH 连接已断开！")
                        pending = info.setdefault("pending_messages", [])
                        pending.append(f"⚠️ **[连接断开警告]** 与 `{info.get('host')}` 的 SSH 连接已失效。可能是网络中断或目标服务器重启。建议重新连接。")
                        sdata["client"] = None
                        continue

                # 【连接池回收机制】: 如果闲置超过 10 分钟 (600秒) 且是真实 SSH 连接，则回收物理 Socket，节省内存
                if idle_time > 600 and not info.get("is_virtual") and client is not None:
                    logger.info(f"💤 [Lazy Pool] Session {sid} ({info.get('host')}) 闲置超过 10 分钟，自动回收物理连接。")
                    try:
                        client.close()
                    except Exception:
                        pass
                    sdata["client"] = None
                
                if info.get("heartbeat_in_progress"):
                    continue
                
                logger.info(f"[Heartbeat Poll Loop] Session {sid} idle_time: {idle_time:.1f}s, enabled: {info.get('heartbeat_enabled')}")
                
                if info.get("heartbeat_enabled"):
                    agent_profile = info.get("agent_profile", "default")
                    
                    if agent_profile == "master":
                        # 全局总控指挥官的专属心跳逻辑
                        # 尝试从 extra_args 读取用户配置的心跳间隔（秒），默认 300 秒（5分钟）
                        try:
                            master_interval = int(info.get("extra_args", {}).get("master_interval", 120))
                        except (ValueError, TypeError):
                            master_interval = 120
                            
                        logger.info(f"[Master Debug] ID: {sid}, Idle: {idle_time:.1f}s, Interval: {master_interval}s, InProgress: {info.get('heartbeat_in_progress')}")
                        if idle_time > master_interval:
                            info["last_active"] = current_time
                            info["heartbeat_in_progress"] = True
                            logger.info(f"👑 [Global Heartbeat] 触发全局指挥官主动巡检 (闲置 {idle_time:.1f} 秒, 设定周期 {master_interval} 秒)...")
                            
                            master_trigger_msg = """【🚨 全局主动故障自愈周期】当前为系统闲置期，全域自愈引擎启动。作为【跨系统总控指挥官】，你必须展现出极致的主动性和执行力！这不是一次简单的巡检报告，而是一次真实的“寻找病患并实施手术”的行动。

【自愈行动纲领 (CRITICAL)】：
1. **全域监控雷达扫描 (先找监控平台，再找告警)**：
   - ⚠️ 不要只看你自己挂载的监控技能！你的平台可能接入了多个异构监控系统。
   - **必须**先调用 `list_active_sessions` 工具，遍历当前所有在线的会话。
   - 找出名字或 profile 带有“监控”、“monitor”、“prometheus”、“zabbix”、“卓豪”等字眼的**监控平台 Agent**。
   - 使用 `delegate_task_to_agent`，向找出的**每一个**监控平台子 Agent 发送指令，让它们各自去拉取自己平台下的 Critical/Warning 级别活跃告警！
2. **伤情分级与研判**：
   - 汇总所有监控平台子 Agent 汇报上来的告警，提取出【所有故障主机的 IP】。
   - 对它们进行严重程度排序，决定先救谁（例如：数据库宕机 > 磁盘爆满 > CPU飙高）。
3. **派遣特种部队 (Swarm 协同排查)**：
   - 再次查看 `list_active_sessions` 的结果，确认这些“生病”的故障主机是否在平台纳管中。
   - 对在线的故障主机，**立刻、逐台**使用 `delegate_task_to_agent` 工具派遣运维子 Agent (如 linux/dba) 登入该机器。
   - ⚠️ 任务下达时必须详尽！例如：“你负责的机器被 Prometheus 报磁盘剩余不足 5%，立刻登入使用 df 和 du 找到大文件，清理释放空间，回复处理结果！”
4. **主刀手术 (主动修复)**：
   - 根据排查子 Agent 的分析结果，如果问题明确且在安全可控范围内，你必须**直接下发带有明确处置方案的指令，让其执行修复**！绝不停留在“建议人类去修”阶段。
5. **抢救记录通报**：只有在完成所有的诊断、排查，甚至**修复动作全部结束**后，才输出一份《全网自愈抢救报告》，并对仍未解决的重大隐患使用 `send_notification` 呼叫人类管理员。"""
                            
                            asyncio.create_task(run_single_heartbeat(sid, info, memory_db, dispatcher, trigger_msg=master_trigger_msg))
                    else:
                        # 普通单机运维 Agent 的心跳逻辑
                        try:
                            normal_interval = int(info.get("extra_args", {}).get("heartbeat_interval", 120))
                        except (ValueError, TypeError):
                            normal_interval = 120
                            
                        logger.info(f"[Heartbeat Poll] Session {sid} idle_time: {idle_time:.1f}s, interval: {normal_interval}s, enabled: {info.get('heartbeat_enabled')}")
                        if idle_time > normal_interval:
                            # 更新时间，防止重复触发
                            info["last_active"] = current_time
                            info["heartbeat_in_progress"] = True
                            logger.info(f"❤️ [Heartbeat] 主动唤醒 Session {sid} 进行单机健康巡检... (闲置 {idle_time:.1f} 秒)")
                            
                            # 开启并发异步任务去执行，防止互相阻塞
                            asyncio.create_task(run_single_heartbeat(sid, info, memory_db, dispatcher))
                        
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")

        # Adaptive sleep: if no sessions have heartbeat enabled, sleep longer to save resources
        any_heartbeat_enabled = any(
            sdata.get("info", {}).get("heartbeat_enabled", False)
            for sdata in list(ssh_manager.active_sessions.values())
        )
        await asyncio.sleep(10 if any_heartbeat_enabled else 30)

def start_heartbeat():
    asyncio.create_task(heartbeat_worker())
