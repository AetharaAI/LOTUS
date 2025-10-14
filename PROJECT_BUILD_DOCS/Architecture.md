# LOTUS AI Operating System - Technical Architecture

## 🏛️ System Overview

LOTUS is built on a **layered, event-driven, modular architecture** that separates concerns and enables hot-swappable capabilities. The system is designed to be:

- **Decoupled**: Modules communicate only via events, not direct references
- **Scalable**: Event bus can distribute across machines
- **Resilient**: Modules can fail independently without crashing the system
- **Extensible**: New capabilities install without touching core code
- **Self-improving**: AI can write and deploy its own modules

---

## 🎯 Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                      │
│  • CLI (terminal)        • Web UI (future)                   │
│  • Voice (microphone)    • Screen (vision)                   │
│  • API (programmatic)    • IDE plugins                       │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER                          │
│  Modules: voice_interface, screen_analyzer, file_watcher    │
│  • Captures inputs from all sources                          │
│  • Normalizes into standard event format                     │
│  • Publishes to message bus                                  │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               REDIS MESSAGE BUS (Communication)              │
│  Channels: system.*, perception.*, cognition.*, action.*     │
│  Streams: conversation_stream, action_log, memory_updates    │
│  • Pub/Sub for events    • Streams for persistence          │
│  • Pattern matching      • Consumer groups                   │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   COGNITION LAYER                            │
│  Module: reasoning (ReAct engine)                            │
│  • Analyzes context      • Plans actions                     │
│  • Makes decisions       • Delegates tasks                   │
│  • Executes tools        • Learns from outcomes              │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   MODULE ECOSYSTEM                           │
│  Core: reasoning, memory, providers, perception              │
│  Capability: code_assistant, voice, screen, self_modifier    │
│  Integration: computer_use, mcp_protocol, browser, ide       │
│  • Specialized functions  • Can be added/removed             │
│  • Event-driven          • Hot-reloadable                    │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              MEMORY SYSTEM (4-Tier Hierarchy)                │
│  L1: Working (Redis)     - Active context                    │
│  L2: Short-term (Streams) - Recent history                   │
│  L3: Long-term (ChromaDB) - Semantic memories                │
│  L4: Persistent (Postgres) - Structured knowledge            │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               INFRASTRUCTURE LAYER                           │
│  • Redis (message bus, cache)                                │
│  • PostgreSQL (structured data)                              │
│  • ChromaDB (vector embeddings)                              │
│  • File system (module storage)                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 The Nucleus (Core Runtime)

The Nucleus is the **minimal, stable kernel** that orchestrates everything but knows nothing about AI.

### Responsibilities
1. **Module Lifecycle Management**
   - Discover modules on startup
   - Resolve dependencies
   - Load modules in correct order
   - Handle module failures gracefully
   - Support hot-reload without restart

2. **Event Loop Management**
   - Run asyncio event loop
   - Manage concurrent tasks
   - Handle signals (SIGTERM, SIGINT)
   - Graceful shutdown

3. **Message Routing**
   - Connect to Redis
   - Route events between modules
   - Handle pattern matching
   - Manage consumer groups

4. **Health Monitoring**
   - Monitor module health
   - Detect crashes and restart
   - Resource usage tracking
   - Performance metrics

### Key Design Principles

**The Nucleus Never Changes**
- Adding new capabilities = add new module
- Changing AI models = change provider config
- New LLM features = new module
- Core remains stable

**Minimal Surface Area**
```python
# nucleus.py - Simple interface
class Nucleus:
    async def boot(self)           # Start system
    async def shutdown(self)       # Stop system
    async def load_module(self, module)  # Load module
    async def unload_module(self, name)  # Unload module
    def health(self) -> dict       # System health
```

---

## 📦 The Module System

### Module Contract

Every module is a self-contained package with:

