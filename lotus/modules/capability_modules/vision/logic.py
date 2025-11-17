"""
LOTUS Vision Module - Computer Vision Capabilities

Provides visual analysis capabilities including:
- Screenshot analysis with AI vision models
- OCR (text extraction)
- UI element detection
- Visual question answering
- Screen reading for accessibility

Uses Claude 3.5 Sonnet (best vision model) with GPT-4V fallback.
"""

import asyncio
import base64
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.module import BaseModule
from lib.decorators import on_event, tool
from lib.exceptions import ProviderError


class ImageFormat(Enum):
    """Supported image formats"""
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    WEBP = "webp"


@dataclass
class VisionAnalysis:
    """Results from visual analysis"""
    description: str
    text_found: List[str]
    ui_elements: List[Dict[str, Any]]
    confidence: float
    model_used: str
    metadata: Dict[str, Any]


@dataclass
class UIElement:
    """Detected UI element"""
    type: str  # button, input, link, etc
    text: str
    location: str  # description of location
    clickable: bool
    confidence: float


class VisionModule(BaseModule):
    """
    Computer Vision Module

    Provides AI-powered visual analysis using state-of-the-art vision models.
    """

    async def initialize(self) -> None:
        """Initialize vision capabilities"""
        self.logger.info("Initializing vision module")

        # Get provider manager
        self.llm = self.config.get("services.llm")
        if not self.llm:
            self.logger.error("LLM provider service not available")
            raise RuntimeError("Vision module requires LLM provider")

        # Configuration
        self.vision_provider = self.config.get("vision.vision_provider", "anthropic")
        self.fallback_provider = self.config.get("vision.fallback_provider", "openai")
        self.max_image_size = self.config.get("vision.max_image_size", 5242880)  # 5MB
        self.compress_images = self.config.get("vision.compress_images", True)

        # Check for image processing library
        try:
            from PIL import Image
            self.PIL = Image
            self.image_processing_available = True
            self.logger.info("PIL available for image processing")
        except ImportError:
            self.PIL = None
            self.image_processing_available = False
            self.logger.warning("PIL not available - image processing limited")

        # Statistics
        self.stats = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "ocr_requests": 0,
            "ui_detections": 0,
            "models_used": {}
        }

        self.logger.info("Vision module initialized successfully")

    # ========================================
    # CORE VISION CAPABILITIES
    # ========================================

    async def _encode_image(self, image_path: str) -> Tuple[str, str]:
        """
        Encode image to base64 for API transmission

        Returns:
            Tuple of (base64_data, media_type)
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_image_size:
            if self.image_processing_available and self.compress_images:
                self.logger.info(f"Image too large ({file_size} bytes), compressing...")
                image_path = await self._compress_image(image_path)
                path = Path(image_path)
            else:
                raise ValueError(f"Image too large: {file_size} bytes (max: {self.max_image_size})")

        # Determine media type
        suffix = path.suffix.lower()
        media_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp'
        }
        media_type = media_type_map.get(suffix, 'image/png')

        # Read and encode
        with open(path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        return image_data, media_type

    async def _compress_image(self, image_path: str, max_dimension: int = 1920) -> str:
        """
        Compress image to reduce size

        Args:
            image_path: Path to image
            max_dimension: Maximum width/height

        Returns:
            Path to compressed image
        """
        if not self.PIL:
            return image_path

        img = self.PIL.open(image_path)

        # Calculate new size
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))

            img = img.resize((new_width, new_height), self.PIL.Resampling.LANCZOS)

        # Save compressed
        compressed_path = str(Path(image_path).with_suffix('.compressed.png'))
        img.save(compressed_path, 'PNG', optimize=True)

        self.logger.info(f"Compressed image: {width}x{height} -> {new_width}x{new_height}")
        return compressed_path

    async def _analyze_with_vision_model(
        self,
        image_path: str,
        prompt: str,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze image using vision-capable LLM

        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            provider: Specific provider to use

        Returns:
            Analysis results
        """
        try:
            # Encode image
            image_data, media_type = await self._encode_image(image_path)

            # Choose provider
            provider = provider or self.vision_provider

            # Build vision request based on provider
            if provider == "anthropic":
                response = await self._analyze_with_claude(image_data, media_type, prompt)
            elif provider == "openai":
                response = await self._analyze_with_gpt4v(image_data, media_type, prompt)
            else:
                raise ValueError(f"Unsupported vision provider: {provider}")

            # Update stats
            self.stats["total_analyses"] += 1
            self.stats["successful_analyses"] += 1
            self.stats["models_used"][provider] = self.stats["models_used"].get(provider, 0) + 1

            return {
                "success": True,
                "analysis": response,
                "provider": provider,
                "image_path": image_path
            }

        except Exception as e:
            self.logger.error(f"Vision analysis failed: {e}")
            self.stats["failed_analyses"] += 1

            # Try fallback provider
            if provider != self.fallback_provider:
                self.logger.info(f"Trying fallback provider: {self.fallback_provider}")
                return await self._analyze_with_vision_model(
                    image_path, prompt, self.fallback_provider
                )

            return {
                "success": False,
                "error": str(e),
                "provider": provider
            }

    async def _analyze_with_claude(
        self,
        image_data: str,
        media_type: str,
        prompt: str
    ) -> str:
        """
        Analyze with Claude 3.5 Sonnet (best vision model)

        Claude uses a different message format for vision.
        """
        try:
            # Import Anthropic SDK
            try:
                import anthropic
            except ImportError:
                raise ProviderError("anthropic package not installed")

            # Get API key
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ProviderError("ANTHROPIC_API_KEY not set")

            # Create client
            client = anthropic.AsyncAnthropic(api_key=api_key)

            # Build message with vision
            response = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            return response.content[0].text

        except Exception as e:
            raise ProviderError(f"Claude vision analysis failed: {e}")

    async def _analyze_with_gpt4v(
        self,
        image_data: str,
        media_type: str,
        prompt: str
    ) -> str:
        """
        Analyze with GPT-4 Vision

        GPT-4V uses a different message format.
        """
        try:
            # Import OpenAI SDK
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ProviderError("openai package not installed")

            # Get API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ProviderError("OPENAI_API_KEY not set")

            # Create client
            client = AsyncOpenAI(api_key=api_key)

            # Build message with vision
            response = await client.chat.completions.create(
                model="gpt-4-vision-preview",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_data}"
                            }
                        }
                    ]
                }]
            )

            return response.choices[0].message.content

        except Exception as e:
            raise ProviderError(f"GPT-4V analysis failed: {e}")

    # ========================================
    # TOOL IMPLEMENTATIONS
    # ========================================

    @tool
    async def analyze_screenshot(
        self,
        image_path: str,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a screenshot with AI vision

        Args:
            image_path: Path to screenshot
            query: Optional specific question about the image

        Returns:
            Detailed analysis of the screenshot
        """
        prompt = query or """
Analyze this screenshot in detail. Provide:
1. Overall description of what you see
2. All visible text (OCR)
3. UI elements (buttons, inputs, links, etc) with their locations
4. Notable features or anomalies
5. Context/purpose of this screen

Format as JSON with keys: description, text, ui_elements, context
"""

        result = await self._analyze_with_vision_model(image_path, prompt)

        if result["success"]:
            try:
                # Try to parse as JSON
                analysis_data = json.loads(result["analysis"])
            except:
                # If not JSON, create structured response
                analysis_data = {
                    "description": result["analysis"],
                    "text": [],
                    "ui_elements": [],
                    "context": "Analysis completed"
                }

            return {
                **result,
                "structured_analysis": analysis_data
            }

        return result

    @tool
    async def read_screen_text(self, image_path: str) -> Dict[str, Any]:
        """
        Extract all text from screenshot (OCR)

        Args:
            image_path: Path to screenshot

        Returns:
            List of all text found
        """
        prompt = """
Extract ALL visible text from this image.
Return as a JSON list of strings, each representing a line or block of text.
Preserve the reading order (top to bottom, left to right).
"""

        self.stats["ocr_requests"] += 1
        result = await self._analyze_with_vision_model(image_path, prompt)

        if result["success"]:
            try:
                text_list = json.loads(result["analysis"])
            except:
                # Fallback: split by newlines
                text_list = result["analysis"].split('\n')

            await self.publish("vision.text_extracted", {
                "image_path": image_path,
                "text": text_list,
                "count": len(text_list)
            })

            return {
                **result,
                "text": text_list,
                "count": len(text_list)
            }

        return result

    @tool
    async def detect_buttons(self, image_path: str) -> Dict[str, Any]:
        """
        Find clickable UI elements

        Args:
            image_path: Path to screenshot

        Returns:
            List of detected buttons/clickable elements
        """
        prompt = """
Identify all clickable UI elements (buttons, links, tabs, etc).
For each element, provide:
- type: button/link/tab/etc
- text: visible text on the element
- location: description of where it is on screen
- purpose: what clicking it would do

Return as JSON array of objects.
"""

        self.stats["ui_detections"] += 1
        result = await self._analyze_with_vision_model(image_path, prompt)

        if result["success"]:
            try:
                ui_elements = json.loads(result["analysis"])
            except:
                ui_elements = []

            await self.publish("vision.ui_detected", {
                "image_path": image_path,
                "elements": ui_elements,
                "count": len(ui_elements)
            })

            return {
                **result,
                "ui_elements": ui_elements,
                "count": len(ui_elements)
            }

        return result

    # ========================================
    # EVENT HANDLERS
    # ========================================

    @on_event("vision.analyze_screen")
    async def handle_analyze_screen(self, event: Dict) -> None:
        """Handle screen analysis requests"""
        image_path = event.data.get("image_path")
        query = event.data.get("query")

        if not image_path:
            self.logger.error("No image_path provided in vision.analyze_screen event")
            return

        result = await self.analyze_screenshot(image_path, query)

        # Publish results
        await self.publish("vision.analysis_complete", result)

    @on_event("perception.screen_capture")
    async def handle_screen_capture(self, event: Dict) -> None:
        """
        Auto-analyze screen captures from perception module

        This creates a seamless flow: perception captures -> vision analyzes
        """
        image_path = event.data.get("path")
        if not image_path:
            return

        self.logger.info(f"Auto-analyzing screen capture: {image_path}")

        # Do quick analysis
        result = await self.analyze_screenshot(
            image_path,
            query="Briefly describe what's on this screen in 2-3 sentences."
        )

        # Store in memory if available
        memory = self.config.get("services.memory")
        if memory and result["success"]:
            await memory.store({
                "type": "screen_capture_analysis",
                "image_path": image_path,
                "analysis": result["structured_analysis"],
                "timestamp": event.data.get("timestamp")
            })

    # ========================================
    # LIFECYCLE
    # ========================================

    async def shutdown(self) -> None:
        """Cleanup on shutdown"""
        self.logger.info("Vision module shutting down")
        self.logger.info(f"Stats: {self.stats}")

        # Clean up compressed images
        # (Optional: implement cleanup of temporary files)

        await super().shutdown()
