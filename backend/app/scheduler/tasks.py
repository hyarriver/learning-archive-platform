"""
定时任务调度
"""
import json
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
    
    async def collect_source(self, db: Session, source: CollectionSource):
        """
        采集单个源
        
        Args:
            db: 数据库会话
            source: 采集源对象
        """
        logger.info(f"开始采集源: {source.name}")
        
        try:
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
                return
            
            # 解析URL模式（简化版：直接使用URL模式作为URL）
            # 实际应用中可能需要更复杂的URL模式匹配和链接发现
            url = source.url_pattern
            
            # 执行爬取
            result = crawler.crawl(url)
            
            if not result:
                # 记录失败日志
                log = CollectionLog(
                    source_id=source.id,
                    url=url,
                    status='failed',
                    error_message='爬取失败，未返回结果'
                )
                db.add(log)
                db.commit()
                logger.warning(f"采集失败: {source.name}, URL: {url}")
                return
            
            # 转换为Markdown
            content_html = result.get('content', '')
            title = result.get('title', '无标题')
            
            if source.source_type == 'webpage':
                # HTML转Markdown
                markdown_content = self.markdown_converter.convert(content_html, title=title)
            else:
                # 视频字幕已经是文本，直接格式化
                markdown_content = f"# {title}\n\n{content_html}"
            
            # 生成TOC
            markdown_content = self.toc_generator.generate(markdown_content)
            
            # 提取标签和摘要
            tags = self.tag_extractor.extract(markdown_content, title=title)
            summary = self.summary_generator.generate(markdown_content, title=title)
            
            # 计算内容哈希
            content_hash = calculate_file_hash(markdown_content)
            
            # 检查是否已存在相同内容的文件（去重）
            existing_file = db.query(File).filter(
                File.source_id == source.id,
                File.file_hash == content_hash
            ).first()
            
            if existing_file:
                # 文件已存在，创建新版本（如果内容有变化）
                logger.info(f"文件已存在，检查版本: {source.name}, 标题: {title}")
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
                
                return
            
            # 保存文件
            date = datetime.now()
            file_path = self.file_manager.save_collection(
                source_name=source.name,
                title=title,
                content=markdown_content,
                date=date
            )
            
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
            
        except Exception as e:
            logger.exception(f"采集源异常: {source.name}, 错误: {str(e)}")
            
            # 记录失败日志
            log = CollectionLog(
                source_id=source.id,
                url=source.url_pattern,
                status='failed',
                error_message=str(e)
            )
            db.add(log)
            db.commit()
    
    def trigger_collection(self, source_id: Optional[int] = None):
        """
        手动触发采集（同步方法，供API调用）
        
        Args:
            source_id: 源ID，如果为None则采集所有启用的源
        """
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            if source_id:
                # 采集指定源
                source = db.query(CollectionSource).filter(
                    CollectionSource.id == source_id,
                    CollectionSource.enabled == True
                ).first()
                
                if source:
                    import asyncio
                    asyncio.run(self.collect_source(db, source))
                else:
                    logger.warning(f"采集源不存在或未启用: {source_id}")
            else:
                # 采集所有启用的源
                import asyncio
                asyncio.run(self.collect_all_sources())
        
        except Exception as e:
            logger.exception(f"手动触发采集异常: {str(e)}")
            raise
        finally:
            db.close()


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