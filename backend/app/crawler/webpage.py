"""
网页爬虫
"""
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

from app.crawler.base import BaseCrawler
from app.crawler.parser import HTMLParser
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class WebPageCrawler(BaseCrawler):
    """网页爬虫"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化网页爬虫
        
        Args:
            config: 爬虫配置，可包含 selectors 等解析配置
        """
        super().__init__(config)
        self.parser = HTMLParser(config)
    
    def parse(self, content: str, url: str = None) -> Dict[str, Any]:
        """
        解析网页内容
        
        Args:
            content: HTML内容
            url: 源URL（可选）
            
        Returns:
            包含 title, content, metadata 的字典
        """
        try:
            soup = BeautifulSoup(content, 'lxml')
        except Exception as e:
            logger.warning(f"使用 lxml 解析失败，尝试 html.parser: {e}")
            soup = BeautifulSoup(content, 'html.parser')
        
        # 提取标题
        title = self.parser.extract_title(soup, url)
        
        # 提取正文
        body_html = self.parser.extract_body(soup)
        
        # 提取元数据
        metadata = self.parser.extract_metadata(soup)
        
        return {
            'title': title,
            'content': body_html,
            'content_type': 'html',
            'metadata': metadata
        }