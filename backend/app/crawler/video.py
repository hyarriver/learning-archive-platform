"""
视频字幕爬虫（使用 subprocess 调用 yt-dlp 避免事件循环冲突）
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
        使用 yt-dlp 提取视频信息和字幕（使用 subprocess 避免事件循环冲突）
        
        Args:
            content: 不使用
            url: 视频URL
            
        Returns:
            包含 title, content (字幕), metadata 的字典
        """
        if not url:
            raise ValueError("视频URL不能为空")
        
        try:
            # 使用 subprocess 调用 yt-dlp 命令行工具，完全避免事件循环问题
            with tempfile.TemporaryDirectory() as tmpdir:
                import json
                
                # 构建 yt-dlp 命令参数
                output_template = str(Path(tmpdir) / '%(title)s.%(ext)s')
                
                # 首先提取视频信息（JSON格式）
                info_cmd = [
                    'yt-dlp',
                    '--quiet',
                    '--no-warnings',
                    '--skip-download',
                    '--dump-json',
                    '--write-sub',
                    '--write-auto-sub' if self.write_auto_sub else '--no-write-auto-sub',
                    '--sub-langs', ','.join(self.subtitle_langs),
                    '--sub-format', 'vtt',
                    '--output', output_template,
                    url
                ]
                
                try:
                    # 执行命令获取视频信息
                    result = subprocess.run(
                        info_cmd,
                        capture_output=True,
                        text=True,
                        timeout=120,  # 2分钟超时
                        check=True
                    )
                    
                    # 解析 JSON 输出
                    info = json.loads(result.stdout)
                    
                    # 获取视频 URL（优先使用 webpage_url，否则使用 url）
                    video_url = info.get('webpage_url') or info.get('url') or url
                    
                    # 构建视频信息 Markdown 内容（包含下载链接）
                    duration_str = self._format_duration(info.get('duration'))
                    upload_date_str = info.get('upload_date', '')
                    if upload_date_str and len(upload_date_str) == 8:
                        # 格式化日期：YYYYMMDD -> YYYY-MM-DD
                        upload_date_str = f"{upload_date_str[:4]}-{upload_date_str[4:6]}-{upload_date_str[6:8]}"
                    
                    video_info_content = f"""# {info.get('title', '无标题视频')}

## 视频信息

- **标题**: {info.get('title', '无标题视频')}
- **上传者**: {info.get('uploader', '未知')}
- **上传日期**: {upload_date_str or '未知'}
- **时长**: {duration_str or '未知'}
- **观看次数**: {info.get('view_count', 0):,} {'' if info.get('view_count') else '未知'}
- **视频链接**: [点击打开视频]({video_url})

## 视频描述

{info.get('description', '无描述')[:1000]}

---

**注意**: 此文件为视频链接，不支持在线预览。请使用下载功能或直接访问上述视频链接。
"""
                    
                    # 构建结果
                    parse_result = {
                        'title': info.get('title', '无标题视频'),
                        'content': video_info_content,
                        'content_type': 'video',
                        'video_url': video_url,
                        'metadata': {
                            'duration': info.get('duration'),
                            'uploader': info.get('uploader'),
                            'upload_date': info.get('upload_date'),
                            'view_count': info.get('view_count'),
                            'description': info.get('description', '')[:500],
                            'thumbnail': info.get('thumbnail'),
                            'webpage_url': info.get('webpage_url'),
                        }
                    }
                    
                    logger.info(f"成功提取视频信息: {url}, 标题: {parse_result['title']}")
                    return parse_result
                    
                except subprocess.CalledProcessError as e:
                    error_msg = f"yt-dlp 命令执行失败: {e.stderr if e.stderr else e.stdout}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                except json.JSONDecodeError as e:
                    error_msg = f"解析 yt-dlp 输出失败: {str(e)}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                except subprocess.TimeoutExpired:
                    error_msg = f"yt-dlp 执行超时: {url}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            error_msg = f"提取视频信息失败: {url}, 错误: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _find_subtitle_files(self, tmpdir: str, video_title: str) -> str:
        """
        查找并读取字幕文件（subprocess 方式）
        
        Args:
            tmpdir: 临时目录
            video_title: 视频标题
            
        Returns:
            字幕文本内容
        """
        subtitle_texts = []
        tmp_path = Path(tmpdir)
        
        # 查找所有 .vtt 文件
        vtt_files = list(tmp_path.glob("*.vtt"))
        
        # 按语言优先级排序
        for lang in self.subtitle_langs:
            for vtt_file in vtt_files:
                if lang in vtt_file.name or lang.replace('-', '') in vtt_file.name:
                    try:
                        content = vtt_file.read_text(encoding='utf-8')
                        subtitle_text = self._vtt_to_text(content)
                        subtitle_texts.append(subtitle_text)
                        break  # 找到第一个匹配的语言就退出
                    except Exception as e:
                        logger.warning(f"读取字幕文件失败: {vtt_file}, 错误: {e}")
                        continue
        
        # 如果没找到指定语言，使用第一个找到的文件
        if not subtitle_texts and vtt_files:
            try:
                content = vtt_files[0].read_text(encoding='utf-8')
                subtitle_text = self._vtt_to_text(content)
                subtitle_texts.append(subtitle_text)
            except Exception as e:
                logger.warning(f"读取字幕文件失败: {vtt_files[0]}, 错误: {e}")
        
        # 合并所有字幕文本
        merged_text = "\n\n".join(subtitle_texts)
        
        if not merged_text.strip():
            return "无可用字幕内容"
        
        return merged_text
    
    def _extract_subtitles_old(self, info: Dict, tmpdir: str, ydl) -> str:
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
    
    def _format_duration(self, seconds: Optional[int]) -> Optional[str]:
        """
        格式化视频时长（秒 -> HH:MM:SS 或 MM:SS）
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时长字符串
        """
        if not seconds:
            return None
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"