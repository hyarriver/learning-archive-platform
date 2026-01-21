"""
采集管理API
"""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db, CollectionSource, CollectionLog
from app.api.dependencies import get_current_user
from app.scheduler import get_scheduler
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/collection", tags=["collection"])


class CollectionSourceCreate(BaseModel):
    """采集源创建模型"""
    name: str
    url_pattern: str
    source_type: str  # 'webpage' or 'video'
    crawler_config: Optional[dict] = None
    search_params: Optional[dict] = None  # 搜索参数，如 {"keyword": "Python", "page": "1"}
    enabled: bool = True


class CollectionSourceUpdate(BaseModel):
    """采集源更新模型"""
    name: Optional[str] = None
    url_pattern: Optional[str] = None
    source_type: Optional[str] = None
    crawler_config: Optional[dict] = None
    search_params: Optional[dict] = None  # 搜索参数
    enabled: Optional[bool] = None


class CollectionSourceInfo(BaseModel):
    """采集源信息模型"""
    id: int
    name: str
    url_pattern: str
    source_type: str
    crawler_config: Optional[dict]
    search_params: Optional[dict] = None  # 搜索参数
    enabled: bool
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/sources", response_model=List[CollectionSourceInfo])
async def list_sources(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取所有采集源列表
    
    Args:
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        采集源列表
    """
    sources = db.query(CollectionSource).all()
    
    result = []
    for source in sources:
        crawler_config = None
        if source.crawler_config:
            try:
                crawler_config = json.loads(source.crawler_config)
            except json.JSONDecodeError:
                pass
        
        search_params = None
        if source.search_params:
            try:
                search_params = json.loads(source.search_params)
            except json.JSONDecodeError:
                pass
        
        result.append(CollectionSourceInfo(
            id=source.id,
            name=source.name,
            url_pattern=source.url_pattern,
            source_type=source.source_type,
            crawler_config=crawler_config,
            search_params=search_params,
            enabled=source.enabled,
            created_at=source.created_at.isoformat() if source.created_at else None,
            updated_at=source.updated_at.isoformat() if source.updated_at else None
        ))
    
    return result


@router.post("/sources", response_model=CollectionSourceInfo)
async def create_source(
    source_data: CollectionSourceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    创建采集源
    
    Args:
        source_data: 采集源数据
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        创建的采集源信息
    """
    # 验证源类型
    if source_data.source_type not in ['webpage', 'video']:
        raise HTTPException(status_code=400, detail="源类型必须是 'webpage' 或 'video'")
    
    # 准备爬虫配置JSON
    crawler_config_str = None
    if source_data.crawler_config:
        crawler_config_str = json.dumps(source_data.crawler_config, ensure_ascii=False)
    
    # 准备搜索参数JSON
    search_params_str = None
    if source_data.search_params:
        search_params_str = json.dumps(source_data.search_params, ensure_ascii=False)
    
    # 创建采集源
    source = CollectionSource(
        name=source_data.name,
        url_pattern=source_data.url_pattern,
        source_type=source_data.source_type,
        crawler_config=crawler_config_str,
        search_params=search_params_str,
        enabled=source_data.enabled
    )
    
    db.add(source)
    db.commit()
    db.refresh(source)
    
    logger.info(f"创建采集源: {source.name}")
    
    crawler_config = None
    if source.crawler_config:
        try:
            crawler_config = json.loads(source.crawler_config)
        except json.JSONDecodeError:
            pass
    
    search_params = None
    if source.search_params:
        try:
            search_params = json.loads(source.search_params)
        except json.JSONDecodeError:
            pass
    
    return CollectionSourceInfo(
        id=source.id,
        name=source.name,
        url_pattern=source.url_pattern,
        source_type=source.source_type,
        crawler_config=crawler_config,
        search_params=search_params,
        enabled=source.enabled,
        created_at=source.created_at.isoformat() if source.created_at else None,
        updated_at=source.updated_at.isoformat() if source.updated_at else None
    )


@router.put("/sources/{source_id}", response_model=CollectionSourceInfo)
async def update_source(
    source_id: int,
    source_data: CollectionSourceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    更新采集源
    
    Args:
        source_id: 采集源ID
        source_data: 更新数据
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        更新后的采集源信息
        
    Raises:
        HTTPException: 如果采集源不存在
    """
    source = db.query(CollectionSource).filter(CollectionSource.id == source_id).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="采集源不存在")
    
    # 更新字段
    if source_data.name is not None:
        source.name = source_data.name
    if source_data.url_pattern is not None:
        source.url_pattern = source_data.url_pattern
    if source_data.source_type is not None:
        if source_data.source_type not in ['webpage', 'video']:
            raise HTTPException(status_code=400, detail="源类型必须是 'webpage' 或 'video'")
        source.source_type = source_data.source_type
    if source_data.crawler_config is not None:
        source.crawler_config = json.dumps(source_data.crawler_config, ensure_ascii=False)
    if source_data.search_params is not None:
        if source_data.search_params:
            source.search_params = json.dumps(source_data.search_params, ensure_ascii=False)
        else:
            source.search_params = None
    if source_data.enabled is not None:
        source.enabled = source_data.enabled
    
    from datetime import datetime
    source.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(source)
    
    logger.info(f"更新采集源: {source.name}")
    
    crawler_config = None
    if source.crawler_config:
        try:
            crawler_config = json.loads(source.crawler_config)
        except json.JSONDecodeError:
            pass
    
    search_params = None
    if source.search_params:
        try:
            search_params = json.loads(source.search_params)
        except json.JSONDecodeError:
            pass
    
    return CollectionSourceInfo(
        id=source.id,
        name=source.name,
        url_pattern=source.url_pattern,
        source_type=source.source_type,
        crawler_config=crawler_config,
        search_params=search_params,
        enabled=source.enabled,
        created_at=source.created_at.isoformat() if source.created_at else None,
        updated_at=source.updated_at.isoformat() if source.updated_at else None
    )


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    删除采集源
    
    Args:
        source_id: 采集源ID
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 如果采集源不存在
    """
    source = db.query(CollectionSource).filter(CollectionSource.id == source_id).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="采集源不存在")
    
    db.delete(source)
    db.commit()
    
    logger.info(f"删除采集源: {source.name}")
    
    return {"message": "采集源已删除"}


@router.post("/sources/{source_id}/trigger")
async def trigger_collection(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    手动触发采集
    
    Args:
        source_id: 采集源ID
        background_tasks: 后台任务
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        触发结果
        
    Raises:
        HTTPException: 如果采集源不存在或调度器未启动
    """
    source = db.query(CollectionSource).filter(CollectionSource.id == source_id).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="采集源不存在")
    
    # 检查采集源是否启用
    if not source.enabled:
        raise HTTPException(status_code=400, detail="该采集源已禁用，无法触发采集。请先启用采集源。")
    
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=500, detail="任务调度器未启动")
    
    # 在后台任务中执行采集，避免阻塞请求
    # 注意：需要创建新的数据库会话，因为后台任务会在请求结束后执行
    async def _run_collection():
        db_gen = get_db()
        db_session = next(db_gen)
        try:
            await scheduler.collect_source(db_session, source)
            logger.info(f"手动触发采集完成: {source.name}")
        except Exception as e:
            error_type = type(e).__name__
            try:
                if hasattr(e, 'args') and e.args and isinstance(e.args[0], str):
                    error_detail = e.args[0][:200]
                else:
                    error_detail = f"{error_type}: 采集失败"
            except Exception:
                error_detail = f"{error_type}: 采集失败"
            logger.error(f"触发采集失败: {source.name}, 错误类型: {error_type}, 错误信息: {error_detail}")
        finally:
            db_session.close()
    
    # 添加到后台任务
    background_tasks.add_task(_run_collection)
    
    return {"message": "采集任务已提交，正在后台执行"}


@router.post("/trigger")
async def trigger_all_collection(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    手动触发所有启用的采集源
    
    Args:
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        触发结果
        
    Raises:
        HTTPException: 如果调度器未启动
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=500, detail="任务调度器未启动")
    
    # 直接执行采集（异步，不会阻塞太久）
    try:
        await scheduler.collect_all_sources()
        logger.info("手动触发所有采集源完成")
        return {"message": "所有采集任务已完成"}
    except Exception as e:
        # 安全地获取错误信息，避免格式化异常对象时触发异步操作
        error_type = type(e).__name__
        try:
            if hasattr(e, 'args') and e.args and isinstance(e.args[0], str):
                error_detail = e.args[0][:200]
            else:
                error_detail = f"{error_type}: 采集失败"
        except Exception:
            error_detail = f"{error_type}: 采集失败"
        
        # 使用 logger.error 而不是 logger.exception
        logger.error(f"触发所有采集失败: 错误类型: {error_type}, 错误信息: {error_detail}")
        raise HTTPException(status_code=500, detail=f"触发采集失败: {error_detail}")


@router.get("/sources/{source_id}/progress")
async def get_collection_progress(
    source_id: int,
    current_user = Depends(get_current_user)
):
    """
    获取采集进度
    
    Args:
        source_id: 采集源ID
        current_user: 当前登录用户
        
    Returns:
        采集进度信息
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=500, detail="任务调度器未启动")
    
    progress = scheduler.get_progress(source_id)
    
    if not progress:
        # 返回默认的空进度
        return {
            "source_id": source_id,
            "status": "idle",
            "progress": 0,
            "message": "暂无采集任务",
            "start_time": None,
            "end_time": None
        }
    
    return {
        "source_id": source_id,
        "status": progress.get("status", "idle"),
        "progress": progress.get("progress", 0),
        "message": progress.get("message", ""),
        "start_time": progress.get("start_time"),
        "end_time": progress.get("end_time")
    }


@router.get("/logs")
async def get_collection_logs(
    source_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取采集日志
    
    Args:
        source_id: 采集源ID（可选）
        status: 状态筛选（可选：'success', 'failed', 'skipped'）
        limit: 返回数量限制
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        采集日志列表
    """
    query = db.query(CollectionLog)
    
    if source_id:
        query = query.filter(CollectionLog.source_id == source_id)
    
    if status:
        query = query.filter(CollectionLog.status == status)
    
    logs = query.order_by(CollectionLog.executed_at.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "source_id": log.source_id,
            "url": log.url,
            "status": log.status,
            "error_message": log.error_message,
            "file_id": log.file_id,
            "executed_at": log.executed_at.isoformat() if log.executed_at else None
        }
        for log in logs
    ]