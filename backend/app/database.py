"""
数据库连接与模型定义
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # 'admin' 或 'user'
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class CollectionSource(Base):
    """采集源配置模型"""
    __tablename__ = "collection_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # 来源名称
    url_pattern = Column(Text, nullable=False)  # URL模式或搜索URL
    source_type = Column(String, nullable=False)  # 'webpage' / 'video'
    crawler_config = Column(Text, nullable=True)  # JSON配置
    search_params = Column(Text, nullable=True)  # 搜索参数 JSON格式，如 {"keyword": "Python", "page": "1"}
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # 关系
    files = relationship("File", back_populates="source")
    logs = relationship("CollectionLog", back_populates="source")


class File(Base):
    """文件索引模型"""
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source_id = Column(Integer, ForeignKey("collection_sources.id"), nullable=True)
    upload_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 上传用户ID
    file_path = Column(Text, nullable=False)  # 相对路径
    file_hash = Column(String, index=True, nullable=True)  # 文件哈希
    tags = Column(Text, nullable=True)  # JSON数组
    summary = Column(Text, nullable=True)  # 摘要
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # 关系
    source = relationship("CollectionSource", back_populates="files")
    upload_user = relationship("User", foreign_keys=[upload_user_id])  # 上传用户关系
    versions = relationship("FileVersion", back_populates="file")
    logs = relationship("CollectionLog", back_populates="file")


class CollectionLog(Base):
    """采集日志模型"""
    __tablename__ = "collection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("collection_sources.id"), nullable=True)
    url = Column(Text, nullable=False)
    status = Column(String, nullable=False, index=True)  # 'success' / 'failed' / 'skipped'
    error_message = Column(Text, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    source = relationship("CollectionSource", back_populates="logs")
    file = relationship("File", back_populates="logs")


class FileVersion(Base):
    """文件版本模型"""
    __tablename__ = "file_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_path = Column(Text, nullable=False)
    content_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    file = relationship("File", back_populates="versions")


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