```yaml
# manifest.yaml - The module's contract
name: "code_assistant"
version: "1.2.0"
type: "capability"                    # core | capability | integration
author: "LOTUS Team"
license: "MIT"
priority: "high"                      # critical | high | normal | low

# What this module needs to work
dependencies:
  modules: ["reasoning", "memory", "providers"]
  system: ["python>=3.11"]
  packages: ["tree-sitter", "pygments"]

# What events this module listens to
subscriptions:
  - pattern: "cognition.code_request"
    handler: "handle_code_request"
  - pattern: "perception.file_changed"
    handler: "on_file_change"
    filter: "*.py"
  - pattern: "cognition.debugging_needed"
    handler: "debug_code"

# What events this module publishes
publications:
  - "action.code_suggestion"
  - "action.code_execution"
  - "cognition.analysis_complete"
  - "memory.store_pattern"

# LLM providers this module uses
providers:
  primary: "claude-sonnet-4"
  fallback: ["gpt-4o", "ollama:deepseek-coder"]
  delegation:
    complex_architecture: "claude-opus-4"
    quick_fixes: "gpt-4o-mini"
    code_review: "claude-sonnet-4"

# Memory collections this module uses
memory:
  vector_collections: 
    - "code_patterns"
    - "bug_solutions"
    - "architecture_designs"
  state_keys:
    - "active_project"
    - "recent_files"
    - "user_preferences"

# Tools this module provides
tools:
  - name: "analyze_code"
    description: "Analyze code for bugs and improvements"
    parameters:
      - name: "code"
        type: "string"
        required: true
      - name: "language"
        type: "string"
        required: false

  - name: "write_code"
    description: "Generate code based on specification"
    parameters:
      - name: "spec"
        type: "dict"
        required: true

# Capabilities this module exposes
capabilities:
  - "code_analysis"
  - "bug_fixing"
  - "architecture_design"
  - "real_time_assistance"
  - "pattern_learning"

# Configuration options
config_schema:
  watch_patterns: ["*.py", "*.js", "*.ts"]
  auto_fix: false
  suggestion_delay: 1.0

# Can this module be hot-reloaded?
hotload: true

# Security permissions needed
permissions:
  - "file.read"
  - "file.write"
  - "network.http"
  - "llm.api_call"
```

### BaseModule Class

All modules inherit from `BaseModule`:

```python
# lib/module.py
from abc import ABC, abstractmethod
import asyncio
from typing import Any, Dict, Callable
import redis.asyncio as redis

class BaseModule(ABC):
    """Base class for all LOTUS modules"""
    
    def __init__(self, config: Dict[str, Any], message_bus, memory, llm_providers):
        self.name = None  # Set by nucleus
        self.config = config
        self.bus = message_bus
        self.memory = memory
        self.llm = llm_providers
        self.logger = None  # Set by nucleus
        self._event_handlers = {}
        self._tools = {}
        self._periodic_tasks = []
    
    # Lifecycle hooks (optional to override)
    async def initialize(self):
        """Called once when module loads"""
        pass
    
    async def shutdown(self):
        """Called when module unloads"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Return module health status"""
        return {"status": "healthy"}
    
    # Event handling
    async def publish(self, channel: str, data: Dict[str, Any]):
        """Publish event to message bus"""
        await self.bus.publish(channel, {
            "source": self.name,
            "data": data,
            "timestamp": time.time()
        })
    
    def register_handler(self, pattern: str, handler: Callable):
        """Register event handler"""
        self._event_handlers[pattern] = handler
    
    def register_tool(self, name: str, func: Callable):
        """Register a tool that can be called"""
        self._tools[name] = func
    
    def add_periodic_task(self, interval: float, func: Callable):
        """Register a periodic task"""
        self._periodic_tasks.append((interval, func))
    
    # Helper methods available to all modules
    async def get_state(self, key: str) -> Any:
        """Get module state from memory"""
        return await self.memory.get_state(self.name, key)
    
    async def set_state(self, key: str, value: Any):
        """Set module state in memory"""
        await self.memory.set_state(self.name, key, value)
    
    async def recall_memory(self, query: str, limit: int = 10):
        """Retrieve relevant memories"""
        return await self.memory.recall(query, limit)
    
    async def store_memory(self, content: str, type: str = "episodic"):
        """Store a new memory"""
        await self.memory.remember(content, type)
```

### Module Decorators

Decorators make it easy to register handlers and tools:

