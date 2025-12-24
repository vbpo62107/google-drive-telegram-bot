"""
动画效果模块
通过消息编辑实现类似动画的效果
提供加载动画、进度动画等视觉反馈
"""

import asyncio
from typing import Optional, List
from pyrogram.types import Message
from bot.ui_apple_style import AppleUI


class AnimationFrames:
    """动画帧定义"""
    
    # 加载动画（旋转效果）
    LOADING = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    # 点状加载
    DOTS = ["   ", ".  ", ".. ", "..."]
    
    # 进度条样式
    PROGRESS_EMPTY = "░"
    PROGRESS_FILLED = "█"
    
    # 箭头动画
    ARROWS = ["→", "↗", "↑", "↖", "←", "↙", "↓", "↘"]
    
    # 心跳动画
    HEARTBEAT = ["🤍", "🩶", "🩷", "❤️", "🩷", "🩶"]
    
    # 上传/下载动画
    UPLOAD = ["📤", "⬆️", "☁️", "✅"]
    DOWNLOAD = ["📥", "⬇️", "💾", "✅"]


class UIAnimation:
    """UI 动画控制器"""
    
    @staticmethod
    async def loading_animation(
        message: Message,
        text: str,
        duration: float = 3.0,
        frame_delay: float = 0.15
    ) -> None:
        """
        显示加载动画
        
        Args:
            message: 要编辑的消息对象
            text: 加载提示文本
            duration: 动画持续时间（秒）
            frame_delay: 帧间延迟（秒）
        """
        frames = AnimationFrames.LOADING
        end_time = asyncio.get_event_loop().time() + duration
        frame_index = 0
        
        while asyncio.get_event_loop().time() < end_time:
            try:
                frame = frames[frame_index % len(frames)]
                await message.edit_text(f"{frame} {text}")
                frame_index += 1
                await asyncio.sleep(frame_delay)
            except Exception:
                break
    
    @staticmethod
    async def dots_animation(
        message: Message,
        base_text: str,
        duration: float = 2.0
    ) -> None:
        """
        显示点状加载动画
        
        Args:
            message: 消息对象
            base_text: 基础文本
            duration: 持续时间
        """
        frames = AnimationFrames.DOTS
        end_time = asyncio.get_event_loop().time() + duration
        frame_index = 0
        
        while asyncio.get_event_loop().time() < end_time:
            try:
                dots = frames[frame_index % len(frames)]
                await message.edit_text(f"{base_text}{dots}")
                frame_index += 1
                await asyncio.sleep(0.4)
            except Exception:
                break
    
    @staticmethod
    async def progress_animation(
        message: Message,
        title: str,
        start: int = 0,
        end: int = 100,
        step: int = 5,
        delay: float = 0.3
    ) -> None:
        """
        显示进度条动画
        
        Args:
            message: 消息对象
            title: 标题
            start: 起始进度
            end: 结束进度
            step: 每步增量
            delay: 步间延迟
        """
        for progress in range(start, end + 1, step):
            bar_length = 10
            filled = int(progress / 10)
            bar = AnimationFrames.PROGRESS_FILLED * filled + \
                  AnimationFrames.PROGRESS_EMPTY * (bar_length - filled)
            
            text = AppleUI.format_message(
                title=title,
                icon=AppleUI.ICONS["processing"],
                content=f"{bar} {progress}%"
            )
            
            try:
                await message.edit_text(text)
                await asyncio.sleep(delay)
            except Exception:
                break
    
    @staticmethod
    async def countdown_animation(
        message: Message,
        title: str,
        seconds: int = 3
    ) -> None:
        """
        倒计时动画
        
        Args:
            message: 消息对象
            title: 标题
            seconds: 倒计时秒数
        """
        for i in range(seconds, 0, -1):
            text = AppleUI.format_message(
                title=title,
                icon="⏱",
                content=f"**{i}**"
            )
            
            try:
                await message.edit_text(text)
                await asyncio.sleep(1.0)
            except Exception:
                break
    
    @staticmethod
    async def typewriter_effect(
        message: Message,
        full_text: str,
        delay: float = 0.05
    ) -> None:
        """
        打字机效果（逐字显示）
        
        Args:
            message: 消息对象
            full_text: 完整文本
            delay: 每个字符的延迟
        """
        current_text = ""
        
        for char in full_text:
            current_text += char
            try:
                await message.edit_text(current_text)
                await asyncio.sleep(delay)
            except Exception:
                break
    
    @staticmethod
    async def pulse_animation(
        message: Message,
        texts: List[str],
        duration: float = 3.0,
        delay: float = 0.5
    ) -> None:
        """
        脉冲动画（文本循环显示）
        
        Args:
            message: 消息对象
            texts: 文本列表
            duration: 总持续时间
            delay: 切换延迟
        """
        end_time = asyncio.get_event_loop().time() + duration
        index = 0
        
        while asyncio.get_event_loop().time() < end_time:
            try:
                text = texts[index % len(texts)]
                await message.edit_text(text)
                index += 1
                await asyncio.sleep(delay)
            except Exception:
                break
    
    @staticmethod
    async def success_animation(
        message: Message,
        title: str,
        content: str
    ) -> None:
        """
        成功动画（从加载到成功）
        
        Args:
            message: 消息对象
            title: 标题
            content: 内容
        """
        # 阶段1：加载
        frames = ["⏳", "⌛", "⏳", "⌛"]
        for frame in frames:
            text = AppleUI.format_message(
                title="处理中",
                icon=frame,
                content="正在处理您的请求..."
            )
            try:
                await message.edit_text(text)
                await asyncio.sleep(0.3)
            except Exception:
                break
        
        # 阶段2：成功
        final_text = AppleUI.format_message(
            title=title,
            icon=AppleUI.ICONS["success"],
            content=content
        )
        
        try:
            await message.edit_text(final_text)
        except Exception:
            pass
    
    @staticmethod
    async def upload_animation(
        message: Message,
        filename: str,
        total_size: int
    ) -> None:
        """
        上传动画序列
        
        Args:
            message: 消息对象
            filename: 文件名
            total_size: 总大小（字节）
        """
        frames = AnimationFrames.UPLOAD
        stages = [
            ("准备上传", 0),
            ("正在上传", 50),
            ("同步中", 90),
            ("完成", 100)
        ]
        
        for i, (stage, progress) in enumerate(stages):
            icon = frames[i] if i < len(frames) else frames[-1]
            
            text = AppleUI.format_message(
                title=stage,
                icon=icon,
                content=(
                    f"**文件**: `{filename}`\n"
                    f"**进度**: {progress}%\n"
                    f"**大小**: {format_size(total_size)}"
                )
            )
            
            try:
                await message.edit_text(text)
                await asyncio.sleep(0.8)
            except Exception:
                break


