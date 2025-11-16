"""
Perception Module - Real-Time Input Awareness

This module gives LOTUS awareness of:
- File system changes (watchdog)
- Clipboard content (pyperclip)
- Working context (inferred from activity)

This is what makes LOTUS feel "alive" - she sees what you're doing.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import time

from lib.module import BaseModule
from lib.decorators import on_event, periodic

try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler, FileSystemEvent,
        FileCreatedEvent, FileModifiedEvent, FileDeletedEvent
    )
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class FileChangeHandler(FileSystemEventHandler):
    """Handler for file system events"""
    
    def __init__(self, module: 'PerceptionModule'):
        self.module = module
        self.last_events: Dict[str, float] = {}
        self.debounce = module.config.get("perception.file_watching.debounce_seconds", 2)
        
    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self._handle_event("created", event.src_path)
    
    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self._handle_event("modified", event.src_path)
    
    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            self._handle_event("deleted", event.src_path)
    
    def _handle_event(self, event_type: str, path: str):
        """Debounce and handle file events"""
        now = time.time()
        key = f"{event_type}:{path}"
        
        # Check debounce
        if key in self.last_events:
            if now - self.last_events[key] < self.debounce:
                return
        
        self.last_events[key] = now
        
        # Queue event for async processing
        asyncio.create_task(
            self.module._handle_file_event(event_type, path)
        )


class PerceptionModule(BaseModule):
    """
    Perception System Coordinator
    
    Monitors:
    - File system changes
    - Clipboard content
    - Working context
    
    Provides real-time awareness of user activity.
    """
    
    async def initialize(self) -> None:
        """Initialize perception systems"""
        self.logger.info("Initializing perception system")
        
        # File watching
        self.observers: List[Observer] = []
        self.watched_paths: Set[Path] = set()
        self.file_watcher_enabled = self.config.get("perception.file_watching.enabled", True)
        
        # Clipboard monitoring
        self.last_clipboard = ""
        self.clipboard_enabled = self.config.get("perception.clipboard.enabled", True)
        self.clipboard_poll_interval = self.config.get("perception.clipboard.poll_interval", 1.0)
        
        # Context tracking
        self.current_context = {
            "active_file": None,
            "active_directory": None,
            "recent_files": [],
            "working_on": None,
            "last_activity": None
        }
        self.context_enabled = self.config.get("perception.context.enabled", True)
        
        # Statistics
        self.stats = {
            "files_watched": 0,
            "file_events": 0,
            "clipboard_changes": 0,
            "context_updates": 0
        }
        
        # Start watchers if enabled
        if self.file_watcher_enabled and WATCHDOG_AVAILABLE:
            await self._start_file_watchers()
        elif self.file_watcher_enabled and not WATCHDOG_AVAILABLE:
            self.logger.warning("File watching requested but watchdog not installed")
        
        # Check clipboard availability
        if self.clipboard_enabled and not CLIPBOARD_AVAILABLE:
            self.logger.warning("Clipboard monitoring requested but pyperclip not installed")
            self.clipboard_enabled = False
        
        self.logger.info("Perception system initialized")
    
    async def _start_file_watchers(self) -> None:
        """Start watching configured paths"""
        watch_paths = self.config.get("perception.file_watching.watch_paths", [])
        
        for path_str in watch_paths:
            # Expand user home directory
            path = Path(path_str).expanduser()
            
            if path.exists():
                await self._watch_path(path)
            else:
                self.logger.warning(f"Watch path does not exist: {path}")
    
    async def _watch_path(self, path: Path) -> None:
        """Start watching a specific path"""
        if path in self.watched_paths:
            self.logger.debug(f"Already watching: {path}")
            return
        
        try:
            observer = Observer()
            handler = FileChangeHandler(self)
            observer.schedule(handler, str(path), recursive=True)
            observer.start()
            
            self.observers.append(observer)
            self.watched_paths.add(path)
            self.stats["files_watched"] += 1
            
            self.logger.info(f"Started watching: {path}")
            
        except Exception as e:
            self.logger.error(f"Failed to watch {path}: {e}")
    
    @on_event("perception.start_watching")
    async def handle_start_watching(self, event: Dict[str, Any]) -> None:
        """
        Start watching a new path
        
        Event data:
        {
            "path": "/path/to/watch"
        }
        """
        path_str = event.get("path")
        if path_str:
            path = Path(path_str).expanduser()
            await self._watch_path(path)
    
    @on_event("perception.stop_watching")
    async def handle_stop_watching(self, event: Dict[str, Any]) -> None:
        """
        Stop watching a path
        
        Event data:
        {
            "path": "/path/to/stop"
        }
        """
        path_str = event.get("path")
        if path_str:
            path = Path(path_str).expanduser()
            await self._unwatch_path(path)
    
    async def _unwatch_path(self, path: Path) -> None:
        """Stop watching a specific path"""
        if path not in self.watched_paths:
            return
        
        # Find and stop the observer for this path
        for observer in self.observers:
            try:
                observer.stop()
                observer.join()
                self.observers.remove(observer)
                break
            except Exception as e:
                self.logger.error(f"Error stopping observer: {e}")
        
        self.watched_paths.remove(path)
        self.logger.info(f"Stopped watching: {path}")
    
    async def _handle_file_event(self, event_type: str, path: str) -> None:
        """Process file system event"""
        # Check ignore patterns
        ignore_patterns = self.config.get("perception.file_watching.ignore_patterns", [])
        if any(pattern in path for pattern in ignore_patterns):
            return
        
        self.stats["file_events"] += 1
        
        # Update context
        await self._update_context_from_file(path)
        
        # Publish event
        await self.publish(f"file.{event_type}", {
            "path": path,
            "timestamp": datetime.now().isoformat(),
            "context": self.current_context
        })
        
        self.logger.debug(f"File {event_type}: {path}")
    
    @periodic(interval=1.0)
    async def monitor_clipboard(self) -> None:
        """Monitor clipboard for changes"""
        if not self.clipboard_enabled:
            return
        
        try:
            current = pyperclip.paste()
            
            # Check if changed
            if current != self.last_clipboard and current:
                # Check size limit
                max_size = self.config.get("perception.clipboard.max_size", 10000)
                if len(current) > max_size:
                    self.logger.debug("Clipboard content too large, ignoring")
                    return
                
                # Check ignore patterns
                ignore_patterns = self.config.get("perception.clipboard.ignore_patterns", [])
                if any(pattern.lower() in current.lower() for pattern in ignore_patterns):
                    self.logger.debug("Clipboard content matched ignore pattern")
                    return
                
                self.last_clipboard = current
                self.stats["clipboard_changes"] += 1
                
                # Update context
                await self._update_context_from_clipboard(current)
                
                # Publish event
                await self.publish("clipboard.changed", {
                    "content": current[:1000],  # Truncate for event
                    "length": len(current),
                    "timestamp": datetime.now().isoformat(),
                    "context": self.current_context
                })
                
                self.logger.debug(f"Clipboard changed ({len(current)} chars)")
                
        except Exception as e:
            self.logger.error(f"Clipboard monitoring error: {e}")
    
    @periodic(interval=10)
    async def update_context(self) -> None:
        """Periodic context update"""
        if not self.context_enabled:
            return
        
        # Context inference logic would go here
        # For now, just track that we're updating
        self.stats["context_updates"] += 1
        
        # Could analyze recent files, clipboard, etc to infer what user is working on
    
    async def _update_context_from_file(self, path: str) -> None:
        """Update working context from file activity"""
        path_obj = Path(path)
        
        # Update active file
        self.current_context["active_file"] = str(path_obj)
        self.current_context["active_directory"] = str(path_obj.parent)
        self.current_context["last_activity"] = datetime.now().isoformat()
        
        # Add to recent files
        recent = self.current_context.get("recent_files", [])
        if str(path_obj) not in recent:
            recent.insert(0, str(path_obj))
            self.current_context["recent_files"] = recent[:10]  # Keep last 10
        
        # Try to infer what they're working on
        if self.config.get("perception.context.infer_from_files", True):
            self._infer_working_on(path_obj)
    
    async def _update_context_from_clipboard(self, content: str) -> None:
        """Update context from clipboard content"""
        self.current_context["last_activity"] = datetime.now().isoformat()
        
        # Try to infer context from clipboard content
        if self.config.get("perception.context.infer_from_clipboard", True):
            self._infer_from_clipboard(content)
    
    def _infer_working_on(self, path: Path) -> None:
        """Infer what user is working on from file path"""
        # Simple heuristics - could be much more sophisticated
        if "project" in str(path).lower():
            self.current_context["working_on"] = "project"
        elif any(ext in path.suffix for ext in [".py", ".js", ".ts", ".java"]):
            self.current_context["working_on"] = "coding"
        elif any(ext in path.suffix for ext in [".md", ".txt", ".doc"]):
            self.current_context["working_on"] = "writing"
        elif any(ext in path.suffix for ext in [".csv", ".xlsx", ".json"]):
            self.current_context["working_on"] = "data_analysis"
    
    def _infer_from_clipboard(self, content: str) -> None:
        """Infer context from clipboard content"""
        # Simple keyword matching
        if "def " in content or "function " in content or "class " in content:
            self.current_context["working_on"] = "coding"
        elif "https://" in content:
            self.current_context["working_on"] = "research"
    
    async def shutdown(self) -> None:
        """Shutdown perception system"""
        self.logger.info("Shutting down perception system")
        
        # Stop all file watchers
        for observer in self.observers:
            try:
                observer.stop()
                observer.join()
            except Exception as e:
                self.logger.error(f"Error stopping observer: {e}")
        
        self.logger.info("Perception system shutdown complete")