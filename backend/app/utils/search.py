"""
全文搜索工具模块
使用SQLite FTS5实现全文搜索
"""
from typing import List, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import File
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_fts_table(db: Session):
    """
    创建全文搜索虚拟表（FTS5）
    
    Args:
        db: 数据库会话
    """
    try:
        # 创建FTS5虚拟表
        db.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                id UNINDEXED,
                title,
                content,
                tags,
                summary,
                content='files',
                content_rowid='id'
            )
        """))
        
        # 创建触发器，自动更新FTS索引
        db.execute(text("""
            CREATE TRIGGER IF NOT EXISTS files_fts_insert AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, title, content, tags, summary)
                VALUES (new.id, new.title, '', new.tags, new.summary);
            END
        """))
        
        db.execute(text("""
            CREATE TRIGGER IF NOT EXISTS files_fts_delete AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, title, content, tags, summary)
                VALUES ('delete', old.id, old.title, '', old.tags, old.summary);
            END
        """))
        
        db.execute(text("""
            CREATE TRIGGER IF NOT EXISTS files_fts_update AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, title, content, tags, summary)
                VALUES ('delete', old.id, old.title, '', old.tags, old.summary);
                INSERT INTO files_fts(rowid, title, content, tags, summary)
                VALUES (new.id, new.title, '', new.tags, new.summary);
            END
        """))
        
        db.commit()
        logger.info("FTS5表创建成功")
    except Exception as e:
        logger.error(f"创建FTS5表失败: {e}")
        db.rollback()


def update_file_content_in_fts(db: Session, file_id: int, content: str):
    """
    更新文件内容到FTS索引
    
    Args:
        db: 数据库会话
        file_id: 文件ID
        content: 文件内容
    """
    try:
        db.execute(text("""
            UPDATE files_fts 
            SET content = :content 
            WHERE rowid = :file_id
        """), {"file_id": file_id, "content": content})
        db.commit()
        logger.debug(f"更新FTS索引: file_id={file_id}")
    except Exception as e:
        logger.error(f"更新FTS索引失败: file_id={file_id}, error={e}")
        db.rollback()


def search_files(
    db: Session,
    query: str,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[int] = None,
    is_admin: bool = False
) -> Dict:
    """
    全文搜索文件
    
    Args:
        db: 数据库会话
        query: 搜索关键词
        limit: 返回结果数量限制
        offset: 偏移量
        user_id: 用户ID（用于权限过滤）
        is_admin: 是否为管理员
        
    Returns:
        搜索结果字典，包含total和items
    """
    try:
        # 构建搜索查询（FTS5语法）
        # 使用MATCH操作符进行全文搜索
        fts_query = f'"{query}"'  # 精确短语匹配
        # 或者使用: fts_query = query  # 分词匹配
        
        # 基础查询：从FTS表获取匹配的文件ID
        base_sql = """
            SELECT 
                fts.rowid as id,
                bm25(files_fts) as rank
            FROM files_fts
            WHERE files_fts MATCH :query
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """
        
        # 执行FTS查询
        fts_results = db.execute(
            text(base_sql),
            {"query": fts_query, "limit": limit, "offset": offset}
        ).fetchall()
        
        file_ids = [row[0] for row in fts_results]
        
        if not file_ids:
            return {"total": 0, "items": []}
        
        # 获取文件详细信息
        query_obj = db.query(File).filter(File.id.in_(file_ids))
        
        # 权限过滤
        if not is_admin and user_id:
            query_obj = query_obj.filter(
                (File.source_id.isnot(None)) | (File.upload_user_id == user_id)
            )
        
        files = query_obj.all()
        
        # 获取总数（需要重新查询，因为权限过滤）
        count_sql = """
            SELECT COUNT(DISTINCT fts.rowid)
            FROM files_fts
            WHERE files_fts MATCH :query
        """
        total_result = db.execute(text(count_sql), {"query": fts_query}).fetchone()
        total = total_result[0] if total_result else 0
        
        # 构建结果
        results = []
        for file in files:
            import json
            tags = json.loads(file.tags) if file.tags else []
            
            results.append({
                "id": file.id,
                "title": file.title,
                "source_id": file.source_id,
                "upload_user_id": file.upload_user_id,
                "file_path": file.file_path,
                "tags": tags,
                "summary": file.summary,
                "created_at": file.created_at.isoformat() if file.created_at else None,
            })
        
        return {
            "total": total,
            "items": results
        }
        
    except Exception as e:
        logger.error(f"全文搜索失败: query={query}, error={e}")
        # 如果FTS搜索失败，回退到简单的LIKE搜索
        return _fallback_search(db, query, limit, offset, user_id, is_admin)


def _fallback_search(
    db: Session,
    query: str,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[int] = None,
    is_admin: bool = False
) -> Dict:
    """
    回退搜索方法（当FTS不可用时使用LIKE搜索）
    
    Args:
        db: 数据库会话
        query: 搜索关键词
        limit: 返回结果数量限制
        offset: 偏移量
        user_id: 用户ID
        is_admin: 是否为管理员
        
    Returns:
        搜索结果字典
    """
    search_pattern = f"%{query}%"
    query_obj = db.query(File).filter(
        (File.title.like(search_pattern)) |
        (File.summary.like(search_pattern))
    )
    
    # 权限过滤
    if not is_admin and user_id:
        query_obj = query_obj.filter(
            (File.source_id.isnot(None)) | (File.upload_user_id == user_id)
        )
    
    total = query_obj.count()
    files = query_obj.order_by(File.created_at.desc()).offset(offset).limit(limit).all()
    
    import json
    results = []
    for file in files:
        tags = json.loads(file.tags) if file.tags else []
        results.append({
            "id": file.id,
            "title": file.title,
            "source_id": file.source_id,
            "upload_user_id": file.upload_user_id,
            "file_path": file.file_path,
            "tags": tags,
            "summary": file.summary,
            "created_at": file.created_at.isoformat() if file.created_at else None,
        })
    
    return {
        "total": total,
        "items": results
    }
