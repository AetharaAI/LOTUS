#!/usr/bin/env python3
"""
Session 7 - LOTUS Integration Diagnostic
=========================================

This script checks the current state of the LOTUS project and identifies:
1. Missing files
2. Import issues
3. Configuration problems
4. Integration gaps

Run this FIRST to understand what needs fixing!
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import importlib.util

# ANSI colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {text}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {text}")

def print_error(text):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {text}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {text}")


class LOTUSDiagnostic:
    """Diagnostic tool for LOTUS project"""
    
    def __init__(self, project_root: str = "."):
        self.root = Path(project_root).resolve()
        self.issues = []
        self.warnings = []
        self.successes = []
        
    def check_directory_structure(self) -> Dict[str, bool]:
        """Check if all required directories exist"""
        print_header("DIRECTORY STRUCTURE CHECK")
        
        required_dirs = [
            "lib",
            "modules",
            "modules/core_modules",
            "modules/core_modules/reasoning",
            "modules/core_modules/memory",
            "modules/core_modules/providers",
            "modules/core_modules/perception",
            "modules/capability_modules",
            "modules/integration_modules",
            "config",
            "config/modules",
            "data",
            "data/logs",
            "data/memory",
            "data/knowledge",
            "scripts",
            "tests"
        ]
        
        results = {}
        for dir_path in required_dirs:
            full_path = self.root / dir_path
            exists = full_path.exists() and full_path.is_dir()
            results[dir_path] = exists
            
            if exists:
                print_success(f"Directory exists: {dir_path}")
            else:
                print_error(f"Directory missing: {dir_path}")
                self.issues.append(f"Missing directory: {dir_path}")
                
        return results
    
    def check_core_files(self) -> Dict[str, bool]:
        """Check if core system files exist"""
        print_header("CORE FILES CHECK")
        
        core_files = [
            "nucleus.py",
            "cli.py",
            "requirements.txt",
            "README.md",
            ".env.example",
            "lib/__init__.py",
            "lib/module.py",
            "lib/decorators.py",
            "lib/message_bus.py",
            "lib/memory.py",
            "lib/providers.py",
            "lib/config.py",
            "lib/logging.py",
            "lib/exceptions.py",
            "lib/utils.py",
            "config/system.yaml",
            "config/providers.yaml"
        ]
        
        results = {}
        for file_path in core_files:
            full_path = self.root / file_path
            exists = full_path.exists() and full_path.is_file()
            results[file_path] = exists
            
            if exists:
                print_success(f"File exists: {file_path}")
            else:
                print_error(f"File missing: {file_path}")
                self.issues.append(f"Missing file: {file_path}")
                
        return results
    
    def check_module_configs(self) -> Dict[str, bool]:
        """Check if module config override files exist"""
        print_header("MODULE CONFIG OVERRIDE FILES CHECK")
        
        config_files = [
            "config/modules/reasoning.yaml",
            "config/modules/memory.yaml",
            "config/modules/providers.yaml",
            "config/modules/code_assistant.yaml",
            "config/modules/perception.yaml",
            "config/modules/consciousness.yaml"
        ]
        
        results = {}
        for file_path in config_files:
            full_path = self.root / file_path
            exists = full_path.exists() and full_path.is_file()
            results[file_path] = exists
            
            if exists:
                print_success(f"Config exists: {file_path}")
                # Check if file is empty
                if full_path.stat().st_size == 0:
                    print_warning(f"  └─ File is EMPTY (needs content)")
                    self.warnings.append(f"Empty config file: {file_path}")
            else:
                print_error(f"Config missing: {file_path}")
                self.issues.append(f"Missing config: {file_path}")
                
        return results
    
    def check_module_manifests(self) -> Dict[str, bool]:
        """Check if core module manifests exist"""
        print_header("MODULE MANIFEST FILES CHECK")
        
        manifests = [
            "modules/core_modules/reasoning/manifest.yaml",
            "modules/core_modules/memory/manifest.yaml",
            "modules/core_modules/providers/manifest.yaml",
            "modules/core_modules/perception/manifest.yaml"
        ]
        
        results = {}
        for file_path in manifests:
            full_path = self.root / file_path
            exists = full_path.exists() and full_path.is_file()
            results[file_path] = exists
            
            if exists:
                print_success(f"Manifest exists: {file_path}")
            else:
                print_error(f"Manifest missing: {file_path}")
                self.issues.append(f"Missing manifest: {file_path}")
                
        return results
    
    def check_module_logic(self) -> Dict[str, bool]:
        """Check if core module logic files exist"""
        print_header("MODULE LOGIC FILES CHECK")
        
        logic_files = [
            "modules/core_modules/reasoning/logic.py",
            "modules/core_modules/memory/logic.py",
            "modules/core_modules/providers/logic.py",
            "modules/core_modules/perception/logic.py"
        ]
        
        results = {}
        for file_path in logic_files:
            full_path = self.root / file_path
            exists = full_path.exists() and full_path.is_file()
            results[file_path] = exists
            
            if exists:
                print_success(f"Logic file exists: {file_path}")
                # Check if file has minimal implementation
                size = full_path.stat().st_size
                if size < 500:  # Less than 500 bytes probably means stub
                    print_warning(f"  └─ File is very small ({size} bytes) - might be incomplete")
                    self.warnings.append(f"Potentially incomplete: {file_path}")
            else:
                print_error(f"Logic file missing: {file_path}")
                self.issues.append(f"Missing logic file: {file_path}")
                
        return results
    
    def check_imports(self) -> List[Tuple[str, bool, str]]:
        """Test if core imports work"""
        print_header("IMPORT CHECKS")
        
        # Add project root to path
        sys.path.insert(0, str(self.root))
        
        import_tests = [
            ("lib.module", "BaseModule"),
            ("lib.decorators", "on_event"),
            ("lib.message_bus", "MessageBus"),
            ("lib.memory", "WorkingMemory"),
            ("lib.providers", "LLMProviderManager"),
            ("lib.config", "Config"),
            ("lib.logging", "setup_logging"),
            ("lib.exceptions", "ModuleLoadError"),
            ("lib.utils", "get_timestamp")
        ]
        
        results = []
        for module_name, attr_name in import_tests:
            try:
                module = importlib.import_module(module_name)
                has_attr = hasattr(module, attr_name)
                
                if has_attr:
                    print_success(f"Import OK: from {module_name} import {attr_name}")
                    results.append((f"{module_name}.{attr_name}", True, ""))
                else:
                    print_error(f"Missing attribute: {module_name}.{attr_name}")
                    results.append((f"{module_name}.{attr_name}", False, f"Attribute {attr_name} not found"))
                    self.issues.append(f"Missing attribute: {module_name}.{attr_name}")
                    
            except ImportError as e:
                print_error(f"Import failed: {module_name} - {str(e)}")
                results.append((module_name, False, str(e)))
                self.issues.append(f"Import error: {module_name} - {str(e)}")
                
        return results
    
    def generate_report(self):
        """Generate final diagnostic report"""
        print_header("DIAGNOSTIC REPORT")
        
        print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
        print(f"  Total Issues: {Colors.FAIL}{len(self.issues)}{Colors.ENDC}")
        print(f"  Total Warnings: {Colors.WARNING}{len(self.warnings)}{Colors.ENDC}")
        
        if self.issues:
            print(f"\n{Colors.BOLD}{Colors.FAIL}Critical Issues:{Colors.ENDC}")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        if self.warnings:
            print(f"\n{Colors.BOLD}{Colors.WARNING}Warnings:{Colors.ENDC}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.issues and not self.warnings:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ No issues found! Project structure looks good!{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}{Colors.BOLD}⚠ Issues found that need attention{Colors.ENDC}")
        
        print()
    
    def run_full_diagnostic(self):
        """Run complete diagnostic"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 58 + "║")
        print("║" + "  LOTUS PROJECT - SESSION 7 DIAGNOSTIC".center(58) + "║")
        print("║" + " " * 58 + "║")
        print("╚" + "═" * 58 + "╝")
        print(f"{Colors.ENDC}")
        
        print_info(f"Project root: {self.root}")
        
        # Run all checks
        self.check_directory_structure()
        self.check_core_files()
        self.check_module_configs()
        self.check_module_manifests()
        self.check_module_logic()
        self.check_imports()
        
        # Generate final report
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
            print_info("Please run this script from the LOTUS project directory")
            sys.exit(1)
    
    # Run diagnostic
    diagnostic = LOTUSDiagnostic(project_root)
    diagnostic.run_full_diagnostic()
    
    # Exit with appropriate code
    if diagnostic.issues:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()