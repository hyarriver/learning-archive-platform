"""
图片下载器（用于在HTML转Markdown前下载图片）
"""
import re
import hashlib
import requests
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from app.utils.logger import setup_logger
from app.utils.helpers import sanitize_filename

logger = setup_logger(__name__)


class ImageDownloader:
    """图片下载器"""
    
    def __init__(self, base_url: str = None, images_dir: Path = None):
        """
        初始化图片下载器
        
        Args:
            base_url: 基础URL（用于解析相对路径的图片）
            images_dir: 图片保存目录
        """
        self.base_url = base_url
        self.images_dir = images_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 已下载的图片映射：{original_url: local_path}
        self.downloaded_images: Dict[str, str] = {}
    
    def download_images_from_html(
        self,
        html: str,
        source_name: str,
        title: str,
        date_str: str
    ) -> str:
        """
        从HTML中下载所有图片并替换链接
        
        Args:
            html: HTML内容
            source_name: 来源名称
            title: 标题
            date_str: 日期字符串（YYYY-MM-DD）
            
        Returns:
            替换后的HTML内容（图片链接已替换为本地路径）
        """
        if not self.images_dir:
            logger.warning("图片目录未设置，跳过图片下载")
            return html
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            img_tags = soup.find_all('img')
            
            if not img_tags:
                logger.debug("HTML中未找到图片")
                return html
            
            # 创建图片保存目录（使用sanitize_filename确保路径一致）
            safe_source = sanitize_filename(source_name)
            images_base_dir = self.images_dir / safe_source / date_str / 'images'
            images_base_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"找到 {len(img_tags)} 个图片，开始下载...")
            
            for idx, img in enumerate(img_tags):
                src = img.get('src')
                if not src:
                    continue
                
                # 解析图片URL
                img_url = self._resolve_image_url(src)
                if not img_url:
                    logger.warning(f"无法解析图片URL: {src}")
                    continue
                
                # 下载图片
                local_path = self._download_image(img_url, images_base_dir, idx)
                if local_path:
                    # 替换为相对路径（相对于Markdown文件的路径）
                    relative_path = f"images/{local_path.name}"
                    img['src'] = relative_path
                    logger.debug(f"图片已下载并替换: {img_url} -> {relative_path}")
                else:
                    logger.warning(f"图片下载失败: {img_url}")
            
            # 返回修改后的HTML
            return str(soup)
            
        except Exception as e:
            logger.error(f"下载图片时出错: {e}")
            return html  # 出错时返回原始HTML
    
    def _resolve_image_url(self, src: str) -> Optional[str]:
        """
        解析图片URL为绝对URL
        
        Args:
            src: 图片src属性值
            
        Returns:
            绝对URL，失败返回None
        """
        if not src:
            return None
        
        src = src.strip()
        
        # 已经是绝对URL
        if src.startswith(('http://', 'https://')):
            return src
        
        # 如果是data URI，跳过
        if src.startswith('data:'):
            return None
        
        # 如果是相对URL且有base_url
        if self.base_url:
            return urljoin(self.base_url, src)
        
        return None
    
    def _download_image(self, img_url: str, save_dir: Path, index: int) -> Optional[Path]:
        """
        下载图片到本地
        
        Args:
            img_url: 图片URL
            save_dir: 保存目录
            index: 图片索引（用于生成文件名）
            
        Returns:
            保存后的文件路径，失败返回None
        """
        try:
            # 检查是否已下载（使用URL哈希）
            url_hash = hashlib.md5(img_url.encode('utf-8')).hexdigest()[:8]
            
            # 尝试获取文件扩展名
            parsed = urlparse(img_url)
            path = parsed.path
            ext = Path(path).suffix.lower()
            
            # 如果扩展名不是图片格式，尝试从Content-Type获取
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
            if ext not in image_extensions:
                # 先发送HEAD请求获取Content-Type
                try:
                    response = self.session.head(img_url, timeout=10, allow_redirects=True)
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                        ext = '.jpg'
                    elif 'image/png' in content_type:
                        ext = '.png'
                    elif 'image/gif' in content_type:
                        ext = '.gif'
                    elif 'image/webp' in content_type:
                        ext = '.webp'
                    elif 'image/svg+xml' in content_type:
                        ext = '.svg'
                    else:
                        ext = '.jpg'  # 默认使用jpg
                except Exception:
                    ext = '.jpg'  # 默认使用jpg
            
            # 生成文件名
            filename = f"img_{index}_{url_hash}{ext}"
            file_path = save_dir / filename
            
            # 如果文件已存在，直接返回
            if file_path.exists():
                logger.debug(f"图片已存在，跳过下载: {filename}")
                return file_path
            
            # 下载图片
            response = self.session.get(img_url, timeout=30, allow_redirects=True, stream=True)
            response.raise_for_status()
            
            # 验证Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"不是图片类型: {content_type}, URL: {img_url}")
                return None
            
            # 保存图片
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"图片下载成功: {filename} ({file_path.stat().st_size} bytes)")
            return file_path
            
        except Exception as e:
            logger.warning(f"下载图片失败: {img_url}, 错误: {e}")
            return None
