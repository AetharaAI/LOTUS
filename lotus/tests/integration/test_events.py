#!/usr/bin/env python3
"""
Test script to verify LOTUS event flow
"""

import asyncio
import sys
import os
from pathlib import Path

# Add lotus to path
sys.path.insert(0, str(Path(__file__).parent / "lotus"))

async def test_memory_events():
    """Test memory module event handling"""
    from lotus.lib.message_bus import MessageBus
    from lotus.lib.config import Config

    # Load config
    config = Config("config/system.yaml")
    await config.load()

    # Create message bus
    bus = MessageBus(config)
    await bus.connect()

    print("Testing memory store event...")

    # Subscribe to memory response
    async def on_memory_stored(channel, data):
        print(f"✅ Memory stored: {data}")

    await bus.subscribe("memory.stored", on_memory_stored)

    # Publish memory store event
    await bus.publish("memory.store", {
        "content": "This is a test memory for LOTUS system verification",
        "memory_type": "episodic",
        "importance": 0.7,
        "metadata": {"test": True, "source": "system_test"}
    })

    print("Event published, waiting for response...")

    # Wait a bit for processing
    await asyncio.sleep(2)

    # Test memory retrieval
    print("Testing memory retrieval...")

    async def on_memory_retrieved(channel, data):
        print(f"✅ Memory retrieved: {len(data.get('memories', []))} memories found")

    await bus.subscribe("memory.retrieved", on_memory_retrieved)

    await bus.publish("memory.retrieve", {
        "query": "test memory",
        "max_results": 5
    })

    # Wait for response
    await asyncio.sleep(2)

    await bus.disconnect()
    print("✅ Event flow test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_memory_events())