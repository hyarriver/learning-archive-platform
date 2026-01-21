"""
爬虫模块
"""
from app.crawler.base import BaseCrawler
from app.crawler.webpage import WebPageCrawler
from app.crawler.video import VideoCrawler

# 尝试导入Selenium支持
try:
    from app.crawler.selenium_crawler import SeleniumWebPageCrawler, SELENIUM_AVAILABLE
    __all__ = ['BaseCrawler', 'WebPageCrawler', 'VideoCrawler', 'SeleniumWebPageCrawler', 'SELENIUM_AVAILABLE']
except ImportError:
    SELENIUM_AVAILABLE = False
    __all__ = ['BaseCrawler', 'WebPageCrawler', 'VideoCrawler']