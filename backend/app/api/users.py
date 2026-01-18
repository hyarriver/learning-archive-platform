"""
用户管理API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db, User, File
from app.api.dependencies import get_current_user, get_current_admin
from app.utils.auth import get_password_hash
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    password: str
    role: Optional[str] = "user"  # 'admin' 或 'user'


class UserUpdate(BaseModel):
    """用户更新模型"""
    role: Optional[str] = None  # 'admin' 或 'user'


class UserInfo(BaseModel):
    """用户信息模型"""
    id: int
    username: str
    role: str
    created_at: str
    last_login: Optional[str] = None
    file_count: Optional[int] = 0  # 用户上传的文件数量
    
    class Config:
        from_attributes = True


@router.post("/", response_model=UserInfo)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    创建新用户（仅管理员）
    
    Args:
        user_data: 用户数据
        db: 数据库会话
        current_admin: 当前管理员用户
        
    Returns:
        创建的用户信息
        
    Raises:
        HTTPException: 如果用户名已存在或角色无效
    """
    # 验证角色
    if user_data.role not in ['admin', 'user']:
        raise HTTPException(status_code=400, detail="角色必须是 'admin' 或 'user'")
    
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 统计用户文件数量
    file_count = db.query(File).filter(File.upload_user_id == user.id).count()
    
    logger.info(f"管理员 {current_admin.username} 创建用户: {user.username}, 角色: {user.role}")
    
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        file_count=file_count
    )


@router.get("/", response_model=List[UserInfo])
async def list_users(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    获取用户列表（仅管理员）
    
    Args:
        db: 数据库会话
        current_admin: 当前管理员用户
        
    Returns:
        用户列表
    """
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    result = []
    for user in users:
        # 统计每个用户的文件数量
        file_count = db.query(File).filter(File.upload_user_id == user.id).count()
        
        result.append(UserInfo(
            id=user.id,
            username=user.username,
            role=user.role,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None,
            file_count=file_count
        ))
    
    return result


@router.get("/{user_id}", response_model=UserInfo)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    获取用户详情（仅管理员）
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        current_admin: 当前管理员用户
        
    Returns:
        用户信息
        
    Raises:
        HTTPException: 如果用户不存在
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 统计用户文件数量
    file_count = db.query(File).filter(File.upload_user_id == user.id).count()
    
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        file_count=file_count
    )


@router.put("/{user_id}", response_model=UserInfo)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    更新用户信息（仅管理员，主要用于修改角色）
    
    Args:
        user_id: 用户ID
        user_update: 更新数据
        db: 数据库会话
        current_admin: 当前管理员用户
        
    Returns:
        更新后的用户信息
        
    Raises:
        HTTPException: 如果用户不存在或角色无效
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能修改自己的角色
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")
    
    # 更新角色
    if user_update.role is not None:
        if user_update.role not in ['admin', 'user']:
            raise HTTPException(status_code=400, detail="角色必须是 'admin' 或 'user'")
        user.role = user_update.role
        logger.info(f"管理员 {current_admin.username} 修改用户 {user.username} 角色为: {user.role}")
    
    db.commit()
    db.refresh(user)
    
    # 统计用户文件数量
    file_count = db.query(File).filter(File.upload_user_id == user.id).count()
    
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        file_count=file_count
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    删除用户（仅管理员）
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        current_admin: 当前管理员用户
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 如果用户不存在或不能删除自己
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能删除自己
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")
    
    username = user.username
    
    # 删除用户相关的文件（可选，这里保留文件但移除关联）
    # 或者可以选择级联删除文件
    db.query(File).filter(File.upload_user_id == user.id).update({"upload_user_id": None})
    
    # 删除用户
    db.delete(user)
    db.commit()
    
    logger.info(f"管理员 {current_admin.username} 删除用户: {username}")
    
    return {"message": "用户已删除"}