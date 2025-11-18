"""确保 bot.modules 中的命令处理器被注册。

Pyrogram 的插件系统会自动导入 bot/plugins 下的所有模块，但 bot/modules
中的处理器此前依赖 `load_module_plugins` 手动加载。增加这个插件后，
启动时会自动导入这些模块，避免遗漏导致指令无响应。
"""

from importlib import import_module
from pathlib import Path


MODULE_NAMES = [
    "auth_mode",
    "auto_capture",
    "download_manager",
    "list_drive",
    "mirror",
    "search_drive",
]


def _import_modules() -> None:
    base_path = Path(__file__).resolve().parent.parent / "modules"
    if not base_path.is_dir():
        return
    for name in MODULE_NAMES:
        try:
            import_module(f"bot.modules.{name}")
        except Exception:
            # 让其他插件继续加载，具体异常会在 Pyrogram 日志中显示
            continue


_import_modules()

