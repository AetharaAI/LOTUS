#!/usr/bin/env python3
"""
Lotus Flow Mapper: Static analyzer for boot flow, module deps, and pub/sub.
Run: python lotus_flow_mapper.py
Outputs: Text summary + flow.dot (viz w/ graphviz).
"""

import ast
import yaml
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

# Point to your nucleus.py and module dirs
NUCLEUS_PATH = Path("nucleus.py")  # Adjust if needed
MODULE_BASE = Path("modules")  # Your base modules dir

class FlowVisitor(ast.NodeVisitor):
    """AST visitor to extract boot flow from docstrings."""
    def __init__(self):
        self.boot_steps = []
    
    def visit_AsyncFunctionDef(self, node):
        if node.name == 'boot':
            docstring = ast.get_docstring(node)
            if docstring:
                lines = docstring.split('\n')
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith(tuple(f"{i}." for i in range(1, 10))):
                        self.boot_steps.append(stripped)
        self.generic_visit(node)

def scan_modules() -> Dict[str, Dict]:
    """Scan module dirs for manifests, extract deps + subs."""
    modules = {}
    subdirs = ["core_modules", "capabilities", "integrations", "personalities"]
    for subdir in subdirs:
        mod_dir = MODULE_BASE / subdir
        if not mod_dir.exists():
            continue
        for mod_path in mod_dir.iterdir():
            if not mod_path.is_dir():
                continue
            manifest_path = mod_path / "manifest.yaml"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = yaml.safe_load(f) or {}
                mod_name = mod_path.name
                modules[mod_name] = {
                    "deps": manifest.get("dependencies", {}).get("modules", []),
                    "subs": manifest.get("subscriptions", []),
                    "type": manifest.get("type", "unknown")
                }
    return modules

def generate_dot(modules: Dict[str, Dict]) -> str:
    """Generate DOT graph for deps + subs."""
    dot = 'digraph LotusFlow {\n    rankdir=LR;\n    node [shape=box, style=filled];\n'
    dot += '    Nucleus [fillcolor=lightblue];\n'
    
    # Modules as nodes
    for mod, info in modules.items():
        color = "lightgreen" if info["type"] == "core" else "yellow"
        dot += f'    {mod} [fillcolor={color}, label="{mod}\\nType: {info["type"]}"];\n'
        dot += f'    Nucleus -> {mod};\n'
    
    # Dep edges
    for mod, info in modules.items():
        for dep in info["deps"]:
            if dep in modules:
                dot += f'    {dep} -> {mod} [style=dashed, label="dep"];\n'
    
    # Sub edges (group by pattern)
    patterns = {}
    for mod, info in modules.items():
        for sub in info["subs"]:
            pat = sub.get("pattern", "unknown")
            if pat not in patterns:
                patterns[pat] = []
            patterns[pat].append(f"{mod}::{sub.get('handler', 'handle')}")

    for pat, handlers in patterns.items():
        pat_node = f"PubSub_{pat.replace('.', '_')}"
        dot += f'    {pat_node} [shape=ellipse, fillcolor=pink, label="{pat}"];\n'
        for handler in handlers:
            mod = handler.split("::")[0]
            dot += f'    {mod} -> {pat_node} [style=dotted, label="sub"];\n'

    dot += '}'
    return dot

def main():
    if not NUCLEUS_PATH.exists():
        print("❌ nucleus.py not found—adjust NUCLEUS_PATH.")
        sys.exit(1)
    
    # Parse boot flow
    with open(NUCLEUS_PATH) as f:
        code = f.read()
    tree = ast.parse(code)
    visitor = FlowVisitor()
    visitor.visit(tree)
    
    print("🌸 LOTUS Intended Boot Flow (from nucleus.py docstring):")
    for i, step in enumerate(visitor.boot_steps, 1):
        print(f"  {i:2d}. {step}")
    print()
    
    # Scan modules
    modules = scan_modules()
    if not modules:
        print("⚠️  No modules found—check MODULE_BASE path.")
    else:
        print(f"📂 Discovered {len(modules)} modules:")
        for mod, info in modules.items():
            deps_str = f" (deps: {', '.join(info['deps'])})" if info["deps"] else ""
            print(f"  - {mod}{deps_str}")
            if info["subs"]:
                print(f"    Subs: {[s.get('pattern', '?') for s in info['subs']]}")
        print()
    
    # Generate + save graph
    dot = generate_dot(modules)
    with open("flow.dot", "w") as f:
        f.write(dot)
    print("📊 Flow graph saved to 'flow.dot' (run 'dot -Tpng flow.dot -o flow.png' to viz).")
    print("\nSample DOT Preview:")
    print(dot[:200] + "...")  # Truncated preview

if __name__ == "__main__":
    main()