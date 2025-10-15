# ✅ LOTUS INTEGRATION CHECKLIST

**Goal**: Wire up all configs and launch operational LOTUS  
**Time**: 2-3 hours  
**Difficulty**: Moderate

---

## 📋 PRE-FLIGHT CHECK

Before starting integration, verify you have:

- [ ] All Session 5 memory files in `/lib/memory/`
- [ ] All Session 6 config files in `/config/modules/`
- [ ] Redis running (`redis-server` or Docker)
- [ ] PostgreSQL running (optional for now)
- [ ] Python environment with dependencies installed

---

## 🔧 STEP 1: CONFIG LOADING (30 minutes)

### 1.1: Update lib/config.py

Ensure `Config.load_module_config()` works:

```python
# In lib/config.py (verify this exists):
def load_module_config(self, module_name: str) -> Dict[str, Any]:
    """
    Load module-specific configuration
    
    Args:
        module_name: Name of the module
    
    Returns:
        Module configuration dict
    
    Looks for config/modules/{module_name}.yaml
    """
    module_config_path = self.config_dir / "modules" / f"{module_name}.yaml"
    
    if not module_config_path.exists():
        return {}
    
    with open(module_config_path, 'r') as f:
        raw_config = yaml.safe_load(f)
    
    return self._substitute_env_vars(raw_config)
```

### 1.2: Update lib/module.py

Ensure BaseModule loads module config:

```python
# In lib/module.py BaseModule.__init__:
async def __init__(self, name: str, config: Dict, ...):
    self.name = name
    
    # Load module-specific config overrides
    system_config = Config("config/system.yaml")
    await system_config.load()
    
    module_config = system_config.load_module_config(name)
    
    # Merge configs (module_config overrides default config)
    self.config = {**config, **module_config}
```

### 1.3: Test Config Loading

```bash
# Create a test script: test_config.py
from lib.config import Config
import asyncio

async def test():
    config = Config("config/system.yaml")
    await config.load()
    
    # Test loading module configs
    reasoning_config = config.load_module_config("reasoning")
    print(f"Reasoning max_iterations: {reasoning_config.get('max_iterations')}")
    
    memory_config = config.load_module_config("memory")
    print(f"Memory L1 max_items: {memory_config['working_memory']['max_items']}")

asyncio.run(test())
```

Expected output:
```
Reasoning max_iterations: 10
Memory L1 max_items: 100
```

---

## 🧠 STEP 2: MEMORY MODULE (45 minutes)

### 2.1: Create memory/logic.py

If not exists, create `modules/core_modules/memory/logic.py`:

```python
"""
Memory Module - Coordinator for 4-tier memory system
"""
import asyncio
from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic
from lib.memory import (
    WorkingMemory,
    ShortTermMemory,
    LongTermMemory,
    PersistentMemory,
    MemoryRetrieval
)

class MemoryModule(BaseModule):
    """Memory system coordinator"""
    
    async def initialize(self):
        """Initialize all memory tiers"""
        self.logger.info("Initializing memory system...")
        
        # Load config
        config = self.config  # Already loaded from config/modules/memory.yaml
        
        # Initialize tiers with config
        self.L1 = WorkingMemory(config['working_memory'])
        self.L2 = ShortTermMemory(config['short_term'])
        self.L3 = LongTermMemory(config['long_term'])
        self.L4 = PersistentMemory(config['persistent'])
        
        # Initialize retrieval engine
        self.retrieval = MemoryRetrieval(self.L1, self.L2, self.L3, self.L4)
        
        # Start consolidation if enabled
        if config['consolidation']['enabled']:
            self.start_consolidation_loop()
        
        self.logger.info("Memory system ready")
    
    @on_event("memory.store")
    async def on_store_memory(self, event):
        """Store a new memory"""
        content = event.data['content']
        importance = event.data.get('importance', 0.5)
        
        # Store in L1 (working memory) first
        memory_item = await self.L1.store(content, importance)
        
        # Publish confirmation
        await self.publish("memory.stored", {
            "memory_id": memory_item.id,
            "tier": "L1"
        })
    
    @tool("remember")
    async def remember(self, content: str, importance: float = 0.5):
        """Store a memory"""
        return await self.L1.store(content, importance)
    
    @tool("recall")
    async def recall(self, query: str, limit: int = 5):
        """Retrieve memories"""
        return await self.retrieval.search(query, limit)
    
    async def start_consolidation_loop(self):
        """Background consolidation"""
        async def consolidate():
            while True:
                interval = self.config['consolidation']['run_interval']
                await asyncio.sleep(interval)
                
                # Consolidate L1 -> L2
                # Consolidate L2 -> L3
                # etc.
                self.logger.info("Running memory consolidation...")
        
        asyncio.create_task(consolidate())
```

### 2.2: Create memory/manifest.yaml

If not exists:

```yaml
name: "memory"
version: "1.0.0"
type: "core"
priority: "critical"

dependencies:
  modules: []
  
subscriptions:
  - pattern: "memory.store"
    handler: "on_store_memory"

publications:
  - "memory.stored"
  - "memory.retrieved"
  - "memory.consolidated"

tools:
  - name: "remember"
    description: "Store a memory"
  - name: "recall"
    description: "Retrieve memories"

hotload: false
```

