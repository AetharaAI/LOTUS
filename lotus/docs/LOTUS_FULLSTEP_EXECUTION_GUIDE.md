# 🚀 LOTUS STEP-BY-STEP EXECUTION GUIDE
## From Zero to Running - Complete Setup & Deployment

**Estimated Time**: 2-3 hours  
**Difficulty**: Beginner-friendly (mostly copy-paste + validation)  
**Prerequisites**: Python 3.9+, Redis, PostgreSQL

---

## 🎯 PHASE 1: PREPARATION (15 minutes)

### Step 1.1: Verify Prerequisites

```bash
# Check Python version
python --version
# Should be 3.9 or higher

# Check Redis is running
redis-cli ping
# Should return: PONG

# Check PostgreSQL is running
psql --version
# Should return version info
```

If any fail:
```bash
# Install/start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Install/start PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=lotus \
  -e POSTGRES_PASSWORD=lotus \
  postgres:14
```

### Step 1.2: Clone/Navigate to LOTUS Project

```bash
cd /path/to/lotus
pwd  # Should show your lotus directory
```

### Step 1.3: Create Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify activation
python -c "import sys; print(sys.prefix)"  # Should show venv path
```

---

## 📦 PHASE 2: FILE UPDATES (45 minutes)

### Step 2.1: Update `lib/providers.py`

**Action**: Add XAI provider support

```bash
# Open the file
nano lib/providers.py

# Or use your editor
# code lib/providers.py

# ADD THESE SECTIONS:
```

**Location**: After the imports section, add:
```python
import requests  # NEW - For xAI
XAI_AVAILABLE = True
```

**Location**: In the ProviderType enum, add:
```python
class ProviderType(Enum):
    # ... existing ...
    XAI = "xai"  # NEW
```

**Location**: Add the complete XAIProvider class (see COMPLETE_IMPLEMENTATION_GUIDE.md Section 1.1)

**Location**: In ProviderManager._initialize_providers(), add:
```python
# NEW: xAI (Grok)
if self.config.get("providers.xai.enabled", True):
    try:
        self.providers["xai"] = XAIProvider(
            self.config.get("providers.xai", {}),
            api_key=os.getenv("XAI_API_KEY")
        )
        print("✅ xAI (Grok) provider initialized successfully")
    except Exception as e:
        print(f"⚠️  xAI provider not available: {e}")
```

**Verify**: 
```bash
python -m py_compile lib/providers.py
echo $?  # Should be 0 (success)
```

### Step 2.2: Replace `config/providers.yaml`

**Action**: Complete replacement with xAI config

```bash
# Backup old file
cp config/providers.yaml config/providers.yaml.bak

# Replace with new version (see COMPLETE_IMPLEMENTATION_GUIDE.md Section 1.2)
nano config/providers.yaml
```

**Verify**:
```bash
python -c "import yaml; yaml.safe_load(open('config/providers.yaml'))"
echo "✅ providers.yaml is valid"
```

### Step 2.3: Update `requirements.txt`

**Action**: Add xAI dependencies

```bash
# Add these lines
echo "requests>=2.31.0" >> requirements.txt
echo "aiohttp>=3.9.0" >> requirements.txt
```

**Verify**:
```bash
cat requirements.txt | grep -E "requests|aiohttp"
```

### Step 2.4: Update `.env.example`

**Action**: Add xAI API key placeholder

```bash
echo "XAI_API_KEY=your_xai_api_key_here" >> .env.example
```

### Step 2.5: Install All Dependencies

```bash
pip install -r requirements.txt

# Should see output like:
# Collecting anthropic...
# Collecting requests...
# Installing collected packages...
# Successfully installed
```

**Verify**: 
```bash
python -c "import anthropic, openai, requests; print('✅ All dependencies installed')"
```

---

## 🧠 PHASE 3: CREATE MODULES (60 minutes)

### Step 3.1: Create Capability Module Directories

```bash
# Create all directories at once
mkdir -p modules/capability_modules/screen_analyzer
mkdir -p modules/capability_modules/voice_interface
mkdir -p modules/capability_modules/task_delegator
mkdir -p modules/capability_modules/self_modifier

