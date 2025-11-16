"""
LOTUS API - Main FastAPI Application

The API layer for AetherAI - The American Standard for Sovereign AI.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import chat, models, system, memory
from .services.lotus_adapter import LOTUSAdapter
from ..lib.config import Config
from ..lib.logging import get_logger


logger = get_logger("lotus.api")


# Global adapter instance
adapter: LOTUSAdapter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting LOTUS API...")

    global adapter

    # Load configuration
    config = Config("config/system.yaml")
    logger.info("Configuration loaded")

    # Initialize LOTUS adapter
    adapter = LOTUSAdapter(config)
    await adapter.initialize()
    logger.info("LOTUS adapter initialized")

    logger.info("✅ LOTUS API ready!")

    yield

    # Shutdown
    logger.info("📴 Shutting down LOTUS API...")
    logger.info("👋 LOTUS API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="LOTUS API",
    description="The American Standard for Sovereign AI Infrastructure",
    version="1.0.0",
    lifespan=lifespan
)


# CORS Configuration
# In production, restrict to your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://aetherai.aetherpro.tech",
        "https://*.vercel.app"  # Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add response time header to all requests"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(models.router, prefix="/api", tags=["models"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(memory.router, prefix="/api", tags=["memory"])


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "LOTUS API",
        "description": "The American Standard for Sovereign AI Infrastructure",
        "version": "1.0.0",
        "status": "operational",
        "motto": "Built on US infrastructure. Powered by American innovation. 🇺🇸"
    }


# Health check endpoint
@app.get("/health")
async def health():
    """Simple health check"""
    return {"status": "healthy"}


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


def get_adapter() -> LOTUSAdapter:
    """Get the global adapter instance"""
    if adapter is None:
        raise RuntimeError("LOTUS adapter not initialized")
    return adapter
