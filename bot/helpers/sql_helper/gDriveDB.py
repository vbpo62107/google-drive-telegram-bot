import json
import pickle
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from cachetools import TTLCache
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, func, inspect, text

from bot import (
    DEFAULT_AUTH_MODE,
    DRIVE_CIRCUIT_TIMEOUT,
    DRIVE_FAILURE_THRESHOLD,
    LOGGER,
    OAUTH_SCOPE,
    TOKEN_ENCRYPTION_KEY,
)
from bot.helpers.sql_helper import BASE, get_session


@dataclass
class CredentialRecord:
    chat_id: int
    mode: str
    payload: dict[str, Any]
    fingerprint: Optional[str]
    device: Optional[str]
    failure_count: int
    circuit_until: Optional[datetime]
    updated_at: Optional[datetime]

    def is_service_account(self) -> bool:
        return self.mode == "service_account"

    def is_oauth(self) -> bool:
        return self.mode == "oauth"

    def to_json(self) -> str:
        return json.dumps(self.payload)

    def is_circuit_open(self) -> bool:
        if not self.circuit_until:
            return False
        return self.circuit_until > datetime.utcnow()


class gDriveCreds(BASE):
    __tablename__ = "gDrive"
    chat_id = Column(Integer, primary_key=True)
    credential_string = Column(LargeBinary)
    mode = Column(String(32), default="oauth")
    fingerprint = Column(String(256))
    device = Column(String(128))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    failure_count = Column(Integer, default=0)
    circuit_until = Column(DateTime)


gDriveCreds.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()
_CACHE = TTLCache(maxsize=256, ttl=1800)
_FERNET: Optional[Fernet] = None


def _ensure_columns():
    engine = BASE.metadata.bind
    if engine is None:
        return
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns("gDrive")}
    statements = []
    if "mode" not in existing:
        statements.append("ALTER TABLE \"gDrive\" ADD COLUMN mode VARCHAR(32) DEFAULT 'oauth'")
    if "fingerprint" not in existing:
        statements.append("ALTER TABLE \"gDrive\" ADD COLUMN fingerprint VARCHAR(256)")
    if "device" not in existing:
        statements.append("ALTER TABLE \"gDrive\" ADD COLUMN device VARCHAR(128)")
    if "updated_at" not in existing:
        statements.append("ALTER TABLE \"gDrive\" ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()")
    if "failure_count" not in existing:
        statements.append("ALTER TABLE \"gDrive\" ADD COLUMN failure_count INTEGER DEFAULT 0")
    if "circuit_until" not in existing:
        statements.append("ALTER TABLE \"gDrive\" ADD COLUMN circuit_until TIMESTAMP NULL")
    if not statements:
        return
    with engine.connect() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                continue


_ensure_columns()


def _cache_key(chat_id):
    if isinstance(chat_id, bool):
        return chat_id
    try:
        return int(chat_id)
    except (TypeError, ValueError):
        return chat_id


def _cache_set(chat_id, record: Optional[CredentialRecord]):
    key = _cache_key(chat_id)
    if record is None:
        _CACHE.pop(key, None)
    else:
        _CACHE[key] = (record, time.time())


def _cache_get(chat_id) -> Optional[CredentialRecord]:
    key = _cache_key(chat_id)
    cached = _CACHE.get(key)
    if cached is None:
        return None
    return cached[0]


def _invalidate_drive(chat_id):
    try:
        from bot.modules.drive_helper import invalidate_drive_instance
    except Exception:
        return
    try:
        invalidate_drive_instance(chat_id)
    except Exception:
        pass


def _get_cipher() -> Fernet:
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    try:
        _FERNET = Fernet(TOKEN_ENCRYPTION_KEY.encode())
    except Exception as exc:
        LOGGER.error("Invalid TOKEN_ENCRYPTION_KEY: %s", exc)
        raise
    return _FERNET


def _encrypt_payload(payload: dict[str, Any]) -> bytes:
    return _get_cipher().encrypt(json.dumps(payload).encode("utf-8"))


def _convert_legacy(blob: bytes) -> Optional[dict[str, Any]]:
    try:
        legacy = pickle.loads(blob)
    except Exception:
        return None
    try:
        refresh_token = getattr(legacy, "refresh_token", None)
        client_id = getattr(legacy, "client_id", None)
        client_secret = getattr(legacy, "client_secret", None)
        token_uri = getattr(legacy, "token_uri", "https://oauth2.googleapis.com/token")
        scopes = getattr(legacy, "scopes", None)
        if scopes is None:
            scopes = [OAUTH_SCOPE]
        elif isinstance(scopes, (set, tuple)):
            scopes = list(scopes)
        expiry = getattr(legacy, "token_expiry", None)
        expiry_iso = expiry.isoformat() if expiry else None
        token = getattr(legacy, "access_token", None)
        payload = {
            "mode": "oauth",
            "token": token,
            "refresh_token": refresh_token,
            "token_uri": token_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "scopes": scopes,
            "expiry": expiry_iso,
        }
        return payload
    except Exception:
        return None


def _deserialize(blob: Optional[bytes]) -> tuple[dict[str, Any], bool]:
    if not blob:
        return {}, False
    try:
        decrypted = _get_cipher().decrypt(blob)
        return json.loads(decrypted.decode("utf-8")), False
    except InvalidToken:
        converted = _convert_legacy(blob)
        if converted:
            return converted, True
        LOGGER.warning("Failed to decrypt credential blob: invalid token")
    except Exception as exc:
        LOGGER.error("Failed to decrypt credential blob: %s", exc)
    return {}, False


