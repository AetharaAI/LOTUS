#!/usr/bin/env python3
"""
Quick fix script for LOTUS manifest dependencies issue.
This will fix the 'dependencies: []' problem by changing it to proper dict structure.
"""

import yaml
from pathlib import Path
import shutil
from datetime import datetime

def fix_manifest(file_path):
    """Fix a single manifest file"""
    print(f"Fixing: {file_path}")
    
    # Backup original
    backup_path = file_path.with_suffix('.yaml.backup')
    shutil.copy2(file_path, backup_path)
    print(f"  Backed up to: {backup_path}")
    
    # Load the manifest
    with open(file_path, 'r') as f:
        content = yaml.safe_load(f)
    
    # Fix dependencies if it's a list
    if isinstance(content.get('dependencies'), list):
        print(f"  Found list dependencies: {content['dependencies']}")
        # Convert empty list to proper dict structure
        if len(content['dependencies']) == 0:
            content['dependencies'] = {
                'modules': [],
                'system': [],
                'packages': []
            }
        else:
            # If there were items in the list, preserve them as modules
            content['dependencies'] = {
                'modules': content['dependencies'],
                'system': [],
                'packages': []
            }
        print(f"  Fixed to dict structure")
    
    # Write back the fixed content
    with open(file_path, 'w') as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False)
    
    print(f"  ✓ Fixed successfully!")
    return True

def main():
    """Fix all manifest files in the LOTUS modules directory"""
    print("🔧 LOTUS Manifest Fixer")
    print("=" * 60)
    print()
    
    # Find all manifest.yaml files
    base_path = Path.cwd()
    manifest_files = list(base_path.glob("modules/**/manifest.yaml"))
    
    print(f"Found {len(manifest_files)} manifest files")
    print()
    
    fixed_count = 0
    for manifest_path in manifest_files:
        try:
            # Check if it needs fixing
            with open(manifest_path, 'r') as f:
                content = yaml.safe_load(f)
                if isinstance(content.get('dependencies'), list):
                    if fix_manifest(manifest_path):
                        fixed_count += 1
                    print()
                else:
                    print(f"Skipping (already correct): {manifest_path}")
        except Exception as e:
            print(f"❌ Error fixing {manifest_path}: {e}")
    
    print("=" * 60)
    print(f"✅ Fixed {fixed_count} manifest files")
    print()
    print("You can now run: python nucleus.py")
    print()
    print("To restore backups if needed:")
    print("  find . -name '*.yaml.backup' -exec bash -c 'mv {} ${0%.backup}' {} \\;")

if __name__ == "__main__":
    main()