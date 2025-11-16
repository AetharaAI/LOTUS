"""
Global adapter instance for LOTUS API.
"""

from typing import Optional
from lotus.api.services.lotus_adapter import LOTUSAdapter

# Global adapter instance
_adapter: Optional[LOTUSAdapter] = None

def set_adapter(adapter: LOTUSAdapter) -> None:
    """Set the global adapter instance."""
    global _adapter
    _adapter = adapter

def get_adapter() -> LOTUSAdapter:
    """Get the global adapter instance."""
    if _adapter is None:
        raise RuntimeError("Adapter not initialized. Call set_adapter() first.")
    return _adapter