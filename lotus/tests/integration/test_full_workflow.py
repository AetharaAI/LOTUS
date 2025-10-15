#!/usr/bin/env python3
"""
LOTUS Test & Demo Script

This script demonstrates LOTUS's capabilities:
1. Boot the system
2. Test core modules (memory, providers, perception)
3. Send test events
4. Show module communication
5. Display stats

Usage:
    python test_lotus.py
"""

import asyncio
import sys
from pathlib import Path

# Add lotus to path
sys.path.insert(0, str(Path(__file__).parent))

from nucleus import Nucleus
import time


async def test_memory_system(nucleus: Nucleus):
    """Test the memory system"""
    print("\n" + "="*60)
    print("Testing Memory System")
    print("="*60)
    
    # Store a memory
    print("\n1. Storing a memory in L1 (working memory)...")
    await nucleus.message_bus.publish("memory.store", {
        "content": "LOTUS is an AI Operating System",
        "metadata": {
            "type": "fact",
            "importance": 0.9
        },
        "tier": "L1"
    })
    
    await asyncio.sleep(1)
    
    # Store another memory
    print("2. Storing a memory in L3 (long-term memory)...")
    await nucleus.message_bus.publish("memory.store", {
        "content": "The user loves coding in Python",
        "metadata": {
            "type": "preference",
            "importance": 0.7
        },
        "tier": "L3"
    })
    
    await asyncio.sleep(1)
    
    # Retrieve memories
    print("3. Retrieving memories...")
    await nucleus.message_bus.publish("memory.retrieve", {
        "query": "LOTUS",
        "tier": "all",
        "limit": 5
    })
    
    await asyncio.sleep(2)
    print("✔ Memory system test complete!")


async def test_provider_system(nucleus: Nucleus):
    """Test the LLM provider system"""
    print("\n" + "="*60)
    print("Testing Provider System")
    print("="*60)
    
    # List available providers
    print("\n1. Listing available providers...")
    # In a real system, we'd call the tool, but for demo we'll just publish
    
    # Request a completion (this would fail without API keys, but shows the flow)
    print("2. Requesting LLM completion (will use fallback if API keys not configured)...")
    await nucleus.message_bus.publish("llm.complete", {
        "prompt": "Say hello to LOTUS!",
        "provider": "auto",
        "max_tokens": 100,
        "temperature": 0.7
    })
    
    await asyncio.sleep(2)
    print("✔ Provider system test complete!")


async def test_perception_system(nucleus: Nucleus):
    """Test the perception system"""
    print("\n" + "="*60)
    print("Testing Perception System")
    print("="*60)
    
    # Start watching a test directory
    print("\n1. Starting file watcher on current directory...")
    await nucleus.message_bus.publish("perception.start_watching", {
        "path": str(Path.cwd())
    })
    
    await asyncio.sleep(1)
    
    print("2. Perception system is now monitoring:")
    print("   - File system changes")
    print("   - Clipboard content")
    print("   - Working context")
    
    await asyncio.sleep(2)
    print("✔ Perception system test complete!")


async def demonstrate_module_communication(nucleus: Nucleus):
    """Demonstrate event-driven communication"""
    print("\n" + "="*60)
    print("Demonstrating Module Communication")
    print("="*60)
    
    print("\nEvent-driven architecture in action:")
    print("1. Memory module listening on 'memory.*'")
    print("2. Provider module listening on 'llm.*'")
    print("3. Perception module listening on 'file.*', 'clipboard.*'")
    print("4. All modules can publish events that others receive")
    
    print("\nExample flow:")
    print("  User edits file â†' Perception detects â†' Publishes 'file.modified'")
    print("  â†' Reasoning sees change â†' Requests memory â†' Gets context")
    print("  â†' Reasoning decides action â†' Calls LLM â†' Generates response")
    
    await asyncio.sleep(3)


async def show_system_stats(nucleus: Nucleus):
    """Show system statistics"""
    print("\n" + "="*60)
    print("System Statistics")
    print("="*60)
    
    print(f"\nNucleus:")
    print(f"  Uptime: {(time.time() - nucleus.start_time.timestamp()):.1f}s" if nucleus.start_time else "  Not started")
    print(f"  Modules loaded: {len(nucleus.modules)}")
    print(f"  Load order: {', '.join(nucleus.load_order)}")
    
    print(f"\nModules:")
    for name, module in nucleus.modules.items():
        print(f"  ✔ {name}")
        print(f"     Type: {module.metadata.type}")
        print(f"     Priority: {module.metadata.priority}")
    
    await asyncio.sleep(1)


async def main():
    """Main test flow"""
    print("ðŸŒ¸" + "="*58 + "ðŸŒ¸")
    print("   LOTUS AI Operating System - Test & Demo")
    print("ðŸŒ¸" + "="*58 + "ðŸŒ¸")
    
    try:
        # Initialize nucleus
        print("\nInitializing LOTUS...")
        nucleus = Nucleus()
        
        # Boot the system
        await nucleus.boot()
        
        print("\n" + "âœ"*30)
        print("LOTUS is online! Running tests...\n")
        await asyncio.sleep(2)
        
        # Run tests
        await demonstrate_module_communication(nucleus)
        await test_memory_system(nucleus)
        await test_provider_system(nucleus)
        await test_perception_system(nucleus)
        await show_system_stats(nucleus)
        
        # Keep running for a bit to see events
        print("\n" + "="*60)
        print("Monitoring for events (10 seconds)...")
        print("Try: copying text, modifying files in watched directories")
        print("="*60)
        
        await asyncio.sleep(10)
        
        # Shutdown
        print("\n\nShutting down LOTUS...")
        await nucleus.shutdown()
        
        print("\nðŸŒ¸ Test complete! LOTUS is offline.")
        
    except KeyboardInterrupt:
        print("\n\nâš ï¸ Interrupted! Shutting down...")
        if 'nucleus' in locals():
            await nucleus.shutdown()
    except Exception as e:
        print(f"\n\nâŒ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'nucleus' in locals():
            await nucleus.shutdown()


if __name__ == "__main__":
    print("\nâ„¹ï¸  Note: Some tests may fail if dependencies (Redis, PostgreSQL) are not running")
    print("â„¹ï¸  API keys not required for this demo - fallbacks will be used\n")
    
    asyncio.run(main())