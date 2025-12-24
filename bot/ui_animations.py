"""
Apple 风格动画效果模块
通过消息编辑模拟动画效果，提升用户体验
"""

import asyncio
from typing import List, Optional
from pyrogram.types import Message
from bot.ui_apple_style import AppleUI


class AnimationFrames:
    """预定义的动画帧集合"""
    
    # 加载动画帧
    LOADING = [
        "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"
    ]
    
    # 进度点动画
    DOTS = [
        ".", "..", "...", "....", "....."
    ]
    
    # 成功动画（逐渐显示）
    SUCCESS = [
        "○", "◔", "◑", "◕", "●", "✓", "✅"
    ]
    
    # 下载动画
    DOWNLOAD = [
        "⬇️ ", "⬇️ ▁", "⬇️ ▂", "⬇️ ▃", "⬇️ ▄", "⬇️ ▅", "⬇️ ▆", "⬇️ ▇", "⬇️ █"
    ]
    
    # 上传动画
    UPLOAD = [
        "⬆️ ", "⬆️ ▁", "⬆️ ▂", "⬆️ ▃", "⬆️ ▄", "⬆️ ▅", "⬆️ ▆", "⬆️ ▇", "⬆️ █"
    ]
    
    # 搜索动画
    SEARCH = [
        "🔍 .", "🔍 ..", "🔍 ...", "🔎 ...", "🔎 ..", "🔎 ."
    ]
    
    # 处理中动画
    PROCESSING = [
        "⚙️ ", "⚙️  ○", "⚙️  ◔", "⚙️  ◑", "⚙️  ◕", "⚙️  ●"
    ]


class UIAnimations:
    """UI 动画工具类"""
    
    @staticmethod
    async def loading_animation(
        message: Message,
        base_text: str,
        duration: float = 3.0,
        frames: List[str] = None
    ) -> None:
        """
        显示加载动画
        
        Args:
            message: 要编辑的消息对象
            base_text: 基础文本内容
            duration: 动画持续时间（秒）
            frames: 自定义动画帧
        """
        if frames is None:
            frames = AnimationFrames.LOADING
        
        iterations = int(duration / 0.3)  # 每帧 0.3 秒
        
        for i in range(iterations):
            frame = frames[i % len(frames)]
            try:
                await message.edit_text(f"{frame} {base_text}")
                await asyncio.sleep(0.3)
            except Exception:
                break
    
    @staticmethod
    async def dots_animation(
        message: Message,
        base_text: str,
        cycles: int = 3
    ) -> None:
        """
        点点点加载动画
        
        Args:
            message: 消息对象
            base_text: 基础文本
            cycles: 动画循环次数
        """
        for _ in range(cycles):
            for dots in AnimationFrames.DOTS:
                try:
                    await message.edit_text(f"{base_text}{dots}")
                    await asyncio.sleep(0.3)
                except Exception:
                    break
    
    @staticmethod
    async def success_reveal(
        message: Message,
        final_text: str,
        keyboard = None
    ) -> None:
        """
        成功揭示动画
        
        Args:
            message: 消息对象
            final_text: 最终显示的文本
            keyboard: 可选的键盘布局
        """
        for frame in AnimationFrames.SUCCESS:
            try:
                temp_text = f"{frame} 处理中..."
                await message.edit_text(temp_text)
                await asyncio.sleep(0.15)
            except Exception:
                break
        
        # 显示最终文本
        try:
            await message.edit_text(final_text, reply_markup=keyboard)
        except Exception:
            pass
    
    @staticmethod
    async def progress_bar_animation(
        message: Message,
        filename: str,
        total_steps: int = 10,
        status: str = "uploading"
    ) -> None:
        """
        进度条动画演示
        
        Args:
            message: 消息对象
            filename: 文件名
            total_steps: 总步数
            status: 状态类型
        """
        total_size = 100 * 1024 * 1024  # 100 MB 示例
        
        for step in range(total_steps + 1):
            percentage = (step / total_steps) * 100
            current_size = int(total_size * percentage / 100)
            
            text = AppleUI.format_progress(
                current=current_size,
                total=total_size,
                status=status,
                filename=filename,
                speed="2.5 MB/s" if step < total_steps else ""
            )
            
            try:
                await message.edit_text(text)
                await asyncio.sleep(0.5)
            except Exception:
                break
    
    @staticmethod
    async def typing_effect(
        message: Message,
        final_text: str,
        delay: float = 0.05
    ) -> None:
        """
        打字机效果（逐字显示）
        
        Args:
            message: 消息对象
            final_text: 最终文本
            delay: 每个字符的延迟
        """
        displayed = ""
        for char in final_text:
            displayed += char
            try:
                await message.edit_text(displayed + "▌")  # 光标效果
                await asyncio.sleep(delay)
            except Exception:
                break
        
        # 移除光标
        try:
            await message.edit_text(final_text)
        except Exception:
            pass
    
    @staticmethod
    async def fade_in(
        message: Message,
        lines: List[str],
        delay: float = 0.5
    ) -> None:
        """
        淡入效果（逐行显示）
        
        Args:
            message: 消息对象
            lines: 文本行列表
            delay: 每行延迟
        """
        displayed_lines = []
        
        for line in lines:
            displayed_lines.append(line)
            text = "\n".join(displayed_lines)
            try:
                await message.edit_text(text)
                await asyncio.sleep(delay)
            except Exception:
                break
    
    @staticmethod
    async def countdown(
        message: Message,
        base_text: str,
        seconds: int = 5
    ) -> None:
        """
        倒计时动画
        
        Args:
            message: 消息对象
            base_text: 基础文本
            seconds: 倒计时秒数
        """
        for i in range(seconds, 0, -1):
            text = f"{base_text}\n\n⏱ {i} 秒"
            try:
                await message.edit_text(text)
                await asyncio.sleep(1)
            except Exception:
                break
    
    @staticmethod
    async def status_transition(
        message: Message,
        from_status: str,
        to_status: str,
        duration: float = 1.5
    ) -> None:
        """
        状态转换动画
        
        Args:
            message: 消息对象
            from_status: 起始状态
            to_status: 目标状态
            duration: 过渡时间
        """
        # 淡出
        fade_frames = ["●", "◕", "◑", "◔", "○"]
        for frame in fade_frames:
            text = f"{frame} {from_status}"
            try:
                await message.edit_text(text)
                await asyncio.sleep(duration / len(fade_frames) / 2)
            except Exception:
                break
        
        # 淡入
        fade_frames.reverse()
        for frame in fade_frames:
            text = f"{frame} {to_status}"
            try:
                await message.edit_text(text)
                await asyncio.sleep(duration / len(fade_frames) / 2)
            except Exception:
                break


