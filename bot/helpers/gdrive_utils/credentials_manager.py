import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from bot import (
    G_DRIVE_CLIENT_ID,
    G_DRIVE_CLIENT_SECRET,
    LOGGER,
    OAUTH_SCOPE,
    SERVICE_ACCOUNT_DATA,
    SERVICE_ACCOUNT_FILE,
    SERVICE_ACCOUNT_SUBJECT,
)
from bot.helpers.sql_helper import gDriveDB
from bot.helpers.sql_helper.gDriveDB import CredentialRecord

SERVICE_ACCOUNT_SCOPE = "https://www.googleapis.com/auth/drive"


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                return None


def _serialize_datetime(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def _compute_oauth_fingerprint(payload: dict) -> Optional[str]:
    refresh_token = payload.get("refresh_token")
    client_id = payload.get("client_id")
    client_secret = payload.get("client_secret")
    if not refresh_token and not payload.get("token"):
        return None
    base = "|".join(
        [
            refresh_token or "",
            client_id or "",
            client_secret or "",
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _load_service_account_info() -> Optional[dict]:
    if SERVICE_ACCOUNT_DATA:
        try:
            return json.loads(SERVICE_ACCOUNT_DATA)
        except json.JSONDecodeError as exc:
            LOGGER.error("Invalid SERVICE_ACCOUNT_DATA: %s", exc)
            return None
    if SERVICE_ACCOUNT_FILE:
        try:
            with open(SERVICE_ACCOUNT_FILE, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            LOGGER.error("SERVICE_ACCOUNT_FILE not found: %s", SERVICE_ACCOUNT_FILE)
        except json.JSONDecodeError as exc:
            LOGGER.error("Invalid SERVICE_ACCOUNT_FILE JSON: %s", exc)
    return None


@dataclass
class _ServiceAccountBundle:
    info: dict
    fingerprint: str


class CredentialManager:
    def __init__(self) -> None:
        self._service_account_bundle: Optional[_ServiceAccountBundle] = None
        self._lock = threading.RLock()

    def service_account_available(self) -> bool:
        return self._ensure_service_account() is not None

    def _ensure_service_account(self) -> Optional[_ServiceAccountBundle]:
        with self._lock:
            if self._service_account_bundle is not None:
                return self._service_account_bundle
            info = _load_service_account_info()
            if not info:
                return None
            fingerprint = hashlib.sha256(json.dumps(info, sort_keys=True).encode("utf-8")).hexdigest()
            self._service_account_bundle = _ServiceAccountBundle(info=info, fingerprint=fingerprint)
            return self._service_account_bundle

    def service_account_fingerprint(self) -> Optional[str]:
        bundle = self._ensure_service_account()
        if not bundle:
            return None
        return bundle.fingerprint

    def ensure_fingerprint(self, user_id: int, record: CredentialRecord) -> Optional[str]:
        if record.fingerprint:
            return record.fingerprint
        if record.is_service_account():
            fingerprint = self.service_account_fingerprint()
            if fingerprint:
                payload = record.payload or {"mode": "service_account"}
                gDriveDB.update_payload(user_id, payload, fingerprint)
            return fingerprint
        fingerprint = _compute_oauth_fingerprint(record.payload)
        if fingerprint:
            gDriveDB.update_payload(user_id, record.payload, fingerprint)
        return fingerprint

    def build_credentials(self, user_id: int, record: CredentialRecord) -> Optional[Credentials]:
        if record.is_service_account():
            bundle = self._ensure_service_account()
            if not bundle:
                return None
            creds = service_account.Credentials.from_service_account_info(bundle.info, scopes=[SERVICE_ACCOUNT_SCOPE])
            if SERVICE_ACCOUNT_SUBJECT:
                creds = creds.with_subject(SERVICE_ACCOUNT_SUBJECT)
            return creds
        return self._build_oauth_credentials(user_id, record)

    def _build_oauth_credentials(self, user_id: int, record: CredentialRecord) -> Optional[Credentials]:
        payload = dict(record.payload)
        refresh_token = payload.get("refresh_token")
        token = payload.get("token")
        if not refresh_token and not token:
            return None
        creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri=payload.get("token_uri") or "https://oauth2.googleapis.com/token",
            client_id=payload.get("client_id") or G_DRIVE_CLIENT_ID,
            client_secret=payload.get("client_secret") or G_DRIVE_CLIENT_SECRET,
            scopes=payload.get("scopes") or [OAUTH_SCOPE],
        )
        expiry = _parse_datetime(payload.get("expiry"))
        if expiry:
            creds.expiry = expiry
        if not creds.valid or creds.expired:
            try:
                creds.refresh(Request())
            except Exception as exc:
                LOGGER.error("Failed to refresh credentials for %s: %s", user_id, exc)
                raise
            payload["token"] = creds.token
            payload["expiry"] = _serialize_datetime(creds.expiry)
            fingerprint = _compute_oauth_fingerprint(payload)
            gDriveDB.update_payload(user_id, payload, fingerprint)
        return creds

    def serialize_oauth(self, credentials: Credentials) -> tuple[dict, Optional[str]]:
        payload = {
            "mode": "oauth",
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes or [OAUTH_SCOPE]),
            "expiry": _serialize_datetime(credentials.expiry),
        }
        fingerprint = _compute_oauth_fingerprint(payload)
        return payload, fingerprint


credential_manager = CredentialManager()
