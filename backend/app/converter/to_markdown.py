"""
Markdown转换器
"""
import subprocess
from typing import Optional

import html2text

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConversionError(Exception):
    """转换异常"""
    pass


class MarkdownConverter:
    """HTML转Markdown转换器"""
    
    def __init__(self, use_pandoc: bool = None):
        """
        初始化转换器
        
        Args:
            use_pandoc: 是否使用pandoc，None时自动检测
        """
        if use_pandoc is None:
            self.use_pandoc = self._check_pandoc()
        else:
            self.use_pandoc = use_pandoc
        
        # 初始化 html2text
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0  # 不限制行宽
        self.html2text.unicode_snob = True  # 保持Unicode字符
    
    def _check_pandoc(self) -> bool:
        """
        检查pandoc是否可用
        
        Returns:
            是否可用
        """
        try:
            result = subprocess.run(
                ['pandoc', '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("检测到 pandoc，将使用 pandoc 进行转换")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.info(f"未检测到 pandoc，将使用 html2text 进行转换: {e}")
        
        return False
    
    def convert(self, html: str, title: str = None) -> str:
        """
        转换HTML为Markdown
        
        Args:
            html: HTML内容字符串
            title: 标题（可选，会添加到Markdown开头）
            
        Returns:
            Markdown格式字符串
        """
        try:
            if self.use_pandoc:
                markdown = self._convert_with_pandoc(html)
            else:
                markdown = self._convert_with_html2text(html)
            
            # 如果提供了标题且Markdown开头没有标题，添加标题
            if title and not markdown.strip().startswith('#'):
                markdown = f"# {title}\n\n{markdown}"
            
            return markdown
            
        except Exception as e:
            error_msg = f"转换HTML为Markdown失败: {str(e)}"
            logger.error(error_msg)
            raise ConversionError(error_msg)
    
    def _convert_with_pandoc(self, html: str) -> str:
        """
        使用pandoc转换
        
        Args:
            html: HTML内容字符串
            
        Returns:
            Markdown格式字符串
        """
        try:
            result = subprocess.run(
                ['pandoc', '--from=html', '--to=markdown', '--wrap=none'],
                input=html.encode('utf-8'),
                capture_output=True,
                timeout=30,
                check=True
            )
            return result.stdout.decode('utf-8')
        except subprocess.CalledProcessError as e:
            logger.warning(f"pandoc转换失败: {e.stderr.decode('utf-8', errors='ignore')}")
            # 降级使用 html2text
            return self._convert_with_html2text(html)
        except Exception as e:
            logger.warning(f"pandoc调用异常: {e}")
            # 降级使用 html2text
            return self._convert_with_html2text(html)
    
    def _convert_with_html2text(self, html: str) -> str:
        """
        使用html2text转换
        
        Args:
            html: HTML内容字符串
            
        Returns:
            Markdown格式字符串
        """
        try:
            markdown = self.html2text.handle(html)
            # 清理多余的空行
            markdown = self._clean_markdown(markdown)
            return markdown
        except Exception as e:
            logger.error(f"html2text转换失败: {e}")
            raise ConversionError(f"html2text转换失败: {str(e)}")
    
    def _clean_markdown(self, markdown: str) -> str:
        """
        清理Markdown内容（移除多余空行）
        
        Args:
            markdown: Markdown内容
            
        Returns:
            清理后的Markdown
        """
        lines = markdown.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue  # 跳过连续的空行
            cleaned_lines.append(line)
            prev_empty = is_empty
        
        return '\n'.join(cleaned_lines)