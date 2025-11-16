"""
Chat Routes

Handles chat completions with streaming support.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..schemas import ChatRequest, ChatMessage
from ..services.streaming import sse_stream
from ..main import get_adapter
from ...lib.logging import get_logger


logger = get_logger("lotus.api.chat")
router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    Create a chat completion

    Supports streaming via SSE for real-time responses.

    **Request Body:**
    ```json
    {
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "model": "auto",  // or "apriel", "grok", "claude"
        "stream": true,
        "temperature": 0.7,
        "max_tokens": 4096
    }
    ```

    **Response (SSE Stream):**
    ```
    data: {"type": "thinking", "content": "Analyzing request..."}
    data: {"type": "content", "content": "Hello! "}
    data: {"type": "content", "content": "How can I help?"}
    data: {"type": "model", "model": "apriel", "tokens_used": 42}
    data: [DONE]
    ```
    """
    try:
        adapter = get_adapter()

        # Convert Pydantic models to dicts
        messages = [msg.model_dump() for msg in request.messages]

        # Select model
        model_id = adapter.select_model(messages, request.model)

        logger.info(f"Chat completion request: model={model_id}, messages={len(messages)}")

        # Stream completion
        event_generator = adapter.stream_completion(
            messages=messages,
            model_id=model_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # Convert to SSE format
        sse_generator = sse_stream(event_generator)

        return StreamingResponse(
            sse_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",  # CORS for SSE
            }
        )

    except Exception as e:
        logger.error(f"Chat completion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/models")
async def list_chat_models():
    """
    List available chat models

    **Response:**
    ```json
    {
        "models": [
            {
                "id": "apriel",
                "name": "Apriel 1.5",
                "status": "online",
                "capabilities": ["chat", "code", "analysis"],
                "hosted": "self",
                "description": "AetherPro flagship model"
            },
            ...
        ]
    }
    ```
    """
    try:
        adapter = get_adapter()
        models = adapter.get_all_models()

        return {"models": models}

    except Exception as e:
        logger.error(f"List models error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
