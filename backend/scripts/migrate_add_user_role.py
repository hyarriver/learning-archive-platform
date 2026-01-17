"""
数据库迁移脚本：添加用户角色字段
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from sqlalchemy import create_engine, text


def migrate_add_user_role():
    """添加用户角色字段"""
    
    # 创建数据库连接
    engine = create_engine(settings.database_url, echo=True)
    
    try:
        with engine.connect() as conn:
            # 检查字段是否已存在
            cursor = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'role' not in columns:
                # 添加 role 字段，默认为 'user'
                conn.execute(text("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user' NOT NULL"))
                conn.commit()
                print("[OK] 已添加 role 字段到 users 表")
                
                # 将第一个用户设置为管理员（如果存在）
                result = conn.execute(text("SELECT id FROM users LIMIT 1"))
                first_user = result.fetchone()
                if first_user:
                    conn.execute(text("UPDATE users SET role = 'admin' WHERE id = :id"), {"id": first_user[0]})
                    conn.commit()
                    print(f"[OK] 已将用户 ID {first_user[0]} 设置为管理员")
            else:
                print("[INFO] role 字段已存在，跳过迁移")
        
        print(f"数据库迁移完成！数据库文件位置: {settings.database_url}")
    
    except Exception as e:
        print(f"[ERROR] 迁移失败: {str(e)}")
        raise


if __name__ == "__main__":
    migrate_add_user_role()
