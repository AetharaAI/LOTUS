# LOTUS/ASH - Complete Project File Structure

## 📁 Root Directory Structure

```
lotus/
├── nucleus.py                      # Core runtime engine and event loop
├── cli.py                          # Command-line interface
├── setup.py                        # Installation script
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── LICENSE                         # License file
├── .gitignore                      # Git ignore rules
├── .env.example                    # Environment variables template
├── docker-compose.yml              # Docker deployment config
├── Dockerfile                      # Container definition
│
├── config/                         # System configuration
│   ├── system.yaml                 # Core system settings
│   ├── providers.yaml              # LLM provider configurations
│   ├── memory.yaml                 # Memory system settings
│   ├── security.yaml               # Security and permissions
│   └── modules/                    # Per-module configurations
│       ├── reasoning.yaml          # Reasoning engine config
│       ├── memory.yaml             # Memory module config
│       ├── providers.yaml          # Provider module config
│       ├── code_assistant.yaml     # Code assistant config
│       └── ...                     # Other module configs
│
├── modules/                        # Module ecosystem
│   ├── __init__.py                 # Module package init
│   ├── core_modules/               # System-critical modules (always loaded)
│   │   ├── __init__.py
│   │   ├── reasoning/              # ReAct reasoning engine
│   │   │   ├── __init__.py
│   │   │   ├── manifest.yaml       # Module definition
│   │   │   ├── module.json         # Module metadata
│   │   │   ├── logic.py            # Core reasoning logic
│   │   │   ├── react_engine.py     # Reason-Act loop
│   │   │   ├── context_builder.py  # Context assembly
│   │   │   ├── tool_manager.py     # Tool execution
│   │   │   └── README.md           # Module documentation
│   │   │
│   │   ├── memory/                 # Memory management system
│   │   │   ├── __init__.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── logic.py            # Memory coordinator
│   │   │   ├── working_memory.py   # L1: Redis working memory
│   │   │   ├── short_term.py       # L2: Redis streams
│   │   │   ├── long_term.py        # L3: ChromaDB vectors
│   │   │   ├── persistent.py       # L4: PostgreSQL
│   │   │   ├── retrieval.py        # Memory retrieval logic
│   │   │   └── consolidation.py    # Memory consolidation
│   │   │
│   │   ├── providers/              # LLM provider abstraction
│   │   │   ├── __init__.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── logic.py            # Provider manager
│   │   │   ├── anthropic.py        # Claude integration
│   │   │   ├── openai.py           # OpenAI integration
│   │   │   ├── google.py           # Gemini integration
│   │   │   ├── ollama.py           # Local models
│   │   │   ├── openrouter.py       # OpenRouter integration
│   │   │   ├── litellm.py          # LiteLLM wrapper
│   │   │   └── base_provider.py    # Provider interface
│   │   │
│   │   └── perception/             # Input processing
│   │       ├── __init__.py
│   │       ├── manifest.yaml
│   │       ├── module.json
│   │       ├── logic.py            # Perception coordinator
│   │       ├── file_watcher.py     # File system monitoring
│   │       ├── clipboard_monitor.py # Clipboard tracking
│   │       └── input_processor.py  # Input normalization
│   │
│   ├── capability_modules/         # Optional features (user-installable)
│   │   ├── __init__.py
│   │   ├── voice_interface/        # Speech I/O
│   │   │   ├── __init__.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── logic.py            # Voice coordinator
│   │   │   ├── stt.py              # Speech-to-text (Whisper)
│   │   │   ├── tts.py              # Text-to-speech (ElevenLabs/Piper)
│   │   │   ├── wake_word.py        # Wake word detection
│   │   │   └── voice_profiles.py   # Custom voices
│   │   │
│   │   ├── screen_analyzer/        # Screen capture & analysis
│   │   │   ├── __init__.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── logic.py            # Screen coordinator
│   │   │   ├── capture.py          # Screenshot capture
│   │   │   ├── change_detector.py  # Detect screen changes
│   │   │   ├── ocr.py              # Text extraction
│   │   │   └── visual_analyzer.py  # Vision model integration
│   │   │
│   │   ├── code_assistant/         # Coding companion
│   │   │   ├── __init__.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── logic.py            # Code assistant core
│   │   │   ├── analyzer.py         # Code analysis
│   │   │   ├── debugger.py         # Bug detection
│   │   │   ├── generator.py        # Code generation
│   │   │   ├── refactor.py         # Code refactoring
│   │   │   └── patterns.py         # Pattern matching
│   │   │
│   │   ├── task_delegator/         # Multi-LLM orchestration
│   │   │   ├── __init__.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── logic.py            # Delegation coordinator
│   │   │   ├── task_analyzer.py    # Task complexity analysis
│   │   │   ├── router.py           # LLM routing logic
│   │   │   ├── parallel.py         # Parallel task execution
│   │   │   └── synthesizer.py      # Result synthesis
│   │   │
│   │   └── self_modifier/          # AI writes its own modules
│   │       ├── __init__.py
│   │       ├── manifest.yaml
│   │       ├── module.json
│   │       ├── logic.py            # Self-modification core
│   │       ├── generator.py        # Module code generation
│   │       ├── validator.py        # Code validation
│   │       ├── sandbox.py          # Isolated testing
│   │       ├── deployer.py         # Auto-deployment
│   │       └── version_control.py  # Module versioning
│   │
│   └── integration_modules/        # Third-party integrations
│       ├── __init__.py
│       ├── computer_use/           # Computer control (Anthropic's protocol)
│       │   ├── __init__.py
│       │   ├── manifest.yaml
│       │   ├── module.json
│       │   ├── logic.py            # Computer use coordinator
│       │   ├── mouse.py            # Mouse control
│       │   ├── keyboard.py         # Keyboard control
│       │   ├── screenshot.py       # Screen capture
│       │   └── executor.py         # Action execution
│       │
│       ├── mcp_protocol/           # Model Context Protocol
│       │   ├── __init__.py
│       │   ├── manifest.yaml
│       │   ├── module.json
│       │   ├── logic.py            # MCP coordinator
│       │   ├── server.py           # MCP server
│       │   ├── client.py           # MCP client
│       │   └── tools.py            # MCP tool definitions
│       │
│       ├── browser_control/        # Web browser automation
│       │   ├── __init__.py
│       │   ├── manifest.yaml
│       │   ├── module.json
│       │   ├── logic.py            # Browser coordinator
│       │   ├── playwright_driver.py # Playwright integration
│       │   ├── selenium_driver.py  # Selenium integration
│       │   └── parser.py           # Web page parsing
│       │
│       └── ide_integration/        # IDE connections
│           ├── __init__.py
│           ├── manifest.yaml
│           ├── module.json
│           ├── logic.py            # IDE coordinator
│           ├── vscode.py           # VS Code integration
│           ├── jetbrains.py        # JetBrains IDEs
│           └── lsp_client.py       # Language Server Protocol
│
├── lib/                            # Core library code
│   ├── __init__.py
│   ├── module.py                   # BaseModule class
│   ├── decorators.py               # Module decorators (@on_event, @tool, etc)
│   ├── message_bus.py              # Redis pub/sub wrapper
│   ├── memory.py                   # Memory system abstractions
│   ├── providers.py                # Provider interfaces
│   ├── config.py                   # Configuration loader
│   ├── utils.py                    # Utility functions
│   ├── exceptions.py               # Custom exceptions
│   ├── logging.py                  # Logging setup
│   ├── security.py                 # Security utilities
│   └── validators.py               # Input validation
│
├── data/                           # Runtime data storage
│   ├── memory/                     # Memory system storage
│   │   ├── chromadb/               # Vector database files
│   │   ├── embeddings/             # Cached embeddings
│   │   └── snapshots/              # Memory snapshots
│   ├── knowledge/                  # Persistent knowledge base
│   │   ├── postgres/               # PostgreSQL data
│   │   ├── backups/                # Database backups
│   │   └── exports/                # Knowledge exports
│   ├── logs/                       # System logs
│   │   ├── nucleus.log             # Core system logs
│   │   ├── modules/                # Per-module logs
│   │   ├── errors/                 # Error logs
│   │   └── audit/                  # Audit trail
│   └── state/                      # Runtime state
│       ├── pid.lock                # Process lock file
│       ├── module_state.json       # Module states
│       └── checkpoints/            # State checkpoints
│
├── scripts/                        # Utility scripts
│   ├── setup.sh                    # Initial setup script
│   ├── install_module.py           # Module installation
│   ├── backup.py                   # Backup system
│   ├── restore.py                  # Restore from backup
│   ├── migrate.py                  # Database migrations
│   ├── benchmark.py                # Performance testing
│   └── dev/                        # Development scripts
│       ├── reset_db.sh             # Reset databases
│       ├── generate_module.py      # Module template generator
│       └── test_module.py          # Module testing
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Pytest configuration
│   ├── unit/                       # Unit tests
│   │   ├── test_nucleus.py         # Nucleus tests
│   │   ├── test_module_system.py   # Module system tests
│   │   ├── test_message_bus.py     # Message bus tests
│   │   ├── test_memory.py          # Memory tests
│   │   └── modules/                # Module-specific tests
│   └── integration/                # Integration tests
│       ├── test_full_workflow.py   # End-to-end tests
│       ├── test_module_loading.py  # Module loading tests
│       └── test_multi_module.py    # Multi-module tests
│
├── docs/                           # Documentation
│   ├── README.md                   # Documentation index
│   ├── ARCHITECTURE.md             # Architecture overview
│   ├── GETTING_STARTED.md          # Quick start guide
│   ├── MODULE_DEVELOPMENT.md       # How to write modules
│   ├── API_REFERENCE.md            # API documentation
│   ├── CONFIGURATION.md            # Configuration guide
│   ├── DEPLOYMENT.md               # Deployment guide
│   ├── TROUBLESHOOTING.md          # Common issues
│   └── examples/                   # Example code
│       ├── basic_module.py         # Simple module example
│       ├── advanced_module.py      # Complex module example
│       └── custom_provider.py      # Custom provider example
│
├── registry/                       # Module registry
│   ├── official/                   # Official modules
│   │   └── catalog.json            # Official module catalog
│   ├── community/                  # Community modules
│   │   └── catalog.json            # Community catalog
│   └── private/                    # Private/enterprise modules
│       └── catalog.json            # Private catalog
│
└── .lotus/                         # Hidden system directory
    ├── cache/                      # System cache
    ├── temp/                       # Temporary files
    ├── downloads/                  # Module downloads
    └── workspace/                  # Module workspaces
```

