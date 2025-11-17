"""
LOTUS - Async Event-Driven AI Architecture

A modular, event-driven system for AI agents with:
- 4-tier memory system
- Multi-provider LLM support
- Async message bus
- Dynamic module loading
"""

__version__ = "0.1.0"

from lotus.lib.module import BaseModule, ModuleMetadata
from lotus.lib.decorators import on_event, tool, periodic
from lotus.lib.config import Config
from lotus.lib.message_bus import MessageBus
from lotus.lib.logging import setup_logging, get_logger

__all__ = [
    'BaseModule',
    'ModuleMetadata',
    'on_event',
    'tool',
    'periodic',
    'Config',
    'MessageBus',
    'setup_logging',
    'get_logger',
]
