"""
修复数据库表结构，添加缺失的字段
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from sqlalchemy import create_engine, text, inspect


def fix_database():
    """修复数据库表结构"""
    
    engine = create_engine(settings.database_url, echo=True)
    
    # 检查表结构
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # 检查 files 表是否有 upload_user_id 字段
        columns = inspector.get_columns('files')
        column_names = [col['name'] for col in columns]
        
        print(f"当前 files 表的字段: {column_names}")
        print()
        
        # 如果缺少 upload_user_id，添加它
        if 'upload_user_id' not in column_names:
            print("添加缺失的 upload_user_id 字段...")
            conn.execute(text("""
                ALTER TABLE files 
                ADD COLUMN upload_user_id INTEGER REFERENCES users(id);
            """))
            conn.commit()
            print("已添加 upload_user_id 字段")
        else:
            print("upload_user_id 字段已存在")
        
        # 检查 users 表是否有 role 字段
        columns = inspector.get_columns('users')
        column_names = [col['name'] for col in columns]
        
        print(f"当前 users 表的字段: {column_names}")
        print()
        
        # 如果缺少 role，添加它
        if 'role' not in column_names:
            print("添加缺失的 role 字段...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN role TEXT DEFAULT 'user' NOT NULL;
            """))
            conn.commit()
            print("已添加 role 字段")
        else:
            print("role 字段已存在")
        
        print()
        print("数据库表结构修复完成！")


if __name__ == "__main__":
    fix_database()
