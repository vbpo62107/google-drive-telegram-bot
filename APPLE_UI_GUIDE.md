# Apple UI 设计指南

## 第一阶段：基础优化 ✅

本指南详细说明如何在 Google Drive Telegram Bot 中使用 Apple 设计语言风格的 UI 组件。

## 已完成的优化

### 1. 核心 UI 工具模块

**文件：** `bot/ui_apple_style.py`

该模块提供了一套完整的 Apple 风格 UI 工具：

#### 主要类：`AppleUI`

```python
from bot.ui_apple_style import AppleUI

# 图标系统
AppleUI.ICONS["upload"]    # 📤
AppleUI.ICONS["success"]   # ✅
AppleUI.ICONS["error"]     # ❌
# ... 更多图标
```

#### 消息格式化

```python
# 基本消息
text = AppleUI.format_message(
    title="标题",
    subtitle="副标题",
    content="内容主体",
    footer="页脚信息",
    icon="🎉"
)

# 成功消息
success = AppleUI.create_success_message(
    title="上传成功",
    message="文件已保存到 Google Drive",
    action="查看文件"
)

# 错误消息
error = AppleUI.create_error_message(
    error_type="auth_failed",
    custom_message="自定义错误信息"
)
```

#### 按钮创建

```python
# 单个按钮
button = AppleUI.create_button(
    text="上传文件",
    callback_data="upload_file",
    icon=AppleUI.ICONS["upload"]
)

# 键盘布局
keyboard = AppleUI.create_keyboard([
    [button1],  # 第一行
    [button2, button3],  # 第二行，两个按钮
])

# 或者自动分行
keyboard = AppleUI.create_keyboard(
    [button1, button2, button3, button4],
    row_width=2  # 每行 2 个按钮
)
```

#### 进度显示

```python
progress_text = AppleUI.format_progress(
    current=50 * 1024 * 1024,  # 50 MB
    total=100 * 1024 * 1024,   # 100 MB
    status="uploading",
    filename="document.pdf",
    speed="2.5 MB/s"
)
```

#### 列表格式化

```python
list_text = AppleUI.format_list(
    items=[
        "上传 Telegram 文件",
        "支持直链下载",
        "团队盘支持"
    ],
    title="主要功能",
    icon="•"
)
```

### 2. Apple 风格欢迎页面

**文件：** `bot/plugins/welcome_apple.py`

重构了 `/start` 和 `/help` 命令，提供：

- 简洁的欢迎界面
- 分页的帮助文档
- 交互式导航
- 快速开始指南

#### 功能亮点

1. **欢迎页面** (`/start`)
   - 个性化问候
   - 功能概览
   - 快捷操作按钮

2. **帮助系统** (`/help`)
   - 第 1 页：基本命令
   - 第 2 页：文件操作
   - 第 3 页：搜索与监控
   - 流畅的翻页体验

3. **交互回调**
   - `get_started` - 开始使用
   - `show_help` - 显示帮助
   - `show_about` - 关于页面
   - `back_home` - 返回主页
   - `auth_now` - 开始授权
   - `help_page_X` - 帮助页面翻页

## 如何在其他模块中使用

### 示例 1：重构一个命令处理器

```python
from pyrogram import Client, filters
from bot.ui_apple_style import AppleUI

@Client.on_message(filters.command(["mycommand"]))
async def my_command_handler(client, message):
    # 使用 Apple 风格消息
    text = AppleUI.format_message(
        title="功能名称",
        icon=AppleUI.ICONS["info"],
        content="这里是功能说明"
    )
    
    # 创建按钮
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "执行操作",
            callback_data="do_action",
            icon=AppleUI.ICONS["play"]
        )],
        [AppleUI.create_button(
            "取消",
            callback_data="cancel",
            icon=AppleUI.ICONS["cancel"]
        )]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)
```

### 示例 2：显示进度

```python
# 在上传/下载过程中更新进度
async def upload_with_progress(message, file_path, total_size):
    uploaded = 0
    
    while uploaded < total_size:
        # 上传逻辑...
        uploaded += chunk_size
        
        # 格式化进度消息
        progress_text = AppleUI.format_progress(
            current=uploaded,
            total=total_size,
            status="uploading",
            filename=os.path.basename(file_path),
            speed=calculate_speed()
        )
        
        # 更新消息
        await message.edit_text(progress_text)
```

### 示例 3：错误处理

```python
try:
    # 执行操作
    result = await perform_operation()
except AuthenticationError:
    # 使用标准化错误消息
    error = AppleUI.create_error_message("auth_failed")
    
    text = f"{error['title']}\n\n{error['message']}"
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            error['action'],
            callback_data="reauth",
            icon=AppleUI.ICONS["auth"]
        )]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)
except Exception as e:
    # 自定义错误消息
    error = AppleUI.create_error_message(
        "not_found",
        custom_message=str(e)
    )
    await message.reply_text(f"{error['title']}\n\n{error['message']}")
```

## 设计原则

### 1. 极简主义
- 减少视觉杂乱
- 突出核心功能
- 避免过多文本和按钮

### 2. 层级清晰
- 使用标题、副标题和内容分层
- 通过粗体、斜体建立视觉层次
- 适度的空白和间距

### 3. 一致性
- 所有按钮使用统一的图标系统
- 消息格式保持一致
- 交互模式可预测

### 4. 人性化
- 提供明确的反馈
- 错误提示友好且具体
- 带有解决方案的提示

## 图标系统

当前可用的图标（模拟 SF Symbols）：

| 类别 | 图标名 | Emoji |
|------|---------|-------|
| **功能** | upload | 📤 |
| | download | 📥 |
| | folder | 📁 |
| | file | 📄 |
| | settings | ⚙️ |
| | help | ❓ |
| | info | ℹ️ |
| **状态** | success | ✅ |
| | error | ❌ |
| | warning | ⚠️ |
| | processing | ⏳ |
| | completed | ✓ |
| **操作** | play | ▶️ |
| | pause | ⏸ |
| | stop | ⏹ |
| | cancel | ✕ |
| | refresh | 🔄 |
| | search | 🔍 |
| | delete | 🗑 |
| | copy | 📋 |
| **导航** | back | ◀️ |
| | forward | ▶️ |
| | home | 🏠 |
| | menu | ☰ |
| **Drive** | gdrive | ☁️ |
| | auth | 🔐 |
| | link | 🔗 |

## 错误消息模板

已预设的错误类型：

- `auth_failed` - 认证失败
- `file_too_large` - 文件过大
- `network_error` - 网络错误
- `invalid_input` - 无效输入
- `permission_denied` - 权限不足
- `not_found` - 未找到资源

## 测试

1. 启动 bot
2. 发送 `/start` 查看新的欢迎界面
3. 发送 `/help` 查看分页帮助系统
4. 点击各个按钮测试交互

## 下一步

第二阶段：交互增强（计划中）
- 添加动画效果
- 实现上下文相关的帮助提示
- 优化任务管理界面

## 贡献

如果您有更好的 UI 设计建议，欢迎提交 Issue 或 Pull Request！

## 许可证

本项目采用 GPL-3.0 许可证。
