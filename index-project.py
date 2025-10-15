# index-project.py
import os
from pathlib import Path
from collections import defaultdict
import json  # For potential exports

# Updated EXPECTED_STRUCTURE parsed/refined from Project_Structure.md (Oct 14, 2025)
# Ignored extras like 'consciousness' module; focused on core/complete tree.
# Nested as {'files': [...], 'subdirs': {...}} for recursive scanning.
EXPECTED_STRUCTURE = {
    'root_files': [
        'nucleus.py', 'cli.py', 'setup.py', 'requirements.txt', 'README.md', 'LICENSE',
        '.gitignore', '.env.example', 'docker-compose.yml', 'Dockerfile'
    ],
    'dirs': {
        'config': {
            'files': ['system.yaml', 'providers.yaml', 'memory.yaml', 'security.yaml'],
            'subdirs': {
                'modules': {
                    'files': ['reasoning.yaml', 'memory.yaml', 'providers.yaml', 'code_assistant.yaml']  # + ... for others
                }
            }
        },
        'modules': {
            'files': ['__init__.py', 'README.md'],
            'subdirs': {
                'core_modules': {
                    'files': ['__init__.py'],
                    'subdirs': {
                        'reasoning': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'react_engine.py', 'context_builder.py', 'tool_manager.py', 'README.md']
                        },
                        'memory': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'working_memory.py', 'short_term.py', 'long_term.py', 'persistent.py', 'retrieval.py', 'consolidation.py']
                        },
                        'providers': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'anthropic.py', 'openai.py', 'google.py', 'ollama.py', 'openrouter.py', 'litellm.py', 'base_provider.py']
                        },
                        'perception': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'file_watcher.py', 'clipboard_monitor.py', 'input_processor.py']
                        }
                    }
                },
                'capability_modules': {
                    'files': ['__init__.py'],
                    'subdirs': {
                        'voice_interface': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'stt.py', 'tts.py', 'wake_word.py', 'voice_profiles.py']
                        },
                        'screen_analyzer': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'capture.py', 'change_detector.py', 'ocr.py', 'visual_analyzer.py']
                        },
                        'code_assistant': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'analyzer.py', 'debugger.py', 'generator.py', 'refactor.py', 'patterns.py']
                        },
                        'task_delegator': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'task_analyzer.py', 'router.py', 'parallel.py', 'synthesizer.py']
                        },
                        'self_modifier': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'generator.py', 'validator.py', 'sandbox.py', 'deployer.py', 'version_control.py']
                        }
                    }
                },
                'integration_modules': {
                    'files': ['__init__.py'],
                    'subdirs': {
                        'computer_use': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'mouse.py', 'keyboard.py', 'screenshot.py', 'executor.py']
                        },
                        'mcp_protocol': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'server.py', 'client.py', 'tools.py']
                        },
                        'browser_control': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'playwright_driver.py', 'selenium_driver.py', 'parser.py']
                        },
                        'ide_integration': {
                            'files': ['__init__.py', 'manifest.yaml', 'module.json', 'logic.py', 'vscode.py', 'jetbrains.py', 'lsp_client.py']
                        }
                    }
                }
            }
        },
        'lib': {
            'files': [
                '__init__.py', 'module.py', 'decorators.py', 'message_bus.py', 'memory.py',
                'providers.py', 'config.py', 'utils.py', 'exceptions.py', 'logging.py',
                'security.py', 'validators.py'
            ],
            'subdirs': {}
        },
        'data': {
            'files': [],
            'subdirs': {
                'memory': {
                    'files': [],
                    'subdirs': {'chromadb': {'files': []}, 'embeddings': {'files': []}, 'snapshots': {'files': []}}
                },
                'knowledge': {
                    'files': [],
                    'subdirs': {'postgres': {'files': []}, 'backups': {'files': []}, 'exports': {'files': []}}
                },
                'logs': {
                    'files': ['nucleus.log'],
                    'subdirs': {'modules': {'files': []}, 'errors': {'files': []}, 'audit': {'files': []}}
                },
                'state': {
                    'files': ['pid.lock', 'module_state.json'],
                    'subdirs': {'checkpoints': {'files': []}}
                }
            }
        },
        'scripts': {
            'files': ['setup.sh', 'install_module.py', 'backup.py', 'restore.py', 'migrate.py', 'benchmark.py'],
            'subdirs': {
                'dev': {
                    'files': ['reset_db.sh', 'generate_module.py', 'test_module.py'],
                    'subdirs': {}
                }
            }
        },
        'tests': {
            'files': ['__init__.py', 'conftest.py'],
            'subdirs': {
                'unit': {
                    'files': ['test_nucleus.py', 'test_module_system.py', 'test_message_bus.py', 'test_memory.py'],
                    'subdirs': {'modules': {'files': []}}
                },
                'integration': {
                    'files': ['test_full_workflow.py', 'test_module_loading.py', 'test_multi_module.py'],
                    'subdirs': {}
                }
            }
        },
        'docs': {
            'files': [
                'README.md', 'ARCHITECTURE.md', 'GETTING_STARTED.md', 'MODULE_DEVELOPMENT.md',
                'API_REFERENCE.md', 'CONFIGURATION.md', 'DEPLOYMENT.md', 'TROUBLESHOOTING.md'
            ],
            'subdirs': {
                'examples': {
                    'files': ['basic_module.py', 'advanced_module.py', 'custom_provider.py'],
                    'subdirs': {}
                }
            }
        },
        'registry': {
            'files': [],
            'subdirs': {
                'official': {'files': ['catalog.json']},
                'community': {'files': ['catalog.json']},
                'private': {'files': ['catalog.json']}
            }
        },
        '.lotus': {
            'files': [],
            'subdirs': {
                'cache': {'files': []},
                'temp': {'files': []},
                'downloads': {'files': []},
                'workspace': {'files': []}
            }
        }
    }
}

