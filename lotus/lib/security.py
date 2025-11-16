"""
LOTUS Security Utilities

Security functions for input validation, sanitization, and protection.
"""

import re
import hashlib
import secrets
from typing import Any, Optional
from pathlib import Path

from .exceptions import SecurityError


def validate_input(text: str, max_length: int = 10000, allow_special_chars: bool = True) -> str:
    """
    Validate and sanitize text input

    Args:
        text: Input text to validate
        max_length: Maximum allowed length
        allow_special_chars: Whether to allow special characters

    Returns:
        Validated text

    Raises:
        SecurityError: If validation fails
    """
    if not isinstance(text, str):
        raise SecurityError("Input must be a string")

    if len(text) > max_length:
        raise SecurityError(f"Input exceeds maximum length of {max_length}")

    # Check for null bytes
    if '\x00' in text:
        raise SecurityError("Null bytes not allowed in input")

    # Optionally restrict special characters
    if not allow_special_chars:
        if not re.match(r'^[a-zA-Z0-9\s\.,!?-]*$', text):
            raise SecurityError("Invalid characters in input")

    return text


def sanitize_path(path: str, base_dir: Optional[str] = None) -> Path:
    """
    Sanitize file path to prevent directory traversal

    Args:
        path: Path to sanitize
        base_dir: Base directory to restrict to (optional)

    Returns:
        Sanitized Path object

    Raises:
        SecurityError: If path is invalid or outside base_dir
    """
    # Convert to Path and resolve
    try:
        sanitized = Path(path).resolve()
    except Exception as e:
        raise SecurityError(f"Invalid path: {e}")

    # Check for directory traversal
    if base_dir:
        base = Path(base_dir).resolve()
        try:
            sanitized.relative_to(base)
        except ValueError:
            raise SecurityError(f"Path outside allowed directory: {path}")

    return sanitized


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent injection attacks

    Args:
        filename: Filename to sanitize

    Returns:
        Safe filename

    Raises:
        SecurityError: If filename is invalid
    """
    # Remove path separators
    filename = filename.replace('/', '').replace('\\', '')

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Allow only alphanumeric, dots, dashes, underscores
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        raise SecurityError(f"Invalid filename: {filename}")

    # Prevent hidden files (starting with .)
    if filename.startswith('.'):
        raise SecurityError("Hidden filenames not allowed")

    # Prevent reserved names (Windows)
    reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                'LPT1', 'LPT2', 'LPT3']
    if filename.upper() in reserved:
        raise SecurityError(f"Reserved filename: {filename}")

    return filename


def generate_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token

    Args:
        length: Token length in bytes

    Returns:
        Hex-encoded token
    """
    return secrets.token_hex(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """
    Hash password with salt

    Args:
        password: Password to hash
        salt: Salt (generated if not provided)

    Returns:
        Tuple of (hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    # Use PBKDF2 for password hashing
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # iterations
    )

    return hash_obj.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Verify password against hash

    Args:
        password: Password to verify
        password_hash: Expected hash
        salt: Salt used for hashing

    Returns:
        True if password matches
    """
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, password_hash)


def sanitize_json(data: Any, max_depth: int = 10, current_depth: int = 0) -> Any:
    """
    Sanitize JSON data to prevent DoS attacks

    Args:
        data: JSON data to sanitize
        max_depth: Maximum nesting depth
        current_depth: Current nesting level (internal)

    Returns:
        Sanitized data

    Raises:
        SecurityError: If data exceeds max depth
    """
    if current_depth > max_depth:
        raise SecurityError(f"JSON depth exceeds maximum of {max_depth}")

    if isinstance(data, dict):
        return {
            k: sanitize_json(v, max_depth, current_depth + 1)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [
            sanitize_json(item, max_depth, current_depth + 1)
            for item in data
        ]
    else:
        return data


def check_rate_limit(identifier: str, max_requests: int = 100,
                     window_seconds: int = 60, store: dict = None) -> bool:
    """
    Simple in-memory rate limiting

    Args:
        identifier: Unique identifier (IP, user ID, etc.)
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
        store: Storage dict (for testing, uses global dict if None)

    Returns:
        True if request allowed, False if rate limited

    Note: This is a simple in-memory implementation.
    For production, use Redis-based rate limiting.
    """
    import time

    if store is None:
        if not hasattr(check_rate_limit, '_store'):
            check_rate_limit._store = {}
        store = check_rate_limit._store

    now = time.time()

    # Clean up old entries
    store[identifier] = [
        timestamp for timestamp in store.get(identifier, [])
        if now - timestamp < window_seconds
    ]

    # Check limit
    if len(store[identifier]) >= max_requests:
        return False

    # Record request
    store[identifier].append(now)
    return True
