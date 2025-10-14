# LOTUS Modules Directory

This directory contains all LOTUS modules organized by type.

## ðŸ"‚ Directory Structure

```
modules/
â"œâ"€â"€ core_modules/          # System-critical modules (always loaded)
â"‚   â"œâ"€â"€ reasoning/         âœ… ReAct reasoning engine
â"‚   â"œâ"€â"€ memory/            âœ… 4-tier memory system
â"‚   â"œâ"€â"€ providers/         âœ… LLM provider management
â"‚   â""â"€â"€ perception/        âœ… Input monitoring
â"‚
â"œâ"€â"€ capability_modules/   # Optional features (user-installable)
â"‚   â"œâ"€â"€ voice_interface/   ðŸš§ Speech I/O (TODO)
â"‚   â"œâ"€â"€ screen_analyzer/   ðŸš§ Screen capture (TODO)
â"‚   â"œâ"€â"€ code_assistant/    ðŸš§ Coding companion (TODO)
â"‚   â"œâ"€â"€ task_delegator/    ðŸš§ Multi-LLM orchestration (TODO)
â"‚   â""â"€â"€ self_modifier/     ðŸš§ AI writes modules (TODO)
â"‚
â"œâ"€â"€ integration_modules/  # Third-party integrations
â"‚   â"œâ"€â"€ computer_use/      ðŸš§ Computer control (TODO)
â"‚   â"œâ"€â"€ mcp_protocol/      ðŸš§ Model Context Protocol (TODO)
â"‚   â"œâ"€â"€ browser_control/   ðŸš§ Web automation (TODO)
â"‚   â""â"€â"€ ide_integration/   ðŸš§ IDE connections (TODO)
â"‚
â""â"€â"€ example_modules/      # Example modules for learning
    â""â"€â"€ hello_world/       âœ… Simple example module
```

## ðŸ" Module Structure

Every module MUST have this structure:

```
module_name/
â"œâ"€â"€ __init__.py           # Python package marker
â"œâ"€â"€ manifest.yaml         # Module contract (REQUIRED)
â"œâ"€â"€ module.json          # Module metadata (REQUIRED)
â"œâ"€â"€ logic.py             # Main module logic (REQUIRED)
â"œâ"€â"€ [additional_files]   # Optional additional code
â""â"€â"€ README.md            # Module documentation (recommended)
```

### manifest.yaml

Defines the module's interface with the system:

```yaml
name: my_module
version: 1.0.0
type: core  # or capability, integration, example
priority: normal  # critical, high, normal, low
description: "What this module does"

capabilities:
  - capability_1
  - capability_2

subscriptions:
  - pattern: "event.pattern"
    description: "What event this handles"

publications:
  - event: "module.event"
    description: "Event this module publishes"

dependencies:
  - other_module_name

config:
  setting1: value1
  setting2: value2
```

### module.json

Metadata about the module:

```json
{
  "name": "my_module",
  "version": "1.0.0",
  "display_name": "My Module",
  "description": "Detailed description",
  "author": "Your Name",
  "license": "MIT",
  "requirements": {
    "python": ">=3.10",
    "packages": [
      "some-package>=1.0.0"
    ]
  }
}
```

### logic.py

Main module implementation:

```python
from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic

class MyModule(BaseModule):
    async def initialize(self) -> None:
        """Initialize the module"""
        self.logger.info("My module starting")
        # Your initialization code
    
    @on_event("some.event")
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle an event"""
        # Your event handling code
        await self.publish("module.response", {"data": "..."})
    
    @tool("my_tool")
    async def my_tool(self, arg1: str) -> Any:
        """A tool that can be called"""
        return {"result": "..."}
    
    @periodic(interval=60)
    async def periodic_task(self) -> None:
        """Runs every 60 seconds"""
        # Your periodic task code
    
    async def shutdown(self) -> None:
        """Clean shutdown"""
        self.logger.info("My module shutting down")
```

