import os
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import admin, ai, auth, catalog, exams, knowledge, papers, plan, practice, review, vocab, wrongbook
from app.core.auth import current_user

# 本地源码布局: <root>/backend/app/main.py -> BACKEND_DIR=backend, PROJECT_ROOT=root
# 容器布局:     /app/app/main.py          -> BACKEND_DIR=/app, PROJECT_ROOT=/app（frontend 在其中）
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR if (BACKEND_DIR / "frontend").is_dir() else BACKEND_DIR.parent
# 反向代理子路径（如 nginx /kaoyan/ -> 本服务），由环境变量 APP_PREFIX 注入，默认根路径
APP_PREFIX = os.environ.get("APP_PREFIX", "").rstrip("/")

app = FastAPI(title="考研助手", docs_url=APP_PREFIX + "/api/docs")


@app.middleware("http")
async def no_cache_html(request, call_next):
    """HTML 不缓存（发版即生效）；带哈希的静态资源交给浏览器长缓存。"""
    resp = await call_next(request)
    if "text/html" in resp.headers.get("content-type", ""):
        resp.headers["Cache-Control"] = "no-cache"
    return resp

app.include_router(auth.router, prefix=APP_PREFIX)
for r in (
    catalog.router, papers.router, exams.router, practice.router,
    wrongbook.router, ai.router, review.router, vocab.router, plan.router, admin.router,
    knowledge.router,
):
    app.include_router(r, prefix=APP_PREFIX, dependencies=[Depends(current_user)])


@app.get(APP_PREFIX + "/api/health")
def health():
    return {"ok": True}


# 原卷切片 / 作文图表（注意：/assets 留给前端构建产物，这里用 /paper-assets 避免路由冲突）
# 目录可能由容器运行时挂载提供（晚于/早于 import 均有可能），故无条件挂载 + check_dir=False
assets_dir = PROJECT_ROOT / "data/assets"
app.mount(APP_PREFIX + "/paper-assets", StaticFiles(directory=assets_dir, check_dir=False), name="paper-assets")

# 前端构建产物（生产模式同源部署）
dist_dir = PROJECT_ROOT / "frontend/dist"
if dist_dir.is_dir():
    app.mount(APP_PREFIX + "/", StaticFiles(directory=dist_dir, html=True), name="frontend")
