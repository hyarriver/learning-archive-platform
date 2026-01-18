"""
更新测试采集源为真实可访问的URL
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import get_db, CollectionSource


def update_test_source():
    """更新测试采集源"""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 获取第一个采集源
        source = db.query(CollectionSource).filter(
            CollectionSource.id == 1
        ).first()
        
        if not source:
            print("未找到采集源")
            return
        
        # 更新为一个真实可访问的URL（使用维基百科的一个AI相关页面作为测试）
        # 或者使用一个简单的公开博客
        test_url = "https://zh.wikipedia.org/wiki/人工智能"  # 维基百科页面
        
        source.url_pattern = test_url
        db.commit()
        
        print(f"已更新采集源:")
        print(f"  ID: {source.id}")
        print(f"  名称: {source.name}")
        print(f"  URL: {source.url_pattern}")
    
    finally:
        db.close()


if __name__ == "__main__":
    update_test_source()
