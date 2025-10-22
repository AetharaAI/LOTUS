# test_publish.py
import asyncio
from lib.message_bus import MessageBus

async def send_test():
    bus = MessageBus()
    await bus.connect()
    await bus.publish("perception.user_input", {"text": "hello from test script", "context": {"source": "manual_test"}})
    await bus.disconnect()

asyncio.run(send_test())