```python
# lib/decorators.py
from functools import wraps

def on_event(pattern: str, filter: str = None):
    """Decorator to register event handler"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, event):
            # Apply filter if specified
            if filter and not match_filter(event, filter):
                return
            return await func(self, event)
        
        wrapper._event_pattern = pattern
        wrapper._event_filter = filter
        return wrapper
    return decorator

def tool(name: str, description: str = ""):
    """Decorator to register a tool"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            return await func(self, *args, **kwargs)
        
        wrapper._tool_name = name
        wrapper._tool_description = description
        return wrapper
    return decorator

def periodic(interval: float):
    """Decorator for periodic tasks"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self):
            while True:
                try:
                    await func(self)
                except Exception as e:
                    self.logger.error(f"Periodic task error: {e}")
                await asyncio.sleep(interval)
        
        wrapper._periodic_interval = interval
        return wrapper
    return decorator

# Example usage in a module:
class MyModule(BaseModule):
    @on_event("user.message", filter="*.py")
    async def on_code_file(self, event):
        """Automatically called when user opens .py file"""
        pass
    
    @tool("analyze")
    async def analyze(self, code: str) -> dict:
        """Tool that reasoning engine can call"""
        return {"result": "analysis"}
    
    @periodic(interval=60)
    async def cleanup(self):
        """Runs every 60 seconds"""
        pass
```

---

## 📡 Message Bus Architecture

### Event Channels

Events use hierarchical naming:

```
system.*                    # System-level events
├── system.boot            # System starting up
├── system.shutdown        # System shutting down
├── system.module_loaded   # Module was loaded
├── system.module_failed   # Module failed
└── system.health_check    # Health check request

perception.*               # Input from the world
├── perception.user_input  # User text input
├── perception.voice_input # Voice input
├── perception.screen_update # Screen changed
├── perception.file_changed # File modified
└── perception.clipboard   # Clipboard changed

cognition.*                # AI thinking/decisions
├── cognition.task_request # New task to handle
├── cognition.tool_call    # Need to use a tool
├── cognition.delegate     # Delegate to another LLM
├── cognition.question     # Need more information
└── cognition.decision     # Decision made

action.*                   # Output to the world
├── action.speak          # Text to speak (voice)
├── action.display        # Show to user
├── action.execute        # Run code/command
├── action.mouse_move     # Computer use
├── action.type_text      # Computer use
└── action.file_write     # Write file

memory.*                   # Memory operations
├── memory.store          # Store new memory
├── memory.recall         # Recall memories
├── memory.consolidate    # Move to long-term
└── memory.forget         # Prune old memories
```

### Event Structure

```python
{
    "channel": "cognition.task_request",
    "source": "code_assistant",
    "timestamp": 1697234567.123,
    "data": {
        "task": "Debug this function",
        "context": {...},
        "priority": "high"
    },
    "metadata": {
        "trace_id": "abc123",
        "user_id": "user_001"
    }
}
```

### Streams for Persistence

Redis Streams provide persistent, ordered logs:

```python
# conversation_stream - Full conversation history
XADD conversation_stream * \
    user "Can you help debug this?" \
    lotus "Of course! What's the issue?" \
    timestamp 1697234567

# action_log - Audit trail of all actions
XADD action_log * \
    action "file_write" \
    path "/code/main.py" \
    result "success" \
    timestamp 1697234568

# memory_updates - Memory system changes
XADD memory_updates * \
    operation "store" \
    collection "code_patterns" \
    embedding_id "abc123" \
    timestamp 1697234569
```

---

## 🔧 Computer Use & MCP Integration

### Computer Use Module

The `computer_use` module implements Anthropic's computer use protocol:

```python
# modules/integration_modules/computer_use/logic.py
from lib.module import BaseModule
from lib.decorators import on_event, tool
import pyautogui
import mss

class ComputerUseModule(BaseModule):
    """Full computer control capabilities"""
    
    async def initialize(self):
        self.screen_size = pyautogui.size()
        self.sct = mss.mss()
    
    @tool("mouse_move")
    async def mouse_move(self, x: int, y: int):
        """Move mouse to coordinates"""
        pyautogui.moveTo(x, y)
        await self.publish("action.mouse_moved", {"x": x, "y": y})
    
    @tool("mouse_click")
    async def mouse_click(self, button: str = "left"):
        """Click mouse button"""
        pyautogui.click(button=button)
        await self.publish("action.mouse_clicked", {"button": button})
    
    @tool("type_text")
    async def type_text(self, text: str):
        """Type text on keyboard"""
        pyautogui.write(text)
        await self.publish("action.text_typed", {"text": text})
    
    @tool("press_key")
    async def press_key(self, key: str):
        """Press keyboard key"""
        pyautogui.press(key)
        await self.publish("action.key_pressed", {"key": key})
    
    @tool("take_screenshot")
    async def take_screenshot(self, region: dict = None) -> bytes:
        """Capture screenshot"""
        if region:
            screenshot = self.sct.grab(region)
        else:
            screenshot = self.sct.grab(self.sct.monitors[0])
        
        # Convert to bytes
        img_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
        return img_bytes
    
    @tool("get_screen_info")
    async def get_screen_info(self) -> dict:
        """Get screen dimensions and info"""
        return {
            "width": self.screen_size[0],
            "height": self.screen_size[1],
            "monitors": len(self.sct.monitors) - 1  # Exclude "all in one"
        }
    
    @on_event("cognition.computer_action")
    async def handle_computer_action(self, event):
        """Handle computer control requests from reasoning engine"""
        action = event.data["action"]
        params = event.data.get("params", {})
        
        # Execute requested action
        if action in self._tools:
            result = await self._tools[action](**params)
            await self.publish("action.computer_action_complete", {
                "action": action,
                "result": result
            })
```

