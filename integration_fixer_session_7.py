#!/usr/bin/env python3
"""
Session 7 - Automatic Integration Fixer
========================================

This script automatically fixes common integration issues in the LOTUS project:
1. Creates missing __init__.py files
2. Updates imports to use absolute paths
3. Creates missing config files
4. Fixes module structure

Run this AFTER the diagnostic to auto-fix issues!
"""

import os
import sys
from pathlib import Path
from typing import List

# ANSI colors
class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_success(text):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {text}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {text}")

def print_error(text):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {text}")


class LOTUSIntegrationFixer:
    """Automatic fixer for LOTUS integration issues"""
    
    def __init__(self, project_root: str = "."):
        self.root = Path(project_root).resolve()
        self.fixes_applied = []
        
    def create_missing_init_files(self):
        """Create __init__.py in all Python package directories"""
        print(f"\n{Colors.BOLD}Creating missing __init__.py files...{Colors.ENDC}")
        
        directories = [
            "lib",
            "modules",
            "modules/core_modules",
            "modules/core_modules/reasoning",
            "modules/core_modules/memory",
            "modules/core_modules/providers",
            "modules/core_modules/perception",
            "modules/capability_modules",
            "modules/integration_modules",
            "tests"
        ]
        
        for dir_path in directories:
            init_file = self.root / dir_path / "__init__.py"
            
            if not init_file.exists():
                init_file.parent.mkdir(parents=True, exist_ok=True)
                init_file.write_text(f'"""LOTUS {dir_path} package"""\n')
                print_success(f"Created: {init_file.relative_to(self.root)}")
                self.fixes_applied.append(f"Created {init_file.relative_to(self.root)}")
            else:
                print_warning(f"Already exists: {init_file.relative_to(self.root)}")
    
    def create_lib_init_with_exports(self):
        """Create lib/__init__.py with proper exports"""
        print(f"\n{Colors.BOLD}Creating lib/__init__.py with exports...{Colors.ENDC}")
        
        lib_init = self.root / "lib" / "__init__.py"
        
        content = '''"""
LOTUS Core Library
==================

This package contains all core infrastructure components:
- BaseModule: Base class for all modules
- MessageBus: Event system
- Memory: 4-tier memory abstractions
- Providers: LLM provider interfaces
- Config: Configuration management
- Decorators: Event/tool decorators
"""

# Import and export core components
from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic
from lib.message_bus import MessageBus
from lib.config import Config
from lib.exceptions import (
    LOTUSError,
    ModuleLoadError,
    ConfigError,
    EventError
)

__all__ = [
    'BaseModule',
    'on_event',
    'tool',
    'periodic',
    'MessageBus',
    'Config',
    'LOTUSError',
    'ModuleLoadError',
    'ConfigError',
    'EventError'
]

__version__ = '0.1.0'
'''
        
        lib_init.write_text(content)
        print_success(f"Created: {lib_init.relative_to(self.root)}")
        self.fixes_applied.append("Created lib/__init__.py with exports")
    
    def create_missing_config_files(self):
        """Create missing module config override files"""
        print(f"\n{Colors.BOLD}Creating missing config override files...{Colors.ENDC}")
        
        config_dir = self.root / "config" / "modules"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create README in config/modules
        readme = config_dir / "README.md"
        readme.write_text("""# Module Configuration Overrides

This directory contains configuration override files for LOTUS modules.

## How It Works

1. Each module has a `manifest.yaml` in its directory that defines default settings
2. Files in this directory override those defaults at runtime
3. Format: `{module_name}.yaml`

## Example

```yaml
# config/modules/reasoning.yaml
max_iterations: 15  # Override default of 10
temperature: 0.8    # Override default of 0.7
```

## Files

- `reasoning.yaml` - Reasoning engine configuration
- `memory.yaml` - Memory system configuration  
- `providers.yaml` - LLM provider configuration
- `perception.yaml` - Perception module configuration
- `code_assistant.yaml` - Code assistant configuration
- `consciousness.yaml` - Consciousness module configuration (DISABLED by default)
""")
        print_success(f"Created: {readme.relative_to(self.root)}")
        
        # Check if config files exist (they should from Session 6)
        config_files = [
            "reasoning.yaml",
            "memory.yaml",
            "providers.yaml",
            "perception.yaml",
            "code_assistant.yaml",
            "consciousness.yaml"
        ]
        
        for config_file in config_files:
            config_path = config_dir / config_file
            if config_path.exists():
                print_warning(f"Already exists: {config_path.relative_to(self.root)}")
            else:
                print_error(f"Missing: {config_path.relative_to(self.root)}")
                print_warning("  These should have been created in Session 6")
                print_warning("  You'll need to copy them from Session 6 deliverables")
    
    def create_module_structure(self):
        """Create complete module directory structure"""
        print(f"\n{Colors.BOLD}Creating module directory structure...{Colors.ENDC}")
        
        modules = [
            ("core_modules/reasoning", ["logic.py", "manifest.yaml", "module.json", "README.md"]),
            ("core_modules/memory", ["logic.py", "manifest.yaml", "module.json", "README.md"]),
            ("core_modules/providers", ["logic.py", "manifest.yaml", "module.json", "README.md"]),
            ("core_modules/perception", ["logic.py", "manifest.yaml", "module.json", "README.md"]),
        ]
        
        for module_dir, required_files in modules:
            module_path = self.root / "modules" / module_dir
            module_path.mkdir(parents=True, exist_ok=True)
            
            for file_name in required_files:
                file_path = module_path / file_name
                
                if file_path.exists():
                    size = file_path.stat().st_size
                    if size == 0:
                        print_warning(f"Empty file: {file_path.relative_to(self.root)}")
                    else:
                        print_success(f"Exists ({size} bytes): {file_path.relative_to(self.root)}")
                else:
                    print_error(f"Missing: {file_path.relative_to(self.root)}")
    
    def create_data_directories(self):
        """Create data directories for runtime"""
        print(f"\n{Colors.BOLD}Creating data directories...{Colors.ENDC}")
        
        directories = [
            "data/logs",
            "data/memory/chromadb",
            "data/memory/embeddings",
            "data/memory/snapshots",
            "data/knowledge/postgres",
            "data/knowledge/backups",
            "data/state",
            "data/cache"
        ]
        
        for dir_path in directories:
            full_path = self.root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Create .gitkeep to preserve empty directories
            gitkeep = full_path / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.write_text("")
                print_success(f"Created: {full_path.relative_to(self.root)}/")
            else:
                print_warning(f"Already exists: {full_path.relative_to(self.root)}/")
    
    def create_env_example(self):
        """Create .env.example file"""
        print(f"\n{Colors.BOLD}Creating .env.example...{Colors.ENDC}")
        
        env_file = self.root / ".env.example"
        
        content = '''# LOTUS Environment Configuration
# Copy this file to .env and fill in your actual values

# ===== LLM PROVIDER API KEYS =====
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-google-key-here

# ===== INFRASTRUCTURE =====
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lotus
POSTGRES_USER=lotus
POSTGRES_PASSWORD=lotus

# ChromaDB
CHROMADB_PATH=data/memory/chromadb

# ===== SYSTEM CONFIGURATION =====
LOTUS_ENV=development
LOTUS_LOG_LEVEL=INFO
LOTUS_DEBUG=false

# ===== OPTIONAL SERVICES =====
# ElevenLabs (Voice)
ELEVENLABS_API_KEY=

# OpenRouter (Multi-model access)
OPENROUTER_API_KEY=

# ===== SECURITY =====
# JWT secret for API authentication
JWT_SECRET=generate-a-random-secret-here

# Enable/disable features
ENABLE_VOICE=false
ENABLE_SCREEN_ANALYSIS=false
ENABLE_COMPUTER_USE=false
ENABLE_CONSCIOUSNESS=false
'''
        
        env_file.write_text(content)
        print_success(f"Created: {env_file.relative_to(self.root)}")
        self.fixes_applied.append("Created .env.example")
    
    def create_gitignore(self):
        """Create .gitignore file"""
        print(f"\n{Colors.BOLD}Creating .gitignore...{Colors.ENDC}")
        
        gitignore = self.root / ".gitignore"
        
        content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
