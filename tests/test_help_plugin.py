import pathlib
import sys
import types
from unittest.mock import AsyncMock

import pytest

# Ensure required environment variables for importing bot package
DEFAULT_ENV_VARS = {
    "BOT_TOKEN": "TEST_BOT_TOKEN",
    "APP_ID": "12345",
    "API_HASH": "TEST_API_HASH",
    "DATABASE_URL": "sqlite:///:memory:",
    "SUDO_USERS": "1",
    "SUPPORT_CHAT_LINK": "https://example.com/support",
    "G_DRIVE_CLIENT_ID": "dummy_client_id",
    "G_DRIVE_CLIENT_SECRET": "dummy_client_secret",
    "TOKEN_ENCRYPTION_KEY": "x" * 32,
}


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    for key, value in DEFAULT_ENV_VARS.items():
        monkeypatch.setenv(key, value)

    # Provide lightweight stubs for heavy optional dependencies required during import
    if "bot.helpers.gdrive_utils.credentials_manager" not in sys.modules:
        dummy_gdrive_utils = types.ModuleType("bot.helpers.gdrive_utils")
        sys.modules.setdefault("bot.helpers.gdrive_utils", dummy_gdrive_utils)

        credential_manager_module = types.ModuleType("bot.helpers.gdrive_utils.credentials_manager")

        class _DummyCredentialManager:
            def service_account_available(self) -> bool:  # pragma: no cover - trivial
                return False

        credential_manager_module.credential_manager = _DummyCredentialManager()
        sys.modules["bot.helpers.gdrive_utils.credentials_manager"] = credential_manager_module

    if "bot.helpers.sql_helper" not in sys.modules:
        sql_helper_module = types.ModuleType("bot.helpers.sql_helper")

        class _DummyDriveDB:
            @staticmethod
            def is_authorized(user_id: int) -> bool:  # pragma: no cover - trivial
                return False

        sql_helper_module.gDriveDB = _DummyDriveDB()
        sys.modules["bot.helpers.sql_helper"] = sql_helper_module

    # Ensure the project root is on sys.path for module imports
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


@pytest.fixture
def anyio_backend():  # pragma: no cover - test configuration
    return "asyncio"


class _DummyUser:
    def __init__(self, user_id: int, mention: str) -> None:
        self.id = user_id
        self.mention = mention


class _DummyChat:
    def __init__(self, chat_id: int) -> None:
        self.id = chat_id


class _DummyMessage:
    def __init__(self, message_id: int, chat_id: int, user_id: int) -> None:
        self.id = message_id
        self.chat = _DummyChat(chat_id)
        self.from_user = _DummyUser(user_id, f"<b>User {user_id}</b>")


@pytest.mark.anyio
async def test_start_handler_sends_start_message():
    from bot.config import Messages as tr
    from bot.plugins import help as help_plugin

    client = AsyncMock()
    client.send_message = AsyncMock()
    message = _DummyMessage(message_id=1, chat_id=100, user_id=200)

    await help_plugin._start(client, message)

    assert client.send_message.await_count == 1
    kwargs = client.send_message.await_args.kwargs
    assert kwargs["text"] == tr.START_MSG.format(message.from_user.mention)
    assert kwargs["reply_markup"] is None


@pytest.mark.anyio
async def test_help_handler_sends_help_message_with_keyboard():
    from bot.config import Messages as tr
    from bot.plugins import help as help_plugin
    from pyrogram.types import InlineKeyboardMarkup

    client = AsyncMock()
    client.send_message = AsyncMock()
    message = _DummyMessage(message_id=2, chat_id=101, user_id=201)

    await help_plugin._help(client, message)

    assert client.send_message.await_count == 1
    kwargs = client.send_message.await_args.kwargs
    assert kwargs["text"] == tr.HELP_MSG[1]
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)
    assert kwargs["reply_markup"].inline_keyboard