### MCP Protocol Module

Model Context Protocol for standardized tool interfaces:

```python
# modules/integration_modules/mcp_protocol/logic.py
class MCPProtocolModule(BaseModule):
    """MCP server and client implementation"""
    
    async def initialize(self):
        self.server = MCPServer(port=self.config.get("port", 5555))
        self.clients = {}
        await self.server.start()
        self.register_mcp_tools()
    
    def register_mcp_tools(self):
        """Register all LOTUS tools as MCP tools"""
        # Computer use tools
        self.server.register_tool("computer.mouse_move", 
            self.wrap_tool("mouse_move"))
        self.server.register_tool("computer.click",
            self.wrap_tool("mouse_click"))
        self.server.register_tool("computer.type",
            self.wrap_tool("type_text"))
        
        # File system tools
        self.server.register_tool("fs.read",
            self.wrap_tool("read_file"))
        self.server.register_tool("fs.write",
            self.wrap_tool("write_file"))
        
        # Web browsing tools
        self.server.register_tool("web.navigate",
            self.wrap_tool("navigate_to"))
        self.server.register_tool("web.click_element",
            self.wrap_tool("click_element"))
    
    def wrap_tool(self, tool_name: str):
        """Wrap LOTUS tool for MCP protocol"""
        async def mcp_tool(**params):
            # Publish to reasoning engine
            await self.publish("cognition.tool_call", {
                "tool": tool_name,
                "params": params,
                "protocol": "mcp"
            })
            
            # Wait for result
            result = await self.wait_for_result(tool_name)
            return result
        
        return mcp_tool
    
    @on_event("cognition.mcp_request")
    async def handle_mcp_request(self, event):
        """Handle MCP protocol requests"""
        tool = event.data["tool"]
        params = event.data["params"]
        
        # Execute tool
        result = await self.server.execute_tool(tool, params)
        
        await self.publish("action.mcp_response", {
            "tool": tool,
            "result": result
        })
```

---

## 🧠 Reasoning Engine (ReAct Loop)

The reasoning module is where LOTUS "thinks":

