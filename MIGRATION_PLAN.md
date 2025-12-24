# Apple UI 迁移计划

## 🎯 目标

根据 AGENTS.md 的要求，所有原始命令应该**自动使用 Apple 风格**，无需创建新命令。

## 📋 现状分析

### 已完成的文件

- ✅ `bot/ui_apple_style.py` - 核心 UI 工具库
- ✅ `bot/plugins/welcome_apple.py` - 欢迎和帮助系统（应重命名为 `welcome.py`）
- ✅ `bot/plugins/authorize.py` - 已更新为 Apple 风格

### 需要合并的文件

以下文件存在重复，需要将 Apple 风格版本合并到原始文件：

| 原始文件 | Apple 版本 | 操作 |
|----------|-----------|------|
| `help.py` | `welcome_apple.py` | 重命名 `welcome_apple.py` 为 `help.py` |
| `clone.py` | `file_operations_apple.py` | 合并功能 |
| `delete.py` | `file_operations_apple.py` | 合并功能 |
| `set_parent.py` | `file_operations_apple.py` | 合并功能 |
| - | `mirror_apple.py` | 保留（为增强版本） |
| - | `auth_apple.py` | 删除（已合并到 `authorize.py`） |
| - | `drive_manager_apple.py` | 保留（新功能） |
| - | `search_apple.py` | 保留（新功能） |
| - | `quick_actions_apple.py` | 更新 `quick_actions.py` |
| - | `settings_apple.py` | 保留（新功能） |
| - | `tasks_apple.py` | 保留（新功能） |

---

## 🛣️ 实施步骤

### 阶段 1：重命名核心文件

```bash
# 1. 备份原始 help.py
mv bot/plugins/help.py bot/plugins/help.py.bak

# 2. 将 welcome_apple.py 重命名为 help.py
mv bot/plugins/welcome_apple.py bot/plugins/help.py

# 3. 更新 help.py 中的命令注册
# 修改: @Client.on_message(filters.command(["start"]))
# 修改: @Client.on_message(filters.command(["help"]))
```

### 阶段 2：删除重复文件

```bash
# 删除已合并的 Apple 版本
rm bot/plugins/auth_apple.py
rm bot/plugins/authorize_apple.py  # 如果存在
```

### 阶段 3：更新文件操作命令

将 `clone.py`, `delete.py`, `set_parent.py` 更新为 Apple 风格：

```python
# 每个文件都需要：
# 1. 导入 AppleUI
from bot.ui_apple_style import AppleUI

# 2. 更新所有消息显示
text = AppleUI.format_message(
    title="标题",
    icon=AppleUI.ICONS["icon_name"],
    content="内容"
)

# 3. 更新按钮
keyboard = AppleUI.create_keyboard([...])

# 4. 更新错误处理
error = AppleUI.create_error_message("error_type")
```

---

## 📝 详细清单

### 优先级 1：核心命令（必须）

- [x] `/start` - 已完成 (`welcome_apple.py`)
- [x] `/help` - 已完成 (`welcome_apple.py`)
- [x] `/auth` - 已完成 (`authorize.py`)
- [x] `/revoke` - 已完成 (`authorize.py`)
- [ ] `/clone` - 需更新
- [ ] `/delete` - 需更新
- [ ] `/setparent` - 需更新

### 优先级 2：增强命令（已有 Apple 版本）

- [x] `/mirror_apple` - 保留为增强版
- [x] `/search_apple` - 保留为新功能
- [x] `/settings_apple` - 保留为新功能
- [x] `/tasks_apple` - 保留为新功能
- [x] `/quick` - 需更新

### 优先级 3：辅助命令

- [ ] `debug_commands.py` - 需更新
- [ ] `fallback_commands.py` - 需更新
- [x] `command_logger.py` - 保持原样（后台功能）
- [x] `auth_guard.py` - 保持原样（后台功能）
- [x] `modules_loader.py` - 保持原样（系统功能）

---

## 🛠️ 工具脚本

### 自动化转换脚本

```python
#!/usr/bin/env python3
"""
自动将命令文件转换为 Apple 风格
"""

import re
import sys
from pathlib import Path

def convert_to_apple_style(file_path):
    """转换单个文件为 Apple 风格"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 添加 AppleUI 导入
    if 'from bot.ui_apple_style import AppleUI' not in content:
        import_section = re.search(r'(from bot\.config import.*?)\n', content)
        if import_section:
            insert_pos = import_section.end()
            content = (
                content[:insert_pos] + 
                'from bot.ui_apple_style import AppleUI\n' +
                content[insert_pos:]
            )
    
    # 2. 替换简单的 reply_text
    # TODO: 这需要更复杂的逻辑
    
    # 3. 保存
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python convert.py <file_path>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)
    
    convert_to_apple_style(file_path)
    print(f"Converted: {file_path}")
```

---

## ✅ 验证清单

每个更新的文件都应该通过以下检查：

- [ ] 导入了 `AppleUI`
- [ ] 所有消息使用 `AppleUI.format_message`
- [ ] 所有按钮使用 `AppleUI.create_button`
- [ ] 错误使用 `AppleUI.create_error_message`
- [ ] 成功消息使用 `AppleUI.create_success_message`
- [ ] 进度显示使用 `AppleUI.format_progress`
- [ ] 重要操作有确认对话框
- [ ] 所有图标使用 `AppleUI.ICONS`
- [ ] 测试命令功能正常
- [ ] 测试所有回调按钮

---

## 📊 进度跟踪

### 当前状态

```
总计: 23 个文件
已完成: 4 个 (17%)
进行中: 0 个
待处理: 19 个 (83%)
```

### 下一步

1. 重命名 `welcome_apple.py` 为 `help.py`
2. 删除 `auth_apple.py`
3. 更新 `clone.py`
4. 更新 `delete.py`
5. 更新 `set_parent.py`

---

## 📚 参考文档

- [AGENTS.md](./AGENTS.md) - 开发规范
- [APPLE_UI_GUIDE.md](./APPLE_UI_GUIDE.md) - UI 工具指南
- [APPLE_UI_COMPLETE.md](./APPLE_UI_COMPLETE.md) - 完整项目总结

---

**最后更新**: 2025-12-25  
**状态**: 计划中
