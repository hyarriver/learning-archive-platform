"""
创建用户脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal, User
from app.utils.auth import get_password_hash
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_user(username: str, password: str):
    """
    创建用户
    
    Args:
        username: 用户名
        password: 密码
    """
    db = SessionLocal()
    
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            logger.warning(f"用户已存在: {username}")
            print(f"错误: 用户 '{username}' 已存在")
            return
        
        # 创建用户
        user = User(
            username=username,
            password_hash=get_password_hash(password)
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"创建用户成功: {username}")
        print(f"成功: 用户 '{username}' 已创建")
        
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        print(f"错误: 创建用户失败 - {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python create_user.py <用户名> <密码>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    create_user(username, password)