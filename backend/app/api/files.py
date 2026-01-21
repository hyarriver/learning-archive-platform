"""
文件管理API
"""
import json
from pathlib import Path
from typing import Optional, List
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File as FastAPIFile, Form, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db, File, FileVersion, User
from app.api.dependencies import get_current_user
from app.storage import FileManager, VersionManager
from app.utils.logger import setup_logger
from app.utils.helpers import calculate_file_hash
from app.utils.search import search_files, create_fts_table, update_file_content_in_fts

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


def extract_video_url(content: str) -> Optional[str]:
    """
    从视频文件内容中提取视频链接
    
    Args:
        content: 视频文件内容（Markdown格式）
        
    Returns:
        视频链接，如果未找到则返回None
    """
    import re
    # 查找 Markdown 链接格式： [文本](链接)
    pattern = r'\[点击打开视频\]\((https?://[^\s\)]+)\)'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    
    # 查找直接链接格式：**视频链接**: 链接
    pattern = r'\*\*视频链接\*\*:\s*(https?://[^\s]+)'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    
    # 查找任何 http/https 链接
    pattern = r'(https?://[^\s\)]+)'
    matches = re.findall(pattern, content)
    # 过滤掉可能是缩略图的链接（通常包含 thumbnail、img、image 等关键词）
    for url in matches:
        if not any(keyword in url.lower() for keyword in ['thumbnail', 'img', 'image', '.jpg', '.png', '.gif', '.webp']):
            return url
    
    return None


