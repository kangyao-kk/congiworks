import hashlib
import os
import secrets
from datetime import datetime, timezone

from .config import settings


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 password hashing with random salt."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, settings.pbkdf2_iterations)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against its PBKDF2-SHA256 hash."""
    try:
        salt_hex, key_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, settings.pbkdf2_iterations)
        return secrets.compare_digest(key, stored_key)
    except (ValueError, AttributeError):
        return False


def hash_token(token: str) -> str:
    """Hash a token string with SHA256 for database storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(length: int = 48) -> str:
    """Generate a cryptographically secure random token string."""
    return secrets.token_urlsafe(length)


def utcnow() -> datetime:
    """Return a naive UTC datetime (SQLite does not store timezone info)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
