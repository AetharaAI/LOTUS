# LOTUS - Quick Start After Session 2

**You now have a working AI Operating System with real modules!**

---

## [FAST] QUICKEST PATH TO RUNNING LOTUS

### 1. Install Dependencies (2 minutes)

```bash
cd lotus
pip install redis psycopg[binary] chromadb watchdog pyperclip anthropic openai
```

### 2. Start Redis (30 seconds)

```bash
# Option A: Direct
redis-server

# Option B: Docker
docker run -d -p 6379:6379 redis:7-alpine

# Option C: Homebrew (macOS)
brew services start redis
```

### 3. Test LOTUS (1 minute)

```bash
python test_lotus.py
```

**Expected Output:**
```
LOTUS starting up...
   Found 4 modules
   Loading modules...
   [DONE] Loaded: memory
   [DONE] Loaded: providers
   [DONE] Loaded: perception
   [DONE] Loaded: reasoning

LOTUS is online! Running tests...

[Various test outputs]

Test complete! LOTUS is offline.
```

---

## [INFO] WHAT JUST HAPPENED?

### Modules That Loaded:

1. **Memory Module** [STORAGE]
   - 4-tier memory system active
   - Can store and retrieve memories
   - Automatic consolidation running

2. **Provider Module** [LLM-ACCESS]
   - Claude, GPT, Ollama ready
   - Smart routing enabled
   - Fallback chains configured

3. **Perception Module** [AWARENESS]
   - File watching active
   - Clipboard monitoring running
   - Context inference enabled

4. **Reasoning Module** [BRAIN]
   - ReAct loop ready
   - Tool execution available
   - Memory integration active

### What You Can Do Now:

[DONE] Store memories across sessions  
[DONE] Call any LLM (Claude, GPT, local)  
[DONE] Watch files in real-time  
[DONE] Monitor clipboard  
[DONE] Event-driven communication  

---

## [TEST] INTERACTIVE TESTING

### Test Memory System

```python
import asyncio
from nucleus import Nucleus

async def test_memory():
    nucleus = Nucleus()
    await nucleus.boot()
    
    # Store a memory
    await nucleus.message_bus.publish("memory.store", {
        "content": "LOTUS is revolutionary!",
        "metadata": {
            "type": "fact",
            "importance": 0.9
        },
        "tier": "L3"  # Long-term memory
    })
    
    await asyncio.sleep(1)
    
    # Retrieve it
    await nucleus.message_bus.publish("memory.retrieve", {
        "query": "revolutionary",
        "tier": "all"
    })
    
    await asyncio.sleep(2)
    await nucleus.shutdown()

asyncio.run(test_memory())
```

### Test Provider System

```python
import asyncio
from nucleus import Nucleus

async def test_providers():
    nucleus = Nucleus()
    await nucleus.boot()
    
    # Request completion
    await nucleus.message_bus.publish("llm.complete", {
        "prompt": "Explain LOTUS in one sentence",
        "provider": "auto",  # Smart routing
        "max_tokens": 100
    })
    
    await asyncio.sleep(3)
    await nucleus.shutdown()

asyncio.run(test_providers())
```

### Test Perception System

```python
import asyncio
from nucleus import Nucleus
from pathlib import Path

async def test_perception():
    nucleus = Nucleus()
    await nucleus.boot()
    
    # Start watching current directory
    await nucleus.message_bus.publish("perception.start_watching", {
        "path": str(Path.cwd())
    })
    
    print("Watching for file changes...")
    print("Try creating/editing a file!")
    
    await asyncio.sleep(30)  # Watch for 30 seconds
    await nucleus.shutdown()

asyncio.run(test_perception())
```

---

## [BUILD] BUILD YOUR FIRST MODULE

### 1. Create Module Directory

```bash
mkdir -p modules/capability_modules/my_module
cd modules/capability_modules/my_module
touch __init__.py manifest.yaml module.json logic.py
```

### 2. Write manifest.yaml

```yaml
name: my_module
version: 1.0.0
type: capability
priority: normal
description: "My awesome module"

capabilities:
  - my_feature

subscriptions:
  - pattern: "my.event"
    description: "Handle my events"

publications:
  - event: "my.response"
    description: "My responses"

config:
  my_setting: "value"
```

### 3. Write module.json

```json
{
  "name": "my_module",
  "version": "1.0.0",
  "display_name": "My Module",
  "description": "Does something awesome",
  "author": "You",
  "requirements": {
    "python": ">=3.10"
  }
}
```

### 4. Write logic.py