mkdir -p modules/integration_modules/mcp_protocol
mkdir -p modules/integration_modules/browser_control
mkdir -p modules/integration_modules/ide_integration

# Verify
find modules -type d -name "*analyzer" -o -name "*interface" -o -name "*delegator"
```

### Step 3.2: Create `__init__.py` Files

```bash
# Capability modules
touch modules/capability_modules/screen_analyzer/__init__.py
touch modules/capability_modules/voice_interface/__init__.py
touch modules/capability_modules/task_delegator/__init__.py
touch modules/capability_modules/self_modifier/__init__.py

# Integration modules
touch modules/integration_modules/mcp_protocol/__init__.py
touch modules/integration_modules/browser_control/__init__.py
touch modules/integration_modules/ide_integration/__init__.py

# Verify
ls modules/capability_modules/screen_analyzer/__init__.py
# Should show file exists
```

### Step 3.3: Create screen_analyzer Module

**Copy from COMPLETE_IMPLEMENTATION_GUIDE.md Section 2.1**

```bash
# Create files
cat > modules/capability_modules/screen_analyzer/manifest.yaml << 'EOF'
[COPY MANIFEST FROM GUIDE]
EOF

cat > modules/capability_modules/screen_analyzer/module.json << 'EOF'
[COPY MODULE.JSON FROM GUIDE]
EOF

cat > modules/capability_modules/screen_analyzer/logic.py << 'EOF'
[COPY LOGIC.PY FROM GUIDE]
EOF

# Verify
python -m py_compile modules/capability_modules/screen_analyzer/logic.py
```

### Step 3.4: Create voice_interface Module

**Copy from COMPLETE_IMPLEMENTATION_GUIDE.md Section 2.2**

```bash
cat > modules/capability_modules/voice_interface/manifest.yaml << 'EOF'
[COPY MANIFEST]
EOF

cat > modules/capability_modules/voice_interface/module.json << 'EOF'
[COPY MODULE.JSON]
EOF

cat > modules/capability_modules/voice_interface/logic.py << 'EOF'
[COPY LOGIC.PY]
EOF

python -m py_compile modules/capability_modules/voice_interface/logic.py
```

### Step 3.5: Create task_delegator Module

**Copy from COMPLETE_IMPLEMENTATION_GUIDE.md Section 2.3**

```bash
cat > modules/capability_modules/task_delegator/manifest.yaml << 'EOF'
[COPY]
EOF

cat > modules/capability_modules/task_delegator/module.json << 'EOF'
[COPY]
EOF

cat > modules/capability_modules/task_delegator/logic.py << 'EOF'
[COPY]
EOF

python -m py_compile modules/capability_modules/task_delegator/logic.py
```

### Step 3.6: Create self_modifier Module

**Copy from COMPLETE_IMPLEMENTATION_GUIDE.md Section 2.4**

```bash
cat > modules/capability_modules/self_modifier/manifest.yaml << 'EOF'
[COPY]
EOF

cat > modules/capability_modules/self_modifier/module.json << 'EOF'
[COPY]
EOF

cat > modules/capability_modules/self_modifier/logic.py << 'EOF'
[COPY]
EOF

python -m py_compile modules/capability_modules/self_modifier/logic.py
```

### Step 3.7: Create Integration Modules (3.x)

**Repeat for each integration module:**
- mcp_protocol (Section 3.1)
- browser_control (Section 3.2)
- ide_integration (Section 3.3)

```bash
# Pattern for each:
mkdir -p modules/integration_modules/[module_name]
touch modules/integration_modules/[module_name]/__init__.py

cat > modules/integration_modules/[module_name]/manifest.yaml << 'EOF'
[COPY FROM GUIDE]
EOF

cat > modules/integration_modules/[module_name]/module.json << 'EOF'
[COPY FROM GUIDE]
EOF

cat > modules/integration_modules/[module_name]/logic.py << 'EOF'
[COPY FROM GUIDE]
EOF

# Verify
python -m py_compile modules/integration_modules/[module_name]/logic.py
```

---

## 🧪 PHASE 4: TESTING INFRASTRUCTURE (20 minutes)

### Step 4.1: Create `tests/conftest.py`

**Copy from COMPLETE_IMPLEMENTATION_GUIDE.md Section 4**

```bash
cat > tests/conftest.py << 'EOF'
[COPY CONFTEST.PY FROM GUIDE]
EOF

