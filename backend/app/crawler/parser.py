"""
内容解析器
"""
import re
from typing import Dict, Optional
from bs4 import BeautifulSoup, Tag, NavigableString

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HTMLParser:
    """HTML内容解析器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化解析器
        
        Args:
            config: 解析器配置，包含选择器信息
        """
        self.config = config or {}
        self.selectors = self.config.get('selectors', {})
    
    def extract_title(self, soup: BeautifulSoup, url: str = None) -> str:
        """
        提取标题（多种策略）
        
        Args:
            soup: BeautifulSoup对象
            url: 源URL（可选）
            
        Returns:
            提取的标题
        """
        # 策略1: 使用配置的选择器
        if 'title' in self.selectors:
            try:
                title_elem = soup.select_one(self.selectors['title'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title:
                        return title
            except Exception as e:
                logger.warning(f"使用配置选择器提取标题失败: {e}")
        
        # 策略2: 查找 h1 标签
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            if title:
                return title
        
        # 策略3: 查找 og:title meta标签
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # 策略4: 使用 title 标签
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            if title:
                return title
        
        # 策略5: 从URL提取（最后的手段）
        if url:
            # 尝试从URL路径提取
            match = re.search(r'/([^/]+)/?$', url)
            if match:
                return match.group(1).replace('-', ' ').replace('_', ' ').title()
        
        return "无标题"
    
    def extract_body(self, soup: BeautifulSoup) -> str:
        """
        提取正文内容
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            正文HTML字符串
        """
        # 策略1: 使用配置的选择器
        if 'content' in self.selectors:
            try:
                content_elem = soup.select_one(self.selectors['content'])
                if content_elem:
                    # 清理内容
                    self._clean_content(content_elem)
                    return str(content_elem)
            except Exception as e:
                logger.warning(f"使用配置选择器提取正文失败: {e}")
        
        # 策略2: 查找常见的文章容器
        common_selectors = [
            'article',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            'main',
            '#content',
            '#main-content'
        ]
        
        for selector in common_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    self._clean_content(elem)
                    return str(elem)
            except Exception:
                continue
        
        # 策略3: 使用 body 标签（作为最后手段）
        body = soup.find('body')
        if body:
            self._clean_content(body)
            return str(body)
        
        return str(soup)
    
    def _clean_content(self, element: Tag):
        """
        清理HTML元素，移除无关内容
        
        Args:
            element: BeautifulSoup元素对象
        """
        # 移除脚本和样式
        for script in element.find_all(['script', 'style', 'noscript']):
            script.decompose()
        
        # 移除常见的无关元素
        unwanted_selectors = [
            'header', 'footer', 'nav', '.nav', '#nav',
            '.sidebar', '.sidebar-menu', '#sidebar',
            '.comments', '.comment', '#comments',
            '.ad', '.advertisement', '.ads',
            '.share', '.social-share',
            '.breadcrumb', '.breadcrumbs'
        ]
        
        for selector in unwanted_selectors:
            try:
                for elem in element.select(selector):
                    elem.decompose()
            except Exception:
                continue
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        提取元数据
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            元数据字典
        """
        metadata = {}
        
        # 提取meta标签
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property') or meta.get('itemprop')
            content = meta.get('content')
            if name and content:
                metadata[name.lower()] = content.strip()
        
        # 提取作者
        author_selectors = [
            'meta[name="author"]',
            '.author',
            '[rel="author"]'
        ]
        for selector in author_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    author = elem.get('content') or elem.get_text(strip=True)
                    if author:
                        metadata['author'] = author
                        break
            except Exception:
                continue
        
        # 提取发布日期
        date_selectors = [
            'meta[property="article:published_time"]',
            'time[datetime]',
            '.published-date',
            '.post-date'
        ]
        for selector in date_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    date = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                    if date:
                        metadata['published_date'] = date
                        break
            except Exception:
                continue
        
        return metadata