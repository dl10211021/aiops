import paramiko
import uuid
import logging
import threading
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
        self._sessions_lock = threading.Lock()
        # 线程池隔离执行防止死锁阻塞协程
        self.executor = ThreadPoolExecutor(max_workers=10)

    def connect(
        self,
        host: str,
        port: int,
        username: str,
        password: str | None = None,
        key_filename: str | None = None,
        allow_modifications: bool = False,
        active_skills: list[str] | None = None,
        agent_profile: str = "default",
        remark: str = "",
        asset_type: str = "ssh",
        extra_args: dict | None = None,
        lazy: bool = False,
        tags: list[str] | None = None,
        target_scope: str = "asset",
        scope_value: str | None = None,
    ) -> dict:
        """建立一个新的 SSH 连接或虚拟资产凭据会话"""
        if not tags:
            tags = ["未分组"]
        if not active_skills:
            active_skills = []  # 【解除绑定】不再强行绑定 linux_basic，让用户自由决定
        if extra_args is None:
            extra_args = {}
        if not asset_type:
            asset_type = "ssh"

        import hashlib

        unique_str = f"{asset_type}_{username}@{host}:{port}"
        session_id = str(uuid.UUID(hashlib.md5(unique_str.encode()).hexdigest()))

        # 安全加固：如果该主机已有连接，先释放旧连接的资源，防止连接泄漏
        with self._sessions_lock:
            if session_id in self.active_sessions:
                old_client = self.active_sessions[session_id].get("client")
                if old_client:
                    try:
                        old_client.close()
                    except Exception:
                        pass
                del self.active_sessions[session_id]

        # 核心逻辑分离：如果不是 SSH，就不去尝试 paramiko 连接，只做凭证登记
        if asset_type != "ssh":
            logger.info(
                f"Registered Virtual Asset [{asset_type}] -> {username}@{host}:{port} (Profile: {agent_profile}, Extra: {extra_args})"
            )
            with self._sessions_lock:
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
                        "asset_type": asset_type,
                        "extra_args": extra_args,
                        "tags": tags,
                        "target_scope": target_scope,
                        "scope_value": scope_value,
                        "is_virtual": True,
                        "heartbeat_enabled": False,
                        "last_active": time.time(),
                        "pending_messages": [],
                    },
                }
            return {
                "success": True,
                "session_id": session_id,
                "message": f"{asset_type.upper()} 资产已成功纳管登记",
            }

        # 如果开启了惰性加载 (lazy)，则只保存配置，不实际发起物理连接
        if lazy:
            logger.info(
                f"Registered Lazy SSH Asset -> {username}@{host}:{port} (Profile: {agent_profile})"
            )
            with self._sessions_lock:
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
                        "asset_type": "ssh",
                        "extra_args": extra_args,
                        "tags": tags,
                        "target_scope": target_scope,
                        "scope_value": scope_value,
                        "is_virtual": False,
                        "heartbeat_enabled": False,
                        "last_active": time.time() - 1000,  # 初始化为较早时间
                        "pending_messages": [],
                    },
                }
            return {
                "success": True,
                "session_id": session_id,
                "message": "惰性连接注册成功",
            }

        # 以下是原生的 SSH 连接逻辑
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            logger.info(
                f"Attempting to connect via SSH to {username}@{host}:{port} (Profile: {agent_profile}, Mod: {allow_modifications})..."
            )
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                key_filename=key_filename,
                timeout=10,  # 超时时间 10 秒
                banner_timeout=30,
            )

            with self._sessions_lock:
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
                        "asset_type": "ssh",
                        "extra_args": extra_args,
                        "tags": tags,
                        "target_scope": target_scope,
                        "scope_value": scope_value,
                        "is_virtual": False,
                        "heartbeat_enabled": False,
                        "last_active": time.time(),
                        "pending_messages": [],
                    },
                }
            logger.info(f"Connected successfully. Session ID: {session_id}")
            return {"success": True, "session_id": session_id, "message": "连接成功"}

        except paramiko.AuthenticationException:
            logger.error("Authentication failed.")
            return {"success": False, "message": "认证失败：用户名或密码错误"}
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return {"success": False, "message": f"连接异常: {str(e)}"}

    def connect_local(
        self,
        agent_profile: str = "default",
        active_skills: list[str] | None = None,
        remark: str = "",
    ) -> dict:
        """【本地总控】建立一个本地虚拟会话，不需要 SSH 目标机器。专供跑监控脚本的大模型使用。"""
        if not active_skills:
            active_skills = []  # 【解除绑定】

        session_id = str(uuid.uuid4())
        with self._sessions_lock:
            self.active_sessions[session_id] = {
                "client": None,  # 空 Client，因为不连远程
                "info": {
                    "host": "localhost",
                    "port": 0,
                    "username": "opscore_agent",
                    "password": "",
                    "connected_at": time.time(),
                    "allow_modifications": True,  # 本地脚本肯定需要执行权限
                    "active_skills": active_skills,
                    "agent_profile": agent_profile,
                    "remark": remark,
                    "asset_type": "virtual",
                    "extra_args": {},
                    "tags": ["本地会话"],
                    "is_virtual": True,
                    "heartbeat_enabled": False,
                    "last_active": time.time(),
                    "pending_messages": [],
                },
            }
        logger.info(f"Local Virtual Session Established. Session ID: {session_id}")
        return {
            "success": True,
            "session_id": session_id,
            "message": "本地虚拟会话就绪",
        }

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
            except Exception:
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
                banner_timeout=30,
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
            return {
                "success": False,
                "error": "当前为监控专用的【本地宿主机虚拟会话】，请使用 `local_execute_script` 工具去执行 `manage-engine` 卡带中的 Python 脚本，而不要调用 `linux_execute_command`。",
            }

        client = self._get_or_create_client(session_id)
        if not client:
            return {
                "success": False,
                "error": "无法建立或恢复到目标机器的物理连接。请检查网络或凭证。",
            }

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

            start_time = time.time()
            while not stdout.channel.exit_status_ready():
                if time.time() - start_time > timeout:
                    stdout.channel.close()
                    return {
                        "success": False,
                        "error": f"指令执行超时 (超过 {timeout} 秒) 已被系统强行中断。",
                    }
                time.sleep(0.5)

            # 读取输出（限制最大读取 5MB 防止内存耗尽，匹配大模型 1M Token 能力）
            exit_status = stdout.channel.recv_exit_status()  # 获取退出状态码
            output = (
                stdout.read(5 * 1024 * 1024).decode("utf-8", errors="replace").strip()
            )
            error = (
                stderr.read(5 * 1024 * 1024).decode("utf-8", errors="replace").strip()
            )

            # 将多流合并或者分开返回，供大模型分析
            result_str = output if output else error

            return {
                "success": True,
                "exit_status": exit_status,
                "output": result_str,
                "has_error": bool(error and exit_status != 0),
            }
        except Exception as e:
            return {"success": False, "error": f"指令执行超时或崩溃: {str(e)}"}

    def disconnect(self, session_id: str) -> bool:
        """安全断开连接"""
        with self._sessions_lock:
            if session_id in self.active_sessions:
                client = self.active_sessions[session_id].get("client")
                if client:
                    try:
                        client.close()
                    except Exception:
                        pass
                del self.active_sessions[session_id]
                return True
        return False

    def get_session_snapshot(self) -> dict:
        """线程安全地获取所有会话的快照副本，供心跳和轮询使用"""
        with self._sessions_lock:
            return dict(self.active_sessions)


# 单例模式，保证全局只有一个 Manager
ssh_manager = SSHConnectionManager()
