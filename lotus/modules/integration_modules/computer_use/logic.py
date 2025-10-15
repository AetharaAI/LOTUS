"""
Computer Use Module - Direct Computer Control

This module provides Ash with the ability to control the computer directly:
- Screen capture and monitoring
- Mouse control (move, click)
- Keyboard control (type, press keys)
- Vision-based UI understanding
- Integration with Anthropic's Computer Use API

This gives Ash true agency in interacting with the computer.
"""

import asyncio
import base64
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib

import pyautogui
import mss
from PIL import Image
import numpy as np

from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic


@dataclass
class ScreenState:
    """Represents current screen state"""
    timestamp: datetime
    screenshot: Image.Image
    screenshot_hash: str
    active_window: Optional[str]
    resolution: Tuple[int, int]
    cursor_position: Tuple[int, int]


@dataclass
class ComputerAction:
    """Represents a computer control action"""
    action_type: str  # screenshot, mouse_move, mouse_click, key_press, type_text
    parameters: Dict[str, Any]
    timestamp: datetime
    success: bool = False
    error: Optional[str] = None


class ComputerUse(BaseModule):
    """
    Computer Control Module
    
    Provides direct computer interaction capabilities through:
    - Screen capture and monitoring
    - Mouse and keyboard control
    - UI element detection
    - Vision-based understanding
    
    Integrates with Anthropic's Computer Use API for Claude-powered
    computer control.
    """
    
    async def initialize(self):
        """Initialize computer control"""
        self.logger.info("Initializing Computer Use module")
        
        # Screen capture
        self.sct = mss.mss()
        self.last_screenshot = None
        self.last_screenshot_hash = None
        
        # Current screen state
        self.current_state = None
        
        # Action history
        self.action_history = []
        
        # Safety checks
        self.safety_enabled = True
        self.forbidden_areas = self.config.get("mouse.safety.forbidden_areas", [])
        
        # Configure PyAutoGUI safety
        pyautogui.PAUSE = 0.1  # Pause between actions
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        
        # Start screen monitoring if enabled
        if self.config.get("screen_capture.enabled", True):
            asyncio.create_task(self._screen_monitoring_loop())
        
        self.logger.info("Computer Use module initialized")
    
    # ========================================
    # EVENT HANDLERS
    # ========================================
    
    @on_event("cognition.computer_action")
    async def on_computer_action(self, event):
        """Handle computer action requests from reasoning engine"""
        action_type = event.data.get("action")
        params = event.data.get("params", {})
        
        result = await self.execute_action(action_type, params)
        
        await self.publish("computer.action_complete", {
            "action": action_type,
            "success": result.success,
            "error": result.error
        })
    
    @on_event("perception.screen_request")
    async def on_screen_request(self, event):
        """Handle screen capture requests"""
        screenshot = await self.capture_screenshot()
        
        await self.publish("computer.screenshot_captured", {
            "timestamp": datetime.now().isoformat(),
            "screenshot": screenshot
        })
    
    # ========================================
    # SCREEN CAPTURE
    # ========================================
    
    async def capture_screenshot(
        self,
        monitor: int = 1,
        region: Optional[Dict] = None
    ) -> Image.Image:
        """
        Capture screenshot
        
        Args:
            monitor: Monitor number (1 = primary)
            region: Optional region {"x": 0, "y": 0, "width": 100, "height": 100}
        
        Returns:
            PIL Image
        """
        try:
            # Capture screen
            if region:
                screenshot = self.sct.grab(region)
            else:
                screenshot = self.sct.grab(self.sct.monitors[monitor])
            
            # Convert to PIL Image
            img = Image.frombytes(
                "RGB",
                screenshot.size,
                screenshot.bgra,
                "raw",
                "BGRX"
            )
            
            # Resize if configured
            if self.config.get("screen_capture.resize", True):
                max_width = self.config.get("screen_capture.max_width", 1280)
                max_height = self.config.get("screen_capture.max_height", 720)
                img.thumbnail((max_width, max_height), Image.LANCZOS)
            
            # Cache
            self.last_screenshot = img
            self.last_screenshot_hash = self._hash_image(img)
            
            return img
        
        except Exception as e:
            self.logger.error(f"Screenshot capture failed: {e}")
            raise
    
    def _hash_image(self, img: Image.Image) -> str:
        """Hash image for change detection"""
        img_bytes = img.tobytes()
        return hashlib.md5(img_bytes).hexdigest()
    
    async def _screen_monitoring_loop(self):
        """Background loop to monitor screen changes"""
        interval = self.config.get("screen_capture.interval_seconds", 2)
        change_detection = self.config.get("screen_capture.change_detection", True)
        
        while True:
            try:
                # Capture screenshot
                screenshot = await self.capture_screenshot()
                
                # Check for changes
                if change_detection and self.last_screenshot_hash:
                    current_hash = self._hash_image(screenshot)
                    
                    if current_hash != self.last_screenshot_hash:
                        # Screen changed
                        await self.publish("perception.screen_update", {
                            "timestamp": datetime.now().isoformat(),
                            "changed": True
                        })
                        
                        # Update state
                        await self._update_screen_state(screenshot)
                
                # Wait
                await asyncio.sleep(interval)
            
            except Exception as e:
                self.logger.error(f"Screen monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _update_screen_state(self, screenshot: Image.Image):
        """Update current screen state"""
        self.current_state = ScreenState(
            timestamp=datetime.now(),
            screenshot=screenshot,
            screenshot_hash=self._hash_image(screenshot),
            active_window=pyautogui.getActiveWindow().title if pyautogui.getActiveWindow() else None,
            resolution=screenshot.size,
            cursor_position=pyautogui.position()
        )
    
    # ========================================
    # MOUSE CONTROL
    # ========================================
    
    async def mouse_move(self, x: int, y: int, duration: float = 0.3) -> bool:
        """
        Move mouse cursor to position
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration: Movement duration (seconds)
        
        Returns:
            Success boolean
        """
        try:
            # Safety check
            if not self._is_safe_position(x, y):
                self.logger.warning(f"Mouse move to ({x}, {y}) blocked by safety rules")
                return False
            
            # Move cursor
            if self.config.get("mouse.movement.smooth", True):
                pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
            else:
                pyautogui.moveTo(x, y)
            
            self.logger.debug(f"Mouse moved to ({x}, {y})")
            return True
        
        except Exception as e:
            self.logger.error(f"Mouse move failed: {e}")
            return False
    
    async def mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1
    ) -> bool:
        """
        Click mouse button
        
        Args:
            x: X coordinate (None = current position)
            y: Y coordinate (None = current position)
            button: 'left', 'right', or 'middle'
            clicks: Number of clicks (1 or 2)
        
        Returns:
            Success boolean
        """
        try:
            # Safety check
            if x is not None and y is not None:
                if not self._is_safe_position(x, y):
                    self.logger.warning(f"Click at ({x}, {y}) blocked by safety rules")
                    return False
                
                # Move to position first
                await self.mouse_move(x, y)
            
            # Check if confirmation required
            if self.config.get("autonomy.require_confirmation", []):
                if "mouse_click" in self.config["autonomy"]["require_confirmation"]:
                    self.logger.info("Mouse click requires confirmation (not implemented)")
                    # In real system, would prompt user
            
            # Perform click
            pyautogui.click(button=button, clicks=clicks)
            
            self.logger.info(f"Mouse clicked at ({x or 'current'}, {y or 'current'})")
            return True
        
        except Exception as e:
            self.logger.error(f"Mouse click failed: {e}")
            return False
    
    def _is_safe_position(self, x: int, y: int) -> bool:
        """Check if mouse position is safe"""
        if not self.safety_enabled:
            return True
        
        # Check forbidden areas
        for area in self.forbidden_areas:
            if (area['x'] <= x <= area['x'] + area['width'] and
                area['y'] <= y <= area['y'] + area['height']):
                return False
        
        return True
    
    # ========================================
    # KEYBOARD CONTROL
    # ========================================
    
    async def type_text(self, text: str, interval: float = 0.05) -> bool:
        """
        Type text via keyboard
        
        Args:
            text: Text to type
            interval: Delay between keystrokes
        
        Returns:
            Success boolean
        """
        try:
            # Safety check
            if self._contains_forbidden_keys(text):
                self.logger.warning("Text contains forbidden key combinations")
                return False
            
            # Type text
            typing_speed = self.config.get("keyboard.safety.typing_speed", 0.05)
            pyautogui.write(text, interval=typing_speed)
            
            self.logger.debug(f"Typed text: {text[:50]}...")
            return True
        
        except Exception as e:
            self.logger.error(f"Type text failed: {e}")
            return False
    
    async def press_key(self, key: str, presses: int = 1) -> bool:
        """
        Press keyboard key
        
        Args:
            key: Key name (e.g., 'enter', 'tab', 'ctrl')
            presses: Number of times to press
        
        Returns:
            Success boolean
        """
        try:
            # Safety check
            if key in self.config.get("keyboard.safety.forbidden_keys", []):
                self.logger.warning(f"Key '{key}' is forbidden")
                return False
            
            # Press key
            pyautogui.press(key, presses=presses)
            
            self.logger.debug(f"Pressed key: {key}")
            return True
        
        except Exception as e:
            self.logger.error(f"Press key failed: {e}")
            return False
    
    async def key_combination(self, *keys: str) -> bool:
        """
        Press key combination
        
        Args:
            *keys: Keys to press together (e.g., 'ctrl', 'c')
        
        Returns:
            Success boolean
        """
        try:
            # Safety check
            combo = "+".join(keys)
            if combo in self.config.get("keyboard.safety.forbidden_keys", []):
                self.logger.warning(f"Key combination '{combo}' is forbidden")
                return False
            
            # Press combination
            pyautogui.hotkey(*keys)
            
            self.logger.debug(f"Pressed key combination: {combo}")
            return True
        
        except Exception as e:
            self.logger.error(f"Key combination failed: {e}")
            return False
    
    def _contains_forbidden_keys(self, text: str) -> bool:
        """Check if text contains forbidden key combinations"""
        # Simplified - real implementation would be more sophisticated
        return False
    
    # ========================================
    # VISION ANALYSIS
    # ========================================
    
    async def analyze_screen(
        self,
        analysis_type: str = "full"
    ) -> Dict[str, Any]:
        """
        Analyze screen content using vision model
        
        Args:
            analysis_type: Type of analysis
                - 'full': Complete screen analysis
                - 'ui_elements': Detect buttons, inputs, etc.
                - 'text': OCR text extraction
                - 'state': Application state detection
        
        Returns:
            Analysis results
        """
        if not self.current_state:
            # Capture screenshot first
            await self.capture_screenshot()
            await self._update_screen_state(self.last_screenshot)
        
        # Convert screenshot to base64 for vision API
        screenshot_b64 = self._image_to_base64(self.current_state.screenshot)
        
        # Build vision prompt based on analysis type
        prompt = self._build_vision_prompt(analysis_type)
        
        # Use vision-capable model
        provider = self.config.get("vision.provider", "claude-sonnet-4")
        
        response = await self.llm.complete(
            prompt=prompt,
            provider=provider,
            images=[screenshot_b64],
            temperature=0.3
        )
        
        # Parse response
        analysis = self._parse_vision_response(response.content, analysis_type)
        
        return analysis
    
    def _image_to_base64(self, img: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=90)
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def _build_vision_prompt(self, analysis_type: str) -> str:
        """Build prompt for vision analysis"""
        prompts = {
            "full": """Analyze this screenshot and describe:
1. What application/window is visible
2. What the user is doing
3. Any UI elements (buttons, inputs, etc.)
4. Any text content
5. Current state of the application""",
            
            "ui_elements": """Identify all UI elements in this screenshot:
- Buttons (with labels and positions)
- Input fields
- Dropdown menus
- Links
- Icons
Return as JSON with coordinates.""",
            
            "text": """Extract all visible text from this screenshot.
Include labels, menu items, dialog text, etc.
Organize by region if possible.""",
            
            "state": """Analyze the application state:
- What application is this?
- What is the user doing?
- Are there any errors or warnings?
- What actions are available?"""
        }
        
        return prompts.get(analysis_type, prompts["full"])
    
    def _parse_vision_response(
        self,
        response: str,
        analysis_type: str
    ) -> Dict[str, Any]:
        """Parse vision model response"""
        # Simplified parsing - real implementation would be more sophisticated
        return {
            "analysis_type": analysis_type,
            "content": response,
            "timestamp": datetime.now().isoformat()
        }
    
    # ========================================
    # HIGH-LEVEL ACTIONS
    # ========================================
    
    async def execute_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> ComputerAction:
        """
        Execute a computer action
        
        Routes to appropriate handler based on action type.
        """
        action = ComputerAction(
            action_type=action_type,
            parameters=parameters,
            timestamp=datetime.now()
        )
        
        try:
            if action_type == "screenshot":
                await self.capture_screenshot()
                action.success = True
            
            elif action_type == "mouse_move":
                success = await self.mouse_move(
                    parameters.get("x", 0),
                    parameters.get("y", 0)
                )
                action.success = success
            
            elif action_type == "mouse_click":
                success = await self.mouse_click(
                    parameters.get("x"),
                    parameters.get("y"),
                    parameters.get("button", "left")
                )
                action.success = success
            
            elif action_type == "type_text":
                success = await self.type_text(parameters.get("text", ""))
                action.success = success
            
            elif action_type == "press_key":
                success = await self.press_key(parameters.get("key", ""))
                action.success = success
            
            elif action_type == "analyze_screen":
                result = await self.analyze_screen(
                    parameters.get("analysis_type", "full")
                )
                action.success = True
            
            else:
                action.error = f"Unknown action type: {action_type}"
                action.success = False
        
        except Exception as e:
            action.error = str(e)
            action.success = False
            self.logger.error(f"Action execution failed: {e}")
        
        # Log action
        self.action_history.append(action)
        
        return action
    
    # ========================================
    # ANTHROPIC COMPUTER USE API INTEGRATION
    # ========================================
    
    async def use_computer_use_api(
        self,
        task_description: str
    ) -> Dict[str, Any]:
        """
        Use Anthropic's Computer Use API
        
        This leverages Claude's built-in computer control capabilities.
        Claude decides what actions to take autonomously.
        
        Args:
            task_description: What you want Claude to do
        
        Returns:
            Task result
        """
        # This would integrate with Anthropic's Computer Use API
        # which gives Claude direct computer control
        
        self.logger.info(f"Using Computer Use API for: {task_description}")
        
        # In a real implementation, this would:
        # 1. Send task to Claude with computer_use tool enabled
        # 2. Claude would autonomously execute actions
        # 3. Return results
        
        # For now, placeholder
        return {
            "task": task_description,
            "status": "Computer Use API integration pending"
        }
    
    # ========================================
    # TOOLS (exposed to other modules)
    # ========================================
    
    @tool("screenshot")
    async def tool_screenshot(self) -> str:
        """Capture screenshot"""
        img = await self.capture_screenshot()
        return self._image_to_base64(img)
    
    @tool("mouse_move")
    async def tool_mouse_move(self, x: int, y: int) -> bool:
        """Move mouse cursor"""
        return await self.mouse_move(x, y)
    
    @tool("mouse_click")
    async def tool_mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left"
    ) -> bool:
        """Click mouse"""
        return await self.mouse_click(x, y, button)
    
    @tool("type_text")
    async def tool_type_text(self, text: str) -> bool:
        """Type text"""
        return await self.type_text(text)
    
    @tool("press_key")
    async def tool_press_key(self, key: str) -> bool:
        """Press keyboard key"""
        return await self.press_key(key)
    
    @tool("analyze_screen")
    async def tool_analyze_screen(self, analysis_type: str = "full") -> Dict:
        """Analyze screen content"""
        return await self.analyze_screen(analysis_type)
    
    @tool("get_active_window")
    async def tool_get_active_window(self) -> str:
        """Get active window title"""
        window = pyautogui.getActiveWindow()
        return window.title if window else "Unknown"
    
    # ========================================
    # UTILITIES
    # ========================================
    
    @periodic(interval=300)  # Every 5 minutes
    async def periodic_state_update(self):
        """Update screen state periodically"""
        try:
            screenshot = await self.capture_screenshot()
            await self._update_screen_state(screenshot)
        except Exception as e:
            self.logger.error(f"Periodic state update failed: {e}")
    
    async def get_current_state(self) -> Optional[ScreenState]:
        """Get current screen state"""
        return self.current_state
    
    async def get_action_history(
        self,
        limit: int = 10
    ) -> List[ComputerAction]:
        """Get recent action history"""
        return self.action_history[-limit:]