#!/usr/bin/env python3
"""
LOTUS API Server Launcher

Start the FastAPI server for AetherAI.

Usage:
    python run_api.py                    # Development mode
    python run_api.py --production       # Production mode with Gunicorn
"""

import os
import sys
import argparse


def run_development():
    """Run in development mode with uvicorn"""
    import uvicorn

    print("🚀 Starting LOTUS API in DEVELOPMENT mode...")
    print("📍 API: http://localhost:8080")
    print("📖 Docs: http://localhost:8080/docs")
    print()

    uvicorn.run(
        "lotus.api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )


def run_production():
    """Run in production mode with gunicorn"""
    import subprocess

    print("🚀 Starting LOTUS API in PRODUCTION mode...")
    print("📍 API: http://localhost:8080")
    print()

    subprocess.run([
        "gunicorn",
        "lotus.api.main:app",
        "--workers", "4",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--bind", "0.0.0.0:8080",
        "--timeout", "300",
        "--access-logfile", "-",
        "--error-logfile", "-"
    ])


def main():
    parser = argparse.ArgumentParser(description="LOTUS API Server")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run in production mode with Gunicorn"
    )

    args = parser.parse_args()

    # Set Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    if args.production:
        run_production()
    else:
        run_development()


if __name__ == "__main__":
    main()
