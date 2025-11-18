# OpenAI Codex Agent for google-drive-telegram-bot

You are an AI coding assistant dedicated to this repository: `vbpo62107/google-drive-telegram-bot`.

## Tech Stack & Entry Point

* Python 3.x
* Telegram bot built with Pyrogram
* Entry file: `bot/__main__.py`:

  * Imports all modules under `bot.modules.*`.
  * Configures plugins via `plugins = {"root": "bot/plugins"}`.
  * Ensures `DOWNLOAD_DIRECTORY` exists.
  * Cleans up Drive instances when the process exits.

## Configuration

* `bot/__init__.py` loads environment variables (optionally from `.env`) and validates required fields:

  * BOT_TOKEN, APP_ID, API_HASH, DATABASE_URL, SUDO_USERS, SUPPORT_CHAT_LINK,
    G_DRIVE_CLIENT_ID, G_DRIVE_CLIENT_SECRET, etc.
* Parses boolean values and numeric limits (MAX_MIRROR_FILE_SIZE, MAX_CONCURRENT_MIRRORS,
  DRIVE_FAILURE_THRESHOLD, DRIVE_CIRCUIT_TIMEOUT).
* Normalizes DEFAULT_AUTH_MODE to `"oauth"` or `"service_account"`.
* Converts SUDO_USERS into a sorted list of ints and requires at least one ID.

## Commands & User-Facing Text

* Command names and aliases are defined in `BotCommands` in `bot/config.py`.
* All user-visible text is in Chinese and defined in `Messages` in `bot/config.py`.
* When adding new user-visible text, add it to `Messages` instead of hard-coding Chinese strings directly in code.

## Permissions

* High-privilege operations (mirroring, downloads, long-running Drive operations) must:

  * Check `SUDO_USERS` (only SUDO users may trigger them).
  * Use `CustomFilters.auth_users` when Drive authorization is required.

## Mirror Tasks

* Long-running mirror tasks (download + upload) use:

  * The SQLAlchemy model `MirrorTask` (table name `mirror_tasks`).
  * `TaskManager` and `MirrorTaskRunner` in `bot/modules/task_manager.py`.
* All mirror-type behaviors must reuse `MirrorTask` and `TaskManager`.
* Use existing status values and keep `stage` as short Chinese step descriptions.
* Progress updates must go through `_handle_progress`.
* Support pause / resume / cancel, using callback buttons `mirror:{task_id}:{pause|resume|cancel}`.

## Download / Upload Logic

* Direct HTTP downloads: extend `DirectLinkFetcher` in `bot/modules/download_manager.py`.
* Telegram file downloads: use `TelegramFetcher`.
* YouTube / streaming downloads: use `YtDlpFetcher`.
* Uploads to Google Drive: use `GoogleDriveHelper` in `bot/modules/gdriveTools.py`
  and helper methods in `bot/modules/drive_helper.py`. Do not create ad-hoc Drive clients.

## Drive Authorization & Modes

* Use `credential_manager` in `bot/helpers/gdrive_utils/credentials_manager.py`.
* Use SQL helpers under `bot/helpers/sql_helper` (gDriveDB, idsDB, mirror_tasks).
* Use `get_drive_instance` / `cleanup_drive_instances` / `invalidate_drive_instance`.
* Support both modes: `"oauth"` and `"service_account"`.

## Plugins & Handlers

* Steps for adding a new bot command:

  1. Add the command name and aliases to `BotCommands` in `bot/config.py`.
  2. Add Chinese user-facing text to `Messages` in `bot/config.py`.
  3. Implement the handler in `bot/plugins/*.py`:

     * When Drive authorization is required, use
       `@Client.on_message(... & CustomFilters.auth_users)`.
* Handler requirements:

  * Validate parameters thoroughly.
  * Use clear Chinese error messages and usage hints.
  * Put business logic in `bot/modules` or `bot/helpers`, not directly inside the handler.

## Style & Safety

* Use type hints and follow PEP 8.
* Reuse utility functions from `bot/helpers/utils.py` (e.g., `format_bytes`, progress bar helpers, etc.).
* Do not weaken the validation logic in `bot/__init__.py`.
* Respect all limits: MAX_MIRROR_FILE_SIZE, MAX_CONCURRENT_MIRRORS, Drive circuit breaker, etc.
* Do not hard-code real secrets or user IDs (except the fixed SUDO developer ID in `bot/__init__.py`).
