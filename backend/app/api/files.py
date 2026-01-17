"""
文件管理API
"""
import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File as FastAPIFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db, File, FileVersion, User
from app.api.dependencies import get_current_user
from app.storage import FileManager, VersionManager
from app.utils.logger import setup_logger
from app.utils.helpers import calculate_file_hash

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


class FileInfo(BaseModel):
    """文件信息模型"""
    id: int
    title: str
    source_id: Optional[int]
    upload_user_id: Optional[int]
    upload_username: Optional[str]  # 上传用户名
    source_name: Optional[str]  # 来源名称
    file_path: str
    tags: List[str]
    summary: Optional[str]
    file_type: str  # 'collection' 或 'upload'
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
    file_type: Optional[str] = Query(None, description="文件类型：collection或upload"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取文件列表（分页）
    管理员可以看到所有文件，普通用户只能看到自己上传的文件和所有采集的文件
    
    Args:
        page: 页码
        page_size: 每页数量
        source_id: 来源ID（可选）
        tag: 标签筛选（可选）
        search: 搜索关键词（可选）
        file_type: 文件类型筛选（可选：collection或upload）
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        文件列表响应
    """
    query = db.query(File)
    
    # 权限过滤：普通用户只能看到自己上传的文件和所有采集的文件
    user_role = getattr(current_user, 'role', 'user')
    if user_role != 'admin':
        # 普通用户：采集文件（source_id不为空）或自己上传的文件（upload_user_id等于当前用户ID）
        query = query.filter(
            (File.source_id.isnot(None)) | (File.upload_user_id == current_user.id)
        )
    
    # 来源筛选
    if source_id:
        query = query.filter(File.source_id == source_id)
    
    # 文件类型筛选
    if file_type == 'collection':
        query = query.filter(File.source_id.isnot(None))
    elif file_type == 'upload':
        query = query.filter(File.upload_user_id.isnot(None))
    
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
        
        # 获取来源名称
        source_name = None
        if file.source_id and file.source:
            source_name = file.source.name
        
        # 获取上传用户名
        upload_username = None
        if file.upload_user_id and file.upload_user:
            upload_username = file.upload_user.username
        
        # 判断文件类型
        file_type_str = 'collection' if file.source_id else 'upload'
        
        file_list.append(FileInfo(
            id=file.id,
            title=file.title,
            source_id=file.source_id,
            upload_user_id=file.upload_user_id,
            upload_username=upload_username,
            source_name=source_name,
            file_path=file.file_path,
            tags=tags,
            summary=file.summary,
            file_type=file_type_str,
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
    
    # 判断文件类型并选择正确的目录
    if file.upload_user_id:
        # 用户上传的文件
        base_dir = file_manager.uploads_dir
        relative_path = Path(file.file_path.replace('uploads/', '')) if file.file_path.startswith('uploads/') else Path(file.file_path)
    else:
        # 采集的文件
        base_dir = file_manager.collections_dir
        relative_path = Path(file.file_path.replace('collections/', '')) if file.file_path.startswith('collections/') else Path(file.file_path)
    
    content = file_manager.read_file(relative_path, base_dir=base_dir)
    
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
    
    # 判断文件类型并选择正确的目录
    if file.upload_user_id:
        # 用户上传的文件
        base_dir = file_manager.uploads_dir
        relative_path = Path(file.file_path.replace('uploads/', '')) if file.file_path.startswith('uploads/') else Path(file.file_path)
    else:
        # 采集的文件
        base_dir = file_manager.collections_dir
        relative_path = Path(file.file_path.replace('collections/', '')) if file.file_path.startswith('collections/') else Path(file.file_path)
    
    content = file_manager.read_file(relative_path, base_dir=base_dir)
    
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


@router.post("/upload", response_model=FileInfo, status_code=201)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    上传文件
    
    Args:
        file: 上传的文件
        title: 文件标题（可选，默认为文件名）
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        文件信息
        
    Raises:
        HTTPException: 如果上传失败
    """
    try:
        # 读取文件内容
        content_bytes = await file.read()
        
        # 尝试解码为文本（Markdown文件）
        try:
            content_str = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文件必须是UTF-8编码的文本文件")
        
        # 确定文件标题
        file_title = title or file.filename or "未命名文件"
        # 移除扩展名
        if file_title.endswith('.md'):
            file_title = file_title[:-3]
        
        # 保存文件
        file_manager = FileManager()
        relative_path = file_manager.save_upload(
            user_id=current_user.id,
            filename=f"{file_title}.md",
            content=content_bytes
        )
        
        # 计算文件哈希
        content_hash = calculate_file_hash(content_str)
        
        # 构建文件路径（使用相对路径，标记为uploads类型）
        # 文件路径格式：uploads/{user_id}/{filename}.md
        file_path_str = f"uploads/{relative_path}"
        
        # 创建文件记录
        file_record = File(
            title=file_title,
            source_id=None,  # 用户上传的文件没有来源
            upload_user_id=current_user.id,
            file_path=file_path_str,
            file_hash=content_hash,
            tags=None,
            summary=None
        )
        
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        
        logger.info(f"用户上传文件: {file_title}, 用户: {current_user.username}")
        
        return FileInfo(
            id=file_record.id,
            title=file_record.title,
            source_id=file_record.source_id,
            upload_user_id=file_record.upload_user_id,
            upload_username=current_user.username,
            source_name=None,
            file_path=file_record.file_path,
            tags=[],
            summary=file_record.summary,
            file_type='upload',
            created_at=file_record.created_at.isoformat() if file_record.created_at else None,
            updated_at=file_record.updated_at.isoformat() if file_record.updated_at else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"上传文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    删除文件
    管理员可以删除所有文件，普通用户只能删除自己上传的文件
    
    Args:
        file_id: 文件ID
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 如果文件不存在或权限不足
    """
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 权限检查
    user_role = getattr(current_user, 'role', 'user')
    if user_role != 'admin':
        # 普通用户只能删除自己上传的文件
        if file.upload_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此文件，只能删除自己上传的文件")
        
        # 普通用户不能删除采集的文件
        if file.source_id is not None:
            raise HTTPException(status_code=403, detail="无权删除采集的文件")
    
    # 删除物理文件
    file_manager = FileManager()
    file_path = Path(file.file_path)
    
    # 判断文件是在哪个目录下
    if file.upload_user_id:
        # 用户上传的文件
        base_dir = file_manager.uploads_dir
        relative_path = Path(file.file_path.replace('uploads/', '')) if file.file_path.startswith('uploads/') else Path(file.file_path)
    else:
        # 采集的文件
        base_dir = file_manager.collections_dir
        relative_path = Path(file.file_path.replace('collections/', '')) if file.file_path.startswith('collections/') else Path(file.file_path)
    
    file_manager.delete_file(relative_path, base_dir)
    
    # 删除数据库记录
    db.delete(file)
    db.commit()
    
    logger.info(f"删除文件: {file.title}, 操作者: {current_user.username}")
    
    return {"message": "文件已删除"}