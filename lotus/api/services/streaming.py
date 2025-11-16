"""
SSE Streaming Service

Handles Server-Sent Events for real-time chat streaming.
"""

import json
import asyncio
from typing import AsyncIterator, Dict, Any


async def sse_stream(event_generator: AsyncIterator[Dict[str, Any]]) -> AsyncIterator[str]:
    """
    Convert async generator to SSE format

    Args:
        event_generator: Async generator yielding event dicts

    Yields:
        SSE-formatted strings
    """
    try:
        async for event in event_generator:
            # Format as SSE
            data = json.dumps(event)
            yield f"data: {data}\n\n"

    except Exception as e:
        # Send error event
        error_event = {
            "type": "error",
            "error": str(e)
        }
        yield f"data: {json.dumps(error_event)}\n\n"

    finally:
        # Send completion signal
        yield "data: [DONE]\n\n"


async def heartbeat_stream(interval: int = 15) -> AsyncIterator[str]:
    """
    Generate heartbeat events to keep connection alive

    Args:
        interval: Seconds between heartbeats

    Yields:
        SSE heartbeat comments
    """
    while True:
        await asyncio.sleep(interval)
        yield ": heartbeat\n\n"
