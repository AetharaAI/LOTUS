"""
LOTUS LLM Provider System

Unified interface for multiple LLM providers:
- Anthropic (Claude)
- OpenAI (GPT)
- Ollama (Local models)
- xAI (Grok)
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from .logging import get_logger
from .exceptions import ProviderError


logger = get_logger("providers")


class ProviderType(Enum):
    """Supported LLM providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    XAI = "xai"


@dataclass
class LLMResponse:
    """
    Standardized LLM response

    Normalized response format across all providers.
    """
    text: str
    model: str
    provider: str
    tokens_used: int = 0
    finish_reason: str = "complete"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseProvider(ABC):
    """
    Base class for LLM providers

    All providers must implement these methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.logger = logger

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate completion

        Args:
            prompt: Input prompt
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with generated text
        """
        pass

    async def shutdown(self) -> None:
        """
        Shutdown provider and cleanup resources

        This method should be overridden by providers that need cleanup.
        """
        self.logger.debug(f"Shutting down {self.__class__.__name__}")


class AnthropicProvider(BaseProvider):
    """
    Anthropic (Claude) provider
    """

    def __init__(self, config: Dict[str, Any], api_key: str = None):
        super().__init__(config)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            self.client = None
            logger.warning("anthropic package not installed")

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using Claude"""
        if not self.client:
            raise ProviderError("Anthropic client not initialized")

        model = kwargs.get('model', self.config.get('default_model', 'claude-3-5-sonnet-20241022'))
        max_tokens = kwargs.get('max_tokens', 4096)
        temperature = kwargs.get('temperature', 0.7)

        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            return LLMResponse(
                text=response.content[0].text,
                model=model,
                provider="anthropic",
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason,
                metadata={
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            )

        except Exception as e:
            raise ProviderError(f"Anthropic API error: {e}")

    async def shutdown(self) -> None:
        """Shutdown Anthropic provider"""
        await super().shutdown()
        if self.client:
            # Close any open connections
            pass


class OpenAIProvider(BaseProvider):
    """
    OpenAI (GPT) provider
    """

    def __init__(self, config: Dict[str, Any], api_key: str = None):
        super().__init__(config)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            self.client = None
            logger.warning("openai package not installed")

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using GPT"""
        if not self.client:
            raise ProviderError("OpenAI client not initialized")

        model = kwargs.get('model', self.config.get('default_model', 'gpt-4'))
        max_tokens = kwargs.get('max_tokens', 4096)
        temperature = kwargs.get('temperature', 0.7)

        try:
            response = await self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            return LLMResponse(
                text=response.choices[0].message.content,
                model=model,
                provider="openai",
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                }
            )

        except Exception as e:
            raise ProviderError(f"OpenAI API error: {e}")

    async def shutdown(self) -> None:
        """Shutdown OpenAI provider"""
        await super().shutdown()
        if self.client:
            await self.client.close()


class OllamaProvider(BaseProvider):
    """
    Ollama (Local models) provider
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')

        try:
            import httpx
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        except ImportError:
            self.client = None
            logger.warning("httpx package not installed")

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using Ollama"""
        if not self.client:
            raise ProviderError("Ollama client not initialized")

        model = kwargs.get('model', self.config.get('default_model', 'llama2'))
        temperature = kwargs.get('temperature', 0.7)

        try:
            response = await self.client.post(
                '/api/generate',
                json={
                    'model': model,
                    'prompt': prompt,
                    'temperature': temperature,
                    'stream': False
                }
            )

            data = response.json()

            return LLMResponse(
                text=data.get('response', ''),
                model=model,
                provider="ollama",
                tokens_used=data.get('eval_count', 0),
                metadata=data
            )

        except Exception as e:
            raise ProviderError(f"Ollama API error: {e}")

    async def shutdown(self) -> None:
        """Shutdown Ollama provider"""
        await super().shutdown()
        if self.client:
            await self.client.aclose()


class XAIProvider(BaseProvider):
    """
    xAI (Grok) provider
    """

    def __init__(self, config: Dict[str, Any], api_key: str = None):
        super().__init__(config)
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.base_url = "https://api.x.ai/v1"

        try:
            import httpx
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=120.0
            )
        except ImportError:
            self.client = None
            logger.warning("httpx package not installed")

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using Grok"""
        if not self.client:
            raise ProviderError("xAI client not initialized")

        model = kwargs.get('model', self.config.get('default_model', 'grok-beta'))
        max_tokens = kwargs.get('max_tokens', 4096)
        temperature = kwargs.get('temperature', 0.7)

        try:
            response = await self.client.post(
                '/chat/completions',
                json={
                    'model': model,
                    'messages': [{"role": "user", "content": prompt}],
                    'max_tokens': max_tokens,
                    'temperature': temperature
                }
            )

            data = response.json()

            return LLMResponse(
                text=data['choices'][0]['message']['content'],
                model=model,
                provider="xai",
                tokens_used=data.get('usage', {}).get('total_tokens', 0),
                finish_reason=data['choices'][0].get('finish_reason', 'complete'),
                metadata=data.get('usage', {})
            )

        except Exception as e:
            raise ProviderError(f"xAI API error: {e}")

    async def shutdown(self) -> None:
        """Shutdown xAI provider"""
        await super().shutdown()
        if self.client:
            await self.client.aclose()


class ProviderManager:
    """
    Manages multiple LLM providers

    Handles provider initialization, selection, and fallback.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider manager

        Args:
            config: Configuration dict with provider settings
        """
        self.config = config
        self.providers: Dict[str, BaseProvider] = {}
        self.default_provider: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize all enabled providers"""
        logger.info("Initializing LLM providers...")

        # Initialize Anthropic
        if self.config.get('providers.anthropic.enabled', False):
            try:
                self.providers['anthropic'] = AnthropicProvider(
                    self.config.get('providers.anthropic', {})
                )
                logger.info("✓ Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic: {e}")

        # Initialize OpenAI
        if self.config.get('providers.openai.enabled', False):
            try:
                self.providers['openai'] = OpenAIProvider(
                    self.config.get('providers.openai', {})
                )
                logger.info("✓ OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        # Initialize Ollama
        if self.config.get('providers.ollama.enabled', False):
            try:
                self.providers['ollama'] = OllamaProvider(
                    self.config.get('providers.ollama', {})
                )
                logger.info("✓ Ollama provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama: {e}")

        # Initialize xAI
        if self.config.get('providers.xai.enabled', False):
            try:
                self.providers['xai'] = XAIProvider(
                    self.config.get('providers.xai', {})
                )
                logger.info("✓ xAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize xAI: {e}")

        # Set default provider
        self.default_provider = self.config.get('providers.default_provider', 'anthropic')

        if not self.providers:
            logger.warning("No LLM providers initialized!")

    async def complete(self, prompt: str, provider: str = None, **kwargs) -> LLMResponse:
        """
        Generate completion using specified or default provider

        Args:
            prompt: Input prompt
            provider: Provider name (optional, uses default if not specified)
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse

        Raises:
            ProviderError: If provider not available
        """
        provider_name = provider or self.default_provider

        if provider_name not in self.providers:
            raise ProviderError(f"Provider '{provider_name}' not available")

        return await self.providers[provider_name].complete(prompt, **kwargs)

    async def shutdown(self) -> None:
        """Shutdown all providers"""
        logger.info("Shutting down LLM providers...")

        for name, provider in self.providers.items():
            try:
                await provider.shutdown()
                logger.debug(f"✓ {name} provider shutdown")
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())
