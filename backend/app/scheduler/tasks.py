"""
定时任务调度
"""
import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, CollectionSource, File, CollectionLog
from app.crawler import WebPageCrawler, VideoCrawler
from app.converter import (
    MarkdownConverter,
    TOCGenerator,
    TagExtractor,
    SummaryGenerator
)
from app.converter.image_downloader import ImageDownloader
from app.storage import FileManager, VersionManager
from app.utils.helpers import calculate_file_hash
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CollectionScheduler:
    """采集任务调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        self.file_manager = FileManager()
        self.version_manager = VersionManager()
        self.markdown_converter = MarkdownConverter()
        self.toc_generator = TOCGenerator()
        self.tag_extractor = TagExtractor()
        self.summary_generator = SummaryGenerator()
        # 创建线程池执行器用于运行同步的爬虫代码
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="crawler")
        # 进度跟踪：{source_id: {'status': 'running', 'progress': 0-100, 'message': '...', 'start_time': ..., 'end_time': ...}}
        self.progress = {}
    
    def start(self):
        """启动调度器"""
        # 添加定时任务（每天0点执行）
        self.scheduler.add_job(
            self.collect_all_sources,
            trigger=CronTrigger(
                hour=settings.collection_schedule_hour,
                minute=settings.collection_schedule_minute
            ),
            id='daily_collection',
            name='每日采集任务',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(f"任务调度器已启动，每日 {settings.collection_schedule_hour}:{settings.collection_schedule_minute:02d} 执行采集任务")
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        # 关闭线程池
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        logger.info("任务调度器已停止")
    
    async def collect_all_sources(self):
        """
        采集所有启用的源（异步任务）
        """
        logger.info("开始执行每日采集任务")
        
        # 获取数据库会话
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # 获取所有启用的采集源
            sources = db.query(CollectionSource).filter(
                CollectionSource.enabled == True
            ).all()
            
            if not sources:
                logger.info("没有启用的采集源")
                return
            
            logger.info(f"找到 {len(sources)} 个启用的采集源")
            
            # 遍历每个源进行采集
            for source in sources:
                try:
                    await self.collect_source(db, source)
                except Exception as e:
                    logger.error(f"采集源失败: {source.name}, 错误: {str(e)}")
                    continue
            
            logger.info("每日采集任务执行完成")
            
        except Exception as e:
            logger.exception(f"采集任务执行异常: {str(e)}")
        finally:
            db.close()
    
    def _update_progress(self, source_id: int, status: str, progress: int, message: str):
        """
        更新采集进度
        
        Args:
            source_id: 采集源ID
            status: 状态 ('pending', 'running', 'completed', 'failed')
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        if source_id not in self.progress:
            self.progress[source_id] = {
                'status': status,
                'progress': progress,
                'message': message,
                'start_time': datetime.utcnow().isoformat(),
                'end_time': None
            }
        else:
            self.progress[source_id].update({
                'status': status,
                'progress': progress,
                'message': message
            })
        
        # 如果完成或失败，记录结束时间
        if status in ('completed', 'failed'):
            self.progress[source_id]['end_time'] = datetime.utcnow().isoformat()
    
    def get_progress(self, source_id: int) -> Optional[Dict[str, Any]]:
        """
        获取采集进度
        
        Args:
            source_id: 采集源ID
            
        Returns:
            进度信息字典，如果不存在则返回None
        """
        return self.progress.get(source_id)
    
    def clear_progress(self, source_id: int):
        """
        清除采集进度（任务完成后一段时间可清除）
        
        Args:
            source_id: 采集源ID
        """
        if source_id in self.progress:
            del self.progress[source_id]
    
    async def collect_source(self, db: Session, source: CollectionSource):
        """
        采集单个源
        
        Args:
            db: 数据库会话
            source: 采集源对象
        """
        logger.info(f"开始采集源: {source.name}")
        
        # 初始化进度
        self._update_progress(source.id, 'pending', 0, '准备开始采集...')
        
        try:
            # 更新进度：解析配置
            self._update_progress(source.id, 'running', 10, '解析爬虫配置...')
            
            # 解析爬虫配置
            crawler_config = {}
            if source.crawler_config:
                try:
                    crawler_config = json.loads(source.crawler_config)
                except json.JSONDecodeError as e:
                    logger.warning(f"解析爬虫配置失败: {source.name}, 错误: {e}")
            
            # 创建爬虫实例
            if source.source_type == 'webpage':
                crawler = WebPageCrawler(config=crawler_config)
            elif source.source_type == 'video':
                crawler = VideoCrawler(config=crawler_config)
            else:
                logger.error(f"不支持的源类型: {source.source_type}")
                self._update_progress(source.id, 'failed', 0, f'不支持的源类型: {source.source_type}')
                return
            
            # 检查是否有搜索参数，如果有则进入搜索模式
            search_params = None
            if source.search_params:
                try:
                    search_params = json.loads(source.search_params)
                    # 验证搜索参数不为空
                    if not search_params or not isinstance(search_params, dict) or len(search_params) == 0:
                        logger.warning(f"搜索参数为空或无效: {source.name}")
                        search_params = None
                except json.JSONDecodeError as e:
                    logger.warning(f"解析搜索参数失败: {source.name}, 错误: {e}")
                    search_params = None
            
            # 如果有搜索参数，使用搜索模式（批量采集）
            if search_params:
                logger.info(f"使用搜索模式采集: {source.name}, 搜索参数: {search_params}")
                await self._collect_from_search(db, source, crawler, search_params)
                return
            else:
                logger.info(f"使用单URL模式采集: {source.name}, URL: {source.url_pattern}")
            
            # 否则使用单URL模式
            # 解析URL模式（简化版：直接使用URL模式作为URL）
            url = source.url_pattern
            
            # 更新进度：开始爬取
            self._update_progress(source.id, 'running', 20, f'正在爬取内容: {url[:50]}...')
            
            # 在线程池中执行同步的爬虫代码，避免阻塞事件循环
            # Python 3.9+ 支持 asyncio.to_thread，它会在完全独立的线程中执行，自动处理事件循环隔离
            result = await asyncio.to_thread(crawler.crawl, url)
            
            if not result:
                # 记录失败日志
                error_msg = '爬取失败，未返回结果'
                log = CollectionLog(
                    source_id=source.id,
                    url=url,
                    status='failed',
                    error_message=error_msg
                )
                db.add(log)
                db.commit()
                logger.warning(f"采集失败: {source.name}, URL: {url}")
                self._update_progress(source.id, 'failed', 30, error_msg)
                return
            
            # 更新进度：爬取完成，开始转换
            self._update_progress(source.id, 'running', 40, '爬取完成，正在下载图片...')
            
            # 转换为Markdown（所有同步操作在线程池中执行）
            content_html = result.get('content', '')
            title = result.get('title', '无标题')
            source_url = result.get('url', url)  # 获取源URL用于解析相对路径图片
            
            # 计算日期字符串（用于图片保存路径）
            date = datetime.now()
            date_str = date.strftime("%Y-%m-%d")
            
            # 定义一个内部函数来执行所有同步的转换操作
            def _process_content():
                if source.source_type == 'webpage':
                    # 先下载图片并替换HTML中的图片链接
                    images_dir = self.file_manager.collections_dir
                    image_downloader = ImageDownloader(
                        base_url=source_url,
                        images_dir=images_dir
                    )
                    
                    # 下载图片并替换HTML中的链接
                    content_html_with_local_images = image_downloader.download_images_from_html(
                        html=content_html,
                        source_name=source.name,
                        title=title,
                        date_str=date_str
                    )
                    
                    # HTML转Markdown（图片链接已替换为本地路径）
                    markdown_content = self.markdown_converter.convert(content_html_with_local_images, title=title)
                    # 生成TOC（仅对网页类型）
                    markdown_content = self.toc_generator.generate(markdown_content)
                else:
                    # 视频类型：content 已经是格式化的 Markdown，包含视频信息和链接
                    markdown_content = content_html
                    # 视频类型不需要生成 TOC
                
                # 提取标签和摘要
                tags = self.tag_extractor.extract(markdown_content, title=title)
                summary = self.summary_generator.generate(markdown_content, title=title)
                
                # 计算内容哈希
                content_hash = calculate_file_hash(markdown_content)
                
                return markdown_content, tags, summary, content_hash
            
            # 在线程池中执行同步操作
            # 使用 None 作为 executor 以避免与已有的事件循环冲突
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            
            markdown_content, tags, summary, content_hash = await loop.run_in_executor(
                None, _process_content
            )
            
            # 更新进度：转换完成，检查文件
            self._update_progress(source.id, 'running', 60, '转换完成，正在检查文件...')
            
            # 检查是否已存在相同内容的文件（去重）
            existing_file = db.query(File).filter(
                File.source_id == source.id,
                File.file_hash == content_hash
            ).first()
            
            if existing_file:
                # 文件已存在，创建新版本（如果内容有变化）
                logger.info(f"文件已存在，检查版本: {source.name}, 标题: {title}")
                self._update_progress(source.id, 'running', 80, '文件已存在，创建新版本...')
                
                self.version_manager.create_version(
                    db=db,
                    file_id=existing_file.id,
                    content=markdown_content,
                    current_file_path=Path(existing_file.file_path)
                )
                
                # 记录成功日志
                log = CollectionLog(
                    source_id=source.id,
                    url=url,
                    status='success',
                    file_id=existing_file.id
                )
                db.add(log)
                db.commit()
                
                self._update_progress(source.id, 'completed', 100, f'采集完成: {title}')
                return
            
            # 更新进度：保存文件
            self._update_progress(source.id, 'running', 80, '正在保存文件...')
            
            # 保存文件
            date = datetime.now()
            file_path = self.file_manager.save_collection(
                source_name=source.name,
                title=title,
                content=markdown_content,
                date=date
            )
            
            # 更新进度：创建数据库记录
            self._update_progress(source.id, 'running', 90, '正在创建数据库记录...')
            
            # 创建文件记录
            file_record = File(
                title=title,
                source_id=source.id,
                file_path=str(file_path),
                file_hash=content_hash,
                tags=json.dumps(tags, ensure_ascii=False) if tags else None,
                summary=summary
            )
            
            db.add(file_record)
            db.commit()
            db.refresh(file_record)
            
            # 记录成功日志
            log = CollectionLog(
                source_id=source.id,
                url=url,
                status='success',
                file_id=file_record.id
            )
            db.add(log)
            db.commit()
            
            logger.info(f"采集成功: {source.name}, 标题: {title}, 文件ID: {file_record.id}")
            self._update_progress(source.id, 'completed', 100, f'采集完成: {title}')
        
        except Exception as e:
            # 安全地获取错误信息，完全避免格式化异常对象本身
            # 因为异常对象可能包含异步相关信息，格式化时会触发 asyncio.run()
            error_type_name = type(e).__name__
            
            # 构建简单的错误消息，不格式化异常对象本身
            error_msg = f"{error_type_name}: 采集失败"
            
            # 尝试从异常消息中提取信息（如果异常有 args 属性）
            try:
                if hasattr(e, 'args') and e.args:
                    # 只使用第一个参数，避免格式化整个异常对象
                    first_arg = e.args[0] if e.args else None
                    if first_arg and isinstance(first_arg, str):
                        error_msg = f"{error_type_name}: {first_arg[:400]}"
            except Exception:
                pass  # 如果提取失败，使用默认消息
            
            # 使用 logger.error 而不是 logger.exception
            # logger.exception 会格式化完整 traceback，可能触发异步操作
            try:
                logger.error(f"采集源异常: {source.name}, 错误: {error_msg}")
            except Exception:
                # 如果日志记录失败，至少输出到标准错误
                import sys
                try:
                    print(f"采集源异常: {source.name}, 错误: {error_msg}", file=sys.stderr, flush=True)
                except:
                    pass
            
            # 更新进度为失败
            self._update_progress(source.id, 'failed', 0, error_msg[:200])
            
            # 记录失败日志到数据库
            try:
                log = CollectionLog(
                    source_id=source.id,
                    url=source.url_pattern,
                    status='failed',
                    error_message=error_msg[:500]  # 限制错误消息长度
                )
                db.add(log)
                db.commit()
            except Exception:
                # 如果数据库操作失败，忽略（避免在异常处理中再次出错）
                pass
        finally:
            # 确保爬虫资源被释放（特别是Selenium）
            if 'crawler' in locals() and hasattr(crawler, 'close'):
                try:
                    crawler.close()
                except Exception:
                    pass
    
    async def _collect_from_search(self, db: Session, source: CollectionSource, crawler, search_params: dict):
        """
        从搜索结果批量采集
        
        Args:
            db: 数据库会话
            source: 采集源对象
            crawler: 爬虫实例
            search_params: 搜索参数字典，如 {"keyword": "Python", "page": "1"}
        """
        try:
            # 构建搜索URL
            base_url = source.url_pattern
            search_url = self._build_search_url(base_url, search_params)
            
            logger.info(f"开始搜索模式采集: {source.name}, 搜索URL: {search_url}")
            
            # 更新进度：开始搜索
            self._update_progress(source.id, 'running', 5, '正在搜索内容...')
            
            # 提取搜索结果链接
            # 对于视频类型，使用 WebPageCrawler 提取链接，然后过滤出视频链接
            if source.source_type == 'video':
                # 视频类型：需要先使用网页爬虫提取搜索链接，然后过滤出视频链接
                logger.info(f"视频类型搜索模式：使用网页爬虫提取搜索链接，然后过滤视频链接")
                webpage_crawler = WebPageCrawler(config=crawler_config)
                
                # 获取等待选择器配置（用于Selenium）
                wait_selector = None
                if webpage_crawler.config:
                    wait_selector = webpage_crawler.config.get('search_wait_selector')
                
                # 在线程池中提取搜索链接
                if wait_selector:
                    all_links = await asyncio.to_thread(webpage_crawler.extract_search_links, search_url, 50, wait_selector)
                else:
                    all_links = await asyncio.to_thread(webpage_crawler.extract_search_links, search_url, 50)
                
                # 过滤出视频链接（B站、YouTube等）
                search_links = []
                for link in all_links:
                    # 检查是否为视频链接
                    if self._is_video_link(link):
                        search_links.append(link)
                
                if not search_links:
                    logger.warning(f"未找到视频链接，原始链接数: {len(all_links)}")
                    logger.info(f"提示：可能是：1) 搜索结果中没有视频链接；2) 链接格式不匹配；3) 需要使用Selenium加载动态内容")
                
                # 关闭网页爬虫资源
                try:
                    webpage_crawler.close()
                except Exception:
                    pass
            else:
                # 网页类型：直接使用传入的爬虫提取链接
                # 获取等待选择器配置（用于Selenium）
                wait_selector = None
                if isinstance(crawler, WebPageCrawler) and crawler.config:
                    wait_selector = crawler.config.get('search_wait_selector')
                
                # 在线程池中提取搜索链接
                if wait_selector:
                    search_links = await asyncio.to_thread(crawler.extract_search_links, search_url, 50, wait_selector)
                else:
                    search_links = await asyncio.to_thread(crawler.extract_search_links, search_url, 50)
            
            if not search_links:
                error_msg = '未找到搜索结果链接（可能是JavaScript动态加载，需要使用其他方法）'
                self._update_progress(source.id, 'failed', 10, error_msg)
                logger.warning(f"搜索未找到链接: {source.name}, URL: {search_url}")
                logger.info(f"提示: {source.name} 的搜索结果可能是JavaScript动态加载的，BeautifulSoup无法提取。可能需要：1) 使用Selenium等工具；2) 分析网站API接口；3) 配置特定的选择器")
                # 记录失败日志
                try:
                    log = CollectionLog(
                        source_id=source.id,
                        url=search_url,
                        status='failed',
                        error_message=error_msg
                    )
                    db.add(log)
                    db.commit()
                except Exception:
                    pass
                return
            
            # 过滤掉搜索页面本身（避免采集搜索页面）
            from urllib.parse import urlparse
            search_parsed = urlparse(search_url)
            search_base = f"{search_parsed.scheme}://{search_parsed.netloc}{search_parsed.path}"
            
            filtered_links = []
            filtered_reasons = {}  # 记录过滤原因用于调试
            
            for link in search_links:
                link_parsed = urlparse(link)
                filtered = False
                reason = None
                
                # 排除搜索页面本身
                if link == search_url:
                    filtered = True
                    reason = "搜索页面本身"
                
                # 排除与搜索页面相同路径的链接（可能是查询参数不同）
                elif link_parsed.netloc == search_parsed.netloc and link_parsed.path == search_parsed.path:
                    filtered = True
                    reason = "与搜索页面相同路径"
                
                # 更精确地排除搜索相关URL路径（只排除明确的搜索路径）
                # 避免误过滤包含"search"的内容页面
                elif (link_parsed.path.lower() == '/search' or 
                      link_parsed.path.lower().startswith('/search?') or
                      link_parsed.path.lower().startswith('/search/') or
                      link_parsed.path.lower() == '/so/search' or
                      link_parsed.path.lower().startswith('/so/search?') or
                      link_parsed.path.lower().startswith('/so/search/')):
                    filtered = True
                    reason = "搜索路径"
                
                # 注意：不再过滤查询参数中包含search的链接
                # 因为很多内容链接也可能有查询参数，误过滤风险太大
                
                if filtered:
                    if reason:
                        filtered_reasons[link] = reason
                    logger.debug(f"排除链接 ({reason}): {link}")
                else:
                    filtered_links.append(link)
            
            # 如果过滤后没有链接，记录详细信息用于调试
            if not filtered_links:
                error_msg = f'过滤后未找到有效的搜索结果链接（原始链接数: {len(search_links)}，可能所有链接都被过滤掉了）'
                self._update_progress(source.id, 'failed', 10, error_msg)
                logger.warning(f"过滤后未找到有效链接: {source.name}, 原始链接数: {len(search_links)}, 搜索URL: {search_url}")
                
                # 记录前几个链接和过滤原因用于调试
                if search_links:
                    logger.warning(f"前5个原始链接示例:")
                    for i, link in enumerate(search_links[:5], 1):
                        reason = filtered_reasons.get(link, "未知原因")
                        logger.warning(f"  {i}. {link} (过滤原因: {reason})")
                
                # 记录失败日志，包含原始链接信息用于调试
                try:
                    log = CollectionLog(
                        source_id=source.id,
                        url=search_url,
                        status='failed',
                        error_message=error_msg
                    )
                    db.add(log)
                    db.commit()
                except Exception:
                    pass
                return
            
            logger.info(f"找到 {len(search_links)} 个链接，过滤后剩余 {len(filtered_links)} 个有效链接")
            if filtered_links:
                logger.info(f"前3个有效链接示例: {filtered_links[:3]}")
            search_links = filtered_links
            
            # 更新进度：开始批量采集
            total = len(search_links)
            success_count = 0
            fail_count = 0
            
            for idx, link_url in enumerate(search_links):
                try:
                    # 计算进度 (10-90%)
                    progress = 10 + int((idx / total) * 80)
                    self._update_progress(source.id, 'running', progress, f'正在采集 ({idx + 1}/{total}): {link_url[:50]}...')
                    
                    # 爬取单个链接
                    # 如果是视频类型，确保使用 VideoCrawler
                    if source.source_type == 'video':
                        video_crawler = VideoCrawler(config=crawler_config)
                        result = await asyncio.to_thread(video_crawler.crawl, link_url)
                    else:
                        result = await asyncio.to_thread(crawler.crawl, link_url)
                    
                    if not result:
                        fail_count += 1
                        # 记录失败日志
                        log = CollectionLog(
                            source_id=source.id,
                            url=link_url,
                            status='failed',
                            error_message='爬取失败，未返回结果'
                        )
                        db.add(log)
                        continue
                    
                    # 处理内容
                    content_html = result.get('content', '')
                    title = result.get('title', '无标题')
                    source_url = result.get('url', link_url)  # 获取源URL用于解析相对路径图片
                    
                    # 计算日期字符串（用于图片保存路径）
                    date = datetime.now()
                    date_str = date.strftime("%Y-%m-%d")
                    
                    # 处理内容转换
                    def _process_content():
                        if source.source_type == 'webpage':
                            # 先下载图片并替换HTML中的图片链接
                            images_dir = self.file_manager.collections_dir
                            image_downloader = ImageDownloader(
                                base_url=source_url,
                                images_dir=images_dir
                            )
                            
                            # 下载图片并替换HTML中的链接
                            content_html_with_local_images = image_downloader.download_images_from_html(
                                html=content_html,
                                source_name=source.name,
                                title=title,
                                date_str=date_str
                            )
                            
                            # HTML转Markdown（图片链接已替换为本地路径）
                            markdown_content = self.markdown_converter.convert(content_html_with_local_images, title=title)
                            # 生成TOC（仅对网页类型）
                            markdown_content = self.toc_generator.generate(markdown_content)
                        else:
                            # 视频类型：content 已经是格式化的 Markdown，包含视频信息和链接
                            markdown_content = content_html
                            # 视频类型不需要生成 TOC
                        
                        tags = self.tag_extractor.extract(markdown_content, title=title)
                        summary = self.summary_generator.generate(markdown_content, title=title)
                        content_hash = calculate_file_hash(markdown_content)
                        
                        return markdown_content, tags, summary, content_hash
                    
                    loop = asyncio.get_running_loop()
                    markdown_content, tags, summary, content_hash = await loop.run_in_executor(
                        None, _process_content
                    )
                    
                    # 检查是否已存在
                    existing_file = db.query(File).filter(
                        File.source_id == source.id,
                        File.file_hash == content_hash
                    ).first()
                    
                    if existing_file:
                        # 已存在，创建新版本
                        self.version_manager.create_version(
                            db=db,
                            file_id=existing_file.id,
                            content=markdown_content,
                            current_file_path=Path(existing_file.file_path)
                        )
                        log = CollectionLog(
                            source_id=source.id,
                            url=link_url,
                            status='success',
                            file_id=existing_file.id
                        )
                        db.add(log)
                        db.commit()
                        success_count += 1
                    else:
                        # 保存新文件
                        date = datetime.now()
                        file_path = self.file_manager.save_collection(
                            source_name=source.name,
                            title=title,
                            content=markdown_content,
                            date=date
                        )
                        
                        file_record = File(
                            title=title,
                            source_id=source.id,
                            file_path=str(file_path),
                            file_hash=content_hash,
                            tags=json.dumps(tags, ensure_ascii=False) if tags else None,
                            summary=summary
                        )
                        
                        db.add(file_record)
                        db.commit()
                        db.refresh(file_record)
                        
                        log = CollectionLog(
                            source_id=source.id,
                            url=link_url,
                            status='success',
                            file_id=file_record.id
                        )
                        db.add(log)
                        db.commit()
                        success_count += 1
                    
                except Exception as e:
                    fail_count += 1
                    error_type_name = type(e).__name__
                    error_msg = f"{error_type_name}: 采集失败"
                    try:
                        if hasattr(e, 'args') and e.args and isinstance(e.args[0], str):
                            error_msg = f"{error_type_name}: {e.args[0][:200]}"
                    except Exception:
                        pass
                    
                    logger.error(f"采集链接失败: {link_url}, 错误: {error_msg}")
                    
                    # 记录失败日志
                    try:
                        log = CollectionLog(
                            source_id=source.id,
                            url=link_url,
                            status='failed',
                            error_message=error_msg[:500]
                        )
                        db.add(log)
                        db.commit()
                    except Exception:
                        pass
                    
                    continue
            
            # 完成
            message = f'批量采集完成: 成功 {success_count}/{total}, 失败 {fail_count}/{total}'
            logger.info(f"搜索模式采集完成: {source.name}, {message}")
            self._update_progress(source.id, 'completed', 100, message)
        
        except Exception as e:
            error_type_name = type(e).__name__
            error_msg = f"{error_type_name}: 搜索采集失败"
            try:
                if hasattr(e, 'args') and e.args and isinstance(e.args[0], str):
                    error_msg = f"{error_type_name}: {e.args[0][:200]}"
            except Exception:
                pass
            
            logger.error(f"搜索模式采集异常: {source.name}, 错误: {error_msg}")
            self._update_progress(source.id, 'failed', 0, error_msg)
        finally:
            # 确保爬虫资源被释放（特别是Selenium）
            if 'crawler' in locals() and hasattr(crawler, 'close'):
                try:
                    crawler.close()
                except Exception:
                    pass
    
    def _is_video_link(self, url: str) -> bool:
        """
        判断链接是否为视频链接
        
        Args:
            url: 链接URL
            
        Returns:
            如果是视频链接返回True，否则返回False
        """
        if not url:
            return False
        
        url_lower = url.lower()
        
        # B站视频链接
        if 'bilibili.com' in url_lower and '/video/' in url_lower:
            return True
        
        # YouTube视频链接
        if ('youtube.com' in url_lower and '/watch' in url_lower) or \
           ('youtu.be' in url_lower):
            return True
        
        # 其他视频平台（可以根据需要扩展）
        video_patterns = [
            '/video/',
            '/v/',
            'watch?v=',
            'v=',
            '.mp4',
            '.avi',
            '.mov',
            '.flv'
        ]
        
        for pattern in video_patterns:
            if pattern in url_lower:
                return True
        
        return False
    
    def _build_search_url(self, base_url: str, search_params: dict) -> str:
        """
        构建搜索URL（拼接参数）
        
        Args:
            base_url: 基础URL
            search_params: 参数字典
            
        Returns:
            完整的搜索URL
        """
        from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
        
        # 解析基础URL
        parsed = urlparse(base_url)
        query_dict = parse_qs(parsed.query)
        
        # 合并搜索参数
        for key, value in search_params.items():
            query_dict[key] = [str(value)]
        
        # 重新构建URL
        new_query = urlencode(query_dict, doseq=True)
        new_parsed = parsed._replace(query=new_query)
        
        return urlunparse(new_parsed)
    
    def trigger_collection(self, source_id: Optional[int] = None):
        """
        手动触发采集（同步方法，保留以供其他地方调用）
        注意：在FastAPI的异步上下文中，应直接使用 collect_source 或 collect_all_sources
        
        此方法已废弃，建议直接使用异步方法 collect_source 或 collect_all_sources
        
        Args:
            source_id: 源ID，如果为None则采集所有启用的源
        """
        logger.warning("trigger_collection 方法已废弃，请使用异步方法 collect_source 或 collect_all_sources")
        raise NotImplementedError("此方法已废弃，请使用异步方法 collect_source 或 collect_all_sources")


# 全局调度器实例
_scheduler: Optional[CollectionScheduler] = None


def setup_scheduler() -> CollectionScheduler:
    """
    设置并启动调度器（单例模式）
    
    Returns:
        调度器实例
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = CollectionScheduler()
        _scheduler.start()
    
    return _scheduler


def get_scheduler() -> Optional[CollectionScheduler]:
    """
    获取调度器实例
    
    Returns:
        调度器实例
    """
    return _scheduler