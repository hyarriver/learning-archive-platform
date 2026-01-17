"""
版本管理器
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from sqlalchemy.orm import Session

from app.config import settings
from app.database import File, FileVersion
from app.storage.file_manager import FileManager
from app.utils.helpers import calculate_file_hash
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class VersionManager:
    """版本管理器"""
    
    def __init__(self):
        """初始化版本管理器"""
        self.file_manager = FileManager()
        self.collections_dir = settings.get_collections_dir()
    
    def create_version(
        self,
        db: Session,
        file_id: int,
        content: str,
        current_file_path: Path
    ) -> Optional[FileVersion]:
        """
        创建新版本（如果内容有变化）
        
        Args:
            db: 数据库会话
            file_id: 文件ID
            content: 新内容
            current_file_path: 当前文件相对路径
            
        Returns:
            新版本对象，如果内容未变化返回None
        """
        # 获取当前文件信息
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            logger.error(f"文件不存在: {file_id}")
            return None
        
        # 计算新内容的哈希
        new_hash = calculate_file_hash(content)
        
        # 如果内容未变化，不创建新版本
        if file.file_hash == new_hash:
            logger.info(f"文件内容未变化，不创建新版本: {file_id}")
            return None
        
        # 获取当前最大版本号
        max_version = self._get_max_version(db, file_id)
        new_version_number = max_version + 1
        
        # 构建版本文件路径
        version_dir = self.collections_dir / current_file_path.parent / "versions"
        version_dir.mkdir(parents=True, exist_ok=True)
        
        version_file_path = version_dir / f"v{new_version_number}.md"
        
        # 保存版本文件
        version_file_path.write_text(content, encoding='utf-8')
        
        # 创建版本记录
        version_relative_path = version_file_path.relative_to(self.collections_dir)
        
        version = FileVersion(
            file_id=file_id,
            version_number=new_version_number,
            file_path=str(version_relative_path),
            content_hash=new_hash
        )
        
        db.add(version)
        db.commit()
        db.refresh(version)
        
        logger.info(f"创建新版本: 文件 {file_id}, 版本 {new_version_number}")
        
        return version
    
    def get_max_version(self, db: Session, file_id: int) -> int:
        """
        获取文件的最大版本号
        
        Args:
            db: 数据库会话
            file_id: 文件ID
            
        Returns:
            最大版本号（如果没有版本则为0）
        """
        return self._get_max_version(db, file_id)
    
    def _get_max_version(self, db: Session, file_id: int) -> int:
        """
        获取文件的最大版本号（内部方法）
        
        Args:
            db: 数据库会话
            file_id: 文件ID
            
        Returns:
            最大版本号（如果没有版本则为0）
        """
        max_version = db.query(
            FileVersion.version_number
        ).filter(
            FileVersion.file_id == file_id
        ).order_by(
            FileVersion.version_number.desc()
        ).first()
        
        return max_version[0] if max_version else 0
    
    def get_version_content(
        self,
        db: Session,
        file_id: int,
        version_number: int
    ) -> Optional[str]:
        """
        获取指定版本内容
        
        Args:
            db: 数据库会话
            file_id: 文件ID
            version_number: 版本号
            
        Returns:
            版本内容，失败返回None
        """
        version = db.query(FileVersion).filter(
            FileVersion.file_id == file_id,
            FileVersion.version_number == version_number
        ).first()
        
        if not version:
            logger.warning(f"版本不存在: 文件 {file_id}, 版本 {version_number}")
            return None
        
        # 读取版本文件
        version_path = Path(version.file_path)
        content = self.file_manager.read_file(version_path)
        
        return content
    
    def get_all_versions(
        self,
        db: Session,
        file_id: int
    ) -> List[FileVersion]:
        """
        获取文件的所有版本
        
        Args:
            db: 数据库会话
            file_id: 文件ID
            
        Returns:
            版本列表（按版本号降序）
        """
        versions = db.query(FileVersion).filter(
            FileVersion.file_id == file_id
        ).order_by(
            FileVersion.version_number.desc()
        ).all()
        
        return versions
    
    def get_latest_version(self, db: Session, file_id: int) -> Optional[FileVersion]:
        """
        获取文件的最新版本
        
        Args:
            db: 数据库会话
            file_id: 文件ID
            
        Returns:
            最新版本对象，不存在返回None
        """
        version = db.query(FileVersion).filter(
            FileVersion.file_id == file_id
        ).order_by(
            FileVersion.version_number.desc()
        ).first()
        
        return version