"""
Global adapter instance for LOTUS API.

Provides access to the Nucleus adapter from route handlers.
"""

from typing import Optional

# Global adapter instance
_adapter = None


def set_adapter(adapter) -> None:
    """Set the global adapter instance."""
    global _adapter
    _adapter = adapter


def get_adapter():
    """Get the global adapter instance."""
    if _adapter is None:
        raise RuntimeError("Adapter not initialized. Call set_adapter() first.")
    return _adapter
