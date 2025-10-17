#!/usr/bin/env python3
"""
LOTUS Manifest Diagnostic Tool

This tool will scan all your manifest.yaml files and identify which ones are malformed.
Run this in your lotus directory to find and fix the problematic manifest files.
"""

import yaml
import sys
from pathlib import Path
import json

def check_manifest(manifest_path):
    """Check if a manifest file is properly formatted"""
    issues = []
    
    try:
        with open(manifest_path, 'r') as f:
            content = f.read()
            manifest = yaml.safe_load(content)
            
            # Check if it's a valid dictionary
            if manifest is None:
                issues.append("Empty file")
            elif isinstance(manifest, list):
                issues.append("Root element is a list (should be a dictionary/mapping)")
                issues.append("Hint: Remove any leading '- ' from the first line")
            elif not isinstance(manifest, dict):
                issues.append(f"Root element is {type(manifest).__name__} (should be dict)")
            else:
                # Check for required fields
                if "name" not in manifest:
                    issues.append("Missing 'name' field")
                if "version" not in manifest:
                    issues.append("Missing 'version' field")
                    
                # Check dependencies structure
                if "dependencies" in manifest:
                    deps = manifest["dependencies"]
                    if not isinstance(deps, dict):
                        issues.append(f"'dependencies' is {type(deps).__name__} (should be dict)")
                    elif "modules" in deps:
                        if not isinstance(deps["modules"], list):
                            issues.append(f"'dependencies.modules' is {type(deps['modules']).__name__} (should be list)")
            
            return manifest, issues
            
    except yaml.YAMLError as e:
        issues.append(f"YAML parsing error: {e}")
        return None, issues
    except Exception as e:
        issues.append(f"Unexpected error: {e}")
        return None, issues

def scan_modules(base_path="."):
    """Scan all modules for manifest issues"""
    base = Path(base_path)
    
    module_dirs = [
        base / "modules" / "core_modules",
        base / "modules" / "capabilities",
        base / "modules" / "integrations",
        base / "modules" / "personalities"
    ]
    
    print("🔍 LOTUS Manifest Diagnostic Tool")
    print("=" * 60)
    print()
    
    total_modules = 0
    problem_modules = []
    
    for module_dir in module_dirs:
        if not module_dir.exists():
            continue
            
        print(f"📁 Scanning: {module_dir.relative_to(base)}")
        
        for module_path in sorted(module_dir.iterdir()):
            if not module_path.is_dir():
                continue
                
            manifest_path = module_path / "manifest.yaml"
            if not manifest_path.exists():
                continue
                
            total_modules += 1
            module_name = module_path.name
            
            manifest, issues = check_manifest(manifest_path)
            
            if issues:
                problem_modules.append((module_name, manifest_path, issues))
                print(f"   ❌ {module_name}: {len(issues)} issue(s)")
                for issue in issues:
                    print(f"      - {issue}")
            else:
                print(f"   ✓ {module_name}: OK")
        print()
    
    print("=" * 60)
    print(f"📊 Summary: Scanned {total_modules} modules")
    
    if problem_modules:
        print(f"❌ Found {len(problem_modules)} module(s) with issues:")
        print()
        
        for module_name, path, issues in problem_modules:
            print(f"Module: {module_name}")
            print(f"File: {path}")
            print("Issues:")
            for issue in issues:
                print(f"  - {issue}")
            print()
            
            # Show how to fix common issues
            if any("list" in issue for issue in issues):
                print("💡 HOW TO FIX:")
                print("   Your manifest starts with a dash '-' making it a list.")
                print("   Remove the leading dash from the first line.")
                print()
                print("   WRONG:")
                print("   - name: my_module")
                print("     version: 1.0.0")
                print()
                print("   CORRECT:")
                print("   name: my_module")
                print("   version: 1.0.0")
                print()
    else:
        print("✅ All manifests are properly formatted!")
    
    return len(problem_modules) == 0

def generate_example_manifest():
    """Generate an example manifest.yaml"""
    example = {
        "name": "example_module",
        "version": "1.0.0",
        "type": "capability",
        "author": "LOTUS Team",
        "description": "Example module manifest",
        "priority": "normal",
        "dependencies": {
            "modules": ["reasoning", "memory"],
            "system": ["python>=3.10"],
            "packages": []
        },
        "subscriptions": [
            {
                "pattern": "perception.user_input",
                "handler": "handle_input"
            }
        ],
        "publications": [
            "action.response"
        ],
        "providers": {
            "primary": "claude-3-opus",
            "fallback": ["gpt-4"]
        },
        "memory": {
            "vector_collections": ["example_collection"],
            "state_keys": ["example_state"]
        },
        "capabilities": [
            "example_capability"
        ],
        "config_schema": {
            "enabled": True,
            "debug": False
        }
    }
    
    print("\n" + "=" * 60)
    print("📝 EXAMPLE MANIFEST.YAML:")
    print("=" * 60)
    print(yaml.dump(example, default_flow_style=False, sort_keys=False))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnose LOTUS manifest files")
    parser.add_argument("--path", default=".", help="Path to LOTUS directory")
    parser.add_argument("--example", action="store_true", help="Show example manifest")
    
    args = parser.parse_args()
    
    if args.example:
        generate_example_manifest()
    else:
        success = scan_modules(args.path)
        sys.exit(0 if success else 1)