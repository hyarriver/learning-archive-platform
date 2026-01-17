"""
爬虫模块
"""
from app.crawler.base import BaseCrawler
from app.crawler.webpage import WebPageCrawler
from app.crawler.video import VideoCrawler

__all__ = ['BaseCrawler', 'WebPageCrawler', 'VideoCrawler']