# Google Drive Uploader Telegram Bot
**A Telegram bot to upload files from Telegram or Direct links to Google Drive.**
- Find it on Telegram as [Google Drive Uploader](https://t.me/uploadgdrivebot)

## Features
- [X] Telegram files support.
- [X] Direct Links support.
- [X] Custom Upload Folder.
- [X] TeamDrive Support.
- [X] Clone/Copy Google Drive Files.
- [X] Delete Google Drive Files.
- [X] Empty Google Drive trash.
- [X] youtube-dl support.
- [X] Mirror task manager with pause/resume/cancel controls and persistent recovery.

## ToDo 
- [ ] Handle more exceptions.
- [ ] LOGGER support.
- [ ] Service account support.
- [ ] Update command.

## Deploying

### Deploy on [Heroku](https://heroku.com)
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### Installation
- Install required modules.
```sh
apt install -y git python3 ffmpeg
```
- Clone this git repository.
```sh 
git clone https://github.com/spilgt/google-drive-telegram-bot
```
- Change Directory
```sh 
cd google-drive-telegram-bot
```
- Install requirements with pip3
```sh 
pip3 install -r requirements.txt
```

### Configuration
The bot now relies exclusively on environment variables. You can either export them in your shell or create a `.env` file next to `README.md`.

1. Copy `.env.example` to `.env`.
   ```sh
   cp .env.example .env
   ```
2. Fill in each placeholder with your real secrets.
3. Start the bot; configuration values are loaded from the environment at runtime.

### Required variables
- `BOT_TOKEN` - Get it by contacting [BotFather](https://t.me/botfather)
- `APP_ID` - Get it by creating an app on [my.telegram.org](https://my.telegram.org/apps)
- `API_HASH` - Get it by creating an app on [my.telegram.org](https://my.telegram.org/apps)
- `SUDO_USERS` - Space separated list of Telegram user IDs with elevated access
- `SUPPORT_CHAT_LINK` - Telegram invite link of the support chat
- `DATABASE_URL` - Postgres connection string
- `G_DRIVE_CLIENT_ID` - Google OAuth client ID
- `G_DRIVE_CLIENT_SECRET` - Google OAuth client secret

### Optional variables
- `DOWNLOAD_DIRECTORY` - Custom path for downloads. Must end with a forward `/` slash. Defaults to `./downloads/`
- `MAX_MIRROR_FILE_SIZE` - Maximum file size in bytes for mirror operations. Defaults to `10737418240`
- `MAX_CONCURRENT_MIRRORS` - Maximum number of concurrent mirror tasks. Defaults to `2`

### Mirror task controls
- `/mirror <url>` now creates a managed task with inline buttons to pause, resume, or cancel.
- Tasks beyond the concurrency limit wait in a queue and start automatically when slots free up.
- Progress notifications stay in sync with the task database so running tasks restore after bot restarts.

### Automatic channel monitoring
- SUDO users can manage keyword-based channel monitors with `/addmonitor`, `/listmonitor`, `/togglemonitor`, and `/delmonitor`.
- When the bot is a member of the channel and a post matches configured keywords, media or links are mirrored automatically with the same task manager used by manual `/mirror` jobs.
- Notifications are sent to all SUDO users and tasks can be paused, resumed, or cancelled from the inline controls in the admin chat.
- Disable monitors when no longer needed to stop background listeners and avoid unintended transfers.

### Deploy 
```sh 
python3 -m bot
```

## Credits
- [Dan](https://github.com/delivrance) for creating [PyroGram](https://pyrogram.org)
- [Spechide](https://github.com/Spechide) for [gDriveDB.py](./bot/helpers/sql_helper/gDriveDB.py)
- [Shivam Jha](https://github.com/lzzy12) for [Clone Feature](./bot/helpers/gdrive_utils/gDrive.py) from [python-aria-mirror-bot](https://github.com/lzzy12/python-aria-mirror-bot)

## Copyright & License
- Copyright (©) 2020 by [Adnan Ahmad](https://github.com/viperadnan-git)
- Licensed under the terms of the [GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007](./LICENSE)
