"""
数据库迁移脚本：添加文件上传用户字段
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from sqlalchemy import create_engine, text


def migrate_add_upload_user():
    """添加文件上传用户字段"""
    
    # 创建数据库连接
    engine = create_engine(settings.database_url, echo=True)
    
    try:
        with engine.connect() as conn:
            # 检查字段是否已存在
            cursor = conn.execute(text("PRAGMA table_info(files)"))
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'upload_user_id' not in columns:
                # 添加 upload_user_id 字段
                conn.execute(text("ALTER TABLE files ADD COLUMN upload_user_id INTEGER"))
                conn.commit()
                print("[OK] 已添加 upload_user_id 字段到 files 表")
            else:
                print("[INFO] upload_user_id 字段已存在，跳过迁移")
        
        print(f"数据库迁移完成！数据库文件位置: {settings.database_url}")
    
    except Exception as e:
        print(f"[ERROR] 迁移失败: {str(e)}")
        raise


if __name__ == "__main__":
    migrate_add_upload_user()
