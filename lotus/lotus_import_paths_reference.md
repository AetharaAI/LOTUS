# 🔗 LOTUS IMPORT PATHS & MODULE STRUCTURE REFERENCE
## Definitive Guide to Consistent Imports Across LOTUS

---

## 📍 PROJECT STRUCTURE & PATHS

```
lotus/                                    # Project root
│
├── lib/                                  # Core library (SYSTEM CORE)
│   ├── __init__.py
│   ├── module.py                         # BaseModule class
│   ├── decorators.py                     # @on_event, @tool, @periodic
│   ├── message_bus.py                    # Redis communication
│   ├── memory.py                         # 4-tier memory system
│   ├── providers.py                      # LLM provider abstraction ⭐ XAI HERE
│   ├── config.py                         # Configuration loader
│   ├── logging.py                        # Logging system
│   ├── exceptions.py                     # Custom exceptions
│   ├── utils.py                          # Utility functions
│   ├── security.py                       # Security utilities
│   └── validators.py                     # Input validation
│
├── modules/                              # Module ecosystem
│   ├── __init__.py
│   ├── core_modules/                     # ALWAYS LOADED
│   │   ├── __init__.py
│   │   ├── reasoning/                    # ReAct reasoning engine
│   │   │   ├── __init__.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   └── logic.py
│   │   ├── memory/
│   │   ├── providers/
│   │   └── perception/
│   │
│   ├── capability_modules/               # OPTIONAL - LOADED IF ENABLED
│   │   ├── __init__.py
│   │   ├── screen_analyzer/              # ⭐ NEW
│   │   ├── voice_interface/              # ⭐ NEW
│   │   ├── task_delegator/               # ⭐ NEW
│   │   ├── self_modifier/                # ⭐ NEW
│   │   ├── code_assistant/
│   │   └── ...others
│   │
│   └── integration_modules/              # ON-DEMAND
│       ├── __init__.py
│       ├── mcp_protocol/                 # ⭐ NEW
│       ├── browser_control/              # ⭐ NEW
│       ├── ide_integration/              # ⭐ NEW
│       ├── computer_use/
│       └── ...others
│
├── config/                               # Configuration files
│   ├── system.yaml
│   ├── providers.yaml                    # ⭐ HAS XAI CONFIG
│   └── modules/
│
├── data/                                 # Runtime data
│   ├── memory/
│   ├── knowledge/
│   ├── logs/
│   └── state/
│
├── scripts/                              # Utility scripts
│   ├── validate_lotus.py                 # ⭐ NEW
│   ├── install_module.py                 # ⭐ NEW
│   └── ...others
│
├── tests/                                # Test suite
│   ├── conftest.py                       # ⭐ NEW - Pytest fixtures
│   ├── test_modules.py
│   └── ...others
│
├── nucleus.py                            # Core runtime (ENTRY POINT)
├── cli.py                                # Command-line interface
├── requirements.txt                      # ⭐ HAS XAI DEPS
├── .env.example                          # ⭐ HAS XAI_API_KEY
└── README.md
```

---

## 📦 IMPORT PATTERNS

### Pattern 1: Imports FROM lib (Most Common)

**Location**: Any module file (`modules/*/logic.py`)

```python
# ✅ CORRECT: Import from lib (relative to project root)
from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic
from lib.message_bus import MessageBus
from lib.memory import MemorySystem
from lib.providers import ProviderManager, LLMResponse
from lib.config import Config
from lib.logging import get_logger
from lib.exceptions import LOTUSException
from lib.utils import parse_yaml, normalize_text
from lib.security import validate_input
from lib.validators import validate_url
```

