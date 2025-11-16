"""Fix imports in all Python files to use lotus.lib instead of lib"""

import os
import re
from pathlib import Path

def fix_imports(file_path):
    """Fix imports in a single file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace "from lib." with "from lotus.lib."
    fixed = re.sub(r'from lib\.', 'from lotus.lib.', content)
    # Replace "import lib." with "import lotus.lib."
    fixed = re.sub(r'import lib\.', 'import lotus.lib.', fixed)
    
    if fixed != content:
        print(f"Fixing imports in {file_path}")
        with open(file_path, 'w') as f:
            f.write(fixed)

def main():
    # Start from the lotus/modules directory
    modules_dir = Path(__file__).parent / 'lotus' / 'modules'
    
    # Walk through all Python files
    for root, _, files in os.walk(modules_dir):
        for file in files:
            if file.endswith('.py'):
                fix_imports(os.path.join(root, file))

if __name__ == '__main__':
    main()