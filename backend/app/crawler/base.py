"""
基础爬虫类
"""
import time
import requests
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CrawlerError(Exception):
    """爬虫异常"""
    pass


class BaseCrawler(ABC):
    """基础爬虫抽象类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化爬虫
        
        Args:
            config: 爬虫配置字典
        """
        self.config = config or {}
        self.session = requests.Session()
        
        # 设置用户代理
        user_agent = self.config.get('user_agent') or settings.crawler_user_agent
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # 配置参数
        self.request_delay = self.config.get('request_delay', settings.crawler_request_delay)
        self.max_retries = self.config.get('max_retries', settings.crawler_max_retries)
        self.timeout = self.config.get('timeout', 30)
    
    def fetch(self, url: str) -> Optional[str]:
        """
        获取网页内容（带重试机制）
        
        Args:
            url: 目标URL
            
        Returns:
            网页内容字符串，失败返回None
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # 请求延迟
                if attempt > 0:
                    delay = self.request_delay * (2 ** (attempt - 1))  # 指数退避
                    logger.info(f"重试第 {attempt} 次，等待 {delay:.1f} 秒: {url}")
                    time.sleep(delay)
                
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type and 'text/plain' not in content_type:
                    logger.warning(f"非文本内容类型: {content_type}, URL: {url}")
                
                logger.info(f"成功获取内容: {url} (尝试 {attempt + 1}/{self.max_retries})")
                return response.text
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {url}, 错误: {str(e)}")
                continue
        
        # 所有重试都失败
        error_msg = f"获取内容失败，已重试 {self.max_retries} 次: {url}"
        if last_exception:
            error_msg += f", 最后错误: {str(last_exception)}"
        logger.error(error_msg)
        raise CrawlerError(error_msg)
    
    @abstractmethod
    def parse(self, content: str, url: str = None) -> Dict[str, Any]:
        """
        解析内容（子类必须实现）
        
        Args:
            content: 网页内容
            url: 源URL（可选）
            
        Returns:
            解析后的数据字典，包含 title, content, metadata 等
        """
        raise NotImplementedError
    
    def crawl(self, url: str) -> Optional[Dict[str, Any]]:
        """
        执行完整爬取流程
        
        Args:
            url: 目标URL
            
        Returns:
            解析后的数据字典，失败返回None
        """
        try:
            logger.info(f"开始爬取: {url}")
            content = self.fetch(url)
            if not content:
                return None
            
            result = self.parse(content, url)
            result['url'] = url
            logger.info(f"爬取成功: {url}, 标题: {result.get('title', 'N/A')}")
            return result
            
        except CrawlerError as e:
            logger.error(f"爬虫错误: {url}, {str(e)}")
            return None
        except Exception as e:
            logger.exception(f"未知错误: {url}, {str(e)}")
            return None
        finally:
            # 请求间隔
            if self.request_delay > 0:
                time.sleep(self.request_delay)