## âœ… Completed Modules

### Core Modules

1. **reasoning** ðŸ§  (70% complete)
   - ReAct reasoning loop
   - Think-Act-Observe-Learn cycle
   - Tool execution
   - Memory integration
   
2. **memory** ðŸ'¾ (âœ… 100% complete)
   - 4-tier architecture
   - Automatic consolidation
   - Semantic search
   - Multi-tier retrieval
   
3. **providers** ðŸ"Œ (âœ… 100% complete)
   - Claude, GPT, Gemini, Ollama
   - Smart routing
   - Fallback handling
   - Cost optimization
   
4. **perception** ðŸ'ï¸ (âœ… 100% complete)
   - File watching
   - Clipboard monitoring
   - Context awareness
   - Real-time updates

### Example Modules

1. **hello_world** ðŸ'‹ (100% complete)
   - Simple example
   - Shows basic patterns
   - Good starting point

## ðŸš§ Modules To Build

### High Priority (Week 2-3)
- **code_assistant**: Real-time coding companion
- **voice_interface**: Speech I/O with STT/TTS
- **screen_analyzer**: Screen capture and analysis

### Medium Priority (Week 3-4)
- **computer_use**: Full computer control
- **mcp_protocol**: Model Context Protocol integration
- **task_delegator**: Multi-LLM orchestration

### Revolutionary Feature (Week 4+)
- **self_modifier**: AI writes and installs its own modules ðŸ"¥

## ðŸ"§ Creating a New Module

### 1. Generate Template

```bash
cd lotus
python scripts/dev/generate_module.py my_module --type capability
```

### 2. Implement Logic

Edit the generated files:
- Fill in `manifest.yaml` with events and config
- Complete `logic.py` with your code
- Update `module.json` with metadata

### 3. Test Module

```bash
python scripts/dev/test_module.py my_module
```

### 4. Install Module

```bash
python cli.py install my_module
```

The module will be hot-loaded into LOTUS without restart!

## ðŸ"š Best Practices

### Event Handling
- Use descriptive event names: `module.action.result`
- Always include timestamp in events
- Handle errors gracefully

### Module Communication
- âœ… Use events for async communication
- âœ… Use tools for synchronous operations
- âŒ Never directly call other modules

### State Management
- Store state in module instance variables
- Use memory system for persistent state
- Publish state changes as events

### Error Handling
- Always wrap operations in try/except
- Log errors with context
- Publish error events for monitoring

### Performance
- Keep event handlers fast (<100ms)
- Use async/await properly
- Offload heavy work to background tasks

## ðŸŽ¯ Module Checklist

Before publishing a module:

- [ ] manifest.yaml is complete and valid
- [ ] module.json has all metadata
- [ ] logic.py inherits from BaseModule
- [ ] All event handlers are decorated
- [ ] Module has graceful shutdown
- [ ] README.md documents usage
- [ ] Code follows style guide
- [ ] Tests are written and passing
- [ ] Dependencies are documented

## 🌟 Module Ideas

Ideas for community modules:

### Productivity
- Calendar integration
- Email management
- Task tracking
- Note taking

### Development
- Git integration
- Code review assistant
- Test generator
- Documentation writer

### Research
- Paper summarizer
- Web scraper
- Data analyzer
- Knowledge graph builder

### Entertainment
- Music player control
- Game integration
- Social media manager
- Content creator

### Home Automation
- Smart home control
- IoT integration
- Automation scripts
- Energy monitoring

## ðŸ"– Documentation

For more details:
- **Architecture**: `docs/ARCHITECTURE.md`
- **Module Development**: `docs/MODULE_DEVELOPMENT.md`
- **API Reference**: `docs/API_REFERENCE.md`

## ðŸ†˜ Getting Help

If you're building a module and need help:
1. Check the `example_modules/hello_world` module
2. Review the core modules for patterns
3. Check the documentation
4. Ask in the community

---

**Happy Module Building! ðŸŒ¸**