```python
# modules/core_modules/reasoning/logic.py
class ReasoningEngine(BaseModule):
    """
    The brain of LOTUS - ReAct (Reason + Act) loop
    
    Flow:
    1. THINK: Analyze context, recall memories, understand goal
    2. REASON: Break down problem, identify tools needed
    3. ACT: Execute tools, delegate tasks, take actions
    4. OBSERVE: Monitor results, detect errors
    5. LEARN: Store successful patterns, adjust approach
    6. LOOP: Continue until goal achieved
    """
    
    @on_event("perception.user_input")
    async def on_user_input(self, event):
        """Main entry point for user requests"""
        user_message = event.data["text"]
        context = await self.build_context(user_message)
        
        await self.think_act_loop(context)
    
    async def think_act_loop(self, initial_context):
        """The core ReAct loop"""
        context = initial_context
        max_iterations = 10
        
        for iteration in range(max_iterations):
            # THINK: What should I do next?
            thought = await self.think(context)
            
            if thought.is_complete:
                await self.respond(thought.response)
                break
            
            # ACT: Execute the planned actions
            results = await self.act(thought.actions)
            
            # OBSERVE: Analyze the results
            observations = await self.observe(results)
            
            # LEARN: Update memory with successful patterns
            await self.learn(thought, results)
            
            # Update context for next iteration
            context = await self.update_context(context, thought, observations)
    
    async def think(self, context: dict) -> Thought:
        """
        Reason about the situation
        
        Returns a Thought object containing:
        - understanding: What the user wants
        - plan: Steps to accomplish it
        - actions: Specific actions to take
        - reasoning: Why these actions
        """
        # Get relevant memories
        memories = await self.memory.recall(context["query"])
        
        # Get available tools
        tools = await self.get_available_tools()
        
        # Build prompt for LLM
        prompt = self.build_reasoning_prompt(context, memories, tools)
        
        # Ask LLM to reason
        response = await self.llm.complete(
            prompt=prompt,
            provider=self.config.providers.reasoning,
            temperature=0.7
        )
        
        # Parse response into structured Thought
        thought = self.parse_thought(response)
        
        return thought
    
    async def act(self, actions: List[Action]) -> List[Result]:
        """Execute planned actions"""
        results = []
        
        for action in actions:
            if action.type == "tool_call":
                result = await self.execute_tool(action)
            elif action.type == "delegate":
                result = await self.delegate_task(action)
            elif action.type == "respond":
                result = await self.respond_to_user(action)
            elif action.type == "query_memory":
                result = await self.query_memory(action)
            
            results.append(result)
            
            # Check if we should stop early
            if result.should_stop:
                break
        
        return results
    
    async def execute_tool(self, action: Action) -> Result:
        """Execute a tool call"""
        tool_name = action.tool
        params = action.params
        
        # Publish tool call event
        await self.publish("cognition.tool_call", {
            "tool": tool_name,
            "params": params
        })
        
        # Wait for tool result
        result = await self.wait_for_event(
            "action.tool_result",
            filter=lambda e: e.data["tool"] == tool_name,
            timeout=30.0
        )
        
        return Result(
            success=result.data["success"],
            data=result.data["result"],
            error=result.data.get("error")
        )
    
    async def delegate_task(self, action: Action) -> Result:
        """Delegate complex task to specialized LLM"""
        task = action.task
        target_provider = self.select_provider_for_task(task)
        
        await self.publish("cognition.delegate", {
            "task": task,
            "provider": target_provider,
            "callback": f"{self.name}.receive_delegation"
        })
        
        # Wait for delegated result
        result = await self.wait_for_event(
            f"{self.name}.receive_delegation",
            timeout=120.0
        )
        
        return Result(
            success=True,
            data=result.data["result"]
        )
    
    def select_provider_for_task(self, task: dict) -> str:
        """Intelligently select best LLM for task"""
        complexity = task.get("complexity", "medium")
        domain = task.get("domain", "general")
        
        # Route to appropriate model
        if complexity == "high" or domain == "architecture":
            return "claude-opus-4"
        elif domain == "code":
            return "claude-sonnet-4"
        elif complexity == "low":
            return "gpt-4o-mini"
        else:
            return self.config.providers.default
```

---

## 🎯 Self-Modification System

The crown jewel - LOTUS writing her own modules:

