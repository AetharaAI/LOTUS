"""
System Routes

Health checks, metrics, and system status.
"""

from fastapi import APIRouter, HTTPException

from ..schemas import HealthResponse
from ..adapter import get_adapter
from ...lib.logging import get_logger


logger = get_logger("lotus.api.system")
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    System health check

    Returns:
    - Overall status
    - Model statuses
    - Service statuses (Redis, MongoDB, Weaviate)
    - Uptime
    - Version
    """
    try:
        adapter = get_adapter()
        stats = adapter.get_stats()

        # Get model statuses
        models = adapter.get_all_models()
        model_statuses = {m["id"]: m["status"] for m in models}

        # Get service statuses
        # TODO: Actually check service health
        service_statuses = {
            "redis": "connected",
            "mongodb": "connected",
            "weaviate": "connected"
        }

        # Determine overall status
        all_models_online = all(s == "online" for s in model_statuses.values())
        all_services_ok = all(s == "connected" for s in service_statuses.values())

        if all_models_online and all_services_ok:
            overall_status = "healthy"
        elif any(s == "online" for s in model_statuses.values()):
            overall_status = "degraded"
        else:
            overall_status = "down"

        return HealthResponse(
            status=overall_status,
            models=model_statuses,
            services=service_statuses,
            uptime=stats.get("uptime", 0),
            version="1.0.0"
        )

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get usage statistics

    Returns:
    - Total requests
    - Model usage breakdown
    - Token usage by model
    - Uptime
    """
    try:
        adapter = get_adapter()
        stats = adapter.get_stats()

        return stats

    except Exception as e:
        logger.error(f"Get stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/version")
async def get_version():
    """Get API version"""
    return {
        "version": "1.0.0",
        "name": "LOTUS API",
        "motto": "The American Standard for Sovereign AI Infrastructure 🇺🇸"
    }


@router.get("/lotus/status")
async def get_lotus_status():
    """
    Get complete LOTUS system status

    Returns detailed information about:
    - Nucleus health and uptime
    - All loaded modules and their status
    - Infrastructure (Redis, Memory tiers, PostgreSQL, ChromaDB)
    - Usage statistics
    - Memory tier stats (L1-L4)
    """
    try:
        adapter = get_adapter()
        status = adapter.get_system_status()
        return status

    except Exception as e:
        logger.error(f"Get LOTUS status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lotus/modules")
async def get_lotus_modules():
    """
    Get all loaded LOTUS modules

    Returns module names, types, versions, and health status
    """
    try:
        adapter = get_adapter()
        status = adapter.get_system_status()

        return {
            "modules": status.get("modules", {}),
            "total_modules": len(status.get("modules", {}))
        }

    except Exception as e:
        logger.error(f"Get LOTUS modules error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
