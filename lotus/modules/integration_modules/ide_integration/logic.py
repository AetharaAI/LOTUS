"""IDE Integration Module"""
from lotus.lib.module import BaseModule
from lotus.lib.decorators import on_event, tool

class IDEIntegration(BaseModule):
    async def initialize(self) -> None:
        self.logger.info("💻 Initializing IDE Integration Module")
    
    @on_event("ide.open_file")
    async def open_file(self, event: dict) -> None:
        file_path = event.get("path")
        self.logger.info(f"📄 Opening: {file_path}")
    
    @tool("get_current_file")
    async def get_current_file(self) -> dict:
        return {"file": None, "line": 0}