"""
FastAPI主应用
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine, get_db
from app.api import auth, files, collection, users
from app.scheduler import setup_scheduler
from app.utils.logger import setup_logger
from app.utils.search import create_fts_table

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时执行
    logger.info("应用启动中...")
    
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表已创建/更新")
    
    # 创建全文搜索表
    try:
        db = next(get_db())
        create_fts_table(db)
        db.close()
        logger.info("全文搜索表已创建/更新")
    except Exception as e:
        logger.warning(f"创建全文搜索表失败: {e}")
    
    # 启动任务调度器
    scheduler = setup_scheduler()
    logger.info("任务调度器已启动")
    
    yield
    
    # 关闭时执行
    logger.info("应用关闭中...")
    if scheduler:
        scheduler.stop()
    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="学习资料聚合平台 API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS（跨域资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(collection.router)
app.include_router(users.router)

# 挂载前端静态文件（如果前端文件在项目目录中）
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    # 挂载 CSS 文件
    css_path = frontend_path / "css"
    if css_path.exists():
        app.mount("/static", StaticFiles(directory=str(css_path)), name="static")
    
    # 挂载组件文件
    components_path = frontend_path / "components"
    if components_path.exists():
        app.mount("/components", StaticFiles(directory=str(components_path)), name="components")
    
    # 挂载 JS 文件
    js_path = frontend_path / "js"
    if js_path.exists():
        app.mount("/js", StaticFiles(directory=str(js_path)), name="js")
    
    # 提供 index.html
    @app.get("/")
    async def root():
        from fastapi.responses import FileResponse
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {
            "message": "学习资料聚合平台 API",
            "version": "1.0.0",
            "docs": "/docs"
        }
    
    @app.get("/index.html")
    async def index():
        from fastapi.responses import FileResponse
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="前端文件未找到")
else:
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": "学习资料聚合平台 API",
            "version": "1.0.0",
            "docs": "/docs"
        }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.exception(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )