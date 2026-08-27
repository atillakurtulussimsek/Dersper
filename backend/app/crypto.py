"""Yapay zeka API anahtarı gibi hassas alanların şifrelenmesi."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    """ENCRYPTION_KEY geçerli bir Fernet anahtarı değilse ondan türetir."""
    raw = settings.encryption_key.encode()
    try:
        return Fernet(raw)
    except (ValueError, TypeError):
        derived = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
        return Fernet(derived)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return ""


def mask(value: str) -> str:
    """Arayüzde göstermek için: sk-abc...wxyz"""
    if not value:
        return ""
    if len(value) <= 10:
        return "•" * len(value)
    return f"{value[:5]}…{value[-4:]}"
