import os
import codecs

def patch_agent():
    fpath = "core/agent.py"
    with codecs.open(fpath, "r", "utf-8") as f:
        c = f.read()

    # 1. timeout
    c = c.replace("timeout=120.0", "timeout=600.0")
    c = c.replace("timeout=30.0", "timeout=600.0")

    # 2. limit
    c = c.replace("for iteration in range(15):", "for iteration in range(50):")
    c = c.replace("for iteration in range(10):", "for iteration in range(50):")
    c = c.replace("最大 15 轮", "最大 50 轮")
    c = c.replace("最大 10 轮", "最大 50 轮")
    c = c.replace("提升至 120 秒", "提升至 600 秒")

    # 3. compress_and_store_ltm
    c = c.replace(
        "asyncio.create_task(memory_db.compress_and_store_ltm(session_id, client))",
        "asyncio.create_task(memory_db.compress_and_store_ltm(session_id, client, model_name))"
    )

    with codecs.open(fpath, "w", "utf-8") as f:
        f.write(c)

def patch_ssh():
    fpath = "connections/ssh_manager.py"
    # we need to recover the original utf-8 if possible. Since it's untracked, it wasn't affected by git restore.
    # But wait, my previous Get-Content/Set-Content corrupted it.
    # Let me just rewrite it fully.
    code = """import paramiko
import uuid
import logging
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class SSHConnectionManager:
    """
    负责维护与底层 Linux 服务器的 SSH 长连接。
    它不仅提供即时的指令执行能力，还可以扩展心跳维持，以确保 AI 在多轮对话中不会掉线。
    """
    def __init__(self):
        # 存放活动状态的会话 { session_id: {"client": paramiko.SSHClient, "info": dict} }
        self.active_sessions = {}
        # 线程池隔离执行防止死锁阻塞协程
        self.executor = ThreadPoolExecutor(max_workers=10)

    def connect(self, host: str, port: int, username: str, password: str = None, key_filename: str = None, allow_modifications: bool = False, active_skills: list[str] = None, agent_profile: str = "default", remark: str = "", protocol: str = "ssh", extra_args: dict = None, lazy: bool = False, group_name: str = "未分组") -> dict:
        """建立一个新的 SSH 连接或虚拟资产凭据会话"""
        if not active_skills:
            active_skills = [] # 【解除绑定】不再强行绑定 linux_basic，让用户自由决定
        if extra_args is None:
            extra_args = {}
            
        import hashlib
        unique_str = f"{protocol}_{username}@{host}:{port}"
        session_id = str(uuid.UUID(hashlib.md5(unique_str.encode()).hexdigest()))
        
        # 安全加固：如果该主机已有连接，先释放旧连接的资源，防止连接泄漏
        if session_id in self.active_sessions:
            self.disconnect(session_id)
        
        # 核心逻辑分离：如果不是 SSH，就不去尝试 paramiko 连接，只做凭证登记
        if protocol != "ssh":
            logger.info(f"Registered Virtual Asset [{protocol}] -> {username}@{host}:{port} (Profile: {agent_profile}, Extra: {extra_args})")
            self.active_sessions[session_id] = {
                "client": None,  # 空 Client，防止报错
                "info": {
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": password,
                    "connected_at": time.time(),
                    "allow_modifications": allow_modifications,
                    "active_skills": active_skills,
                    "agent_profile": agent_profile,
                    "remark": remark,
                    "protocol": protocol,
                    "extra_args": extra_args,
                    "group_name": group_name,
                    "is_virtual": True,
                    "heartbeat_enabled": False,
                    "last_active": time.time(),
                    "pending_messages": []
                }
            }
            return {"success": True, "session_id": session_id, "message": f"{protocol.upper()} 资产已成功纳管登记"}

        # 如果开启了惰性加载 (lazy)，则只保存配置，不实际发起物理连接
        if lazy:
            logger.info(f"Registered Lazy SSH Asset -> {username}@{host}:{port} (Profile: {agent_profile})")
            self.active_sessions[session_id] = {
                "client": None,
                "info": {
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": password,
                    "connected_at": time.time(),
                    "allow_modifications": allow_modifications,
                    "active_skills": active_skills,
                    "agent_profile": agent_profile,
                    "remark": remark,
                    "protocol": "ssh",
                    "extra_args": extra_args,
                    "group_name": group_name,
                    "is_virtual": False,
                    "heartbeat_enabled": False,
                    "last_active": time.time() - 1000, # 初始化为较早时间
                    "pending_messages": []
                }
            }
            return {"success": True, "session_id": session_id, "message": "惰性连接注册成功"}
            
        # 以下是原生的 SSH 连接逻辑
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            logger.info(f"Attempting to connect via SSH to {username}@{host}:{port} (Profile: {agent_profile}, Mod: {allow_modifications})...")
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                key_filename=key_filename,
                timeout=10, # 超时时间 10 秒
                banner_timeout=30
            )
            
            self.active_sessions[session_id] = {
                "client": client,
                "info": {
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": password,
                    "connected_at": time.time(),
                    "allow_modifications": allow_modifications,
                    "active_skills": active_skills,
                    "agent_profile": agent_profile,
                    "remark": remark,
                    "protocol": "ssh",
                    "extra_args": extra_args,
                    "group_name": group_name,
                    "is_virtual": False,
                    "heartbeat_enabled": False,
                    "last_active": time.time(),
                    "pending_messages": []
                }
            }
            logger.info(f"Connected successfully. Session ID: {session_id}")
            return {"success": True, "session_id": session_id, "message": "连接成功"}
            
        except paramiko.AuthenticationException:
            logger.error("Authentication failed.")
            return {"success": False, "message": "认证失败：用户名或密码错误"}
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return {"success": False, "message": f"连接异常: {str(e)}"}

    def connect_local(self, agent_profile: str = "default", active_skills: list[str] = None, remark: str = "") -> dict:
        """【本地总控】建立一个本地虚拟会话，不需要 SSH 目标机器。专供跑监控脚本的大模型使用。"""
        if not active_skills:
            active_skills = [] # 【解除绑定】
            
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            "client": None,  # 空 Client，因为不连远程
            "info": {
                "host": "localhost",
                "username": "opscore_agent",
                "connected_at": time.time(),
                "allow_modifications": True, # 本地脚本肯定需要执行权限
                "active_skills": active_skills,
                "agent_profile": agent_profile,
                "remark": remark,
                "is_virtual": True
            }
        }
        logger.info(f"Local Virtual Session Established. Session ID: {session_id}")
        return {"success": True, "session_id": session_id, "message": "本地虚拟会话就绪"}

    def _get_or_create_client(self, session_id: str):
        """获取真实的物理连接。如果断开了，就用保存的凭证重新连。"""
        if session_id not in self.active_sessions:
            return None
            
        session_data = self.active_sessions[session_id]
        info = session_data["info"]
        
        if info.get("is_virtual"):
            return None
            
        client = session_data.get("client")
        
        # 简单检查连接是否还活着
        is_active = False
        if client:
            try:
                transport = client.get_transport()
                if transport and transport.is_active():
                    is_active = True
            except:
                pass
                
        if is_active:
            # 更新最后活跃时间
            info["last_active"] = time.time()
            return client
            
        # 如果走到这里，说明 client 是 None 或者连接已死，需要重新建立（惰性重连）
        logger.info(f"🚀 [Lazy Pool] 正在唤醒物理连接至 {info['host']}...")
        new_client = paramiko.SSHClient()
        new_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            new_client.connect(
                hostname=info["host"],
                port=info["port"],
                username=info["username"],
                password=info.get("password"),
                timeout=10,
                banner_timeout=30
            )
            session_data["client"] = new_client
            info["last_active"] = time.time()
            return new_client
        except Exception as e:
            logger.error(f"❌ [Lazy Pool] 重连 {info['host']} 失败: {e}")
            return None

    def execute_command(self, session_id: str, command: str, timeout: int = 30) -> dict:
        """
        在指定的长连接 Session 中执行系统指令，并获取返回结果（阻塞式）。
        这也就是以后大模型 Skills 工具调用的实际执行体。
        """
        if session_id not in self.active_sessions:
            return {"success": False, "error": "会话已过期或不存在，请重新连接"}
            
        info = self.active_sessions[session_id]["info"]
        if info.get("is_virtual"):
             return {"success": False, "error": "当前为监控专用的【本地宿主机虚拟会话】，请使用 `local_execute_script` 工具去执行 `manage-engine` 卡带中的 Python 脚本，而不要调用 `linux_execute_command`。"}
             
        client = self._get_or_create_client(session_id)
        if not client:
            return {"success": False, "error": "无法建立或恢复到目标机器的物理连接。请检查网络或凭证。"}
        
        # 将实际执行放入线程池，避免死锁
        future = self.executor.submit(self._do_execute, client, command, timeout)
        try:
            return future.result(timeout=timeout + 5)
        except Exception as e:
            return {"success": False, "error": f"指令执行超时或崩溃: {str(e)}"}

    def _do_execute(self, client, command: str, timeout: int) -> dict:
        try:
            # 开启通道执行命令
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            
            # 引入非阻塞的超时循环等待机制，防止 AI 运行 top 等挂起命令导致线程池死锁
            import time
            start_time = time.time()
            while not stdout.channel.exit_status_ready():
                if time.time() - start_time > timeout:
                    stdout.channel.close()
                    return {"success": False, "error": f"指令执行超时 (超过 {timeout} 秒) 已被系统强行中断。"}
                time.sleep(0.5)
                
            # 读取输出（限制最大读取 5MB 防止内存耗尽，匹配大模型 1M Token 能力）
            exit_status = stdout.channel.recv_exit_status() # 获取退出状态码
            output = stdout.read(5 * 1024 * 1024).decode('utf-8', errors='replace').strip()
            error = stderr.read(5 * 1024 * 1024).decode('utf-8', errors='replace').strip()
            
            # 将多流合并或者分开返回，供大模型分析
            result_str = output if output else error
            
            return {
                "success": True,
                "exit_status": exit_status,
                "output": result_str,
                "has_error": bool(error and exit_status != 0)
            }
        except Exception as e:
            return {"success": False, "error": f"指令执行超时或崩溃: {str(e)}"}

    def disconnect(self, session_id: str) -> bool:
        """安全断开连接"""
        if session_id in self.active_sessions:
            if self.active_sessions[session_id]["client"]:
                self.active_sessions[session_id]["client"].close()
            del self.active_sessions[session_id]
            return True
        return False

# 单例模式，保证全局只有一个 Manager
ssh_manager = SSHConnectionManager()
"""
    with codecs.open(fpath, "w", "utf-8") as f:
        f.write(code)

patch_agent()
patch_ssh()
print("Patch applied.")
