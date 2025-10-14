#!/usr/bin/env python3
"""
LOTUS Command Line Interface

Provides commands for managing the LOTUS system:
- start: Start LOTUS
- stop: Stop LOTUS
- restart: Restart LOTUS
- status: Check system status
- install: Install a module
- list: List installed modules
- logs: View logs
- chat: Interactive chat with LOTUS
"""

import click
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """LOTUS AI Operating System - Command Line Interface"""
    pass


@cli.command()
@click.option("--config", default="config/system.yaml", help="Config file path")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def start(config, debug):
    """Start the LOTUS system"""
    click.echo("🌸 Starting LOTUS...")
    
    # Import here to avoid circular imports
    from nucleus import Nucleus
    
    # Create and run nucleus
    nucleus = Nucleus(config_path=config)
    
    try:
        asyncio.run(nucleus.run())
    except KeyboardInterrupt:
        click.echo("\n🌸 LOTUS stopped")


@cli.command()
def stop():
    """Stop the LOTUS system"""
    click.echo("🌸 Stopping LOTUS...")
    # TODO: Implement graceful stop via PID file
    click.echo("   Not implemented yet. Use Ctrl+C to stop.")


@cli.command()
def restart():
    """Restart the LOTUS system"""
    click.echo("🌸 Restarting LOTUS...")
    # TODO: Implement restart
    click.echo("   Not implemented yet.")


@cli.command()
def status():
    """Check LOTUS system status"""
    click.echo("🌸 LOTUS Status")
    click.echo()
    
    # Check if running
    # TODO: Check PID file and process
    click.echo("   Status: Unknown")
    click.echo("   Uptime: N/A")
    click.echo("   Modules: N/A")
    click.echo()
    click.echo("   Use 'lotus start' to start the system")


@cli.command()
@click.argument("module_name")
@click.option("--local", type=click.Path(), help="Install from local path")
@click.option("--github", help="Install from GitHub (user/repo)")
def install(module_name, local, github):
    """Install a module"""
    click.echo(f"🌸 Installing module: {module_name}")
    
    if local:
        click.echo(f"   Source: Local ({local})")
    elif github:
        click.echo(f"   Source: GitHub ({github})")
    else:
        click.echo(f"   Source: Official registry")
    
    # TODO: Implement module installation
    click.echo("   Not implemented yet.")


@cli.command()
@click.option("--type", type=click.Choice(["all", "core", "capability", "integration"]), 
              default="all", help="Filter by module type")
def list(type):
    """List installed modules"""
    click.echo(f"🌸 Installed Modules ({type})")
    click.echo()
    
    modules_dir = Path("modules")
    
    if type in ["all", "core"]:
        click.echo("   Core Modules:")
        core_dir = modules_dir / "core_modules"
        if core_dir.exists():
            for module in core_dir.iterdir():
                if module.is_dir() and not module.name.startswith("."):
                    click.echo(f"     • {module.name}")
        click.echo()
    
    if type in ["all", "capability"]:
        click.echo("   Capability Modules:")
        cap_dir = modules_dir / "capability_modules"
        if cap_dir.exists():
            for module in cap_dir.iterdir():
                if module.is_dir() and not module.name.startswith("."):
                    click.echo(f"     • {module.name}")
        click.echo()
    
    if type in ["all", "integration"]:
        click.echo("   Integration Modules:")
        int_dir = modules_dir / "integration_modules"
        if int_dir.exists():
            for module in int_dir.iterdir():
                if module.is_dir() and not module.name.startswith("."):
                    click.echo(f"     • {module.name}")


@cli.command()
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
def logs(follow, lines):
    """View system logs"""
    click.echo(f"🌸 LOTUS Logs (last {lines} lines)")
    click.echo()
    
    log_file = Path("data/logs").glob("lotus_*.log")
    log_files = sorted(log_file, reverse=True)
    
    if not log_files:
        click.echo("   No log files found")
        return
    
    latest_log = log_files[0]
    click.echo(f"   Log file: {latest_log}")
    click.echo()
    
    # Read last N lines
    with open(latest_log, 'r') as f:
        all_lines = f.readlines()
        for line in all_lines[-lines:]:
            click.echo(f"   {line.rstrip()}")
    
    if follow:
        # TODO: Implement tail -f behavior
        click.echo("\n   Follow mode not implemented yet. Use: tail -f data/logs/*.log")


@cli.command()
def chat():
    """Interactive chat with LOTUS"""
    click.echo("🌸 LOTUS Interactive Chat")
    click.echo("   Type 'exit' to quit\n")
    
    # TODO: Implement interactive chat
    # For now, just a placeholder
    
    click.echo("   Chat interface not implemented yet.")
    click.echo("   Start LOTUS with 'lotus start' and use the API or SDK.")


@cli.command()
@click.argument("module_name")
@click.option("--type", default="capability", help="Module type")
def create(module_name, type):
    """Create a new module from template"""
    click.echo(f"🌸 Creating new module: {module_name}")
    click.echo(f"   Type: {type}")
    
    # TODO: Implement module template generation
    click.echo("   Not implemented yet. See docs/MODULE_DEVELOPMENT.md")


if __name__ == "__main__":
    cli()