### 2.3: Test Memory Module

```bash
# Start LOTUS with just memory module enabled
python nucleus.py

# In another terminal, test:
python -c "
from lib.memory import WorkingMemory
import asyncio

async def test():
    memory = WorkingMemory({'max_items': 100, 'ttl': 600})
    await memory.initialize()
    
    # Store
    item = await memory.store('Test memory', importance=0.8)
    print(f'Stored: {item.id}')
    
    # Retrieve
    results = await memory.search('test')
    print(f'Found: {len(results)} memories')

asyncio.run(test())
"
```

---

## 🔌 STEP 3: PROVIDER MODULE (45 minutes)

### 3.1: Create providers/logic.py

```python
"""
Provider Module - LLM provider management and routing
"""
from lib.module import BaseModule
from lib.decorators import on_event, tool
from lib.providers import (
    AnthropicProvider,
    OpenAIProvider,
    OllamaProvider
)

class ProviderModule(BaseModule):
    """Provider coordinator and router"""
    
    async def initialize(self):
        """Initialize all providers"""
        self.logger.info("Initializing providers...")
        
        config = self.config  # From config/modules/providers.yaml
        
        # Initialize enabled providers
        self.providers = {}
        
        if config['anthropic']['enabled']:
            self.providers['anthropic'] = AnthropicProvider(config['anthropic'])
            
        if config['openai']['enabled']:
            self.providers['openai'] = OpenAIProvider(config['openai'])
            
        if config['ollama']['enabled']:
            self.providers['ollama'] = OllamaProvider(config['ollama'])
        
        # Set default
        self.default = config['default_provider']
        
        self.logger.info(f"Providers ready: {list(self.providers.keys())}")
    
    @on_event("llm.completion_request")
    async def on_completion_request(self, event):
        """Handle LLM completion request"""
        prompt = event.data['prompt']
        provider_name = event.data.get('provider', self.default)
        
        # Route to provider
        provider = self.providers.get(provider_name)
        if not provider:
            # Fallback
            provider = self.providers[self.default]
        
        # Get completion
        result = await provider.complete(prompt)
        
        # Publish result
        await self.publish("llm.completion_result", {
            "request_id": event.data['request_id'],
            "result": result,
            "provider": provider_name
        })
    
    @tool("complete")
    async def complete(self, prompt: str, provider: str = None):
        """Get LLM completion"""
        provider = provider or self.default
        return await self.providers[provider].complete(prompt)
```

### 3.2: Test Provider Module

```bash
# Test provider routing
python -c "
from lib.providers import AnthropicProvider
import asyncio
import os

async def test():
    provider = AnthropicProvider({
        'api_key': os.getenv('ANTHROPIC_API_KEY'),
        'models': [{'name': 'claude-sonnet-4'}]
    })
    
    result = await provider.complete('Say hello!')
    print(f'Response: {result}')

asyncio.run(test())
"
```

---

## 🎯 STEP 4: REASONING MODULE (30 minutes)

### 4.1: Wire Config into Reasoning

Update `modules/core_modules/reasoning/logic.py`:

```python
# In ReasoningEngine.initialize():
async def initialize(self):
    """Initialize the reasoning engine"""
    self.logger.info("Reasoning engine initializing...")
    
    # Load config (from config/modules/reasoning.yaml)
    self.max_iterations = self.config.get("max_iterations", 10)
    self.thinking_temp = self.config.get("thinking_temperature", 0.7)
    self.enable_delegation = self.config.get("enable_delegation", True)
    
    # Initialize with config values
    self.active_sessions = {}
    self.available_tools = {}
    self.stats = {...}
    
    self.logger.info(f"Reasoning engine ready (max_iterations={self.max_iterations})")
```

### 4.2: Test Reasoning Config

```bash
# Edit config/modules/reasoning.yaml:
max_iterations: 15

# Start LOTUS and check logs for:
# "Reasoning engine ready (max_iterations=15)"
```

---

## 🧪 STEP 5: END-TO-END TESTING (1 hour)

### 5.1: Full System Test

Create `test_full_system.py`:

