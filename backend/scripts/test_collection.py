"""
测试采集功能
直接测试采集流程，定位问题
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import get_db, CollectionSource
from app.scheduler.tasks import CollectionScheduler
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_collection():
    """测试采集功能"""
    print("=" * 80)
    print("开始测试采集功能")
    print("=" * 80)
    print()
    
    # 获取数据库会话
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 获取第一个启用的采集源
        source = db.query(CollectionSource).filter(
            CollectionSource.enabled == True
        ).first()
        
        if not source:
            print("[错误] 未找到启用的采集源")
            print("请先创建采集源配置")
            return
        
        print(f"找到采集源:")
        print(f"  ID: {source.id}")
        print(f"  名称: {source.name}")
        print(f"  URL: {source.url_pattern}")
        print(f"  类型: {source.source_type}")
        print()
        
        # 创建调度器
        scheduler = CollectionScheduler()
        print("调度器已创建")
        print()
        
        # 执行采集
        print("开始采集...")
        print("-" * 80)
        try:
            await scheduler.collect_source(db, source)
            print("-" * 80)
            print("[成功] 采集完成（无异常）")
        except Exception as e:
            print("-" * 80)
            print(f"[失败] 采集失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_collection())