def build_tree(path, prefix='', is_last=True):
    """Build a tree string representation (ASCII-safe)."""
    tree_lines = []
    items = sorted([item for item in os.listdir(path) if not item.startswith('.') or item == '.lotus'])
    for i, item in enumerate(items):
        item_path = os.path.join(path, item)
        connector = '└── ' if i == len(items) - 1 else '├── '
        item_str = f"{item}/" if os.path.isdir(item_path) else item
        tree_lines.append(f"{prefix}{connector}{item_str}")
        if os.path.isdir(item_path):
            extension = '    ' if i == len(items) - 1 else '│   '
            subtree = build_tree(item_path, prefix + extension, i == len(items) - 1)
            tree_lines.extend(subtree)
    return tree_lines

def check_file_status(full_path):
    """Check if file exists and its status (heuristic-based)."""
    if not os.path.exists(full_path):
        return '❌ Missing'
    size = os.path.getsize(full_path)
    ext = Path(full_path).suffix.lower()
    if ext == '.py' and size > 200:  # Bumped for more robust "coded" check
        return '✅ Coded'
    elif ext in ['.yaml', '.yml', '.json', '.md'] and size > 100:
        return '✅ Complete'
    elif size == 0:
        return '⚠️ Empty'
    else:
        return '⚠️ Stub/Partial'

def scan_directory(base_path, structure, current_path='', file_status={}):
    """Recursively scan actual dir vs expected structure, update status."""
    abs_path = os.path.join(base_path, current_path) if current_path else base_path
    if not os.path.exists(abs_path):
        return file_status

    # Scan existing files/dirs
    for item in os.listdir(abs_path):
        item_path = os.path.join(abs_path, item)
        rel_path = os.path.join(current_path, item) if current_path else item
        if os.path.isfile(item_path):
            file_status[rel_path] = check_file_status(item_path)
        else:
            scan_directory(base_path, structure, rel_path, file_status)

    # Flag expected missing files from structure
    def flag_missing(curr_struct, curr_rel):
        for exp_file in curr_struct.get('files', []):
            exp_rel = os.path.join(curr_rel, exp_file) if curr_rel else exp_file
            if exp_rel not in file_status:
                file_status[exp_rel] = '❌ Missing (Expected)'
        for subdir, sub_struct in curr_struct.get('subdirs', {}).items():
            sub_rel = os.path.join(curr_rel, subdir) if curr_rel else subdir
            flag_missing(sub_struct, sub_rel)

    if current_path:
        # For root, start with dirs
        root_struct = structure
    else:
        root_struct = {'dirs': structure['dirs'], 'files': []}  # Treat root specially
    flag_missing(root_struct, current_path)

    return file_status

def detect_duplicates_and_conflicts(file_status):
    """Detect duplicates by basename across dirs (e.g., multiple manifest.yaml)."""
    dups = defaultdict(list)
    for path, status in file_status.items():
        if status != '❌ Missing (Expected)':  # Only actual/existing
            basename = Path(path).name
            dups[basename].append(path)
    conflicts = {k: v for k, v in dups.items() if len(v) > 1}
    return conflicts