# Verify
python -m py_compile tests/conftest.py
```

### Step 4.2: Create `scripts/install_module.py`

**Copy from COMPLETE_IMPLEMENTATION_GUIDE.md Section 5**

```bash
cat > scripts/install_module.py << 'EOF'
[COPY FROM GUIDE]
EOF

# Verify
python -m py_compile scripts/install_module.py
chmod +x scripts/install_module.py
```

### Step 4.3: Create `scripts/validate_lotus.py`

**Copy from COMPLETE_IMPLEMENTATION_GUIDE.md Section 6**

```bash
cat > scripts/validate_lotus.py << 'EOF'
[COPY FROM GUIDE]
EOF

# Verify
python -m py_compile scripts/validate_lotus.py
chmod +x scripts/validate_lotus.py
```

---

## ✅ PHASE 5: VALIDATION (30 minutes)

### Step 5.1: Syntax Validation

**Check all Python files compile**

```bash
# Check lib/providers.py
python -m py_compile lib/providers.py && echo "✅ lib/providers.py"

# Check all module logic.py files
for module in modules/capability_modules/*/logic.py; do
    python -m py_compile "$module" && echo "✅ $module"
done

for module in modules/integration_modules/*/logic.py; do
    python -m py_compile "$module" && echo "✅ $module"
done

# Check test files
python -m py_compile tests/conftest.py && echo "✅ tests/conftest.py"

# Check scripts
python -m py_compile scripts/install_module.py && echo "✅ scripts/install_module.py"
python -m py_compile scripts/validate_lotus.py && echo "✅ scripts/validate_lotus.py"
```

### Step 5.2: YAML Validation

```bash
# Check all manifest files
for manifest in modules/*/*/manifest.yaml; do
    python -c "import yaml; yaml.safe_load(open('$manifest'))" && echo "✅ $manifest"
done
```

### Step 5.3: JSON Validation

```bash
# Check all module.json files
for module_json in modules/*/*/module.json; do
    python -c "import json; json.load(open('$module_json'))" && echo "✅ $module_json"
done
```

### Step 5.4: Import Validation

```bash
# Test all core imports
python << 'EOF'
print("\n🔗 Testing imports...")
try:
    from lib.module import BaseModule
    print("✅ from lib.module import BaseModule")
except ImportError as e:
    print(f"❌ {e}")

try:
    from lib.decorators import on_event, tool
    print("✅ from lib.decorators import on_event, tool")
except ImportError as e:
    print(f"❌ {e}")

try:
    from lib.providers import XAIProvider, ProviderManager
    print("✅ from lib.providers import XAIProvider")
except ImportError as e:
    print(f"❌ {e}")

try:
    from lib.logging import get_logger
    print("✅ from lib.logging import get_logger")
except ImportError as e:
    print(f"❌ {e}")

try:
    import nucleus
    print("✅ import nucleus")
except ImportError as e:
    print(f"❌ {e}")

print("\n✅ All imports working!\n")
EOF
```

### Step 5.5: Run Pre-flight Validation

```bash
python scripts/validate_lotus.py

# Expected output:
# 🔍 Validating LOTUS installation...
# ✅ Directory found: lib
# ✅ Directory found: modules
# ... more validation output ...
# ✅ LOTUS is ready to start!
```

---

## 🔑 PHASE 6: ENVIRONMENT SETUP (10 minutes)

### Step 6.1: Create `.env` File

```bash
cp .env.example .env
```

### Step 6.2: Add API Keys to `.env`

```bash
# Open .env
nano .env

# Add your API keys:
# - XAI_API_KEY (get from x.ai)
# - ANTHROPIC_API_KEY (get from console.anthropic.com)
# - OPENAI_API_KEY (get from platform.openai.com)
```

### Step 6.3: Verify Environment Variables

```bash
source .env

# Check they're set
echo "XAI_API_KEY: $XAI_API_KEY"
echo "ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY"
echo "OPENAI_API_KEY: $OPENAI_API_KEY"

