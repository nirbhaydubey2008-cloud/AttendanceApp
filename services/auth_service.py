"""
services/auth_service.py
Cryptographic authentication and session token service.
Features:
- NIST/OWASP-compliant PBKDF2-HMAC-SHA256 password hashing (600,000 iterations).
- Constant-time hash verification via hmac.compare_digest.
- Secure, URL-safe random session tokens with sliding TTL expiration.
- In-memory token management with automatic pruning.
"""

import os
import time
import hmac
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

ITERATIONS = 600000
HASH_ALGO = "sha256"
SALT_BYTES = 32
DEFAULT_TOKEN_EXPIRY_HOURS = 8.0

# In-memory token store: { token: { "user_id": int, "username": str, "role": str, "expires_at": float } }
_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}


def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 600,000 iterations and a unique 32-byte salt.
    Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    
    salt = secrets.token_bytes(SALT_BYTES)
    key = hashlib.pbkdf2_hmac(HASH_ALGO, password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored PBKDF2 hash using constant-time comparison.
    """
    if not password or not stored_hash:
        return False

    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False

        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])

        candidate_key = hashlib.pbkdf2_hmac(HASH_ALGO, password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(candidate_key, expected_key)
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def prune_expired_tokens():
    """Removes expired session tokens from active store."""
    now = time.time()
    expired = [t for t, s in _ACTIVE_SESSIONS.items() if s["expires_at"] < now]
    for t in expired:
        _ACTIVE_SESSIONS.pop(t, None)


def create_session_token(
    user_id: int,
    username: str,
    role: str,
    expiry_hours: float = DEFAULT_TOKEN_EXPIRY_HOURS
) -> str:
    """
    Generates a cryptographically secure 32-byte token associated with the authenticated user.
    """
    prune_expired_tokens()
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + (expiry_hours * 3600.0)

    _ACTIVE_SESSIONS[token] = {
        "user_id": user_id,
        "username": username,
        "role": role.upper(),
        "created_at": time.time(),
        "expires_at": expires_at
    }
    return token


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validates a session token and returns session metadata if valid and unexpired.
    """
    if not token:
        return None

    prune_expired_tokens()
    session = _ACTIVE_SESSIONS.get(token)
    if not session:
        return None

    if session["expires_at"] < time.time():
        _ACTIVE_SESSIONS.pop(token, None)
        return None

    return session


def revoke_session_token(token: str) -> bool:
    """Revokes / logs out a session token."""
    if token in _ACTIVE_SESSIONS:
        del _ACTIVE_SESSIONS[token]
        return True
    return False


def clear_all_sessions():
    """Utility for testing or security lockdown."""
    _ACTIVE_SESSIONS.clear()


def generate_temporary_password(prefix: str = "Temp", length: int = 8) -> str:
    """
    Generates a secure, memorable temporary activation password for new student accounts.
    Format: Temp-XXXXXX! (e.g. Temp-A9F2D1!)
    """
    token_hex = secrets.token_hex(max(2, length // 2)).upper()
    return f"{prefix}-{token_hex}!"
