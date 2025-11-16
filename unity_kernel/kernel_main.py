#!/usr/bin/env python3
"""
UnityKernel Main Entry Point

Run this to start the kernel.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from kernel import UnityKernel


async def main():
    """Main entry point"""
    # Create kernel
    kernel = UnityKernel("config/system.yaml")

    # Run kernel (boots, runs, and shuts down on Ctrl+C)
    await kernel.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
