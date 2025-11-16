"""
LOTUS Custom Exceptions

Defines all custom exception types used throughout the system.
"""


class LOTUSException(Exception):
    """Base exception for all LOTUS errors"""
    pass


class SystemError(LOTUSException):
    """System-level errors (initialization, shutdown, etc.)"""
    pass


class ModuleLoadError(LOTUSException):
    """Module loading and initialization errors"""

    def __init__(self, module_name: str, message: str, original_exception: Exception = None):
        self.module_name = module_name
        self.original_exception = original_exception
        super().__init__(f"Failed to load module '{module_name}': {message}")


class CircularDependencyError(ModuleLoadError):
    """Circular dependency detected in module graph"""

    def __init__(self, cycle: list):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(
            "circular_dependency",
            f"Circular dependency detected: {cycle_str}"
        )


class ConfigurationError(LOTUSException):
    """Configuration-related errors"""
    pass


class MessageBusError(LOTUSException):
    """Message bus communication errors"""
    pass


class MemoryError(LOTUSException):
    """Memory system errors"""
    pass


class ProviderError(LOTUSException):
    """LLM provider errors"""
    pass


class ValidationError(LOTUSException):
    """Input validation errors"""
    pass


class SecurityError(LOTUSException):
    """Security-related errors"""
    pass
