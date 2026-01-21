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
        提取正文内容（增强版，确保完整提取所有文字内容）
        
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
                    # 验证提取的内容是否有文字
                    text_content = content_elem.get_text(strip=True)
                    if text_content and len(text_content) > 50:  # 至少有50个字符
                        return str(content_elem)
                    else:
                        logger.debug(f"配置选择器提取的内容太短: {len(text_content)} 字符")
            except Exception as e:
                logger.warning(f"使用配置选择器提取正文失败: {e}")
        
        # 策略2: 查找常见的文章容器（扩展选择器列表）
        common_selectors = [
            # 博客和文章相关
            'article',
            '.article-content',
            '.article-body',
            '.article-text',
            '.post-content',
            '.post-body',
            '.post-text',
            '.entry-content',
            '.entry-body',
            '.entry-text',
            '.blog-content',
            '.blog-post-content',
            # 通用内容容器
            '.content',
            '.content-body',
            '.main-content',
            '.text-content',
            '#content',
            '#main-content',
            '#article-content',
            # main标签相关
            'main',
            'main article',
            'main .content',
            # 特定平台选择器
            '.markdown-body',  # GitHub/GitLab等
            '.markdown-content',
            '.note-content',  # 笔记平台
            '.doc-content',  # 文档平台
            '.page-content',  # 通用页面内容
        ]
        
        for selector in common_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    # 清理内容
                    self._clean_content(elem)
                    # 验证提取的内容是否有足够的文字
                    text_content = elem.get_text(strip=True)
                    if text_content and len(text_content) > 50:
                        logger.debug(f"使用选择器 '{selector}' 成功提取内容: {len(text_content)} 字符")
                        return str(elem)
                    else:
                        logger.debug(f"选择器 '{selector}' 提取的内容太短: {len(text_content)} 字符")
            except Exception as e:
                logger.debug(f"选择器 '{selector}' 提取失败: {e}")
                continue
        
        # 策略3: 查找包含最多文字的元素（智能选择）
        # 从body中查找文字最多的div或section
        body = soup.find('body')
        if body:
            # 清理body的无关内容
            self._clean_content(body)
            
            # 尝试找到文字最多的容器
            text_containers = body.find_all(['div', 'section', 'article', 'main'], recursive=True)
            best_container = None
            max_text_length = 0
            
            for container in text_containers:
                # 排除明显不是正文的容器
                container_classes = container.get('class', [])
                container_id = container.get('id', '')
                container_str = ' '.join(container_classes) + ' ' + container_id
                
                # 跳过导航、侧边栏、评论等
                skip_keywords = ['nav', 'sidebar', 'menu', 'comment', 'ad', 'advertisement', 'footer', 'header']
                if any(keyword in container_str.lower() for keyword in skip_keywords):
                    continue
                
                text_length = len(container.get_text(strip=True))
                if text_length > max_text_length:
                    max_text_length = text_length
                    best_container = container
            
            # 如果找到文字较多的容器，使用它
            if best_container and max_text_length > 200:  # 至少200字符
                logger.debug(f"找到文字最多的容器: {max_text_length} 字符")
                self._clean_content(best_container)
                return str(best_container)
            else:
                # 否则使用整个body
                logger.debug(f"未找到理想容器，使用body: {len(body.get_text(strip=True))} 字符")
                return str(body)
        
        # 策略4: 使用整个soup作为最后手段
        logger.warning("未能提取到理想内容，返回整个页面HTML")
        return str(soup)
    
    def _clean_content(self, element: Tag):
        """
        清理HTML元素，移除无关内容（增强版）
        
        Args:
            element: BeautifulSoup元素对象
        """
        # 移除脚本和样式
        for script in element.find_all(['script', 'style', 'noscript', 'iframe']):
            script.decompose()
        
        # 移除常见的无关元素（扩展列表）
        unwanted_selectors = [
            # 导航和结构
            'header', 'footer', 'nav', '.nav', '#nav',
            '.navigation', '.navbar', '#navbar',
            # 侧边栏
            '.sidebar', '.sidebar-menu', '#sidebar',
            '.aside', 'aside',
            # 评论
            '.comments', '.comment', '#comments',
            '.comment-section', '.comment-list',
            # 广告
            '.ad', '.advertisement', '.ads',
            '[class*="ad-"]', '[id*="ad-"]',
            '[class*="advertisement"]',
            # 分享按钮
            '.share', '.social-share', '.share-buttons',
            '.social-media', '.social-icons',
            # 面包屑
            '.breadcrumb', '.breadcrumbs',
            # 相关文章推荐
            '.related-posts', '.related-articles',
            '.recommended', '.recommend',
            # 标签和分类
            '.tags', '.tag-list', '.categories',
            # 作者信息（可选，根据需要保留）
            # '.author', '.author-info',
            # 元信息
            '.meta', '.post-meta', '.entry-meta',
            # 其他无关元素
            '.modal', '.popup', '.dialog',
            '.cookie-banner', '.consent-banner',
        ]
        
        for selector in unwanted_selectors:
            try:
                for elem in element.select(selector):
                    elem.decompose()
            except Exception:
                continue
        
        # 移除隐藏元素（display:none 或 visibility:hidden）
        try:
            for elem in element.find_all(style=True):
                style = elem.get('style', '').lower()
                if 'display:none' in style or 'display: none' in style or 'visibility:hidden' in style or 'visibility: hidden' in style:
                    elem.decompose()
        except Exception:
            pass
    
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
    
    def extract_search_links(self, soup: BeautifulSoup, base_url: str = None, max_links: int = 50) -> list:
        """
        从搜索结果页面提取链接
        
        Args:
            soup: BeautifulSoup对象
            base_url: 基础URL，用于解析相对链接
            max_links: 最大提取链接数
            
        Returns:
            链接URL列表
        """
        links = []
        
        # 策略1: 使用配置的选择器
        if 'search_result_link' in self.selectors:
            try:
                link_elements = soup.select(self.selectors['search_result_link'])
                for elem in link_elements[:max_links]:
                    href = elem.get('href')
                    if href:
                        # 解析绝对URL
                        absolute_url = self._resolve_url(href, base_url)
                        if absolute_url and absolute_url not in links:
                            links.append(absolute_url)
                if links:
                    logger.info(f"使用配置选择器提取到 {len(links)} 个链接")
                    return links
            except Exception as e:
                logger.warning(f"使用配置选择器提取链接失败: {e}")
        
        # 策略2: 查找常见的搜索结果容器中的链接
        # 通常搜索结果在列表项或卡片中
        common_selectors = [
            # CSDN搜索结果选择器
            '.search-list-con .search-item h3 a',
            '.search-list-con .search-item a.title',
            '.search-list .search-item h3 a',
            '.mainContent .search-list h3 a',
            # 通用搜索结果选择器
            '.search-result h3 a',
            '.search-result a.title',
            '.result-item h3 a',
            '.result-item a.title',
            '.search-item h3 a',
            '.search-item a.title',
            '.result h3 a',
            '.item h3 a',
            'article h3 a',
            '.video-item h3 a',
            '.post-item h3 a',
            # 其他常见格式
            '.search-result a',
            '.result-item a',
            '.search-item a',
            '.result a',
            '.item a',
            'article a',
            '.video-item a',
            '.post-item a'
        ]
        
        for selector in common_selectors:
            try:
                link_elements = soup.select(selector)
                for elem in link_elements[:max_links]:
                    href = elem.get('href')
                    if href:
                        absolute_url = self._resolve_url(href, base_url)
                        # 过滤掉明显不是内容页面的链接（如导航、标签等）
                        if absolute_url and self._is_content_link(absolute_url, href) and absolute_url not in links:
                            links.append(absolute_url)
                    if len(links) >= max_links:
                        break
                if links:
                    logger.info(f"使用通用选择器提取到 {len(links)} 个链接")
                    return links
            except Exception:
                continue
        
        # 策略3: 从所有链接中筛选可能的搜索结果链接
        # 过滤掉导航、页脚、分享等链接
        all_links = soup.find_all('a', href=True)
        filtered_links = []
        
        exclude_keywords = ['#', 'javascript:', 'mailto:', 'tel:', '/tag/', '/category/', '/author/', '/page/', '/search', '/so/search']
        
        for link in all_links:
            href = link.get('href')
            if not href:
                continue
            
            # 跳过明显不需要的链接（包括搜索页面）
            if any(keyword in href.lower() for keyword in exclude_keywords):
                continue
            
            absolute_url = self._resolve_url(href, base_url)
            if absolute_url and absolute_url not in links and absolute_url not in filtered_links:
                # 排除搜索页面本身
                if base_url and absolute_url == base_url:
                    continue
                # 检查是否为内容链接
                if not self._is_content_link(absolute_url, href):
                    continue
                # 检查链接文本，如果为空或太短可能不是内容链接
                text = link.get_text(strip=True)
                if text and len(text) > 5:
                    filtered_links.append(absolute_url)
            
            if len(filtered_links) >= max_links:
                break
        
        logger.info(f"从所有链接中筛选出 {len(filtered_links)} 个可能的搜索结果链接")
        return filtered_links
    
    def _resolve_url(self, href: str, base_url: str = None) -> Optional[str]:
        """
        解析URL为绝对URL
        
        Args:
            href: 链接地址（可能是相对或绝对）
            base_url: 基础URL
            
        Returns:
            绝对URL，如果无法解析返回None
        """
        if not href:
            return None
        
        href = href.strip()
        
        # 已经是绝对URL
        if href.startswith(('http://', 'https://')):
            return href
        
        # 如果是相对URL且有base_url
        if base_url:
            from urllib.parse import urljoin
            return urljoin(base_url, href)
        
        return None
    
    def _is_content_link(self, url: str, href: str = None) -> bool:
        """
        判断链接是否是内容页面链接（而非导航、标签等）
        
        Args:
            url: 链接URL
            href: 原始href（可选）
            
        Returns:
            是否为内容链接
        """
        if not url:
            return False
        
        url_lower = url.lower()
        
        # 排除明显的非内容链接
        exclude_patterns = [
            '#', 'javascript:', 'mailto:', 'tel:',
            '/tag/', '/tags/', '/category/', '/categories/',
            '/author/', '/user/', '/profile/',
            '/page/', '/search', '/so/search', '/login', '/register',
            '/about', '/contact', '/help', '/faq'
        ]
        
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False
        
        # 如果有href参数，也检查它
        if href:
            href_lower = href.lower()
            for pattern in exclude_patterns:
                if pattern in href_lower:
                    return False
        
        return True