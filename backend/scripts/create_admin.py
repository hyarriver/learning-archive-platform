"""
创建管理员账户脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database import SessionLocal, User
from app.utils.auth import create_user, get_password_hash
from sqlalchemy.orm import Session


def create_admin_user():
    """创建管理员账户"""
    db: Session = SessionLocal()
    
    try:
        # 检查管理员是否已存在
        admin = db.query(User).filter(User.username == "admin").first()
        
        if admin:
            # 更新为管理员角色
            admin.role = "admin"
            admin.password_hash = get_password_hash("admin123")
            db.commit()
            print(f"[OK] 管理员账户已存在，已更新密码和角色")
            print(f"用户名: admin")
            print(f"密码: admin123")
            print(f"角色: {admin.role}")
        else:
            # 创建新管理员
            admin = create_user(db, "admin", "admin123", role="admin")
            print(f"[OK] 管理员账户创建成功")
            print(f"用户名: admin")
            print(f"密码: admin123")
            print(f"角色: {admin.role}")
    
    except Exception as e:
        print(f"[ERROR] 创建管理员失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
