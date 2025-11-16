"""
LOTUS Utility Functions

Common utilities used throughout the system.
"""

import uuid
import yaml
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID

    Args:
        prefix: Optional prefix for the ID

    Returns:
        Unique identifier string
    """
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def timestamp_now() -> str:
    """
    Get current timestamp in ISO format

    Returns:
        ISO formatted timestamp string
    """
    return datetime.now(timezone.utc).isoformat()


def timestamp_unix() -> float:
    """
    Get current Unix timestamp

    Returns:
        Unix timestamp (seconds since epoch)
    """
    return datetime.now(timezone.utc).timestamp()


def parse_yaml(file_path: str) -> Dict[str, Any]:
    """
    Parse a YAML file

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed YAML as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def parse_json(file_path: str) -> Dict[str, Any]:
    """
    Parse a JSON file

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON as dictionary
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(path, 'r') as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison

    Args:
        text: Input text

    Returns:
        Normalized text (lowercase, stripped, single spaces)
    """
    if not text:
        return ""

    # Convert to lowercase, strip whitespace, collapse multiple spaces
    normalized = ' '.join(text.lower().strip().split())
    return normalized


def hash_text(text: str, algorithm: str = "sha256") -> str:
    """
    Hash text using specified algorithm

    Args:
        text: Text to hash
        algorithm: Hash algorithm (md5, sha1, sha256, etc.)

    Returns:
        Hex digest of hash
    """
    hasher = hashlib.new(algorithm)
    hasher.update(text.encode('utf-8'))
    return hasher.hexdigest()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries

    Args:
        dict1: Base dictionary
        dict2: Dictionary to merge (overwrites dict1)

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def safe_get(data: Dict, key_path: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary value using dot notation

    Args:
        data: Dictionary to search
        key_path: Dot-separated key path (e.g., "a.b.c")
        default: Default value if key not found

    Returns:
        Value at key path or default

    Example:
        >>> data = {"a": {"b": {"c": 123}}}
        >>> safe_get(data, "a.b.c")
        123
        >>> safe_get(data, "a.b.x", "default")
        'default'
    """
    keys = key_path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def format_size(size_bytes: int) -> str:
    """
    Format byte size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def ensure_dir(path: str) -> Path:
    """
    Ensure directory exists, create if needed

    Args:
        path: Directory path

    Returns:
        Path object for the directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path
