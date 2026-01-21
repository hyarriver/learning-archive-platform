"""
CSDN API接口爬虫（尝试分析并使用CSDN的实际API接口）
"""
import json
import time
import requests
from typing import Dict, Any, Optional, List

from app.crawler.base import BaseCrawler
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CSDNSearchAPI:
    """CSDN搜索API接口分析"""
    
    def __init__(self):
        """初始化CSDN API客户端"""
        self.base_url = "https://so.csdn.net/api/v3/search"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://so.csdn.net/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
    
    def search(self, keyword: str, page: int = 1, page_size: int = 20) -> Optional[Dict]:
        """
        搜索CSDN内容
        
        Args:
            keyword: 搜索关键词
            page: 页码（从1开始）
            page_size: 每页数量
            
        Returns:
            搜索结果JSON，失败返回None
        """
        try:
            # 尝试CSDN可能的API端点
            api_endpoints = [
                f"{self.base_url}?q={keyword}&p={page}&t=all&o=&s=&l=&v=&isd=&page={page}&size={page_size}",
                f"https://so.csdn.net/api/v2/search?q={keyword}&p={page}",
                f"https://so.csdn.net/so/search/s.do?q={keyword}&t=all&p={page}"
            ]
            
            for endpoint in api_endpoints:
                try:
                    logger.debug(f"尝试CSDN API端点: {endpoint}")
                    response = self.session.get(endpoint, timeout=10)
                    logger.debug(f"API响应状态码: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '').lower()
                        if 'application/json' in content_type:
                            data = response.json()
                            logger.info(f"✓ 成功调用CSDN API: {endpoint}")
                            return data
                        else:
                            # 尝试解析为JSON（即使Content-Type不是JSON）
                            try:
                                data = response.json()
                                logger.info(f"✓ 成功调用CSDN API（强制JSON解析）: {endpoint}")
                                return data
                            except Exception as parse_error:
                                logger.debug(f"响应不是JSON格式: {parse_error}")
                                # 如果不是JSON，可能是HTML，记录部分内容
                                if len(response.text) < 500:
                                    logger.debug(f"API响应内容（前500字符）: {response.text[:500]}")
                except Exception as e:
                    logger.debug(f"API端点 {endpoint} 请求失败: {e}")
                    continue
            
            logger.warning(f"所有CSDN API端点都失败，关键词: {keyword}")
            return None
            
        except Exception as e:
            logger.error(f"CSDN API搜索失败: {keyword}, 错误: {str(e)}")
            return None
    
    def extract_links_from_api(self, api_result: Dict, max_links: int = 50) -> List[str]:
        """
        从API结果中提取链接
        
        Args:
            api_result: API返回的JSON数据
            max_links: 最大链接数
            
        Returns:
            链接URL列表
        """
        links = []
        
        if not api_result:
            return links
        
        # 尝试多种可能的JSON结构
        possible_paths = [
            ['result_vos'],  # CSDN可能的结构
            ['data', 'result_vos'],
            ['data', 'result'],
            ['data', 'items'],
            ['data', 'list'],
            ['result'],
            ['items'],
            ['list'],
            ['data']
        ]
        
        items = None
        for path in possible_paths:
            try:
                items = api_result
                for key in path:
                    if isinstance(items, dict) and key in items:
                        items = items[key]
                    elif isinstance(items, list):
                        break
                    else:
                        items = None
                        break
                
                if items and isinstance(items, list) and len(items) > 0:
                    logger.info(f"找到结果项，路径: {path}, 数量: {len(items)}")
                    break
            except Exception:
                continue
        
        if not items or not isinstance(items, list):
            logger.warning(f"无法从API结果中提取结果项，JSON结构: {list(api_result.keys()) if isinstance(api_result, dict) else type(api_result)}")
            return links
        
        # 提取每个结果项的链接
        for item in items[:max_links]:
            if not isinstance(item, dict):
                continue
            
            # 尝试多种可能的链接字段
            link_fields = ['url', 'link', 'href', 'article_url', 'blog_url', 'download_url']
            for field in link_fields:
                if field in item and item[field]:
                    link = item[field]
                    # 确保是完整URL
                    if link.startswith('http'):
                        if link not in links:
                            links.append(link)
                        break
                    elif link.startswith('//'):
                        if f"https:{link}" not in links:
                            links.append(f"https:{link}")
                        break
                    elif link.startswith('/'):
                        if f"https://so.csdn.net{link}" not in links:
                            links.append(f"https://so.csdn.net{link}")
                        break
        
        logger.info(f"从API结果中提取到 {len(links)} 个链接")
        return links
