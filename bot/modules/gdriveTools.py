import asyncio
from typing import Optional

from bot.modules.drive_helper import get_drive_instance


class GoogleDriveHelper:
    def __init__(self, user_id: int) -> None:
        self._user_id = str(user_id)
        self._drive = None
        self._lock = asyncio.Lock()

    async def _ensure_drive(self):
        if self._drive is not None:
            return
        async with self._lock:
            if self._drive is None:
                self._drive = await get_drive_instance(self._user_id)

    async def clone(self, link: str) -> str:
        await self._ensure_drive()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._drive.clone, link)

    async def upload(self, file_path: str, mime_type: Optional[str] = None) -> str:
        await self._ensure_drive()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._drive.upload_file, file_path, mime_type)

    async def delete(self, link: str) -> str:
        await self._ensure_drive()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._drive.delete_file, link)
