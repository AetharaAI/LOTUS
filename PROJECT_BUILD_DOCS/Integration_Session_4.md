# QUICK INTEGRATION GUIDE - Session 4

## 🔌 How to Integrate the New Modules

### Step 1: Copy Files to Your Project

```bash
# From /mnt/user-data/outputs/lotus/ to your actual lotus/ directory

# 1. Persona config
cp config/persona.yaml /your/lotus/config/

# 2. Prompt builder
cp modules/core_modules/reasoning/prompt_builder.py /your/lotus/modules/core_modules/reasoning/

# 3. Code Assistant module
cp -r modules/capability_modules/code_assistant/ /your/lotus/modules/capability_modules/

# 4. Computer Use module
cp -r modules/integration_modules/computer_use/ /your/lotus/modules/integration_modules/
```

### Step 2: Update Reasoning Engine

In `/lotus/modules/core_modules/reasoning/logic.py`, update the `initialize()` method:

```python
from .prompt_builder import PersonaAwarePromptBuilder

class ReasoningEngine(BaseModule):
    
    async def initialize(self):
        """Initialize with persona awareness"""
        await super().initialize()
        
        # Load persona configuration ⭐ ADD THIS
        self.prompt_builder = PersonaAwarePromptBuilder(
            config_path="config/persona.yaml"
        )
        
        self.logger.info(
            f"Reasoning engine initialized with persona: {self.prompt_builder.name}"
        )
        
        # Get persona-driven settings
        self.max_iterations = self.prompt_builder.get_max_iterations()
        self.thinking_depth = self.prompt_builder.get_thinking_depth()
        self.tool_autonomy = self.prompt_builder.get_tool_autonomy_level()
```

Then update the `_build_reasoning_prompt` method:

```python
# OLD (hardcoded):
def _build_reasoning_prompt(self, context, memories, tools):
    prompt = f"""You are LOTUS, an AI assistant..."""
    return prompt

# NEW (persona-driven):
async def think(self, context: Dict) -> Thought:
    """Think with persona-aware prompting"""
    
    # Get relevant memories
    memories = await self.memory.recall(context["query"])
    
    # Get available tools
    tools = await self._get_available_tools()
    
    # Build prompt using persona configuration ⭐ USE THIS
    prompt = self.prompt_builder.build_reasoning_prompt(
        context=context,
        memories=memories,
        tools=tools,
        additional_context={
            "project": "LOTUS",
            "user": "Cory",
            "autonomy_mode": self.tool_autonomy
        }
    )
    
    # Continue with rest of think() method...
```

### Step 3: Register New Modules

The modules will auto-load if in the correct directories, but you can explicitly enable them in `/lotus/config/system.yaml`:

```yaml
modules:
  core:
    - reasoning
    - memory
    - perception
  
  capability:
    - code_assistant  # ⭐ ADD THIS
  
  integration:
    - computer_use    # ⭐ ADD THIS
```

### Step 4: Install Dependencies

```bash
# For Code Assistant
pip install tree-sitter watchdog jedi pylint black

# For Computer Use
pip install pyautogui mss pillow opencv-python

# Or install all at once:
pip install -r requirements.txt
```

### Step 5: Configure Persona

Edit `/lotus/config/persona.yaml` to customize Ash's personality:

```yaml
persona:
  name: "Ash"
  
  # Adjust these to your preferences
  personality:
    primary_traits:
      - analytical
      - proactive
      - autonomous
      - curious
      - direct
  
  # Control tool autonomy
  tool_usage:
    autonomy_level: "high"  # or "medium", "low"
    
    auto_execute:
      - "Code analysis"
      - "File operations"
      - "Web searches"
    
    require_confirmation:
      - "System modifications"
      - "Code execution"
```

### Step 6: Test Code Assistant

```python
# test_code_assistant.py
import asyncio
from nucleus import Nucleus

async def test_code_assistant():
    nucleus = Nucleus()
    await nucleus.boot()
    
    # Wait for modules to load
    await asyncio.sleep(2)
    
    # Test code analysis
    await nucleus.message_bus.publish("cognition.code_request", {
        "type": "analyze",
        "params": {
            "file_path": "test.py"
        }
    })
    
    # Wait for result
    await asyncio.sleep(5)
    
    print("Check logs for analysis results!")

if __name__ == "__main__":
    asyncio.run(test_code_assistant())
```

### Step 7: Test Computer Use

