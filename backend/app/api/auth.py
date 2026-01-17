"""
认证相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.dependencies import get_current_user
from app.utils.auth import authenticate_user, create_access_token, create_user
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
    role: str
    created_at: str
    
    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    """注册请求模型"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


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


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    Args:
        register_data: 注册数据
        db: 数据库会话
        
    Returns:
        创建的用户信息
        
    Raises:
        HTTPException: 如果用户名已存在或数据验证失败
    """
    try:
        user = create_user(db, register_data.username, register_data.password, role="user")
        logger.info(f"新用户注册: {user.username}")
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except ValueError as e:
        logger.warning(f"注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


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
        "role": getattr(current_user, 'role', 'user'),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }