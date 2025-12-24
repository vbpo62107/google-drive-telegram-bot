# 🤖 AI Agent Guide - Google Drive Telegram Bot

**Apple Design Edition v2.0** - 简洁、直观、高效

---

## 🎯 快速开始

### 项目核心

```python
仓库: vbpo62107/google-drive-telegram-bot
技术栈: Python 3.x + Pyrogram + Google Drive API
入口: bot/__main__.py
UI 框架: Apple 设计语言 (bot/ui_apple_style.py)
```

### 关键原则

✅ **始终使用 AppleUI** - 所有界面必须统一风格  
✅ **用户友好错误** - 使用预设错误模板  
✅ **确认关键操作** - 重要操作需二次确认  
✅ **保持一致性** - 遵循现有设计模式

---

## 📖 核心组件

### 1. Apple UI 系统

**必须使用** `bot/ui_apple_style.py`

```python
from bot.ui_apple_style import AppleUI

# 消息格式化
text = AppleUI.format_message(
    title="标题",
    icon=AppleUI.ICONS["success"],
    content="内容"
)

# 创建按钮
keyboard = AppleUI.create_keyboard([
    [AppleUI.create_button("执行", "action", icon="▶️")]
])

# 错误处理
error = AppleUI.create_error_message("auth_failed")
```

**图标系统** (35+ 图标)
```python
AppleUI.ICONS = {
    "success": "✅", "error": "❌", "warning": "⚠️",
    "upload": "📤", "download": "📥", "gdrive": "📦",
    "play": "▶️", "pause": "⏸", "cancel": "✕",
    # ... 查看 APPLE_UI_GUIDE.md 获取完整列表
}
```

**错误模板** (6 种)
- `auth_failed` - 认证失败
- `network_error` - 网络错误
- `permission_denied` - 权限不足
- `invalid_input` - 输入无效
- `file_not_found` - 文件不存在
- `unknown_error` - 未知错误

---

### 2. 配置系统

**文件**: `bot/__init__.py` + `bot/config.py`

```python
# 环境变量（必选）
BOT_TOKEN, APP_ID, API_HASH
DATABASE_URL, SUDO_USERS
G_DRIVE_CLIENT_ID, G_DRIVE_CLIENT_SECRET

# 命令定义
BotCommands.CommandName = "command_name"

# 用户文案（中文）
Messages.MESSAGE_NAME = "消息内容"
```

⚠️ **禁止**: 在代码中硬编码中文文案，必须使用 `Messages` 类

---

### 3. 权限系统

```python
from bot import SUDO_USERS
from bot.helpers.utils import CustomFilters

# 检查 SUDO 权限
if message.from_user.id not in SUDO_USERS:
    error = AppleUI.create_error_message("permission_denied")
    await message.reply_text(...)
    return

# Drive 授权检查
@Client.on_message(filters.command(["cmd"]) & CustomFilters.auth_users)
```

---

### 4. Mirror 任务系统

**文件**: `bot/modules/task_manager.py`

```python
from bot.modules.task_manager import task_manager
from bot.helpers.sql_helper.mirror_tasks import MirrorTask

# 创建任务
runner = await task_manager.submit(
    client, user_id, chat_id, url, filename
)

# 控制任务
await task_manager.pause(client, task_id)
await task_manager.resume(client, task_id)
await task_manager.cancel(client, task_id)
```

**回调按钮格式**: `mirror:{task_id}:{pause|resume|cancel}`

---

### 5. Google Drive 系统

**文件**: `bot/modules/drive_helper.py`

```python
from bot.modules.drive_helper import get_drive_instance
from bot.helpers.gdrive_utils.credentials_manager import credential_manager

# 获取 Drive 实例
drive = get_drive_instance(user_id)

# 支持两种模式
# - oauth: 用户授权
# - service_account: 服务账户
```

⚠️ **禁止**: 直接创建 Drive 客户端，必须使用 `get_drive_instance`

---

## 🛠️ 开发流程

### 添加新命令

**1. 定义命令** (`bot/config.py`)
```python
class BotCommands:
    MyCommand = "mycommand"

class Messages:
    MY_COMMAND_HELP = "命令说明"
    MY_COMMAND_SUCCESS = "操作成功"
```

**2. 创建处理器** (`bot/plugins/my_plugin.py`)
```python
from bot.ui_apple_style import AppleUI
from pyrogram import Client, filters

@Client.on_message(filters.command(["mycommand"]))
async def my_command_handler(client, message):
    # 1. 验证权限
    if message.from_user.id not in SUDO_USERS:
        error = AppleUI.create_error_message("permission_denied")
        await message.reply_text(...)
        return
    
    # 2. 验证输入
    if not valid_input:
        error = AppleUI.create_error_message("invalid_input")
        await message.reply_text(...)
        return
    
    # 3. 执行逻辑
    try:
        result = await perform_action()
        
        # 4. 显示成功
        success = AppleUI.create_success_message(
            title="操作成功",
            message=Messages.MY_COMMAND_SUCCESS
        )
        text = AppleUI.format_message(
            title=success["title"],
            content=success["message"]
        )
        await message.reply_text(text)
        
    except Exception as e:
        # 5. 错误处理
        error = AppleUI.create_error_message(
            "unknown_error",
            str(e)
        )
        await message.reply_text(...)
```

**3. 添加交互** (可选)
```python
# 创建确认对话框
text = AppleUI.format_message(
    title="确认操作",
    icon=AppleUI.ICONS["warning"],
    content="确定要执行此操作吗？"
)

keyboard = AppleUI.create_keyboard([
    [
        AppleUI.create_button(
            "确认",
            callback_data="confirm_action",
            icon=AppleUI.ICONS["success"]
        ),
        AppleUI.create_button(
            "取消",
            callback_data="cancel_action",
            icon=AppleUI.ICONS["cancel"]
        )
    ]
])

await message.reply_text(text, reply_markup=keyboard)

# 处理回调
@Client.on_callback_query(filters.regex(r"^confirm_action$"))
async def confirm_callback(client, callback_query):
    # 执行确认后的操作
    pass
```

---

## 🎨 设计规范

### 消息结构

```
🎉 **标题**             # 粗体 + 图标
  ↓
__副标题__              # 斜体
  ↓
内容段落               # 常规文本
• 列表项 1
• 列表项 2
  ↓
💡 页脚提示           # 辅助信息
```

### 按钮布局

```python
# ✅ 推荐：主操作在第一行
AppleUI.create_keyboard([
    [AppleUI.create_button("主操作", "main")],        # 独立
    [
        AppleUI.create_button("辅助操作1", "aux1"),
        AppleUI.create_button("辅助操作2", "aux2")
    ],
    [AppleUI.create_button("取消", "cancel")]       # 最后
])

# ❌ 避免：每行超过 2 个按钮
```

### 进度显示

```python
# 使用内置方法
text = AppleUI.format_progress(
    current=50*1024*1024,
    total=100*1024*1024,
    status="uploading",
    filename="file.zip",
    speed="2.5 MB/s"
)

# 输出
⬆️ 正在上传

file.zip

█████░░░░░ 50.0%

50.0 MB / 100.0 MB • 2.5 MB/s
```

---

## ⚠️ 重要约束

### 必须遵守

❌ **禁止硬编码中文** - 使用 `Messages` 类  
❌ **禁止直接创建 Drive 实例** - 使用 `get_drive_instance`  
❌ **禁止绕过权限检查** - 始终验证 `SUDO_USERS`  
❌ **禁止忽略限制** - 尊重 `MAX_MIRROR_FILE_SIZE` 等

### 必须使用

✅ **AppleUI 工具类** - 所有界面  
✅ **错误模板** - 所有错误处理  
✅ **task_manager** - Mirror 任务  
✅ **CustomFilters** - 权限检查

---

## 📚 快速参考

### 常用导入

```python
# Apple UI
from bot.ui_apple_style import AppleUI

# 权限
from bot import SUDO_USERS
from bot.helpers.utils import CustomFilters

# 配置
from bot.config import BotCommands, Messages

# Mirror
from bot.modules.task_manager import task_manager
from bot.helpers.sql_helper.mirror_tasks import MirrorTask

# Drive
from bot.modules.drive_helper import get_drive_instance
from bot.helpers.gdrive_utils.credentials_manager import credential_manager

# Pyrogram
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
```

### 常用模式

```python
# 1. 权限检查
if user_id not in SUDO_USERS:
    error = AppleUI.create_error_message("permission_denied")
    # ...

# 2. 输入验证
if not valid:
    error = AppleUI.create_error_message("invalid_input", "详细原因")
    # ...

# 3. 确认对话
text = AppleUI.format_message(title="确认操作", ...)
keyboard = [[confirm_btn, cancel_btn]]

# 4. 进度显示
if progress % 5 == 0:  # 每 5% 更新
    text = AppleUI.format_progress(...)
    await message.edit_text(text)

# 5. 成功/失败
try:
    result = await action()
    success = AppleUI.create_success_message(...)
except Exception as e:
    error = AppleUI.create_error_message("unknown_error", str(e))
```

---

## 🔗 文档链接

**必读文档**:
- [APPLE_UI_GUIDE.md](./APPLE_UI_GUIDE.md) - AppleUI API 参考
- [APPLE_UI_PHASE2.md](./APPLE_UI_PHASE2.md) - 交互增强示例
- [APPLE_UI_COMPLETE.md](./APPLE_UI_COMPLETE.md) - 完整项目总结

**代码示例**:
- [welcome_apple.py](./bot/plugins/welcome_apple.py) - 欢迎和帮助系统
- [mirror_apple.py](./bot/plugins/mirror_apple.py) - Mirror 任务管理
- [auth_apple.py](./bot/plugins/auth_apple.py) - 授权流程

---

## ✨ 代码风格

### Python 规范

```python
# ✅ 使用类型注解
async def my_function(client: Client, message: Message) -> None:
    pass

# ✅ 添加文档字符串
def create_message(title: str, content: str) -> str:
    """
    创建格式化消息
    
    Args:
        title: 消息标题
        content: 消息内容
        
    Returns:
        格式化的消息文本
    """
    pass

# ✅ 使用有意义的变量名
user_id = message.from_user.id  # ✅
uid = message.from_user.id      # ❌

# ✅ 遵循 PEP 8
# - 4 空格缩进
# - 行宽不超过 100 字符
# - 函数/方法间空 2 行
```

### 异常处理

```python
# ✅ 推荐：具体异常类型
try:
    result = await perform_action()
except PermissionError:
    error = AppleUI.create_error_message("permission_denied")
except ConnectionError:
    error = AppleUI.create_error_message("network_error")
except Exception as e:
    LOGGER.exception("Unexpected error")
    error = AppleUI.create_error_message("unknown_error", str(e))

# ❌ 避免：空捕获
try:
    result = await perform_action()
except:
    pass  # 禁止
```

---

## 🐛 调试提示

### 日志记录

```python
from bot import LOGGER

# 信息
LOGGER.info("User %s triggered command %s", user_id, command)

# 警告
LOGGER.warning("Rate limit approached for user %s", user_id)

# 错误
LOGGER.error("Failed to process task %s: %s", task_id, error)

# 异常（带栈跟踪）
LOGGER.exception("Unexpected error in handler")
```

### 测试方法

```bash
# 启动 Bot
python3 -m bot

# 测试命令
/start          # 欢迎页面
/help           # 帮助系统
/mirror_apple   # Mirror 功能
/auth_apple     # 授权流程
```

---

## 🎓 最佳实践

### 十条黄金法则

1. **始终使用 AppleUI** - 保持界面一致性
2. **验证所有输入** - 防止意外错误
3. **检查用户权限** - 保障安全性
4. **使用错误模板** - 提供友好提示
5. **重要操作确认** - 防止误操作
6. **记录关键事件** - 便于调试追踪
7. **复用现有组件** - 避免重复开发
8. **遵循命名约定** - 提高可读性
9. **添加类型注解** - 减少错误
10. **编写文档字符串** - 方便维护

---

## 🚀 快速检測清单

在提交代码前，确保：

- [ ] 使用了 `AppleUI` 工具类
- [ ] 所有文案存在 `Messages` 中
- [ ] 添加了权限检查
- [ ] 输入验证完善
- [ ] 错误处理友好
- [ ] 重要操作有确认
- [ ] 添加了日志记录
- [ ] 遵循 PEP 8 规范
- [ ] 添加了类型注解
- [ ] 编写了文档字符串

---

## 🎁 总结

**Apple 设计版本的核心理念**：

🎨 **简洁** - 去除不必要的复杂性  
👁️ **直观** - 用户无需学习即可使用  
⚡ **高效** - 减少操作步骤，提升响应速度  
❤️ **友好** - 以用户为中心，提供关怀体验

**开发者请始终记住**：  
“用户不关心你用了什么技术，他们只关心是否好用。”

---

**文档版本**: v2.0.0  
**最后更新**: 2025-12-24  
**设计语言**: Apple Human Interface Guidelines  
**License**: GPL-3.0
