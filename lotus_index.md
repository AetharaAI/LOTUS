# LOTUS Project Index - Full Context Report (Updated Oct 14, 2025)

**Scan Path:** `/home/cory/Desktop/Lotus/lotus`  
**Generated:** Tue Oct 14 07:23:53 PM EDT 2025  
**Total Expected Files:** ~193 (per Project_Structure.md)  
**Files Scanned:** 184  
**Implemented/Coded:** 40 (21.7%)  
**Notes:** Based on complete tree from Project_Structure.md. Extras (e.g., consciousness module) ignored. Use for LLM context—paste into Claude.ai knowledge.

## 📂 Actual Directory Tree (Current State)

```ascii
├── .lotus/
├── README.md
├── cli.py
├── config/
│   ├── memory.yaml
│   ├── modules/
│   │   ├── code_assistant.yaml
│   │   ├── consciousness.yaml
│   │   ├── memory.yaml
│   │   ├── providers.yaml
│   │   └── reasoning.yaml
│   ├── providers.yaml
│   ├── security.yaml
│   └── system.yaml
├── data/
│   ├── knowledge/
│   ├── logs/
│   │   └── nucleus.log
│   ├── memory/
│   └── state/
│       ├── module_state.json
│       └── pid.lock
├── docker-compose.yml
├── docs/
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   ├── CONFIGURATION.md
│   ├── DEPLOYMENT.md
│   ├── GETTING_STARTED.md
│   ├── INDEX_Session_2.md
│   ├── MODULE_DEVELOPMENT.md
│   ├── README_SESSION_1_STATUS.md
│   ├── SESSION_2_SUMMARY_(CLEAN).md
│   ├── TROUBLESHOOTING.md
│   └── examples/
│       ├── advanced_module.py
│       ├── basic_module.py
│       └── custom_provider.py
├── lib/
│   ├── __init__.py
│   ├── config.py
│   ├── decorators.py
│   ├── exceptions.py
│   ├── logging.py
│   ├── memory.py
│   ├── message_bus.py
│   ├── module.py
│   ├── providers.py
│   ├── security.py
│   ├── utils.py
│   └── validators.py
├── modules/
│   ├── __init__.py
│   ├── capability_modules/
│   │   ├── __init__.py
│   │   ├── code_assistant/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py
│   │   │   ├── debugger.py
│   │   │   ├── generator.py
│   │   │   ├── logic.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── patterns.py
│   │   │   └── refactor.py
│   │   ├── consciousness/
│   │   │   ├── __init__.py
│   │   │   ├── important-additions-no-interference.txt
│   │   │   ├── logic.py
│   │   │   └── manifest.yaml
│   │   ├── screen_analyzer/
│   │   │   ├── __init__.py
│   │   │   ├── capture.py
│   │   │   ├── change_detector.py
│   │   │   ├── logic.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── ocr.py
│   │   │   └── visual_analyzer.py
│   │   ├── self_modifier/
│   │   │   ├── __init__.py
│   │   │   ├── deployer.py
│   │   │   ├── generator.py
│   │   │   ├── logic.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── sandbox.py
│   │   │   ├── validator.py
│   │   │   └── version_control.py
│   │   ├── task_delegator/
│   │   │   ├── __init__.py
│   │   │   ├── logic.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── parallel.py
│   │   │   ├── router.py
│   │   │   ├── synthesizer.py
│   │   │   └── task_analyzer.py
│   │   └── voice_interface/
│   │       ├── __init__.py
│   │       ├── logic.py
│   │       ├── manifest.yaml
│   │       ├── module.json
│   │       ├── stt.py
│   │       ├── tts.py
│   │       ├── voice_profiles.py
│   │       └── wake_word.py
│   ├── core_modules/
│   │   ├── __init__.py
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── consolidation.py
│   │   │   ├── logic.py
│   │   │   ├── long_term.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── persistent.py
│   │   │   ├── retrieval.py
│   │   │   ├── short_term.py
│   │   │   └── working_memory.py
│   │   ├── perception/
│   │   │   ├── __init__.py
│   │   │   ├── clipboard_monitor.py
│   │   │   ├── file_watcher.py
│   │   │   ├── input_processor.py
│   │   │   ├── logic.py
│   │   │   ├── manifest.yaml
│   │   │   └── module.json
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── anthropic.py
│   │   │   ├── base_provider.py
│   │   │   ├── google.py
│   │   │   ├── litellm.py
│   │   │   ├── logic.py
│   │   │   ├── manifest.yaml
│   │   │   ├── module.json
│   │   │   ├── ollama.py
│   │   │   ├── openai.py
│   │   │   └── openrouter.py
│   │   └── reasoning/
│   │       ├── README.md
│   │       ├── __init__.py
│   │       ├── context_builder.py
│   │       ├── logic.py
│   │       ├── manifest.yaml
│   │       ├── module.json
│   │       ├── react_engine.py
│   │       └── tool_manager.py
│   ├── hello_world_module/
│   │   ├── __init__.py
│   │   ├── logic.py
│   │   └── manifest.yaml
│   └── integration_modules/
│       ├── __init__.py
│       ├── browser_control/
│       │   ├── __init__.py
│       │   ├── logic.py
│       │   ├── manifest.yaml
│       │   ├── module.json
│       │   ├── parser.py
│       │   ├── playwright_driver.py
│       │   └── selenium_driver.py
│       ├── computer_use/
│       │   ├── __init__.py
│       │   ├── executor.py
│       │   ├── keyboard.py
│       │   ├── logic.py
│       │   ├── manifest.yaml
│       │   ├── module.json
│       │   ├── mouse.py
│       │   └── screenshot.py
│       ├── ide_integration/
│       │   ├── __init__.py
│       │   ├── jetbrains.py
│       │   ├── logic.py
│       │   ├── lsp_client.py
│       │   ├── manifest.yaml
│       │   ├── module.json
│       │   └── vscode.py
│       └── mcp_protocol/
│           ├── __init__.py
│           ├── client.py
│           ├── logic.py
│           ├── manifest.yaml
│           ├── module.json
│           ├── server.py
│           └── tools.py
├── nucleus.py
├── registry/
│   ├── community/
│   │   └── catalog.json
│   ├── official/
│   │   └── catalog.json
│   └── private/
│       └── catalog.json
├── requirements.txt
├── scripts/
│   ├── backup.py
│   ├── benchmark.py
│   ├── dev/
│   │   ├── generate_module.py
│   │   ├── reset_db.sh
│   │   └── test_module.py
│   ├── install_module.py
│   ├── migrate.py
│   ├── restore.py
│   └── setup.sh
├── setup.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── integration/
    │   ├── test_full_workflow.py
    │   ├── test_module_loading.py
    │   └── test_multi_module.py
    └── unit/
        ├── test_memory.py
        ├── test_message_bus.py
        ├── test_module_system.py
        └── test_nucleus.py
```