```python
# modules/capability_modules/self_modifier/logic.py
class SelfModifierModule(BaseModule):
    """
    Enables LOTUS to write, test, and deploy her own modules
    
    Process:
    1. Analyze need (what capability is missing?)
    2. Design module (architecture, interfaces)
    3. Generate code (manifest, logic, tests)
    4. Test in sandbox (isolated environment)
    5. Validate safety (security checks)
    6. Deploy (install into live system)
    7. Monitor (ensure it works correctly)
    """
    
    @on_event("cognition.capability_missing")
    async def on_missing_capability(self, event):
        """Triggered when LOTUS realizes she can't do something"""
        capability_needed = event.data["capability"]
        context = event.data["context"]
        
        await self.generate_module(capability_needed, context)
    
    async def generate_module(self, capability: str, context: dict):
        """Generate a new module from scratch"""
        
        # STEP 1: Analyze and Design
        design = await self.design_module(capability, context)
        
        # STEP 2: Generate Code
        module_code = await self.generate_code(design)
        
        # STEP 3: Test in Sandbox
        test_results = await self.test_module(module_code)
        
        if not test_results.passed:
            # Try to fix issues
            module_code = await self.fix_issues(module_code, test_results)
            test_results = await self.test_module(module_code)
            
            if not test_results.passed:
                await self.publish("action.speak", {
                    "text": f"I tried to create a {capability} module but "
                            f"couldn't get it working. The tests failed."
                })
                return
        
        # STEP 4: Safety Validation
        safety_check = await self.validate_safety(module_code)
        
        if not safety_check.is_safe:
            await self.publish("action.speak", {
                "text": f"I created a {capability} module but it failed "
                        f"safety checks: {safety_check.reason}"
            })
            return
        
        # STEP 5: Deploy
        await self.deploy_module(module_code)
        
        await self.publish("action.speak", {
            "text": f"Great! I just created and installed a {capability} "
                    f"module. It's now available for use!"
        })
    
    async def design_module(self, capability: str, context: dict) -> ModuleDesign:
        """Design the module architecture"""
        
        # Use powerful model for architecture design
        prompt = f"""
        I need to create a new module for LOTUS AI OS with this capability: {capability}
        
        Context: {json.dumps(context, indent=2)}
        
        Design a module following the LOTUS module specification:
        - manifest.yaml (subscriptions, publications, dependencies, tools)
        - logic.py (main module class with event handlers and tools)
        - Any additional files needed
        
        The module must:
        1. Be self-contained (no external file dependencies)
        2. Follow BaseModule interface
        3. Use event-driven communication only
        4. Handle errors gracefully
        5. Include comprehensive logging
        
        Return the complete module design as JSON.
        """
        
        response = await self.llm.complete(
            prompt=prompt,
            provider="claude-opus-4",  # Use smartest model for design
            temperature=0.3
        )
        
        design = json.loads(response)
        return ModuleDesign(**design)
    
    async def generate_code(self, design: ModuleDesign) -> ModuleCode:
        """Generate the actual code files"""
        
        manifest_code = await self.generate_manifest(design)
        logic_code = await self.generate_logic(design)
        additional_files = await self.generate_additional_files(design)
        
        return ModuleCode(
            manifest=manifest_code,
            logic=logic_code,
            additional=additional_files
        )
    
    async def generate_logic(self, design: ModuleDesign) -> str:
        """Generate the main logic.py file"""
        
        prompt = f"""
        Generate the logic.py file for a LOTUS module with this design:
        
        {json.dumps(design.dict(), indent=2)}
        
        Requirements:
        1. Must inherit from BaseModule
        2. Implement all event handlers from manifest
        3. Implement all tools from manifest
        4. Include error handling and logging
        5. Follow Python best practices
        6. Add type hints
        7. Include docstrings
        
        Generate ONLY the Python code, no explanations.
        """
        
        code = await self.llm.complete(
            prompt=prompt,
            provider="claude-sonnet-4",  # Good at code generation
            temperature=0.2
        )
        
        return code
    
    async def test_module(self, module_code: ModuleCode) -> TestResults:
        """Test the module in an isolated sandbox"""
        
        # Create sandbox environment
        sandbox = await self.create_sandbox()
        
        try:
            # Install module in sandbox
            await sandbox.install_module(module_code)
            
            # Run tests
            results = await sandbox.run_tests(module_code.tests)
            
            return results
            
        finally:
            await sandbox.cleanup()
    
    async def validate_safety(self, module_code: ModuleCode) -> SafetyCheck:
        """Check if module is safe to deploy"""
        
        checks = []
        
        # Check 1: No dangerous imports
        if self.has_dangerous_imports(module_code.logic):
            checks.append("Contains dangerous imports (os.system, subprocess, etc)")
        
        # Check 2: No file system access outside allowed paths
        if self.has_unauthorized_file_access(module_code.logic):
            checks.append("Attempts unauthorized file system access")
        
        # Check 3: No network access without permission
        if self.has_unauthorized_network(module_code.logic):
            checks.append("Attempts network access without permission")
        
        # Check 4: Code analysis for vulnerabilities
        vulnerabilities = await self.analyze_for_vulnerabilities(module_code.logic)
        checks.extend(vulnerabilities)
        
        is_safe = len(checks) == 0
        
        return SafetyCheck(
            is_safe=is_safe,
            issues=checks,
            reason="; ".join(checks) if checks else "All safety checks passed"
        )
    
    async def deploy_module(self, module_code: ModuleCode):
        """Deploy the module to the live system"""
        
        module_name = module_code.manifest["name"]
        module_dir = f"modules/capability_modules/{module_name}"
        
        # Create module directory
        os.makedirs(module_dir, exist_ok=True)
        
        # Write files
        with open(f"{module_dir}/manifest.yaml", "w") as f:
            yaml.dump(module_code.manifest, f)
        
        with open(f"{module_dir}/logic.py", "w") as f:
            f.write(module_code.logic)
        
        with open(f"{module_dir}/module.json", "w") as f:
            json.dump(module_code.metadata, f, indent=2)
        
        # Tell nucleus to load it (hot reload!)
        await self.publish("system.load_module", {
            "name": module_name,
            "type": "capability"
        })
        
        # Store in memory for future reference
        await self.memory.remember(f"Created module: {module_name}", type="module_creation")
```

