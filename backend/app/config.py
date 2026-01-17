"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = Field(default="Learning Archive Platform", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # 数据库
    database_url: str = Field(default="sqlite:///./data/archive.db", alias="DATABASE_URL")
    
    # JWT配置
    jwt_secret_key: str = Field(default="change-me-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")  # 24小时
    
    # 文件存储
    data_dir: str = Field(default="./data", alias="DATA_DIR")
    collections_dir: str = Field(default="./data/collections", alias="COLLECTIONS_DIR")
    uploads_dir: str = Field(default="./data/uploads", alias="UPLOADS_DIR")
    
    # 任务调度
    scheduler_timezone: str = Field(default="Asia/Shanghai", alias="SCHEDULER_TIMEZONE")
    collection_schedule_hour: int = Field(default=0, alias="COLLECTION_SCHEDULE_HOUR")
    collection_schedule_minute: int = Field(default=0, alias="COLLECTION_SCHEDULE_MINUTE")
    
    # 爬虫配置
    crawler_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="CRAWLER_USER_AGENT"
    )
    crawler_request_delay: float = Field(default=1.0, alias="CRAWLER_REQUEST_DELAY")
    crawler_max_retries: int = Field(default=3, alias="CRAWLER_MAX_RETRIES")
    
    # 日志
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: str = Field(default="./logs", alias="LOG_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_data_dir(self) -> Path:
        """获取数据目录路径"""
        return Path(self.data_dir)
    
    def get_collections_dir(self) -> Path:
        """获取采集内容目录路径"""
        return Path(self.collections_dir)
    
    def get_uploads_dir(self) -> Path:
        """获取上传文件目录路径"""
        return Path(self.uploads_dir)
    
    def get_log_dir(self) -> Path:
        """获取日志目录路径"""
        return Path(self.log_dir)
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        self.get_data_dir().mkdir(parents=True, exist_ok=True)
        self.get_collections_dir().mkdir(parents=True, exist_ok=True)
        self.get_uploads_dir().mkdir(parents=True, exist_ok=True)
        self.get_log_dir().mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()

# 初始化时创建目录
settings.ensure_directories()
