# 🚀 LOTUS Quick Start Guide

**Get LOTUS running in 15 minutes!**

This guide will get you from zero to a working LOTUS instance that can:
- Accept user input
- Think using ReAct loop
- Access memory
- Call LLM providers
- Respond intelligently

---

## ⚡ Quick Setup (15 minutes)

### 1. Prerequisites (2 minutes)
```bash
# Check Python version (need 3.11+)
python --version

# Install Docker (if not installed)
# macOS: https://docs.docker.com/desktop/install/mac-install/
# Linux: https://docs.docker.com/engine/install/
# Windows: https://docs.docker.com/desktop/install/windows-install/
```

### 2. Start Infrastructure (3 minutes)
```bash
# Start Redis (message bus)
docker run -d --name lotus-redis -p 6379:6379 redis:7-alpine

# Start PostgreSQL (persistent memory)
docker run -d --name lotus-postgres \
  -p 5432:5432 \
  -e POSTGRES_DB=lotus \
  -e POSTGRES_USER=lotus \
  -e POSTGRES_PASSWORD=lotus \
  postgres:14

# Verify they're running
docker ps
# Should see both containers running
```

### 3. Install Dependencies (5 minutes)
```bash
# Navigate to LOTUS directory
cd lotus

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# This installs:
# - Redis client
# - PostgreSQL client
# - ChromaDB (vector database)
# - Anthropic SDK
# - OpenAI SDK
# - And more...
```

### 4. Configure API Keys (2 minutes)
```bash
# Create environment file
cat > .env << EOF
# LLM Provider API Keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here

# Infrastructure
REDIS_HOST=localhost
REDIS_PORT=6379
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lotus
POSTGRES_USER=lotus
POSTGRES_PASSWORD=lotus

# System
LOTUS_ENV=development
LOTUS_LOG_LEVEL=INFO
EOF

# Edit .env and add your actual API keys
nano .env  # or vim, code, whatever you prefer
```

### 5. Initialize Database (1 minute)
```bash
# Create database schema
python scripts/migrate.py

# This creates tables for persistent memory
```

### 6. Test the System (2 minutes)
```bash
# Try to start LOTUS
python nucleus.py

# You should see:
# 🌸 LOTUS starting up...
#    Found X modules
#    Loading modules...
#    ✓ Loaded: reasoning
#    ✓ Loaded: memory (if completed)
#    ✓ Loaded: providers (if completed)
# 🌸 LOTUS is online and ready!

# If you see errors, check:
# - Redis is running (docker ps)
# - PostgreSQL is running (docker ps)
# - API keys are set (.env file)
```

---

## 🎯 First Interaction

### Option A: Python REPL (For Testing)
```python
# Start Python in the lotus directory
python

# Import and start LOTUS
from nucleus import Nucleus
import asyncio

async def test():
    nucleus = Nucleus()
    await nucleus.boot()
    
    # Send a test message
    await nucleus.message_bus.publish("perception.user_input", {
        "text": "Hello LOTUS, can you hear me?",
        "context": {}
    })
    
    # Keep running
    await asyncio.sleep(60)

# Run it
asyncio.run(test())
```

### Option B: CLI (Once Built)
```bash
# Start interactive chat
python cli.py chat

LOTUS> Hello! Can you introduce yourself?
🌸 Hi! I'm LOTUS, your AI operating system. I'm like JARVIS but open source!
   I can help with coding, analysis, planning, and much more. What can I do 
   for you today?

LOTUS> What can you do?
🌸 I have several capabilities:
   - Intelligent reasoning using ReAct loops
   - Multi-tier memory (I remember our conversations)
   - Access to multiple LLM providers (Claude, GPT, Ollama)
   - Real-time code analysis (once code_assistant module is loaded)
   - And I can even write new modules to extend my own capabilities!
   
   What would you like help with?
```

---

## 🔧 Complete the Core Modules

Right now, only the reasoning engine is complete. To get full functionality:

### 1. Memory Module (Required)
```bash
# Create the memory coordinator
cd modules/core_modules/memory
```

Create `logic.py`:
```python
from lib.module import BaseModule
from lib.decorators import on_event, periodic

class MemoryCoordinator(BaseModule):
    async def initialize(self):
        # Use the memory system from lib/memory.py
        pass
    
    @on_event("memory.store")
    async def on_store_request(self, event):
        # Store memory
        content = event.data.get("content")
        await self.memory.remember(content)
    
    @on_event("memory.recall")
    async def on_recall_request(self, event):
        # Retrieve memories
        query = event.data.get("query")
        memories = await self.memory.recall(query)
        
        await self.publish("memory.recall_result", {
            "query": query,
            "memories": [m.to_dict() for m in memories]
        })
    
    @periodic(interval=300)
    async def consolidate_memories(self):
        # Move short-term to long-term every 5 minutes
        await self.memory.consolidate()
```

### 2. Provider Module (Required)
```bash
cd modules/core_modules/providers
```

Create `logic.py`:
```python
from lib.module import BaseModule
from lib.decorators import on_event

class ProviderCoordinator(BaseModule):
    async def initialize(self):
        # Provider manager is already available via self.llm
        pass
    
    @on_event("llm.completion_request")
    async def on_completion_request(self, event):
        prompt = event.data.get("prompt")
        provider = event.data.get("provider", "default")
        
        response = await self.llm.complete(
            prompt=prompt,
            provider=provider
        )
        
        await self.publish("llm.completion_result", {
            "content": response.content,
            "model": response.model
        })
```

