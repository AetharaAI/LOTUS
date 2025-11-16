"""
LOTUS Input Validators

Validation functions for various input types.
"""

import re
from typing import Any, Optional
from pathlib import Path
from urllib.parse import urlparse

from .exceptions import ValidationError


def validate_url(url: str, allowed_schemes: Optional[list] = None) -> str:
    """
    Validate URL format and scheme

    Args:
        url: URL to validate
        allowed_schemes: List of allowed schemes (default: ['http', 'https'])

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid
    """
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']

    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in allowed_schemes:
            raise ValidationError(
                f"Invalid URL scheme: {parsed.scheme}. Allowed: {allowed_schemes}"
            )

        # Check netloc exists
        if not parsed.netloc:
            raise ValidationError("URL must have a domain")

        return url

    except Exception as e:
        raise ValidationError(f"Invalid URL: {e}")


def validate_email(email: str) -> str:
    """
    Validate email address format

    Args:
        email: Email to validate

    Returns:
        Validated email

    Raises:
        ValidationError: If email is invalid
    """
    # Basic email regex (not RFC-compliant but good enough)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email address: {email}")

    return email.lower()


def validate_port(port: Any) -> int:
    """
    Validate port number

    Args:
        port: Port to validate (int or str)

    Returns:
        Valid port number

    Raises:
        ValidationError: If port is invalid
    """
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        raise ValidationError(f"Port must be an integer: {port}")

    if not (1 <= port_int <= 65535):
        raise ValidationError(f"Port must be between 1 and 65535: {port}")

    return port_int


def validate_host(host: str) -> str:
    """
    Validate hostname or IP address

    Args:
        host: Hostname or IP to validate

    Returns:
        Validated host

    Raises:
        ValidationError: If host is invalid
    """
    # Allow alphanumeric, dots, hyphens
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        raise ValidationError(f"Invalid hostname: {host}")

    # Check length
    if len(host) > 253:
        raise ValidationError("Hostname too long")

    # Check each label
    labels = host.split('.')
    for label in labels:
        if len(label) > 63:
            raise ValidationError("Hostname label too long")
        if not label or label.startswith('-') or label.endswith('-'):
            raise ValidationError(f"Invalid hostname label: {label}")

    return host


def validate_path(path: str, must_exist: bool = False,
                 must_be_file: bool = False,
                 must_be_dir: bool = False) -> Path:
    """
    Validate file system path

    Args:
        path: Path to validate
        must_exist: Whether path must exist
        must_be_file: Whether path must be a file
        must_be_dir: Whether path must be a directory

    Returns:
        Valid Path object

    Raises:
        ValidationError: If path is invalid
    """
    try:
        path_obj = Path(path)
    except Exception as e:
        raise ValidationError(f"Invalid path: {e}")

    if must_exist and not path_obj.exists():
        raise ValidationError(f"Path does not exist: {path}")

    if must_be_file and not path_obj.is_file():
        raise ValidationError(f"Path is not a file: {path}")

    if must_be_dir and not path_obj.is_dir():
        raise ValidationError(f"Path is not a directory: {path}")

    return path_obj


def validate_json(data: Any, schema: Optional[dict] = None) -> Any:
    """
    Validate JSON data structure

    Args:
        data: Data to validate
        schema: Optional schema dict (basic validation)

    Returns:
        Validated data

    Raises:
        ValidationError: If data is invalid
    """
    if schema is None:
        return data

    # Basic schema validation (not full JSON Schema)
    if 'type' in schema:
        expected_type = schema['type']

        type_map = {
            'object': dict,
            'array': list,
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'null': type(None)
        }

        if expected_type in type_map:
            expected = type_map[expected_type]
            if not isinstance(data, expected):
                raise ValidationError(
                    f"Expected {expected_type}, got {type(data).__name__}"
                )

    # Validate required fields
    if isinstance(data, dict) and 'required' in schema:
        for field in schema['required']:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")

    # Validate properties
    if isinstance(data, dict) and 'properties' in schema:
        for key, value_schema in schema['properties'].items():
            if key in data:
                validate_json(data[key], value_schema)

    return data


def validate_module_name(name: str) -> str:
    """
    Validate module name format

    Args:
        name: Module name to validate

    Returns:
        Validated module name

    Raises:
        ValidationError: If name is invalid
    """
    # Module names: lowercase, alphanumeric, underscores
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        raise ValidationError(
            f"Invalid module name: {name}. "
            "Must start with lowercase letter and contain only lowercase letters, "
            "numbers, and underscores."
        )

    # Prevent reserved names
    reserved = ['lib', 'config', 'data', 'tests', 'scripts']
    if name in reserved:
        raise ValidationError(f"Reserved module name: {name}")

    return name


def validate_event_name(name: str) -> str:
    """
    Validate event name format

    Args:
        name: Event name to validate

    Returns:
        Validated event name

    Raises:
        ValidationError: If name is invalid
    """
    # Event names: module.action (supports wildcards)
    pattern = r'^[a-z][a-z0-9_]*(\.[a-z*][a-z0-9_*]*)*$'

    if not re.match(pattern, name):
        raise ValidationError(
            f"Invalid event name: {name}. "
            "Format: module.action (e.g., 'perception.file_changed' or 'perception.*')"
        )

    return name


def validate_config_value(value: Any, value_type: str) -> Any:
    """
    Validate configuration value

    Args:
        value: Value to validate
        value_type: Expected type ('string', 'int', 'float', 'bool', 'list', 'dict')

    Returns:
        Validated and converted value

    Raises:
        ValidationError: If value is invalid
    """
    type_map = {
        'string': str,
        'int': int,
        'float': float,
        'bool': bool,
        'list': list,
        'dict': dict
    }

    if value_type not in type_map:
        raise ValidationError(f"Unknown type: {value_type}")

    expected_type = type_map[value_type]

    # Try to convert
    try:
        if value_type == 'bool' and isinstance(value, str):
            # Special handling for bool strings
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError()

        if isinstance(value, expected_type):
            return value
        else:
            return expected_type(value)

    except (ValueError, TypeError):
        raise ValidationError(
            f"Cannot convert {value} to {value_type}"
        )
