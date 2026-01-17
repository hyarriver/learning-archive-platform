"""
目录生成器
"""
import re
from typing import List, Dict

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TOCGenerator:
    """Markdown目录生成器"""
    
    def generate(self, markdown: str, min_level: int = 2, max_level: int = 4) -> str:
        """
        生成TOC并插入到文档开头
        
        Args:
            markdown: Markdown内容
            min_level: 最小标题级别（1-6）
            max_level: 最大标题级别（1-6）
            
        Returns:
            包含TOC的Markdown内容
        """
        headers = self._extract_headers(markdown, min_level, max_level)
        
        if not headers:
            # 如果没有找到标题，直接返回原内容
            return markdown
        
        toc = self._build_toc(headers)
        
        # 插入到第一个标题之前
        lines = markdown.split('\n')
        first_header_idx = None
        
        for i, line in enumerate(lines):
            if re.match(r'^#{1,6}\s+', line):
                first_header_idx = i
                break
        
        if first_header_idx is not None:
            # 在第一个标题前插入TOC
            lines.insert(first_header_idx, toc)
            lines.insert(first_header_idx, '')  # 空行
            return '\n'.join(lines)
        else:
            # 如果没找到标题，在开头插入
            return f"{toc}\n\n{markdown}"
    
    def _extract_headers(self, markdown: str, min_level: int, max_level: int) -> List[Dict]:
        """
        提取Markdown标题
        
        Args:
            markdown: Markdown内容
            min_level: 最小标题级别
            max_level: 最大标题级别
            
        Returns:
            标题列表，每个包含 level 和 text
        """
        pattern = r'^(#{1,6})\s+(.+)$'
        headers = []
        
        for line in markdown.split('\n'):
            match = re.match(pattern, line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                
                # 过滤级别范围
                if min_level <= level <= max_level:
                    # 生成锚点ID
                    anchor = self._generate_anchor(text)
                    headers.append({
                        'level': level,
                        'text': text,
                        'anchor': anchor
                    })
        
        return headers
    
    def _generate_anchor(self, text: str) -> str:
        """
        生成标题锚点ID
        
        Args:
            text: 标题文本
            
        Returns:
            锚点ID（小写，空格替换为连字符）
        """
        # 转换为小写
        anchor = text.lower()
        # 替换空格为连字符
        anchor = re.sub(r'\s+', '-', anchor)
        # 移除特殊字符
        anchor = re.sub(r'[^\w\-]', '', anchor)
        # 移除连续的连字符
        anchor = re.sub(r'-+', '-', anchor)
        # 移除首尾连字符
        anchor = anchor.strip('-')
        
        return anchor
    
    def _build_toc(self, headers: List[Dict]) -> str:
        """
        构建目录Markdown
        
        Args:
            headers: 标题列表
            
        Returns:
            目录Markdown字符串
        """
        toc_lines = ['## 目录']
        toc_lines.append('')
        
        for header in headers:
            indent = '  ' * (header['level'] - 2)  # 相对于h2的缩进
            link = f"[{header['text']}](#{header['anchor']})"
            toc_lines.append(f"{indent}- {link}")
        
        return '\n'.join(toc_lines)