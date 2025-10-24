
# cli.py
from __future__ import annotations # Must be the very first line

# Debug prints must come after __future__ import
print("CLI: Starting CLI module execution...")

import threading
import traceback
import shlex
from datetime import datetime
import asyncio
import logging
from typing import Optional, Any, Coroutine, TYPE_CHECKING, List, Dict, Callable
from rich.table import Table
from rich.console import Console # Moved import to top
import json
import time
import uuid
import sys
from pathlib import Path # Moved import to top

print("CLI: Basic imports completed")

# --- Kernel Component Imports ---
print("CLI: About to check TYPE_CHECKING and import kernel components")

if TYPE_CHECKING:
    print("CLI: TYPE_CHECKING is True, importing kernel components for type hints")
    from PresenceOS_kernel import (
        SystemState, ModuleState, EventType, Event, Priority,
        PresenceKernel, KernelAPI, ModuleInterface
    )
    PromptInterfaceModule = Any # Forward declaration for PromptInterfaceModule
else:
    print("CLI: TYPE_CHECKING is False, skipping type hint imports")

# Simplified import logic - always start with dummy classes
# Real components will be imported dynamically in the constructor
KERNEL_COMPONENTS_AVAILABLE = False
print("CLI: Set KERNEL_COMPONENTS_AVAILABLE to False")

class KernelAPI:
    def get_config_dir(self) -> str: return "."
class PresenceKernel: pass
class Priority:
    NORMAL = None
    HIGH = None
    CRITICAL = None
    LOW = None
    BACKGROUND = None
class SystemState: pass
class ModuleState: pass
class EventType: pass
class Event: pass
class ModuleInterface: pass
PromptInterfaceModule = Any
# --- End Kernel Component Imports ---

print("CLI: About to define AsyncCommandLineInterface class")

