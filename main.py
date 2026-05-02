import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.http_middleware_service import (
    SECURITY_HEADERS,
    dispatch_api_token_auth,
    dispatch_request_id,
    dispatch_security_headers,
)
from core.hydration_status_service import (
    HYDRATE_STATUS as hydrate_status,
)
from core.asset_hydration_service import hydrate_assets
from core.health_service import build_health_status
from core.frontend_entry_service import (
    get_legacy_static_dir,
    get_react_assets_dir,
    resolve_frontend_entry,
)
from core.runtime_config_service import (
    DEFAULT_OPSCORE_HOST,
    DEFAULT_OPSCORE_PORT,
    get_allowed_origins,
    get_log_level,
    get_runtime_host,
    get_runtime_port,
)
from core.application_lifecycle_service import start_app_services, stop_app_services
from core.logging_service import configure_logging

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


configure_logging(get_log_level())


async def background_hydrate_assets():
    """后台并发尝试重连历史资产，避免阻塞主服务启动"""
    await hydrate_assets()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_app_services(hydration_runner=background_hydrate_assets)
    yield
    stop_app_services()


# ------------- 初始化 FastAPI 实例 -------------
app = FastAPI(
    title="OpsCore API (Linux Connection MVP)",
    description="AIOps 平台后端核心：支持状态保持的远程资产连接与指令分发",
    version="1.0",
    lifespan=lifespan,
)

from fastapi.staticfiles import StaticFiles

allowed_origins = get_allowed_origins()

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
