"""
认证工具模块
"""
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import User


def _prehash_password(password: str) -> bytes:
    """
    对密码进行预哈希（SHA-256 + base64），以绕过 bcrypt 72 字节限制
    
    Args:
        password: 原始密码字符串
        
    Returns:
        预哈希后的密码字节串（固定长度，适合 bcrypt）
    """
    # 使用 SHA-256 哈希密码，然后 base64 编码
    # 这样无论原始密码多长，传给 bcrypt 的都是固定长度的字符串（44字节）
    sha256_digest = hashlib.sha256(password.encode('utf-8')).digest()
    prehashed = base64.b64encode(sha256_digest)  # 保持为 bytes
    return prehashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码（bcrypt格式）
        
    Returns:
        是否匹配
    """
    try:
        # 使用预哈希方案绕过 bcrypt 72 字节限制
        prehashed_password = _prehash_password(plain_password)
        # bcrypt.checkpw 接受 bytes 类型
        hashed_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        return bcrypt.checkpw(prehashed_password, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    
    Args:
        password: 明文密码（任意长度）
        
    Returns:
        哈希密码（bcrypt格式字符串）
    """
    # 使用预哈希方案绕过 bcrypt 72 字节限制
    # 先对密码进行 SHA-256 哈希，然后对哈希结果进行 bcrypt 哈希
    prehashed_password = _prehash_password(password)
    # bcrypt.gensalt() 生成盐，bcrypt.hashpw 进行哈希
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(prehashed_password, salt)
    return hashed.decode('utf-8')  # 转换为字符串存储


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        JWT令牌字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码JWT令牌
    
    Args:
        token: JWT令牌字符串
        
    Returns:
        解码后的数据，失败返回None
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    验证用户
    
    Args:
        db: 数据库会话
        username: 用户名
        password: 密码
        
    Returns:
        用户对象，验证失败返回None
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    根据ID获取用户
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        用户对象，不存在返回None
    """
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, username: str, password: str, role: str = "user") -> User:
    """
    创建新用户
    
    Args:
        db: 数据库会话
        username: 用户名
        password: 明文密码
        role: 用户角色，默认为 'user'
        
    Returns:
        创建的用户对象
        
    Raises:
        ValueError: 如果用户名已存在或角色无效
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise ValueError("用户名已存在")
    
    # 验证角色
    if role not in ["admin", "user"]:
        raise ValueError("角色必须是 'admin' 或 'user'")
    
    # 创建用户
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        role=role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user