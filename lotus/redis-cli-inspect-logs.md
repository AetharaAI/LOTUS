➜  ~ redis-cli xrevrange stream:debug.messages + - COUNT 10
 1) 1) "1761107440130-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "clipboard.changed"
       5) "data"
       6) "{\"content\": \"redis-cli xrevrange stream:debug.messages + - COUNT 10\", \"length\": 54, \"timestamp\": \"2025-10-22T00:30:40.129198\", \"context\": {\"active_file\": null, \"active_directory\": null, \"recent_files\": [], \"working_on\": \"coding\", \"last_activity\": \"2025-10-22T00:30:40.129182\"}}"
       7) "ts"
       8) "2025-10-22T04:30:40.130133"
 2) 1) "1761107404296-0"
    2) 1) "direction"
       2) "recv"
       3) "channel"
       4) "perception.user_input"
       5) "data"
       6) "{\"text\": \"hi\", \"context\": {\"source\": \"cli\"}}"
       7) "ts"
       8) "2025-10-22T04:30:04.295016"
 3) 1) "1761107404295-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "perception.user_input"
       5) "data"
       6) "{\"text\": \"hi\", \"context\": {\"source\": \"cli\"}}"
       7) "ts"
       8) "2025-10-22T04:30:04.295016"
 4) 1) "1761107358702-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "clipboard.changed"
       5) "data"
       6) "{\"content\": \"./venv/bin/python3 nucleus.py\\n# In a separate terminal (or background), publish a test prompt:\\ncd /home/cory/Desktop/Lotus/lotus\\n./venv/bin/python3 - <<'PY'\\nimport asyncio, sys, os\\nsys.path.insert(0, os.getcwd())\\nfrom lib.message_bus import MessageBus\\nasync def main():\\n    bus = MessageBus()\\n    await bus.connect()\\n    await bus.publish('perception.user_input', {\\\"text\\\": \\\"audit stream smoke test\\\", \\\"context\\\": {}})\\n    await asyncio.sleep(0.5)\\n    await bus.disconnect()\\nasyncio.run(main())\\nPY\\n# Inspect streams:\\nredis-cli xrevrange stream:debug.messages + - COUNT 10\\nredis-cli xrevrange stream:action.respond + - COUNT 10\\n# Tail the nucleus log:\\ntail -n 200 /home/cory/Desktop/Lotus/data/logs/nucleus.log\", \"length\": 706, \"timestamp\": \"2025-10-22T00:29:18.701908\", \"context\": {\"active_file\": null, \"active_directory\": null, \"recent_files\": [], \"working_on\": \"coding\", \"last_activity\": \"2025-10-22T00:29:18.701897\"}}"
       7) "ts"
       8) "2025-10-22T04:29:18.702465"
 5) 1) "1761107330541-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "clipboard.changed"
       5) "data"
       6) "{\"content\": \"cd /home/cory/Desktop/Lotus/lotus\\n# start nucleus in foreground (keeps it attached to terminal)\\n./venv/bin/python3 nucleus.py\\n# In a separate terminal (or background), publish a test prompt:\\ncd /home/cory/Desktop/Lotus/lotus\\n./venv/bin/python3 - <<'PY'\\nimport asyncio, sys, os\\nsys.path.insert(0, os.getcwd())\\nfrom lib.message_bus import MessageBus\\nasync def main():\\n    bus = MessageBus()\\n    await bus.connect()\\n    await bus.publish('perception.user_input', {\\\"text\\\": \\\"audit stream smoke test\\\", \\\"context\\\": {}})\\n    await asyncio.sleep(0.5)\\n    await bus.disconnect()\\nasyncio.run(main())\\nPY\\n# Inspect streams:\\nredis-cli xrevrange stream:debug.messages + - COUNT 10\\nredis-cli xrevrange stream:action.respond + - COUNT 10\\n# Tail the nucleus log:\\ntail -n 200 /home/cory/Desktop/Lotus/data/logs/nucleus.log\", \"length\": 802, \"timestamp\": \"2025-10-22T00:28:50.540416\", \"context\": {\"active_file\": null, \"active_directory\": null, \"recent_files\": [], \"working_on\": \"coding\", \"last_activity\": \"2025-10-22T00:28:50.540402\"}}"
       7) "ts"
       8) "2025-10-22T04:28:50.541040"
 6) 1) "1761107283242-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "system.ready"
       5) "data"
       6) "{\"timestamp\": \"2025-10-22T00:28:03.241794\", \"modules_loaded\": 4, \"personality\": \"ash\"}"
       7) "ts"
       8) "2025-10-22T04:28:03.242206"
 7) 1) "1761107283241-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "system.module.ready"
       5) "data"
       6) "{\"module\": \"providers\", \"version\": \"1.0.0\", \"type\": \"core\"}"
       7) "ts"
       8) "2025-10-22T04:28:03.240937"
 8) 1) "1761107281807-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "system.module.ready"
       5) "data"
       6) "{\"module\": \"reasoning\", \"version\": \"1.0.0\", \"type\": \"core\"}"
       7) "ts"
       8) "2025-10-22T04:28:01.807382"
 9) 1) "1761107281801-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "system.module.ready"
       5) "data"
       6) "{\"module\": \"memory\", \"version\": \"1.0.0\", \"type\": \"core\"}"
       7) "ts"
       8) "2025-10-22T04:28:01.801239"
