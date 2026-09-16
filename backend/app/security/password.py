"""bcrypt password hashing helpers."""

import bcrypt


_BCRYPT_MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    value = password.encode("utf-8")
    if not value:
        raise ValueError("password must not be empty")
    if len(value) > _BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("password must not exceed 72 UTF-8 bytes")
    return value


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash; the original password is never retained."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a candidate without leaking malformed-hash failures."""
    try:
        return bcrypt.checkpw(
            _password_bytes(password),
            password_hash.encode("ascii"),
        )
    except (ValueError, UnicodeEncodeError):
        return False
