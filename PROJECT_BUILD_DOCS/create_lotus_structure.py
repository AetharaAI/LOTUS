
import os
from pathlib import Path

def create_lotus_structure(base_dir='lotus'):
    """
    Creates the complete LOTUS project file structure with empty files.
    
    Run this script in the directory where you want the 'lotus/' folder to be created.
    All files will be empty (0 bytes) for you to overwrite with your code.
    """
    root = Path(base_dir)
    root.mkdir(exist_ok=True)
    
    # Define the directory tree as a nested dictionary
    # Keys are file/dir names, values are {} for empty files, or sub-dicts for directories
    tree = {
        # Root files
        'nucleus.py': {},
        'cli.py': {},
        'setup.py': {},
        'requirements.txt': {},
        'README.md': {},
        'LICENSE': {},
        '.gitignore': {},
        '.env.example': {},
        'docker-compose.yml': {},
        'Dockerfile': {},
        
        # config/
        'config': {
            'system.yaml': {},
            'providers.yaml': {},
            'memory.yaml': {},
            'security.yaml': {},
            'modules': {
                'reasoning.yaml': {},
                'memory.yaml': {},
                'providers.yaml': {},
                'code_assistant.yaml': {},
            }
        },
        
        # modules/
        'modules': {
            '__init__.py': {},
            'core_modules': {
                '__init__.py': {},
                'reasoning': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'react_engine.py': {},
                    'context_builder.py': {},
                    'tool_manager.py': {},
                    'README.md': {},
                },
                'memory': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'working_memory.py': {},
                    'short_term.py': {},
                    'long_term.py': {},
                    'persistent.py': {},
                    'retrieval.py': {},
                    'consolidation.py': {},
                },
                'providers': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'anthropic.py': {},
                    'openai.py': {},
                    'google.py': {},
                    'ollama.py': {},
                    'openrouter.py': {},
                    'litellm.py': {},
                    'base_provider.py': {},
                },
                'perception': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'file_watcher.py': {},
                    'clipboard_monitor.py': {},
                    'input_processor.py': {},
                }
            },
            'capability_modules': {
                '__init__.py': {},
                'voice_interface': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'stt.py': {},
                    'tts.py': {},
                    'wake_word.py': {},
                    'voice_profiles.py': {},
                },
                'screen_analyzer': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'capture.py': {},
                    'change_detector.py': {},
                    'ocr.py': {},
                    'visual_analyzer.py': {},
                },
                'code_assistant': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'analyzer.py': {},
                    'debugger.py': {},
                    'generator.py': {},
                    'refactor.py': {},
                    'patterns.py': {},
                },
                'task_delegator': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'task_analyzer.py': {},
                    'router.py': {},
                    'parallel.py': {},
                    'synthesizer.py': {},
                },
                'self_modifier': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'generator.py': {},
                    'validator.py': {},
                    'sandbox.py': {},
                    'deployer.py': {},
                    'version_control.py': {},
                }
            },
            'integration_modules': {
                '__init__.py': {},
                'computer_use': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'mouse.py': {},
                    'keyboard.py': {},
                    'screenshot.py': {},
                    'executor.py': {},
                },
                'mcp_protocol': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'server.py': {},
                    'client.py': {},
                    'tools.py': {},
                },
                'browser_control': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'playwright_driver.py': {},
                    'selenium_driver.py': {},
                    'parser.py': {},
                },
                'ide_integration': {
                    '__init__.py': {},
                    'manifest.yaml': {},
                    'module.json': {},
                    'logic.py': {},
                    'vscode.py': {},
                    'jetbrains.py': {},
                    'lsp_client.py': {},
                }
            }
        },
        
        # lib/
        'lib': {
            '__init__.py': {},
            'module.py': {},
            'decorators.py': {},
            'message_bus.py': {},
            'memory.py': {},
            'providers.py': {},
            'config.py': {},
            'utils.py': {},
            'exceptions.py': {},
            'logging.py': {},
            'security.py': {},
            'validators.py': {},
        },
        
        # data/
        'data': {
            'memory': {
                'chromadb': {},  # Empty dir
                'embeddings': {},  # Empty dir
                'snapshots': {},  # Empty dir
            },
            'knowledge': {
                'postgres': {},  # Empty dir
                'backups': {},  # Empty dir
                'exports': {},  # Empty dir
            },
            'logs': {
                'nucleus.log': {},
                'modules': {},  # Empty dir
                'errors': {},  # Empty dir
                'audit': {},  # Empty dir
            },
            'state': {
                'pid.lock': {},
                'module_state.json': {},
                'checkpoints': {},  # Empty dir
            }
        },
        
        # scripts/
        'scripts': {
            'setup.sh': {},
            'install_module.py': {},
            'backup.py': {},
            'restore.py': {},
            'migrate.py': {},
            'benchmark.py': {},
            'dev': {
                'reset_db.sh': {},
                'generate_module.py': {},
                'test_module.py': {},
            }
        },
        
        # tests/
        'tests': {
            '__init__.py': {},
            'conftest.py': {},
            'unit': {
                'test_nucleus.py': {},
                'test_module_system.py': {},
                'test_message_bus.py': {},
                'test_memory.py': {},
                'modules': {},  # Empty dir for module-specific tests
            },
            'integration': {
                'test_full_workflow.py': {},
                'test_module_loading.py': {},
                'test_multi_module.py': {},
            }
        },
        
        # docs/
        'docs': {
            'README.md': {},
            'ARCHITECTURE.md': {},
            'GETTING_STARTED.md': {},
            'MODULE_DEVELOPMENT.md': {},
            'API_REFERENCE.md': {},
            'CONFIGURATION.md': {},
            'DEPLOYMENT.md': {},
            'TROUBLESHOOTING.md': {},
            'examples': {
                'basic_module.py': {},
                'advanced_module.py': {},
                'custom_provider.py': {},
            }
        },
        
        # registry/
        'registry': {
            'official': {
                'catalog.json': {},
            },
            'community': {
                'catalog.json': {},
            },
            'private': {
                'catalog.json': {},
            }
        },
        
        # .lotus/
        '.lotus': {
            'cache': {},  # Empty dir
            'temp': {},  # Empty dir
            'downloads': {},  # Empty dir
            'workspace': {},  # Empty dir
        }
    }
    
    def _create_tree(path: Path, tree_dict: dict):
        for name, sub_tree in tree_dict.items():
            full_path = path / name
            if isinstance(sub_tree, dict) and sub_tree:  # Directory with contents
                full_path.mkdir(exist_ok=True)
                _create_tree(full_path, sub_tree)
            else:  # File (empty)
                if full_path.suffix or name.startswith('.'):  # Ensure files are created
                    full_path.touch(exist_ok=True)
    
    _create_tree(root, tree)
    
    print(f"Created LOTUS structure in '{base_dir}/' with all empty files and directories.")

if __name__ == "__main__":
    create_lotus_structure()
