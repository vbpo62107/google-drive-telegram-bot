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
        LOGGER.debug("Starting format extraction from info dict")
        
        formats = info.get('formats', [])
        LOGGER.info("Total available formats from yt-dlp: %d", len(formats))
        
        quality_map = {}
        video_formats_count = 0
        skipped_formats = 0
        
        for fmt in formats:
            # 检查是否有视频编码
            vcodec = fmt.get('vcodec')
            if not vcodec or vcodec == 'none':
                LOGGER.debug(
                    "Skipping format (no video codec): format_id=%s, vcodec=%s",
                    fmt.get('format_id'),
                    vcodec
                )
                skipped_formats += 1
                continue
            
            # 检查分辨率
            height = fmt.get('height')
            if not height:
                LOGGER.debug(
                    "Skipping format (no height): format_id=%s, width=%s",
                    fmt.get('format_id'),
                    fmt.get('width')
                )
                skipped_formats += 1
                continue
            
            video_formats_count += 1
            
            # 构建清晰度名称
            quality_name = f"{height}p"
            fps = fmt.get('fps', 30)
            if fps and fps > 30:
                quality_name += f" {int(fps)}fps"
            
            ext = fmt.get('ext', 'mp4')
            bitrate = fmt.get('tbr')
            
            LOGGER.debug(
                "Processing video format: format_id=%s, quality=%s, resolution=%sx%s, fps=%d, bitrate=%s, ext=%s",
                fmt.get('format_id'),
                quality_name,
                fmt.get('width'),
                height,
                fps,
                bitrate,
                ext
            )
            
            # 检查是否已存在相同清晰度，选择更好的
            if quality_name in quality_map:
                existing = quality_map[quality_name]
                LOGGER.debug(
                    "Duplicate quality level detected: quality=%s, new_bitrate=%s, existing_bitrate=%s",
                    quality_name,
                    bitrate,
                    existing.bitrate
                )
                if bitrate and existing.bitrate:
                    try:
                        new_bitrate = float(bitrate)
                        existing_bitrate = float(existing.bitrate)
                        if new_bitrate <= existing_bitrate:
                            LOGGER.debug(
                                "Keeping existing format for quality %s (higher bitrate: %s > %s)",
                                quality_name,
                                existing_bitrate,
                                new_bitrate
                            )
                            continue
                        LOGGER.debug(
                            "Replacing with new format for quality %s (higher bitrate: %s > %s)",
                            quality_name,
                            new_bitrate,
                            existing_bitrate
                        )
                    except (ValueError, TypeError) as e:
                        LOGGER.warning(
                            "Failed to compare bitrates: quality=%s, error=%s",
                            quality_name,
                            str(e)
                        )
                        continue
            
            quality_map[quality_name] = QualityOption(
                format_id=fmt.get('format_id'),
                format_name=quality_name,
                resolution=f"{fmt.get('width', '?')}x{height}",
                ext=ext,
                fps=int(fps) if fps else 0,
                bitrate=str(bitrate) if bitrate else None
            )
            LOGGER.debug(
                "Added quality option to map: quality=%s, format_id=%s",
                quality_name,
                fmt.get('format_id')
            )
        
        LOGGER.info(
            "Format extraction summary: video_formats=%d, duplicates_handled=%d, skipped=%d",
            video_formats_count,
            len(quality_map),
            skipped_formats
        )
        
        # 按分辨率排序
        sorted_qualities = sorted(
            quality_map.values(),
            key=lambda x: int(x.resolution.split('x')[1]),
            reverse=True
        )
        
        LOGGER.debug("Sorted qualities in descending order: %s", 
                    [q.format_name for q in sorted_qualities])
        
        # 限制为前8个
        result = sorted_qualities[:8]
        LOGGER.info(
            "Final quality options selected: count=%d, qualities=%s",
            len(result),
            [q.format_name for q in result]
        )
        
        return result
    
    @staticmethod
    async def show_quality_selector(
        client: Client,
        message: Message,
        info: dict,
        video_title: str
    ) -> Optional[Message]:
        """显示清晰度选择界面"""
        LOGGER.info(
            "Initiating quality selector display: user_id=%s, video_title=%s",
            message.from_user.id,
            video_title
        )
        
        try:
            qualities = YtDlpQualitySelector.extract_formats(info)
            
            if not qualities:
                LOGGER.warning(
                    "No available qualities found for video: user_id=%s, title=%s",
                    message.from_user.id,
                    video_title
                )
                return await client.send_message(
                    message.chat.id,
                    "❌ **未找到可用的清晰度**\n该视频可能受到限制。",
                    reply_to_message_id=message.id
                )
            
            # 构建清晰度按钮
            buttons = []
            for i, quality in enumerate(qualities):
                if i % 2 == 0:
                    buttons.append([])
                
                btn_text = f"📹 {quality.format_name}"
                if quality.bitrate:
                    try:
                        btn_text += f" ({int(float(quality.bitrate))}k)"
                        LOGGER.debug(
                            "Button label created: quality=%s, text=%s, bitrate=%s",
                            quality.format_name,
                            btn_text,
                            quality.bitrate
                        )
                    except (ValueError, TypeError) as e:
                        LOGGER.debug(
                            "Failed to parse bitrate for button label: quality=%s, bitrate=%s, error=%s",
                            quality.format_name,
                            quality.bitrate,
                            str(e)
                        )
                
                buttons[-1].append(
                    InlineKeyboardButton(
                        text=btn_text,
                        callback_data=f"ytdl_select_{quality.format_id}"
                    )
                )
                LOGGER.debug(
                    "Added quality button: format_id=%s, text=%s, index=%d",
                    quality.format_id,
                    btn_text,
                    i
                )
            
            # 添加音频按钮
            buttons.append([
                InlineKeyboardButton(
                    text="🎵 最佳音质（仅音频）",
                    callback_data="ytdl_select_audio"
                )
            ])
            LOGGER.debug("Added audio-only button")
            
            # 限制最多显示5行
            buttons = buttons[:5]
            LOGGER.info(
                "Quality selector buttons prepared: count=%d, button_rows=%d",
                sum(len(row) for row in buttons),
                len(buttons)
            )
            
            text = (
                f"🎬 **{video_title[:50]}**\n\n"
                f"请选择下载清晰度：\n\n"
                f"找到 {len(qualities)} 种清晰度"
            )
            
            LOGGER.info(
                "Sending quality selector message: user_id=%s, qualities_count=%d",
                message.from_user.id,
                len(qualities)
            )
            
            result = await client.send_message(
                message.chat.id,
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                reply_to_message_id=message.id
            )
            
            LOGGER.info(
                "Quality selector message sent successfully: user_id=%s, message_id=%s",
                message.from_user.id,
                result.id
            )
            
            return result
        
        except Exception as e:
            LOGGER.error(
                "Error in show_quality_selector: user_id=%s, video_title=%s, error=%s",
                message.from_user.id,
                video_title,
                str(e),
                exc_info=True
            )
            raise
