"""
Provider Module - Multi-Provider LLM Access

This module manages all LLM provider interactions:
- Anthropic (Claude)
- OpenAI (GPT)
- Google (Gemini)
- Ollama (Local models)

Features:
- Intelligent routing based on task type
- Automatic fallback on errors
- Cost optimization
- Rate limit handling
- Streaming support
"""

import asyncio
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum

from lib.module import BaseModule
from lib.decorators import on_event, tool
from lib.providers import (
    AnthropicProvider, OpenAIProvider, 
    GoogleProvider, OllamaProvider,
    ProviderError, ProviderResponse
)


class TaskComplexity(Enum):
    """Task complexity levels for routing"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class CompletionRequest:
    """LLM completion request"""
    prompt: str
    system_prompt: Optional[str] = None
    provider: Optional[str] = None  # Specific provider or auto-route
    model: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7
    stream: bool = False
    tools: Optional[List[Dict]] = None
    metadata: Optional[Dict[str, Any]] = None


class ProviderModule(BaseModule):
    """
    LLM Provider Coordinator
    
    Manages all provider interactions with:
    - Smart routing
    - Fallback chains
    - Cost optimization
    - Rate limit handling
    """
    
    async def initialize(self) -> None:
        """Initialize all configured providers"""
        self.logger.info("Initializing LLM provider system")
        
        # Initialize providers
        self.providers: Dict[str, Any] = {}
        
        # Anthropic
        if self.config.get("providers.anthropic.enabled", True):
            self.providers["anthropic"] = AnthropicProvider(
                self.config,
                api_key=self.config.get("ANTHROPIC_API_KEY")
            )
            self.logger.info("Initialized Anthropic provider")
        
        # OpenAI
        if self.config.get("providers.openai.enabled", True):
            self.providers["openai"] = OpenAIProvider(
                self.config,
                api_key=self.config.get("OPENAI_API_KEY")
            )
            self.logger.info("Initialized OpenAI provider")
        
        # Google
        if self.config.get("providers.google.enabled", False):
            self.providers["google"] = GoogleProvider(
                self.config,
                api_key=self.config.get("GOOGLE_API_KEY")
            )
            self.logger.info("Initialized Google provider")
        
        # Ollama (local)
        if self.config.get("providers.ollama.enabled", True):
            self.providers["ollama"] = OllamaProvider(
                self.config,
                base_url=self.config.get("providers.ollama.base_url", "http://localhost:11434")
            )
            self.logger.info("Initialized Ollama provider")
        
        # Default provider
        self.default_provider = self.config.get(
            "providers.default_provider", 
            "claude-sonnet-4"
        )
        
        # Fallback chain
        self.fallback_enabled = self.config.get("providers.fallback.enabled", True)
        self.fallback_chain = self.config.get("providers.fallback.chain", [])
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_count": 0,
            "provider_usage": {name: 0 for name in self.providers.keys()}
        }
        
        self.logger.info(f"Provider system initialized with {len(self.providers)} providers")
    
    @on_event("llm.complete")
    async def handle_completion(self, event: Dict[str, Any]) -> None:
        """
        Handle LLM completion request
        
        Event data:
        {
            "prompt": "your prompt here",
            "system_prompt": "optional system prompt",
            "provider": "auto",  # or specific: claude, gpt, gemini, ollama
            "model": "claude-sonnet-4",
            "max_tokens": 4000,
            "temperature": 0.7,
            "tools": [],  # optional tools
            "metadata": {}
        }
        """
        request = CompletionRequest(
            prompt=event.get("prompt", ""),
            system_prompt=event.get("system_prompt"),
            provider=event.get("provider"),
            model=event.get("model"),
            max_tokens=event.get("max_tokens", 4000),
            temperature=event.get("temperature", 0.7),
            stream=event.get("stream", False),
            tools=event.get("tools"),
            metadata=event.get("metadata", {})
        )
        
        if not request.prompt:
            self.logger.warning("Completion request with empty prompt")
            return
        
        try:
            # Route to provider
            provider_name, provider = self._route_request(request)
            
            self.logger.debug(f"Routing completion to {provider_name}")
            
            # Generate completion
            if request.stream:
                # Handle streaming
                await self._handle_streaming_completion(
                    provider, provider_name, request
                )
            else:
                # Handle regular completion
                response = await provider.complete(
                    prompt=request.prompt,
                    system_prompt=request.system_prompt,
                    model=request.model,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    tools=request.tools
                )
                
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["provider_usage"][provider_name] += 1
                
                # Publish response
                await self.publish("llm.response", {
                    "content": response.content,
                    "provider": provider_name,
                    "model": response.model,
                    "tokens": response.usage,
                    "metadata": request.metadata
                })
                
        except ProviderError as e:
            self.logger.error(f"Provider error: {e}")
            
            # Try fallback
            if self.fallback_enabled:
                await self._try_fallback(request, provider_name)
            else:
                self.stats["failed_requests"] += 1
                await self.publish("provider.error", {
                    "error": str(e),
                    "provider": provider_name,
                    "metadata": request.metadata
                })
    
    @on_event("llm.stream")
    async def handle_streaming(self, event: Dict[str, Any]) -> None:
        """Handle streaming completion request"""
        event["stream"] = True
        await self.handle_completion(event)
    
    @on_event("provider.switch")
    async def handle_switch_provider(self, event: Dict[str, Any]) -> None:
        """
        Switch default provider
        
        Event data:
        {
            "provider": "claude-sonnet-4"
        }
        """
        new_provider = event.get("provider")
        
        if new_provider and self._provider_available(new_provider):
            old_provider = self.default_provider
            self.default_provider = new_provider
            
            await self.publish("provider.switched", {
                "from": old_provider,
                "to": new_provider
            })
            
            self.logger.info(f"Switched provider from {old_provider} to {new_provider}")
        else:
            self.logger.warning(f"Provider {new_provider} not available")
    
    @tool("list_providers")
    async def list_providers(self) -> Dict[str, Any]:
        """List all available providers and their status"""
        return {
            "providers": [
                {
                    "name": name,
                    "enabled": True,
                    "models": provider.available_models(),
                    "usage_count": self.stats["provider_usage"].get(name, 0)
                }
                for name, provider in self.providers.items()
            ],
            "default": self.default_provider,
            "fallback_chain": self.fallback_chain
        }
    
    @tool("provider_stats")
    async def get_stats(self) -> Dict[str, Any]:
        """Get provider usage statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0 else 0
            )
        }
    
    # Helper methods
    
    def _route_request(
        self, 
        request: CompletionRequest
    ) -> tuple[str, Any]:
        """Route request to appropriate provider"""
        # If specific provider requested
        if request.provider and request.provider in self.providers:
            return request.provider, self.providers[request.provider]
        
        # Auto-route based on task complexity
        complexity = self._assess_complexity(request)
        
        # Get routing rules
        routing = self.config.get("providers.routing", {})
        
        # Determine provider
        if complexity == TaskComplexity.SIMPLE:
            provider_name = routing.get("fast_tasks", self.default_provider)
        elif complexity == TaskComplexity.COMPLEX:
            provider_name = routing.get("complex_tasks", self.default_provider)
        elif "code" in request.prompt.lower():
            provider_name = routing.get("coding_tasks", self.default_provider)
        else:
            provider_name = self.default_provider
        
        # Resolve to actual provider
        if provider_name in self.providers:
            return provider_name, self.providers[provider_name]
        
        # Fallback to default
        return self.default_provider, self.providers[list(self.providers.keys())[0]]
    
    def _assess_complexity(self, request: CompletionRequest) -> TaskComplexity:
        """Assess task complexity for routing"""
        prompt_length = len(request.prompt)
        
        if prompt_length < 100:
            return TaskComplexity.SIMPLE
        elif prompt_length < 500:
            return TaskComplexity.MODERATE
        elif prompt_length < 2000:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.EXPERT
    
    async def _try_fallback(
        self, 
        request: CompletionRequest,
        failed_provider: str
    ) -> None:
        """Try fallback providers"""
        self.logger.info(f"Attempting fallback from {failed_provider}")
        
        for provider_name in self.fallback_chain:
            if provider_name == failed_provider:
                continue
            
            if provider_name not in self.providers:
                continue
            
            try:
                provider = self.providers[provider_name]
                response = await provider.complete(
                    prompt=request.prompt,
                    system_prompt=request.system_prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature
                )
                
                self.stats["fallback_count"] += 1
                self.stats["successful_requests"] += 1
                
                await self.publish("provider.fallback", {
                    "from": failed_provider,
                    "to": provider_name
                })
                
                await self.publish("llm.response", {
                    "content": response.content,
                    "provider": provider_name,
                    "model": response.model,
                    "fallback": True
                })
                
                self.logger.info(f"Fallback successful using {provider_name}")
                return
                
            except Exception as e:
                self.logger.warning(f"Fallback to {provider_name} failed: {e}")
                continue
        
        # All fallbacks failed
        self.stats["failed_requests"] += 1
        await self.publish("provider.error", {
            "error": "All providers failed",
            "attempted": [failed_provider] + self.fallback_chain
        })
    
    async def _handle_streaming_completion(
        self,
        provider: Any,
        provider_name: str,
        request: CompletionRequest
    ) -> None:
        """Handle streaming completion"""
        try:
            async for chunk in provider.stream(
                prompt=request.prompt,
                system_prompt=request.system_prompt,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ):
                await self.publish("llm.stream_chunk", {
                    "content": chunk.content,
                    "provider": provider_name,
                    "done": chunk.done,
                    "metadata": request.metadata
                })
            
            self.stats["successful_requests"] += 1
            
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            if self.fallback_enabled:
                # Try fallback with non-streaming
                request.stream = False
                await self._try_fallback(request, provider_name)
    
    def _provider_available(self, provider_name: str) -> bool:
        """Check if provider is available"""
        return provider_name in self.providers
    
    async def shutdown(self) -> None:
        """Shutdown all providers gracefully"""
        self.logger.info("Shutting down provider system")
        
        for name, provider in self.providers.items():
            try:
                await provider.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down {name}: {e}")
        
        self.logger.info("Provider system shutdown complete")