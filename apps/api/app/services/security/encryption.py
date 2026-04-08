"""
Token Encryption Service

Encrypts/decrypts sensitive credentials (OAuth tokens, API keys) using
Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256). Key is loaded
from the ENCRYPTION_KEY env var; never stored in the database.

If ENCRYPTION_KEY is unset, the service generates a temporary in-memory
key and logs a warning so dev environments still work — but tokens
encrypted with that key will become unreadable on the next process
start. Production deployments MUST set a permanent key.
"""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionService:
    """Encrypts credentials before DB storage; decrypts when loading for API use."""

    _fernet: Fernet | None = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        if cls._fernet is None:
            key = os.getenv("ENCRYPTION_KEY")
            if not key:
                logger.warning(
                    "ENCRYPTION_KEY not set in .env — generating temporary key. "
                    "Set a permanent key with: "
                    'python3 -c "from cryptography.fernet import Fernet; '
                    'print(Fernet.generate_key().decode())"'
                )
                key = Fernet.generate_key().decode()
            cls._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str | None) -> str | None:
        """Encrypt a string. Returns base64-encoded ciphertext, or None for empty input."""
        if not plaintext:
            return None
        try:
            return cls._get_fernet().encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.error("Encryption failed: %s", e)
            return None

    @classmethod
    def decrypt(cls, ciphertext: str | None) -> str | None:
        """Decrypt a Fernet ciphertext. Returns plaintext or None on failure."""
        if not ciphertext:
            return None
        try:
            return cls._get_fernet().decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("Decryption failed: invalid token — key mismatch or corrupted data")
            return None
        except Exception as e:
            logger.error("Decryption failed: %s", e)
            return None

    @classmethod
    def generate_key(cls) -> str:
        """Generate a fresh Fernet key. Run once and store in .env."""
        return Fernet.generate_key().decode()


# Singleton helper functions for ergonomic imports.
def encrypt(plaintext: str | None) -> str | None:
    return EncryptionService.encrypt(plaintext)


def decrypt(ciphertext: str | None) -> str | None:
    return EncryptionService.decrypt(ciphertext)
