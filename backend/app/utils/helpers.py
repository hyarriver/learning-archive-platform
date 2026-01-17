"""
通用工具函数
"""
import re
import hashlib
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        max_length: 最大长度
        
    Returns:
        清理后的文件名
    """
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename)  # 多个空格合并为一个
    filename = filename.strip()
    
    # 限制长度
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    # 如果为空，使用默认名称
    if not filename:
        filename = "untitled"
    
    return filename


def calculate_file_hash(content: str) -> str:
    """
    计算文件内容的SHA256哈希值
    
    Args:
        content: 文件内容字符串
        
    Returns:
        十六进制哈希值
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def ensure_directory(path: Path) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        路径对象
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def extract_domain_from_url(url: str) -> Optional[str]:
    """
    从URL中提取域名
    
    Args:
        url: URL字符串
        
    Returns:
        域名，提取失败返回None
    """
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc
    except Exception:
        return None