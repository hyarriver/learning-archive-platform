"""
初始化数据库
创建必要的表结构
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from sqlalchemy import create_engine, text


def init_database():
    """初始化数据库表结构"""
    
    # 创建数据库连接
    engine = create_engine(settings.database_url, echo=True)
    
    # SQL语句
    sql_statements = [
        # 用户表
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        """,
        
        # 采集源配置表
        """
        CREATE TABLE IF NOT EXISTS collection_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url_pattern TEXT NOT NULL,
            source_type TEXT NOT NULL,
            crawler_config TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        );
        """,
        
        # 文件索引表
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source_id INTEGER,
            file_path TEXT NOT NULL,
            file_hash TEXT,
            tags TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES collection_sources(id)
        );
        """,
        
        # 采集日志表
        """
        CREATE TABLE IF NOT EXISTS collection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            file_id INTEGER,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES collection_sources(id),
            FOREIGN KEY (file_id) REFERENCES files(id)
        );
        """,
        
        # 文件版本表
        """
        CREATE TABLE IF NOT EXISTS file_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            content_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id),
            UNIQUE(file_id, version_number)
        );
        """,
        
        # 创建索引（分开执行，SQLite不支持一次执行多个语句）
        "CREATE INDEX IF NOT EXISTS idx_files_source_id ON files(source_id);",
        "CREATE INDEX IF NOT EXISTS idx_files_file_hash ON files(file_hash);",
        "CREATE INDEX IF NOT EXISTS idx_collection_logs_source_id ON collection_logs(source_id);",
        "CREATE INDEX IF NOT EXISTS idx_collection_logs_status ON collection_logs(status);",
        "CREATE INDEX IF NOT EXISTS idx_file_versions_file_id ON file_versions(file_id);",
    ]
    
    with engine.connect() as conn:
        for sql in sql_statements:
            conn.execute(text(sql))
        conn.commit()
    
    print("数据库初始化完成！")
    print(f"数据库文件位置: {settings.database_url}")


if __name__ == "__main__":
    init_database()
