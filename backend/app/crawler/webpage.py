"""
网页爬虫
"""
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

from app.crawler.base import BaseCrawler
from app.crawler.parser import HTMLParser
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# 尝试导入Selenium支持
try:
    from app.crawler.selenium_crawler import SeleniumWebPageCrawler, SELENIUM_AVAILABLE
except ImportError:
    SELENIUM_AVAILABLE = False
    SeleniumWebPageCrawler = None


class WebPageCrawler(BaseCrawler):
    """网页爬虫（支持Selenium模式）"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化网页爬虫
        
        Args:
            config: 爬虫配置，可包含：
                - selectors: 解析选择器配置
                - use_selenium: 是否使用Selenium（默认: False）
                - selenium_config: Selenium配置（当use_selenium=True时）
        """
        super().__init__(config)
        self.parser = HTMLParser(config)
        
        # 检查是否使用Selenium
        self.use_selenium = self.config.get('use_selenium', False)
        if self.use_selenium:
            if not SELENIUM_AVAILABLE:
                logger.warning("配置要求使用Selenium，但Selenium未安装。将使用普通requests模式。")
                self.use_selenium = False
                self.selenium_crawler = None
            else:
                selenium_config = self.config.get('selenium_config', {})
                # 合并配置
                combined_config = {**self.config, **selenium_config}
                try:
                    self.selenium_crawler = SeleniumWebPageCrawler(config=combined_config)
                    logger.info("已启用Selenium模式（支持JavaScript渲染）")
                except Exception as e:
                    logger.warning(f"初始化Selenium失败，将使用普通模式: {e}")
                    self.use_selenium = False
                    self.selenium_crawler = None
        else:
            self.selenium_crawler = None
    
    def fetch(self, url: str) -> Optional[str]:
        """
        获取网页内容（根据配置选择requests或Selenium）
        
        Args:
            url: 目标URL
            
        Returns:
            网页内容字符串，失败返回None
        """
        if self.use_selenium and self.selenium_crawler:
            return self.selenium_crawler.fetch(url)
        else:
            return super().fetch(url)
    
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
    
    def extract_search_links(self, url: str, max_links: int = 50, wait_selector: str = None) -> List[str]:
        """
        从搜索结果页面提取链接（支持Selenium模式和API模式）
        
        Args:
            url: 搜索结果页面URL
            max_links: 最大提取链接数
            wait_selector: 等待结果出现的CSS选择器（Selenium模式使用）
            
        Returns:
            链接URL列表
        """
        # 优先尝试CSDN API接口（如果URL是CSDN搜索）
        if 'so.csdn.net' in url or ('csdn.net' in url and 'search' in url):
            try:
                from urllib.parse import urlparse, parse_qs
                from app.crawler.csdn_api import CSDNSearchAPI
                
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                
                # 提取搜索关键词
                keyword = query_params.get('q', [None])[0]
                if keyword:
                    logger.info(f"检测到CSDN搜索，尝试使用API接口: 关键词={keyword}")
                    api_client = CSDNSearchAPI()
                    api_result = api_client.search(keyword, page=1, page_size=max_links)
                    if api_result:
                        logger.info(f"CSDN API返回了数据，尝试提取链接...")
                        links = api_client.extract_links_from_api(api_result, max_links=max_links)
                        if links:
                            logger.info(f"✓ 通过CSDN API成功提取到 {len(links)} 个链接")
                            return links
                        else:
                            logger.warning("CSDN API返回了数据但未提取到链接，JSON结构可能不同，尝试其他方法...")
                            # 保存API结果用于调试
                            try:
                                from pathlib import Path
                                debug_dir = Path("./logs/debug_html")
                                debug_dir.mkdir(parents=True, exist_ok=True)
                                debug_file = debug_dir / f"csdn_api_result_{time.strftime('%Y%m%d_%H%M%S')}.json"
                                with open(debug_file, 'w', encoding='utf-8') as f:
                                    json.dump(api_result, f, ensure_ascii=False, indent=2)
                                logger.info(f"已保存CSDN API结果到: {debug_file}")
                            except Exception:
                                pass
                    else:
                        logger.warning("CSDN API未返回数据，将使用Selenium或普通方法...")
            except Exception as e:
                logger.warning(f"CSDN API方法失败，将使用其他方法: {e}")
        
        if self.use_selenium and self.selenium_crawler:
            # 使用Selenium提取链接
            wait_sel = wait_selector or self.config.get('search_wait_selector')
            return self.selenium_crawler.extract_search_links(url, max_links=max_links, wait_selector=wait_sel)
        
        # 使用普通requests模式
        try:
            content = self.fetch(url)
            if not content:
                logger.warning(f"无法获取搜索结果页面: {url}")
                return []
            
            soup = BeautifulSoup(content, 'lxml')
            links = self.parser.extract_search_links(soup, base_url=url, max_links=max_links)
            
            # 记录提取到的链接信息（用于调试）
            if links:
                logger.info(f"从搜索结果页面提取到 {len(links)} 个链接: {url}")
                logger.debug(f"前3个链接示例: {links[:3]}")
            else:
                logger.warning(f"未能从搜索结果页面提取到链接: {url}")
                # 尝试记录页面的一些信息用于调试
                title_elem = soup.find('title')
                if title_elem:
                    logger.debug(f"搜索结果页面标题: {title_elem.get_text(strip=True)}")
                
                # 保存HTML到文件用于调试（可选）
                try:
                    from pathlib import Path
                    debug_dir = Path("./logs/debug_html")
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    debug_file = debug_dir / f"search_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"已保存搜索结果页面HTML到: {debug_file}")
                except Exception as e:
                    logger.debug(f"保存调试HTML失败: {e}")
            
            return links
            
        except Exception as e:
            logger.error(f"提取搜索链接失败: {url}, 错误: {str(e)}")
            return []
    
    def close(self):
        """关闭爬虫资源（如果使用了Selenium）"""
        if self.selenium_crawler:
            self.selenium_crawler.close()
    
    def __del__(self):
        """析构函数"""
        self.close()