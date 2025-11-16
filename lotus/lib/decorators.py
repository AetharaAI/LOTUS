"""
LOTUS Decorators

Decorators for module event handling, tool registration, and periodic tasks.
"""

import asyncio
import functools
from typing import Callable, Any, Optional


def on_event(event_pattern: str):
    """
    Decorator to mark a method as an event handler

    Args:
        event_pattern: Event pattern to subscribe to (supports wildcards: "perception.*")

    Usage:
        @on_event("perception.file_changed")
        async def handle_file_changed(self, event_data):
            # Handle the event
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function
        func._lotus_event_handler = event_pattern

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


def tool(name: Optional[str] = None, description: str = ""):
    """
    Decorator to mark a method as a callable tool

    Args:
        name: Tool name (defaults to function name)
        description: Tool description

    Usage:
        @tool("analyze_file")
        async def analyze_file(self, file_path: str) -> dict:
            # Analyze file and return results
            return {"status": "success"}
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__

        # Store metadata on the function
        func._lotus_tool = {
            'name': tool_name,
            'description': description or func.__doc__ or "",
            'function': func
        }

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await func(self, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)

        return wrapper

    return decorator


def periodic(interval: float):
    """
    Decorator to mark a method as a periodic task

    Args:
        interval: Interval in seconds between executions

    Usage:
        @periodic(60)  # Run every 60 seconds
        async def check_health(self):
            # Perform health check
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function
        func._lotus_periodic = {
            'interval': interval,
            'function': func
        }

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


def setup_module_decorators(module_instance: Any) -> None:
    """
    Setup decorators for a module instance

    This function scans a module instance for decorated methods and
    registers them appropriately (event handlers, tools, periodic tasks).

    Args:
        module_instance: Instance of a BaseModule subclass
    """
    # Scan all methods for decorators
    for attr_name in dir(module_instance):
        if attr_name.startswith('_'):
            continue

        attr = getattr(module_instance, attr_name)

        # Check for event handler decorator
        if hasattr(attr, '_lotus_event_handler'):
            event_pattern = attr._lotus_event_handler
            module_instance.register_event_handler(event_pattern, attr)

            # Also subscribe on the message bus
            asyncio.create_task(
                module_instance.subscribe(event_pattern, attr)
            )

        # Check for tool decorator
        if hasattr(attr, '_lotus_tool'):
            tool_info = attr._lotus_tool
            module_instance.register_tool(tool_info['name'], attr)

        # Check for periodic decorator
        if hasattr(attr, '_lotus_periodic'):
            periodic_info = attr._lotus_periodic
            interval = periodic_info['interval']

            # Create periodic task
            async def run_periodic_task(func=attr, interval_seconds=interval):
                """Wrapper to run periodic task"""
                while module_instance.is_running:
                    try:
                        await func()
                    except Exception as e:
                        module_instance.logger.error(
                            f"Error in periodic task {func.__name__}: {e}"
                        )
                    await asyncio.sleep(interval_seconds)

            # Start the periodic task
            task = asyncio.create_task(run_periodic_task())
            module_instance._periodic_tasks.append(task)
