"""ytdl 清晰度选择器"""
import logging
from typing import Optional, List
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

LOGGER = logging.getLogger(__name__)


class QualityOption:
    def __init__(self, format_id: str, format_name: str, resolution: str, 
                 ext: str, fps: int = 0, bitrate: Optional[str] = None):
        self.format_id = format_id
        self.format_name = format_name
        self.resolution = resolution
        self.ext = ext
        self.fps = fps
        self.bitrate = bitrate


class YtDlpQualitySelector:
    @staticmethod
    def extract_formats(info: dict) -> List[QualityOption]:
        """从 yt-dlp 信息中提取清晰度选项"""
        formats = info.get('formats', [])
        LOGGER.info("extract_formats called with %d total formats", len(formats))
        quality_map = {}
        
        for fmt in formats:
            if not fmt.get('vcodec') or fmt.get('vcodec') == 'none':
                continue
            
            height = fmt.get('height')
            if not height:
                continue
            
            quality_name = f"{height}p"
            fps = fmt.get('fps', 30)
            if fps and fps > 30:
                quality_name += f" {int(fps)}fps"
            
            ext = fmt.get('ext', 'mp4')
            bitrate = fmt.get('tbr')
            
            if quality_name in quality_map:
                existing = quality_map[quality_name]
                if bitrate and existing.bitrate:
                    try:
                        if float(bitrate) <= float(existing.bitrate):
                            continue
                    except (ValueError, TypeError):
                        continue
            
            quality_map[quality_name] = QualityOption(
                format_id=fmt.get('format_id'),
                format_name=quality_name,
                resolution=f"{fmt.get('width', '?')}x{height}",
                ext=ext,
                fps=int(fps) if fps else 0,
                bitrate=str(bitrate) if bitrate else None
            )
        
        sorted_qualities = sorted(
            quality_map.values(),
            key=lambda x: int(x.resolution.split('x')[1]),
            reverse=True
        )

        LOGGER.info("Returning %d quality options", len(sorted_qualities[:8]))

        return sorted_qualities[:8]
    
    @staticmethod
    async def show_quality_selector(
        client: Client,
        message: Message,
        info: dict,
        video_title: str
    ) -> Optional[Message]:
        """显示清晰度选择界面"""
        LOGGER.info("show_quality_selector called with title: %s", video_title)
        qualities = YtDlpQualitySelector.extract_formats(info)
        LOGGER.info("Extracted %d qualities from video", len(qualities))
        
        if not qualities:
            return await client.send_message(
                message.chat.id,
                "❌ **未找到可用的清晰度**\n该视频可能受到限制。",
                reply_to_message_id=message.id
            )
        
        buttons = []
        for i, quality in enumerate(qualities):
            if i % 2 == 0:
                buttons.append([])
            
            btn_text = f"📹 {quality.format_name}"
            if quality.bitrate:
                try:
                    btn_text += f" ({int(float(quality.bitrate))}k)"
                except:
                    pass
            
            buttons[-1].append(
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"ytdl_select_{quality.format_id}"
                )
            )
        
        buttons.append([
            InlineKeyboardButton(
                text="🎵 最佳音质（仅音频）",
                callback_data="ytdl_select_audio"
            )
        ])
        
        buttons = buttons[:5]
        
        text = (
            f"🎬 **{video_title[:50]}**\n\n"
            f"请选择下载清晰度：\n\n"
            f"找到 {len(qualities)} 种清晰度"
        )
        
        return await client.send_message(
            message.chat.id,
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            reply_to_message_id=message.id
        )
