"""
Pytest Configuration for LOTUS Tests

Fixtures and setup for testing LOTUS modules.
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add lotus to path
LOTUS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LOTUS_ROOT))

from lib.config import Config
from lib.message_bus import MessageBus
from lib.logging import get_logger


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def config():
    """Load test configuration"""
    config_path = LOTUS_ROOT / "config"
    return Config(config_path)


@pytest.fixture
async def message_bus(config):
    """Create message bus for tests"""
    bus = MessageBus(config.get("redis_host", "localhost"))
    yield bus
    await bus.cleanup()


@pytest.fixture
def logger():
    """Get test logger"""
    return get_logger("test")


@pytest.fixture
def temp_module_dir(tmp_path):
    """Create temporary module directory"""
    module_dir = tmp_path / "test_module"
    module_dir.mkdir()
    return module_dir


@pytest.mark.asyncio
async def test_example(message_bus):
    """Example async test"""
    assert message_bus is not None