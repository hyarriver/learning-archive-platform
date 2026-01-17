"""
视频字幕爬虫
"""
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from app.crawler.base import BaseCrawler
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class VideoCrawler(BaseCrawler):
    """视频字幕爬虫（使用 yt-dlp）"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化视频爬虫
        
        Args:
            config: 爬虫配置，可包含字幕语言等配置
        """
        super().__init__(config)
        self.subtitle_langs = self.config.get('subtitle_langs', ['zh', 'en', 'zh-Hans', 'zh-Hant'])
        self.write_auto_sub = self.config.get('write_auto_sub', True)
    
    def fetch(self, url: str) -> Optional[str]:
        """
        获取视频信息（不使用普通HTTP请求）
        
        Args:
            url: 视频URL
            
        Returns:
            视频信息JSON字符串
        """
        # yt-dlp 不使用 requests，直接返回 None，让 parse 方法处理
        return None
    
    def parse(self, content: str = None, url: str = None) -> Dict[str, Any]:
        """
        使用 yt-dlp 提取视频信息和字幕
        
        Args:
            content: 不使用
            url: 视频URL
            
        Returns:
            包含 title, content (字幕), metadata 的字典
        """
        if not url:
            raise ValueError("视频URL不能为空")
        
        try:
            # 使用 yt-dlp 提取信息
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': self.write_auto_sub,
                'subtitleslangs': self.subtitle_langs,
                'subtitlesformat': 'vtt',  # 使用 VTT 格式
            }
            
            import yt_dlp
            
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts['outtmpl'] = str(Path(tmpdir) / '%(title)s.%(ext)s')
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # 提取信息
                    info = ydl.extract_info(url, download=False)
                    
                    # 提取字幕
                    subtitles = self._extract_subtitles(info, tmpdir, ydl)
                    
                    # 构建结果
                    result = {
                        'title': info.get('title', '无标题视频'),
                        'content': subtitles,
                        'content_type': 'subtitle',
                        'metadata': {
                            'duration': info.get('duration'),
                            'uploader': info.get('uploader'),
                            'upload_date': info.get('upload_date'),
                            'view_count': info.get('view_count'),
                            'description': info.get('description', '')[:500],  # 限制长度
                            'thumbnail': info.get('thumbnail'),
                        }
                    }
                    
                    logger.info(f"成功提取视频信息: {url}, 标题: {result['title']}")
                    return result
                    
        except Exception as e:
            error_msg = f"提取视频信息失败: {url}, 错误: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _extract_subtitles(self, info: Dict, tmpdir: str, ydl) -> str:
        """
        提取并合并字幕
        
        Args:
            info: yt-dlp 提取的视频信息
            tmpdir: 临时目录
            ydl: YoutubeDL 实例
            
        Returns:
            合并后的字幕文本（Markdown格式）
        """
        subtitle_texts = []
        
        # 尝试获取自动生成的字幕
        subtitles = info.get('subtitles', {})
        automatic_captions = info.get('automatic_captions', {})
        
        # 合并字幕字典
        all_subtitles = {**subtitles, **automatic_captions}
        
        # 按优先级选择字幕语言
        selected_lang = None
        for lang in self.subtitle_langs:
            if lang in all_subtitles:
                selected_lang = lang
                break
        
        if not selected_lang:
            # 如果没有找到指定语言，使用第一个可用语言
            if all_subtitles:
                selected_lang = list(all_subtitles.keys())[0]
                logger.info(f"未找到指定语言字幕，使用: {selected_lang}")
            else:
                logger.warning("未找到任何字幕")
                return "无可用字幕"
        
        # 下载字幕
        subtitle_formats = all_subtitles[selected_lang]
        
        # 优先选择 vtt 格式
        subtitle_format = None
        for fmt in ['vtt', 'ttml', 'srv3', 'srv2', 'srv1']:
            if any(f.get('ext') == fmt for f in subtitle_formats):
                subtitle_format = fmt
                break
        
        if not subtitle_format:
            subtitle_format = subtitle_formats[0].get('ext')
        
        try:
            # 使用 yt-dlp 下载字幕到临时文件
            sub_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': self.write_auto_sub,
                'subtitleslangs': [selected_lang],
                'outtmpl': str(Path(tmpdir) / '%(title)s.%(ext)s'),
            }
            
            import yt_dlp
            with yt_dlp.YoutubeDL(sub_opts) as sub_ydl:
                sub_ydl.download([info.get('webpage_url') or info.get('url')])
            
            # 读取字幕文件
            subtitle_file = Path(tmpdir) / f"{info.get('title', 'subtitle')}.{selected_lang}.{subtitle_format}"
            
            if subtitle_file.exists():
                content = subtitle_file.read_text(encoding='utf-8')
                # 简单转换VTT为文本
                subtitle_text = self._vtt_to_text(content)
                subtitle_texts.append(subtitle_text)
        
        except Exception as e:
            logger.error(f"下载字幕失败: {e}")
        
        # 合并所有字幕文本
        merged_text = "\n\n".join(subtitle_texts)
        
        # 如果为空，返回提示
        if not merged_text.strip():
            return "无可用字幕内容"
        
        return merged_text
    
    def _vtt_to_text(self, vtt_content: str) -> str:
        """
        将VTT字幕转换为纯文本
        
        Args:
            vtt_content: VTT格式字幕内容
            
        Returns:
            纯文本内容
        """
        lines = vtt_content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # 跳过时间戳和标记
            if not line or line.startswith('WEBVTT') or '-->' in line:
                continue
            # 跳过样式标记
            if line.startswith('<') and line.endswith('>'):
                continue
            # 移除HTML标签
            import re
            line = re.sub(r'<[^>]+>', '', line)
            if line:
                text_lines.append(line)
        
        return '\n'.join(text_lines)
    
    def crawl(self, url: str) -> Optional[Dict[str, Any]]:
        """
        执行完整爬取流程（重写以适配视频爬虫）
        
        Args:
            url: 视频URL
            
        Returns:
            解析后的数据字典，失败返回None
        """
        try:
            logger.info(f"开始爬取视频: {url}")
            result = self.parse(url=url)
            result['url'] = url
            logger.info(f"视频爬取成功: {url}, 标题: {result.get('title', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"视频爬虫错误: {url}, {str(e)}")
            return None