10) 1) "1761107281795-0"
    2) 1) "direction"
       2) "publish"
       3) "channel"
       4) "clipboard.changed"
       5) "data"
       6) "{\"content\": \"### Issue: Unbounded Audit Stream Growth\\n**Why:** `stream:debug.messages` xadd lacks `maxlen`, fills Redis mem over repeated publishes (vectors in data bloat it). Ties to reboot need.\\n\\n**Fix in publish() after channel xadd:**\\n```python\\n# Audit entry\\ntry:\\n    await self.redis.xadd(\\\"stream:debug.messages\\\", {\\\"direction\\\": \\\"publish\\\", \\\"channel\\\": channel, \\\"data\\\": json.dumps(data), \\\"ts\\\": datetime.utcnow().isoformat()}, maxlen=5000)\\nexcept Exception:\\n    pass\\n```\\n\\n### Issue: Payload Refs in Handler Loop\\n**Why:** json.loads(payload) holds refs; repeated async calls without del leak in loop, esp. large perception data.\\n\\n**Wrap in _message_handler() after \\\"if message...\\\":**\\n```python\\nif message and message[\\\"type\\\"] in [\\\"message\\\", \\\"pmessage\\\"]:\\n    payload = None\\n    try:\\n        # Deserialize...\\n        data = json.loads(message[\\\"data\\\"])\\n        channel = data[\\\"channel\\\"]\\n        payload = data[\\\"data\\\"]\\n        # ... rest of handler\\n    except Exception:\\n        # Fallback...\\n    finally:\\n        del \", \"length\": 1869, \"timestamp\": \"2025-10-22T00:28:01.794389\", \"context\": {\"active_file\": null, \"active_directory\": null, \"recent_files\": [], \"working_on\": null, \"last_activity\": \"2025-10-22T00:28:01.794370\"}}"
       7) "ts"
       8) "2025-10-22T04:28:01.795236"
➜  ~ 

