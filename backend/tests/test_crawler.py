"""
爬虫模块测试
"""
import pytest
from unittest.mock import Mock, patch
from app.crawler.base import BaseCrawler, CrawlerError
from app.crawler.webpage import WebPageCrawler


class TestBaseCrawler:
    """基础爬虫测试"""
    
    def test_fetch_success(self):
        """测试成功获取内容"""
        crawler = BaseCrawler()
        
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.text = "<html><body>Test</body></html>"
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            content = crawler.fetch("http://example.com")
            assert content == "<html><body>Test</body></html>"
    
    def test_fetch_retry(self):
        """测试重试机制"""
        crawler = BaseCrawler(config={"max_retries": 3})
        
        with patch('requests.Session.get') as mock_get:
            # 前两次失败，第三次成功
            mock_get.side_effect = [
                Exception("Connection error"),
                Exception("Timeout"),
                Mock(
                    text="<html>Success</html>",
                    headers={"Content-Type": "text/html"},
                    raise_for_status=Mock()
                )
            ]
            
            content = crawler.fetch("http://example.com")
            assert content == "<html>Success</html>"
            assert mock_get.call_count == 3
    
    def test_fetch_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        crawler = BaseCrawler(config={"max_retries": 2})
        
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = Exception("Connection error")
            
            with pytest.raises(CrawlerError):
                crawler.fetch("http://example.com")
            
            assert mock_get.call_count == 2


class TestWebPageCrawler:
    """网页爬虫测试"""
    
    def test_parse_basic_html(self):
        """测试解析基本HTML"""
        crawler = WebPageCrawler()
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Title</h1>
                <p>Test content</p>
            </body>
        </html>
        """
        
        result = crawler.parse(html)
        assert result["title"] == "Test Page"
        assert "Test content" in result["content"]
