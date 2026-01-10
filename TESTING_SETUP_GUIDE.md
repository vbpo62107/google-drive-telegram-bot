# 🔧 v2.1 测试准备和执行指南

## 📋 文档信息

**版本：** v2.1 Alpha  
**创建日期：** 2026-01-10  
**目的：** 指导测试人员准备和执行测试

---

## 🎯 测试前准备清单

### ✅ 必需准备项

- [ ] Python 3.8+ 已安装
- [ ] Bot 依赖包已安装
- [ ] Google Drive API 已配置
- [ ] Telegram Bot Token 已获取
- [ ] 测试账号已创建
- [ ] 测试数据已准备
- [ ] 测试环境已验证

### ✅ 推荐准备项

- [ ] 阅读测试计划文档
- [ ] 准备测试记录表格
- [ ] 准备屏幕录制工具
- [ ] 创建测试专用Drive文件夹
- [ ] 准备各种测试文件

---

## 🚀 测试环境设置

### 步骤 1: 安装依赖

```bash
# 克隆项目（如果还没有）
git clone https://github.com/vbpo62107/google-drive-telegram-bot
cd google-drive-telegram-bot

# 安装Python依赖
pip3 install -r requirements.txt

# 验证安装
python3 -c "import pyrogram; print('Pyrogram OK')"
python3 -c "import google.auth; print('Google Auth OK')"
```

### 步骤 2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

**必需配置项：**
```bash
# Telegram Bot
BOT_TOKEN=your_bot_token_here
APP_ID=your_app_id
API_HASH=your_api_hash

# 授权用户（你的Telegram用户ID）
SUDO_USERS=123456789

# Google Drive API
G_DRIVE_CLIENT_ID=your_client_id
G_DRIVE_CLIENT_SECRET=your_client_secret

# 数据库
DATABASE_URL=postgresql://user:pass@localhost/dbname

# 支持群组
SUPPORT_CHAT_LINK=https://t.me/your_support_group
```

### 步骤 3: 启动Bot

```bash
# 启动Bot
python3 -m bot

# 看到以下输出表示成功：
# ✅ Bot started successfully
# ✅ AppleUI loaded
# ✅ 21 commands registered
```

### 步骤 4: 验证基础功能

在Telegram中测试基本命令：
```
/start     # 应该显示欢迎消息
/help      # 应该显示帮助信息
/auth      # 开始授权流程
```

---

## 📁 测试数据准备

### 创建测试文件夹结构

在你的Google Drive中创建以下结构：

```
📁 BotTest/
├── 📁 TestFolder1/
│   ├── 📄 document1.pdf (1MB)
│   ├── 📄 document2.docx (500KB)
│   └── 🖼️ image1.jpg (200KB)
├── 📁 TestFolder2/
│   ├── 📁 SubFolder1/
│   │   ├── 📄 file1.txt (10KB)
│   │   └── 📄 file2.txt (10KB)
│   └── 🎬 video1.mp4 (50MB)
├── 📁 EmptyFolder/
├── 📁 LargeFolder/ (包含30+个文件)
├── 📄 test_file.txt (1KB)
├── 📄 测试文件.txt (1KB) # 中文文件名
├── 📄 file with spaces.txt (1KB)
└── 📄 large_file.zip (100MB+)
```

### 测试文件准备脚本

创建 `prepare_test_data.py`：

```python
#!/usr/bin/env python3
"""准备测试数据的脚本"""

import os
import random
import string

def create_test_file(filename, size_kb):
    """创建指定大小的测试文件"""
    with open(filename, 'wb') as f:
        f.write(os.urandom(size_kb * 1024))
    print(f"✅ 创建文件: {filename} ({size_kb}KB)")

def create_text_file(filename, content):
    """创建文本文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 创建文件: {filename}")

def main():
    print("🔧 开始准备测试数据...\n")
    
    # 创建测试目录
    os.makedirs('test_data', exist_ok=True)
    os.chdir('test_data')
    
    # 小文件
    create_test_file('small_file.txt', 10)  # 10KB
    
    # 中等文件
    create_test_file('medium_file.pdf', 1024)  # 1MB
    
    # 大文件
    create_test_file('large_file.zip', 10240)  # 10MB
    
    # 特殊文件名
    create_text_file('测试文件.txt', '这是中文内容')
    create_text_file('file with spaces.txt', 'Content with spaces')
    create_text_file('file_with_@#$%.txt', 'Special chars in name')
    
    # 创建多个测试文件
    for i in range(1, 31):
        create_text_file(f'file_{i:02d}.txt', f'Test file number {i}')
    
    print("\n✅ 测试数据准备完成！")
    print(f"📁 位置: {os.getcwd()}")
    print("\n📤 请手动上传这些文件到你的Google Drive测试文件夹")

if __name__ == '__main__':
    main()
```