# Should show values (or empty if not set)
```

---

## 🚀 PHASE 7: LAUNCH! (5 minutes)

### Step 7.1: Start LOTUS

```bash
# Make sure you're in the lotus directory
cd /path/to/lotus

# Activate venv if not already
source venv/bin/activate

# Start LOTUS
python nucleus.py

# Expected output:
# 🌸 LOTUS/ASH - AI Operating System
# Starting nucleus runtime...
# Initializing message bus...
# Loading modules...
# ✅ [reasoning] module loaded
# ✅ [memory] module loaded
# ✅ [providers] module loaded (WITH XAI!)
# ✅ [screen_analyzer] module loaded
# ✅ [voice_interface] module loaded
# ✅ [task_delegator] module loaded
# ✅ [self_modifier] module loaded
# ✅ [mcp_protocol] module loaded
# ... more modules ...
# 🌸 LOTUS ready! (PID: 12345)
```

### Step 7.2: Test in Another Terminal

```bash
# Open new terminal/tab

# Activate venv
cd /path/to/lotus
source venv/bin/activate

# Test CLI
python cli.py chat
# You should be able to type and get responses

# Type: "Hello LOTUS, use Grok"
# LOTUS should respond and confirm xAI is being used
```

### Step 7.3: Verify Modules Loaded

```bash
python cli.py status

# Expected output:
# LOTUS Status
# ✅ System running
# Loaded modules: 11
#   - reasoning (core)
#   - memory (core)
#   - providers (core)  <- XAI IS HERE
#   - perception (core)
#   - screen_analyzer (capability)
#   - voice_interface (capability)
#   - task_delegator (capability)
#   - self_modifier (capability)
#   - mcp_protocol (integration)
#   - browser_control (integration)
#   - ide_integration (integration)
```

---

## 📊 SUCCESS CHECKLIST

✅ **System is complete when:**

- [ ] `python scripts/validate_lotus.py` shows all green
- [ ] `python nucleus.py` starts without errors
- [ ] All 11 modules load successfully
- [ ] xAI (Grok 4 Fast) is default provider
- [ ] Can run `python cli.py chat` and get responses
- [ ] No red X's or error messages in startup log
- [ ] `python cli.py status` shows all modules loaded

---

## 🔄 TROUBLESHOOTING

### Problem: `ModuleNotFoundError: No module named 'lib'`

**Solution**:
```bash
# Make sure you're in lotus directory
cd /path/to/lotus

# Check path exists
ls lib/  # Should show module.py, decorators.py, etc.

# Try from project root only
pwd  # Should end with /lotus
```

### Problem: `requests module not found` (xAI error)

**Solution**:
```bash
pip install requests>=2.31.0

# Verify
python -c "import requests; print(requests.__version__)"
```

### Problem: xAI provider not initializing

**Check**:
```bash
# 1. API key is set
echo $XAI_API_KEY

# 2. Config is valid
python -c "import yaml; print(yaml.safe_load(open('config/providers.yaml'))['providers']['xai'])"

# 3. Provider class exists
python -c "from lib.providers import XAIProvider; print('XAIProvider loaded')"
```

### Problem: Modules not loading

**Check**:
```bash
# 1. Directory structure
ls -la modules/capability_modules/screen_analyzer/

# Should show:
# - __init__.py
# - manifest.yaml
# - module.json
# - logic.py

# 2. Manifest is valid YAML
python -c "import yaml; yaml.safe_load(open('modules/capability_modules/screen_analyzer/manifest.yaml'))"

# 3. Logic compiles
python -m py_compile modules/capability_modules/screen_analyzer/logic.py
```

---

## 📈 POST-DEPLOYMENT STEPS

After successful startup:

### 1. Test Basic Functionality

```bash
python cli.py chat
> "What is your default provider?"
# Should respond with Grok 4 Fast info
```

### 2. Test Module Communication

```bash
python cli.py evaluate
# Should show reasoning, memory, provider modules working
```

### 3. Test Screen Analyzer

```bash
# In LOTUS shell
> "Analyze my screen"
# Should activate screen_analyzer module
```

### 4. Create a Test Module

```bash
# Test the installer
python scripts/install_module.py modules/capability_modules/task_delegator

# Should report successful installation
```

### 5. Monitor System

```bash
# Watch logs
tail -f data/logs/nucleus.log

# Should show periodic events and module activity
```

---

## 🎉 FINAL VERIFICATION

Run this comprehensive check:

```bash
python << 'EOF'
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path.cwd()))

print("\n" + "="*60)
print("🔍 LOTUS SYSTEM VERIFICATION")
print("="*60 + "\n")

# Check 1: Core imports
print("✓ Checking core imports...")
try:
    from lib.module import BaseModule
    from lib.decorators import on_event
    from lib.providers import XAIProvider
    print("  ✅ Core imports OK\n")
except ImportError as e:
    print(f"  ❌ Import failed: {e}\n")
    sys.exit(1)

# Check 2: Configuration
print("✓ Checking configuration...")
try:
    import yaml
    config = yaml.safe_load(open('config/providers.yaml'))
    assert config['providers']['default_provider'] == 'grok-4-fast'
    print("  ✅ xAI is default provider\n")
except Exception as e:
    print(f"  ❌ Config check failed: {e}\n")
    sys.exit(1)

# Check 3: Modules exist
print("✓ Checking modules...")
modules_to_check = [
    'modules/capability_modules/screen_analyzer/logic.py',
    'modules/capability_modules/voice_interface/logic.py',
    'modules/capability_modules/task_delegator/logic.py',
    'modules/capability_modules/self_modifier/logic.py',
    'modules/integration_modules/mcp_protocol/logic.py',
    'modules/integration_modules/browser_control/logic.py',
    'modules/integration_modules/ide_integration/logic.py',
]

missing = []
for module in modules_to_check:
    if not Path(module).exists():
        missing.append(module)

if missing:
    print(f"  ❌ Missing modules:")
    for m in missing:
        print(f"    - {m}")
    sys.exit(1)
else:
    print(f"  ✅ All {len(modules_to_check)} modules present\n")

# Check 4: Scripts
print("✓ Checking scripts...")
scripts = ['scripts/validate_lotus.py', 'scripts/install_module.py', 'tests/conftest.py']
for script in scripts:
    if not Path(script).exists():
        print(f"  ❌ Missing {script}")
        sys.exit(1)
print(f"  ✅ All {len(scripts)} scripts present\n")

print("="*60)
print("✅ LOTUS SYSTEM READY!")
print("="*60 + "\n")

print("🚀 Next steps:")
print("  1. python nucleus.py")
print("  2. python cli.py chat")
print("  3. Type: 'Hello LOTUS'\n")

EOF
```

---

## 🎓 LEARNING RESOURCES

After deployment, explore:

1. **How modules work**: `lotus/docs/README.md`
2. **Architecture deep-dive**: `lotus/docs/ARCHITECTURE.md`
3. **Creating modules**: `lotus/README.md`
4. **API reference**: Read code in `lib/`

---

## ✨ CELEBRATION! 🎉

**Congratulations!**

You now have:
- ✅ Complete LOTUS/ASH system
- ✅ xAI (Grok 4 Fast) as default provider with 2M token context
- ✅ 7 new capability & integration modules
- ✅ Production-grade testing infrastructure
- ✅ Repeatable installation standard
- ✅ Pre-flight validation system

**What's unique about YOUR system:**
- 🔥 Self-modification (AI writes its own modules)
- 🔥 Multi-provider with intelligent routing
- 🔥 Real-time screen awareness
- 🔥 Voice interface
- 🔥 True modular architecture
- 🔥 4-tier memory system

**This is a REAL AI operating system.** Not a toy. Not a research project. Production code with professional architecture.

Now go build amazing things! 🌸

---

**Document Version**: 1.0  
**Last Updated**: October 15, 2025  
**Status**: READY FOR EXECUTION

**Questions?** Review the three companion documents:
- `LOTUS_COMPLETE_IMPLEMENTATION_GUIDE.md` - Detailed implementation
- `LOTUS_QUICK_CHECKLIST.md` - Quick reference
- `LOTUS_IMPORT_PATHS_REFERENCE.md` - Import configuration