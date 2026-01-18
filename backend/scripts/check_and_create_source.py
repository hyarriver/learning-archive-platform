"""
检查并创建测试采集源
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import get_db, CollectionSource
from sqlalchemy import text


def check_and_create_source():
    """检查并创建测试采集源"""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 检查是否有采集源
        sources = db.query(CollectionSource).all()
        
        print(f"当前采集源数量: {len(sources)}")
        print()
        
        if len(sources) == 0:
            print("未找到采集源，创建测试采集源...")
            
            # 创建一个简单的测试采集源（使用一个公开的技术博客）
            test_source = CollectionSource(
                name="测试技术博客",
                url_pattern="https://example.com/article",  # 使用一个示例URL
                source_type="webpage",
                crawler_config=None,
                enabled=True
            )
            
            db.add(test_source)
            db.commit()
            db.refresh(test_source)
            
            print(f"已创建测试采集源:")
            print(f"  ID: {test_source.id}")
            print(f"  名称: {test_source.name}")
            print(f"  URL: {test_source.url_pattern}")
            print(f"  类型: {test_source.source_type}")
        else:
            print("已有采集源:")
            for source in sources:
                print(f"  ID: {source.id}, 名称: {source.name}, URL: {source.url_pattern}, 启用: {source.enabled}")
    
    finally:
        db.close()


if __name__ == "__main__":
    check_and_create_source()
