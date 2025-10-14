"""
Hello World Example Module

This is a simple example module that demonstrates:
- Event handling with @on_event
- Tool registration with @tool
- Periodic tasks with @periodic
- Publishing events
- Module lifecycle (initialize, shutdown)

This serves as a template for creating new modules.
"""

from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic


class HelloWorld(BaseModule):
    """
    Example module that greets users
    
    Demonstrates basic module functionality:
    - Listening to events
    - Publishing events
    - Providing tools
    - Running periodic tasks
    """
    
    async def initialize(self):
        """
        Module initialization
        
        Called once when the module is loaded.
        Use this to:
        - Load saved state
        - Connect to external services
        - Preload data
        - Set up module-specific resources
        """
        self.logger.info(f"[{self.name}] Initializing...")
        
        # Module state
        self.greet_count = 0
        self.last_greeting = None
        
        # Get configuration
        self.greeting_message = self.config.get(
            f"modules.{self.name}.settings.greeting_message",
            default="Hello from LOTUS!"
        )
        
        self.auto_greet = self.config.get(
            f"modules.{self.name}.settings.auto_greet_on_startup",
            default=True
        )
        
        self.logger.info(f"[{self.name}] Initialized successfully")
    
    @on_event("system.ready")
    async def on_system_ready(self, event):
        """
        Handle system ready event
        
        This is called when LOTUS finishes booting.
        """
        self.logger.info(f"[{self.name}] System is ready!")
        
        # Auto-greet on startup if configured
        if self.auto_greet:
            await self.publish("action.speak", {
                "text": self.greeting_message,
                "source": self.name
            })
            
            await self.publish("example.hello_sent", {
                "count": 1,
                "message": self.greeting_message
            })
    
    @on_event("user.greeting")
    async def on_user_greeting(self, event):
        """
        Handle user greeting event
        
        Responds when user greets the system.
        """
        user_message = event.data.get("message", "")
        self.logger.info(f"[{self.name}] Received greeting: {user_message}")
        
        # Respond with a greeting
        response = f"Hey there! {self.greeting_message}"
        
        await self.publish("action.speak", {
            "text": response,
            "source": self.name
        })
        
        self.greet_count += 1
        self.last_greeting = user_message
    
    @tool("say_hello")
    async def say_hello(self, name: str) -> dict:
        """
        Tool: Say hello to someone
        
        This tool can be called by other modules or the reasoning engine.
        
        Args:
            name: Name to greet
        
        Returns:
            Dict with greeting message and metadata
        """
        greeting = f"Hello, {name}! {self.greeting_message}"
        
        self.logger.info(f"[{self.name}] Tool called: say_hello(name={name})")
        
        self.greet_count += 1
        
        return {
            "greeting": greeting,
            "name": name,
            "total_greetings": self.greet_count,
            "module": self.name
        }
    
    @tool("get_stats")
    async def get_stats(self) -> dict:
        """
        Tool: Get module statistics
        
        Returns:
            Dict with module stats
        """
        return {
            "module": self.name,
            "greet_count": self.greet_count,
            "last_greeting": self.last_greeting,
            "status": "active"
        }
    
    @periodic(interval=60)
    async def periodic_log(self):
        """
        Periodic task: Log status every 60 seconds
        
        Demonstrates periodic tasks that run in the background.
        """
        self.logger.debug(f"[{self.name}] Status: {self.greet_count} greetings sent")
    
    async def shutdown(self):
        """
        Module shutdown
        
        Called when the module is being unloaded or system is shutting down.
        Use this to:
        - Save state
        - Close connections
        - Clean up resources
        """
        self.logger.info(f"[{self.name}] Shutting down...")
        self.logger.info(f"[{self.name}] Total greetings: {self.greet_count}")
        
        # Call parent shutdown
        await super().shutdown()