def generate_index(base_dir='lotus', output_file='lotus_index.md'):
    """Generate comprehensive Markdown index report."""
    if not os.path.exists(base_dir):
        return f"# LOTUS Project Index\n\n❌ Directory '{base_dir}' not found. Run from parent of lotus/ or adjust base_dir."

    # Build actual tree
    tree_lines = ['```ascii']
    tree_lines.extend(build_tree(base_dir))
    tree_lines.append('```')

    # Scan status
    file_status = scan_directory(base_dir, EXPECTED_STRUCTURE)

    # Duplicates/conflicts
    conflicts = detect_duplicates_and_conflicts(file_status)

    # Progress metrics
    total_expected = sum(len(s.get('files', [])) + sum(len(ss.get('files', [])) for ss in s.get('subdirs', {}).values())
                       for s in [EXPECTED_STRUCTURE] + [v for d in EXPECTED_STRUCTURE['dirs'].values() for v in [d] + list(d.get('subdirs', {}).values())])
    total_scanned = len(file_status)
    implemented = sum(1 for s in file_status.values() if '✅' in s)
    progress = (implemented / total_scanned * 100) if total_scanned > 0 else 0

    # MD Report
    md = f"""# LOTUS Project Index - Full Context Report (Updated Oct 14, 2025)

**Scan Path:** `{os.path.abspath(base_dir)}`  
**Generated:** {os.popen('date').read().strip()}  
**Total Expected Files:** ~{total_expected} (per Project_Structure.md)  
**Files Scanned:** {total_scanned}  
**Implemented/Coded:** {implemented} ({progress:.1f}%)  
**Notes:** Based on complete tree from Project_Structure.md. Extras (e.g., consciousness module) ignored. Use for LLM context—paste into Claude.ai knowledge.

## 📂 Actual Directory Tree (Current State)

{chr(10).join(tree_lines)}

## 📋 File Status Inventory (Actual vs Expected)

| Relative Path | Status | Notes |
|---------------|--------|-------|
"""
    for path in sorted(file_status.keys()):
        status = file_status[path]
        notes = 'Expected core file' if '(Expected)' in status else ''
        md += f"| `{path}` | {status} | {notes} |\n"

    md += "\n## 🔍 Duplicates/Conflicts (e.g., manifest.yaml in multiple modules)\n\n"
    if conflicts:
        for basename, paths in sorted(conflicts.items()):
            md += f"- **{basename}** in: {', '.join(f'`{p}`' for p in paths)}\n  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.\n"
    else:
        md += "✅ No conflicts—structure clean! (Paths uniquify duplicates.)\n"

    md += """
## 🏗️ Implementation Gaps & Next Steps (From Sessions 1-2 + Structure)

- **✅ Complete/Core (Per INDEX.md):** lib/ (BaseModule, etc.), modules/core_modules/memory/* (4-tier), providers/* (LLM routing), perception/* (file/clipboard watch).
- **⚠️ Partial (70%):** modules/core_modules/reasoning/* (ReAct loop—add react_engine.py, tool_manager.py).
- **❌ Missing Priorities (Implement Next):**
  - capability_modules/voice_interface/* (STT/TTS—Whisper/ElevenLabs deps in requirements.txt).
  - capability_modules/screen_analyzer/* (Capture/OCR—mss/Pillow).
  - integration_modules/computer_use/* (Mouse/keyboard—pyautogui/pynput).
  - docs/* (Full guides—e.g., MODULE_DEVELOPMENT.md for @on_event examples).
  - scripts/dev/generate_module.py (Template gen for new modules).
- **Standard Module Template (Enforce):**
  ```
  module_name/
  ├── __init__.py
  ├── manifest.yaml  # Subscriptions/publications/tools/providers
  ├── module.json    # Metadata/version
  ├── logic.py       # class MyModule(BaseModule): @on_event... @tool...
  └── README.md
  ```
- **Naming/Import Rules (For Claude/LLMs):**
  - **Classes:** Inherit `BaseModule` from `lib/module.py`.
  - **Events/Tools:** Use `lib/decorators.py` (@on_event("perception.*"), @tool("analyze_code")).
  - **Imports:** Relative/absolute std (e.g., `from lib.message_bus import MessageBus`; no hard `../` paths).
  - **Configs:** Override in config/modules/{module}.yaml; load via `lib/config.py`.
  - **Discovery:** Nucleus scans modules/*/manifest.yaml—must validate schema.
  - **Memory/Providers:** Access via `self.memory`, `self.llm` in BaseModule.
- **Data Flow Reminder:** User → perception/* events → Redis (lib/message_bus.py) → reasoning (ReAct) → memory/providers → action/* outputs.
- **Tips for Next Session (e.g., Session 3 Voice/Screen):** Generate missing files with `mkdir -p path/to/module && echo 'class ... (BaseModule):' > logic.py`. Test via `python tests/unit/test_memory.py`. Reference requirements.txt for deps.

**Full Context for LLMs:** This report = tree + status + rules. No need for file dumps—generate code respecting paths/imports. Progress to 100% by filling gaps.

---

*Auto-generated via Grok—refined from Project_Structure.md v1.0.*"""

    # Save MD
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md)

    # Optional: JSON export for scripting
    json_data = {
        'tree_lines': tree_lines[1:-1],  # Raw tree
        'file_status': dict(sorted(file_status.items())),
        'conflicts': dict(sorted(conflicts.items())) if conflicts else {},
        'progress': progress
    }
    with open('lotus_index.json', 'w') as f:
        json.dump(json_data, f, indent=2)

    print(f"✅ Full index generated: {output_file} (MD) + lotus_index.json")
    print(md)  # Console output for immediate copy-paste to Claude

if __name__ == "__main__":
    generate_index()
