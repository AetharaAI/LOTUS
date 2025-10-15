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
from typing import Optional
import subprocess

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
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

# Initialize console
if RICH_AVAILABLE:
    console = Console()
else:
    console = None


def print_styled(text: str, style: str = ""):
    """Print with style if rich is available"""
    if RICH_AVAILABLE and console:
        console.print(text, style=style)
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
    import time
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
            table.add_row("Uptime:", status_data.get("uptime", "Unknown"))
            table.add_row("Modules:", str(status_data.get("modules_count", "?")))
            table.add_row("Memory:", status_data.get("memory", "Unknown"))
            table.add_row("CPU:", status_data.get("cpu", "Unknown"))
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
            pass
        
        # Get module count from state file
        state_file = Path("data/state/module_state.json")
        if state_file.exists():
            try:
                with open(state_file) as f:
                    module_state = json.load(f)
                    status["modules_count"] = len(module_state.get("active_modules", []))
            except:
                pass
        
    except OSError:
        pass
    
    return status


@cli.command()
@click.option("--interactive", "-i", is_flag=True, help="Start interactive chat session")
@click.argument("message", required=False)
def chat(interactive, message):
    """Chat with LOTUS"""
    
    if interactive:
        # Start interactive session
        print_styled("\n🌸 LOTUS Interactive Chat", "bold cyan")
        print_styled("Type 'exit' or 'quit' to end session\n", "dim")
        
        while True:
            try:
                user_input = input("You: ")
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    print_styled("\n🌸 Goodbye!\n", "cyan")
                    break
                
                if not user_input.strip():
                    continue
                
                # Send to LOTUS and get response
                response = send_message_to_lotus(user_input)
                print_styled(f"\nLOTUS: {response}\n", "green")
                
            except KeyboardInterrupt:
                print_styled("\n\n🌸 Chat ended\n", "yellow")
                break
            except Exception as e:
                print_styled(f"\n✗ Error: {e}\n", "red")
    
    elif message:
        # Single message
        response = send_message_to_lotus(message)
        print_styled(f"\n🌸 LOTUS: {response}\n", "green")
    
    else:
        print_styled("\n✗ Please provide a message or use --interactive\n", "red")
        print_styled("Examples:", "cyan")
        print_styled("  lotus chat 'Hello LOTUS'", "dim")
        print_styled("  lotus chat --interactive\n", "dim")


def send_message_to_lotus(message: str) -> str:
    """Send message to running LOTUS instance"""
    # TODO: Implement via Redis pub/sub
    # For now, return placeholder
    return "I received your message! (Full chat implementation coming soon)"


@cli.command()
@click.option("--type", "-t", type=click.Choice(["all", "core", "capability", "integration"]), 
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
        table.add_column("Status", style="magenta")
        
        for module in modules_list:
            status = "✓ Active" if module.get("active") else "○ Inactive"
            table.add_row(
                module["name"],
                module["type"],
                module.get("version", "?"),
                status
            )
        
        console.print(table)
    else:
        for module in modules_list:
            status = "[ACTIVE]" if module.get("active") else "[INACTIVE]"
            print(f"{status} {module['name']} ({module['type']}) v{module.get('version', '?')}")
    
    print()


def discover_modules(filter_type: str = "all") -> list:
    """Discover installed modules"""
    modules = []
    modules_dir = Path("modules")
    
    if not modules_dir.exists():
        return modules
    
    # Scan module directories
    for type_dir in ["core_modules", "capability_modules", "integration_modules"]:
        type_path = modules_dir / type_dir
        if not type_path.exists():
            continue
        
        module_type = type_dir.replace("_modules", "")
        
        if filter_type != "all" and filter_type != module_type:
            continue
        
        for module_dir in type_path.iterdir():
            if not module_dir.is_dir():
                continue
            
            manifest = module_dir / "manifest.yaml"
            if not manifest.exists():
                continue
            
            # Parse manifest
            import yaml
            with open(manifest) as f:
                manifest_data = yaml.safe_load(f)
            
            modules.append({
                "name": manifest_data.get("name", module_dir.name),
                "type": module_type,
                "version": manifest_data.get("version", "?"),
                "active": True  # TODO: Check actual status
            })
    
    return modules


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
        subprocess.run([editor, str(config_file)])
    else:
        # Display config
        print_styled(f"\n🌸 Config for {module_name}\n", "bold cyan")
        
        with open(config_file) as f:
            content = f.read()
        
        if RICH_AVAILABLE and console:
            syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            print(content)
        
        print()


@cli.command()
@click.option("--tail", "-f", is_flag=True, help="Follow log file")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
@click.option("--module", "-m", help="Show logs for specific module")
def logs(tail, lines, module):
    """View LOTUS logs"""
    
    if module:
        log_file = Path(f"data/logs/modules/{module}.log")
    else:
        log_file = Path("data/logs/nucleus.log")
    
    if not log_file.exists():
        print_styled(f"\n✗ Log file not found: {log_file}\n", "red")
        return
    
    if tail:
        # Follow log file
        try:
            subprocess.run(["tail", "-f", str(log_file)])
        except KeyboardInterrupt:
            print()
    else:
        # Show last N lines
        with open(log_file) as f:
            lines_list = f.readlines()
            
            print_styled(f"\n🌸 Last {lines} lines of {log_file.name}\n", "bold cyan")
            
            for line in lines_list[-lines:]:
                print(line, end="")
            
            print()


@cli.command()
def test():
    """Run system tests"""
    print_styled("\n🌸 Running LOTUS Tests\n", "bold cyan")
    
    # Run pytest
    try:
        import pytest
        exit_code = pytest.main(["-v", "tests/", "--color=yes"])
        sys.exit(exit_code)
    except ImportError:
        print_styled("✗ pytest not installed", "red")
        print_styled("  Run: pip install pytest\n", "yellow")
        sys.exit(1)


@cli.command()
def doctor():
    """Run diagnostic checks"""
    print_styled("\n🌸 LOTUS System Diagnostic\n", "bold cyan")
    
    # Run diagnostic script
    diagnostic_script = Path(__file__).parent / "session7_diagnostic.py"
    
    if diagnostic_script.exists():
        subprocess.run([sys.executable, str(diagnostic_script)])
    else:
        print_styled("✗ Diagnostic script not found", "red")
        print_styled(f"  Expected: {diagnostic_script}\n", "yellow")


@cli.command()
@click.argument("module_path")
@click.option("--name", help="Module name (auto-detected if not provided)")
def install(module_path, name):
    """Install a module"""
    print_styled(f"\n🌸 Installing module from {module_path}\n", "bold cyan")
    
    # TODO: Implement module installation
    print_styled("✗ Module installation not yet implemented", "yellow")
    print_styled("  Coming soon!\n", "dim")


if __name__ == "__main__":
    cli()