class AsyncCommandLineInterface:
    print("CLI: AsyncCommandLineInterface class definition started")
    def __init__(self, api: 'KernelAPI', kernel_event_loop: asyncio.AbstractEventLoop):
        # Try to import kernel components dynamically if not already available
        global KERNEL_COMPONENTS_AVAILABLE
        if not KERNEL_COMPONENTS_AVAILABLE:
            print("CLI constructor: Attempting to import kernel components dynamically...")
            try:
                # Import kernel components dynamically
                from PresenceOS_kernel import (
                    SystemState, ModuleState, EventType, Event, Priority,
                    PresenceKernel, KernelAPI as RealKernelAPI, ModuleInterface
                )
                # Update global variables with real implementations
                globals()['SystemState'] = SystemState
                globals()['ModuleState'] = ModuleState
                globals()['EventType'] = EventType
                globals()['Event'] = Event
                globals()['Priority'] = Priority
                globals()['PresenceKernel'] = PresenceKernel
                globals()['KernelAPI'] = RealKernelAPI
                globals()['ModuleInterface'] = ModuleInterface
                globals()['KERNEL_COMPONENTS_AVAILABLE'] = True
                print("CLI constructor: Successfully imported kernel components dynamically")
            except ImportError as e:
                print(f"CLI constructor: Failed to import kernel components dynamically: {e}")
                import traceback
                traceback.print_exc()
                KERNEL_COMPONENTS_AVAILABLE = False
            except Exception as e:
                print(f"CLI constructor: Unexpected error importing kernel components: {e}")
                import traceback
                traceback.print_exc()
                KERNEL_COMPONENTS_AVAILABLE = False


        self.api: KernelAPI = api
        self.logger = logging.getLogger("Kernel").getChild('cli') if KERNEL_COMPONENTS_AVAILABLE else logging.getLogger("DummyCLI")
        self.console = Console() # Initialize Rich Console

        if KERNEL_COMPONENTS_AVAILABLE:
            if not isinstance(api, KernelAPI): # type: ignore
                self.logger.critical(f"CLI received incorrect API type. Expected KernelAPI, got {type(api)}")
                raise TypeError(f"AsyncCommandLineInterface expected KernelAPI, got {type(api)}")
            if not isinstance(kernel_event_loop, asyncio.AbstractEventLoop):
                self.logger.critical(f"CLI received incorrect event loop type. Expected AbstractEventLoop, got {type(kernel_event_loop)}")
                raise TypeError("AsyncCommandLineInterface expected AbstractEventLoop for kernel_event_loop")
        else:
            self.logger.critical("CLI initialized without actual KernelAPI. It will not function correctly.")

        self._running = False
        self._thread_lock = threading.Lock()
        self._kernel_loop: Optional[asyncio.AbstractEventLoop] = kernel_event_loop

        if self._kernel_loop:
            self.logger.info(f"CLI initialized with kernel event loop: {self._kernel_loop}")
        else:
            self.logger.error("CLI initialized but kernel event loop was None! Async operations will fail.")

        self.commands: Dict[str, Callable[[List[str]], None]] = {
            'help': self.cmd_help, 'exit': self.cmd_exit, 'quit': self.cmd_exit,
            'shutdown': self.cmd_shutdown, 'status': self.cmd_status,
            'modules': self.cmd_list_modules, 'list_modules': self.cmd_list_modules, # Alias
            'modinfo': self.cmd_module_info, 'module_info': self.cmd_module_info, # Alias
            'load': self.cmd_load_module, 'load_module': self.cmd_load_module, # Alias
            'unload': self.cmd_unload_module, 'unload_module': self.cmd_unload_module, # Alias
            'reload': self.cmd_reload_module, 'restart': self.cmd_restart,
            'config': self.cmd_config, 'events': self.cmd_events,
            'health': self.cmd_health, 'publish': self.cmd_publish_event,
            'ask': self.cmd_ask, 'session': self.cmd_session,
            'registry': self.cmd_registry, 'send_mesh_signal': self.cmd_send_mesh_signal,
            'send_external_command': self.cmd_send_external_command, 'scaffold_agent': self.cmd_scaffold_agent,
            # Combined Intelligence Commands
            'collective': self.cmd_collective, 'intelligence': self.cmd_intelligence,
            'orchestrate': self.cmd_orchestrate, 'semantic': self.cmd_semantic,
            'agents': self.cmd_agents
        }
        self.prompt = "PresenceOS> "
        self.current_session_id: Optional[str] = None

        self.system_registry: Optional[Dict[str, Any]] = None
        if KERNEL_COMPONENTS_AVAILABLE and hasattr(self.api, 'get_config_dir'):  # Check if api has method
            try:
                registry_path = Path(self.api.get_config_dir()) / "system" / "system_registry.json"
                if registry_path.is_file():
                    with open(registry_path, 'r') as f:
                        self.system_registry = json.load(f)
                    self.logger.info(f"CLI: System registry loaded from {registry_path}")
                else:
                    self.logger.warning(f"CLI: System registry file not found at {registry_path}. 'registry' command will be limited.")
            except Exception as e:
                self.logger.error(f"CLI: Failed to load system registry: {e}")
        elif not KERNEL_COMPONENTS_AVAILABLE:
            self.logger.warning("CLI: KernelAPI not available, cannot load system registry.")


    def _ensure_kernel_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        # ... (this method seems fine) ...
        if not KERNEL_COMPONENTS_AVAILABLE:
            self.logger.error("CLI: Cannot ensure kernel loop: Kernel components unavailable.")
            return None
        if self._kernel_loop is None:
            self.logger.error("CLI: _kernel_loop is None.")
            return None
        if not self._kernel_loop.is_running():
            self.logger.error(f"CLI: Provided kernel event loop ({self._kernel_loop}) is reported as not running.")
            return None
        return self._kernel_loop

    def _run_async(self, coro: Coroutine[Any, Any, Any]) -> Any:
        # ... (this method seems fine for scheduling a single top-level coroutine) ...
        if not KERNEL_COMPONENTS_AVAILABLE:
            self.console.print("[bold red]Error: Cannot execute async command; kernel components not loaded.[/]")
            self.logger.error("CLI: _run_async called without kernel components.")
            return None
        loop = self._ensure_kernel_loop()
        if not loop:
              self.console.print("[bold red]Error: Kernel event loop unavailable or not running for async operation.[/]")
              self.logger.error("CLI: _run_async cannot proceed, kernel loop invalid or not running.")
              return None
        if not asyncio.iscoroutine(coro):
            self.logger.error(f"CLI: _run_async called with non-coroutine: {type(coro)}")
            self.console.print(f"[bold red]Internal Error: Attempted to run non-async function '{getattr(coro, '__name__', 'unknown')}' asynchronously.[/]")
            return None
        try:
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=60)
        except asyncio.TimeoutError:
              self.console.print("[bold red]Error: Async operation timed out.[/]")
              self.logger.warning(f"Async operation from CLI timed out.")
              return None
        except RuntimeError as e:
            if "cannot schedule new futures after shutdown" in str(e) or "Event loop is closed" in str(e):
                self.console.print("[bold red]Error: Kernel event loop is shutting down or closed. Cannot schedule async operation.[/]")
                self.logger.warning(f"Async op failed as event loop is stopping/closed: {e}")
            else:
                self.console.print(f"[bold red]Error during async operation: {e}[/]")
                self.logger.error(f"RuntimeError in _run_async: {e}", exc_info=True)
            return None
        except Exception as e:
              self.console.print(f"[bold red]Error during async operation: {e}[/]")
              self.logger.error(f"Exception in _run_async: {e}", exc_info=True)
              return None

    def start(self):
        print(f"CLI start: KERNEL_COMPONENTS_AVAILABLE = {KERNEL_COMPONENTS_AVAILABLE}")
        print(f"CLI start: _kernel_loop = {self._kernel_loop}")
        print(f"CLI start: _kernel_loop.is_running() = {self._kernel_loop.is_running() if self._kernel_loop else 'N/A'}")
        print(f"CLI start: self.logger = {self.logger}")

        if not KERNEL_COMPONENTS_AVAILABLE:
            print("CLI start: KERNEL_COMPONENTS_AVAILABLE is False, cannot start CLI")
            self.logger.critical("CLI cannot start: Kernel components failed to import.")
            self.console.print("[bold red]CRITICAL: PresenceOS CLI cannot start due to missing kernel components.[/]")
            return

        print("CLI start: KERNEL_COMPONENTS_AVAILABLE is True, proceeding with CLI start")
        with self._thread_lock:
            if self._running:
                self.logger.warning("CLI: Start requested, but already running.")
                return
            self._running = True
        self.logger.info("CLI: Thread started")
        self._print_welcome()
        if KERNEL_COMPONENTS_AVAILABLE and self._kernel_loop and self._kernel_loop.is_running():
            try:
                async def get_initial_session_id():
                    pim_instance = await self._get_prompt_interface_module_instance()
                    if pim_instance and hasattr(pim_instance, 'current_session_id'):
                        self.current_session_id = getattr(pim_instance, 'current_session_id')
                        self.logger.info(f"CLI: Initialized current_session_id to '{self.current_session_id}' from PromptInterface.")
                asyncio.run_coroutine_threadsafe(get_initial_session_id(), self._kernel_loop)
            except Exception as e_init_sess:
                self.logger.warning(f"CLI: Could not get initial session ID from PromptInterface: {e_init_sess}")

        print("CLI start: Entering main command loop")
        while self._running:
            try:
                cmd_line_str = input(self.prompt)
                if not self._running: break
                cmd_line_str = cmd_line_str.strip()
                if not cmd_line_str: continue

                parts = shlex.split(cmd_line_str)
                cmd, args_list = parts[0].lower(), parts[1:]
                if cmd in self.commands:
                    self.commands[cmd](args_list)
                else:
                    self.console.print(f"Unknown command: '{cmd}'. Type 'help'.")
            except KeyboardInterrupt: self.console.print("\nUse 'exit' or 'shutdown'.")
            except EOFError: self.cmd_exit([]); break
            except Exception as e:
                cmd_str_local = locals().get('cmd_line_str', 'N/A_CMD_LINE')
                self.logger.error(f"CLI: Error processing command '{cmd_str_local}': {e}", exc_info=True)
                self.console.print(f"[bold red]Unexpected error: {e}[/]")


    def stop(self):
        # ... (this method seems fine) ...
        with self._thread_lock:
            if self._running: self.logger.info("CLI: Stopping..."); self._running = False
            else: self.logger.info("CLI: Already stopped.")

    def _print_welcome(self):
        # ... (this method seems fine) ...
        self.console.print("\n" + "="*60 + "\n   PresenceOS Async Command Line Interface\n" + "="*60)
        self.console.print("Type 'help'. 'exit'/'quit' to exit CLI. 'shutdown' for kernel.")
        self.console.print("New commands: 'ask \"your prompt\"' and 'session <new [id]|id|history|clear_history|summarize [session_id]>'. Type 'registry' for more.")


    def cmd_help(self, args: List[str]):
        """Shows available commands or help for a specific command. Usage: help [command]"""
        # ... (updated help text for session and registry) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI functionality limited: Kernel components unavailable.[/]");
        if args and args[0] in self.commands:
            doc = self.commands[args[0]].__doc__ or "No documentation for this command."
            self.console.print(f"\nHelp for '{args[0]}':\n  {doc.strip()}")
            if args[0] == 'session':
                self.console.print("  Session subcommands: new [id], id, history, clear_history, summarize [session_id]")
            elif args[0] == 'registry':
                self.console.print("  Registry subcommands: agents, agent <id>, events, event <type>")
            elif args[0] == 'collective':
                self.console.print("  Collective subcommands: status, insights [count], patterns, resonance")
            elif args[0] == 'orchestrate':
                self.console.print("  Orchestrate subcommands: status, config <key> <value>, agents <list>, merge <strategy>")
            elif args[0] == 'semantic':
                self.console.print("  Semantic subcommands: status, intents, routes, knowledge")
            elif args[0] == 'intelligence':
                self.console.print("  Intelligence subcommands: query \"prompt\", debate \"topic\", compare <req_id>, optimize")
            elif args[0] == 'agents':
                self.console.print("  Agents subcommands: performance, capabilities, combinations, sync")
            return
        self.console.print("\nAvailable commands:")
        self.console.print("\n[bold cyan]System Management:[/]")
        system_cmds = ['help', 'exit', 'shutdown', 'status', 'health', 'modules', 'modinfo', 'load', 'unload', 'reload', 'config', 'events', 'publish']
        for cmd in sorted(system_cmds):
            if cmd in self.commands:
                docstring_first_line = (self.commands[cmd].__doc__ or '').splitlines()[0].strip()
                self.console.print(f"  {cmd:<20} - {docstring_first_line}")

        self.console.print("\n[bold green]Session & Communication:[/]")
        session_cmds = ['ask', 'session', 'registry', 'send_mesh_signal', 'send_external_command', 'scaffold_agent']
        for cmd in sorted(session_cmds):
            if cmd in self.commands:
                docstring_first_line = (self.commands[cmd].__doc__ or '').splitlines()[0].strip()
                self.console.print(f"  {cmd:<20} - {docstring_first_line}")

        self.console.print("\n[bold magenta]Combined Intelligence:[/]")
        intelligence_cmds = ['collective', 'orchestrate', 'semantic', 'intelligence', 'agents']
        for cmd in sorted(intelligence_cmds):
            if cmd in self.commands:
                docstring_first_line = (self.commands[cmd].__doc__ or '').splitlines()[0].strip()
                self.console.print(f"  {cmd:<20} - {docstring_first_line}")

        self.console.print("\nFor detailed help on subcommands, type: help <command_name>")
        self.console.print("For combined intelligence features, see: help collective, help orchestrate, help semantic, help intelligence, help agents")


    def cmd_exit(self, args: List[str]):
        """Exits the CLI. The PresenceOS kernel continues running."""
        # ... (this method seems fine) ...
        self.console.print("Exiting CLI. Kernel continues running.")
        self.stop()

    def cmd_shutdown(self, args: List[str]):
        """Requests a shutdown of the PresenceOS kernel and exits the CLI."""
        # ... (this method seems fine) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        self.console.print("Requesting kernel shutdown...")
        self._run_async(self.api.shutdown_kernel())
        self.console.print("Kernel shutdown initiated.")
        self.stop()

    def cmd_status(self, args: List[str]):
        """Displays the current status of the PresenceOS kernel and modules."""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        self.console.print("\n--- Kernel Status ---")
        try:
            health = self.api.get_system_health()
            if not health: self.console.print("Could not retrieve health status."); return

            metrics = health.get("system_metrics", {})
            uptime_sec = metrics.get('uptime_seconds', -1)
            if uptime_sec >= 0:
                d, rem = divmod(uptime_sec, 86400); h, rem = divmod(rem, 3600); m, s = divmod(rem, 60)
                self.console.print(f"Uptime: {int(d)}d {int(h):02}:{int(m):02}:{int(s):02}")
            else: self.console.print("Uptime: N/A")

            # ... (rest of status output using self.console.print) ...
            cpu = metrics.get('cpu_usage_percent', -1.0)
            mem = metrics.get('memory_usage_mb', -1.0)
            threads = metrics.get('threads_active', -1)
            event_rate = metrics.get('event_rate_per_sec', -1.0)
            self.console.print(f"CPU Usage: {cpu:.2f}%" if cpu != -1.0 else "CPU Usage: N/A")
            self.console.print(f"Memory Usage: {mem:.2f} MB" if mem != -1.0 else "Memory Usage: N/A")
            self.console.print(f"Active Threads: {threads}" if threads != -1 else "Active Threads: N/A")
            self.console.print(f"Event Rate: {event_rate:.2f} events/sec" if event_rate != -1.0 else "Event Rate: N/A")

            modules = self.api.get_all_modules()
            module_count = len(modules)
            states: dict[str, int] = {}
            for mod_dict in modules:
                  state = mod_dict.get('state', 'UNKNOWN')
                  states[state] = states.get(state, 0) + 1

            self.console.print("\n--- Module Summary ---")
            self.console.print(f"Total Modules Registered: {module_count}")
            if states:
                for state_name, count_val in sorted(states.items()): self.console.print(f"  - {state_name}: {count_val}")
            else: self.console.print("  No modules registered.")

        except Exception as e: self.console.print(f"[bold red]Error retrieving status: {e}[/]"); self.logger.error("cmd_status error", exc_info=True)


    def cmd_list_modules(self, args: List[str]):
        """Lists all registered modules with their ID, Name, Version, State, and Priority."""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        self.console.print("\n--- Registered Modules ---")
        try:
            modules = self.api.get_all_modules()
            if not modules: self.console.print("No modules registered."); return

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan", width=25)
            table.add_column("Name", style="green", width=30)
            table.add_column("Version", style="blue", width=10)
            table.add_column("State", style="yellow", width=12)
            table.add_column("Priority", style="dim", width=10)

            for m_dict in modules:
                  table.add_row(
                      m_dict.get('id','?'),
                      m_dict.get('name','?'),
                      m_dict.get('version','?'),
                      m_dict.get('state','?'),
                      m_dict.get('startup_priority','?')
                  )
            self.console.print(table)
        except Exception as e: self.console.print(f"[bold red]Error listing modules: {e}[/]"); self.logger.error("cmd_list_modules error", exc_info=True)


    def cmd_module_info(self, args: List[str]):
        """Displays detailed information for a specific module. Usage: module_info <module_id>"""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        if not args: self.console.print("Usage: module_info <module_id>"); return
        module_id = args[0]
        self.console.print(f"\n--- Module Details: {module_id} ---")
        try:
            mod_info = self.api.get_module_info(module_id)
            if not mod_info: self.console.print(f"Module '{module_id}' not found."); return
            for k, v_item in mod_info.items():
                display_val = v_item
                if k == 'dependencies' and isinstance(v_item, list): display_val = ', '.join(v_item) if v_item else 'None'
                elif isinstance(v_item, (dict, list)): display_val = json.dumps(v_item, indent=2)
                self.console.print(f"  {k.replace('_', ' ').title():<20}: {display_val}")
        except Exception as e: self.console.print(f"[bold red]Error getting module info: {e}[/]"); self.logger.error("cmd_module_info error", exc_info=True)


    def cmd_load_module(self, args: List[str]):
        """Loads (and initializes/starts) a module. Usage: load <module_id>"""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        if not args: self.console.print("Usage: load <module_id>"); return
        module_id = args[0]; self.console.print(f"Attempting to load module '{module_id}'...")
        res = self._run_async(self.api.load_module(module_id))
        self.console.print(f"Load request for '{module_id}' {'sent successfully.' if res else 'failed or timed out.'} Result: {res}")

    def cmd_unload_module(self, args: List[str]):
        """Unloads a module. Usage: unload <module_id> [force]"""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        if not args: self.console.print("Usage: unload <module_id> [force]"); return
        module_id, force = args[0], len(args) > 1 and args[1].lower() == 'force'
        self.console.print(f"Attempting to unload module '{module_id}' (force={force})...")
        res = self._run_async(self.api.unload_module(module_id, force=force))
        self.console.print(f"Unload request for '{module_id}' {'sent successfully.' if res else 'failed or timed out.'} Result: {res}")


    def cmd_reload_module(self, args: List[str]):
        """Reloads (unloads, then loads) a module. Usage: reload <module_id> [force]"""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        if not args: self.console.print("Usage: reload <module_id> [force]"); return
        module_id, force = args[0], len(args) > 1 and args[1].lower() == 'force'
        self.console.print(f"Attempting to reload module '{module_id}' (force={force})...")
        res = self._run_async(self.api.reload_module(module_id, force_unload=force))
        self.console.print(f"Reload request for '{module_id}' {'sent successfully.' if res else 'failed or timed out.'} Result: {res}")

    def cmd_restart(self, args: List[str]):
        """Restarts the entire PresenceOS kernel (Experimental)."""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        self.console.print("Requesting kernel restart (Experimental)...")
        try:
            if input("Are you sure? (yes/no): ").lower() == 'yes':
                self._run_async(self.api.restart_kernel())
                self.console.print("Kernel restart initiated. CLI will likely disconnect.")
                self.stop()
            else: self.console.print("Restart cancelled.")
        except EOFError: self.console.print("\nInput closed, cancelling restart."); self.stop()


    def cmd_config(self, args: List[str]):
        """Views or sets system or module configurations.
        Usage: config system view
               config system set <key> <json_value>
               config module <module_id> view
               config module <module_id> set <key> <json_value>"""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        doc = self.commands['config'].__doc__ or "Config command usage: config <system|module> <view|set> ..."
        if not args or args[0].lower() not in ['system','module'] or \
           (len(args) > 1 and args[1].lower() not in ['view','set']):
            self.console.print(doc); return

        cfg_type, action_or_mod_id = args[0].lower(), args[1]
        try:
            if cfg_type == 'system':
                action = action_or_mod_id.lower()
                if action == 'view':
                    if len(args)!=2: self.console.print(doc); return
                    data = self.api.get_system_config()
                    self.console.print("\n--- System Configuration ---"); [self.console.print(f"  {k:<25}: {json.dumps(v)}") for k,v in sorted(data.items())]
                elif action == 'set':
                    if len(args)!=4: self.console.print(doc); return
                    k, v_str = args[2], args[3]
                    try: v = json.loads(v_str)
                    except json.JSONDecodeError: self.console.print(f"Invalid JSON: {v_str}"); return
                    self._run_async(self.api.update_system_config({k:v}))
                    self.console.print(f"System config update for '{k}' requested.")
                else: self.console.print(doc)
            elif cfg_type == 'module':
                if len(args) < 3: self.console.print(doc); return
                mod_id = action_or_mod_id
                action = args[2].lower()
                if not self.api.get_module_info(mod_id): self.console.print(f"Module '{mod_id}' not found."); return
                if action == 'view':
                    if len(args)!=3: self.console.print(doc); return
                    data = self.api.get_module_config(mod_id)
                    self.console.print(f"\n--- Configuration for Module: {mod_id} ---")
                    if data: [self.console.print(f"  {k:<25}: {json.dumps(v)}") for k,v in sorted(data.items())]
                    else: self.console.print("  (No specific configuration or module uses defaults)")
                elif action == 'set':
                    if len(args)!=5: self.console.print(doc); return
                    k, v_str = args[3], args[4]
                    try: v = json.loads(v_str)
                    except json.JSONDecodeError: self.console.print(f"Invalid JSON: {v_str}"); return
                    self._run_async(self.api.update_module_config(mod_id, {k:v}))
                    self.console.print(f"Module '{mod_id}' config update for '{k}' requested.")
                else: self.console.print(doc)
        except Exception as e: self.console.print(f"[bold red]Config error: {e}[/]"); self.logger.error("cmd_config error", exc_info=True)


    def cmd_events(self, args: List[str]):
        """Displays recent event history. Usage: events [count] [event_type_filter]"""
        # ... (this method seems fine, using self.console.print) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        count, etype_filter = 20, None
        if args:
            try: count = int(args[0]); etype_filter = args[1] if len(args)>1 else None
            except ValueError: count=20; etype_filter=args[0]
            if len(args) > 2: self.console.print("Warning: Extra args for 'events' ignored.")

        self.console.print(f"\n--- Event History (Last {count}{f', Type: {etype_filter}' if etype_filter else ''}) ---")
        try:
            history = self.api.get_event_history(count, etype_filter)
            if not history: self.console.print("No events found matching criteria."); return

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Timestamp", style="cyan", width=24)
            table.add_column("Priority", style="blue", width=10)
            table.add_column("Source", style="green", width=25)
            table.add_column("Type", style="yellow", width=40)
            table.add_column("Data Preview", style="white")

            for ev_dict in history:
                ts = datetime.fromtimestamp(ev_dict.get('timestamp',0)).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                data_val = ev_dict.get('data',{})
                d_str = json.dumps(data_val); d_str = d_str[:47]+"..." if len(d_str)>50 else d_str
                table.add_row(ts, ev_dict.get('priority','?'), ev_dict.get('source','?'), ev_dict.get('event_type','?'), d_str)
            self.console.print(table)
        except Exception as e: self.console.print(f"[bold red]Events error: {e}[/]"); self.logger.error("cmd_events error", exc_info=True)


    def cmd_health(self, args: List[str]):
        """Displays system and module health. Usage: health [check] (use 'check' to force a new run)"""
        # ... (your existing cmd_health is good, already uses rich.Table) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        force = len(args)>0 and args[0].lower()=='check'
        self.console.print(f"\n--- System Health {'(Forcing new check...)' if force else '(Using cached or periodic check)'} ---")
        try:
            health_data = self._run_async(self.api.run_health_check()) if force else self.api.get_system_health() # type: ignore
            if not health_data: self.console.print("No health data available."); return
            ts = datetime.fromtimestamp(health_data.get('timestamp',0)).strftime('%Y-%m-%d %H:%M:%S')
            self.console.print(f"Timestamp: {ts}, Overall Healthy: {health_data.get('overall_healthy', '?')}")
            metrics = health_data.get("system_metrics",{}); self.console.print("[System Metrics]"); [self.console.print(f"  {k.replace('_',' ').title()}: {v}") for k,v in metrics.items()]
            self.console.print("\n[Module Health]")
            mod_health = health_data.get("module_health",{})
            if not mod_health: self.console.print("  No module health data."); return

            table = Table(title="Module Health Status")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("State", style="yellow")
            table.add_column("Healthy", style="green")
            table.add_column("Details/Error", style="white")

            for mid, mh_dict in sorted(mod_health.items()):
                state = mh_dict.get('state', 'N/A')
                healthy = str(mh_dict.get('healthy', '?'))
                details = mh_dict.get('error_detail', '') or str(mh_dict.get('details', '')) or '(OK)'

                health_style = "green" if healthy.lower() == 'true' else "red" if healthy.lower() == 'false' else "dim"
                state_style = "green" if state == "RUNNING" else "yellow" if state in ["REGISTERED", "STOPPED", "INITIALIZED", "LOADING"] else "red"

                table.add_row(
                    mid,
                    f"[{state_style}]{state}[/{state_style}]",
                    f"[{health_style}]{healthy}[/{health_style}]",
                    details[:70] + ("..." if len(details) > 70 else "")
                )
            self.console.print(table)
        except Exception as e: self.console.print(f"[bold red]Health error: {e}[/]"); self.logger.error("cmd_health error", exc_info=True)


    def cmd_publish_event(self, args: List[str]):
        """Publishes a custom event. Usage: publish <event_type_str> [json_data_str] [priority_str (NORMAL, HIGH etc.)]"""
        # ... (this method seems fine, but ensure Priority enum is the real one when KERNEL_COMPONENTS_AVAILABLE) ...
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        doc = self.commands['publish'].__doc__ or "Publish command usage: publish <etype> [data_json] [priority]"
        if not args: self.console.print(doc); return

        etype, data_str, prio_name_str = args[0], "{}", "NORMAL"
        if len(args) > 1:
            try:
                json.loads(args[1]); data_str = args[1]
                if len(args) > 2: prio_name_str = args[2].upper()
            except (json.JSONDecodeError, IndexError):
                prio_name_str = args[1].upper()
                if len(args) > 2: self.console.print(f"Error: Too many arguments if JSON data is omitted. {doc}"); return

        try:
            data_payload = json.loads(data_str)
            if not isinstance(data_payload, dict): self.console.print("Error: JSON data for event must be an object/dictionary."); return

            event_priority: Optional[Priority] = None # type: ignore
            # This part needs access to the actual Priority Enum from PresenceOS_kernel
            # The dummy Priority class won't have members like Priority['NORMAL']
            if KERNEL_COMPONENTS_AVAILABLE:
                try:
                    event_priority = Priority[prio_name_str] # type: ignore
                except KeyError: # Handle invalid priority string
                    valid_priorities = ', '.join([p.name for p in Priority]) # type: ignore
                    self.console.print(f"Invalid priority '{prio_name_str}'. Use: {valid_priorities}"); return
                except KeyError:
                    valid_priorities = ', '.join([p.name for p in Priority]) # type: ignore
                    self.console.print(f"Invalid priority '{prio_name_str}'. Use: {valid_priorities}"); return
            else:
                self.console.print("CLI Error: Priority Enum not available as kernel components are not loaded."); return

        except json.JSONDecodeError: self.console.print(f"Invalid JSON data string: {data_str}"); return
        except Exception as e: self.console.print(f"Argument parsing error for publish: {e}"); return

        self.console.print(f"Publishing event: Type='{etype}', Priority={event_priority.name if event_priority else prio_name_str}, Data={json.dumps(data_payload)}") # type: ignore
        self._run_async(self.api.publish_event(etype, 'cli_command', data_payload, event_priority)) # type: ignore
        self.console.print("Event publish requested.")


    async def _get_prompt_interface_module_instance(self) -> Optional[PromptInterfaceModule]: # type: ignore
        if not KERNEL_COMPONENTS_AVAILABLE: return None
        # Ensure self.api is not None and has _kernel attribute
        if self.api and hasattr(self.api, '_kernel') and self.api._kernel and hasattr(self.api._kernel, 'module_loader'): # type: ignore
            module_loader = self.api._kernel.module_loader # type: ignore
            module_info = module_loader.get_module_info("prompt_interface")
            if module_info and module_info.instance:
                return module_info.instance
        self.logger.error("CLI: PromptInterfaceModule instance not found or kernel structure inaccessible.")
        self.console.print("[bold red]Error: PromptInterfaceModule is not available for 'ask'/'session' commands.[/]")
        return None

    async def _cmd_ask_async_helper(self, prompt_text: str):
        pim_instance: Optional[PromptInterfaceModule] = await self._get_prompt_interface_module_instance() # type: ignore
        if pim_instance and hasattr(pim_instance, 'process_user_prompt'):
            if asyncio.iscoroutinefunction(pim_instance.process_user_prompt):
                await pim_instance.process_user_prompt(prompt_text) # type: ignore
            else:
                self.logger.error("CLI: PromptInterfaceModule.process_user_prompt is not an async method.")
                self.console.print("[bold red]Internal Error: PromptInterfaceModule.process_user_prompt is not async.[/]")
        elif pim_instance:
            self.logger.error("CLI: PromptInterfaceModule found, but 'process_user_prompt' method is missing.")
            self.console.print("[bold red]Error: PromptInterfaceModule found, but 'process_user_prompt' method is missing.[/]")


    def cmd_ask(self, args: List[str]):
        """Sends a prompt to the LLM system. Usage: ask "Your prompt text here" """
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable for 'ask'.[/]"); return
        if not args: self.console.print("Usage: ask \"Your prompt text here\""); return
        prompt_text = " ".join(args)
        if len(prompt_text) >= 2 and prompt_text.startswith(('"', "'")) and prompt_text.endswith(prompt_text[0]):
            prompt_text = prompt_text[1:-1]

        if not prompt_text.strip(): self.console.print("Error: Prompt text cannot be empty."); return
        self.console.print(f"Sending prompt to LLM interface: \"{prompt_text}\"")
        self._run_async(self._cmd_ask_async_helper(prompt_text))

    async def _cmd_session_async_helper(self, action: str, new_id_val: Optional[str] = None, summarize_session_id: Optional[str] = None):
        pim_instance: Optional[PromptInterfaceModule] = await self._get_prompt_interface_module_instance() # type: ignore

        current_pim_session_id = None
        if pim_instance and hasattr(pim_instance, 'current_session_id'):
            current_pim_session_id = getattr(pim_instance, 'current_session_id')
            # Sync CLI's view of session ID with PIM's view
            if self.current_session_id != current_pim_session_id:
                  self.logger.info(f"CLI: Syncing session ID from PIM '{current_pim_session_id}' (was '{self.current_session_id}').")
                  self.current_session_id = current_pim_session_id


        if action == "new":
            old_cli_session_id = self.current_session_id
            new_session_id_to_set = new_id_val or str(uuid.uuid4())
            self.current_session_id = new_session_id_to_set # Update CLI's current session ID

            if pim_instance and hasattr(pim_instance, 'new_session') and asyncio.iscoroutinefunction(pim_instance.new_session):
                await pim_instance.new_session(new_session_id_to_set) # type: ignore
                self.console.print(f"New session: {new_session_id_to_set} (Old CLI: {old_cli_session_id}). History cleared by PromptInterface.")
            else:
                self.console.print(f"New session ID for CLI: {new_session_id_to_set} (Old CLI: {old_cli_session_id}). PromptInterfaceModule not updated or 'new_session' method issue.")

        elif action == "id":
            self.console.print(f"Current CLI session ID: {self.current_session_id or 'N/A'}")
            if current_pim_session_id: # Use the freshly fetched one
                  self.console.print(f"PromptInterface session ID: {current_pim_session_id}")

        elif action == "history":
            sid_to_show = self.current_session_id or 'N/A'
            history: List[Dict[str,Any]] = []
            if pim_instance and hasattr(pim_instance, 'get_formatted_history') and asyncio.iscoroutinefunction(pim_instance.get_formatted_history):
                history = await pim_instance.get_formatted_history() # type: ignore
            elif pim_instance and hasattr(pim_instance, 'conversation_history'):
                history = getattr(pim_instance, 'conversation_history', [])

            self.console.print(f"Session ({sid_to_show}) History ({len(history)} turns):")
            if not history: self.console.print("  (empty or unavailable from PromptInterface)")
            for i, entry in enumerate(history):
                content_preview = str(entry.get('content',''))[:80]
                if len(str(entry.get('content',''))) > 80: content_preview += "..."
                self.console.print(f"  {i+1}. {entry.get('role','?').capitalize()}: {content_preview}")

        elif action == "clear_history":
            sid_to_clear = self.current_session_id
            if pim_instance and hasattr(pim_instance, 'clear_current_session_history') and asyncio.iscoroutinefunction(pim_instance.clear_current_session_history):
                await pim_instance.clear_current_session_history() # type: ignore
                self.console.print(f"Session ({sid_to_clear}) history cleared via PromptInterface.")
            else:
                self.console.print(f"Could not clear history via PromptInterface for session {sid_to_clear}.")

        elif action == "summarize":
            target_session_id_for_summary = summarize_session_id or self.current_session_id
            if not target_session_id_for_summary:
                self.console.print("[bold red]Error: No active session to summarize or session ID not provided.[/]")
                return

            self.console.print(f"Requesting summarization for session: {target_session_id_for_summary}...")
            summarize_request_id = str(uuid.uuid4())

            if KERNEL_COMPONENTS_AVAILABLE and self.api:
                # Ensure Priority Enum is correctly referenced
                priority_to_use = Priority.NORMAL if hasattr(Priority, "NORMAL") else None
                if priority_to_use is None:
                      self.logger.error("CLI: Priority.NORMAL not found. Cannot set event priority for summarize.")
                      self.console.print("[bold red]Internal Error: Could not determine event priority.[/]")
                      return

                await self.api.publish_event(
                    etype="presence_session:summarize_request",
                    src="cli_command",
                    data={
                        "request_id": summarize_request_id,
                        "session_id": target_session_id_for_summary,
                        "reason": "user_cli_command"
                    },
                    prio=priority_to_use
                )
                self.console.print(f"Summarization request sent (ReqID: {summarize_request_id}) for session {target_session_id_for_summary}.")
            else:
                self.console.print("[bold red]Error: Cannot publish summarize event, kernel components or API not available.[/]")


    def cmd_session(self, args: List[str]):
        """Manages user sessions.
        Usage: session new [custom_id]   - Starts a new session (optionally with custom ID).
               session id                  - Shows the current session ID.
               session history             - Shows history for the current session.
               session clear_history       - Clears history for the current session.
               session summarize [sess_id] - Requests summarization for a session (current if ID omitted)."""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable for 'session'.[/]"); return

        valid_actions = ["new", "id", "history", "clear_history", "summarize"]
        doc = (self.commands['session'].__doc__ or "").strip()

        if not args or args[0].lower() not in valid_actions:
            self.console.print(f"Invalid session command. Usage:\n{doc}"); return

        action = args[0].lower()

        new_id_val: Optional[str] = None
        summarize_session_id_val: Optional[str] = None

        if action == "new":
            if len(args) > 1: new_id_val = args[1]
            self._run_async(self._cmd_session_async_helper(action, new_id_val=new_id_val))
        elif action == "summarize":
            if len(args) > 1: summarize_session_id_val = args[1]
            self._run_async(self._cmd_session_async_helper(action, summarize_session_id=summarize_session_id_val))
        elif action in ["id", "history", "clear_history"]:
            if len(args) > 1: self.console.print(f"Warning: Extra arguments for 'session {action}' ignored.");
            self._run_async(self._cmd_session_async_helper(action))
        else:
              self.console.print(f"Unknown session action: {action}. Usage:\n{doc}")

    # Rest of the CLI methods would go here...
    # For brevity, I'll just include the essential ones

    def cmd_scaffold_agent(self, args: List[str]):
        """Triggers the AgentScaffolder module to create a new agent."""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        if len(args) < 6:
            self.console.print("Missing arguments for scaffold_agent."); return

        agent_name = args[0]
        role = args[1]
        llm_api = args[2]
        llm_model = args[3]
        api_key_env_var = args[4]
        priming_prompt_text = args[5]

        event_data = {
            "request_id": str(uuid.uuid4()),
            "agent_name": agent_name,
            "role": role,
            "llm_api": llm_api,
            "llm_model": llm_model,
            "api_key_env_var": api_key_env_var,
            "priming_prompt": priming_prompt_text,
            "enable_docker_compose": False,
            "tools_to_include": []
        }

        self.console.print(f"Publishing scaffold_agent request for: {agent_name}...")
        self._run_async(self.api.publish_event("presence_system:scaffold_agent_request", 'cli_command', event_data, Priority.HIGH))
        self.console.print("Agent scaffolding request sent.")

    def cmd_send_mesh_signal(self, args: List[str]):
        """Sends an inter-node mesh signal via Redis."""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        if not args:
            self.console.print("Usage: send_mesh_signal <signal_type> [json_payload_str] [target_node_id]"); return

        signal_type = args[0]
        payload_str = args[1] if len(args) > 1 else "{}"
        target_node_id = args[2] if len(args) > 2 else None

        try:
            payload_dict = json.loads(payload_str)
            event_data = {
                "signal_id": str(uuid.uuid4()),
                "signal_type": signal_type,
                "payload": payload_dict,
                "from": self.api.get_system_config().get('system_id', 'cli_instance'),
                "to": target_node_id
            }

            self.console.print(f"Publishing MESH_SIGNAL_SEND_REQUEST: Type='{signal_type}', To='{target_node_id or 'all'}'")
            self._run_async(self.api.publish_event("MESH_SIGNAL_SEND_REQUEST", 'cli_command', event_data, Priority.NORMAL))
            self.console.print("Mesh signal send requested.")
        except json.JSONDecodeError:
            self.console.print(f"[bold red]Invalid JSON payload string: {payload_str}[/]")

    def cmd_send_external_command(self, args: List[str]):
        """Sends an external command to trigger an internal PresenceOS event via Redis."""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return
        if not args:
            self.console.print("Usage: send_external_command <command_type> [json_data_str]"); return

        command_type = args[0]
        data_str = args[1] if len(args) > 1 else "{}"

        try:
            data_payload = json.loads(data_str)
            event_to_bridge_data = {
                "command_type": command_type,
                "data": data_payload,
                "request_id": str(uuid.uuid4()),
                "source_cli_id": self.api.get_system_config().get('system_id', 'cli_instance'),
                "timestamp": datetime.utcnow().isoformat()
            }

            self.console.print(f"Publishing internal event to be bridged to Redis: Type='{command_type}'")
            self._run_async(self.api.publish_event("presence_external:command:send_request", 'cli_command', event_to_bridge_data, Priority.HIGH))
            self.console.print("External command send requested.")
        except json.JSONDecodeError:
            self.console.print(f"[bold red]Invalid JSON data string: {data_str}[/]")
        except Exception as e:
            self.console.print(f"[bold red]Error sending external command: {e}[/]")
            self.logger.error("cmd_send_external_command error", exc_info=True)

    # ===== COMBINED INTELLIGENCE COMMANDS =====

    def cmd_collective(self, args: List[str]):
        """Query collective consciousness insights and system intelligence metrics.
        Usage: collective status                    - Show collective intelligence status
               collective insights [count]          - Show recent insights
               collective patterns                  - Show agent collaboration patterns
               collective resonance                 - Show cognitive resonance events"""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return

        if not args or args[0] == "status":
            self.console.print("\n--- Collective Intelligence Status ---")
            # Query collective consciousness module
            self._run_async(self._query_collective_status())
        elif args[0] == "insights":
            count = int(args[1]) if len(args) > 1 else 10
            self.console.print(f"\n--- Recent Collective Insights (Last {count}) ---")
            self._run_async(self._query_collective_insights(count))
        elif args[0] == "patterns":
            self.console.print("\n--- Agent Collaboration Patterns ---")
            self._run_async(self._query_collaboration_patterns())
        elif args[0] == "resonance":
            self.console.print("\n--- Cognitive Resonance Events ---")
            self._run_async(self._query_resonance_events())
        else:
            self.console.print("Usage: collective <status|insights|patterns|resonance>")

    def cmd_orchestrate(self, args: List[str]):
        """Configure and monitor LLM orchestration.
        Usage: orchestrate status                   - Show orchestration status
               orchestrate config <key> <value>     - Configure orchestrator
               orchestrate agents <agent1,agent2>   - Set preferred agent combination
               orchestrate merge <strategy>         - Set response merge strategy"""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return

        if not args or args[0] == "status":
            self.console.print("\n--- LLM Orchestration Status ---")
            self._run_async(self._query_orchestration_status())
        elif args[0] == "config" and len(args) >= 3:
            key, value = args[1], args[2]
            self.console.print(f"Setting orchestrator config: {key} = {value}")
            self._run_async(self._configure_orchestrator(key, value))
        elif args[0] == "agents" and len(args) >= 2:
            agents = args[1].split(',')
            self.console.print(f"Setting preferred agents: {', '.join(agents)}")
            self._run_async(self._set_preferred_agents(agents))
        elif args[0] == "merge" and len(args) >= 2:
            strategy = args[1]
            self.console.print(f"Setting merge strategy: {strategy}")
            self._run_async(self._set_merge_strategy(strategy))
        else:
            self.console.print("Usage: orchestrate <status|config|agents|merge>")

    def cmd_semantic(self, args: List[str]):
        """Monitor semantic communication patterns.
        Usage: semantic status                    - Show semantic communication status
               semantic intents                   - Show active agent intents
               semantic routes                    - Show semantic routing table
               semantic knowledge                 - Show knowledge graph status"""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return

        if not args or args[0] == "status":
            self.console.print("\n--- Semantic Communication Status ---")
            self._run_async(self._query_semantic_status())
        elif args[0] == "intents":
            self.console.print("\n--- Active Agent Intents ---")
            self._run_async(self._query_active_intents())
        elif args[0] == "routes":
            self.console.print("\n--- Semantic Routing Table ---")
            self._run_async(self._query_semantic_routes())
        elif args[0] == "knowledge":
            self.console.print("\n--- Knowledge Graph Status ---")
            self._run_async(self._query_knowledge_graph())
        else:
            self.console.print("Usage: semantic <status|intents|routes|knowledge>")

    def cmd_intelligence(self, args: List[str]):
        """Combined intelligence operations.
        Usage: intelligence query "prompt"         - Query all agents in parallel
               intelligence debate "topic"         - Trigger multi-agent debate
               intelligence compare <req_id>       - Compare agent responses
               intelligence optimize                - Optimize agent combinations"""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return

        if not args:
            self.console.print("Usage: intelligence <query|debate|compare|optimize>")
        elif args[0] == "query" and len(args) >= 2:
            prompt = " ".join(args[1:])
            self.console.print(f"🚀 Triggering combined intelligence query: {prompt}")
            self._run_async(self._trigger_combined_query(prompt))
        elif args[0] == "debate" and len(args) >= 2:
            topic = " ".join(args[1:])
            self.console.print(f"🗣️ Triggering multi-agent debate: {topic}")
            self._run_async(self._trigger_debate(topic))
        elif args[0] == "compare" and len(args) >= 2:
            request_id = args[1]
            self.console.print(f"⚖️ Comparing responses for request: {request_id}")
            self._run_async(self._compare_responses(request_id))
        elif args[0] == "optimize":
            self.console.print("🎯 Optimizing agent combinations...")
            self._run_async(self._optimize_combinations())
        else:
            self.console.print("Usage: intelligence <query|debate|compare|optimize>")

    def cmd_agents(self, args: List[str]):
        """Advanced agent management and analysis.
        Usage: agents performance                - Show agent performance metrics
               agents capabilities               - Show agent capabilities
               agents combinations               - Show effective agent combinations
               agents sync                       - Trigger agent synchronization"""
        if not KERNEL_COMPONENTS_AVAILABLE: self.console.print("[bold red]CLI Error: Kernel unavailable.[/]"); return

        if not args or args[0] == "performance":
            self.console.print("\n--- Agent Performance Metrics ---")
            self._run_async(self._query_agent_performance())
        elif args[0] == "capabilities":
            self.console.print("\n--- Agent Capabilities ---")
            self._run_async(self._query_agent_capabilities())
        elif args[0] == "combinations":
            self.console.print("\n--- Effective Agent Combinations ---")
            self._run_async(self._query_agent_combinations())
        elif args[0] == "sync":
            self.console.print("🔄 Triggering agent synchronization...")
            self._run_async(self._trigger_agent_sync())
        else:
            self.console.print("Usage: agents <performance|capabilities|combinations|sync>")

    # ===== ASYNC HELPERS FOR COMBINED INTELLIGENCE =====

    async def _query_collective_status(self):
        """Query collective consciousness status"""
        try:
            # Publish event to query collective consciousness
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "status"
            }
            await self.api.publish_event("presence_collective:status_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Collective status request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying collective status: {e}[/]")

    async def _query_collective_insights(self, count: int):
        """Query recent collective insights"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "insights",
                "count": count
            }
            await self.api.publish_event("presence_collective:insights_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print(f"Requested {count} recent insights. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying insights: {e}[/]")

    async def _query_collaboration_patterns(self):
        """Query agent collaboration patterns"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "patterns"
            }
            await self.api.publish_event("presence_collective:patterns_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Collaboration patterns request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying patterns: {e}[/]")

    async def _query_resonance_events(self):
        """Query cognitive resonance events"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "resonance"
            }
            await self.api.publish_event("presence_collective:resonance_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Resonance events request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying resonance: {e}[/]")

    async def _query_orchestration_status(self):
        """Query LLM orchestration status"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "status"
            }
            await self.api.publish_event("presence_orchestrator:status_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Orchestration status request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying orchestration status: {e}[/]")

    async def _configure_orchestrator(self, key: str, value: str):
        """Configure orchestrator settings"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "config_key": key,
                "config_value": value
            }
            await self.api.publish_event("presence_orchestrator:config_update", 'cli_command', event_data, Priority.HIGH)
            self.console.print(f"Orchestrator config update sent: {key} = {value}")
        except Exception as e:
            self.console.print(f"[bold red]Error configuring orchestrator: {e}[/]")

    async def _set_preferred_agents(self, agents: List[str]):
        """Set preferred agent combination"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "preferred_agents": agents
            }
            await self.api.publish_event("presence_orchestrator:set_agents", 'cli_command', event_data, Priority.HIGH)
            self.console.print(f"Preferred agents set: {', '.join(agents)}")
        except Exception as e:
            self.console.print(f"[bold red]Error setting preferred agents: {e}[/]")

    async def _set_merge_strategy(self, strategy: str):
        """Set response merge strategy"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "merge_strategy": strategy
            }
            await self.api.publish_event("presence_orchestrator:set_merge_strategy", 'cli_command', event_data, Priority.HIGH)
            self.console.print(f"Merge strategy set: {strategy}")
        except Exception as e:
            self.console.print(f"[bold red]Error setting merge strategy: {e}[/]")

    async def _query_semantic_status(self):
        """Query semantic communication status"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "status"
            }
            await self.api.publish_event("presence_semantic:status_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Semantic status request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying semantic status: {e}[/]")

    async def _query_active_intents(self):
        """Query active agent intents"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "intents"
            }
            await self.api.publish_event("presence_semantic:intents_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Active intents request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying intents: {e}[/]")

    async def _query_semantic_routes(self):
        """Query semantic routing table"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "routes"
            }
            await self.api.publish_event("presence_semantic:routes_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Semantic routes request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying routes: {e}[/]")

    async def _query_knowledge_graph(self):
        """Query knowledge graph status"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "knowledge"
            }
            await self.api.publish_event("presence_semantic:knowledge_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Knowledge graph request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying knowledge graph: {e}[/]")

    async def _trigger_combined_query(self, prompt: str):
        """Trigger combined intelligence query"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "prompt": prompt,
                "query_type": "combined_intelligence"
            }
            await self.api.publish_event("presence_intelligence:combined_query", 'cli_command', event_data, Priority.HIGH)
            self.console.print(f"Combined intelligence query triggered: {prompt}")
        except Exception as e:
            self.console.print(f"[bold red]Error triggering combined query: {e}[/]")

    async def _trigger_debate(self, topic: str):
        """Trigger multi-agent debate"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "topic": topic,
                "debate_type": "multi_agent"
            }
            await self.api.publish_event("presence_intelligence:multi_agent_debate", 'cli_command', event_data, Priority.HIGH)
            self.console.print(f"Multi-agent debate triggered: {topic}")
        except Exception as e:
            self.console.print(f"[bold red]Error triggering debate: {e}[/]")

    async def _compare_responses(self, request_id: str):
        """Compare agent responses for a request"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "target_request_id": request_id,
                "comparison_type": "response_analysis"
            }
            await self.api.publish_event("presence_intelligence:compare_responses", 'cli_command', event_data, Priority.NORMAL)
            self.console.print(f"Response comparison triggered for request: {request_id}")
        except Exception as e:
            self.console.print(f"[bold red]Error comparing responses: {e}[/]")

    async def _optimize_combinations(self):
        """Optimize agent combinations"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "optimization_type": "agent_combinations"
            }
            await self.api.publish_event("presence_intelligence:optimize_combinations", 'cli_command', event_data, Priority.HIGH)
            self.console.print("Agent combination optimization triggered.")
        except Exception as e:
            self.console.print(f"[bold red]Error optimizing combinations: {e}[/]")

    async def _query_agent_performance(self):
        """Query agent performance metrics"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "performance"
            }
            await self.api.publish_event("presence_agents:performance_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Agent performance request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying agent performance: {e}[/]")

    async def _query_agent_capabilities(self):
        """Query agent capabilities"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "capabilities"
            }
            await self.api.publish_event("presence_agents:capabilities_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Agent capabilities request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying capabilities: {e}[/]")

    async def _query_agent_combinations(self):
        """Query effective agent combinations"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "query_type": "combinations"
            }
            await self.api.publish_event("presence_agents:combinations_request", 'cli_command', event_data, Priority.NORMAL)
            self.console.print("Agent combinations request sent. Check events for response.")
        except Exception as e:
            self.console.print(f"[bold red]Error querying combinations: {e}[/]")

    async def _trigger_agent_sync(self):
        """Trigger agent synchronization"""
        try:
            event_data = {
                "request_id": str(uuid.uuid4()),
                "sync_type": "full_synchronization"
            }
            await self.api.publish_event("presence_agents:sync_request", 'cli_command', event_data, Priority.HIGH)
            self.console.print("Agent synchronization triggered.")
        except Exception as e:
            self.console.print(f"[bold red]Error triggering agent sync: {e}[/]")


# --- End of AsyncCommandLineInterface class ---


if __name__ == "__main__":
    print("CLI Module - Standalone Test Mode")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)-7s] %(name)-15s: %(message)s')
    if not KERNEL_COMPONENTS_AVAILABLE:
        print("CRITICAL: Cannot run CLI test: PresenceOS_kernel components not available via import.")
        print("CLI module loaded but kernel components not available for standalone testing.")
        print("This is normal when CLI is imported by the kernel.")
        # Don't exit - allow the module to be imported even without kernel components
        # sys.exit(1)

    print("To test CLI, run PresenceOS via run_presence_os.py")