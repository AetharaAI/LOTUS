"""
UnityKernel Config Manager

Hot-reloadable configuration system with schema validation.
Supports YAML, JSON, and environment variable overrides.
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import yaml
import json
from datetime import datetime

from .types import Event, EventType


class ConfigManager:
    """
    Configuration management with hot-reload support

    Features:
    - Load from YAML/JSON
    - Environment variable overrides (UNITY_KEY_NAME)
    - Schema validation
    - Hot-reload without restart
    - Change notifications via events
    """

    def __init__(self, config_path: str, event_bus: Optional[any] = None):
        """
        Initialize config manager

        Args:
            config_path: Path to config file or directory
            event_bus: Event bus for change notifications
        """
        self.config_path = Path(config_path)
        self.event_bus = event_bus

        # Configuration data
        self.config: Dict[str, Any] = {}
        self.schema: Dict[str, Any] = {}

        # Change tracking
        self.last_modified: Optional[datetime] = None
        self.change_listeners: List[Callable] = []

        # Hot-reload
        self.watch_task: Optional[asyncio.Task] = None
        self.watching = False

    async def load(self) -> None:
        """Load configuration from file"""
        if self.config_path.is_dir():
            # Load all config files from directory
            await self._load_directory()
        else:
            # Load single config file
            await self._load_file(self.config_path)

        # Apply environment variable overrides
        self._apply_env_overrides()

        # Validate against schema
        self._validate()

        # Track modification time
        if self.config_path.exists():
            self.last_modified = datetime.fromtimestamp(
                self.config_path.stat().st_mtime
            )

        print(f"✓ Configuration loaded from {self.config_path}")

    async def _load_file(self, file_path: Path) -> None:
        """Load a single config file"""
        if not file_path.exists():
            print(f"⚠ Config file not found: {file_path}, using defaults")
            self.config = self._get_defaults()
            return

        with open(file_path, 'r') as f:
            if file_path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif file_path.suffix == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {file_path.suffix}")

        # Merge with existing config
        self._deep_merge(self.config, data or {})

    async def _load_directory(self) -> None:
        """Load all config files from directory"""
        config_dir = self.config_path

        # Load in order: defaults, system, modules, local
        load_order = [
            'defaults.yaml',
            'system.yaml',
            'modules.yaml',
            'local.yaml'  # Local overrides (gitignored)
        ]

        for filename in load_order:
            file_path = config_dir / filename
            if file_path.exists():
                await self._load_file(file_path)

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        # UNITY_KEY_NAME -> key.name in config
        for key, value in os.environ.items():
            if key.startswith('UNITY_'):
                config_key = key[6:].lower().replace('_', '.')
                self.set(config_key, value)

    def _validate(self) -> None:
        """Validate configuration against schema"""
        if not self.schema:
            return  # No schema defined

        # Basic validation (can be extended with jsonschema)
        for key, schema in self.schema.items():
            if schema.get('required', False):
                if not self.has(key):
                    raise ValueError(f"Required config key missing: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key: Configuration key (e.g., "redis.host")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        current = self.config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def set(self, key: str, value: Any, notify: bool = True) -> None:
        """
        Set configuration value using dot notation

        Args:
            key: Configuration key
            value: Value to set
            notify: Whether to notify listeners of change
        """
        keys = key.split('.')
        current = self.config

        # Navigate to parent
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set value
        old_value = current.get(keys[-1])
        current[keys[-1]] = value

        # Notify listeners if value changed
        if notify and old_value != value:
            self._notify_change(key, old_value, value)

    def has(self, key: str) -> bool:
        """Check if configuration key exists"""
        return self.get(key) is not None

    def _notify_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify listeners of configuration change"""
        # Call registered listeners
        for listener in self.change_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    asyncio.create_task(listener(key, old_value, new_value))
                else:
                    listener(key, old_value, new_value)
            except Exception as e:
                print(f"⚠ Config change listener error: {e}")

        # Publish event if bus available
        if self.event_bus:
            event = Event(
                event_type=EventType.CONFIG_CHANGED.value,
                source="config_manager",
                data={
                    'key': key,
                    'old_value': str(old_value),
                    'new_value': str(new_value)
                }
            )
            asyncio.create_task(self.event_bus.publish(event, persist=False))

    def on_change(self, listener: Callable) -> None:
        """Register a change listener"""
        self.change_listeners.append(listener)

    async def start_watching(self, interval: float = 1.0) -> None:
        """
        Start watching config file for changes

        Args:
            interval: Check interval in seconds
        """
        self.watching = True
        self.watch_task = asyncio.create_task(self._watch_loop(interval))
        print(f"✓ Config hot-reload enabled (checking every {interval}s)")

    async def stop_watching(self) -> None:
        """Stop watching config file"""
        self.watching = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass

    async def _watch_loop(self, interval: float) -> None:
        """Background task that watches for config changes"""
        while self.watching:
            try:
                await asyncio.sleep(interval)

                # Check if file was modified
                if self.config_path.exists():
                    current_mtime = datetime.fromtimestamp(
                        self.config_path.stat().st_mtime
                    )

                    if self.last_modified and current_mtime > self.last_modified:
                        print(f"🔄 Config file changed, reloading...")
                        await self.reload()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠ Config watch error: {e}")

    async def reload(self) -> None:
        """Reload configuration from file"""
        old_config = self.config.copy()
        self.config = {}

        await self.load()

        # Publish reload event
        if self.event_bus:
            event = Event(
                event_type=EventType.CONFIG_RELOADED.value,
                source="config_manager",
                data={
                    'timestamp': datetime.utcnow().isoformat(),
                    'changes': self._diff_configs(old_config, self.config)
                }
            )
            await self.event_bus.publish(event, persist=False)

    def _diff_configs(self, old: Dict, new: Dict) -> List[str]:
        """Get list of changed keys"""
        changes = []

        # Check all keys in both configs
        all_keys = set(self._flatten_dict(old).keys()) | set(self._flatten_dict(new).keys())

        for key in all_keys:
            old_val = self._get_nested(old, key)
            new_val = self._get_nested(new, key)
            if old_val != new_val:
                changes.append(key)

        return changes

    def _flatten_dict(self, d: Dict, parent_key: str = '') -> Dict:
        """Flatten nested dict to dot notation"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _get_nested(self, d: Dict, key: str) -> Any:
        """Get nested value using dot notation"""
        keys = key.split('.')
        current = d
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current

    def _deep_merge(self, target: Dict, source: Dict) -> None:
        """Deep merge source dict into target dict"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'kernel': {
                'name': 'unity_kernel',
                'version': '0.1.0',
                'log_level': 'INFO'
            },
            'event_bus': {
                'redis_url': None,  # Optional
                'enable_streams': True
            },
            'priority_processor': {
                'workers': {
                    'critical': 4,
                    'high': 8,
                    'normal': 16,
                    'low': 4,
                    'deferred': 2
                }
            },
            'modules': {
                'auto_discover': True,
                'discovery_paths': ['./modules'],
                'auto_load_core': True
            },
            'health': {
                'check_interval': 30,
                'degraded_threshold': 0.7,
                'restart_failed_modules': True
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return self.config.copy()

    def save(self, path: Optional[Path] = None) -> None:
        """
        Save configuration to file

        Args:
            path: Optional path to save to (defaults to original path)
        """
        save_path = path or self.config_path

        with open(save_path, 'w') as f:
            if save_path.suffix in ['.yaml', '.yml']:
                yaml.dump(self.config, f, default_flow_style=False)
            elif save_path.suffix == '.json':
                json.dump(self.config, f, indent=2)

        print(f"✓ Configuration saved to {save_path}")
