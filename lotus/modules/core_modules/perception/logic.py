"""
LOTUS Perception Module - Multi-Modal Input Processing

This module is responsible for perceiving the environment (screen, clipboard,
user input, voice, files) and translating raw observations into standardized
events for the rest of the LOTUS system.
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lotus.lib.module import BaseModule, Event
from lotus.lib.decorators import on_event, tool, periodic # Import tool decorator explicitly

# Conditional imports for perception sources
_PYPERCLIP_AVAILABLE = False
try:
    import pyperclip # For clipboard monitoring
    _PYPERCLIP_AVAILABLE = True
except ImportError:
    pass

_MSS_AVAILABLE = False
_PIL_AVAILABLE = False
try:
    import mss # For screen capture
    from PIL import Image # For image processing/diffing
    _MSS_AVAILABLE = True
    _PIL_AVAILABLE = True
except ImportError:
    pass

# Assuming file_watcher would be a separate internal utility or class
# from .file_watcher import FileWatcher # Example


class PerceptionModule(BaseModule):
    """
    Perception System Coordinator
    
    Observes the environment and publishes raw perception events.
    No longer directly triggers ReasoningEngine, but feeds the ContextOrchestrator.
    """
    
    def __init__(self, name: str, metadata: Dict, message_bus: Any, config: Any, logger: logging.Logger):
        super().__init__(name, metadata, message_bus, config, logger)
        self.logger = logging.getLogger(f"lotus.module.{self.name}")

        self.clipboard_monitor_task: Optional[asyncio.Task] = None
        self.last_clipboard_content: Optional[str] = None

        self.screen_monitor_task: Optional[asyncio.Task] = None
        self.last_screen_hash: Optional[str] = None
        self.last_screen_image: Optional[Image.Image] = None
        
        self.monitor_clipboard_enabled = self.config.get("perception.clipboard.enabled", True)
        self.monitor_clipboard_interval = self.config.get("perception.clipboard.interval_seconds", 1.0)
        self.clipboard_max_chars = self.config.get("perception.clipboard.max_chars", 5000)

        self.monitor_screen_enabled = self.config.get("perception.screen.enabled", False)
        self.monitor_screen_interval = self.config.get("perception.screen.interval_seconds", 2.0)
        self.screen_ocr_enabled = self.config.get("perception.screen.ocr_enabled", False)

    async def initialize(self):
        """Initialize the perception module"""
        self.logger.info("Initializing perception system")
        
        if self.monitor_clipboard_enabled:
            if _PYPERCLIP_AVAILABLE:
                self.clipboard_monitor_task = asyncio.create_task(self._monitor_clipboard())
                self.logger.info("Clipboard monitoring enabled.")
            else:
                self.logger.warning("pyperclip not installed. Clipboard monitoring disabled.")
                self.monitor_clipboard_enabled = False

        if self.monitor_screen_enabled:
            if _MSS_AVAILABLE and _PIL_AVAILABLE:
                self.screen_monitor_task = asyncio.create_task(self._monitor_screen())
                self.logger.info("Screen monitoring enabled.")
            else:
                self.logger.warning("mss or Pillow not installed. Screen monitoring disabled.")
                self.monitor_screen_enabled = False
        
        self.logger.info("Perception system initialized")
    
    async def _monitor_clipboard(self) -> None:
        """Continuously monitors the clipboard for changes and publishes raw events."""
        self.logger.debug("Starting clipboard monitor task.")
        while True:
            try:
                current_content = pyperclip.paste()
                if current_content != self.last_clipboard_content:
                    content_length = len(current_content)
                    if content_length > self.clipboard_max_chars:
                        self.logger.warning(f"Clipboard content too large ({content_length} chars), truncating for raw event.")
                        display_content = current_content[:self.clipboard_max_chars]
                    else:
                        display_content = current_content
                    
                    self.logger.debug(f"Clipboard changed ({content_length} chars). Publishing raw event.")
                    await self.publish("perception.raw.clipboard_changed", {
                        "content": display_content,
                        "length": content_length,
                        "timestamp": time.time(),
                        "context": {"active_file": None, "active_directory": None},
                        "source_module": self.name
                    })
                    self.last_clipboard_content = current_content
                
                await asyncio.sleep(self.monitor_clipboard_interval)
            except asyncio.CancelledError:
                self.logger.info("Clipboard monitor task cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in clipboard monitor: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _monitor_screen(self) -> None:
        """Continuously monitors the screen for changes and publishes raw events."""
        self.logger.debug("Starting screen monitor task.")
        with mss.mss() as sct:
            while True:
                try:
                    screenshot_bytes = sct.grab(sct.monitors[0])
                    current_image = Image.frombytes("RGB", screenshot_bytes.size, screenshot_bytes.rgb)

                    current_hash = self._calculate_image_hash(current_image)
                    change_percentage = 0.0

                    if self.last_screen_image:
                        change_percentage = self._calculate_image_diff(self.last_screen_image, current_image)
                    
                    text_content = ""
                    if self.screen_ocr_enabled:
                        try:
                            import pytesseract
                            text_content = pytesseract.image_to_string(current_image)
                            self.logger.debug(f"OCR extracted text (length: {len(text_content)}) from screen.")
                        except ImportError:
                            self.logger.warning("pytesseract not installed, cannot perform OCR. Install with `pip install pytesseract` and configure Tesseract.")
                            self.screen_ocr_enabled = False
                        except Exception as ocr_e:
                            self.logger.error(f"Error during OCR: {ocr_e}", exc_info=True)
                    
                    if current_hash != self.last_screen_hash or change_percentage > 0.01:
                        self.logger.debug(f"Screen changed (hash diff: {current_hash != self.last_screen_hash}, {change_percentage:.2f}% pixel change). Publishing raw event.")
                        await self.publish("perception.raw.screen_update", {
                            "image_hash": current_hash,
                            "change_percentage": change_percentage,
                            "text_content": text_content,
                            "image_ref": f"screen_capture_{int(time.time())}.png",
                            "timestamp": time.time(),
                            "context": {},
                            "source_module": self.name
                        })
                        self.last_screen_hash = current_hash
                        self.last_screen_image = current_image
                    
                    await asyncio.sleep(self.monitor_screen_interval)
                except asyncio.CancelledError:
                    self.logger.info("Screen monitor task cancelled.")
                    break
                except Exception as e:
                    self.logger.error(f"Error in screen monitor: {e}", exc_info=True)
                    await asyncio.sleep(5)

    def _calculate_image_hash(self, image: Image.Image) -> str:
        """Calculates a simple perceptual hash of an image for quick comparison."""
        small_image = image.resize((8, 8), Image.Resampling.LANCZOS).convert("L")
        pixels = list(small_image.getdata())
        avg = sum(pixels) / len(pixels)
        hash_bits = "".join(['1' if p > avg else '0' for p in pixels])
        return hash_bits

    def _calculate_image_diff(self, img1: Image.Image, img2: Image.Image) -> float:
        """Calculates the percentage difference between two images."""
        if img1.size != img2.size:
            return 1.0
        
        diff_pixels = 0
        img1_gray = img1.convert("L")
        img2_gray = img2.convert("L")

        for x in range(img1.width):
            for y in range(img1.height):
                if img1_gray.getpixel((x, y)) != img2_gray.getpixel((x, y)):
                    diff_pixels += 1
        
        return diff_pixels / (img1.width * img1.height)

    @on_event("perception.user_input")
    async def on_user_input(self, event: Event) -> None: # Type hint for Event
        """Handles user text input and publishes it as a raw perception event."""
        user_message = event.data.get("text", "")
        context = event.data.get("context", {})
        
        self.logger.info(f"Received user text input, publishing to raw channel: {user_message[:100]}...")
        await self.publish("perception.raw.user_input", {
            "text": user_message,
            "context": context,
            "timestamp": time.time(),
            "source_module": self.name
        })

    @on_event("perception.voice_input")
    async def on_voice_input(self, event: Event) -> None: # Type hint for Event
        """Handles voice input (transcript) and publishes it as a raw perception event."""
        transcript = event.data.get("transcript", "")
        context = event.data.get("context", {})

        self.logger.info(f"Received voice input transcript, publishing to raw channel: {transcript[:100]}...")
        await self.publish("perception.raw.user_input", {
            "text": transcript,
            "context": {**context, "modality": "voice"},
            "timestamp": time.time(),
            "source_module": self.name
        })

    @tool("take_screenshot", description="Captures the current screen as an image.", category="perception", parameters={})
    async def take_screenshot(self) -> Dict[str, Any]:
        """Tool to manually trigger a screenshot capture."""
        if not (_MSS_AVAILABLE and _PIL_AVAILABLE):
            return {"success": False, "error": "mss or Pillow not installed for screenshot."}
        
        self.logger.info("Tool 'take_screenshot' called.")
        with mss.mss() as sct:
            screenshot_bytes = sct.grab(sct.monitors[0])
            # In a real tool, you'd save this image and return a path/reference
            return {"success": True, "image_size": screenshot_bytes.size, "message": "Screenshot captured (raw bytes not returned via tool)."}


    async def shutdown(self):
        """Clean shutdown"""
        self.logger.info("Perception system shutting down...")
        if self.clipboard_monitor_task:
            self.clipboard_monitor_task.cancel()
            try: await self.clipboard_monitor_task
            except asyncio.CancelledError: pass
        if self.screen_monitor_task:
            self.screen_monitor_task.cancel()
            try: await self.screen_monitor_task
            except asyncio.CancelledError: pass
        
        await super().shutdown() # Call BaseModule's shutdown for periodic tasks etc.
        self.logger.info("Perception system shutdown complete")