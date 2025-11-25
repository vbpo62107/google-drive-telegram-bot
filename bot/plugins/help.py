from typing import Optional

from bot import LOGGER, SUPPORT_CHAT_LINK
from bot.config import Messages as tr
from bot.plugins.utils import mark_command_handled
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _build_help_keyboard(pos: int) -> list[list[InlineKeyboardButton]]:
    if pos == 1:
        return [[InlineKeyboardButton(text="-->", callback_data="help+2")]]
    if pos == len(tr.HELP_MSG) - 1:
        return [
            [
                InlineKeyboardButton(text="Support Chat", url=SUPPORT_CHAT_LINK),
                InlineKeyboardButton(
                    text="Feature Request",
                    url="https://github.com/viperadnan-git/google-drive-telegram-bot/issues/new",
                ),
            ],
            [InlineKeyboardButton(text="<--", callback_data=f"help+{pos-1}")],
        ]
    return [
        [
            InlineKeyboardButton(text="<--", callback_data=f"help+{pos-1}"),
            InlineKeyboardButton(text="-->", callback_data=f"help+{pos+1}"),
        ],
    ]


async def _send_response(
    client: Client,
    message,
    text: str,
    command_name: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    mark_command_handled(message)
    try:
        await client.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=reply_markup,
            reply_to_message_id=message.id,
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        LOGGER.exception(
            "Failed to send %s response (chat_id=%s, user_id=%s, message_id=%s)",
            command_name,
            getattr(message.chat, "id", "unknown"),
            getattr(message.from_user, "id", "unknown"),
            getattr(message, "id", "unknown"),
        )
        LOGGER.warning(
            "Retrying %s response without custom markup due to error: %s",
            command_name,
            exc,
        )
        await client.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=None,
            reply_to_message_id=message.id,
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
        )


@Client.on_message(filters.private & filters.incoming & filters.command(["start"]), group=2)
async def _start(client, message):
    text = tr.START_MSG.format(message.from_user.mention)
    await _send_response(client, message, text, "/start")


@Client.on_message(filters.private & filters.incoming & filters.command(["help"]), group=2)
async def _help(client, message):
    text = tr.HELP_MSG[1]
    markup = InlineKeyboardMarkup(_build_help_keyboard(1))
    await _send_response(client, message, text, "/help", markup)


help_callback_filter = filters.create(lambda _, __, query: (query.data or "").startswith("help+"))


@Client.on_callback_query(help_callback_filter)
async def help_answer(client, callback_query):
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.id
    msg = int(callback_query.data.split("+")[1])
    text = tr.HELP_MSG[msg]
    markup = InlineKeyboardMarkup(_build_help_keyboard(msg))
    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        LOGGER.exception("Failed to edit help message")
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
        )
