"""
LOTUS Logging System

Centralized logging configuration with color output and structured logging.
"""

import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime


# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Log levels
    DEBUG = '\033[36m'      # Cyan
    INFO = '\033[32m'       # Green
    WARNING = '\033[33m'    # Yellow
    ERROR = '\033[31m'      # Red
    CRITICAL = '\033[35m'   # Magenta

    # Components
    TIMESTAMP = '\033[90m'  # Gray
    MODULE = '\033[94m'     # Blue


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emoji"""

    LEVEL_EMOJI = {
        'DEBUG': '🔍',
        'INFO': '✨',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥'
    }

    LEVEL_COLORS = {
        'DEBUG': Colors.DEBUG,
        'INFO': Colors.INFO,
        'WARNING': Colors.WARNING,
        'ERROR': Colors.ERROR,
        'CRITICAL': Colors.CRITICAL
    }

    def format(self, record):
        # Get emoji and color for this level
        emoji = self.LEVEL_EMOJI.get(record.levelname, '📝')
        color = self.LEVEL_COLORS.get(record.levelname, Colors.RESET)

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')

        # Format the log message
        message = super().format(record)

        # Construct colored output
        output = (
            f"{Colors.TIMESTAMP}{timestamp}{Colors.RESET} "
            f"{emoji} "
            f"{Colors.MODULE}{record.name:20s}{Colors.RESET} "
            f"{color}{message}{Colors.RESET}"
        )

        return output


# Global logger registry
_loggers: Dict[str, logging.Logger] = {}
_log_level = logging.INFO
_log_file: Optional[str] = None


def setup_logging(config: Any = None) -> logging.Logger:
    """
    Setup the logging system

    Args:
        config: Configuration object (optional)

    Returns:
        Root logger instance
    """
    global _log_level, _log_file

    # Get configuration
    if config:
        _log_level = getattr(logging, config.get('logging.level', 'INFO').upper())
        _log_file = config.get('logging.file')

    # Create root logger
    root_logger = logging.getLogger('lotus')
    root_logger.setLevel(_log_level)
    root_logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_log_level)
    console_handler.setFormatter(ColoredFormatter('%(message)s'))
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    if _log_file:
        file_handler = logging.FileHandler(_log_file)
        file_handler.setLevel(_log_level)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger for a specific component

    Args:
        name: Logger name (usually module name)

    Returns:
        Logger instance
    """
    if name not in _loggers:
        logger = logging.getLogger(f'lotus.{name}')
        logger.setLevel(_log_level)
        _loggers[name] = logger

    return _loggers[name]


def set_log_level(level: str) -> None:
    """Set global log level"""
    global _log_level
    _log_level = getattr(logging, level.upper())

    # Update all existing loggers
    for logger in _loggers.values():
        logger.setLevel(_log_level)
