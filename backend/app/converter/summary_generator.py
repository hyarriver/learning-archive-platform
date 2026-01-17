"""
摘要生成器
"""
import re
from typing import Optional

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SummaryGenerator:
    """摘要生成器"""
    
    def __init__(self, max_length: int = 200):
        """
        初始化摘要生成器
        
        Args:
            max_length: 摘要最大长度（字符数）
        """
        self.max_length = max_length
    
    def generate(self, markdown: str, title: str = None) -> str:
        """
        生成摘要
        
        Args:
            markdown: Markdown内容
            title: 标题（可选）
            
        Returns:
            摘要文本
        """
        # 策略1: 提取第一段非标题内容
        summary = self._extract_first_paragraph(markdown)
        
        # 策略2: 如果第一段太短，提取前几段
        if len(summary) < 50:
            summary = self._extract_first_paragraphs(markdown, num_paragraphs=3)
        
        # 策略3: 如果仍然太短，提取前N句
        if len(summary) < 50:
            summary = self._extract_first_sentences(markdown, num_sentences=3)
        
        # 清理摘要
        summary = self._clean_summary(summary)
        
        # 截断到最大长度
        if len(summary) > self.max_length:
            summary = summary[:self.max_length].rsplit('。', 1)[0] + '。'
            if not summary.endswith('。') and len(summary) < self.max_length - 10:
                summary += '...'
        
        return summary
    
    def _extract_first_paragraph(self, markdown: str) -> str:
        """
        提取第一段非标题内容
        
        Args:
            markdown: Markdown内容
            
        Returns:
            第一段文本
        """
        lines = markdown.split('\n')
        
        for line in lines:
            line = line.strip()
            # 跳过标题、列表、代码块等
            if (line and 
                not re.match(r'^#{1,6}\s+', line) and  # 不是标题
                not re.match(r'^[-*+]\s+', line) and  # 不是列表
                not re.match(r'^\d+\.\s+', line) and  # 不是有序列表
                not line.startswith('```') and  # 不是代码块
                not line.startswith('|') and  # 不是表格
                len(line) > 10):  # 长度合理
                return line
        
        return ""
    
    def _extract_first_paragraphs(self, markdown: str, num_paragraphs: int = 3) -> str:
        """
        提取前几段内容
        
        Args:
            markdown: Markdown内容
            num_paragraphs: 段落数量
            
        Returns:
            合并的段落文本
        """
        lines = markdown.split('\n')
        paragraphs = []
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    if len(paragraph_text) > 10:
                        paragraphs.append(paragraph_text)
                    current_paragraph = []
                    if len(paragraphs) >= num_paragraphs:
                        break
                continue
            
            # 跳过标题、列表、代码块等
            if (not re.match(r'^#{1,6}\s+', line) and
                not re.match(r'^[-*+]\s+', line) and
                not re.match(r'^\d+\.\s+', line) and
                not line.startswith('```') and
                not line.startswith('|')):
                current_paragraph.append(line)
        
        # 添加最后一段
        if current_paragraph and len(paragraphs) < num_paragraphs:
            paragraph_text = ' '.join(current_paragraph)
            if len(paragraph_text) > 10:
                paragraphs.append(paragraph_text)
        
        return ' '.join(paragraphs)
    
    def _extract_first_sentences(self, markdown: str, num_sentences: int = 3) -> str:
        """
        提取前N句
        
        Args:
            markdown: Markdown内容
            num_sentences: 句子数量
            
        Returns:
            合并的句子文本
        """
        # 移除Markdown标记，提取纯文本
        text = re.sub(r'#{1,6}\s+', '', markdown)  # 移除标题标记
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # 移除链接标记，保留文本
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)  # 移除粗体标记
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)  # 移除斜体标记
        text = re.sub(r'`([^`]+)`', r'\1', text)  # 移除代码标记
        text = re.sub(r'```[\s\S]*?```', '', text)  # 移除代码块
        
        # 按句子分割（中文句号、英文句号、问号、感叹号）
        sentences = re.split(r'[。！？.!?]\s*', text)
        
        # 过滤空句子和太短的句子
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        # 取前N句
        selected_sentences = valid_sentences[:num_sentences]
        
        return '。'.join(selected_sentences) + ('。' if selected_sentences else '')
    
    def _clean_summary(self, summary: str) -> str:
        """
        清理摘要文本
        
        Args:
            summary: 原始摘要
            
        Returns:
            清理后的摘要
        """
        # 移除多余空格
        summary = re.sub(r'\s+', ' ', summary)
        # 移除首尾空格
        summary = summary.strip()
        # 移除Markdown标记
        summary = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', summary)
        summary = re.sub(r'\*\*([^\*]+)\*\*', r'\1', summary)
        summary = re.sub(r'\*([^\*]+)\*', r'\1', summary)
        summary = re.sub(r'`([^`]+)`', r'\1', summary)
        
        return summary