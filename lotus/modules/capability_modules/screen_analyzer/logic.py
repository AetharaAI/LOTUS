"""
Screen Analyzer Module - Real-time Screen Capture & Analysis

Provides visual awareness by:
- Capturing screenshots
- Detecting changes
- Extracting text
- Analyzing UI elements
"""

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
import threading

try:
    import mss
    import pytesseract
    from PIL import Image
    import io
except ImportError as e:
    print(f"Warning: Screen analyzer dependencies not available: {e}")

from lib.module import BaseModule
from lib.decorators import on_event, periodic, tool
from lib.logging import get_logger

logger = get_logger("screen_analyzer")


@dataclass
class ScreenSnapshot:
    """Screen capture data"""
    timestamp: float
    resolution: Tuple[int, int]
    hash: str
    changed: bool = False
    text_content: Optional[str] = None
    elements: Optional[List[Dict]] = None
    raw_image: Optional[bytes] = None


class ScreenAnalyzer(BaseModule):
    """Real-time screen monitoring and analysis"""
    
    async def initialize(self) -> None:
        """Initialize screen analyzer"""
        self.logger.info("🎬 Initializing Screen Analyzer Module")
        
        self.monitoring = False
        self.last_snapshot: Optional[ScreenSnapshot] = None
        self.capture_interval = self.config.get("screen.capture_interval", 2)
        self.change_threshold = self.config.get("screen.change_threshold", 0.15)
        self.extract_text = self.config.get("screen.extract_text", True)
        
        try:
            self.screenshotter = mss.mss()
            self.logger.info("✅ Screen capture initialized (mss)")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize mss: {e}")
            self.screenshotter = None
    
    @on_event("perception.start_monitoring")
    async def start_monitoring(self, event: Dict[str, Any]) -> None:
        """Start continuous screen monitoring"""
        self.monitoring = True
        self.logger.info("📸 Started screen monitoring")
        await self.publish("perception.monitoring_started", {"module": "screen_analyzer"})
    
    @on_event("perception.stop_monitoring")
    async def stop_monitoring(self, event: Dict[str, Any]) -> None:
        """Stop screen monitoring"""
        self.monitoring = False
        self.logger.info("⏹️  Stopped screen monitoring")
        await self.publish("perception.monitoring_stopped", {"module": "screen_analyzer"})
    
    @on_event("perception.screen_analyze")
    async def analyze_screen(self, event: Dict[str, Any]) -> None:
        """Analyze current screen on demand"""
        self.logger.debug("🔍 Analyzing screen on demand")
        snapshot = await self._capture_screenshot()
        
        if snapshot:
            result = {
                "timestamp": snapshot.timestamp,
                "resolution": snapshot.resolution,
                "hash": snapshot.hash,
                "changed": snapshot.changed,
                "text": snapshot.text_content[:500] if snapshot.text_content else None,
                "element_count": len(snapshot.elements) if snapshot.elements else 0
            }
            await self.publish("perception.screen_analyzed", result)
    
    @periodic(interval=2, condition=lambda self: self.monitoring)
    async def monitor_screen(self) -> None:
        """Periodic screen monitoring"""
        snapshot = await self._capture_screenshot()
        
        if snapshot and snapshot.changed:
            self.logger.debug(f"🔄 Screen change detected (hash: {snapshot.hash[:8]}...)")
            
            change_info = {
                "timestamp": snapshot.timestamp,
                "hash": snapshot.hash,
                "resolution": snapshot.resolution,
                "text_changed": snapshot.text_content != (
                    self.last_snapshot.text_content if self.last_snapshot else None
                )
            }
            
            await self.publish("perception.screen_changed", change_info)
            
            if snapshot.text_content:
                await self.publish("perception.text_extracted", {
                    "text": snapshot.text_content,
                    "timestamp": snapshot.timestamp,
                    "length": len(snapshot.text_content)
                })
            
            if snapshot.elements:
                await self.publish("perception.elements_detected", {
                    "elements": snapshot.elements,
                    "count": len(snapshot.elements),
                    "timestamp": snapshot.timestamp
                })
        
        self.last_snapshot = snapshot
    
    async def _capture_screenshot(self) -> Optional[ScreenSnapshot]:
        """Capture current screen"""
        try:
            if not self.screenshotter:
                return None
            
            # Capture primary monitor
            monitor = self.screenshotter.monitors[1]
            screenshot = self.screenshotter.grab(monitor)
            
            # Convert to bytes
            image = Image.frombytes(
                'RGB',
                screenshot.size,
                screenshot.rgb
            )
            
            # Create hash for change detection
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='JPEG', quality=self.config.get("screen.jpeg_quality", 85))
            image_hash = hashlib.md5(image_bytes.getvalue()).hexdigest()
            
            # Extract text if enabled
            text_content = None
            if self.extract_text:
                try:
                    text_content = pytesseract.image_to_string(image)
                except Exception as e:
                    self.logger.debug(f"OCR failed: {e}")
            
            # Detect if screen changed
            changed = True
            if self.last_snapshot:
                # Simple hash-based change detection
                changed = image_hash != self.last_snapshot.hash
            
            snapshot = ScreenSnapshot(
                timestamp=time.time(),
                resolution=screenshot.size,
                hash=image_hash,
                changed=changed,
                text_content=text_content,
                raw_image=image_bytes.getvalue()
            )
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"❌ Screen capture failed: {e}")
            return None
    
    @tool("get_screen_text")
    async def get_screen_text(self) -> Dict[str, Any]:
        """Get current screen text via OCR"""
        snapshot = await self._capture_screenshot()
        return {
            "success": snapshot is not None,
            "text": snapshot.text_content if snapshot else None,
            "timestamp": snapshot.timestamp if snapshot else None
        }
    
    @tool("get_screen_hash")
    async def get_screen_hash(self) -> Dict[str, str]:
        """Get current screen hash for change detection"""
        snapshot = await self._capture_screenshot()
        return {
            "hash": snapshot.hash if snapshot else None,
            "timestamp": snapshot.timestamp if snapshot else None
        }