def _build_record(row: gDriveCreds, payload: dict[str, Any]) -> CredentialRecord:
    mode = (row.mode or payload.get("mode") or DEFAULT_AUTH_MODE).lower()
    fingerprint = row.fingerprint or payload.get("fingerprint")
    device = row.device or payload.get("device")
    failure_count = row.failure_count or 0
    return CredentialRecord(
        chat_id=row.chat_id,
        mode=mode,
        payload=payload,
        fingerprint=fingerprint,
        device=device,
        failure_count=failure_count,
        circuit_until=row.circuit_until,
        updated_at=row.updated_at,
    )


def _save_record(record: CredentialRecord):
    with INSERTION_LOCK:
        with get_session() as session:
            saved = session.query(gDriveCreds).get(record.chat_id)
            if not saved:
                saved = gDriveCreds(record.chat_id)
            saved.mode = record.mode
            saved.fingerprint = record.fingerprint
            saved.device = record.device
            saved.failure_count = record.failure_count
            saved.circuit_until = record.circuit_until
            saved.updated_at = datetime.utcnow()
            saved.credential_string = _encrypt_payload(record.payload)
            session.add(saved)
            session.commit()
    _cache_set(record.chat_id, record)
    _invalidate_drive(record.chat_id)


def search(chat_id) -> Optional[CredentialRecord]:
    with INSERTION_LOCK:
        cached = _cache_get(chat_id)
        if cached is not None:
            return cached
        with get_session() as session:
            saved = session.query(gDriveCreds).get(chat_id)
            if saved is None:
                _cache_set(chat_id, None)
                return None
            payload, converted = _deserialize(saved.credential_string)
            if converted:
                payload.setdefault("mode", "oauth")
                saved.mode = payload.get("mode", saved.mode)
                saved.fingerprint = payload.get("fingerprint", saved.fingerprint)
                saved.device = payload.get("device", saved.device)
                saved.credential_string = _encrypt_payload(payload)
                session.add(saved)
                session.commit()
            record = _build_record(saved, payload)
    _cache_set(chat_id, record)
    return record


def exists(chat_id: str) -> bool:
    record = search(chat_id)
    return record is not None and (record.is_service_account() or bool(record.payload))


def is_authorized(chat_id: str) -> bool:
    record = search(chat_id)
    if record is None:
        return False
    if record.is_service_account():
        return True
    return bool(record.payload.get("refresh_token")) or bool(record.payload.get("token"))


def save_credentials(
    chat_id: int,
    *,
    mode: str,
    payload: dict[str, Any],
    fingerprint: Optional[str] = None,
    device: Optional[str] = None,
) -> CredentialRecord:
    record = CredentialRecord(
        chat_id=chat_id,
        mode=mode,
        payload=payload,
        fingerprint=fingerprint,
        device=device,
        failure_count=0,
        circuit_until=None,
        updated_at=datetime.utcnow(),
    )
    _save_record(record)
    return record


def update_payload(chat_id: int, payload: dict[str, Any], fingerprint: Optional[str]) -> Optional[CredentialRecord]:
    with INSERTION_LOCK:
        with get_session() as session:
            saved = session.query(gDriveCreds).get(chat_id)
            if saved is None:
                return None
            saved.credential_string = _encrypt_payload(payload)
            if fingerprint:
                saved.fingerprint = fingerprint
            saved.updated_at = datetime.utcnow()
            session.add(saved)
            session.commit()
            record = _build_record(saved, payload)
    _cache_set(chat_id, record)
    return record


def mark_failure(chat_id: int) -> Optional[CredentialRecord]:
    with INSERTION_LOCK:
        with get_session() as session:
            saved = session.query(gDriveCreds).get(chat_id)
            if saved is None:
                return None
            current = saved.failure_count or 0
            current += 1
            saved.failure_count = current
            if current >= DRIVE_FAILURE_THRESHOLD:
                saved.circuit_until = datetime.utcnow() + timedelta(seconds=DRIVE_CIRCUIT_TIMEOUT)
                saved.failure_count = 0
                current = 0
            saved.updated_at = datetime.utcnow()
            session.add(saved)
            session.commit()
            payload, _ = _deserialize(saved.credential_string)
            record = _build_record(saved, payload)
    _cache_set(chat_id, record)
    return record


def reset_failures(chat_id: int) -> Optional[CredentialRecord]:
    with INSERTION_LOCK:
        with get_session() as session:
            saved = session.query(gDriveCreds).get(chat_id)
            if saved is None:
                return None
            saved.failure_count = 0
            saved.circuit_until = None
            saved.updated_at = datetime.utcnow()
            session.add(saved)
            session.commit()
            payload, _ = _deserialize(saved.credential_string)
            record = _build_record(saved, payload)
    _cache_set(chat_id, record)
    return record


def is_circuit_open(chat_id: int) -> bool:
    record = search(chat_id)
    if record is None:
        return False
    return record.is_circuit_open()


def _clear(chat_id):
    with INSERTION_LOCK:
        with get_session() as session:
            saved = session.query(gDriveCreds).get(chat_id)
            if saved:
                session.delete(saved)
                session.commit()
    _cache_set(chat_id, None)
    _invalidate_drive(chat_id)