**Why**: lib/* is core system code used by all modules

---

### Pattern 2: Imports WITHIN Modules

**Location**: Module subdirectories

```python
# ✅ CORRECT: Import within module (use relative imports or absolute)
from logic import SomeClass              # Relative (from same dir)
from modules.capability_modules.task_delegator.task_analyzer import TaskAnalyzer  # Absolute

# ❌ WRONG: Don't use relative parent imports
# from ..logic import SomeClass  # Don't do this
```

---

### Pattern 3: Script Imports

**Location**: `scripts/` directory

```python
# ✅ CORRECT: Scripts can use sys.path manipulation
import sys
from pathlib import Path
LOTUS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LOTUS_ROOT))

# Now can import
from lib.config import Config
from lib.logging import get_logger

# Or use relative
import os
os.chdir(LOTUS_ROOT)
```

---

### Pattern 4: CLI Imports

**Location**: `cli.py` (project root)

```python
# ✅ CORRECT: At project root level
from lib.module import BaseModule
from lib.config import Config
from modules.core_modules.reasoning.logic import ReasoningModule
```

---

### Pattern 5: Test Imports

**Location**: `tests/` directory

```python
# ✅ CORRECT: In conftest.py and test files
import sys
from pathlib import Path

LOTUS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LOTUS_ROOT))

from lib.module import BaseModule
from lib.config import Config
```

---

## 🔌 PROVIDER IMPORTS (IMPORTANT!)

### Using xAI Provider

**In lib/providers.py**:
```python
from enum import Enum
import os
import requests  # ⭐ FOR XAI

class ProviderType(Enum):
    # ... existing providers ...
    XAI = "xai"  # ⭐ ADD THIS

class XAIProvider(BaseProvider):  # ⭐ ADD THIS CLASS
    """xAI (Grok) provider"""
    def __init__(self, config: Dict[str, Any], api_key: str = None):
        super().__init__(config)
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        # ... rest of implementation ...
```

**In modules**:
```python
# Access provider through message bus
await self.publish("llm.complete", {
    "prompt": "Your prompt",
    "provider": "grok-4-fast",  # ⭐ NEW DEFAULT
    "max_tokens": 4000
})
```

---

## 🧠 MODULE IMPORTS (STANDARD PATTERN)

### Every new module should import:

**Required**:
```python
from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic
from lib.logging import get_logger
```

**Optional** (as needed):
```python
from lib.message_bus import MessageBus
from lib.memory import MemorySystem
from lib.config import Config
from lib.exceptions import LOTUSException
```

### Example: Screen Analyzer Module

```python
# modules/capability_modules/screen_analyzer/logic.py

# ✅ CORRECT IMPORTS
import asyncio
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

# Third-party
try:
    import mss
    import pytesseract
    from PIL import Image
    import io
except ImportError as e:
    print(f"Warning: {e}")

# LOTUS core
from lib.module import BaseModule              # ✅ Core class
from lib.decorators import on_event, tool     # ✅ Decorators
from lib.logging import get_logger            # ✅ Logging

logger = get_logger("screen_analyzer")        # ✅ Create logger

class ScreenAnalyzer(BaseModule):
    """Module implementation"""
    pass
```

---

## 📋 INITIALIZATION PATTERNS

### Pattern: Module Initialization

```python
class MyModule(BaseModule):
    
    async def initialize(self) -> None:
        """Called once when module loads"""
        self.logger.info("🚀 Initializing MyModule")
        
        # Access config
        self.setting1 = self.config.get("module.setting1", "default")
        
        # Initialize components
        self.component = await self._init_component()
        
        self.logger.info("✅ MyModule ready")
    
    @on_event("my.event")
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle events"""
        pass
    
    @tool("my_tool")
    async def my_tool(self, param: str) -> Dict:
        """Callable tool"""
        return {"result": param}
```

---

## 🔄 CONFIGURATION IMPORTS

### Pattern: Load Configuration

```python
# In module initialization
class MyModule(BaseModule):
    async def initialize(self) -> None:
        # ✅ Access configuration (inherited from BaseModule)
        self.config = self.config  # BaseModule provides this
        
        # Get values with defaults
        enabled = self.config.get("my_module.enabled", True)
        timeout = self.config.get("my_module.timeout", 30)
        
        # For xAI configuration
        xai_enabled = self.config.get("providers.xai.enabled", True)
        xai_model = self.config.get("providers.xai.default_model", "grok-4-fast")
```

**Configuration file**: `config/providers.yaml`
```yaml
providers:
  default_provider: "grok-4-fast"      # ⭐ xAI is default
  
  xai:
    enabled: true
    models:
      - grok-4-fast
      - grok-4
    default_model: "grok-4-fast"
```

---

## 🧪 TEST IMPORTS

### Pattern: Import in Tests

```python
# tests/conftest.py

import sys
from pathlib import Path

# Set up path
LOTUS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LOTUS_ROOT))

# Import from lib
from lib.config import Config
from lib.message_bus import MessageBus
from lib.logging import get_logger

# Create fixtures
@pytest.fixture
def config():
    config_path = LOTUS_ROOT / "config"
    return Config(config_path)

@pytest.fixture
async def message_bus(config):
    bus = MessageBus(config.get("redis_host", "localhost"))
    yield bus
    await bus.cleanup()
```

### Pattern: Import in Test Files

```python
# tests/test_my_module.py

import pytest
from pathlib import Path
import sys

# Same path setup
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.module import BaseModule
from modules.capability_modules.my_module.logic import MyModule


@pytest.mark.asyncio
async def test_my_module(config, message_bus):
    module = MyModule(config, message_bus)
    await module.initialize()
    assert module is not None
```

---

## 🐛 DEBUGGING IMPORT ERRORS

### Error: "ModuleNotFoundError: No module named 'lib'"

**Cause**: Running script from wrong directory

**Fix**:
```python
# At top of script
import sys
from pathlib import Path

LOTUS_ROOT = Path(__file__).parent.parent  # Adjust as needed
sys.path.insert(0, str(LOTUS_ROOT))
```

### Error: "ImportError: cannot import name 'XAIProvider'"

**Cause**: XAIProvider class not added to lib/providers.py

**Fix**: Ensure these are in lib/providers.py:
```python
class XAIProvider(BaseProvider):  # ⭐ Must be present
    pass

class ProviderManager:
    def _initialize_providers(self):
        # ... 
        if self.config.get("providers.xai.enabled", True):
            self.providers["xai"] = XAIProvider(...)  # ⭐ Must initialize
```

### Error: "ImportError: No module named 'mss'"

**Cause**: Dependency not installed

**Fix**:
```bash
pip install -r requirements.txt
# Or individually
pip install mss pillow pytesseract
```

---

## 🚀 PROPER IMPORT WORKFLOW

### Step 1: Start with Core Imports

```python
# Always start with these
from lib.module import BaseModule
from lib.decorators import on_event, tool
from lib.logging import get_logger
```

### Step 2: Add Optional Core Imports

```python
# Add as needed
from lib.message_bus import MessageBus
from lib.memory import MemorySystem
from lib.config import Config
```

### Step 3: Add Third-Party Imports

```python
# After core imports
import asyncio
from typing import Dict, Any
import requests  # For xAI or external APIs
```

### Step 4: Add Try/Except for Optional Dependencies

```python
# For optional packages
try:
    import mss  # Screen capture
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

# In code:
if MSS_AVAILABLE:
    # Use mss
else:
    logger.warning("mss not available")
```

---

## ✅ IMPORT CHECKLIST

Before declaring imports complete:

- [ ] All lib imports use `from lib.*`
- [ ] All module imports use full path: `from modules.*.logic import Class`
- [ ] Scripts have sys.path setup
- [ ] Tests have LOTUS_ROOT setup
- [ ] Third-party imports after core imports
- [ ] Try/except for optional dependencies
- [ ] All imports resolvable: `python -c "from lib.module import BaseModule"`
- [ ] No circular imports
- [ ] No relative parent imports (../)
- [ ] xAI imports working: `from lib.providers import XAIProvider`

---

## 🔍 VERIFY ALL IMPORTS

### Command: Check all imports work

```bash
# Check core library
python -c "from lib.module import BaseModule; print('✅ lib.module')"
python -c "from lib.decorators import on_event, tool; print('✅ lib.decorators')"
python -c "from lib.message_bus import MessageBus; print('✅ lib.message_bus')"
python -c "from lib.memory import MemorySystem; print('✅ lib.memory')"
python -c "from lib.providers import ProviderManager, XAIProvider; print('✅ lib.providers')"
python -c "from lib.config import Config; print('✅ lib.config')"
python -c "from lib.logging import get_logger; print('✅ lib.logging')"

# Check modules import
python -c "from modules.capability_modules.screen_analyzer.logic import ScreenAnalyzer; print('✅ screen_analyzer')"
python -c "from modules.capability_modules.voice_interface.logic import VoiceInterface; print('✅ voice_interface')"
python -c "from modules.capability_modules.task_delegator.logic import TaskDelegator; print('✅ task_delegator')"
python -c "from modules.capability_modules.self_modifier.logic import SelfModifier; print('✅ self_modifier')"

# Check integration modules
python -c "from modules.integration_modules.mcp_protocol.logic import MCPProtocol; print('✅ mcp_protocol')"
python -c "from modules.integration_modules.browser_control.logic import BrowserControl; print('✅ browser_control')"
python -c "from modules.integration_modules.ide_integration.logic import IDEIntegration; print('✅ ide_integration')"

# Check entry points
python -c "import nucleus; print('✅ nucleus')"
python -c "import cli; print('✅ cli')"
```

**If all pass**: ✅ All imports configured correctly!

---

## 📌 QUICK REFERENCE TABLE

| Import | Use Case | Example |
|--------|----------|---------|
| `from lib.module import BaseModule` | All modules | `class MyModule(BaseModule):` |
| `from lib.decorators import on_event` | Event handlers | `@on_event("my.event")` |
| `from lib.decorators import tool` | Callable tools | `@tool("my_tool")` |
| `from lib.logging import get_logger` | Logging | `logger = get_logger("name")` |
| `from lib.providers import XAIProvider` | Use xAI | `XAIProvider(config)` |
| `from lib.config import Config` | Get settings | `self.config.get("key")` |
| `from lib.memory import MemorySystem` | Memory ops | `await self.memory.store()` |
| `from lib.message_bus import MessageBus` | Publish/sub | `await self.publish()` |

---

**All imports properly configured? Run: `python nucleus.py` 🚀**