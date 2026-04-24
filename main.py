import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
import asyncio

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

# 设置基本日志格式，方便本地控制台看
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
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

    start_heartbeat()
    logging.info("Heartbeat worker started.")

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

# ------------- 跨域配置 (本地开发必须开启) -------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许你的前端 HTML 跨域访问
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    print("\n[START] OpsCore Backend is starting on http://localhost:8000")
    print("[INFO] You can visit http://localhost:8000/docs for API details\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