```python
# test_computer_use.py
import asyncio
from nucleus import Nucleus

async def test_computer_use():
    nucleus = Nucleus()
    await nucleus.boot()
    
    await asyncio.sleep(2)
    
    # Test screenshot
    await nucleus.message_bus.publish("cognition.computer_action", {
        "action": "screenshot",
        "params": {}
    })
    
    await asyncio.sleep(2)
    
    # Test mouse move
    await nucleus.message_bus.publish("cognition.computer_action", {
        "action": "mouse_move",
        "params": {"x": 100, "y": 100}
    })
    
    print("Check logs for computer actions!")

if __name__ == "__main__":
    asyncio.run(test_computer_use())
```

---

## ⚙️ Configuration Tips

### Adjust Autonomy Level

In `persona.yaml`:

```yaml
# Conservative (always asks)
autonomy_level: "low"

# Balanced (asks for risky stuff)
autonomy_level: "medium"

# Autonomous (just does it)
autonomy_level: "high"
```

### Customize Communication Style

```yaml
persona:
  communication_style:
    tone: "intelligent-casual"  # professional, casual, technical
    humor: "witty"               # none, dry, witty, playful
    verbosity: "adaptive"        # terse, adaptive, detailed
```

### Add Safety Boundaries

```yaml
safety:
  hard_boundaries:
    - "Delete system files"
    - "Execute untrusted code"
    # Add your own
  
  soft_boundaries:
    - "Major refactoring"
    # Add your own
```

---

## 🐛 Troubleshooting

### Issue: Module not loading

**Solution**: Check logs in `/lotus/data/logs/nucleus.log`:

```bash
tail -f data/logs/nucleus.log | grep code_assistant
```

### Issue: Persona config not found

**Solution**: Verify path in reasoning engine:

```python
self.prompt_builder = PersonaAwarePromptBuilder(
    config_path="config/persona.yaml"  # Relative to project root
)
```

### Issue: Tools not being called

**Solution**: Check tool registration in `tool_manager.py`:

```python
# Make sure new module tools are registered
await self.register_module_tools()
```

### Issue: Code Assistant not watching files

**Solution**: Check config:

```yaml
file_watching:
  enabled: true
  directories:
    - "."  # Current directory
```

### Issue: Computer Use actions blocked

**Solution**: Check safety settings:

```yaml
autonomy:
  require_confirmation:
    - mouse_click  # Remove if you want auto-clicking
```

---

## 📊 Verification Checklist

After integration, verify:

- [ ] Persona config loads without errors
- [ ] Reasoning engine uses prompt_builder
- [ ] Code Assistant module appears in logs
- [ ] Computer Use module appears in logs
- [ ] Tools are registered and callable
- [ ] Events are published and received
- [ ] Autonomous actions work (if enabled)
- [ ] Safety boundaries are respected

---

## 🚀 Next Steps

1. **Test the basics** - Run test scripts
2. **Customize persona** - Adjust persona.yaml
3. **Watch it work** - Give Ash real tasks
4. **Tune autonomy** - Adjust based on results
5. **Add memory tiers** - Complete the system

---

## 💡 Pro Tips

### 1. Start Conservative

Begin with `autonomy_level: "medium"` and increase as you get comfortable.

### 2. Use the Logs

Watch logs in real-time to see Ash's decision-making:

```bash
tail -f data/logs/nucleus.log | grep -E "(THINK|ACT|OBSERVE|LEARN)"
```

### 3. Iterate on Persona

The persona config is HOT-RELOADABLE. Edit it while Ash is running and she'll adapt.

### 4. Build Tool Library

Add more tools to `tool_manager.py`:

```python
@tool("my_custom_tool")
async def my_tool(self, param: str):
    """My custom functionality"""
    return result
```

### 5. Monitor Performance

Check Redis for event flow:

```bash
redis-cli monitor | grep lotus
```

---

## 📝 Quick Reference

### Key Files:
- **Persona**: `/lotus/config/persona.yaml`
- **Prompt Builder**: `/lotus/modules/core_modules/reasoning/prompt_builder.py`
- **Reasoning**: `/lotus/modules/core_modules/reasoning/logic.py`
- **Code Assistant**: `/lotus/modules/capability_modules/code_assistant/logic.py`
- **Computer Use**: `/lotus/modules/integration_modules/computer_use/logic.py`

### Key Events:
- `perception.user_input` - User says something
- `cognition.code_request` - Code task needed
- `cognition.computer_action` - Computer control needed
- `code.analysis_complete` - Code analysis done
- `computer.action_complete` - Computer action done

### Key Tools:
- `analyze_code` - Analyze code file
- `generate_code` - Generate new code
- `fix_issue` - Fix detected issue
- `screenshot` - Capture screen
- `mouse_click` - Click mouse
- `type_text` - Type text

---

**Ready to test?** Run the integration steps above and let Ash come alive! 🚀