class FileInfo(BaseModel):
    """文件信息模型"""
    id: int
    title: str
    source_id: Optional[int]
    upload_user_id: Optional[int]
    upload_username: Optional[str]  # 上传用户名
    source_name: Optional[str]  # 来源名称
    source_type: Optional[str] = None  # 采集源类型：'webpage' 或 'video'（仅采集文件有此字段）
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
    video_url: Optional[str] = None  # 视频链接（仅视频类型有此字段）


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
    
    # 搜索筛选：优先使用全文搜索，否则使用标题搜索
    if search:
        try:
            # 尝试使用全文搜索
            fts_results = search_files(
                db=db,
                query=search,
                limit=page_size,
                offset=(page - 1) * page_size,
                user_id=current_user.id if user_role != 'admin' else None,
                is_admin=(user_role == 'admin')
            )
            
            # 如果FTS搜索有结果，使用FTS结果
            if fts_results["total"] > 0:
                # 应用其他筛选条件
                fts_file_ids = [item["id"] for item in fts_results["items"]]
                query = query.filter(File.id.in_(fts_file_ids))
                
                # 应用来源筛选
                if source_id:
                    query = query.filter(File.source_id == source_id)
                
                # 应用文件类型筛选
                if file_type == 'collection':
                    query = query.filter(File.source_id.isnot(None))
                elif file_type == 'upload':
                    query = query.filter(File.upload_user_id.isnot(None))
                
                # 应用标签筛选
                if tag:
                    query = query.filter(File.tags.contains(tag))
                
                # 重新获取文件
                items = query.order_by(File.created_at.desc()).all()
                total = len(items) if not source_id and not file_type and not tag else query.count()
            else:
                # FTS无结果，回退到标题搜索
                query = query.filter(File.title.contains(search))
        except Exception as e:
            logger.warning(f"全文搜索失败，回退到标题搜索: {e}")
            # 回退到简单的标题搜索
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
        
        # 获取来源名称和类型
        source_name = None
        source_type = None
        if file.source_id and file.source:
            source_name = file.source.name
            source_type = file.source.source_type
        
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
            source_type=source_type,
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
        HTTPException: 如果文件不存在或文件类型不支持预览
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
    
    # 检查是否为视频类型
    is_video = file.source_id and file.source and file.source.source_type == 'video'
    video_url = None
    
    if is_video:
        # 从内容中提取视频链接
        video_url = extract_video_url(content)
        # 视频类型不支持预览，只返回视频链接
        # 但为了兼容性，我们仍然返回内容，前端会处理
    else:
        # 检查是否为视频类型，视频类型不支持预览
        # 这个检查已经移到前面，这里不需要了
        pass
    
    return {
        "id": file.id,
        "title": file.title,
        "content": content,
        "source_id": file.source_id,
        "tags": tags,
        "summary": file.summary,
        "created_at": file.created_at.isoformat() if file.created_at else None,
        "updated_at": file.updated_at.isoformat() if file.updated_at else None,
        "video_url": video_url
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
        HTTPException: 如果文件不存在或下载失败
    """
    try:
        file = db.query(File).filter(File.id == file_id).first()
        
        if not file:
            logger.warning(f"下载文件失败: 文件ID {file_id} 不存在")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查是否为视频类型
        is_video = file.source_id and file.source and file.source.source_type == 'video'
        
        if is_video:
            # 视频类型：返回视频链接信息
            file_manager = FileManager()
            
            # 判断文件类型并选择正确的目录
            base_dir = file_manager.collections_dir
            file_path_str = file.file_path.replace('\\', '/')
            if file_path_str.startswith('collections/'):
                relative_path = Path(file_path_str.replace('collections/', '', 1))
            else:
                relative_path = Path(file_path_str)
            
            content = file_manager.read_file(relative_path, base_dir=base_dir)
            
            if content is None:
                logger.error(f"下载视频文件失败: file_id={file_id}, 文件内容不存在")
                raise HTTPException(status_code=404, detail="文件内容不存在")
            
            # 从内容中提取视频链接
            video_url = extract_video_url(content)
            
            if not video_url:
                logger.warning(f"无法从视频文件中提取视频链接: file_id={file_id}")
                raise HTTPException(status_code=404, detail="视频链接不存在")
            
            # 返回视频链接信息（JSON格式）
            import json
            video_info = {
                "title": file.title,
                "video_url": video_url,
                "message": "这是视频文件，请使用上述链接访问视频"
            }
            
            video_info_json = json.dumps(video_info, ensure_ascii=False, indent=2)
            
            # 处理文件名编码
            filename = f"{file.title}_视频链接.txt"
            filename_encoded = quote(filename.encode('utf-8'))
            content_disposition = f'attachment; filename="{quote(filename)}"; filename*=UTF-8\'\'{filename_encoded}'
            
            logger.info(f"视频文件下载链接返回成功: file_id={file_id}, video_url={video_url}")
            
            return Response(
                content=video_info_json.encode('utf-8'),
                media_type="text/plain; charset=utf-8",
                headers={
                    "Content-Disposition": content_disposition
                }
            )
        
        # 非视频类型：返回文件内容
        # 读取文件内容
        file_manager = FileManager()
        
        # 判断文件类型并选择正确的目录
        if file.upload_user_id:
            # 用户上传的文件
            base_dir = file_manager.uploads_dir
            # 统一路径分隔符处理（Windows兼容）
            file_path_str = file.file_path.replace('\\', '/')
            if file_path_str.startswith('uploads/'):
                relative_path = Path(file_path_str.replace('uploads/', '', 1))
            else:
                relative_path = Path(file_path_str)
            logger.debug(f"下载上传文件: file_id={file_id}, base_dir={base_dir}, relative_path={relative_path}")
        else:
            # 采集的文件
            base_dir = file_manager.collections_dir
            # 统一路径分隔符处理（Windows兼容）
            file_path_str = file.file_path.replace('\\', '/')
            if file_path_str.startswith('collections/'):
                relative_path = Path(file_path_str.replace('collections/', '', 1))
            else:
                relative_path = Path(file_path_str)
            logger.debug(f"下载采集文件: file_id={file_id}, base_dir={base_dir}, relative_path={relative_path}")
        
        content = file_manager.read_file(relative_path, base_dir=base_dir)
        
        if content is None:
            logger.error(f"下载文件失败: file_id={file_id}, 文件内容不存在。路径: {base_dir / relative_path}")
            raise HTTPException(status_code=404, detail="文件内容不存在")
        
        # 处理文件内容编码
        if isinstance(content, bytes):
            # 如果已经是 bytes，直接使用
            content_bytes = content
        elif isinstance(content, str):
            # 如果是字符串，编码为 bytes
            content_bytes = content.encode('utf-8')
        else:
            # 其他类型，尝试转换为字符串再编码
            logger.warning(f"文件内容类型异常: file_id={file_id}, type={type(content)}")
            content_bytes = str(content).encode('utf-8')
        
        # 处理文件名编码（支持中文和特殊字符）
        filename = f"{file.title}.md"
        # 使用 RFC 5987 格式支持 UTF-8 文件名
        filename_encoded = quote(filename.encode('utf-8'))
        content_disposition = f'attachment; filename="{quote(filename)}"; filename*=UTF-8\'\'{filename_encoded}'
        
        logger.info(f"文件下载成功: file_id={file_id}, filename={filename}")
        
        # 返回文件下载响应
        return Response(
            content=content_bytes,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": content_disposition
            }
        )
    
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        # 捕获其他异常，记录日志并返回有意义的错误信息
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else f"{error_type}: 下载失败"
        logger.exception(f"下载文件异常: file_id={file_id}, 错误类型: {error_type}, 错误信息: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"下载文件失败: {error_msg[:200]}"
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


@router.get("/{file_id}/images/{image_path:path}")
async def get_file_image(
    file_id: int,
    image_path: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取文件关联的图片
    
    Args:
        file_id: 文件ID
        image_path: 图片相对路径（相对于Markdown文件）
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        图片文件响应
        
    Raises:
        HTTPException: 如果文件或图片不存在
    """
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_manager = FileManager()
    
    # 判断文件类型并选择正确的目录
    if file.upload_user_id:
        # 用户上传的文件
        base_dir = file_manager.uploads_dir
        file_relative_path = Path(file.file_path.replace('uploads/', '')) if file.file_path.startswith('uploads/') else Path(file.file_path)
    else:
        # 采集的文件
        base_dir = file_manager.collections_dir
        file_relative_path = Path(file.file_path.replace('collections/', '')) if file.file_path.startswith('collections/') else Path(file.file_path)
    
    # 构建图片路径（相对于文件目录）
    # file_relative_path格式：{source}/{date}/{title}.md
    # image_path格式：images/{filename} 或 {filename}（如果已经包含images/）
    # 完整路径：{source}/{date}/images/{filename}
    file_dir = file_relative_path.parent  # {source}/{date}
    
    # URL解码image_path（FastAPI会自动解码，但确保路径正确）
    from urllib.parse import unquote
    decoded_image_path = unquote(image_path)
    
    # 构建图片文件路径
    image_file_path = base_dir / file_dir / decoded_image_path
    
    # 安全检查：确保图片路径在文件目录内
    try:
        image_file_path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        logger.error(f"非法图片路径: file_id={file_id}, image_path={decoded_image_path}, resolved={image_file_path.resolve()}, base_dir={base_dir.resolve()}")
        raise HTTPException(status_code=403, detail=f"非法的图片路径: {decoded_image_path}")
    
    if not image_file_path.exists() or not image_file_path.is_file():
        logger.warning(f"图片不存在: file_id={file_id}, image_path={decoded_image_path}, full_path={image_file_path}")
        raise HTTPException(status_code=404, detail=f"图片不存在: {decoded_image_path}")
    
    # 读取图片文件
    try:
        image_bytes = image_file_path.read_bytes()
        
        # 根据文件扩展名确定Content-Type
        ext = image_file_path.suffix.lower()
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml'
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')
        
        return Response(content=image_bytes, media_type=content_type)
    except Exception as e:
        logger.error(f"读取图片失败: {image_file_path}, 错误: {e}")
        raise HTTPException(status_code=500, detail="读取图片失败")


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


class BulkDeleteRequest(BaseModel):
    """批量删除请求模型"""
    file_ids: List[int]


@router.post("/bulk-delete", status_code=200)
async def bulk_delete_files(
    request: BulkDeleteRequest = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    批量删除文件（仅管理员）
    
    Args:
        request: 批量删除请求，包含文件ID列表
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        删除结果，包含成功和失败的统计
        
    Raises:
        HTTPException: 如果用户不是管理员
    """
    # 权限检查：仅管理员可以使用批量删除
    user_role = getattr(current_user, 'role', 'user')
    if user_role != 'admin':
        raise HTTPException(status_code=403, detail="批量删除功能仅限管理员使用")
    
    if not request.file_ids or len(request.file_ids) == 0:
        raise HTTPException(status_code=400, detail="请至少选择一个文件")
    
    file_manager = FileManager()
    success_count = 0
    failed_count = 0
    failed_files = []
    
    # 批量删除文件
    for file_id in request.file_ids:
        try:
            file = db.query(File).filter(File.id == file_id).first()
            
            if not file:
                failed_count += 1
                failed_files.append({"id": file_id, "reason": "文件不存在"})
                continue
            
            # 删除物理文件
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
            success_count += 1
            
            logger.info(f"批量删除文件: {file.title}, 操作者: {current_user.username}")
            
        except Exception as e:
            failed_count += 1
            failed_files.append({"id": file_id, "reason": str(e)[:100]})
            logger.error(f"批量删除文件失败: file_id={file_id}, 错误: {e}")
    
    # 提交所有成功的删除
    db.commit()
    
    logger.info(f"批量删除完成: 成功 {success_count} 个, 失败 {failed_count} 个, 操作者: {current_user.username}")
    
    return {
        "message": f"批量删除完成: 成功 {success_count} 个, 失败 {failed_count} 个",
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_files": failed_files
    }