# OpenAI Codex Agent for google-drive-telegram-bot

你是一个专门为此仓库工作的 AI 编程助手：`vbpo62107/google-drive-telegram-bot`。

## 技术栈与入口

- Python 3.x
- 使用 Pyrogram 的 Telegram 机器人
- 入口文件：`bot/__main__.py`：
  - 导入 `bot.modules.*` 中的所有模块。
  - 使用 `plugins = {"root": "bot/plugins"}` 配置插件。
  - 确保 `DOWNLOAD_DIRECTORY` 存在。
  - 在进程退出时清理 Drive 实例。

## 配置

- `bot/__init__.py` 加载环境变量（可选从 `.env` 读取）并校验必需字段：
  - BOT_TOKEN、APP_ID、API_HASH、DATABASE_URL、SUDO_USERS、SUPPORT_CHAT_LINK、
    G_DRIVE_CLIENT_ID、G_DRIVE_CLIENT_SECRET 等。
- 解析布尔值和数值限制（MAX_MIRROR_FILE_SIZE、MAX_CONCURRENT_MIRRORS、
  DRIVE_FAILURE_THRESHOLD、DRIVE_CIRCUIT_TIMEOUT）。
- 将 DEFAULT_AUTH_MODE 规范化为 `"oauth"` 或 `"service_account"`。
- 将 SUDO_USERS 转换为排好序的 int 列表，并要求至少有一个 ID。

## 命令与文案

- 命令名称和别名在 `bot/config.py` 中的 `BotCommands` 里定义。
- 所有用户可见文案使用中文，定义在 `bot/config.py` 中的 `Messages`。
- 如需新增用户可见文本，请添加到 `Messages`，不要在代码中直接硬编码中文字符串。

## 权限

- 高权限操作（镜像、下载、耗时的 Drive 操作）必须：
  - 检查 `SUDO_USERS`（只有 SUDO 用户可以触发）。
  - 当需要 Drive 授权时，使用 `CustomFilters.auth_users`。

## 镜像任务

- 长时间运行的镜像任务（下载 + 上传）使用：
  - SQLAlchemy 模型 `MirrorTask`（表名 `mirror_tasks`）。
  - `bot/modules/task_manager.py` 中的 `TaskManager` 与 `MirrorTaskRunner`。
- 对所有镜像类行为都要复用 `MirrorTask` 和 `TaskManager`。
- 使用现有的状态值，并保持 `stage` 为简短的中文步骤描述。
- 进度更新必须通过 `_handle_progress`。
- 支持暂停 / 恢复 / 取消，并使用 `mirror:{task_id}:{pause|resume|cancel}` 回调按钮。

## 下载 / 上传逻辑

- 直链 HTTP 下载：扩展 `bot/modules/download_manager.py` 中的 `DirectLinkFetcher`。
- Telegram 文件下载：使用 `TelegramFetcher`。
- YouTube / 流媒体下载：使用 `YtDlpFetcher`。
- 上传到 Google Drive：使用 `bot/modules/gdriveTools.py` 中的 `GoogleDriveHelper`，
  以及 `bot/modules/drive_helper.py` 中的辅助方法。不要新建临时的 Drive 客户端。

## Drive 授权与模式

- 使用 `bot/helpers/gdrive_utils/credentials_manager.py` 中的 `credential_manager`。
- 使用 `bot/helpers/sql_helper` 中的 SQL 帮助（gDriveDB、idsDB、mirror_tasks）。
- 使用 `get_drive_instance` / `cleanup_drive_instances` / `invalidate_drive_instance`。
- 同时支持两种模式："oauth" 和 "service_account"。

## 插件与处理函数

- 新增机器人命令的步骤：
  1. 在 `bot/config.py` 的 `BotCommands` 中添加命令名称与别名。
  2. 在 `bot/config.py` 的 `Messages` 中添加中文文案。
  3. 在 `bot/plugins/*.py` 中实现 handler：
     - 当需要 Drive 授权时，使用
       `@Client.on_message(... & CustomFilters.auth_users)`。
- Handler 要求：
  - 做好参数校验。
  - 使用清晰的中文错误提示和用法提示。
  - 业务逻辑应放在 `bot/modules` 或 `bot/helpers` 中，而不是直接写在 handler 里。

## 风格与安全

- 使用类型标注，并遵循 PEP 8。
- 复用 `bot/helpers/utils.py` 中的工具函数（如 format_bytes、进度条等）。
- 不要削弱 `bot/__init__.py` 中的校验逻辑。
- 遵守各类限制：MAX_MIRROR_FILE_SIZE、MAX_CONCURRENT_MIRRORS、Drive 熔断等。
- 不要硬编码真实的密钥或用户 ID（`bot/__init__.py` 中的固定 SUDO 开发者 ID 除外）。