### 3. Perception Module (Optional but Recommended)
```bash
cd modules/core_modules/perception
```

Create `logic.py`:
```python
from lib.module import BaseModule
from lib.decorators import on_event
import pyperclip
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PerceptionCoordinator(BaseModule):
    async def initialize(self):
        # Start file watcher
        # Start clipboard monitor
        pass
    
    # Add file watching, clipboard monitoring, etc.
```

---

## 🧪 Test the ReAct Loop

```python
# test_react.py
import asyncio
from nucleus import Nucleus

async def test_reasoning():
    # Start LOTUS
    nucleus = Nucleus()
    await nucleus.boot()
    
    # Wait for startup
    await asyncio.sleep(2)
    
    # Send a reasoning challenge
    await nucleus.message_bus.publish("perception.user_input", {
        "text": "I need to write a Python function that calculates fibonacci numbers. Can you help me plan this?",
        "context": {}
    })
    
    # Wait for response
    # (In real impl, would subscribe to action.respond)
    await asyncio.sleep(10)
    
    print("Check logs for reasoning process!")

if __name__ == "__main__":
    asyncio.run(test_reasoning())
```

Run it:
```bash
python test_react.py

# Check data/logs/nucleus.log to see:
# - Thought generation
# - Action planning
# - Tool execution (simulated)
# - Response generation
```

---

## 📊 Verify Everything Works

### Check Redis
```bash
# Connect to Redis
docker exec -it lotus-redis redis-cli

# See published events
SUBSCRIBE system.*
SUBSCRIBE cognition.*
SUBSCRIBE action.*

# You should see events flowing!
```

### Check PostgreSQL
```bash
# Connect to PostgreSQL
docker exec -it lotus-postgres psql -U lotus -d lotus

# Check tables
\dt

# Check memories
SELECT * FROM memories LIMIT 5;
```

### Check Logs
```bash
# Real-time logs
tail -f data/logs/nucleus.log

# You should see:
# - Module loading
# - Event routing
# - Reasoning process
# - Memory operations
```

---

## 🎯 Your First Real Task

Once everything is working, try this:

```bash
python cli.py chat

You: I'm working on a FastAPI application. I need to add authentication. 
     Can you help me design the architecture?

# LOTUS should:
# 1. Think about the problem (ReAct loop)
# 2. Recall relevant information from memory
# 3. Plan the solution
# 4. Consider delegating to a more powerful model
# 5. Provide a detailed response

# Watch the logs to see the ReAct loop in action!
```

---

## 🐛 Troubleshooting

### Redis Connection Failed
```bash
# Check if Redis is running
docker ps | grep redis

# Restart Redis
docker restart lotus-redis

# Check logs
docker logs lotus-redis
```

### PostgreSQL Connection Failed
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart PostgreSQL
docker restart lotus-postgres

# Check logs
docker logs lotus-postgres

# Verify credentials in .env
```

### Module Load Failed
```bash
# Check module manifest
cat modules/core_modules/reasoning/manifest.yaml

# Check for Python errors
python -m py_compile modules/core_modules/reasoning/logic.py

# Check dependencies
pip list | grep anthropic
```

### API Key Issues
```bash
# Verify API keys are set
echo $ANTHROPIC_API_KEY

# Or check .env file
cat .env | grep ANTHROPIC

# Test API key
python -c "import anthropic; client = anthropic.Anthropic(); print('API key works!')"
```

---

## 📚 Next Steps

### Immediate
1. ✅ Get system running
2. ✅ Test basic ReAct loop
3. ✅ Verify memory storage
4. ✅ Test provider switching

### Week 1
1. Complete memory module
2. Complete provider module  
3. Build basic CLI
4. Add more test cases

### Week 2
1. Build code_assistant module
2. Test real coding workflows
3. Add file watching
4. Integrate with IDE

### Week 3+
1. Add voice interface
2. Add screen analyzer
3. Implement computer use
4. Build self-modifier

---

## 🎉 Success Checklist

- [ ] Redis and PostgreSQL running
- [ ] Dependencies installed
- [ ] API keys configured
- [ ] System boots without errors
- [ ] Reasoning module loads
- [ ] Can publish and receive events
- [ ] Memories are stored
- [ ] LLM providers respond
- [ ] Basic ReAct loop works

When all boxes are checked, you have a working LOTUS foundation! 🚀

---

## 💡 Pro Tips

1. **Watch the logs** - They show exactly what's happening
2. **Use Redis CLI** - See events in real-time
3. **Test incrementally** - One module at a time
4. **Check memory** - Ensure memories are being stored
5. **Monitor performance** - Watch CPU/RAM usage

---

## 🆘 Need Help?

Check these files:
- **BUILD_STATUS.md** - Detailed build status
- **README.md** - Project overview
- **docs/ARCHITECTURE.md** - Technical deep dive

Or review the code:
- **nucleus.py** - Core runtime
- **lib/module.py** - How modules work
- **modules/core_modules/reasoning/logic.py** - ReAct implementation

---

**You're ready to build! Let's make LOTUS real. 🌸**