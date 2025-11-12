import asyncio
import os
from pathlib import PurePath

from pyrogram import Client, filters
from pyrogram.errors import RPCError

from bot import DOWNLOAD_DIRECTORY, LOGGER
from bot.config import BotCommands, Messages
from bot.helpers.downloader import download_file, utube_dl
from bot.helpers.utils import CustomFilters, humanbytes
from bot.modules.drive_helper import DriveAccessError, drive_error_message, get_drive_instance

@Client.on_message(filters.private & filters.incoming & filters.text & (filters.command(BotCommands.Download) | filters.regex('^(ht|f)tp*')) & CustomFilters.auth_users)
async def _download(client, message):
  user_id = message.from_user.id
  if not message.media:
    sent_message = await message.reply_text('🕵️**Checking link...**', quote=True)
    if message.command:
      if len(message.command) > 1:
        link = message.command[1]
      else:
        await sent_message.edit(Messages.PROVIDE_GDRIVE_URL.format(BotCommands.Download[0]))
        return
    else:
      link = message.text
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await sent_message.edit(drive_error_message(exc.code))
        return
    except Exception as exc:
        await sent_message.edit(f"**ERROR:** ```{exc}```")
        return
    if 'drive.google.com' in link:
      await sent_message.edit(Messages.CLONING.format(link))
      LOGGER.info(f'Copy:{user_id}: {link}')
      msg = await asyncio.to_thread(drive.clone, link)
      await sent_message.edit(msg)
    else:
      download_root = os.path.abspath(DOWNLOAD_DIRECTORY)
      if '|' in link:
        link, filename = link.split('|', 1)
        link = link.strip()
        filename = filename.strip()
        filename = PurePath(filename).name
        filename = ''.join(ch for ch in filename if ch.isprintable() and ch not in {'/', '\\'})
        if not filename or any(ord(ch) < 32 for ch in filename) or filename in {'.', '..'}:
          await sent_message.edit(Messages.INVALID_FILENAME)
          return
        dl_path = os.path.abspath(os.path.join(download_root, filename))
        try:
          if os.path.commonpath([download_root, dl_path]) != download_root:
            await sent_message.edit(Messages.INVALID_FILENAME)
            return
        except ValueError:
          await sent_message.edit(Messages.INVALID_FILENAME)
          return
      else:
        link = link.strip()
        filename = os.path.basename(link)
        dl_path = download_root
      LOGGER.info(f'Download:{user_id}: {link}')
      await sent_message.edit(Messages.DOWNLOADING.format(link))
      result, file_path = await asyncio.to_thread(download_file, link, dl_path)
      if result:
        size = await asyncio.to_thread(os.path.getsize, file_path)
        await sent_message.edit(Messages.DOWNLOADED_SUCCESSFULLY.format(os.path.basename(file_path), humanbytes(size)))
        msg = await asyncio.to_thread(drive.upload_file, file_path)
        await sent_message.edit(msg)
        LOGGER.info(f'Deleteing: {file_path}')
        await asyncio.to_thread(os.remove, file_path)
      else:
        await sent_message.edit(Messages.DOWNLOAD_ERROR.format(file_path, link))


@Client.on_message(filters.private & filters.incoming & (filters.document | filters.audio | filters.video | filters.photo) & CustomFilters.auth_users)
async def _telegram_file(client, message):
  user_id = message.from_user.id
  sent_message = await message.reply_text('🕵️**Checking File...**', quote=True)
  if message.document:
    file = message.document
  elif message.video:
    file = message.video
  elif message.audio:
    file = message.audio
  elif message.photo:
    file = message.photo
    file.mime_type = "images/png"
    file.file_name = f"IMG-{user_id}-{message.message_id}.png"
  await sent_message.edit(Messages.DOWNLOAD_TG_FILE.format(file.file_name, humanbytes(file.file_size), file.mime_type))
  LOGGER.info(f'Download:{user_id}: {file.file_id}')
  try:
    drive = await get_drive_instance(user_id)
  except DriveAccessError as exc:
    await sent_message.edit(drive_error_message(exc.code))
    return
  except Exception as exc:
    await sent_message.edit(f"**ERROR:** ```{exc}```")
    return
  file_path = None
  try:
    file_path = await message.download(file_name=DOWNLOAD_DIRECTORY)
    size = await asyncio.to_thread(os.path.getsize, file_path)
    await sent_message.edit(Messages.DOWNLOADED_SUCCESSFULLY.format(os.path.basename(file_path), humanbytes(size)))
    msg = await asyncio.to_thread(drive.upload_file, file_path, file.mime_type)
    await sent_message.edit(msg)
  except RPCError:
    await sent_message.edit(Messages.WENT_WRONG)
  finally:
    if file_path:
      LOGGER.info(f'Deleteing: {file_path}')
      try:
        await asyncio.to_thread(os.remove, file_path)
      except FileNotFoundError:
        pass

@Client.on_message(filters.incoming & filters.private & filters.command(BotCommands.YtDl) & CustomFilters.auth_users)
async def _ytdl(client, message):
  user_id = message.from_user.id
  if len(message.command) > 1:
    sent_message = await message.reply_text('🕵️**Checking Link...**', quote=True)
    link = message.command[1]
    LOGGER.info(f'YTDL:{user_id}: {link}')
    await sent_message.edit(Messages.DOWNLOADING.format(link))
    try:
      drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
      await sent_message.edit(drive_error_message(exc.code))
      return
    except Exception as exc:
      await sent_message.edit(f"**ERROR:** ```{exc}```")
      return
    result, file_path = await asyncio.to_thread(utube_dl, link)
    if result:
      size = await asyncio.to_thread(os.path.getsize, file_path)
      await sent_message.edit(Messages.DOWNLOADED_SUCCESSFULLY.format(os.path.basename(file_path), humanbytes(size)))
      msg = await asyncio.to_thread(drive.upload_file, file_path)
      await sent_message.edit(msg)
      LOGGER.info(f'Deleteing: {file_path}')
      await asyncio.to_thread(os.remove, file_path)
    else:
      await sent_message.edit(Messages.DOWNLOAD_ERROR.format(file_path, link))
  else:
    await message.reply_text(Messages.PROVIDE_YTDL_LINK, quote=True)
