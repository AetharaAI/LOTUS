"""
LOTUS Configuration Management

Handles loading and accessing system configuration from YAML files.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from .exceptions import ConfigurationError
from .utils import deep_merge, safe_get


class Config:
    """
    Configuration manager for LOTUS

    Loads configuration from YAML files and provides easy access to settings.
    Supports:
    - Nested configuration access via dot notation
    - Environment variable overrides
    - Default values
    - Configuration merging
    - Runtime service registration
    """

    def __init__(self, config_path: str = "config/system.yaml"):
        """
        Initialize configuration

        Args:
            config_path: Path to main configuration file or directory
        """
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
        self._loaded = False

    async def load(self) -> None:
        """
        Load configuration from file(s)

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        try:
            # If config_path is a directory, load system.yaml from it
            if self.config_path.is_dir():
                config_file = self.config_path / "system.yaml"
            else:
                config_file = self.config_path

            # Load main configuration
            if config_file.exists():
                with open(config_file, 'r') as f:
                    self.data = yaml.safe_load(f) or {}
            else:
                # Create default configuration
                self.data = self._get_default_config()

            # Load provider configuration if it exists
            if self.config_path.is_dir():
                provider_file = self.config_path / "providers.yaml"
                if provider_file.exists():
                    with open(provider_file, 'r') as f:
                        provider_config = yaml.safe_load(f) or {}
                        self.data = deep_merge(self.data, provider_config)

            # Apply environment variable overrides
            self._apply_env_overrides()

            self._loaded = True

        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if no file exists"""
        return {
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'memory': {
                'working_memory': {
                    'ttl_seconds': 600,
                    'max_items': 100
                },
                'short_term': {
                    'ttl_hours': 24,
                    'max_items': 1000
                },
                'long_term': {
                    'collection_name': 'lotus_memories',
                    'embedding_model': 'all-MiniLM-L6-v2'
                },
                'persistent': {
                    'table_name': 'lotus_knowledge'
                }
            },
            'providers': {
                'anthropic': {'enabled': False},
                'openai': {'enabled': False},
                'ollama': {'enabled': False}
            },
            'system': {
                'personality': 'ash',
                'max_iterations': 6
            },
            'logging': {
                'level': 'INFO'
            }
        }

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        # Example: LOTUS_REDIS_HOST overrides redis.host
        # Example: LOTUS_PROVIDERS_ANTHROPIC_API_KEY overrides providers.anthropic.api_key

        for key, value in os.environ.items():
            if key.startswith('LOTUS_'):
                # Convert LOTUS_REDIS_HOST to redis.host
                config_key = key[6:].lower().replace('_', '.')
                self.set(config_key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key: Configuration key (e.g., "redis.host")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get("redis.host")
            'localhost'
            >>> config.get("redis.port", 6379)
            6379
        """
        # Check services first (for runtime-registered services)
        if key.startswith('services.'):
            service_name = key.split('.', 1)[1]
            if service_name in self._services:
                return self._services[service_name]

        # Get from config data
        return safe_get(self.data, key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation

        Args:
            key: Configuration key (e.g., "redis.host")
            value: Value to set
        """
        keys = key.split('.')
        current = self.data

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value

    def register_service(self, name: str, service: Any) -> None:
        """
        Register a runtime service (like database connections)

        Args:
            name: Service name
            service: Service instance
        """
        self._services[name] = service

    def get_service(self, name: str) -> Optional[Any]:
        """
        Get a registered service

        Args:
            name: Service name

        Returns:
            Service instance or None
        """
        return self._services.get(name)

    def has(self, key: str) -> bool:
        """
        Check if configuration key exists

        Args:
            key: Configuration key

        Returns:
            True if key exists
        """
        return safe_get(self.data, key, None) is not None

    def to_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary

        Returns:
            Complete configuration dictionary
        """
        return self.data.copy()