## 📋 File Status Inventory (Actual vs Expected)

| Relative Path | Status | Notes |
|---------------|--------|-------|
| `.env.example` | ⚠️ Empty |  |
| `.gitignore` | ⚠️ Empty |  |
| `README.md` | ✅ Complete |  |
| `cli.py` | ✅ Coded |  |
| `config/memory.yaml` | ✅ Complete |  |
| `config/modules/code_assistant.yaml` | ⚠️ Empty |  |
| `config/modules/consciousness.yaml` | ✅ Complete |  |
| `config/modules/memory.yaml` | ⚠️ Empty |  |
| `config/modules/providers.yaml` | ⚠️ Empty |  |
| `config/modules/reasoning.yaml` | ⚠️ Empty |  |
| `config/providers.yaml` | ✅ Complete |  |
| `config/security.yaml` | ⚠️ Empty |  |
| `config/system.yaml` | ✅ Complete |  |
| `data/logs/nucleus.log` | ⚠️ Empty |  |
| `data/state/module_state.json` | ⚠️ Empty |  |
| `data/state/pid.lock` | ⚠️ Empty |  |
| `docker-compose.yml` | ⚠️ Empty |  |
| `docs/API_REFERENCE.md` | ⚠️ Empty |  |
| `docs/ARCHITECTURE.md` | ✅ Complete |  |
| `docs/CONFIGURATION.md` | ⚠️ Empty |  |
| `docs/DEPLOYMENT.md` | ⚠️ Empty |  |
| `docs/GETTING_STARTED.md` | ✅ Complete |  |
| `docs/INDEX_Session_2.md` | ✅ Complete |  |
| `docs/MODULE_DEVELOPMENT.md` | ⚠️ Empty |  |
| `docs/README_SESSION_1_STATUS.md` | ✅ Complete |  |
| `docs/SESSION_2_SUMMARY_(CLEAN).md` | ✅ Complete |  |
| `docs/TROUBLESHOOTING.md` | ⚠️ Empty |  |
| `docs/examples/advanced_module.py` | ⚠️ Empty |  |
| `docs/examples/basic_module.py` | ✅ Coded |  |
| `docs/examples/custom_provider.py` | ⚠️ Empty |  |
| `lib/__init__.py` | ✅ Coded |  |
| `lib/config.py` | ✅ Coded |  |
| `lib/decorators.py` | ✅ Coded |  |
| `lib/exceptions.py` | ✅ Coded |  |
| `lib/logging.py` | ✅ Coded |  |
| `lib/memory.py` | ✅ Coded |  |
| `lib/message_bus.py` | ✅ Coded |  |
| `lib/module.py` | ✅ Coded |  |
| `lib/providers.py` | ✅ Coded |  |
| `lib/security.py` | ⚠️ Empty |  |
| `lib/utils.py` | ✅ Coded |  |
| `lib/validators.py` | ⚠️ Empty |  |
| `modules/__init__.py` | ⚠️ Empty |  |
| `modules/capability_modules/__init__.py` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/__init__.py` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/analyzer.py` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/debugger.py` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/generator.py` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/logic.py` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/manifest.yaml` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/module.json` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/patterns.py` | ⚠️ Empty |  |
| `modules/capability_modules/code_assistant/refactor.py` | ⚠️ Empty |  |
| `modules/capability_modules/consciousness/__init__.py` | ⚠️ Empty |  |
| `modules/capability_modules/consciousness/important-additions-no-interference.txt` | ⚠️ Stub/Partial |  |
| `modules/capability_modules/consciousness/logic.py` | ✅ Coded |  |
| `modules/capability_modules/consciousness/manifest.yaml` | ✅ Complete |  |
| `modules/capability_modules/screen_analyzer/__init__.py` | ⚠️ Empty |  |
| `modules/capability_modules/screen_analyzer/capture.py` | ⚠️ Empty |  |
| `modules/capability_modules/screen_analyzer/change_detector.py` | ⚠️ Empty |  |
| `modules/capability_modules/screen_analyzer/logic.py` | ⚠️ Empty |  |
| `modules/capability_modules/screen_analyzer/manifest.yaml` | ⚠️ Empty |  |
| `modules/capability_modules/screen_analyzer/module.json` | ⚠️ Empty |  |
| `modules/capability_modules/screen_analyzer/ocr.py` | ⚠️ Empty |  |
| `modules/capability_modules/screen_analyzer/visual_analyzer.py` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/__init__.py` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/deployer.py` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/generator.py` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/logic.py` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/manifest.yaml` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/module.json` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/sandbox.py` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/validator.py` | ⚠️ Empty |  |
| `modules/capability_modules/self_modifier/version_control.py` | ⚠️ Empty |  |
| `modules/capability_modules/task_delegator/__init__.py` | ⚠️ Empty |  |
| `modules/capability_modules/task_delegator/logic.py` | ⚠️ Empty |  |
| `modules/capability_modules/task_delegator/manifest.yaml` | ⚠️ Empty |  |
| `modules/capability_modules/task_delegator/module.json` | ⚠️ Empty |  |
| `modules/capability_modules/task_delegator/parallel.py` | ⚠️ Empty |  |
| `modules/capability_modules/task_delegator/router.py` | ⚠️ Empty |  |
| `modules/capability_modules/task_delegator/synthesizer.py` | ⚠️ Empty |  |
| `modules/capability_modules/task_delegator/task_analyzer.py` | ⚠️ Empty |  |
| `modules/capability_modules/voice_interface/__init__.py` | ⚠️ Empty |  |
| `modules/capability_modules/voice_interface/logic.py` | ⚠️ Empty |  |
| `modules/capability_modules/voice_interface/manifest.yaml` | ⚠️ Empty |  |
| `modules/capability_modules/voice_interface/module.json` | ⚠️ Empty |  |
| `modules/capability_modules/voice_interface/stt.py` | ⚠️ Empty |  |
| `modules/capability_modules/voice_interface/tts.py` | ⚠️ Empty |  |
| `modules/capability_modules/voice_interface/voice_profiles.py` | ⚠️ Empty |  |
| `modules/capability_modules/voice_interface/wake_word.py` | ⚠️ Empty |  |
| `modules/core_modules/__init__.py` | ⚠️ Empty |  |
| `modules/core_modules/memory/__init__.py` | ⚠️ Empty |  |
| `modules/core_modules/memory/consolidation.py` | ✅ Coded |  |
| `modules/core_modules/memory/logic.py` | ✅ Coded |  |
| `modules/core_modules/memory/long_term.py` | ⚠️ Empty |  |
| `modules/core_modules/memory/manifest.yaml` | ✅ Complete |  |
| `modules/core_modules/memory/module.json` | ✅ Complete |  |
| `modules/core_modules/memory/persistent.py` | ⚠️ Empty |  |
| `modules/core_modules/memory/retrieval.py` | ⚠️ Empty |  |
| `modules/core_modules/memory/short_term.py` | ⚠️ Empty |  |
| `modules/core_modules/memory/working_memory.py` | ⚠️ Empty |  |
| `modules/core_modules/perception/__init__.py` | ⚠️ Empty |  |
| `modules/core_modules/perception/clipboard_monitor.py` | ⚠️ Empty |  |
| `modules/core_modules/perception/file_watcher.py` | ⚠️ Empty |  |
| `modules/core_modules/perception/input_processor.py` | ⚠️ Empty |  |
| `modules/core_modules/perception/logic.py` | ✅ Coded |  |
| `modules/core_modules/perception/manifest.yaml` | ✅ Complete |  |
| `modules/core_modules/perception/module.json` | ✅ Complete |  |
| `modules/core_modules/providers/__init__.py` | ⚠️ Empty |  |
| `modules/core_modules/providers/anthropic.py` | ⚠️ Empty |  |
| `modules/core_modules/providers/base_provider.py` | ⚠️ Empty |  |
| `modules/core_modules/providers/google.py` | ⚠️ Empty |  |
| `modules/core_modules/providers/litellm.py` | ⚠️ Empty |  |
| `modules/core_modules/providers/logic.py` | ✅ Coded |  |
| `modules/core_modules/providers/manifest.yaml` | ✅ Complete |  |
| `modules/core_modules/providers/module.json` | ✅ Complete |  |
| `modules/core_modules/providers/ollama.py` | ⚠️ Empty |  |
| `modules/core_modules/providers/openai.py` | ⚠️ Empty |  |
| `modules/core_modules/providers/openrouter.py` | ⚠️ Empty |  |
| `modules/core_modules/reasoning/README.md` | ⚠️ Empty |  |
| `modules/core_modules/reasoning/__init__.py` | ⚠️ Empty |  |
| `modules/core_modules/reasoning/context_builder.py` | ⚠️ Empty |  |
| `modules/core_modules/reasoning/logic.py` | ✅ Coded |  |
| `modules/core_modules/reasoning/manifest.yaml` | ✅ Complete |  |
| `modules/core_modules/reasoning/module.json` | ⚠️ Empty |  |
| `modules/core_modules/reasoning/react_engine.py` | ⚠️ Empty |  |
| `modules/core_modules/reasoning/tool_manager.py` | ⚠️ Empty |  |
| `modules/hello_world_module/__init__.py` | ⚠️ Empty |  |
| `modules/hello_world_module/logic.py` | ✅ Coded |  |
| `modules/hello_world_module/manifest.yaml` | ✅ Complete |  |
| `modules/integration_modules/__init__.py` | ⚠️ Empty |  |
| `modules/integration_modules/browser_control/__init__.py` | ⚠️ Empty |  |
| `modules/integration_modules/browser_control/logic.py` | ⚠️ Empty |  |
| `modules/integration_modules/browser_control/manifest.yaml` | ⚠️ Empty |  |
| `modules/integration_modules/browser_control/module.json` | ⚠️ Empty |  |
| `modules/integration_modules/browser_control/parser.py` | ⚠️ Empty |  |
| `modules/integration_modules/browser_control/playwright_driver.py` | ⚠️ Empty |  |
| `modules/integration_modules/browser_control/selenium_driver.py` | ⚠️ Empty |  |
| `modules/integration_modules/computer_use/__init__.py` | ⚠️ Empty |  |
| `modules/integration_modules/computer_use/executor.py` | ⚠️ Empty |  |
| `modules/integration_modules/computer_use/keyboard.py` | ⚠️ Empty |  |
| `modules/integration_modules/computer_use/logic.py` | ⚠️ Empty |  |
| `modules/integration_modules/computer_use/manifest.yaml` | ⚠️ Empty |  |
| `modules/integration_modules/computer_use/module.json` | ⚠️ Empty |  |
| `modules/integration_modules/computer_use/mouse.py` | ⚠️ Empty |  |
| `modules/integration_modules/computer_use/screenshot.py` | ⚠️ Empty |  |
| `modules/integration_modules/ide_integration/__init__.py` | ⚠️ Empty |  |
| `modules/integration_modules/ide_integration/jetbrains.py` | ⚠️ Empty |  |
| `modules/integration_modules/ide_integration/logic.py` | ⚠️ Empty |  |
| `modules/integration_modules/ide_integration/lsp_client.py` | ⚠️ Empty |  |
| `modules/integration_modules/ide_integration/manifest.yaml` | ⚠️ Empty |  |
| `modules/integration_modules/ide_integration/module.json` | ⚠️ Empty |  |
| `modules/integration_modules/ide_integration/vscode.py` | ⚠️ Empty |  |
| `modules/integration_modules/mcp_protocol/__init__.py` | ⚠️ Empty |  |
| `modules/integration_modules/mcp_protocol/client.py` | ⚠️ Empty |  |
| `modules/integration_modules/mcp_protocol/logic.py` | ⚠️ Empty |  |
| `modules/integration_modules/mcp_protocol/manifest.yaml` | ⚠️ Empty |  |
| `modules/integration_modules/mcp_protocol/module.json` | ⚠️ Empty |  |
| `modules/integration_modules/mcp_protocol/server.py` | ⚠️ Empty |  |
| `modules/integration_modules/mcp_protocol/tools.py` | ⚠️ Empty |  |
| `nucleus.py` | ✅ Coded |  |
| `registry/community/catalog.json` | ⚠️ Empty |  |
| `registry/official/catalog.json` | ⚠️ Empty |  |
| `registry/private/catalog.json` | ⚠️ Empty |  |
| `requirements.txt` | ⚠️ Stub/Partial |  |
| `scripts/backup.py` | ⚠️ Empty |  |
| `scripts/benchmark.py` | ⚠️ Empty |  |
| `scripts/dev/generate_module.py` | ⚠️ Empty |  |
| `scripts/dev/reset_db.sh` | ⚠️ Empty |  |
| `scripts/dev/test_module.py` | ⚠️ Empty |  |
| `scripts/install_module.py` | ⚠️ Empty |  |
| `scripts/migrate.py` | ⚠️ Empty |  |
| `scripts/restore.py` | ⚠️ Empty |  |
| `scripts/setup.sh` | ⚠️ Empty |  |
| `setup.py` | ⚠️ Empty |  |
| `tests/__init__.py` | ⚠️ Empty |  |
| `tests/conftest.py` | ⚠️ Empty |  |
| `tests/integration/test_full_workflow.py` | ✅ Coded |  |
| `tests/integration/test_module_loading.py` | ⚠️ Empty |  |
| `tests/integration/test_multi_module.py` | ⚠️ Empty |  |
| `tests/unit/test_memory.py` | ⚠️ Empty |  |
| `tests/unit/test_message_bus.py` | ⚠️ Empty |  |
| `tests/unit/test_module_system.py` | ⚠️ Empty |  |
| `tests/unit/test_nucleus.py` | ⚠️ Empty |  |

