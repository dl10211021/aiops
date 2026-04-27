import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager, closing
import asyncio
import sqlite3

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
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-Permitted-Cross-Domain-Policies": "none",
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


# 设置基本日志格式，方便本地控制台看
logging.basicConfig(
    level=get_log_level(), format="%(asctime)s [%(levelname)s] %(message)s"
)

# 资产重连状态跟踪，供前端查询
hydrate_status = {"total": 0, "done": 0, "success": 0, "running": False}


async def background_hydrate_assets():
    """后台并发尝试重连历史资产，避免阻塞主服务启动"""
    from core.memory import memory_db
    from connections.ssh_manager import ssh_manager

    assets = await asyncio.to_thread(memory_db.get_all_assets)

    hydrate_status["total"] = len(assets) if assets else 0
    hydrate_status["done"] = 0
    hydrate_status["success"] = 0
    hydrate_status["running"] = True

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
            hydrate_status["success"] += 1
            return True
        except Exception as e:
            logging.error(f"Auto-hydrate failed for {a['host']}: {e}")
            return False
        finally:
            hydrate_status["done"] += 1

    if assets:
        results = await asyncio.gather(*[_connect_single(a) for a in assets])
        success_count = sum(1 for r in results if r)
        logging.info(
            f"Auto-hydrated {success_count}/{len(assets)} assets from database in background."
        )

    hydrate_status["running"] = False


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
async def api_token_auth(request: Request, call_next):
    if request.url.path.startswith("/api/v1/") and request.method != "OPTIONS":
        from core.security import is_authorized_request

        token = os.environ.get("OPSCORE_API_TOKEN", "")
        if not is_authorized_request(request.headers, token):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid OpsCore API token"},
            )
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        if header not in response.headers:
            response.headers[header] = value
    return response

import sys


# 判断是否是由 PyInstaller 打包运行的
def get_base_path():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(__file__)


# ------------- 挂载静态文件目录 (旧版保留) -------------
static_dir = os.path.join(get_base_path(), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static_legacy")

# ------------- 注册核心 API 路由 -------------
app.include_router(ssh_router, prefix="/api/v1", tags=["OpsCore APIs"])

from fastapi.responses import HTMLResponse

# ------------- React 前端静态资源 (Vite build) -------------
react_dir = os.path.join(get_base_path(), "static_react")
react_assets = os.path.join(react_dir, "assets")
if os.path.exists(react_assets):
    app.mount("/assets", StaticFiles(directory=react_assets), name="react_assets")


# ------------- 健康检查与前端页面 -------------
@app.get("/healthz")
def healthz():
    """Production health check endpoint for load balancers and container probes."""
    base_path = get_base_path()
    root_dir = os.path.dirname(__file__)
    db_path = os.path.join(root_dir, "opscore.db")
    cron_db_path = os.path.join(root_dir, "cron_jobs.sqlite")
    react_index = os.path.join(base_path, "static_react", "index.html")

    checks = {
        "database": {"status": "ok", "path": "opscore.db"},
        "cron_store": {"status": "ok", "path": "cron_jobs.sqlite"},
        "storage": {"status": "ok", "path": root_dir},
        "frontend": {"status": "ok" if os.path.exists(react_index) else "warning"},
        "hydrate": dict(hydrate_status),
    }

    try:
        with closing(sqlite3.connect(db_path, timeout=2)) as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        checks["database"] = {"status": "error", "path": "opscore.db", "error": str(e)}

    try:
        if os.path.exists(cron_db_path):
            with closing(sqlite3.connect(cron_db_path, timeout=2)) as conn:
                conn.execute("SELECT 1")
        else:
            checks["cron_store"] = {"status": "ok", "path": "cron_jobs.sqlite", "message": "not initialized"}
    except Exception as e:
        checks["cron_store"] = {"status": "error", "path": "cron_jobs.sqlite", "error": str(e)}

    if not os.access(root_dir, os.W_OK):
        checks["storage"] = {"status": "error", "path": root_dir, "error": "not writable"}

    overall = "ok"
    if any(item.get("status") == "error" for item in checks.values() if isinstance(item, dict)):
        overall = "error"
    elif any(item.get("status") == "warning" for item in checks.values() if isinstance(item, dict)):
        overall = "warning"

    return {
        "status": overall,
        "service": "opscore-aiops",
        "version": app.version,
        "checks": checks,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    """优先返回 React 构建产物，降级到旧版 HTML"""
    react_index = os.path.join(get_base_path(), "static_react", "index.html")
    if os.path.exists(react_index):
        with open(react_index, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    html_path = os.path.join(get_base_path(), "frontend_demo.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {"status": "ok", "message": "Backend is running."}


if __name__ == "__main__":
    # 启动后端服务
    runtime_host = get_runtime_host()
    runtime_port = get_runtime_port()
    display_host = "localhost" if runtime_host in {"0.0.0.0", "::"} else runtime_host
    print(f"\n[START] OpsCore Backend is starting on http://{display_host}:{runtime_port}")
    print(f"[INFO] You can visit http://{display_host}:{runtime_port}/docs for API details\n")
    uvicorn.run("main:app", host=runtime_host, port=runtime_port, reload=False)
