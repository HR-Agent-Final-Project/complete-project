"""
At-rest encryption for biometric data (face embeddings).

Uses AES-256-GCM (authenticated encryption) so any tampering with the
ciphertext in the database is detected and rejected on read.

Architecture
────────────
  • A dedicated BIOMETRIC_ENCRYPTION_KEY setting (separate from SECRET_KEY)
    is derived via HKDF into a 256-bit AES key at startup.
  • EncryptedJSON is a SQLAlchemy TypeDecorator that transparently encrypts
    on write and decrypts on read — no changes needed in service code.
  • Each encrypted value has its own random 96-bit nonce prepended, so
    two writes of the same plaintext produce different ciphertext.
  • Wire format (stored as base64 in a Text column):
      [ 12 bytes nonce ][ N bytes AES-GCM ciphertext + 16-byte tag ]

Key separation
──────────────
  BIOMETRIC_ENCRYPTION_KEY  →  HKDF  →  AES-256-GCM key
  SECRET_KEY                →  JWT signing (completely separate)

A compromise of one key does NOT expose the other.
"""

import base64
import json
import logging
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import types

logger = logging.getLogger(__name__)

# HKDF context labels — changing these invalidates all existing ciphertext.
_HKDF_SALT = b"aihr_biometric_v1"
_HKDF_INFO = b"face_embedding_aes256gcm"


@lru_cache(maxsize=1)
def _derive_aes_key() -> bytes:
    """
    Derive a 256-bit AES key from BIOMETRIC_ENCRYPTION_KEY using HKDF-SHA256.

    Cached after first call so key derivation runs exactly once per process.
    Raises RuntimeError if BIOMETRIC_ENCRYPTION_KEY is not configured.
    """
    from app.core.config import settings

    master = settings.BIOMETRIC_ENCRYPTION_KEY
    if not master:
        raise RuntimeError(
            "BIOMETRIC_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    hkdf = HKDF(
        algorithm=SHA256(),
        length=32,           # 256-bit AES key
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    )
    return hkdf.derive(master.encode())


class EncryptedJSON(types.TypeDecorator):
    """
    SQLAlchemy column type that transparently encrypts JSON data at rest.

    Usage in a model:
        from app.core.encryption import EncryptedJSON
        face_embedding = Column(EncryptedJSON, nullable=True)

    On INSERT/UPDATE : Python object  →  JSON  →  AES-256-GCM  →  base64 Text
    On SELECT        : base64 Text   →  AES-256-GCM decrypt  →  JSON  →  Python object

    If decryption fails (e.g. corrupted row, or a pre-encryption plaintext
    value that was written before this migration), None is returned so the
    application can handle re-enrollment gracefully rather than crashing.
    """

    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt before writing to the database."""
        if value is None:
            return None

        key = _derive_aes_key()
        plaintext = json.dumps(value).encode()
        nonce = os.urandom(12)          # 96-bit random nonce per write
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        # Prepend nonce so decryption can always find it
        return base64.b64encode(nonce + ciphertext).decode()

    def process_result_value(self, value, dialect):
        """Decrypt when reading from the database."""
        if value is None:
            return None

        try:
            raw = base64.b64decode(value.encode())
            nonce, ciphertext = raw[:12], raw[12:]
            key = _derive_aes_key()
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(plaintext)
        except Exception:
            # Log at WARNING — this is expected for rows written before
            # encryption was enabled (they will need re-enrollment).
            logger.warning(
                "Face embedding decryption failed for a DB row. "
                "The value may have been written before encryption was enabled "
                "and will need re-enrollment."
            )
            return None