## 🔍 Duplicates/Conflicts (e.g., manifest.yaml in multiple modules)

- **README.md** in: `modules/core_modules/reasoning/README.md`, `README.md`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.
- **__init__.py** in: `lib/__init__.py`, `modules/__init__.py`, `modules/integration_modules/mcp_protocol/__init__.py`, `modules/integration_modules/computer_use/__init__.py`, `modules/integration_modules/__init__.py`, `modules/integration_modules/ide_integration/__init__.py`, `modules/integration_modules/browser_control/__init__.py`, `modules/capability_modules/__init__.py`, `modules/capability_modules/code_assistant/__init__.py`, `modules/capability_modules/consciousness/__init__.py`, `modules/capability_modules/task_delegator/__init__.py`, `modules/capability_modules/self_modifier/__init__.py`, `modules/capability_modules/screen_analyzer/__init__.py`, `modules/capability_modules/voice_interface/__init__.py`, `modules/hello_world_module/__init__.py`, `modules/core_modules/perception/__init__.py`, `modules/core_modules/memory/__init__.py`, `modules/core_modules/__init__.py`, `modules/core_modules/reasoning/__init__.py`, `modules/core_modules/providers/__init__.py`, `tests/__init__.py`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.
- **catalog.json** in: `registry/community/catalog.json`, `registry/private/catalog.json`, `registry/official/catalog.json`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.
- **generator.py** in: `modules/capability_modules/code_assistant/generator.py`, `modules/capability_modules/self_modifier/generator.py`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.
- **logic.py** in: `modules/integration_modules/mcp_protocol/logic.py`, `modules/integration_modules/computer_use/logic.py`, `modules/integration_modules/ide_integration/logic.py`, `modules/integration_modules/browser_control/logic.py`, `modules/capability_modules/code_assistant/logic.py`, `modules/capability_modules/consciousness/logic.py`, `modules/capability_modules/task_delegator/logic.py`, `modules/capability_modules/self_modifier/logic.py`, `modules/capability_modules/screen_analyzer/logic.py`, `modules/capability_modules/voice_interface/logic.py`, `modules/hello_world_module/logic.py`, `modules/core_modules/perception/logic.py`, `modules/core_modules/memory/logic.py`, `modules/core_modules/reasoning/logic.py`, `modules/core_modules/providers/logic.py`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.
- **manifest.yaml** in: `modules/integration_modules/mcp_protocol/manifest.yaml`, `modules/integration_modules/computer_use/manifest.yaml`, `modules/integration_modules/ide_integration/manifest.yaml`, `modules/integration_modules/browser_control/manifest.yaml`, `modules/capability_modules/code_assistant/manifest.yaml`, `modules/capability_modules/consciousness/manifest.yaml`, `modules/capability_modules/task_delegator/manifest.yaml`, `modules/capability_modules/self_modifier/manifest.yaml`, `modules/capability_modules/screen_analyzer/manifest.yaml`, `modules/capability_modules/voice_interface/manifest.yaml`, `modules/hello_world_module/manifest.yaml`, `modules/core_modules/perception/manifest.yaml`, `modules/core_modules/memory/manifest.yaml`, `modules/core_modules/reasoning/manifest.yaml`, `modules/core_modules/providers/manifest.yaml`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.
- **memory.yaml** in: `config/memory.yaml`, `config/modules/memory.yaml`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.
- **module.json** in: `modules/integration_modules/mcp_protocol/module.json`, `modules/integration_modules/computer_use/module.json`, `modules/integration_modules/ide_integration/module.json`, `modules/integration_modules/browser_control/module.json`, `modules/capability_modules/code_assistant/module.json`, `modules/capability_modules/task_delegator/module.json`, `modules/capability_modules/self_modifier/module.json`, `modules/capability_modules/screen_analyzer/module.json`, `modules/capability_modules/voice_interface/module.json`, `modules/core_modules/perception/module.json`, `modules/core_modules/memory/module.json`, `modules/core_modules/reasoning/module.json`, `modules/core_modules/providers/module.json`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.
- **providers.yaml** in: `config/providers.yaml`, `config/modules/providers.yaml`
  *Resolve:* Keep per-dir (e.g., modules/core_modules/memory/manifest.yaml vs capability_modules/...); no merge needed—unique by path.

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

*Auto-generated via Grok—refined from Project_Structure.md v1.0.*