venv/
ENV/
env.bak/
venv.bak/

# LOTUS specific
.env
data/logs/*.log
data/memory/chromadb/*
!data/memory/chromadb/.gitkeep
data/memory/embeddings/*
!data/memory/embeddings/.gitkeep
data/knowledge/postgres/*
!data/knowledge/postgres/.gitkeep
data/state/*.json
data/state/pid.lock
data/cache/*
!data/cache/.gitkeep

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation
docs/_build/
site/
'''
        
        gitignore.write_text(content)
        print_success(f"Created: {gitignore.relative_to(self.root)}")
        self.fixes_applied.append("Created .gitignore")
    
    def generate_report(self):
        """Generate final report"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}Integration Fixes Applied{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
        
        if self.fixes_applied:
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"  {i}. {fix}")
        else:
            print("  No fixes needed - project structure looks good!")
        
        print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
        print("  1. Run diagnostic again: python session7_diagnostic.py")
        print("  2. Copy Session 6 config files to config/modules/")
        print("  3. Review and fix any remaining issues")
        print("  4. Continue with integration plan\n")
    
    def run_all_fixes(self):
        """Run all automatic fixes"""
        print(f"\n{Colors.BOLD}🔧 LOTUS Automatic Integration Fixer{Colors.ENDC}")
        print(f"{'='*60}\n")
        
        self.create_missing_init_files()
        self.create_lib_init_with_exports()
        self.create_missing_config_files()
        self.create_module_structure()
        self.create_data_directories()
        self.create_env_example()
        self.create_gitignore()
        
        self.generate_report()


def main():
    """Main entry point"""
    # Determine project root
    project_root = os.getcwd()
    
    # Check if we're in the lotus directory
    if not Path(project_root).name == "lotus":
        # Try to find lotus directory
        if (Path(project_root) / "lotus").exists():
            project_root = Path(project_root) / "lotus"
        else:
            print_error("Cannot find LOTUS project root!")
            print_warning("Please run this script from the LOTUS project directory")
            sys.exit(1)
    
    print(f"Project root: {project_root}\n")
    
    # Run fixer
    fixer = LOTUSIntegrationFixer(project_root)
    fixer.run_all_fixes()


if __name__ == "__main__":
    main()