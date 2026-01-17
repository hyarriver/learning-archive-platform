"""
文件管理器
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings
from app.utils.helpers import sanitize_filename, calculate_file_hash, ensure_directory
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class FileManager:
    """文件管理器"""
    
    def __init__(self):
        """初始化文件管理器"""
        self.collections_dir = settings.get_collections_dir()
        self.uploads_dir = settings.get_uploads_dir()
        
        # 确保目录存在
        ensure_directory(self.collections_dir)
        ensure_directory(self.uploads_dir)
    
    def save_collection(
        self,
        source_name: str,
        title: str,
        content: str,
        date: Optional[datetime] = None
    ) -> Path:
        """
        保存采集内容
        
        Args:
            source_name: 来源名称
            title: 文件标题
            content: 文件内容（Markdown）
            date: 日期（可选，默认为今天）
            
        Returns:
            保存后的相对路径（相对于collections_dir）
        """
        if date is None:
            date = datetime.now()
        
        # 构建路径：collections/{source}/{date}/{title}.md
        date_str = date.strftime("%Y-%m-%d")
        safe_title = sanitize_filename(title)
        safe_source = sanitize_filename(source_name)
        
        file_dir = self.collections_dir / safe_source / date_str
        ensure_directory(file_dir)
        
        file_path = file_dir / f"{safe_title}.md"
        
        # 写入文件
        file_path.write_text(content, encoding='utf-8')
        
        logger.info(f"保存文件: {file_path.relative_to(self.collections_dir)}")
        
        # 返回相对路径（相对于collections_dir）
        return file_path.relative_to(self.collections_dir)
    
    def save_upload(
        self,
        user_id: int,
        filename: str,
        content: bytes
    ) -> Path:
        """
        保存用户上传的文件
        
        Args:
            user_id: 用户ID
            filename: 文件名
            content: 文件内容（字节）
            
        Returns:
            保存后的相对路径（相对于uploads_dir）
        """
        safe_filename = sanitize_filename(filename)
        user_dir = self.uploads_dir / str(user_id)
        ensure_directory(user_dir)
        
        file_path = user_dir / safe_filename
        
        # 写入文件
        file_path.write_bytes(content)
        
        logger.info(f"保存上传文件: {file_path.relative_to(self.uploads_dir)}")
        
        # 返回相对路径（相对于uploads_dir）
        return file_path.relative_to(self.uploads_dir)
    
    def read_file(self, relative_path: Path, base_dir: Path = None) -> Optional[str]:
        """
        读取文件内容
        
        Args:
            relative_path: 相对路径
            base_dir: 基础目录（默认为collections_dir）
            
        Returns:
            文件内容，失败返回None
        """
        if base_dir is None:
            base_dir = self.collections_dir
        
        file_path = base_dir / relative_path
        
        # 安全检查：确保路径在基础目录内
        try:
            file_path.resolve().relative_to(base_dir.resolve())
        except ValueError:
            logger.error(f"路径安全检查失败: {relative_path}")
            return None
        
        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return None
        
        try:
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, 错误: {e}")
            return None
    
    def file_exists(self, relative_path: Path, base_dir: Path = None) -> bool:
        """
        检查文件是否存在
        
        Args:
            relative_path: 相对路径
            base_dir: 基础目录（默认为collections_dir）
            
        Returns:
            是否存在
        """
        if base_dir is None:
            base_dir = self.collections_dir
        
        file_path = base_dir / relative_path
        
        # 安全检查
        try:
            file_path.resolve().relative_to(base_dir.resolve())
        except ValueError:
            return False
        
        return file_path.exists()
    
    def delete_file(self, relative_path: Path, base_dir: Path = None) -> bool:
        """
        删除文件
        
        Args:
            relative_path: 相对路径
            base_dir: 基础目录（默认为collections_dir）
            
        Returns:
            是否成功
        """
        if base_dir is None:
            base_dir = self.collections_dir
        
        file_path = base_dir / relative_path
        
        # 安全检查
        try:
            file_path.resolve().relative_to(base_dir.resolve())
        except ValueError:
            logger.error(f"路径安全检查失败: {relative_path}")
            return False
        
        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return False
        
        try:
            file_path.unlink()
            logger.info(f"删除文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {file_path}, 错误: {e}")
            return False
    
    def calculate_hash(self, content: str) -> str:
        """
        计算文件内容哈希（用于去重）
        
        Args:
            content: 文件内容
            
        Returns:
            十六进制哈希值
        """
        return calculate_file_hash(content)
    
    def get_file_size(self, relative_path: Path, base_dir: Path = None) -> Optional[int]:
        """
        获取文件大小
        
        Args:
            relative_path: 相对路径
            base_dir: 基础目录（默认为collections_dir）
            
        Returns:
            文件大小（字节），失败返回None
        """
        if base_dir is None:
            base_dir = self.collections_dir
        
        file_path = base_dir / relative_path
        
        # 安全检查
        try:
            file_path.resolve().relative_to(base_dir.resolve())
        except ValueError:
            return None
        
        if not file_path.exists():
            return None
        
        try:
            return file_path.stat().st_size
        except Exception as e:
            logger.error(f"获取文件大小失败: {file_path}, 错误: {e}")
            return None