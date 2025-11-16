"""
Models Routes

Model management and information endpoints.
"""

from fastapi import APIRouter, HTTPException

from ..schemas import ModelsResponse, ModelInfo
from ..adapter import get_adapter
from ...lib.logging import get_logger


logger = get_logger("lotus.api.models")
router = APIRouter()


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    Get all available models

    Returns detailed information about each model including:
    - Status (online/offline/degraded)
    - Capabilities
    - Hosting location
    - Cost per million tokens
    - Description
    """
    try:
        adapter = get_adapter()
        models = adapter.get_all_models()

        return ModelsResponse(models=[ModelInfo(**m) for m in models])

    except Exception as e:
        logger.error(f"Get models error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """
    Get information about a specific model

    **Path Parameters:**
    - `model_id`: Model identifier (apriel, grok, or claude)
    """
    try:
        adapter = get_adapter()

        # Validate model_id
        if model_id not in ["apriel", "grok", "claude"]:
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {model_id}"
            )

        model_info = adapter.get_model_info(model_id)

        return ModelInfo(**model_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get model error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
