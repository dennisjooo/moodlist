import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_EXPIRATION_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_EXPIRATION_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(password, hashed)


def hash_token(token: str) -> str:
    """Hash a token using bcrypt for secure storage.

    Note: This is ONE-WAY hashing. The original token cannot be retrieved.
    Use this for storing tokens when you only need to verify them later
    (similar to password hashing).

    Args:
        token: The token to hash

    Returns:
        The hashed token as a string
    """
    # Convert token to bytes and hash it
    token_bytes = token.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(token_bytes, salt)
    return hashed.decode("utf-8")


def verify_hashed_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a plain token against its hashed version.

    Args:
        plain_token: The plain text token to verify
        hashed_token: The hashed token to compare against

    Returns:
        True if the token matches the hash, False otherwise
    """
    plain_bytes = plain_token.encode("utf-8")
    hashed_bytes = hashed_token.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def generate_session_token() -> str:
    """Generate a secure session token."""
    import secrets

    return secrets.token_urlsafe(32)
