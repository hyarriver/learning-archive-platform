"""
搜索关于AI的知识文件并输出文本
"""
import sys
import json
import re
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database import get_db, File, CollectionSource
from app.storage import FileManager
from sqlalchemy import or_, text


def search_ai_files(db):
    """
    搜索关于AI的文件
    
    Args:
        db: 数据库会话
        
    Returns:
        匹配的文件列表
    """
    # 搜索关键词（AI相关）
    ai_keywords = ['AI', '人工智能', '机器学习', '深度学习', '神经网络', 'ChatGPT', 'GPT', 
                   'LLM', '大模型', '自然语言处理', 'NLP', '计算机视觉', 'CV', '强化学习']
    
    # 使用原生SQL查询，避免upload_user_id字段问题
    # 构建OR条件SQL
    base_condition = "files.source_id IS NOT NULL"
    or_conditions = []
    
    for keyword in ai_keywords:
        or_conditions.append(f"(files.title LIKE '%{keyword}%' OR files.tags LIKE '%{keyword}%')")
    
    where_clause = base_condition
    if or_conditions:
        where_clause += " AND (" + " OR ".join(or_conditions) + ")"
    
    sql = f"""
    SELECT id, title, source_id, file_path, file_hash, tags, summary, created_at, updated_at
    FROM files
    WHERE {where_clause}
    ORDER BY created_at DESC
    """
    
    result = db.execute(text(sql))
    rows = result.fetchall()
    
    # 转换为File对象（简化版，只使用需要的字段）
    files = []
    for row in rows:
        # 创建简化的文件对象
        file_obj = type('File', (), {
            'id': row[0],
            'title': row[1],
            'source_id': row[2],
            'file_path': row[3],
            'file_hash': row[4],
            'tags': row[5],
            'summary': row[6],
            'created_at': row[7],
            'updated_at': row[8],
            'upload_user_id': None  # 默认为None
        })()
        files.append(file_obj)
    
    return files


def read_file_content(file, file_manager):
    """
    读取文件内容
    
    Args:
        file: 文件对象
        file_manager: 文件管理器
        
    Returns:
        文件内容（文本）
    """
    try:
        # 只处理采集的文件（source_id不为空）
        # 采集的文件
        base_dir = file_manager.collections_dir
        relative_path = Path(file.file_path.replace('collections/', '')) if file.file_path.startswith('collections/') else Path(file.file_path)
        
        content = file_manager.read_file(relative_path, base_dir=base_dir)
        return content
    except Exception as e:
        print(f"读取文件失败: {file.title}, 错误: {e}")
        return None


def filter_ai_content(content, min_ai_mentions=3):
    """
    检查内容是否包含足够的AI相关内容
    
    Args:
        content: 文件内容
        min_ai_mentions: 最小AI关键词出现次数
        
    Returns:
        是否匹配
    """
    if not content:
        return False
    
    ai_keywords = ['AI', '人工智能', '机器学习', '深度学习', '神经网络', 'ChatGPT', 'GPT', 
                   'LLM', '大模型', '自然语言处理', 'NLP', '计算机视觉', 'CV', '强化学习',
                   'artificial intelligence', 'machine learning', 'deep learning', 'neural network']
    
    content_lower = content.lower()
    mention_count = 0
    
    for keyword in ai_keywords:
        # 不区分大小写匹配
        count = len(re.findall(re.escape(keyword.lower()), content_lower))
        mention_count += count
    
    return mention_count >= min_ai_mentions


def main():
    """主函数"""
    print("=" * 80)
    print("搜索关于AI的知识文件")
    print("=" * 80)
    print()
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 搜索文件
        print("正在搜索AI相关文件...")
        files = search_ai_files(db)
        print(f"找到 {len(files)} 个可能的文件")
        print()
        
        if not files:
            print("未找到AI相关的文件。")
            print("提示：文件标题或标签中包含AI相关关键词才会被找到。")
            return
        
        # 文件管理器
        file_manager = FileManager()
        
        # 过滤并输出文件
        ai_files = []
        for file in files:
            content = read_file_content(file, file_manager)
            
            # 进一步检查内容
            if content and filter_ai_content(content):
                ai_files.append((file, content))
        
        if not ai_files:
            print("未找到内容中包含足够AI相关信息的文件。")
            print("提示：文件内容中需要包含至少3次AI相关关键词。")
            return
        
        print(f"找到 {len(ai_files)} 个包含AI内容的文件：")
        print("=" * 80)
        print()
        
        # 输出所有文件内容
        for idx, (file, content) in enumerate(ai_files, 1):
            # 获取来源名称
            source_name = "未知来源"
            if file.source_id:
                source = db.query(CollectionSource).filter(CollectionSource.id == file.source_id).first()
                if source:
                    source_name = source.name
            
            # 获取标签
            tags = []
            if file.tags:
                try:
                    tags = json.loads(file.tags)
                except:
                    pass
            
            print(f"[文件 {idx}/{len(ai_files)}]")
            print(f"标题: {file.title}")
            print(f"来源: {source_name}")
            print(f"标签: {', '.join(tags) if tags else '无'}")
            print(f"创建时间: {file.created_at.strftime('%Y-%m-%d %H:%M:%S') if file.created_at else '未知'}")
            print(f"文件路径: {file.file_path}")
            print("-" * 80)
            print("内容:")
            print(content)
            print()
            print("=" * 80)
            print()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
