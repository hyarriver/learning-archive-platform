"""
标签提取器
"""
import re
from typing import List, Set
from collections import Counter

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TagExtractor:
    """标签提取器（基于关键词）"""
    
    def __init__(self):
        """初始化标签提取器"""
        # 中文停用词（简化版）
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '为', '可以', '这个', '那个', '还有', '或者', '但是', '如果',
            '因为', '所以', '这些', '那些', '它们', '他们', '我们', '你们', '这样', '那样',
            '什么', '怎么', '为什么', '如何', '以及', '然后', '同时', '此外', '而且',
            'this', 'that', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'and', 'or', 'but', 'if', 'because', 'so', 'when', 'where', 'what', 'how', 'why',
            'with', 'from', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'as', 'about'
        }
    
    def extract(self, markdown: str, title: str = None) -> List[str]:
        """
        提取标签（基于关键词/标题）
        
        Args:
            markdown: Markdown内容
            title: 标题（可选）
            
        Returns:
            标签列表（最多10个）
        """
        tags = set()
        
        # 从标题提取标签
        if title:
            title_tags = self._extract_from_title(title)
            tags.update(title_tags)
        
        # 从内容提取关键词
        content_tags = self._extract_keywords(markdown)
        tags.update(content_tags)
        
        # 转换为列表并限制数量
        tags_list = list(tags)[:10]
        
        return tags_list
    
    def _extract_from_title(self, title: str) -> Set[str]:
        """
        从标题提取标签
        
        Args:
            title: 标题文本
            
        Returns:
            标签集合
        """
        tags = set()
        
        # 提取标题中的关键词（中文和英文）
        # 中文：提取2-4字词组
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', title)
        for word in chinese_words:
            if word not in self.stop_words:
                tags.add(word)
        
        # 英文：提取单词（3字符以上）
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', title)
        for word in english_words:
            word_lower = word.lower()
            if word_lower not in self.stop_words:
                tags.add(word_lower)
        
        return tags
    
    def _extract_keywords(self, markdown: str, max_keywords: int = 8) -> Set[str]:
        """
        从内容提取关键词（高频词）
        
        Args:
            markdown: Markdown内容
            max_keywords: 最多提取的关键词数量
            
        Returns:
            标签集合
        """
        # 提取所有词
        words = []
        
        # 提取中文词组（2-4字）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', markdown)
        words.extend(chinese_words)
        
        # 提取英文单词（3字符以上）
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', markdown)
        words.extend([w.lower() for w in english_words])
        
        # 过滤停用词
        filtered_words = [w for w in words if w not in self.stop_words]
        
        # 统计词频
        word_counts = Counter(filtered_words)
        
        # 获取最常见的词作为标签
        most_common = word_counts.most_common(max_keywords)
        tags = {word for word, count in most_common if count >= 2}  # 至少出现2次
        
        return tags