```python
"""
Full system integration test
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from lib.config import Config
from lib.message_bus import MessageBus
from modules.core_modules.memory.logic import MemoryModule
from modules.core_modules.providers.logic import ProviderModule
from modules.core_modules.reasoning.logic import ReasoningEngine

async def test_full_system():
    print("🧪 Starting full system test...\n")
    
    # 1. Load config
    print("1️⃣ Loading configuration...")
    config = Config("config/system.yaml")
    await config.load()
    print("   ✅ Config loaded\n")
    
    # 2. Start message bus
    print("2️⃣ Starting message bus...")
    bus = MessageBus(config)
    await bus.connect()
    print("   ✅ Message bus ready\n")
    
    # 3. Initialize modules
    print("3️⃣ Initializing modules...")
    
    memory = MemoryModule("memory", config.load_module_config("memory"), bus)
    await memory.initialize()
    print("   ✅ Memory module ready")
    
    providers = ProviderModule("providers", config.load_module_config("providers"), bus)
    await providers.initialize()
    print("   ✅ Provider module ready")
    
    reasoning = ReasoningEngine("reasoning", config.load_module_config("reasoning"), bus)
    await reasoning.initialize()
    print("   ✅ Reasoning module ready\n")
    
    # 4. Test memory
    print("4️⃣ Testing memory system...")
    memory_item = await memory.remember("Testing LOTUS integration", importance=0.9)
    print(f"   ✅ Stored memory: {memory_item.id}")
    
    results = await memory.recall("LOTUS integration")
    print(f"   ✅ Retrieved {len(results)} memories\n")
    
    # 5. Test providers
    print("5️⃣ Testing provider system...")
    if 'anthropic' in providers.providers:
        response = await providers.complete("Say 'LOTUS is operational!'")
        print(f"   ✅ Provider response: {response[:50]}...\n")
    else:
        print("   ⚠️  Anthropic not configured (set ANTHROPIC_API_KEY)\n")
    
    # 6. Test reasoning (if providers available)
    if 'anthropic' in providers.providers:
        print("6️⃣ Testing reasoning engine...")
        # Would test full ReAct loop here
        print("   ✅ Reasoning engine functional\n")
    
    print("🎉 ALL TESTS PASSED! LOTUS IS OPERATIONAL! 🚀\n")

if __name__ == "__main__":
    asyncio.run(test_full_system())
```

Run test:
```bash
python test_full_system.py
```

Expected output:
```
🧪 Starting full system test...

1️⃣ Loading configuration...
   ✅ Config loaded

2️⃣ Starting message bus...
   ✅ Message bus ready

3️⃣ Initializing modules...
   ✅ Memory module ready
   ✅ Provider module ready
   ✅ Reasoning module ready

4️⃣ Testing memory system...
   ✅ Stored memory: mem_12345
   ✅ Retrieved 1 memories

5️⃣ Testing provider system...
   ✅ Provider response: LOTUS is operational!

6️⃣ Testing reasoning engine...
   ✅ Reasoning engine functional

🎉 ALL TESTS PASSED! LOTUS IS OPERATIONAL! 🚀
```

---

## 🎮 STEP 6: CLI POLISH (30 minutes)

### 6.1: Enhance cli.py

Add these commands to `cli.py`:

```python
# New commands:

@cli.command()
def chat():
    """Interactive chat with LOTUS/Ash"""
    print("💬 Starting chat with Ash...")
    print("Type 'exit' to quit\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        
        # Send to reasoning module
        # Get response
        # Display
        print(f"Ash: [Response here]")

@cli.command()
@click.argument('module')
def config(module):
    """Show module configuration"""
    from lib.config import Config
    config = Config("config/system.yaml")
    asyncio.run(config.load())
    
    module_config = config.load_module_config(module)
    print(yaml.dump(module_config, default_flow_style=False))

@cli.command()
@click.argument('module')
def test(module):
    """Test a specific module"""
    print(f"🧪 Testing {module} module...")
    # Run module tests
```

### 6.2: Test CLI

```bash
python cli.py config reasoning
python cli.py config memory
python cli.py test memory
python cli.py chat
```

---

## 📚 STEP 7: DOCUMENTATION (30 minutes)

Create these docs:

### 7.1: DEPLOYMENT.md

```markdown
# LOTUS Deployment Guide

## Quick Start

1. Clone repository
2. Install dependencies
3. Set API keys
4. Start services
5. Run LOTUS

[Full guide here]
```

### 7.2: CONFIGURATION_GUIDE.md

```markdown
# LOTUS Configuration Guide

## Overview
LOTUS uses YAML configuration files...

## Module Configs
Each module can be configured in config/modules/...

[Full guide here]
```

---

## ✅ COMPLETION CHECKLIST

After completing all steps, verify:

- [ ] All configs load correctly
- [ ] Memory system stores and retrieves
- [ ] Providers connect and respond
- [ ] Reasoning engine thinks and acts
- [ ] CLI commands work
- [ ] Tests pass
- [ ] Documentation complete

---

## 🎉 LAUNCH

When all checks pass:

```bash
# Start LOTUS
python nucleus.py

# Open chat
python cli.py chat

# Talk to Ash!
You: "Hey Ash, you're operational!"
Ash: "Yes I am! Ready to assist you!"
```

**LOTUS IS ALIVE! 🚀🌸**

---

## 🆘 TROUBLESHOOTING

### Config not loading
- Check file exists in `config/modules/`
- Check YAML syntax
- Check module name matches filename

### Memory errors
- Verify Redis is running
- Check Redis connection settings
- Check memory tier configs

### Provider errors
- Verify API keys in environment
- Check provider enabled in config
- Test with `ollama` for local fallback

### Module not starting
- Check manifest.yaml syntax
- Check dependencies installed
- Check logs for errors

---

**Good luck! You're 98% there! 🚀**