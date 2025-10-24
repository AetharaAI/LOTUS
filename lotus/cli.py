# --- START OF REFACTORED FILE cli.py ---
#!/usr/bin/env python3
"""
LOTUS Command Line Interface - Enhanced Version
==============================================

Complete CLI for managing and interacting with LOTUS.

Commands:
- start: Start LOTUS system
- stop: Stop LOTUS gracefully
- restart: Restart LOTUS
- status: Check system status
- chat: Interactive chat with LOTUS
- modules: List/manage modules
- config: View/edit configuration
- logs: View system logs
- test: Run tests
- install: Install a module
- doctor: Run diagnostic checks

Author: LOTUS Team
Version: 1.0.0 (Session 7)
"""

import click
import asyncio
import sys
import os
import json
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import subprocess
import time # Import time for delays and timeouts

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

# Initialize console
if RICH_AVAILABLE:
    console = Console()
else:
    console = None


def print_styled(text: str, style: str = "", **kwargs):
    """Print with style if rich is available"""
    if RICH_AVAILABLE and console:
        console.print(text, style=style, **kwargs)
    else:
        print(text)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    🌸 LOTUS AI Operating System - Command Line Interface
    
    Welcome to LOTUS! Use these commands to manage and interact with your AI OS.
    """
    pass


@cli.command()
@click.option("--config", default="config/system.yaml", help="Config file path")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--no-daemon", is_flag=True, help="Run in foreground (don't daemonize)")
def start(config, debug, no_daemon):
    """Start the LOTUS system"""
    print_styled("\n🌸 Starting LOTUS...\n", "bold green")
    
    # Check if already running
    pid_file = Path("data/state/pid.lock")
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 0)  # Check if process exists
            print_styled(f"✗ LOTUS is already running (PID: {pid})", "bold red")
            print_styled("  Use 'lotus stop' to stop it first\n", "yellow")
            sys.exit(1)
        except OSError:
            # Process doesn't exist, remove stale PID file
            pid_file.unlink()
    
    # Import here to avoid circular imports
    try:
        from nucleus import Nucleus
    except ImportError as e:
        print_styled(f"✗ Failed to import Nucleus: {e}", "bold red")
        print_styled("  Make sure you're in the LOTUS project directory", "yellow")
        sys.exit(1)
    
    # Create and run nucleus
    try:
        if no_daemon:
            # Run in foreground
            nucleus = Nucleus(config_path=config)
            asyncio.run(nucleus.run())
        else:
            # Daemonize (run in background)
            print_styled("  Starting in background mode...", "cyan")
            
            # Fork and run
            pid = os.fork()
            if pid == 0:
                # Child process
                os.setsid()
                
                # Close stdin/stdout/stderr to detach from terminal
                sys.stdin.close()
                sys.stdout = open(os.devnull, 'w')
                sys.stderr = open(os.devnull, 'w')

                nucleus = Nucleus(config_path=config)
                
                # Save PID
                pid_file.parent.mkdir(parents=True, exist_ok=True)
                pid_file.write_text(str(os.getpid()))
                
                # Run nucleus
                asyncio.run(nucleus.run())
            else:
                # Parent process
                print_styled(f"  ✓ LOTUS started (PID: {pid})", "green")
                print_styled(f"  Use 'lotus logs -f' to follow logs", "cyan")
                print_styled(f"  Use 'lotus status' to check status\n", "cyan")
                
    except KeyboardInterrupt:
        print_styled("\n🌸 LOTUS startup cancelled", "yellow")
    except Exception as e:
        print_styled(f"\n✗ Failed to start LOTUS: {e}", "bold red")
        sys.exit(1)


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Force stop without graceful shutdown")
def stop(force):
    """Stop the LOTUS system"""
    print_styled("\n🌸 Stopping LOTUS...\n", "bold yellow")
    
    pid_file = Path("data/state/pid.lock")
    
    if not pid_file.exists():
        print_styled("✗ LOTUS is not running", "red")
        print_styled("  No PID file found\n", "yellow")
        sys.exit(1)
    
    try:
        pid = int(pid_file.read_text().strip())
        
        # Check if process exists
        try:
            os.kill(pid, 0)
        except OSError:
            print_styled(f"✗ Process {pid} not found (stale PID file)", "red")
            pid_file.unlink()
            sys.exit(1)
        
        # Send shutdown signal
        if force:
            print_styled(f"  Sending SIGKILL to process {pid}...", "yellow")
            os.kill(pid, signal.SIGKILL)
        else:
            print_styled(f"  Sending SIGTERM to process {pid}...", "cyan")
            os.kill(pid, signal.SIGTERM)
            
            # Wait for graceful shutdown (max 30 seconds)
            import time
            for i in range(30):
                try:
                    os.kill(pid, 0)
                    time.sleep(1)
                except OSError:
                    break
            else:
                print_styled("  Process didn't stop gracefully, forcing...", "yellow")
                os.kill(pid, signal.SIGKILL)
        
        # Remove PID file
        pid_file.unlink()
        
        print_styled("  ✓ LOTUS stopped successfully\n", "green")
        
    except Exception as e:
        print_styled(f"✗ Error stopping LOTUS: {e}\n", "bold red")
        sys.exit(1)


@cli.command()
def restart():
    """Restart the LOTUS system"""
    print_styled("\n🌸 Restarting LOTUS...\n", "bold cyan")
    
    # Stop
    ctx = click.get_current_context()
    ctx.invoke(stop)
    
    # Wait a moment
    time.sleep(2)
    
    # Start
    ctx.invoke(start)


@cli.command()
@click.option("--json-output", is_flag=True, help="Output status as JSON")
def status(json_output):
    """Check LOTUS system status"""
    
    if json_output:
        # JSON output for programmatic use
        status_data = get_system_status()
        print(json.dumps(status_data, indent=2))
        return
    
    print_styled("\n🌸 LOTUS Status\n", "bold cyan")
    
    # Check if running
    pid_file = Path("data/state/pid.lock")
    
    if not pid_file.exists():
        print_styled("Status: Not Running", "red")
        print_styled("\nUse 'lotus start' to start the system\n", "cyan")
        return
    
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # Check if process exists
        
        print_styled(f"Status: Running (PID: {pid})", "green")
        
        # Get more detailed status
        status_data = get_system_status()
        
        if RICH_AVAILABLE and console:
            # Create rich table
            table = Table(show_header=False, box=None)
            table.add_row("Uptime:", Text(status_data.get("uptime", "Unknown"), style="yellow"))
            table.add_row("Modules:", Text(str(status_data.get("modules_count", "?")), style="magenta"))
            table.add_row("Memory:", Text(status_data.get("memory", "Unknown"), style="cyan"))
            table.add_row("CPU:", Text(status_data.get("cpu", "Unknown"), style="green"))
            console.print(table)
        else:
            print(f"Uptime: {status_data.get('uptime', 'Unknown')}")
            print(f"Modules: {status_data.get('modules_count', '?')}")
            print(f"Memory: {status_data.get('memory', 'Unknown')}")
            print(f"CPU: {status_data.get('cpu', 'Unknown')}")
        
        print()
        
    except OSError:
        print_styled("Status: Not Running (stale PID file)", "yellow")
        print_styled("\nRemoving stale PID file...", "cyan")
        pid_file.unlink()
        print()


def get_system_status() -> dict:
    """Get detailed system status"""
    status = {
        "running": False,
        "pid": None,
        "uptime": "Unknown",
        "modules_count": 0,
        "memory": "Unknown",
        "cpu": "Unknown"
    }
    
    pid_file = Path("data/state/pid.lock")
    if not pid_file.exists():
        return status
    
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        
        status["running"] = True
        status["pid"] = pid
        
        # Get process info
        try:
            import psutil
            process = psutil.Process(pid)
            
            # Uptime
            create_time = datetime.fromtimestamp(process.create_time())
            uptime = datetime.now() - create_time
            hours = int(uptime.total_seconds() // 3600)
            minutes = int((uptime.total_seconds() % 3600) // 60)
            status["uptime"] = f"{hours}h {minutes}m"
            
            # Memory
            mem = process.memory_info().rss / (1024 * 1024)  # MB
            status["memory"] = f"{mem:.1f} MB"
            
            # CPU
            cpu = process.cpu_percent(interval=0.1)
            status["cpu"] = f"{cpu:.1f}%"
            
        except ImportError:
            # psutil not installed
            pass
        except psutil.NoSuchProcess:
            # Process died between check and psutil.Process() call
            pass
        
        # Get module count from state file (this is more reliable if Nucleus updates it)
        # For a truly accurate count, you'd need a method in Nucleus itself
        # or poll a dedicated status channel from Nucleus.
        # For now, let's rely on the internal state if it gets populated.
        
        # Note: The original project structure implies Nucleus maintains a module_state.json.
        # However, the current nucleus.py does not explicitly write active modules to module_state.json.
        # We'll keep this placeholder but acknowledge it might not be accurate.
        state_file = Path("data/state/module_state.json")
        if state_file.exists():
            try:
                with open(state_file) as f:
                    module_state = json.load(f)
                    status["modules_count"] = len(module_state.get("active_modules", []))
            except json.JSONDecodeError:
                # Malformed JSON
                pass
            except Exception:
                # Other file errors
                pass
        
    except OSError:
        pass
    
    return status


@cli.command()
@click.option("--interactive", "-i", is_flag=True, help="Start interactive chat session")
@click.option("--debug-events", "-d", is_flag=True, help="Show all internal message bus events for debugging")
@click.argument("message", required=False)
def chat(interactive, message, debug_events):
    """Chat with LOTUS"""
    # Warn if virtualenv does not appear to be active. This helps avoid
    # the common issue where users open a new terminal and forget to
    # `source venv/bin/activate` so dependencies are missing.
    venv_active = os.environ.get('VIRTUAL_ENV') or os.environ.get('VENV')
    if not venv_active:
        print_styled("\n⚠️  It looks like the project's virtualenv is not active.", "yellow")
        print_styled("   Run: source venv/bin/activate  or use ./run_lotus.sh <command>\n", "yellow")
    
    if interactive:
        # Start interactive session
        print_styled("\n🌸 LOTUS Interactive Chat", "bold cyan")
        print_styled("Type 'exit' or 'quit' to end session\n", "dim")
        
        while True:
            try:
                user_input = console.input("[bold green]You:[/bold green] ") # Use rich for input prompt
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    print_styled("\n🌸 Goodbye!\n", "cyan")
                    break
                
                if not user_input.strip():
                    continue
                
                # Send to LOTUS and get response
                # Pass debug_events flag to the sending function
                response = asyncio.run(send_message_to_lotus_async(user_input, debug_events))
                print_styled(f"\n[bold magenta]LOTUS:[/bold magenta] {response}\n")
                
            except KeyboardInterrupt:
                print_styled("\n\n🌸 Chat ended\n", "yellow")
                break
            except Exception as e:
                print_styled(f"\n✗ Error: {e}\n", "red")
    
    elif message:
        # Single message
        response = asyncio.run(send_message_to_lotus_async(message, debug_events))
        print_styled(f"\n[bold magenta]LOTUS:[/bold magenta] {response}\n")
    
    else:
        print_styled("\n✗ Please provide a message or use --interactive\n", "red")
        print_styled("Examples:", "cyan")
        print_styled("  lotus chat 'Hello LOTUS'", "dim")
        print_styled("  lotus chat --interactive\n", "dim")


async def send_message_to_lotus_async(message: str, debug_events: bool = False) -> str:
    """
    Send message to running LOTUS instance via Redis pub/sub and wait for response.
    Includes an event listener for debugging.
    """
    from lib.message_bus import MessageBus

    bus = MessageBus()
    response_queue = asyncio.Queue()
    event_log: List[Dict[str, Any]] = [] # To store all captured events

    async def _event_handler(channel: str, data: Dict[str, Any]):
        """Handler for all subscribed events"""
        event_entry = {"channel": channel, "data": data, "timestamp": datetime.utcnow().isoformat()}
        event_log.append(event_entry)
        
        if debug_events:
            print_styled(f"[bold dim purple]  Event: {channel}[/bold dim purple]", highlight=False)
            if channel == "cognition.thought":
                 print_styled(f"[dim grey]    Thought: {data.get('thought',{}).get('understanding','')[:70]}...[/dim grey]", highlight=False)
            elif channel == "cognition.tool_call":
                 print_styled(f"[dim grey]    Tool: {data.get('tool')}, Params: {data.get('params')}[/dim grey]", highlight=False)
            elif channel == "action.respond":
                 print_styled(f"[bold yellow]    LOTUS Response: {data.get('content','')[:70]}...[/bold yellow]", highlight=False)

        if channel == "action.respond":
            await response_queue.put(data.get("content", "(empty response)"))

    # Use a unique session ID for this interaction for better filtering if needed
    session_id = f"cli-chat-{int(time.time() * 1000)}"
    user_payload = {"text": message, "context": {"source": "cli", "session_id": session_id}}

    response_content = "(No response from LOTUS within timeout)"
    # Give plenty of time for LLM response, but also for debugging in case of hang
    timeout = 60.0 

    try:
        if RICH_AVAILABLE and console:
            # Use Live context for progress spinner and dynamic output
            with Live(
                Text("Waiting for LOTUS...", style="bold yellow"),
             #   spinner="dots",
                refresh_per_second=4,
                console=console
            ) as live:
                await bus.connect()
                
                # Subscribe to all relevant channels for debugging
                await bus.subscribe("perception.*", _event_handler)
                await bus.subscribe("cognition.*", _event_handler)
                await bus.subscribe("action.*", _event_handler)
                await bus.subscribe("memory.*", _event_handler)
                await bus.subscribe("system.*", _event_handler) # Catch any system events

                live.update(Text("Publishing message...", style="bold yellow"))
                await bus.publish("perception.user_input", user_payload)
                
                # Wait for response with timeout
                try:
                    live.update(Text("LOTUS is thinking...", style="bold cyan"))
                    response_content = await asyncio.wait_for(response_queue.get(), timeout=timeout)
                    live.update(Text("LOTUS responded!", style="bold green"))
                except asyncio.TimeoutError:
                    live.update(Text("LOTUS timed out.", style="bold red"))
                    response_content = "(No response from LOTUS within timeout)"
                except Exception as e:
                    live.update(Text(f"Error during response: {e}", style="bold red"))
                    response_content = f"Error during response: {e}"
        else: # No Rich available, fallback to basic print
            print_styled("Connecting to LOTUS...", "yellow")
            await bus.connect()
            await bus.publish("perception.user_input", user_payload)
            print_styled("LOTUS is thinking...", "cyan")
            try:
                response_content = await asyncio.wait_for(response_queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                response_content = "(No response from LOTUS within timeout)"
            except Exception as e:
                response_content = f"Error during response: {e}"

    except Exception as e:
        print_styled(f"Failed to connect to message bus: {e}", "bold red")
        return f"Error connecting to LOTUS: {e}"
    finally:
        try:
            # Unsubscribe from all channels before disconnecting
            if bus.connected:
                await bus.unsubscribe("perception.*", _event_handler)
                await bus.unsubscribe("cognition.*", _event_handler)
                await bus.unsubscribe("action.*", _event_handler)
                await bus.unsubscribe("memory.*", _event_handler)
                await bus.unsubscribe("system.*", _event_handler)
                await bus.disconnect()
        except Exception as e:
            print_styled(f"Error disconnecting from message bus: {e}", "red")

    return response_content


@cli.command()
@click.option("--type", "-t", type=click.Choice(["all", "core", "capability", "integration", "personality"]), 
              default="all", help="Filter by module type")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def modules(type, json_output):
    """List installed modules"""
    
    modules_list = discover_modules(type)
    
    if json_output:
        print(json.dumps(modules_list, indent=2))
        return
    
    print_styled("\n🌸 LOTUS Modules\n", "bold cyan")
    
    if RICH_AVAILABLE and console:
        table = Table(show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Version", style="green")
        table.add_column("Status", style="magenta") # This status is heuristic, not live
        
        for module in modules_list:
            # Heuristic: if core module, assume active. Otherwise, hard to tell without querying nucleus.
            status = "✓ Active" if module["type"] == "core_modules" else "○ Inactive/Unknown"
            table.add_row(
                module["name"],
                module["type"].replace("_modules", "").capitalize(), # Nicer type name
                module.get("version", "?"),
                status
            )
        
        console.print(table)
    else:
        for module in modules_list:
            status = "[ACTIVE]" if module["type"] == "core_modules" else "[INACTIVE/UNKNOWN]"
            print(f"{status} {module['name']} ({module['type'].replace('_modules', '').capitalize()}) v{module.get('version', '?')}")
    
    print()


def discover_modules(filter_type: str = "all") -> list:
    """Discover installed modules by reading manifest files"""
    modules_data = []
    modules_base_dir = Path("modules")
    
    if not modules_base_dir.exists():
        return modules_data
    
    type_dirs_map = {
        "core": "core_modules",
        "capability": "capability_modules",
        "integration": "integration_modules",
        "personality": "personalities"
    }
    
    target_dirs = [type_dirs_map[k] for k in type_dirs_map if filter_type == "all" or filter_type == k]

    for type_dir_name in target_dirs:
        type_path = modules_base_dir / type_dir_name
        if not type_path.exists():
            continue
        
        for module_path in type_path.iterdir():
            if not module_path.is_dir():
                continue
            
            manifest_path = module_path / "manifest.yaml"
            if not manifest_path.exists():
                continue
            
            try:
                import yaml
                with open(manifest_path) as f:
                    manifest_data = yaml.safe_load(f)
                
                module_name = manifest_data.get("name", module_path.name)
                
                modules_data.append({
                    "name": module_name,
                    "type": type_dir_name, # Keep internal type for filtering, convert for display
                    "version": manifest_data.get("version", "0.0.0"),
                    "description": manifest_data.get("description", "No description provided."),
                    "path": str(module_path)
                })
            except Exception as e:
                print_styled(f"✗ Error loading manifest for {module_path.name}: {e}", "red")
    
    return modules_data


@cli.command()
@click.argument("module_name")
@click.option("--edit", is_flag=True, help="Open config in editor")
def config(module_name, edit):
    """View or edit module configuration"""
    
    config_file = Path(f"config/modules/{module_name}.yaml")
    
    if not config_file.exists():
        print_styled(f"\n✗ No config found for module: {module_name}\n", "red")
        return
    
    if edit:
        # Open in editor
        editor = os.environ.get("EDITOR", "nano")
        try:
            subprocess.run([editor, str(config_file)], check=True)
            print_styled(f"\n✓ Config for {module_name} updated.\n", "green")
        except subprocess.CalledProcessError:
            print_styled(f"\n✗ Error opening editor or saving config for {module_name}.\n", "red")
        except FileNotFoundError:
            print_styled(f"\n✗ Editor '{editor}' not found. Please set EDITOR environment variable or install it.\n", "red")
    else:
        # Display config
        print_styled(f"\n🌸 Config for [bold cyan]{module_name}[/bold cyan]\n", "bold")
        
        try:
            with open(config_file) as f:
                content = f.read()
            
            if RICH_AVAILABLE and console:
                syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
                console.print(syntax)
            else:
                print(content)
        except Exception as e:
            print_styled(f"✗ Error reading config file: {e}", "red")
        
        print()


@cli.command()
@click.option("--tail", "-f", is_flag=True, help="Follow log file")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
@click.option("--module", "-m", help="Show logs for specific module")
@click.option("--level", "-l", help="Filter logs by level (e.g., INFO, DEBUG, ERROR)")
def logs(tail, lines, module, level):
    """View LOTUS logs"""
    
    log_dir = Path("data/logs")
    if not log_dir.exists():
        print_styled(f"\n✗ Log directory not found: {log_dir}\n", "red")
        return

    if module:
        log_file = log_dir / "modules" / f"{module}.log"
    else:
        log_file = log_dir / "nucleus.log"
    
    if not log_file.exists():
        print_styled(f"\n✗ Log file not found: {log_file}\n", "red")
        return
    
    # Base command for `tail`
    cmd = ["tail"]
    if tail:
        cmd.append("-f")
    else:
        cmd.extend(["-n", str(lines)])
    cmd.append(str(log_file))

    try:
        # Use subprocess.Popen for filtering, especially with `tail -f`
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print_styled(f"\n🌸 Showing logs from [bold cyan]{log_file.name}[/bold cyan]\n", "bold")

        # Read output line by line and filter
        for line in iter(process.stdout.readline, ''):
            if level and level.upper() not in line.upper():
                continue
            if RICH_AVAILABLE and console:
                # Basic rich formatting based on log level hint
                if "CRITICAL" in line:
                    console.print(line.strip(), style="bold red reverse")
                elif "ERROR" in line:
                    console.print(line.strip(), style="bold red")
                elif "WARNING" in line:
                    console.print(line.strip(), style="yellow")
                elif "INFO" in line:
                    console.print(line.strip(), style="green")
                elif "DEBUG" in line:
                    console.print(line.strip(), style="dim blue")
                else:
                    console.print(line.strip())
            else:
                print(line, end="")
            
            if not tail: # If not tailing, print and exit after processing relevant lines
                # This might need more complex logic to count filtered lines vs total lines
                pass

        # Handle any remaining stderr output
        stderr_output = process.stderr.read()
        if stderr_output:
            print_styled(f"\n[bold red]Error from tail command:[/bold red]\n{stderr_output}", "red")

    except FileNotFoundError:
        print_styled(f"\n✗ Command '{cmd[0]}' not found. Ensure it's in your PATH.\n", "red")
    except KeyboardInterrupt:
        print_styled("\n\n🌸 Log viewing ended.\n", "yellow")
    except Exception as e:
        print_styled(f"\n✗ Error viewing logs: {e}\n", "red")
    finally:
        if 'process' in locals() and process.poll() is None:
            process.terminate()
            process.wait(timeout=5) # Give it a moment to terminate gracefully
            if process.poll() is None:
                process.kill()


@cli.command()
def test():
    """Run system tests"""
    print_styled("\n🌸 Running LOTUS Tests\n", "bold cyan")
    
    # Run pytest
    try:
        import pytest
        # Use subprocess to run pytest for better control and output capture
        result = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests/", "--color=yes"], capture_output=True, text=True)
        
        if RICH_AVAILABLE and console:
            if result.returncode == 0:
                console.print(Panel("✓ All tests passed!", style="bold green"))
            else:
                console.print(Panel("✗ Some tests failed!", style="bold red"))
            console.print(result.stdout)
            if result.stderr:
                console.print(Text("Stderr during tests:", style="bold yellow"))
                console.print(result.stderr)
        else:
            print(result.stdout)
            if result.stderr:
                print("Stderr during tests:")
                print(result.stderr)
        
        sys.exit(result.returncode)

    except ImportError:
        print_styled("✗ pytest not installed", "red")
        print_styled("  Run: pip install pytest\n", "yellow")
        sys.exit(1)
    except Exception as e:
        print_styled(f"✗ An unexpected error occurred while running tests: {e}", "bold red")
        sys.exit(1)


@cli.command()
def doctor():
    """Run diagnostic checks"""
    print_styled("\n🌸 LOTUS System Diagnostic\n", "bold cyan")
    
    # Run diagnostic script
    diagnostic_script = Path(__file__).parent / "scripts" / "dev" / "validate_lotus.py" # Assuming diagnostic script is here based on project structure
    
    if diagnostic_script.exists():
        try:
            print_styled(f"  Running diagnostic script: [cyan]{diagnostic_script.name}[/cyan]\n", "dim")
            subprocess.run([sys.executable, str(diagnostic_script)], check=True)
            print_styled("\n✓ Diagnostics completed successfully.\n", "bold green")
        except subprocess.CalledProcessError:
            print_styled("\n✗ Diagnostics found issues. Please review output above.\n", "bold red")
        except Exception as e:
            print_styled(f"\n✗ An error occurred during diagnostics: {e}\n", "bold red")
    else:
        print_styled(f"✗ Diagnostic script not found at expected path: [yellow]{diagnostic_script}[/yellow]\n", "red")
        print_styled("  Please ensure 'scripts/dev/validate_lotus.py' exists.\n", "yellow")


@cli.command()
@click.argument("module_source") # Can be path, URL, or registry name
@click.option("--name", help="Module name (auto-detected if not provided)")
@click.option("--type", type=click.Choice(["capability", "integration", "personality"]), 
              help="Module type (e.g., 'capability', 'integration')")
@click.option("--force", is_flag=True, help="Force overwrite if module exists")
def install(module_source, name, type, force):
    """Install a module from a path, URL, or registry"""
    print_styled(f"\n🌸 Installing module from [bold cyan]{module_source}[/bold cyan]\n", "bold")
    
    # You'd integrate with your `scripts/install_module.py` here
    install_script = Path(__file__).parent / "scripts" / "install_module.py"
    
    if not install_script.exists():
        print_styled(f"✗ Installation script not found: {install_script}", "red")
        print_styled("  Please ensure 'scripts/install_module.py' exists.\n", "yellow")
        sys.exit(1)

    cmd = [sys.executable, str(install_script), module_source]
    if name:
        cmd.extend(["--name", name])
    if type:
        cmd.extend(["--type", type])
    if force:
        cmd.append("--force")

    try:
        print_styled(f"  Executing: {' '.join(cmd)}\n", "dim")
        subprocess.run(cmd, check=True)
        print_styled(f"\n✓ Module installed successfully!\n", "bold green")
    except subprocess.CalledProcessError as e:
        print_styled(f"\n✗ Module installation failed: {e}", "bold red")
        print_styled(f"  See error output above for details.\n", "yellow")
    except Exception as e:
        print_styled(f"\n✗ An unexpected error occurred during installation: {e}", "bold red")
    
    print_styled("  Remember to restart LOTUS if you're not using hot-reloading for new modules.\n", "dim")


# New script for real-time event flow testing
@cli.command("test-event-flow")
@click.argument("message")
@click.option("--channels", "-c", default="perception.*,cognition.*,action.*,memory.*,system.*", 
              help="Comma-separated list of channel patterns to subscribe to. Use '*' for all.")
@click.option("--timeout", "-t", default=30.0, type=float, help="Timeout in seconds to wait for events.")
def test_event_flow(message: str, channels: str, timeout: float):
    """
    Send a message and display real-time event flow from the message bus.
    Useful for debugging.
    """
    from lib.message_bus import MessageBus

    print_styled("\n🌸 LOTUS Event Flow Monitor\n", "bold cyan")
    print_styled(f"  Message: [bold yellow]'{message}'[/bold yellow]", highlight=False)
    print_styled(f"  Subscribing to: [cyan]'{channels}'[/cyan]", highlight=False)
    print_styled(f"  Timeout: [cyan]{timeout} seconds[/cyan]\n", highlight=False)

    bus = MessageBus()
    event_buffer: List[Tuple[str, Dict[str, Any]]] = []
    
    async def _event_collector(channel: str, data: Dict[str, Any]):
        event_buffer.append((channel, data))
        # Log to console immediately for real-time feedback
        timestamp = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        payload_preview = ""
        if "data" in data and isinstance(data["data"], dict):
            # For specific events, show relevant parts
            if channel == "perception.user_input":
                payload_preview = f"text='{data['data'].get('text', '')[:50]}...'"
            elif channel == "cognition.thought":
                thought_data = data['data'].get('thought', {})
                understanding = thought_data.get('understanding', '')
                plan = thought_data.get('plan', [])
                payload_preview = f"understanding='{understanding[:50]}...', plan='{plan[0] if plan else ''}'"
            elif channel == "cognition.tool_call":
                payload_preview = f"tool='{data['data'].get('tool')}', params={data['data'].get('params')}"
            elif channel == "action.respond":
                payload_preview = f"content='{data['data'].get('content', '')[:70]}...'"
            elif "message" in data["data"]: # Generic message
                payload_preview = f"message='{data['data'].get('message', '')[:50]}...'"
            elif "content" in data["data"]: # Generic content
                payload_preview = f"content='{data['data'].get('content', '')[:50]}...'"
            else: # Fallback for other dicts
                payload_preview = f"keys={list(data['data'].keys())}"
        elif isinstance(data["data"], str):
             payload_preview = f"'{data['data'][:50]}...'"
        
        source_mod = data.get("source", "cli")
        if RICH_AVAILABLE and console:
            console.print(f"[dim blue]{timestamp}[/dim blue] [bold purple]{source_mod}[/bold purple] -> [cyan]{channel}[/cyan] ({payload_preview})", highlight=False)
        else:
            print(f"{timestamp} {source_mod} -> {channel} ({payload_preview})")


    async def _run_event_test():
        try:
            await bus.connect()
            
            # Subscribe to specified channels
            patterns = [p.strip() for p in channels.split(',')]
            for pattern in patterns:
                await bus.subscribe(pattern, _event_collector)
            
            print_styled("\n[bold yellow]--- PUBLISHING MESSAGE ---[/bold yellow]")
            user_payload = {"text": message, "context": {"source": "cli-test-event-flow"}}
            await bus.publish("perception.user_input", user_payload)
            print_styled("[bold yellow]--------------------------[/bold yellow]\n")

            start_time = time.time()
            while (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1) # Keep event loop running
            
            print_styled(f"\n[bold yellow]--- TIMEOUT REACHED ({timeout}s) ---[/bold yellow]")
            print_styled(f"[bold green]Total events captured:[/bold green] {len(event_buffer)}")

        except asyncio.CancelledError:
            print_styled("\n[yellow]Event flow test cancelled.[/yellow]")
        except Exception as e:
            print_styled(f"\n[bold red]Error during event flow test: {e}[/bold red]", highlight=False)
        finally:
            print_styled("\n[dim]Disconnecting from message bus...[/dim]")
            if bus.connected:
                for pattern in patterns:
                    try:
                        await bus.unsubscribe(pattern, _event_collector)
                    except Exception:
                        pass # Ignore unsubscribe errors during cleanup
                await bus.disconnect()
            print_styled("[dim]Disconnected.[/dim]")

    asyncio.run(_run_event_test())


if __name__ == "__main__":
    cli()