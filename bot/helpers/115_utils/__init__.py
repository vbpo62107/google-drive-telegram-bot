from __future__ import annotations

from importlib import import_module

_client = import_module("bot.helpers.115_utils.client")
_upload = import_module("bot.helpers.115_utils.upload")

OneOneFiveAuthError = _client.OneOneFiveAuthError
OneOneFiveClient = _client.OneOneFiveClient
OneOneFiveError = _client.OneOneFiveError
OneOneFiveUploadError = _client.OneOneFiveUploadError
ShareInfo = _client.ShareInfo
upload_to_115_for_user = _upload.upload_to_115_for_user

__all__ = [
    "OneOneFiveAuthError",
    "OneOneFiveClient",
    "OneOneFiveError",
    "OneOneFiveUploadError",
    "ShareInfo",
    "upload_to_115_for_user",
]