---

## 💾 Memory System Details

### Four-Tier Memory Architecture

```python
# modules/core_modules/memory/logic.py
class MemorySystem(BaseModule):
    """
    Four-tier memory system inspired by human cognition:
    
    L1 (Working Memory): Immediate context, fast access
    L2 (Short-term): Recent history, quick retrieval
    L3 (Long-term): Semantic memories, vector search
    L4 (Persistent): Structured knowledge, relational
    """
    
    async def initialize(self):
        # L1: Redis (sub-second access)
        self.l1 = WorkingMemory(redis_client=self.redis)
        
        # L2: Redis Streams (recent history)
        self.l2 = ShortTermMemory(redis_client=self.redis)
        
        # L3: ChromaDB (vector search)
        self.l3 = LongTermMemory(chroma_client=self.chromadb)
        
        # L4: PostgreSQL (structured data)
        self.l4 = PersistentMemory(db_client=self.postgres)
        
        # Start background consolidation
        asyncio.create_task(self.consolidation_loop())
    
    async def remember(self, content: str, type: str = "episodic"):
        """Store a memory across appropriate tiers"""
        
        # Always store in working memory first
        await self.l1.store(content, type)
        
        # Add to short-term stream
        await self.l2.append(content, type)
        
        # If important, immediately add to long-term
        importance = await self.calculate_importance(content)
        if importance > 0.7:
            embedding = await self.embed(content)
            await self.l3.store(embedding, content, type, importance)
    
    async def recall(self, query: str, limit: int = 10) -> List[Memory]:
        """Retrieve relevant memories"""
        
        memories = []
        
        # Check working memory first (fastest)
        working_mem = await self.l1.search(query, limit=5)
        memories.extend(working_mem)
        
        # Check short-term memory
        recent_mem = await self.l2.search(query, limit=5)
        memories.extend(recent_mem)
        
        # Vector search in long-term memory
        if len(memories) < limit:
            query_embedding = await self.embed(query)
            long_term = await self.l3.search(
                query_embedding, 
                limit=limit - len(memories)
            )
            memories.extend(long_term)
        
        # Rank by relevance and recency
        memories = self.rank_memories(memories, query)
        
        return memories[:limit]
    
    async def consolidation_loop(self):
        """
        Background process that moves memories between tiers
        
        Runs every 5 minutes:
        1. Review working memory
        2. Important items → long-term
        3. Old items → expire or archive
        4. Summarize short-term history
        """
        while True:
            await asyncio.sleep(300)  # 5 minutes
            
            try:
                await self.consolidate()
            except Exception as e:
                self.logger.error(f"Consolidation error: {e}")
    
    async def consolidate(self):
        """Consolidate memories from short-term to long-term"""
        
        # Get last hour from short-term
        recent = await self.l2.get_range(
            start_time=time.time() - 3600
        )
        
        # Summarize and extract key points
        summary = await self.llm.complete(
            prompt=f"Summarize these recent interactions:\n{recent}",
            provider="gpt-4o-mini"
        )
        
        # Extract important concepts
        concepts = await self.extract_concepts(summary)
        
        # Store in long-term memory
        for concept in concepts:
            embedding = await self.embed(concept)
            await self.l3.store(embedding, concept, "consolidated")
        
        # Clean up working memory
        await self.l1.prune_old(max_age=600)  # Keep last 10 minutes
```

---

This architecture document continues with more technical details about provider abstraction, tool systems, IDE integrations, and deployment strategies. The key insight is that EVERY piece is modular and can be added/removed/replaced without touching the core.

**Want me to continue building out the actual implementation? I'll start with the nucleus.py and core lib files.**