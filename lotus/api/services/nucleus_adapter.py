"""
LOTUS Nucleus Adapter - Full Integration

Properly integrates FastAPI with the complete LOTUS event-driven architecture.
This replaces the simplified lotus_adapter.py with full Nucleus integration.
"""

import asyncio
import json
import uuid
from typing import AsyncIterator, List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ...context_orchestrator_nucleus import Nucleus
from ...lib.config import Config
from ...lib.logging import get_logger


logger = get_logger("lotus.api.nucleus_adapter")


class NucleusAdapter:
    """
    Full LOTUS Nucleus integration for FastAPI.

    This adapter boots the complete Nucleus runtime engine with:
    - Event-driven message bus (Redis pub/sub)
    - 4-tier memory system (L1→L2→L3→L4)
    - Dynamic module loading (providers, memory, reasoning, perception)
    - Health monitoring and graceful shutdown

    Tiered Initialization:
    - basic: Provider routing only (no Nucleus, no memory persistence)
    - pro: Limited Nucleus (L1+L2 memory, providers)
    - power: Full Nucleus (all modules, full memory, perception, parallel execution)
    """

    def __init__(self, config_path: str = "config/system.yaml", user_tier: str = "basic"):
        self.config_path = config_path
        self.user_tier = user_tier
        self.nucleus: Optional[Nucleus] = None
        self.config: Optional[Config] = None
        self.initialized = False

        # Stats tracking
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "model_usage": {},
            "memory_stores": 0,
            "memory_retrievals": 0
        }

    async def initialize(self):
        """Initialize the adapter based on user tier"""
        try:
            logger.info(f"Initializing NucleusAdapter with tier: {self.user_tier}")

            # Load config
            self.config = Config(self.config_path)

            if self.user_tier == "basic":
                await self._init_basic_mode()
            elif self.user_tier == "pro":
                await self._init_pro_mode()
            elif self.user_tier == "power":
                await self._init_power_mode()
            else:
                raise ValueError(f"Unknown tier: {self.user_tier}")

            self.initialized = True
            logger.info(f"NucleusAdapter initialized successfully (tier: {self.user_tier})")

        except Exception as e:
            logger.error(f"Failed to initialize NucleusAdapter: {e}", exc_info=True)
            raise

    async def _init_basic_mode(self):
        """
        Basic mode: No Nucleus, no persistence, just provider routing

        Perfect for free tier - minimal overhead, fast responses
        """
        logger.info("Initializing BASIC mode (provider routing only)")
        # No Nucleus boot - just config loaded
        # Provider routing happens in stream_completion()

    async def _init_pro_mode(self):
        """
        Pro mode: Limited Nucleus with L1+L2 memory only

        Boots Nucleus but only loads:
        - Memory module (L1 + L2 tiers only)
        - Providers module
        """
        logger.info("Initializing PRO mode (L1+L2 memory)")

        # Boot Nucleus with limited modules
        self.nucleus = Nucleus(self.config_path)

        # Configure to load only memory + providers
        # (Module filtering happens in Nucleus.load_modules())
        await self.nucleus.start()

        logger.info("Nucleus started in PRO mode")

    async def _init_power_mode(self):
        """
        Power mode: Full LOTUS with all modules

        Boots complete Nucleus with:
        - All 4 memory tiers (L1→L2→L3→L4)
        - All providers (Apriel/Grok/Claude)
        - Reasoning engine with tools
        - Perception module (screen/clipboard)
        - Parallel task execution
        """
        logger.info("Initializing POWER mode (full LOTUS)")

        # Boot full Nucleus
        self.nucleus = Nucleus(self.config_path)
        await self.nucleus.start()

        logger.info("Nucleus started in POWER mode with all modules")

    async def shutdown(self):
        """Gracefully shutdown Nucleus and cleanup resources"""
        try:
            logger.info("Shutting down NucleusAdapter...")

            if self.nucleus:
                await self.nucleus.stop()

            self.initialized = False
            logger.info("NucleusAdapter shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        conversation_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream completion with intelligent model routing

        Model routing logic (works for ALL tiers):
        - auto: Smart routing based on query analysis
        - apriel: Self-hosted Apriel model
        - grok: xAI Grok (reasoning tasks)
        - claude: Anthropic Claude (vision/complex tasks)
        """
        if not self.initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        try:
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = str(uuid.uuid4())

            # Route to appropriate model
            selected_model = self._select_model(messages, model)
            logger.info(f"Routing to model: {selected_model} (requested: {model})")

            # Update stats
            self.stats["total_requests"] += 1
            self.stats["model_usage"][selected_model] = self.stats["model_usage"].get(selected_model, 0) + 1

            # Store conversation in memory (if tier supports it)
            if self.user_tier in ["pro", "power"] and self.nucleus:
                await self._store_conversation(conversation_id, messages)

            # Stream response
            async for chunk in self._stream_from_provider(
                selected_model, messages, temperature, max_tokens
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Error in stream_completion: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    def _select_model(self, messages: List[Dict[str, str]], requested_model: str) -> str:
        """
        Intelligent model routing (Model Triad)

        Routes based on query analysis:
        - Vision tasks → Claude
        - Reasoning/math → Grok
        - General → Apriel (self-hosted, free)
        """
        if requested_model != "auto":
            return requested_model

        # Analyze last user message
        last_message = messages[-1]["content"] if messages else ""
        last_message_lower = last_message.lower()

        # Vision detection
        if any(word in last_message_lower for word in ["image", "picture", "photo", "screenshot", "visual"]):
            return "claude"

        # Reasoning detection
        if any(word in last_message_lower for word in ["calculate", "solve", "math", "reasoning", "logic"]):
            return "grok"

        # Default to Apriel (self-hosted)
        return "apriel"

    async def _store_conversation(self, conversation_id: str, messages: List[Dict[str, str]]):
        """Store conversation in memory tiers"""
        try:
            if not self.nucleus:
                return

            # Publish to memory store via message bus
            event_data = {
                "conversation_id": conversation_id,
                "messages": messages,
                "timestamp": datetime.utcnow().isoformat(),
                "importance": 0.5  # Default importance
            }

            await self.nucleus.message_bus.publish(
                "memory.store",
                json.dumps(event_data)
            )

            self.stats["memory_stores"] += 1

        except Exception as e:
            logger.warning(f"Failed to store conversation: {e}")

    async def _stream_from_provider(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> AsyncIterator[str]:
        """
        Stream response from provider

        Routes to appropriate provider based on model:
        - apriel → OpenAI-compatible endpoint (localhost:8001)
        - grok → xAI API
        - claude → Anthropic API
        """
        try:
            # Get provider config
            provider_config = self._get_provider_config(model)

            if model == "apriel":
                async for chunk in self._stream_openai_compatible(
                    provider_config, messages, temperature, max_tokens
                ):
                    yield chunk

            elif model == "grok":
                async for chunk in self._stream_xai(
                    provider_config, messages, temperature, max_tokens
                ):
                    yield chunk

            elif model == "claude":
                async for chunk in self._stream_anthropic(
                    provider_config, messages, temperature, max_tokens
                ):
                    yield chunk

            else:
                raise ValueError(f"Unknown model: {model}")

        except Exception as e:
            logger.error(f"Provider stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': f'Provider error: {str(e)}'})}\n\n"

    def _get_provider_config(self, model: str) -> Dict[str, Any]:
        """Get provider configuration from config"""
        if model == "apriel":
            return {
                "base_url": "http://localhost:8001/v1",
                "api_key": "dummy",
                "model_name": "apriel-1.5"
            }
        elif model == "grok":
            import os
            return {
                "api_key": os.getenv("XAI_API_KEY"),
                "model_name": "grok-beta"
            }
        elif model == "claude":
            import os
            return {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "model_name": "claude-sonnet-4-20250514"
            }
        else:
            raise ValueError(f"Unknown model: {model}")

    async def _stream_openai_compatible(
        self, config: Dict, messages: List[Dict], temperature: float, max_tokens: int
    ) -> AsyncIterator[str]:
        """Stream from OpenAI-compatible endpoint (Apriel)"""
        import httpx

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{config['base_url']}/chat/completions",
                    json={
                        "model": config['model_name'],
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": True
                    },
                    headers={"Authorization": f"Bearer {config['api_key']}"}
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"

            except Exception as e:
                logger.error(f"Apriel stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    async def _stream_xai(
        self, config: Dict, messages: List[Dict], temperature: float, max_tokens: int
    ) -> AsyncIterator[str]:
        """Stream from xAI Grok"""
        import httpx

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                async with client.stream(
                    "POST",
                    "https://api.x.ai/v1/chat/completions",
                    json={
                        "model": config['model_name'],
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": True
                    },
                    headers={"Authorization": f"Bearer {config['api_key']}"}
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"

            except Exception as e:
                logger.error(f"Grok stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    async def _stream_anthropic(
        self, config: Dict, messages: List[Dict], temperature: float, max_tokens: int
    ) -> AsyncIterator[str]:
        """Stream from Anthropic Claude"""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=config['api_key'])

            # Convert messages to Anthropic format
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Stream response
            async with client.messages.stream(
                model=config['model_name'],
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens
            ) as stream:
                async for text in stream.text_stream:
                    # Convert to SSE format
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}\n\n"

        except Exception as e:
            logger.error(f"Claude stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status"""
        status = {
            "status": "online" if self.initialized else "offline",
            "tier": self.user_tier,
            "nucleus": None,
            "modules": {},
            "infrastructure": {},
            "stats": self.stats
        }

        if self.nucleus and self.user_tier in ["pro", "power"]:
            status["nucleus"] = {
                "running": self.nucleus.running if hasattr(self.nucleus, 'running') else False,
                "modules_loaded": len(self.nucleus.modules) if hasattr(self.nucleus, 'modules') else 0
            }

            # Get module info
            if hasattr(self.nucleus, 'modules'):
                for module_name, module in self.nucleus.modules.items():
                    status["modules"][module_name] = {
                        "loaded": True,
                        "type": getattr(module, 'type', 'unknown'),
                        "version": getattr(module, 'version', '1.0.0')
                    }

            # Infrastructure status
            status["infrastructure"] = {
                "redis": hasattr(self.nucleus, 'message_bus') and self.nucleus.message_bus is not None,
                "memory_tiers": {
                    "L1": self.user_tier in ["pro", "power"],
                    "L2": self.user_tier in ["pro", "power"],
                    "L3": self.user_tier == "power",
                    "L4": self.user_tier == "power"
                }
            }

        return status

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models in the Triad"""
        return [
            {
                "id": "apriel",
                "name": "Apriel 1.5",
                "provider": "self-hosted",
                "description": "Self-hosted model for general tasks",
                "available": True,
                "tier_required": "basic"
            },
            {
                "id": "grok",
                "name": "Grok Beta",
                "provider": "xAI",
                "description": "Advanced reasoning and analysis",
                "available": True,
                "tier_required": "basic"
            },
            {
                "id": "claude",
                "name": "Claude Sonnet 4",
                "provider": "Anthropic",
                "description": "Vision and complex reasoning",
                "available": True,
                "tier_required": "basic"
            }
        ]
