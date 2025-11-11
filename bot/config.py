class config:
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    APP_ID = "123456"
    API_HASH = "YOUR_API_HASH"
    DATABASE_URL = "postgres://username:password@host:5432/database"
    SUDO_USERS = "123456789"  # Sepearted by space.
    SUPPORT_CHAT_LINK = "https://your-support-link"
    DOWNLOAD_DIRECTORY = "./downloads/"
    G_DRIVE_CLIENT_ID = "your-google-client-id"
    G_DRIVE_CLIENT_SECRET = "your-google-client-secret"
    MAX_MIRROR_FILE_SIZE = 10 * 1024 * 1024 * 1024


class BotCommands:
  Download = ['download', 'dl']
  Authorize = ['auth', 'authorize']
  SetFolder = ['setfolder', 'setfl']
  Revoke = ['revoke']
  Clone = ['copy', 'clone']
  Delete = ['delete', 'del']
  EmptyTrash = ['emptyTrash']
  YtDl = ['ytdl']
  ListDrive = ['listdrive', 'lsdrive']
  SearchDrive = ['searchdrive', 'sdrive']

class Messages:
    START_MSG = "**你好呀 {}.**\n__我是Google云端硬盘上载程序Bot.您可以使用我从直接链接或电报文件将任何文件/视频上传到Google云端硬盘.__\n__您可以从/ help中了解更多信息. /help.__"

    HELP_MSG = [
        ".",
        "**Google云端硬盘上传器**\n__我可以将文件从直接链接或电报文件上传到您的Google云端硬盘.我需要做的就是对我的Google云端硬盘帐户进行身份验证.然后发送直接下载链接或电报文件.__\n\n我具有更多功能...想知道吗?只需遍历本教程并仔细阅读消息即可.",
        
        f"**验证Google云端硬盘**\n__发送 /{BotCommands.Authorize[0]} 注意,您将收到一个URL,访问URL并按照步骤操作,并在此处发送收到的代码.使用 /{BotCommands.Revoke[0]} 撤销您当前登录的Google云端硬盘帐户.__\n\n**请注意: 在您授权我之前,不会听任何命令或消息 (except /{BotCommands.Authorize[0]} command) 授权命令除外.\n所以, 授权是强制性的 !**",
        
        f"**下载链接**\n__向我发送文件的直接下载链接,我会将其下载到我的服务器上,并将其上传到您的Google Drive帐户. 您可以在上传文件到GDrive帐户之前重命名文件. 只需将URL发送给我和分隔符 ' | '.__\n\n**__例如:__**\n```https://example.com/AFileWithDirectDownloadLink.mkv | 新的文件名.mkv```\n\n**Telegram 文件**\n__要在您的Google云端硬盘帐户中上传电报文件,只需将文件发送给我,我就会下载并将其上传到您的Google云端硬盘帐户.. 注意：电报文件下载速度较慢，大文件可能需要更长的时间。.__\n\n**YouTube-DL 支持**\n__下载YouTube文件使用youtube-dl.\nUse /{BotCommands.YtDl[0]} (YouTube 链接/YouTube-DL Supported site link)__",
        
        f"**要上传的自定义文件夹**\n__要在自定义文件夹或者在__ **TeamDrive** __ ?\nUse /{BotCommands.SetFolder[0]} (Folder URL) 来设置自定义上传文件夹.\n所有文件上传到该文件夹中.__",
        
        f"**删除Google云端硬盘文件**\n__删除谷歌驱动器文件。使用 /{BotCommands.Delete[0]} (文件/文件夹URL) 删除文件或回复 /{BotCommands.Delete[0]} to bot message.\nYou can also empty trash files use /{BotCommands.EmptyTrash[0]}\nNote: Files are deleted permanently. This process cannot be undone.\n\n**Copy Google Drive Files**\n__Yes, Clone or Copy Google Drive Files.\n__Use /{BotCommands.Clone[0]} (File id / Folder id or URL) to copy Google Drive Files in your Google Drive Account.__",

        f"**浏览Google云端硬盘目录**\n__使用 /{BotCommands.ListDrive[0]} (可选: 文件夹ID或路径) 查看当前或指定目录中的文件.__",

        f"**搜索Google云端硬盘文件**\n__使用 /{BotCommands.SearchDrive[0]} 关键字 (可选: 使用 `|` 分隔的分页标记) 按名称搜索可访问的文件或文件夹.__",
        
        "**Rules & Precautions**\n__1. Don't copy BIG Google Drive Files/Folders. It may hang the bot and your files maybe damaged.\n2. Send One request at a time unless bot will stop all processes.\n3. Don't send slow links @transload it first.\n4. Don't misuse, overload or abuse this free service.__",
        
        # Dont remove this ↓ if you respect developer.
        "**Developed by @viperadnan**"
        ]
     
    RATE_LIMIT_EXCEEDED_MESSAGE = "❗ **超过限速.**\n__24小时后超出用户速率限制.__"
    
    FILE_NOT_FOUND_MESSAGE = "❗ **找不到文件/文件夹.**\n__File id - {} 未找到。 确保它是 存在并且可以由登录的帐户访问.__"
    
    INVALID_GDRIVE_URL = "❗ **无效的Google云端硬盘网址**\n确保Google云端硬盘网址的格式正确."
    
    COPIED_SUCCESSFULLY = "✅ **复制成功.**\n[{}]({}) __({})__"
    
    NOT_AUTH = f"🔑 **您尚未认证我可以上传到任何帐户.**\n__Send /{BotCommands.Authorize[0]} to authenticate.__"
    
    DOWNLOADED_SUCCESSFULLY = "📤 **上传文件中...**\n**Filename:** ```{}```\n**Size:** ```{}```"
    
    UPLOADED_SUCCESSFULLY = "✅ **上传成功.**\n[{}]({}) __({})__"
    
    DOWNLOAD_ERROR = "❗**下载失败**\n{}\n__Link - {}__"

    INVALID_FILENAME = "❗ **无效的文件名**\n__请提供有效的文件名.__"
    
    DOWNLOADING = "📥 **下载文件...\nLink:** ```{}```"
    
    ALREADY_AUTH = "🔒 **已授权您的Google云端硬盘帐户.**\n__Use /revoke to revoke the current account.__\n__Send me a direct link or File to Upload on Google Drive__"
    
    FLOW_IS_NONE = f"❗ **无效的代码**\n__Run {BotCommands.Authorize[0]} first.__"
    
    AUTH_SUCCESSFULLY = '🔐 **成功授权Google云端硬盘帐户.**'
    
    INVALID_AUTH_CODE = '❗ **无效的代码**\n__您发送的代码无效或之前已经使用过。通过授权URL生成新的__'
    
    AUTH_TEXT = "⛓️ **要授权您的Google云端硬盘帐户，请访问此 [URL]({}) 并在此处发送生成的代码.**\n__访问URL>允许权限>您将获得一个代码>复制它>在此处发送__"
    
    DOWNLOAD_TG_FILE = "📥 **下载文件...**\n**Filename:** ```{}```\n**Size:** ```{}```\n**MimeType:** ```{}```"
    
    PARENT_SET_SUCCESS = '🆔✅ **自定义文件夹链接设置成功.**\n__您的自定义文件夹ID - {}\nUse__ ```/{} clear``` __to clear it.__'
    
    PARENT_CLEAR_SUCCESS = f'🆔🚮 **自定义文件夹ID已成功清除.**\n__Use__ ```/{BotCommands.SetFolder[0]} (Folder Link)``` __to set it back__.'
    
    CURRENT_PARENT = "🆔 **您当前的自定义文件夹ID - {}**\n__Use__ ```/{} (Folder link)``` __to change it.__"
    
    REVOKED = f"🔓 **成功撤销当前登录的帐户.**\n__Use /{BotCommands.Authorize[0]} 再次进行身份验证并使用该机器人.__"
    
    NOT_FOLDER_LINK = "❗ **无效的文件夹链接.**\n__您发送的链接不属于文件夹.__"
    
    CLONING = "🗂️ **克隆到Google云端硬盘...**\n__G-Drive 链接 - {}__"
    
    PROVIDE_GDRIVE_URL = "**❗ 提供有效的Google云端硬盘网址和命令.**\n__Usage - /{} (GDrive Link)__"
    
    INSUFFICIENT_PERMISSONS = "❗ **您对此文件的权限不足.**\n__File id - {}__"
    
    DELETED_SUCCESSFULLY = "🗑️✅ **文件删除成功.**\n__档案已永久删除 !\nFile id - {}__"
    
    WENT_WRONG = "⁉️ **ERROR: SOMETHING WENT WRONG**\n__Please try again later.__"
    
    EMPTY_TRASH = "🗑️🚮**成功清空垃圾箱 !**"
    
    PROVIDE_YTDL_LINK = "❗**提供有效的YouTube-DL支持的链接.**"
    LIST_HEADER = "📂 **目录内容**\n**路径:** `{}`\n**ID:** `{}`"
    LIST_CONT_HEADER = "📂 **目录内容 (续)**\n**路径:** `{}`\n**ID:** `{}`"
    LIST_EMPTY = "📂 **目录为空**\n**路径:** `{}`"
    LIST_ERROR = "❗ **获取目录内容失败**\n{}"
    LIST_PATH_NOT_FOUND = "❗ **未找到路径段:** `{}`"
    LIST_DEFAULT_LABEL = "默认目录"
    SEARCH_USAGE = "❗ **请提供搜索关键字.**\n__用法 - /{} 关键字 或 /{} 关键字 | 下一页标记__"
    SEARCH_ERROR = "❗ **搜索失败**\n{}"
    SEARCH_NO_RESULTS = "🔍 **没有找到匹配的文件或文件夹.**\n**关键字:** `{}`"
    SEARCH_RESULTS_HEADER = "🔍 **搜索结果**\n**关键字:** `{}`"
    SEARCH_PAGE_TOKEN = "▶️ **下一页标记:** `{}`"
