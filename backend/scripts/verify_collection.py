"""
验证采集结果
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import get_db, File, CollectionSource, CollectionLog


def verify_collection():
    """验证采集结果"""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 检查文件记录
        files = db.query(File).all()
        print(f"采集的文件数量: {len(files)}")
        print()
        
        for file in files:
            print(f"文件ID: {file.id}")
            print(f"标题: {file.title}")
            print(f"来源ID: {file.source_id}")
            print(f"文件路径: {file.file_path}")
            print(f"文件哈希: {file.file_hash[:20] if file.file_hash else 'None'}...")
            tags = json.loads(file.tags) if file.tags else []
            print(f"标签: {tags}")
            print(f"摘要: {file.summary[:50] if file.summary else 'None'}...")
            print()
        
        # 检查采集日志
        logs = db.query(CollectionLog).order_by(CollectionLog.executed_at.desc()).limit(5).all()
        print(f"最近的采集日志数量: {len(logs)}")
        print()
        
        for log in logs:
            print(f"日志ID: {log.id}")
            print(f"来源ID: {log.source_id}")
            print(f"URL: {log.url}")
            print(f"状态: {log.status}")
            if log.error_message:
                print(f"错误: {log.error_message[:100]}")
            print(f"执行时间: {log.executed_at}")
            print()
        
        # 检查文件是否存在
        if files:
            file = files[0]
            from app.config import settings
            collections_dir = Path(settings.collections_dir)
            file_path = collections_dir / file.file_path
            
            print(f"检查文件是否存在: {file_path}")
            if file_path.exists():
                file_size = file_path.stat().st_size
                content_preview = file_path.read_text(encoding='utf-8', errors='ignore')[:200]
                print(f"[成功] 文件存在，大小: {file_size} 字节")
                print(f"内容预览（前200字符）:")
                print(content_preview)
            else:
                print(f"[失败] 文件不存在: {file_path}")
    
    finally:
        db.close()


if __name__ == "__main__":
    verify_collection()