class TransitionEffects:
    """页面过渡效果"""
    
    @staticmethod
    async def fade_transition(
        message: Message,
        old_text: str,
        new_text: str,
        steps: int = 3
    ) -> None:
        """
        淡入淡出过渡
        
        Args:
            message: 消息对象
            old_text: 旧文本
            new_text: 新文本
            steps: 过渡步数
        """
        # 淡出旧内容
        for _ in range(steps):
            try:
                await message.edit_text(old_text + "\n\n⋯")
                await asyncio.sleep(0.2)
            except Exception:
                break
        
        # 淡入新内容
        try:
            await message.edit_text(new_text)
        except Exception:
            pass
    
    @staticmethod
    async def slide_transition(
        message: Message,
        pages: List[str],
        direction: str = "forward"
    ) -> None:
        """
        滑动过渡效果（模拟页面切换）
        
        Args:
            message: 消息对象
            pages: 页面列表
            direction: 方向（forward/backward）
        """
        arrow = "→" if direction == "forward" else "←"
        
        for i, page in enumerate(pages):
            indicator = f"{arrow} 第 {i + 1}/{len(pages)} 页"
            full_text = f"{page}\n\n{indicator}"
            
            try:
                await message.edit_text(full_text)
                await asyncio.sleep(0.5)
            except Exception:
                break


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


# 便捷函数
async def show_loading(
    message: Message,
    text: str = "加载中",
    duration: float = 2.0
) -> None:
    """显示加载动画的快捷函数"""
    await UIAnimation.loading_animation(message, text, duration)


async def show_success(
    message: Message,
    title: str,
    content: str
) -> None:
    """显示成功动画的快捷函数"""
    await UIAnimation.success_animation(message, title, content)


async def show_progress(
    message: Message,
    title: str,
    end: int = 100
) -> None:
    """显示进度动画的快捷函数"""
    await UIAnimation.progress_animation(message, title, 0, end)
