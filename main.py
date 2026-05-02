import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
import asyncio

from core.request_context import current_request_id
from core.http_middleware_service import (
    SECURITY_HEADERS,
    dispatch_api_token_auth,
    dispatch_request_id,
    dispatch_security_headers,
)
from core.hydration_status_service import (
    HYDRATE_STATUS as hydrate_status,
    finish_hydrate_run,
    record_hydrate_done,
    record_hydrate_success,
    start_hydrate_run,
)
from core.health_service import build_health_status
from core.frontend_entry_service import (
    get_legacy_static_dir,
    get_react_assets_dir,
    resolve_frontend_entry,
)

# Backward-compatible alias for callers that still import main.hydrate_status.

# 在所有模块加载之前加载 .env 文件，确保通知配置等环境变量持久生效
try:
    from dotenv import load_dotenv

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
except ImportError:
    pass  # python-dotenv 未安装则跳过

# 导入上面写好的 API 路由
from api.routes import router as ssh_router


DEFAULT_OPSCORE_HOST = "0.0.0.0"
DEFAULT_OPSCORE_PORT = 8000
LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}
def get_runtime_host() -> str:
    return os.environ.get("OPSCORE_HOST", DEFAULT_OPSCORE_HOST).strip() or DEFAULT_OPSCORE_HOST


def get_runtime_port() -> int:
    raw_port = os.environ.get("OPSCORE_PORT", str(DEFAULT_OPSCORE_PORT)).strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("OPSCORE_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("OPSCORE_PORT must be between 1 and 65535")
    return port


def get_log_level() -> int:
    raw_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    return LOG_LEVELS.get(raw_level, logging.INFO)


_old_log_record_factory = logging.getLogRecordFactory()


def _opscore_log_record_factory(*args, **kwargs):
    record = _old_log_record_factory(*args, **kwargs)
    record.request_id = current_request_id() or "-"
    return record


logging.setLogRecordFactory(_opscore_log_record_factory)
logging.basicConfig(
    level=get_log_level(),
    format="%(asctime)s [%(levelname)s] [request_id=%(request_id)s] %(message)s",
)


async def background_hydrate_assets():
    """后台并发尝试重连历史资产，避免阻塞主服务启动"""
    from core.memory import memory_db
    from connections.ssh_manager import ssh_manager

    assets = await asyncio.to_thread(memory_db.get_all_assets)

    start_hydrate_run(len(assets) if assets else 0)

    async def _connect_single(a):
        try:
            await asyncio.to_thread(
                ssh_manager.connect,
                host=a["host"],
                port=a["port"] or 22,
                username=a["username"] or "",
                password=a["password"],
                allow_modifications=False,
                active_skills=a["skills"],
                agent_profile=a["agent_profile"],
                remark=a["remark"],
                asset_type=a.get("asset_type", "ssh"),
                protocol=a.get("protocol"),
                extra_args=a["extra_args"],
                tags=a.get("tags", ["未分组"]),
                lazy=True,
            )
            record_hydrate_success()
            return True
        except Exception as e:
            logging.error(f"Auto-hydrate failed for {a['host']}: {e}")
            return False
        finally:
            record_hydrate_done()

    if assets:
        results = await asyncio.gather(*[_connect_single(a) for a in assets])
        success_count = sum(1 for r in results if r)
        logging.info(
            f"Auto-hydrated {success_count}/{len(assets)} assets from database in background."
        )

    finish_hydrate_run()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    from core.heartbeat import start_heartbeat
    from core.cron_manager import CronManager

    start_heartbeat()
    logging.info("Heartbeat worker started.")
    CronManager.start_scheduler()

    # 将长耗时的资产重连放入后台并发执行，防止拖死应用启动
    asyncio.create_task(background_hydrate_assets())

    yield
    # Shutdown actions
    logging.info("OpsCore Backend shutting down...")


# ------------- 初始化 FastAPI 实例 -------------
app = FastAPI(
    title="OpsCore API (Linux Connection MVP)",
    description="AIOps 平台后端核心：支持状态保持的远程资产连接与指令分发",
    version="1.0",
    lifespan=lifespan,
)

from fastapi.staticfiles import StaticFiles

allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "OPSCORE_ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# ------------- 跨域配置 -------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    return await dispatch_request_id(request, call_next)


@app.middleware("http")
async def api_token_auth(request: Request, call_next):
    token = os.environ.get("OPSCORE_API_TOKEN", "")
    return await dispatch_api_token_auth(request, call_next, token)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    return await dispatch_security_headers(request, call_next)

import sys


# 判断是否是由 PyInstaller 打包运行的
def get_base_path():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(__file__)


# ------------- 挂载静态文件目录 (旧版保留) -------------
static_dir = get_legacy_static_dir(get_base_path())
if static_dir:
    app.mount("/static", StaticFiles(directory=static_dir), name="static_legacy")

# ------------- 注册核心 API 路由 -------------
app.include_router(ssh_router, prefix="/api/v1", tags=["OpsCore APIs"])

from fastapi.responses import HTMLResponse

# ------------- React 前端静态资源 (Vite build) -------------
react_assets = get_react_assets_dir(get_base_path())
if react_assets:
    app.mount("/assets", StaticFiles(directory=react_assets), name="react_assets")


# ------------- 健康检查与前端页面 -------------
@app.get("/healthz")
def healthz():
    """Production health check endpoint for load balancers and container probes."""
    return build_health_status(
        base_path=get_base_path(),
        root_dir=os.path.dirname(__file__),
        version=app.version,
    )


@app.get("/", response_class=HTMLResponse)
def index():
    """优先返回 React 构建产物，降级到旧版 HTML"""
    entry = resolve_frontend_entry(get_base_path())
    if entry.html is not None:
        return HTMLResponse(content=entry.html)
    return entry.fallback


if __name__ == "__main__":
    # 启动后端服务
    runtime_host = get_runtime_host()
    runtime_port = get_runtime_port()
    display_host = "localhost" if runtime_host in {"0.0.0.0", "::"} else runtime_host
    print(f"\n[START] OpsCore Backend is starting on http://{display_host}:{runtime_port}")
    print(f"[INFO] You can visit http://{display_host}:{runtime_port}/docs for API details\n")
    uvicorn.run("main:app", host=runtime_host, port=runtime_port, reload=False)
