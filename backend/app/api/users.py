"""
用户管理API
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db, User
from app.api.dependencies import get_current_user
from app.utils.auth import get_password_hash
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    password: str


class UserInfo(BaseModel):
    """用户信息模型"""
    id: int
    username: str
    created_at: str
    last_login: str = None
    
    class Config:
        from_attributes = True


@router.post("/", response_model=UserInfo)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    创建新用户（需要登录）
    
    Args:
        user_data: 用户数据
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        创建的用户信息
        
    Raises:
        HTTPException: 如果用户名已存在
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password)
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"创建用户: {user.username}")
    
    return UserInfo(
        id=user.id,
        username=user.username,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.get("/", response_model=List[UserInfo])
async def list_users(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取用户列表（需要登录）
    
    Args:
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        用户列表
    """
    users = db.query(User).all()
    
    return [
        UserInfo(
            id=user.id,
            username=user.username,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        for user in users
    ]