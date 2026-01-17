"""
文件管理API
"""
import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db, File, FileVersion
from app.api.dependencies import get_current_user
from app.storage import FileManager, VersionManager
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


class FileInfo(BaseModel):
    """文件信息模型"""
    id: int
    title: str
    source_id: Optional[int]
    file_path: str
    tags: List[str]
    summary: Optional[str]
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """文件列表响应模型"""
    total: int
    page: int
    page_size: int
    items: List[FileInfo]


class FileDetailResponse(BaseModel):
    """文件详情响应模型"""
    id: int
    title: str
    content: str
    source_id: Optional[int]
    tags: List[str]
    summary: Optional[str]
    created_at: str
    updated_at: Optional[str]


@router.get("/", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    source_id: Optional[int] = Query(None, description="来源ID"),
    tag: Optional[str] = Query(None, description="标签筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取文件列表（分页）
    
    Args:
        page: 页码
        page_size: 每页数量
        source_id: 来源ID（可选）
        tag: 标签筛选（可选）
        search: 搜索关键词（可选）
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        文件列表响应
    """
    query = db.query(File)
    
    # 来源筛选
    if source_id:
        query = query.filter(File.source_id == source_id)
    
    # 标签筛选（简单字符串匹配）
    if tag:
        query = query.filter(File.tags.contains(tag))
    
    # 搜索筛选（标题搜索）
    if search:
        query = query.filter(File.title.contains(search))
    
    # 总数
    total = query.count()
    
    # 分页
    items = query.order_by(File.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    # 转换为响应模型
    file_list = []
    for file in items:
        tags = json.loads(file.tags) if file.tags else []
        file_list.append(FileInfo(
            id=file.id,
            title=file.title,
            source_id=file.source_id,
            file_path=file.file_path,
            tags=tags,
            summary=file.summary,
            created_at=file.created_at.isoformat() if file.created_at else None,
            updated_at=file.updated_at.isoformat() if file.updated_at else None
        ))
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": file_list
    }


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取文件详情（包含内容）
    
    Args:
        file_id: 文件ID
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        文件详情响应
        
    Raises:
        HTTPException: 如果文件不存在
    """
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 读取文件内容
    file_manager = FileManager()
    file_path = Path(file.file_path)
    content = file_manager.read_file(file_path)
    
    if content is None:
        raise HTTPException(status_code=404, detail="文件内容不存在")
    
    tags = json.loads(file.tags) if file.tags else []
    
    return {
        "id": file.id,
        "title": file.title,
        "content": content,
        "source_id": file.source_id,
        "tags": tags,
        "summary": file.summary,
        "created_at": file.created_at.isoformat() if file.created_at else None,
        "updated_at": file.updated_at.isoformat() if file.updated_at else None
    }


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    下载文件
    
    Args:
        file_id: 文件ID
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        文件下载响应
        
    Raises:
        HTTPException: 如果文件不存在
    """
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 读取文件内容
    file_manager = FileManager()
    file_path = Path(file.file_path)
    content = file_manager.read_file(file_path)
    
    if content is None:
        raise HTTPException(status_code=404, detail="文件内容不存在")
    
    # 返回文件下载响应
    return Response(
        content=content.encode('utf-8'),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{file.title}.md"'
        }
    )


@router.get("/{file_id}/versions")
async def get_file_versions(
    file_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取文件的所有版本
    
    Args:
        file_id: 文件ID
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        版本列表
        
    Raises:
        HTTPException: 如果文件不存在
    """
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 获取所有版本
    version_manager = VersionManager()
    versions = version_manager.get_all_versions(db, file_id)
    
    return {
        "file_id": file_id,
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "file_path": v.file_path,
                "created_at": v.created_at.isoformat() if v.created_at else None
            }
            for v in versions
        ]
    }


@router.get("/{file_id}/versions/{version_number}")
async def get_file_version(
    file_id: int,
    version_number: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取指定版本的文件内容
    
    Args:
        file_id: 文件ID
        version_number: 版本号
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        版本内容
        
    Raises:
        HTTPException: 如果文件或版本不存在
    """
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 获取版本内容
    version_manager = VersionManager()
    content = version_manager.get_version_content(db, file_id, version_number)
    
    if content is None:
        raise HTTPException(status_code=404, detail="版本不存在")
    
    return {
        "file_id": file_id,
        "version_number": version_number,
        "content": content
    }