"""
Selenium爬虫支持（用于JavaScript动态加载的页面）
"""
import time
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

from app.crawler.base import BaseCrawler
from app.crawler.parser import HTMLParser
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium未安装，无法使用JavaScript渲染功能。请安装: pip install selenium")


class SeleniumWebPageCrawler(BaseCrawler):
    """使用Selenium的网页爬虫（支持JavaScript渲染）"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化Selenium爬虫
        
        Args:
            config: 爬虫配置，可包含：
                - browser: 'chrome', 'edge', 'firefox' (默认: 'chrome')
                - headless: 是否无头模式 (默认: True)
                - wait_timeout: 等待超时时间（秒）(默认: 15)
                - driver_path: WebDriver路径（可选，默认使用系统PATH）
                - content_wait_selector: 等待内容出现的CSS选择器（可选，支持多个用逗号分隔）
                - scroll_to_load: 是否滚动页面触发懒加载 (默认: True)
                - extra_wait_time: 额外等待时间（秒）(默认: 2)
        """
        super().__init__(config)
        self.parser = HTMLParser(config)
        
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium未安装，请先安装: pip install selenium")
        
        # Selenium配置
        self.browser_type = self.config.get('browser', 'chrome').lower()
        self.headless = self.config.get('headless', True)
        self.wait_timeout = self.config.get('wait_timeout', 15)
        self.driver_path = self.config.get('driver_path')
        # 新增配置选项
        self.content_wait_selector = self.config.get('content_wait_selector')
        self.scroll_to_load = self.config.get('scroll_to_load', True)
        self.extra_wait_time = self.config.get('extra_wait_time', 2)
        
        # 初始化WebDriver（延迟初始化，避免每次创建）
        self._driver = None
    
    def _get_driver(self):
        """获取或创建WebDriver实例"""
        if self._driver is None:
            try:
                if self.browser_type == 'chrome':
                    options = ChromeOptions()
                    if self.headless:
                        options.add_argument('--headless=new')
                    options.add_argument('--disable-gpu')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    options.add_argument('--disable-blink-features=AutomationControlled')
                    # 设置用户代理
                    user_agent = self.config.get('user_agent') or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    options.add_argument(f'user-agent={user_agent}')
                    
                    if self.driver_path:
                        service = ChromeService(executable_path=self.driver_path)
                        self._driver = webdriver.Chrome(service=service, options=options)
                    else:
                        self._driver = webdriver.Chrome(options=options)
                        
                elif self.browser_type == 'edge':
                    options = EdgeOptions()
                    if self.headless:
                        options.add_argument('--headless=new')
                    options.add_argument('--disable-gpu')
                    options.add_argument('--disable-blink-features=AutomationControlled')
                    user_agent = self.config.get('user_agent') or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    options.add_argument(f'user-agent={user_agent}')
                    
                    if self.driver_path:
                        service = EdgeService(executable_path=self.driver_path)
                        self._driver = webdriver.Edge(service=service, options=options)
                    else:
                        self._driver = webdriver.Edge(options=options)
                        
                elif self.browser_type == 'firefox':
                    options = FirefoxOptions()
                    if self.headless:
                        options.add_argument('--headless')
                    user_agent = self.config.get('user_agent') or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    options.set_preference('general.useragent.override', user_agent)
                    
                    if self.driver_path:
                        service = FirefoxService(executable_path=self.driver_path)
                        self._driver = webdriver.Firefox(service=service, options=options)
                    else:
                        self._driver = webdriver.Firefox(options=options)
                else:
                    raise ValueError(f"不支持的浏览器类型: {self.browser_type}")
                
                # 设置页面加载超时
                self._driver.set_page_load_timeout(30)
                self._driver.implicitly_wait(5)
                
                logger.info(f"Selenium WebDriver已初始化: {self.browser_type}, headless={self.headless}")
                
            except WebDriverException as e:
                logger.error(f"初始化WebDriver失败: {e}")
                raise
        
        return self._driver
    
    def _wait_for_content(self, driver):
        """
        智能等待内容加载完成
        
        Args:
            driver: WebDriver实例
        """
        wait = WebDriverWait(driver, self.wait_timeout)
        
        # 步骤1: 等待文档readyState为complete
        try:
            wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
            logger.debug("文档readyState已为complete")
        except TimeoutException:
            logger.warning("等待文档readyState超时")
        
        # 步骤2: 等待body元素出现
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.debug("body元素已出现")
        except TimeoutException:
            logger.warning("等待body元素超时")
        
        # 步骤3: 如果配置了内容等待选择器，等待该元素出现
        if self.content_wait_selector:
            try:
                # 支持多个选择器（用逗号分隔）
                selectors = [s.strip() for s in self.content_wait_selector.split(',')]
                found = False
                for selector in selectors:
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        logger.info(f"内容元素已出现: {selector}")
                        found = True
                        break
                    except TimeoutException:
                        continue
                if not found:
                    logger.warning(f"等待内容选择器超时: {self.content_wait_selector}")
            except Exception as e:
                logger.warning(f"等待内容选择器时出错: {e}")
        
        # 步骤4: 等待网络空闲（检查是否有未完成的网络请求）
        try:
            # 使用JavaScript检查网络请求状态
            max_attempts = 10
            for attempt in range(max_attempts):
                network_idle = driver.execute_script("""
                    return window.performance.getEntriesByType('resource').some(function(r) {
                        return r.transferSize === 0 && r.name.indexOf(window.location.href) === 0;
                    }) ? false : (document.readyState === 'complete');
                """)
                if network_idle:
                    break
                time.sleep(0.5)
        except Exception as e:
            logger.debug(f"检查网络空闲状态时出错（可忽略）: {e}")
        
        # 步骤5: 额外等待时间（确保JavaScript完全执行）
        if self.extra_wait_time > 0:
            time.sleep(self.extra_wait_time)
    
    def _scroll_to_trigger_lazy_load(self, driver):
        """
        滚动页面触发懒加载内容
        
        Args:
            driver: WebDriver实例
        """
        if not self.scroll_to_load:
            return
        
        try:
            # 获取页面初始高度
            initial_height = driver.execute_script("return document.body.scrollHeight")
            
            # 滚动到底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # 再次获取页面高度（懒加载可能会增加页面高度）
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # 如果页面高度增加，继续滚动
            scroll_attempts = 0
            max_scroll_attempts = 3
            while new_height > initial_height and scroll_attempts < max_scroll_attempts:
                initial_height = new_height
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = driver.execute_script("return document.body.scrollHeight")
                scroll_attempts += 1
            
            # 滚动到顶部
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
            logger.debug(f"页面滚动完成（触发懒加载）")
        except Exception as e:
            logger.warning(f"滚动页面时出错: {e}")
    
    def fetch(self, url: str) -> Optional[str]:
        """
        使用Selenium获取网页内容（支持JavaScript渲染）
        
        Args:
            url: 目标URL
            
        Returns:
            网页HTML字符串，失败返回None
        """
        try:
            driver = self._get_driver()
            logger.info(f"Selenium开始加载页面: {url}")
            
            driver.get(url)
            
            # 智能等待内容加载完成
            self._wait_for_content(driver)
            
            # 滚动页面触发懒加载
            self._scroll_to_trigger_lazy_load(driver)
            
            # 再次等待以确保滚动后的内容加载完成
            if self.scroll_to_load:
                time.sleep(1)
            
            # 获取页面HTML
            html = driver.page_source
            logger.info(f"Selenium成功获取页面内容: {url}")
            return html
            
        except Exception as e:
            logger.error(f"Selenium获取页面失败: {url}, 错误: {str(e)}")
            return None
    
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
        从搜索结果页面提取链接（支持JavaScript渲染）
        
        Args:
            url: 搜索结果页面URL
            max_links: 最大提取链接数
            wait_selector: 等待结果出现的CSS选择器（可选）
            
        Returns:
            链接URL列表
        """
        try:
            driver = self._get_driver()
            logger.info(f"Selenium开始加载搜索结果页面: {url}")
            
            driver.get(url)
            
            # 等待页面完全加载（等待Vue/React应用初始化）
            try:
                # 等待页面加载完成
                WebDriverWait(driver, self.wait_timeout).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                logger.info("页面DOM加载完成")
            except TimeoutException:
                logger.warning("页面DOM加载超时")
            
            # 如果提供了等待选择器，等待搜索结果出现
            if wait_selector:
                try:
                    WebDriverWait(driver, self.wait_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                    )
                    logger.info(f"搜索结果容器已出现: {wait_selector}")
                except TimeoutException:
                    logger.warning(f"等待搜索结果超时: {wait_selector}，尝试继续...")
            else:
                # 没有指定选择器，尝试等待常见的搜索结果容器
                common_wait_selectors = [
                    '.search-list-con',
                    '.search-list',
                    '.search-result',
                    '[class*="search"]',
                    '[id*="search"]',
                    'article',
                    '.result-item'
                ]
                found = False
                for selector in common_wait_selectors:
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"检测到搜索结果容器: {selector}")
                        found = True
                        break
                    except TimeoutException:
                        continue
                if not found:
                    logger.warning("未检测到常见的搜索结果容器")
            
            # 额外等待JavaScript执行（Vue/React应用渲染）
            time.sleep(3)  # 增加等待时间，确保动态内容加载完成
            
            # 尝试滚动页面触发懒加载
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, 0);")
            except Exception:
                pass
            
            # 获取页面HTML
            content = driver.page_source
            soup = BeautifulSoup(content, 'lxml')
            
            # 使用解析器提取链接
            links = self.parser.extract_search_links(soup, base_url=url, max_links=max_links)
            
            # 如果提取失败，尝试直接通过Selenium查找链接
            if not links or len(links) == 0:
                logger.warning("使用BeautifulSoup未提取到链接，尝试通过Selenium直接查找...")
                
                # 尝试多种选择器直接查找链接
                link_selectors = [
                    '.search-list-con .search-item h3 a',
                    '.search-list-con h3 a',
                    '.search-item h3 a',
                    '.search-item a.title',
                    '.result-item h3 a',
                    'article h3 a',
                    'a[href*="blog.csdn.net"]',
                    'a[href*="download.csdn.net"]'
                ]
                
                selenium_links = []
                for selector in link_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements[:max_links]:
                            href = elem.get_attribute('href')
                            if href and href not in selenium_links:
                                # 过滤搜索页面本身
                                if '/search' not in href.lower() or '/so/search' not in href.lower():
                                    selenium_links.append(href)
                                if len(selenium_links) >= max_links:
                                    break
                        if selenium_links:
                            logger.info(f"通过Selenium选择器 {selector} 找到 {len(selenium_links)} 个链接")
                            break
                    except Exception as e:
                        logger.debug(f"选择器 {selector} 查找失败: {e}")
                        continue
                
                if selenium_links:
                    links = selenium_links
            
            logger.info(f"Selenium从搜索结果页面提取到 {len(links)} 个链接: {url}")
            if links:
                logger.debug(f"前3个链接示例: {links[:3]}")
            return links
            
        except Exception as e:
            logger.error(f"Selenium提取搜索链接失败: {url}, 错误: {str(e)}")
            return []
    
    def close(self):
        """关闭WebDriver"""
        if self._driver is not None:
            try:
                self._driver.quit()
                self._driver = None
                logger.info("Selenium WebDriver已关闭")
            except Exception as e:
                logger.warning(f"关闭WebDriver时出错: {e}")
    
    def __del__(self):
        """析构函数，确保WebDriver被关闭"""
        self.close()