```python
from lib.module import BaseModule
from lib.decorators import on_event, tool

class MyModule(BaseModule):
    async def initialize(self):
        self.logger.info("My module starting!")
        self.counter = 0
    
    @on_event("my.event")
    async def handle_event(self, event):
        self.counter += 1
        await self.publish("my.response", {
            "count": self.counter,
            "message": f"Handled {self.counter} events!"
        })
    
    @tool("my_tool")
    async def my_tool(self):
        return {"status": "working!"}
```

### 5. Test Your Module

```bash
python nucleus.py
# Your module should load automatically!
```

---

## [ARCH] UNDERSTANDING THE SYSTEM

### Architecture Overview

```
┌─────────────────┐
│   NUCLEUS       │ <- Core runtime
└───────┬─────────┘
        │
        │ (loads modules)
        │
┌───────┼────────┐
│   MESSAGE BUS   │ <- Redis pub/sub
└───────┬────────┘
        │
┌───────┴────────────────────────┐
│         MODULES                │
│  ┌────────┐  ┌────────┐  ┌───┐│
│  │ Memory │  │Provider │  │Perc││
│  └────────┘  └────────┘  └───┘│
│  ┌────────┐  ┌────────┐  ┌───┐│
│  │Reasoning │ │  Voice  │  │Code││
│  └────────┘  └────────┘  └───┘│
└────────────────────────────────┘
```

### Event Flow Example

```
1. User edits file
   ↓
2. Perception detects change
   ↓
3. Publishes "file.modified" event to bus
   ↓
4. Memory module receives event
   - Stores context in L1
   ↓
5. Reasoning module receives event
   - Decides if action needed
   ↓
6. Provider module receives LLM request
   - Routes to optimal model
   ↓
7. Response flows back through bus
   ↓
8. User receives intelligent response
```

---

## [DOCS] KEY FILES TO STUDY

### Core System
1. `nucleus.py` - Main runtime (understand the boot sequence)
2. `lib/module.py` - BaseModule class (how modules work)
3. `lib/message_bus.py` - Event system (how modules communicate)

### Example Modules
4. `modules/core_modules/memory/logic.py` - Memory implementation
5. `modules/core_modules/providers/logic.py` - Provider system
6. `modules/core_modules/perception/logic.py` - Perception system

### Documentation
7. `modules/README.md` - Module development guide
8. `SESSION_2_SUMMARY.md` - What we built (detailed)

---

## [HELP] TROUBLESHOOTING

### "Redis connection failed"
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running:
redis-server
```

### "Module failed to load"
- Check module has all required files (manifest.yaml, module.json, logic.py)
- Check logic.py has a class inheriting from BaseModule
- Check for syntax errors in Python code
- Look at logs in console

### "No modules discovered"
- Check you're in the lotus directory
- Check modules are in proper directory structure
- Check __init__.py files exist

### "Import errors"
```bash
# Make sure you're in lotus directory
cd lotus

# Install dependencies
pip install -r requirements.txt
```

---

## [TIPS] USEFUL TRICKS

### Watch Logs
```bash
# Run with debug logging
python nucleus.py --log-level DEBUG
```

### Monitor Events
```bash
# In another terminal
redis-cli
> SUBSCRIBE *
# See all events in real-time
```

### Check Module Status
```python
# In Python console
from nucleus import Nucleus
nucleus = Nucleus()
# Check loaded modules
print(nucleus.modules.keys())
```

---

## [NEXT] WHAT TO DO NEXT

### Today (30 minutes)
1. [DONE] Run test_lotus.py
2. [TODO] Study one module's code
3. [TODO] Understand event flow

### This Week (3-5 hours)
4. [TODO] Create your first module
5. [TODO] Test module communication
6. [TODO] Add custom capability

### Next Week (5-10 hours)
7. [TODO] Build voice interface
8. [TODO] Add screen capture
9. [TODO] Create code assistant

### The Big One (10+ hours)
10. [TODO] Implement self-modification
11. [TODO] Watch LOTUS improve herself
12. [TODO] Celebrate revolution!

---

## [HAVE] YOU NOW HAVE

[DONE] A working AI Operating System  
[DONE] Real memory across sessions  
[DONE] Multi-provider LLM access  
[DONE] Real-time perception  
[DONE] Event-driven architecture  
[DONE] Hot-swappable modules  
[DONE] Comprehensive documentation  
[DONE] Test suite  

**This is not vaporware. This is REAL.**

---

## [LINKS] IMPORTANT DOCUMENTS

- [Session Summary](computer:///mnt/user-data/outputs/SESSION_2_SUMMARY.md) - Detailed build notes
- [Module Guide](computer:///mnt/user-data/outputs/lotus/modules/README.md) - How to build modules
- [Test Script](computer:///mnt/user-data/outputs/lotus/test_lotus.py) - Demo and testing
- [Full Project](computer:///mnt/user-data/outputs/lotus/) - All files

---

**Now go make LOTUS do amazing things!**