运行脚本：
```bash
python3 prepare_test_data.py
```

### 手动上传测试文件

1. 访问 [Google Drive](https://drive.google.com)
2. 创建 `BotTest` 文件夹
3. 上传 `test_data` 目录中的文件
4. 记录文件夹链接备用

---

## 📝 测试执行指南

### 测试流程

```mermaid
测试准备 → 执行测试 → 记录结果 → 报告问题 → 验证修复
```

### 单个命令测试流程

**以 `/searchdrive` 为例：**

1. **准备阶段**
   ```
   - 确认Bot在线
   - 确认已授权
   - 准备测试关键词
   ```

2. **执行测试**
   ```
   - 发送 /searchdrive test
   - 观察响应
   - 截图保存
   ```

3. **验证结果**
   ```
   - ✅ 响应时间 <3秒
   - ✅ 显示搜索结果
   - ✅ 文件信息完整
   - ✅ 图标显示正确
   ```

4. **记录结果**
   ```
   - 在测试表格中标记通过/失败
   - 如果失败，记录详细信息
   - 截图保存到指定目录
   ```

---

## 📊 测试记录表格

创建 `test_results.md` 文件记录测试结果：

```markdown
# 测试执行记录

## 测试信息
- 测试日期：2026-01-10
- 测试人员：Your Name
- Bot版本：v2.1 Alpha
- 环境：Production/Test

## /searchdrive 测试结果

| 用例ID | 测试项 | 状态 | 备注 |
|--------|--------|------|------|
| TC-SD-001 | 基本搜索 | ✅ | 响应正常 |
| TC-SD-002 | 快捷方式 | ✅ | /sd 工作 |
| TC-SD-003 | 中文搜索 | ✅ | 支持中文 |
| TC-SD-004 | 多关键词 | ❌ | 需要修复 |
| TC-SD-B001 | 空关键词 | ✅ | 错误提示OK |

## /list 测试结果

| 用例ID | 测试项 | 状态 | 备注 |
|--------|--------|------|------|
| TC-LS-001 | 列出根目录 | ⚪ | 待测试 |
| TC-LS-002 | 指定文件夹 | ⚪ | 待测试 |

...
```

---

## 🐛 Bug报告模板

当发现问题时，在GitHub Issues中使用此模板：

```markdown
## 🐛 Bug报告

### 基本信息
- **命令：** /searchdrive
- **测试用例：** TC-SD-004
- **发现日期：** 2026-01-10
- **严重程度：** 🔴 高 / 🟡 中 / 🟢 低

### 问题描述
简短描述问题是什么。

### 复现步骤
1. 发送 `/searchdrive test file 2024`
2. 等待响应
3. 观察结果

### 预期行为
应该显示包含所有关键词的文件（AND搜索）。

### 实际行为
只显示包含第一个关键词的文件。

### 截图
如果适用，添加截图帮助说明问题。

### 环境信息
- Bot版本：v2.1 Alpha
- Python版本：3.10.0
- 操作系统：Ubuntu 22.04

### 错误日志
```
[粘贴相关的错误日志]
```

### 可能的原因
如果知道，说明可能的原因。

### 建议的修复方案
如果有想法，提供建议。
```

---

## ✅ 快速测试检查清单

### 每日回归测试（5分钟）

```
□ /start - 欢迎消息正常
□ /help - 帮助信息正常
□ /searchdrive test - 搜索正常
□ /list - 列表显示正常
□ /copy file1 folder1 - 复制正常
□ /move file2 folder2 - 移动正常
```

### 完整功能测试（2小时）

**第1轮：基础功能**
```
□ 测试所有命令的基本用法
□ 测试所有快捷方式
□ 测试中文输入
□ 测试特殊字符
```

**第2轮：边界情况**
```
□ 空输入测试
□ 超长输入测试
□ 无效URL测试
□ 权限错误测试
```

**第3轮：工作流测试**
```
□ 搜索→复制工作流
□ 列表→移动工作流
□ 复制→验证工作流
□ 完整场景测试
```

---

## 🎯 测试最佳实践

### DO ✅

1. **详细记录**
   - 每个测试用例都记录结果
   - 失败用例记录详细信息
   - 保存截图作为证据

2. **系统性测试**
   - 按照测试计划顺序执行
   - 不要跳过任何测试用例
   - 完成一个再开始下一个

3. **环境一致性**
   - 使用相同的测试环境
   - 使用相同的测试数据
   - 记录环境配置

4. **及时报告**
   - 发现问题立即报告
   - 提供详细的复现步骤
   - 附带必要的日志和截图

### DON'T ❌

1. **不要随意测试**
   - 不要跳过测试用例
   - 不要改变测试数据
   - 不要在生产环境测试

2. **不要忽略小问题**
   - UI对齐问题也要报告
   - 拼写错误也要记录
   - 小bug可能导致大问题

3. **不要假设**
   - 不要假设某个功能会工作
   - 不要跳过边界测试
   - 每个用例都要验证

---

## 🔍 常见问题解决

### Q1: Bot无法启动

**问题：** 运行 `python3 -m bot` 时出错

**解决方案：**
```bash
# 1. 检查Python版本
python3 --version  # 应该 >=3.8

# 2. 重新安装依赖
pip3 install -r requirements.txt --upgrade

# 3. 检查环境变量
cat .env | grep BOT_TOKEN

# 4. 检查日志
tail -f bot.log
```

---

### Q2: 授权失败

**问题：** `/auth` 命令无法完成授权

**解决方案：**
```bash
# 1. 检查Google API配置
# 确保 G_DRIVE_CLIENT_ID 和 G_DRIVE_CLIENT_SECRET 正确

# 2. 检查回调URL
# 在Google Cloud Console中配置正确的回调URL

# 3. 清除旧的认证文件
rm -rf credentials/

# 4. 重新授权
/auth
```

---

### Q3: 命令无响应

**问题：** 发送命令后Bot没有响应

**解决方案：**
```bash
# 1. 检查Bot是否在线
# 在Telegram中查看Bot状态

# 2. 检查权限
# 确保你的User ID在SUDO_USERS中

# 3. 检查日志
tail -f bot.log

# 4. 重启Bot
pkill -f "python3 -m bot"
python3 -m bot
```

---

### Q4: 文件操作失败

**问题：** `/copy` 或 `/move` 命令失败

**解决方案：**
```bash
# 1. 检查URL格式
# 确保使用正确的Google Drive URL

# 2. 检查权限
# 确保对源文件和目标文件夹都有权限

# 3. 检查文件是否存在
# 在Drive中确认文件存在

# 4. 查看详细错误
# 检查Bot日志中的错误信息
```

---

### Q5: 性能问题

**问题：** 命令响应很慢

**解决方案：**
```bash
# 1. 检查网络连接
ping google.com

# 2. 检查系统资源
top
df -h

# 3. 检查Google API配额
# 访问Google Cloud Console查看API使用情况

# 4. 优化数据库连接
# 检查PostgreSQL性能
```

---

## 📚 参考资源

### 文档链接
- [测试计划](./TESTING_PLAN_v2.1.md)
- [命令参考](./COMMANDS_REFERENCE.md)
- [开发规范](./AGENTS.md)
- [功能路线图](./FEATURE_ROADMAP.md)

### 外部资源
- [Pyrogram文档](https://docs.pyrogram.org)
- [Google Drive API](https://developers.google.com/drive/api/v3/about-sdk)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

## 🎓 测试技巧

### 技巧1：使用测试脚本

创建一个测试辅助脚本 `quick_test.sh`：

```bash
#!/bin/bash
# 快速测试脚本

echo "🧪 开始快速测试..."

echo "\n1. 测试Bot是否在线"
curl -s https://api.telegram.org/bot$BOT_TOKEN/getMe | jq '.result.username'

echo "\n2. 测试数据库连接"
psql $DATABASE_URL -c "SELECT 1;"

echo "\n3. 测试Google Drive连接"
python3 -c "from bot.helpers.gdrive_utils.gDrive import GoogleDrive; print('Drive OK')"

echo "\n✅ 快速测试完成！"
```

### 技巧2：使用Telegram测试群组

创建一个专门的测试群组：
1. 创建私人群组
2. 添加Bot
3. 在群组中测试
4. 记录所有测试消息

### 技巧3：自动化截图

使用 `scrot` 或类似工具自动截图：
```bash
# 安装
sudo apt install scrot

# 使用
scrot -s test_screenshot_%Y%m%d_%H%M%S.png
```

---

## 📞 获取帮助

### 遇到问题？

1. **查看文档**
   - 先查看本指南的常见问题部分
   - 查看测试计划文档

2. **搜索Issues**
   - [GitHub Issues](https://github.com/vbpo62107/google-drive-telegram-bot/issues)
   - 可能已经有人报告了相同问题

3. **提交新Issue**
   - 使用Bug报告模板
   - 提供详细信息

4. **联系开发团队**
   - 通过Telegram支持群组
   - 发送邮件

---

## ✨ 下一步

准备工作完成后：

1. ✅ 阅读 [测试计划](./TESTING_PLAN_v2.1.md)
2. ✅ 准备测试环境
3. ✅ 准备测试数据
4. 🚀 开始执行测试！

---

**🎯 祝测试顺利！**

*文档版本：v1.0*  
*创建日期：2026-01-10*  
*最后更新：2026-01-10*
