cd /home/cory/Desktop/Lotus/lotus
# start nucleus in foreground (keeps it attached to terminal)
./venv/bin/python3 nucleus.py
# In a separate terminal (or background), publish a test prompt:
cd /home/cory/Desktop/Lotus/lotus
./venv/bin/python3 - <<'PY'
import asyncio, sys, os
sys.path.insert(0, os.getcwd())
from lib.message_bus import MessageBus
async def main():
    bus = MessageBus()
    await bus.connect()
    await bus.publish('perception.user_input', {"text": "audit stream smoke test", "context": {}})
    await asyncio.sleep(0.5)
    await bus.disconnect()
asyncio.run(main())
PY
# Inspect streams:
redis-cli xrevrange stream:debug.messages + - COUNT 10
redis-cli xrevrange stream:action.respond + - COUNT 10
# Tail the nucleus log:
tail -n 200 /home/cory/Desktop/Lotus/data/logs/nucleus.log
