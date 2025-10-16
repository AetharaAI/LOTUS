"""
Pre-flight Validation Script

Run before starting LOTUS to catch configuration issues early.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import List, Dict, Tuple

LOTUS_ROOT = Path(__file__).parent.parent


class LOTUSValidator:
    """Validate LOTUS installation"""
    
    def __init__(self):
        self.issues: Dict[str, List[str]] = {
            "critical": [],
            "warning": [],
            "info": []
        }
    
    def validate_all(self) -> Tuple[bool, Dict[str, List[str]]]:
        """Run all validations"""
        print("🔍 Validating LOTUS installation...")
        
        self._check_directories()
        self._check_core_files()
        self._check_configuration()
        self._check_dependencies()
        self._check_environment()
        self._check_modules()
        
        return len(self.issues["critical"]) == 0, self.issues
    
    def _check_directories(self) -> None:
        """Check required directories exist"""
        required_dirs = [
            "lib",
            "modules",
            "config",
            "data",
            "tests",
            "scripts"
        ]
        
        for dir_name in required_dirs:
            dir_path = LOTUS_ROOT / dir_name
            if not dir_path.exists():
                self.issues["critical"].append(f"Missing directory: {dir_name}")
            else:
                self.issues["info"].append(f"✓ Directory found: {dir_name}")
    
    def _check_core_files(self) -> None:
        """Check core files exist"""
        required_files = [
            "nucleus.py",
            "requirements.txt",
            "README.md",
            ".env.example"
        ]
        
        for filename in required_files:
            file_path = LOTUS_ROOT / filename
            if not file_path.exists():
                self.issues["critical"].append(f"Missing file: {filename}")
            else:
                self.issues["info"].append(f"✓ File found: {filename}")
    
    def _check_configuration(self) -> None:
        """Check configuration files"""
        config_files = [
            "config/system.yaml",
            "config/providers.yaml"
        ]
        
        for config_file in config_files:
            config_path = LOTUS_ROOT / config_file
            if not config_path.exists():
                self.issues["critical"].append(f"Missing config: {config_file}")
            else:
                try:
                    with open(config_path) as f:
                        yaml.safe_load(f)
                    self.issues["info"].append(f"✓ Config valid: {config_file}")
                except Exception as e:
                    self.issues["critical"].append(f"Invalid YAML in {config_file}: {e}")
    
    def _check_dependencies(self) -> None:
        """Check Python dependencies"""
        try:
            import redis
            self.issues["info"].append("✓ redis available")
        except ImportError:
            self.issues["warning"].append("redis not installed (redis-py)")
        
        try:
            import anthropic
            self.issues["info"].append("✓ anthropic available")
        except ImportError:
            self.issues["warning"].append("anthropic not installed")
        
        try:
            import openai
            self.issues["info"].append("✓ openai available")
        except ImportError:
            self.issues["warning"].append("openai not installed")
        
        # NEW: Check for xAI dependencies
        try:
            import requests
            self.issues["info"].append("✓ requests available (for xAI)")
        except ImportError:
            self.issues["warning"].append("requests not installed (needed for xAI)")
    
    def _check_environment(self) -> None:
        """Check environment variables"""
        required_env_vars = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
        
        for var in required_env_vars:
            if not os.getenv(var):
                self.issues["warning"].append(f"Missing env var: {var}")
            else:
                self.issues["info"].append(f"✓ Env var set: {var}")
        
        # NEW: Check for xAI API key
        if not os.getenv("XAI_API_KEY"):
            self.issues["warning"].append("Missing XAI_API_KEY (xAI provider won't work)")
    
    def _check_modules(self) -> None:
        """Check module structure"""
        modules_dir = LOTUS_ROOT / "modules"
        
        if not modules_dir.exists():
            self.issues["critical"].append("modules directory missing")
            return
        
        # Count modules
        core_modules = len(list((modules_dir / "core_modules").glob("*")))
        capability_modules = len(list((modules_dir / "capability_modules").glob("*")))
        integration_modules = len(list((modules_dir / "integration_modules").glob("*")))
        
        self.issues["info"].append(f"✓ Found {core_modules} core modules")
        self.issues["info"].append(f"✓ Found {capability_modules} capability modules")
        self.issues["info"].append(f"✓ Found {integration_modules} integration modules")
    
    def print_report(self, issues: Dict[str, List[str]]) -> None:
        """Print validation report"""
        print("\n" + "="*60)
        print("LOTUS VALIDATION REPORT")
        print("="*60)
        
        if issues["critical"]:
            print("\n🚨 CRITICAL ISSUES (Must fix):")
            for issue in issues["critical"]:
                print(f"  ❌ {issue}")
        
        if issues["warning"]:
            print("\n⚠️  WARNINGS (Should fix):")
            for issue in issues["warning"]:
                print(f"  ⚠️  {issue}")
        
        if issues["info"]:
            print("\nℹ️  INFO (All good):")
            for issue in issues["info"]:
                print(f"  {issue}")
        
        print("\n" + "="*60)
        
        if not issues["critical"]:
            print("✅ LOTUS is ready to start!")
        else:
            print(f"❌ Fix {len(issues['critical'])} critical issues before starting")
        
        print("="*60 + "\n")


def main():
    """Run validation"""
    validator = LOTUSValidator()
    is_valid, issues = validator.validate_all()
    validator.print_report(issues)
    
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()