class ContextualHelp:
    """上下文相关的帮助提示"""
    
    # 帮助提示数据库
    TIPS = {
        "upload_start": [
            "💡 提示：您可以直接发送文件给我进行上传",
            "💡 提示：支持最大 2GB 的文件上传",
            "💡 提示：使用 /setfolder 可以更改默认上传文件夹"
        ],
        "auth_success": [
            "💡 提示：您的授权凭证已安全加密存储",
            "💡 提示：可以随时使用 /revoke 撤销授权",
            "💡 提示：授权后可以使用所有 Drive 功能"
        ],
        "mirror_complete": [
            "💡 提示：文件已保存到您的默认文件夹",
            "💡 提示：使用 /listdrive 可以查看所有文件",
            "💡 提示：支持批量镜像多个文件"
        ],
        "error_occurred": [
            "💡 提示：大多数错误可以通过重试解决",
            "💡 提示：检查您的网络连接状态",
            "💡 提示：加入支持群获取帮助"
        ]
    }
    
    @classmethod
    def get_tip(cls, context: str, index: int = 0) -> Optional[str]:
        """
        获取上下文相关的提示
        
        Args:
            context: 上下文类型
            index: 提示索引
            
        Returns:
            提示文本
        """
        tips = cls.TIPS.get(context, [])
        if tips and 0 <= index < len(tips):
            return tips[index]
        return None
    
    @classmethod
    def get_random_tip(cls, context: str) -> Optional[str]:
        """
        获取随机提示
        
        Args:
            context: 上下文类型
            
        Returns:
            随机提示文本
        """
        import random
        tips = cls.TIPS.get(context, [])
        return random.choice(tips) if tips else None


class SmartNotifications:
    """智能通知系统"""
    
    @staticmethod
    async def success_notification(
        message: Message,
        title: str,
        content: str,
        show_tip: bool = True,
        tip_context: str = None
    ) -> None:
        """
        显示成功通知（带动画）
        
        Args:
            message: 消息对象
            title: 通知标题
            content: 通知内容
            show_tip: 是否显示提示
            tip_context: 提示上下文
        """
        # 成功动画
        for frame in AnimationFrames.SUCCESS[-3:]:
            text = f"{frame} {title}"
            try:
                await message.edit_text(text)
                await asyncio.sleep(0.15)
            except Exception:
                break
        
        # 完整内容
        final_text = AppleUI.format_message(
            title=title,
            icon=AppleUI.ICONS["success"],
            content=content
        )
        
        # 添加提示
        if show_tip and tip_context:
            tip = ContextualHelp.get_random_tip(tip_context)
            if tip:
                final_text += f"\n\n{tip}"
        
        try:
            await message.edit_text(final_text)
        except Exception:
            pass
    
    @staticmethod
    async def error_notification(
        message: Message,
        error_type: str,
        custom_message: str = None,
        show_tip: bool = True
    ) -> None:
        """
        显示错误通知（带提示）
        
        Args:
            message: 消息对象
            error_type: 错误类型
            custom_message: 自定义消息
            show_tip: 是否显示提示
        """
        error = AppleUI.create_error_message(error_type, custom_message)
        
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        
        # 添加提示
        if show_tip:
            tip = ContextualHelp.get_random_tip("error_occurred")
            if tip:
                text += f"\n\n{tip}"
        
        try:
            await message.edit_text(text)
        except Exception:
            pass


# 便捷函数
async def show_loading(
    message: Message,
    text: str = "正在处理",
    duration: float = 2.0
) -> None:
    """显示加载动画的便捷函数"""
    await UIAnimations.loading_animation(message, text, duration)


async def show_success(
    message: Message,
    text: str,
    keyboard = None
) -> None:
    """显示成功消息的便捷函数"""
    await UIAnimations.success_reveal(message, text, keyboard)
