"""
创建测试用户
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import get_db, User
from app.utils.auth import get_password_hash


def create_test_user():
    """创建测试用户"""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 检查是否已有用户
        existing_user = db.query(User).filter(User.username == "admin").first()
        
        if existing_user:
            print(f"用户已存在: {existing_user.username}")
            return existing_user
        
        # 创建新用户
        user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role="admin"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"已创建测试用户:")
        print(f"  用户名: {user.username}")
        print(f"  密码: admin123")
        print(f"  角色: {user.role}")
        
        return user
    
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()
