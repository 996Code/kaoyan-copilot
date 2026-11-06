from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import admin, ai, auth, catalog, exams, papers, plan, practice, review, vocab, wrongbook
from app.core.auth import current_user

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

app = FastAPI(title="考研助手", docs_url="/api/docs")


@app.middleware("http")
async def no_cache_html(request, call_next):
    """HTML 不缓存（发版即生效）；带哈希的静态资源交给浏览器长缓存。"""
    resp = await call_next(request)
    if "text/html" in resp.headers.get("content-type", ""):
        resp.headers["Cache-Control"] = "no-cache"
    return resp

app.include_router(auth.router)
for r in (
    catalog.router, papers.router, exams.router, practice.router,
    wrongbook.router, ai.router, review.router, vocab.router, plan.router, admin.router,
):
    app.include_router(r, dependencies=[Depends(current_user)])


@app.get("/api/health")
def health():
    return {"ok": True}


# 原卷切片 / 作文图表（注意：/assets 留给前端构建产物，这里用 /paper-assets 避免路由冲突）
assets_dir = PROJECT_ROOT / "data/assets"
if assets_dir.is_dir():
    app.mount("/paper-assets", StaticFiles(directory=assets_dir), name="paper-assets")

# 前端构建产物（生产模式同源部署）
dist_dir = PROJECT_ROOT / "frontend/dist"
if dist_dir.is_dir():
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
