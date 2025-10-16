"""Browser Control Module"""
from lib.module import BaseModule
from lib.decorators import on_event, tool

class BrowserControl(BaseModule):
    async def initialize(self) -> None:
        self.logger.info("🌐 Initializing Browser Control Module")
    
    @on_event("browser.navigate")
    async def navigate(self, event: dict) -> None:
        url = event.get("url")
        self.logger.info(f"🔗 Navigating to: {url}")
    
    @tool("take_screenshot")
    async def take_screenshot(self) -> dict:
        return {"success": True, "path": "screenshot.png"}