{"timestamp": "2025-10-22T04:27:53.447643", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Configuration loaded", "module": "nucleus", "function": "boot", "line": 93}
{"timestamp": "2025-10-22T04:27:53.558938", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Redis message bus connected", "module": "nucleus", "function": "_init_infrastructure", "line": 162}
{"timestamp": "2025-10-22T04:27:53.613528", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "PostgreSQL connected", "module": "nucleus", "function": "_init_infrastructure", "line": 180}
{"timestamp": "2025-10-22T04:27:53.613619", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "ChromaDB initialization skipped (config) ", "module": "nucleus", "function": "_init_infrastructure", "line": 211}
{"timestamp": "2025-10-22T04:27:53.613770", "level": "DEBUG", "logger": "lotus", "message": "Discovered module: perception at /home/cory/Desktop/Lotus/lotus/modules/core_modules/perception", "module": "nucleus", "function": "_discover_modules", "line": 252}
{"timestamp": "2025-10-22T04:27:53.613828", "level": "DEBUG", "logger": "lotus", "message": "Discovered module: memory at /home/cory/Desktop/Lotus/lotus/modules/core_modules/memory", "module": "nucleus", "function": "_discover_modules", "line": 252}
{"timestamp": "2025-10-22T04:27:53.613876", "level": "DEBUG", "logger": "lotus", "message": "Discovered module: reasoning at /home/cory/Desktop/Lotus/lotus/modules/core_modules/reasoning", "module": "nucleus", "function": "_discover_modules", "line": 252}
{"timestamp": "2025-10-22T04:27:53.613916", "level": "DEBUG", "logger": "lotus", "message": "Discovered module: providers at /home/cory/Desktop/Lotus/lotus/modules/core_modules/providers", "module": "nucleus", "function": "_discover_modules", "line": 252}
{"timestamp": "2025-10-22T04:27:53.613986", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Discovered 4 modules", "module": "nucleus", "function": "boot", "line": 102}
{"timestamp": "2025-10-22T04:27:53.635610", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Initializing perception system", "module": "logic", "function": "initialize", "line": 90}
{"timestamp": "2025-10-22T04:27:53.635679", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Perception system initialized", "module": "logic", "function": "initialize", "line": 131}
{"timestamp": "2025-10-22T04:27:53.635953", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=system.module.ready source=perception data_type=<class 'dict'> keys=['module', 'version', 'type']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:27:53.637143", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Module loaded: perception", "module": "nucleus", "function": "boot", "line": 115}
{"timestamp": "2025-10-22T04:27:56.402194", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Initializing 4-tier memory system", "module": "logic", "function": "initialize", "line": 35}
{"timestamp": "2025-10-22T04:28:01.794461", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=clipboard.changed source=perception data_type=<class 'dict'> keys=['content', 'length', 'timestamp', 'context']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:28:01.795454", "level": "DEBUG", "logger": "lotus", "message": "Clipboard changed (1869 chars)", "module": "logic", "function": "monitor_clipboard", "line": 273}
{"timestamp": "2025-10-22T04:28:01.796635", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Memory system initialized successfully", "module": "logic", "function": "initialize", "line": 162}
{"timestamp": "2025-10-22T04:28:01.800608", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=system.module.ready source=memory data_type=<class 'dict'> keys=['module', 'version', 'type']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:28:01.801415", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Registered memory service in config", "module": "nucleus", "function": "_load_module", "line": 420}
{"timestamp": "2025-10-22T04:28:01.801499", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Module loaded: memory", "module": "nucleus", "function": "boot", "line": 115}
{"timestamp": "2025-10-22T04:28:01.806520", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Reasoning engine initializing...", "module": "logic", "function": "initialize", "line": 79}
{"timestamp": "2025-10-22T04:28:01.806599", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Reasoning engine ready", "module": "logic", "function": "initialize", "line": 101}
{"timestamp": "2025-10-22T04:28:01.806837", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=system.module.ready source=reasoning data_type=<class 'dict'> keys=['module', 'version', 'type']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:28:01.807520", "level": "DEBUG", "logger": "lotus", "message": "Module reasoning skipped duplicate subscription for perception.user_input -> on_user_input", "module": "nucleus", "function": "_load_module", "line": 461}
{"timestamp": "2025-10-22T04:28:01.807557", "level": "DEBUG", "logger": "lotus", "message": "Module reasoning skipped duplicate subscription for perception.voice_input -> on_voice_input", "module": "nucleus", "function": "_load_module", "line": 461}
{"timestamp": "2025-10-22T04:28:01.807580", "level": "DEBUG", "logger": "lotus", "message": "Module reasoning skipped duplicate subscription for action.tool_result -> on_tool_result", "module": "nucleus", "function": "_load_module", "line": 461}
{"timestamp": "2025-10-22T04:28:01.807632", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Module loaded: reasoning", "module": "nucleus", "function": "boot", "line": 115}
{"timestamp": "2025-10-22T04:28:03.174698", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Initializing LLM provider system", "module": "logic", "function": "initialize", "line": 67}
{"timestamp": "2025-10-22T04:28:03.195629", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Initialized Anthropic provider", "module": "logic", "function": "initialize", "line": 77}
{"timestamp": "2025-10-22T04:28:03.215609", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Initialized OpenAI provider", "module": "logic", "function": "initialize", "line": 84}
{"timestamp": "2025-10-22T04:28:03.235222", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Initialized Ollama provider", "module": "logic", "function": "initialize", "line": 98}
{"timestamp": "2025-10-22T04:28:03.235306", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Provider system initialized with 3 providers", "module": "logic", "function": "initialize", "line": 119}
{"timestamp": "2025-10-22T04:28:03.235520", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=system.module.ready source=providers data_type=<class 'dict'> keys=['module', 'version', 'type']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:28:03.241396", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Registered llm/providers service in config", "module": "nucleus", "function": "_load_module", "line": 424}
{"timestamp": "2025-10-22T04:28:03.241543", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "Module loaded: providers", "module": "nucleus", "function": "boot", "line": 115}
{"timestamp": "2025-10-22T04:28:50.540484", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=clipboard.changed source=perception data_type=<class 'dict'> keys=['content', 'length', 'timestamp', 'context']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:28:50.541198", "level": "DEBUG", "logger": "lotus", "message": "Clipboard changed (802 chars)", "module": "logic", "function": "monitor_clipboard", "line": 273}
{"timestamp": "2025-10-22T04:29:18.701968", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=clipboard.changed source=perception data_type=<class 'dict'> keys=['content', 'length', 'timestamp', 'context']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:29:18.702627", "level": "DEBUG", "logger": "lotus", "message": "Clipboard changed (706 chars)", "module": "logic", "function": "monitor_clipboard", "line": 273}
{"timestamp": "2025-10-22T04:30:04.295131", "level": "DEBUG", "logger": "lotus", "message": "[event] reasoning handling perception.user_input -> on_user_input | data_keys=['text', 'context']", "module": "module", "function": "_handle_event", "line": 139}
{"timestamp": "2025-10-22T04:30:04.295264", "level": "\u001b[32mINFO\u001b[0m", "logger": "lotus", "message": "User input received: hi... | memory=MemoryModule llm=ProviderModule", "module": "logic", "function": "on_user_input", "line": 127}
{"timestamp": "2025-10-22T04:30:04.295322", "level": "DEBUG", "logger": "lotus", "message": "[debug] memory methods: search=True recall=True retrieve=False", "module": "logic", "function": "on_user_input", "line": 139}
{"timestamp": "2025-10-22T04:30:40.129280", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=clipboard.changed source=perception data_type=<class 'dict'> keys=['content', 'length', 'timestamp', 'context']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:30:40.130470", "level": "DEBUG", "logger": "lotus", "message": "Clipboard changed (54 chars)", "module": "logic", "function": "monitor_clipboard", "line": 273}
{"timestamp": "2025-10-22T04:31:06.241244", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=clipboard.changed source=perception data_type=<class 'dict'> keys=['content', 'length', 'timestamp', 'context']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:31:06.242504", "level": "DEBUG", "logger": "lotus", "message": "Clipboard changed (6303 chars)", "module": "logic", "function": "monitor_clipboard", "line": 273}
{"timestamp": "2025-10-22T04:32:03.484692", "level": "DEBUG", "logger": "lotus", "message": "[publish] channel=clipboard.changed source=perception data_type=<class 'dict'> keys=['content', 'length', 'timestamp', 'context']", "module": "module", "function": "publish", "line": 160}
{"timestamp": "2025-10-22T04:32:03.485372", "level": "DEBUG", "logger": "lotus", "message": "Clipboard changed (54 chars)", "module": "logic", "function": "monitor_clipboard", "line": 273}
