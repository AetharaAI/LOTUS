"""
Universal Module Installation Script

Usage:
    python scripts/install_module.py path/to/module
"""

import os
import sys
import json
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

LOTUS_ROOT = Path(__file__).parent.parent
MODULES_DIR = LOTUS_ROOT / "modules"


class ModuleInstaller:
    """Install and validate LOTUS modules"""
    
    REQUIRED_FILES = [
        "manifest.yaml",
        "module.json",
        "logic.py",
        "__init__.py"
    ]
    
    def __init__(self, module_path: Path):
        self.module_path = Path(module_path)
        self.module_name = self.module_path.name
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Validate module structure"""
        if not self.module_path.exists():
            self.errors.append(f"Module path does not exist: {self.module_path}")
            return False, self.errors, self.warnings
        
        # Check required files
        for required_file in self.REQUIRED_FILES:
            file_path = self.module_path / required_file
            if not file_path.exists():
                self.errors.append(f"Missing required file: {required_file}")
        
        # Validate manifest
        manifest_path = self.module_path / "manifest.yaml"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = yaml.safe_load(f)
                
                # Check required manifest fields
                required_fields = ["name", "version", "type", "description"]
                for field in required_fields:
                    if field not in manifest:
                        self.errors.append(f"Missing manifest field: {field}")
                
                # Validate type
                if manifest.get("type") not in ["core", "capability", "integration"]:
                    self.errors.append(f"Invalid module type: {manifest.get('type')}")
                
            except Exception as e:
                self.errors.append(f"Invalid manifest.yaml: {e}")
        
        # Validate module.json
        module_json_path = self.module_path / "module.json"
        if module_json_path.exists():
            try:
                with open(module_json_path) as f:
                    module_json = json.load(f)
                
                if "name" not in module_json:
                    self.errors.append("module.json missing 'name' field")
                
            except Exception as e:
                self.errors.append(f"Invalid module.json: {e}")
        
        # Validate logic.py exists
        logic_path = self.module_path / "logic.py"
        if not logic_path.exists():
            self.errors.append("Missing logic.py - main module implementation")
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def install(self) -> bool:
        """Install module to LOTUS"""
        # Validate first
        is_valid, errors, warnings = self.validate()
        
        if warnings:
            print("\n⚠️  Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        
        if not is_valid:
            print("\n❌ Validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        # Determine target directory
        with open(self.module_path / "manifest.yaml") as f:
            manifest = yaml.safe_load(f)
        
        module_type = manifest.get("type", "capability")
        target_dir = MODULES_DIR / f"{module_type}_modules" / self.module_name
        
        # Install
        try:
            if target_dir.exists():
                shutil.rmtree(target_dir)
            
            shutil.copytree(self.module_path, target_dir)
            print(f"✅ Module installed: {target_dir}")
            
            return True
        except Exception as e:
            print(f"❌ Installation failed: {e}")
            return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/install_module.py <module_path>")
        sys.exit(1)
    
    module_path = Path(sys.argv[1])
    installer = ModuleInstaller(module_path)
    
    if installer.install():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()