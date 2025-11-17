"""
LOTUS Adapter Service

Connects FastAPI to LOTUS core system.
Handles model selection, routing, and streaming.
"""

import asyncio
import json
from typing import AsyncIterator, List, Dict, Any, Optional
from datetime import datetime

from ...lib.providers import ProviderManager, LLMResponse
from ...lib.config import Config
from ...lib.logging import get_logger


logger = get_logger("lotus.api.adapter")


class LOTUSAdapter:
    """
    Adapter between FastAPI and LOTUS core

    Responsibilities:
    - Model selection and routing
    - Streaming management
    - Context building
    - Memory integration
    """

    def __init__(self, config: Config):
        """Initialize adapter with LOTUS config"""
        self.config = config
        self.logger = logger

        # Initialize provider manager
        self.provider_manager = ProviderManager(config)

        # Model capabilities mapping
        self.model_capabilities = {
            "apriel": {
                "name": "Apriel 1.5",
                "capabilities": ["chat", "code", "analysis", "general"],
                "hosted": "self",
                "cost_per_1m": 0.0,  # Self-hosted
                "description": "AetherPro flagship model - self-hosted for sovereignty"
            },
            "grok": {
                "name": "Grok-2",
                "capabilities": ["reasoning", "realtime", "analysis", "planning"],
                "hosted": "xai",
                "cost_per_1m": 5.0,  # xAI pricing
                "description": "Real-time reasoning specialist powered by xAI"
            },
            "claude": {
                "name": "Claude Sonnet 4.5",
                "capabilities": ["vision", "safety", "compliance", "analysis"],
                "hosted": "anthropic",
                "cost_per_1m": 15.0,  # Anthropic pricing
                "description": "Vision and safety specialist from Anthropic"
            }
        }

        # Stats tracking
        self.stats = {
            "total_requests": 0,
            "model_usage": {
                "apriel": 0,
                "grok": 0,
                "claude": 0
            },
            "tokens_used": {
                "apriel": 0,
                "grok": 0,
                "claude": 0
            }
        }

    async def initialize(self):
        """Initialize provider manager and connections"""
        await self.provider_manager.initialize()
        self.logger.info("LOTUS adapter initialized")

    def select_model(self, messages: List[Dict], requested_model: str = "auto") -> str:
        """
        Select appropriate model based on request

        Args:
            messages: Conversation history
            requested_model: User's model preference

        Returns:
            Model ID to use
        """
        # If user explicitly requests a model, use it
        if requested_model in ["apriel", "grok", "claude"]:
            self.logger.info(f"Using user-requested model: {requested_model}")
            return requested_model

        # Auto-routing based on context
        last_message = messages[-1]["content"].lower() if messages else ""

        # Vision tasks -> Claude
        vision_keywords = ["image", "screenshot", "picture", "photo", "analyze this screen", "what do you see"]
        if any(keyword in last_message for keyword in vision_keywords):
            self.logger.info("Auto-routed to Claude (vision task)")
            return "claude"

        # Complex reasoning tasks -> Grok
        reasoning_keywords = [
            "analyze", "explain why", "reason about", "think through",
            "step by step", "break down", "compare", "evaluate"
        ]
        if any(keyword in last_message for keyword in reasoning_keywords):
            self.logger.info("Auto-routed to Grok (reasoning task)")
            return "grok"

        # Default to Apriel (cheapest, self-hosted, good for general use)
        self.logger.info("Auto-routed to Apriel (general task)")
        return "apriel"

    async def stream_completion(
        self,
        messages: List[Dict],
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream chat completion from selected model

        Yields:
            Dict chunks with 'type', 'content', 'model', etc.
        """
        self.stats["total_requests"] += 1
        self.stats["model_usage"][model_id] += 1

        try:
            # Map model_id to provider
            provider_map = {
                "apriel": "ollama",  # Using Ollama as proxy for vLLM
                "grok": "xai",
                "claude": "anthropic"
            }

            provider_name = provider_map.get(model_id, "ollama")

            # Yield thinking indicator
            yield {
                "type": "thinking",
                "content": f"Routing to {self.model_capabilities[model_id]['name']}..."
            }

            await asyncio.sleep(0.1)  # Brief pause for UX

            # Convert messages to prompt format
            prompt = self._build_prompt(messages)

            # Stream from provider
            # Note: This is simplified - real implementation would use actual streaming
            response = await self.provider_manager.complete(
                prompt=prompt,
                provider=provider_name,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Track tokens
            self.stats["tokens_used"][model_id] += response.tokens_used

            # Simulate streaming by chunking response
            content = response.text
            chunk_size = 50  # Characters per chunk

            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield {
                    "type": "content",
                    "content": chunk
                }
                await asyncio.sleep(0.05)  # Smooth streaming

            # Yield model info
            yield {
                "type": "model",
                "model": model_id,
                "tokens_used": response.tokens_used
            }

        except Exception as e:
            self.logger.error(f"Error streaming from {model_id}: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }

    def _build_prompt(self, messages: List[Dict]) -> str:
        """
        Build prompt from message history

        Args:
            messages: List of {role, content} dicts

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a model"""
        if model_id not in self.model_capabilities:
            raise ValueError(f"Unknown model: {model_id}")

        info = self.model_capabilities[model_id].copy()
        info["id"] = model_id

        # Check if provider is initialized
        provider_map = {
            "apriel": "ollama",
            "grok": "xai",
            "claude": "anthropic"
        }

        provider_name = provider_map.get(model_id)
        if provider_name in self.provider_manager.providers:
            info["status"] = "online"
        else:
            info["status"] = "offline"

        return info

    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get info for all models"""
        return [self.get_model_info(mid) for mid in self.model_capabilities.keys()]

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            **self.stats,
            "uptime": 0,  # TODO: Track actual uptime
            "version": "1.0.0"
        }