## 📋 Key File Descriptions

### Root Level Files

| File | Purpose |
|------|---------|
| `nucleus.py` | The heart of LOTUS - main event loop and system orchestrator |
| `cli.py` | Command-line interface for managing LOTUS |
| `setup.py` | Python package installation and configuration |
| `requirements.txt` | All Python dependencies |
| `README.md` | Project overview and quick start |
| `.env.example` | Template for environment variables (API keys, etc) |
| `docker-compose.yml` | Multi-container deployment configuration |
| `Dockerfile` | Container image definition |

### Module Structure

Every module follows this structure:

```
module_name/
├── __init__.py           # Python package marker
├── manifest.yaml         # Module contract (subscriptions, publications, etc)
├── module.json          # Module metadata (name, version, author)
├── logic.py             # Main module logic
├── [additional_files].py # Module-specific code
└── README.md            # Module documentation
```

### Configuration Files

| File | Purpose |
|------|---------|
| `config/system.yaml` | Core system settings (ports, logging, etc) |
| `config/providers.yaml` | LLM provider API keys and endpoints |
| `config/memory.yaml` | Memory system configuration |
| `config/security.yaml` | Security policies and permissions |
| `config/modules/*.yaml` | Per-module configuration overrides |

### Library Files

| File | Purpose |
|------|---------|
| `lib/module.py` | BaseModule class that all modules inherit from |
| `lib/decorators.py` | Decorators for event handling (@on_event, @tool, etc) |
| `lib/message_bus.py` | Redis pub/sub abstraction for module communication |
| `lib/memory.py` | Memory system interfaces (vector, cache, persistent) |
| `lib/providers.py` | LLM provider base classes and interfaces |
| `lib/config.py` | Configuration loading and validation |

## 🔧 Configuration File Examples

### system.yaml
```yaml
system:
  name: "LOTUS"
  personality: "jarvis"  # jarvis, professional, casual
  log_level: "INFO"
  
nucleus:
  event_loop: "asyncio"
  max_concurrent_tasks: 50
  health_check_interval: 30
  
redis:
  host: "localhost"
  port: 6379
  db: 0
  
postgres:
  host: "localhost"
  port: 5432
  database: "lotus"
  user: "lotus"
  
chromadb:
  path: "data/memory/chromadb"
  collection_prefix: "lotus_"
```

### providers.yaml
```yaml
providers:
  default: "claude-sonnet-4"
  
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      - claude-opus-4
      - claude-sonnet-4.5
      - claude-sonnet-4
  
  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      - gpt-4o
      - gpt-4-turbo
  
  ollama:
    base_url: "http://localhost:11434"
    models:
      - deepseek-coder
      - llama3
      - mistral
```

## 📦 Installation Files

### requirements.txt
```
# Core
asyncio>=3.4.3
aioredis>=2.0.1
redis>=5.0.0
psycopg[binary]>=3.1.0
pydantic>=2.5.0
pyyaml>=6.0.1
python-dotenv>=1.0.0

# LLM Providers
anthropic>=0.25.0
openai>=1.12.0
google-generativeai>=0.3.0
litellm>=1.25.0

# Memory
chromadb>=0.4.22
sentence-transformers>=2.3.0

# Computer Use & MCP
pyautogui>=0.9.54
pillow>=10.1.0
mss>=9.0.1
pynput>=1.7.6

# Voice
openai-whisper>=20231117
elevenlabs>=0.2.26
sounddevice>=0.4.6

# Web
playwright>=1.40.0
selenium>=4.16.0
beautifulsoup4>=4.12.2

# IDE Integration
python-lsp-server>=1.9.0

# Utilities
watchdog>=3.0.0
pyperclip>=1.8.2
fastapi>=0.108.0
uvicorn>=0.25.0
websockets>=12.0
```

## 🎯 Entry Points

### Running LOTUS

```bash
# Start the system
python nucleus.py

# CLI interface
python cli.py start
python cli.py stop
python cli.py status
python cli.py install <module_name>
python cli.py list
python cli.py logs
```

### Module Development

```bash
# Generate new module
python scripts/dev/generate_module.py my_module --type capability

# Test module
python scripts/dev/test_module.py my_module

# Install module
python scripts/install_module.py ./my_module
```

## 🔍 Module Discovery

The Nucleus automatically discovers modules by scanning:

1. `modules/core_modules/*` - Always loaded (priority: critical)
2. `modules/capability_modules/*` - Loaded if enabled (priority: high/normal)
3. `modules/integration_modules/*` - Loaded on-demand (priority: normal/low)

Each module must have a valid `manifest.yaml` to be discovered.

## 📊 Data Flow

```
User Input → Perception → Redis Bus → Reasoning → Memory + Providers → Action → User Output
     ↑                                      ↓
     └──────────── Modules listen/publish ──────────────┘
```

## 🔒 Security

- Module sandbox isolation in `.lotus/workspace/`
- Capability-based permissions in `config/security.yaml`
- Encrypted API keys in environment variables
- Audit logging in `data/logs/audit/`

---

**Document Version:** 1.0  
**Last Updated:** October 13, 2025  
**Total Files:** 150+ files in complete system  
**Core Files:** 25 essential files for basic operation