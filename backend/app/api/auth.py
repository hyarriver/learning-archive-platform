"""
认证相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.api.dependencies import get_current_user
from app.utils.auth import authenticate_user, create_access_token
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Token(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """用户信息模型"""
    id: int
    username: str
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    Args:
        form_data: OAuth2密码表单
        db: 数据库会话
        
    Returns:
        Token对象
        
    Raises:
        HTTPException: 如果用户名或密码错误
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        logger.warning(f"登录失败: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    
    logger.info(f"用户登录成功: {user.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """
    获取当前用户信息
    
    Args:
        current_user: 当前登录用户（通过依赖注入）
        
    Returns:
        用户信息
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }