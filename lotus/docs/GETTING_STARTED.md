# Getting Started with LOTUS/ASH

This guide will help you get LOTUS up and running in minutes.

## 📋 Prerequisites

Before installing LOTUS, ensure you have:

### Required
- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Redis 7.0+** ([Installation Guide](https://redis.io/docs/getting-started/installation/))
- **PostgreSQL 14+** ([Installation Guide](https://www.postgresql.org/download/))
- **8GB RAM** (16GB recommended)

### Optional (but recommended)
- **Ollama** for local LLMs ([Installation](https://ollama.ai/download))
- **Docker** for easy deployment
- **Git** for version control

## 🚀 Quick Start (5 minutes)

### Step 1: Install Redis and PostgreSQL

**macOS (using Homebrew):**
```bash
brew install redis postgresql@14
brew services start redis
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server postgresql postgresql-contrib
sudo systemctl start redis
sudo systemctl start postgresql
```

**Windows:**
- Redis: Use Windows Subsystem for Linux (WSL2) or Docker
- PostgreSQL: Download from [postgresql.org](https://www.postgresql.org/download/windows/)

### Step 2: Clone and Setup LOTUS

```bash
# Clone the repository
cd ~/Projects  # or wherever you want to install
git clone <repository-url> lotus
cd lotus

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your favorite editor
```

**Minimum required configuration:**
```bash
# At minimum, add ONE LLM provider API key:
ANTHROPIC_API_KEY=your_key_here
# OR
OPENAI_API_KEY=your_key_here

# Database (defaults work for local development)
POSTGRES_PASSWORD=lotus
```

### Step 4: Initialize Database

```bash
# Create PostgreSQL database
createdb lotus

# Run migrations (TODO: implement)
# python scripts/migrate.py
```

### Step 5: Start LOTUS!

```bash
# Start the system
python nucleus.py

# Or use the CLI
python cli.py start
```

You should see:
```
🌸 LOTUS starting up...
   Time: 2025-10-13T18:30:00
   Python: 3.11.0
   Config: config/system.yaml

   Initializing infrastructure...
   ✓ Redis connected
   ✓ PostgreSQL connected (TODO)
   ✓ ChromaDB initialized (TODO)
   Found 1 modules
   Load order determined: 1 modules to load

   Loading modules...
   ✓ Loaded: hello_world

🌸 LOTUS is online and ready!
   Modules: 1 active
   Memory: 45.2 MB
```

## 🎯 First Steps

### Verify Everything Works

Open a new terminal and check the logs:
```bash
cd lotus
python cli.py logs

# Or directly:
tail -f data/logs/lotus_*.log
```

### List Installed Modules

```bash
python cli.py list
```

### Test the Example Module

The `hello_world` module should have published a greeting. Check the logs to see it!

## 🛠️ Next Steps

### 1. Add More Modules

Start by enabling the core modules:

**Edit `config/system.yaml`:**
```yaml
modules:
  core:
    - reasoning    # Enable when implemented
    - memory       # Enable when implemented
    - providers    # Enable when implemented
    - perception   # Enable when implemented
```

### 2. Configure Your LLM Providers

**Edit `config/providers.yaml`:**
```yaml
# Set your default provider
default: "claude-sonnet-4"

# Enable/disable providers
anthropic:
  enabled: true
  api_key: "${ANTHROPIC_API_KEY}"

openai:
  enabled: true
  api_key: "${OPENAI_API_KEY}"
```

### 3. Try Local Models (Optional)

If you want to use free local LLMs:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3

# Update config/providers.yaml
ollama:
  enabled: true
  base_url: "http://localhost:11434"
  models:
    - llama3
```

### 4. Create Your First Custom Module

```bash
# Generate module template (TODO: implement)
python cli.py create my_module --type capability

# This creates:
# modules/capability_modules/my_module/
#   ├── manifest.yaml
#   ├── logic.py
#   └── README.md
```

## 📚 Learn More

### Key Concepts

1. **Modules**: Self-contained capabilities (like apps on your phone)
2. **Events**: How modules communicate (pub/sub messaging)
3. **Tools**: Functions modules expose to each other
4. **Memory**: 4-tier system (working, short-term, long-term, persistent)
5. **Providers**: Unified interface for any LLM

### Example: How Events Work

```python
# Module A publishes an event
await self.publish("cognition.task_request", {
    "task": "Write a Python function"
})

# Module B listens for the event
@on_event("cognition.task_request")
async def handle_task(self, event):
    task = event.data["task"]
    # Process the task...
```

### Example: Using Tools

```python
# Call a tool in another module
result = await self.call_tool("code_assistant.analyze_code", 
                              code="def hello(): pass")
```

### Example: Accessing Memory

```python
# Store a memory
await self.memory.remember("User prefers Python over JavaScript")

# Recall memories
memories = await self.memory.recall("What language does user prefer?")
```

## 🐛 Troubleshooting

### Redis Connection Error
```
Error: Redis connection failed
```

**Solution:**
```bash
# Check if Redis is running
redis-cli ping  # Should respond "PONG"

# If not running:
brew services start redis  # macOS
sudo systemctl start redis  # Linux
```

### PostgreSQL Connection Error
```
Error: PostgreSQL connection failed
```

**Solution:**
```bash
# Check if PostgreSQL is running
pg_isready

# Check connection
psql -U lotus -d lotus

# If database doesn't exist:
createdb lotus
```

### Module Load Error
```
Error: No BaseModule subclass found in module_name
```

**Solution:**
- Make sure your module's logic.py has a class that inherits from BaseModule
- Class name should be in PascalCase (e.g., `class MyModule(BaseModule)`)

### Import Errors
```
ModuleNotFoundError: No module named 'lib'
```

**Solution:**
```bash
# Make sure you're in the lotus directory
cd lotus

# And running from there
python nucleus.py
```

## 📖 Documentation

- **[Architecture Overview](docs/ARCHITECTURE.md)** - How LOTUS works
- **[Module Development](docs/MODULE_DEVELOPMENT.md)** - Creating modules
- **[API Reference](docs/API_REFERENCE.md)** - Complete API docs
- **[Configuration Guide](docs/CONFIGURATION.md)** - All config options

## 💬 Getting Help

- **GitHub Issues**: Report bugs and request features
- **Discord**: Join our community (link TBD)
- **Documentation**: Check the `docs/` directory

## 🎉 You're Ready!

LOTUS is now running! Here are some things to try:

1. **Explore the codebase**: Start with `nucleus.py` and `lib/module.py`
2. **Read the example module**: `modules/example_modules/hello_world/`
3. **Check out the logs**: `data/logs/lotus_*.log`
4. **Create your first module**: Follow the module development guide
5. **Join the community**: Share what you're building!

---

**Next**: [Module Development Guide](docs/MODULE_DEVELOPMENT.md) →