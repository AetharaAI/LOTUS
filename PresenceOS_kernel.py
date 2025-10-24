# -*- coding: utf-8 -*-
import os
import sys
import site
import time
import uuid
import json
import logging
import importlib.util
import threading
import asyncio
import signal
import socket
import traceback
import copy
import itertools # Added for EventBus fix
from typing import Dict, List, Any, Optional, Callable, Union, TypeVar, Set, Coroutine, Tuple, TYPE_CHECKING
from modules.server_api_module.api_server_module import UIManagerModule
# from modules.system.ui_manager_module import UIManagerModule # Import UIManagerModule for type hinting if available
import aioredis

from core.llm_manager import LLMManager

from aioredis import Redis, RedisError
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file if it exists
# Import RedisStreamLogger for type hinting if available
try:
    from aetherpro_redis_stream_logger import RedisStreamLogger
    REDIS_STREAM_LOGGER_AVAILABLE = True
except ImportError:
    class RedisStreamLogger: pass  # Dummy fallback for type hints
    REDIS_STREAM_LOGGER_AVAILABLE = False
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

# --- Ensure cli.py can be found by PresenceKernel when it imports it ---
# This also helps if other modules within PresenceOS_kernel itself need to import relatively.
_kernel_dir_path = Path(__file__).resolve().parent
if str(_kernel_dir_path) not in sys.path:
    sys.path.insert(0, str(_kernel_dir_path))

# Attempt to import AsyncCommandLineInterface for type hinting within PresenceKernel
# This is a forward reference, actual instance created later.
# cli.py itself will import KernelAPI from this file.
#try:
 #   from cli import AsyncCommandLineInterface
#except ImportError:
    # This might happen if cli.py has issues or isn't found during initial parse of this file.
    # Define a dummy for type hinting purposes only if it fails.
    # The actual import for functionality happens in kernel.boot()
    class AsyncCommandLineInterface: pass # type: ignore
# --- End CLI Forward Reference ---


# --- Enums and Dataclasses ---
class SystemState(Enum):
    INITIALIZING = auto(); BOOTING = auto(); RUNNING = auto(); PAUSED = auto(); SHUTTING_DOWN = auto(); ERROR = auto()

class ModuleState(Enum):
    REGISTERED = auto(); LOADING = auto(); RUNNING = auto(); PAUSED = auto(); ERROR = auto(); STOPPED = auto(); UNREGISTERED = auto()

class Priority(Enum):
    CRITICAL = 0; HIGH = 1; NORMAL = 2; LOW = 3; BACKGROUND = 4

class EventType(Enum):
    SYSTEM_BOOT = auto(); SYSTEM_READY = auto(); SYSTEM_SHUTDOWN = auto(); SYSTEM_ERROR = auto()
    MODULE_REGISTERED = auto(); MODULE_LOADED = auto(); MODULE_STARTED = auto(); MODULE_STOPPED = auto()
    MODULE_ERROR = auto(); MODULE_UNREGISTERED = auto(); CONFIG_CHANGED = auto(); CUSTOM = auto()
    MESH_SIGNAL_RECEIVED = "MESH_SIGNAL_RECEIVED"
    MESH_SIGNAL_SEND_REQUEST = "MESH_SIGNAL_SEND_REQUEST"
    PRESENCE_METACOGNITION_PLANNING_REQUEST = "PRESENCE_METACOGNITION_PLANNING_REQUEST"
    PRESENCE_METACOGNITION_PLANNER_RESPONSE = "PRESENCE_METACOGNITION_PLANNER_RESPONSE"
@dataclass
class Event:
    event_type: Union[EventType, str]
    source: str
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: Priority = Priority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.name if isinstance(self.event_type, EventType) else self.event_type,
            "source": self.source,
            "timestamp": self.timestamp,
            "priority": self.priority.name,
            "data": copy.deepcopy(self.data)
        }

@dataclass
class ModuleInfo: # Ensure ModuleInfo is defined before ModuleLoader uses it
    id: str
    name: str
    version: str
    description: str
    path: str # Path to the module's directory
    module_class: str # The name of the class to instantiate
    dependencies: List[str] = field(default_factory=list)
    startup_priority: Priority = Priority.NORMAL
    config: Dict[str, Any] = field(default_factory=dict) # Default config from manifest
    state: ModuleState = ModuleState.REGISTERED
    instance: Optional[Any] = None # Optional['ModuleInterface'] - but forward ref issue
    error: Optional[str] = None



class QueueItem:
    """Wrapper for items put into the PriorityQueue to ensure correct comparison."""
    def __init__(self, priority: int, timestamp: Optional[Union[float, int]], count: int, event: Optional[Event]):
        self.priority = priority
        # Handle timestamp as either a float/int or a dictionary
        if isinstance(timestamp, dict):
            timestamp = timestamp.get('timestamp') or timestamp.get("time")
        if not isinstance(timestamp, (float, int)):
            self.timestamp = time.time()  # Default to current time if invalid
        else:
            self.timestamp = float(timestamp)
        self.count = count
        self.event = event

    def __lt__(self, other: 'QueueItem') -> bool:
        """Less-than comparison for heapq (PriorityQueue)."""
        if not isinstance(other, QueueItem):
            return NotImplemented
        # Compare by priority first
        if self.priority != other.priority:
            return self.priority < other.priority
        # Compare by timestamp if priorities are equal
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        # Tie-breaker: Compare by count
        return self.count < other.count


# PresenceOS_kernel.py

# ... (all your existing imports and other classes like Event, QueueItem etc. come before this) ...

# --- AsyncEventBus ---
class AsyncEventBus:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.subscribers: Dict[str, Dict[str, Callable[[Event], Coroutine[Any, Any, None]]]] = {}
        # YOU ARE USING Tuple[int, float, int, Event] for the queue, which is fine.
        # My QueueItem was an example, stick to your current PriorityQueue type.
        self.event_queue: asyncio.PriorityQueue[Tuple[int, float, int, Optional[Event]]] = asyncio.PriorityQueue() # Allow Optional[Event] for shutdown
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()
        self.event_history: List[Event] = []
        self.history_max_size = 1000
        self._counter = itertools.count() 

    async def start(self):
        if not self._running:
            self._running = True
            if not self._processor_task or self._processor_task.done():
                # ADD "EVENT_BUS:" prefix to your existing logs for clarity
                self.logger.info("EVENT_BUS: Starting Async EventBus processor task...")
                self._processor_task = asyncio.create_task(self._event_processor(), name="AsyncEventBusProcessor")
            else:
                self.logger.warning("EVENT_BUS: Start called, but task already running.")
        else:
            self.logger.info("EVENT_BUS: Already started.")

    async def stop(self):
        if self._running:
            self.logger.info("EVENT_BUS: Stopping Async EventBus...")
            self._running = False
            try:
                # Use your existing QueueItem structure if that's how you signal shutdown,
                # or use a simple tuple that matches your PriorityQueue type.
                # The key is that event is None and priority is special.
                await self.event_queue.put((-1, time.time(), next(self._counter), None)) 
            except asyncio.QueueFull:
                 self.logger.warning("EVENT_BUS: Async event queue full during stop signal.")

            if self._processor_task and not self._processor_task.done():
                try:
                    self.logger.info("EVENT_BUS: Waiting for processor task to finish...")
                    await asyncio.wait_for(self._processor_task, timeout=5.0) # Increased timeout slightly
                except asyncio.TimeoutError:
                    self.logger.warning("EVENT_BUS: Processor task did not stop cleanly. Cancelling.")
                    self._processor_task.cancel()
                    try: await self._processor_task
                    except asyncio.CancelledError: self.logger.info("EVENT_BUS: Processor task cancel acknowledged.")
                except Exception as e: self.logger.error(f"EVENT_BUS: Error waiting for event bus task: {e}")
            self.logger.info("EVENT_BUS: Stopped.")
        else:
            self.logger.info("EVENT_BUS: Already stopped.")

    async def subscribe(self, event_type: Union[EventType, str, List[Union[EventType, str]]],
                       callback: Callable[[Event], Coroutine[Any, Any, None]], subscriber_id: str) -> None:
        async with self.lock:
            types_to_subscribe = event_type if isinstance(event_type, (list, tuple)) else [event_type]
            for et in types_to_subscribe:
                event_key = et.name if isinstance(et, EventType) else str(et)
                if event_key not in self.subscribers: self.subscribers[event_key] = {}
                
                if subscriber_id in self.subscribers[event_key]:
                    self.logger.warning(f"EVENT_BUS_SUBSCRIBE: Subscriber '{subscriber_id}' already subscribed to '{event_key}'. Overwriting callback.")
                
                self.subscribers[event_key][subscriber_id] = callback
                # --- ADD THIS LOG ---
                self.logger.info(f"EVENT_BUS_SUBSCRIBE: Subscriber '{subscriber_id}' registered for event_type '{event_key}' with callback '{callback.__name__}'. Current listeners for this type: {list(self.subscribers.get(event_key, {}).keys())}")
                # self.logger.debug(f"Subscriber '{subscriber_id}' registered for event '{event_key}'.") # Your old log, keep if you like or remove

    async def unsubscribe(self, event_type: Union[EventType, str, List[Union[EventType, str]]],
                         subscriber_id: str) -> None:
        async with self.lock:
            types_to_unsubscribe = event_type if isinstance(event_type, (list, tuple)) else [event_type]
            for et in types_to_unsubscribe:
                event_key = et.name if isinstance(et, EventType) else str(et)
                if event_key in self.subscribers and subscriber_id in self.subscribers[event_key]:
                    del self.subscribers[event_key][subscriber_id]
                     # --- ADD THIS LOG (or modify existing) ---
                    self.logger.info(f"EVENT_BUS_UNSUBSCRIBE: Subscriber '{subscriber_id}' unregistered from event '{event_key}'.")
                    if not self.subscribers[event_key]: 
                        del self.subscribers[event_key]
                        self.logger.info(f"EVENT_BUS_UNSUBSCRIBE: No more subscribers for event '{event_key}', removing key.")


    async def unsubscribe_all(self, subscriber_id: str) -> None:
        async with self.lock:
            unsubscribed_from = []
            for event_key in list(self.subscribers.keys()):
                if subscriber_id in self.subscribers.get(event_key, {}):
                    del self.subscribers[event_key][subscriber_id]
                    unsubscribed_from.append(event_key)
                    if not self.subscribers[event_key]: 
                        del self.subscribers[event_key]
            if unsubscribed_from:
                 # --- ADD THIS LOG (or modify existing) ---
                self.logger.info(f"EVENT_BUS_UNSUBSCRIBE_ALL: Subscriber '{subscriber_id}' unregistered from events: {unsubscribed_from}.")

  
    async def publish(self, event: Event) -> None:

#        event_type_name = event.event_type_name_for_log()
 #       source_id = event.source_for_log()
  #      priority_name = event.priority.name if isinstance(event.priority, Enum) else str(event.priority)

        event_type_name = event.event_type.name if isinstance(event.event_type, Enum) else str(event.event_type)
        source_id = str(event.source) # Ensure source is a string for logging
        data_summary = list(event.data.keys()) if isinstance(event.data, dict) else type(event.data)
        priority_name = event.priority.name if isinstance(event.priority, Enum) else str(event.priority)
        
        # --- ADD THIS LOG (THIS IS THE CRITICAL ONE FOR PUBLISH) ---
        self.logger.info(f"EVENT_BUS_PUBLISH_CALLED: Event '{event_type_name}' from '{source_id}'. Data keys/type: {data_summary}. Priority: {priority_name}. Full Data (first 200 chars): {str(event.data)[:200]}")


            # Ensure 'event' IS an Event instance and its timestamp is a float
        if not isinstance(event, Event):
            self.logger.error(f"EVENT_BUS_PUBLISH_TYPE_ERROR: Attempted to publish non-Event object: {type(event)}. Event: {str(event)[:200]}")
            return # Do not queue
            
            # THIS IS THE MOST IMPORTANT CHECK NOW
        if not isinstance(event.timestamp, float):
            event_type_name_log = event.event_type.name if isinstance(event.event_type, EventType) else str(event.event_type)
            self.logger.error(f"EVENT_BUS_TIMESTAMP_TYPE_ERROR: Event object (ID: {event.id}, Source: {event.source}, Type: {event_type_name_log}) has non-float timestamp: {type(event.timestamp)} VALUE: {event.timestamp}")
                # Forcing a crash here during debugging might be useful to get a full stack trace
                # of where this bad event originated if the logger isn't enough.
                # raise TypeError(f"CRITICAL: Event {event.id} from {event.source} has bad timestamp type {type(event.timestamp)}") 
            
        item_for_queue = (
            event.priority.value,
            event.timestamp,       # This is the critical field
            next(self._counter),
            event
            )
            # ... rest of the logging and put ...


        # --- REMOVE OR COMMENT OUT THIS SPECIFIC IF BLOCK ---
        # if event.event_type == "presence_memory:history:get_request":
        # # Ensure event.source is the module_id
        #     source_id = event.source if isinstance(event.source, str) else getattr(event.source, 'module_id', 'UnknownSource')
        #     self.logger.info(f"EventBus: Publishing '{event.event_type}' from '{source_id}'. Data: {event.data}")
        # --- END OF BLOCK TO REMOVE/COMMENT ---

        if not self._running:
            self.logger.warning(f"EVENT_BUS_PUBLISH_SKIPPED: EventBus is not running. Event type: {event_type_name}")
            return
        
        self.event_history.append(event) # Consider lock if accessed concurrently
        if len(self.event_history) > self.history_max_size:
            self.event_history.pop(0)
            
        try:
            timestamp = event.timestamp # Already a float from Event dataclass default_factory
            priority_val = event.priority.value # Already an int from Priority Enum
            
            # Using your original Tuple structure for the queue
            await self.event_queue.put((priority_val, timestamp, next(self._counter), event))
            self.logger.debug(f"EVENT_BUS_QUEUED: Event '{event_type_name}' from '{source_id}' successfully queued.")
        except Exception as e:
            self.logger.error(f"EVENT_BUS_QUEUE_FAIL: Failed to queue event {event_type_name}: {e}", exc_info=True)

    # In AsyncEventBus.publish from PresenceOS_kernel.py



    async def _event_processor(self) -> None:
        self.logger.info("EVENT_BUS_PROCESSOR: Task started.")
        while self._running or not self.event_queue.empty():
            try:
                # Get from queue - your queue stores Tuples
                priority_val, ts, count, event_obj = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)

                if event_obj is None and priority_val == -1:  # Shutdown signal
                    self.logger.info("EVENT_BUS_PROCESSOR: Shutdown signal received.")
                    if not self._running:
                        self.logger.info("EVENT_BUS_PROCESSOR: _running is False, exiting processor loop.")
                        self.event_queue.task_done()
                        break 
                    else:
                        self.logger.warning("EVENT_BUS_PROCESSOR: Shutdown signal received but _running is True. Task_done and continuing.")
                        self.event_queue.task_done()
                        continue

                if event_obj:
                    event_to_process = event_obj # This is your Event instance
                    event_type_name = event_to_process.event_type.name if isinstance(event_to_process.event_type, EventType) else str(event_to_process.event_type)
                    source_id = str(event_to_process.source)
                    req_id_from_data = event_to_process.data.get('request_id', 'N/A_IN_PROCESS') if isinstance(event_to_process.data, dict) else 'N/A_DATA_NOT_DICT'
                    
                    # --- ADD THIS LOG ---
                    self.logger.info(f"EVENT_BUS_PROCESSOR_DEQUEUED: Event '{event_type_name}' for ReqID '{req_id_from_data}' from source '{source_id}'.")
                    await self._process_event(event_to_process)
                    self.event_queue.task_done()

            except asyncio.TimeoutError:
                if not self._running and self.event_queue.empty():
                    self.logger.info("EVENT_BUS_PROCESSOR: Timeout, not running, and queue empty. Exiting.")
                    break
                continue
            except asyncio.CancelledError:
                self.logger.info("EVENT_BUS_PROCESSOR: Task cancelled.")
                break
            except Exception as e:
                self.logger.error(f"EVENT_BUS_PROCESSOR: Error in loop: {e}", exc_info=True)
                await asyncio.sleep(0.01) 
        self.logger.info("EVENT_BUS_PROCESSOR: Task finished.")
    

    async def _process_event(self, event: Event) -> None:
        event_key = event.event_type.name if isinstance(event.event_type, EventType) else str(event.event_type)
        
        dispatch_info: List[Tuple[str, str, Coroutine[Any,Any,None]]] = []

        async with self.lock: 
            sub_dict_for_key = self.subscribers.get(event_key)
            if sub_dict_for_key:
                # --- ADD THIS LOG ---
                self.logger.info(f"EVENT_BUS_DISPATCHING: Event '{event_key}'. Found subscribers for specific type: {list(sub_dict_for_key.keys())}")
                for sub_id, callback in sub_dict_for_key.items():
                    # Ensure callback is awaitable
                    if asyncio.iscoroutinefunction(callback):
                        dispatch_info.append((sub_id, callback.__name__, callback(event)))
                    else:
                        self.logger.error(f"EVENT_BUS_DISPATCH_ERROR: Callback for {sub_id} on event {event_key} is not an async function: {callback.__name__}")
            # else: # This else would log for every event with no subscribers, can be noisy.
                # self.logger.debug(f"EVENT_BUS_DISPATCHING: Event '{event_key}'. No specific subscribers found.")

            # Wildcard subscribers - your current code has this, keeping it
            if '*' in self.subscribers:
                self.logger.info(f"EVENT_BUS_DISPATCHING: Event '{event_key}'. Checking wildcard '*' subscribers: {list(self.subscribers['*'].keys())}")
                processed_for_wildcard = set(item[0] for item in dispatch_info) # IDs already added for specific type
                for sub_id, callback in self.subscribers['*'].items():
                    if sub_id not in processed_for_wildcard: 
                        if asyncio.iscoroutinefunction(callback):
                            dispatch_info.append((sub_id, callback.__name__ + " (wildcard)", callback(event)))
                        else:
                             self.logger.error(f"EVENT_BUS_DISPATCH_ERROR: Wildcard callback for {sub_id} on event {event_key} is not an async function: {callback.__name__}")
        
        if dispatch_info:
            for sub_id, cb_name, _ in dispatch_info:
                 self.logger.info(f"EVENT_BUS_DISPATCHING_TO: Event '{event_key}' -> Subscriber '{sub_id}' with callback '{cb_name}'")
            
            coroutines = [item[2] for item in dispatch_info]
            results = await asyncio.gather(*coroutines, return_exceptions=True)
            
            for i, result in enumerate(results):
                sub_id_res, cb_name_res, _ = dispatch_info[i]
                if isinstance(result, Exception):
                    self.logger.error(f"EVENT_BUS_DISPATCH_EXCEPTION: Error executing subscriber callback '{cb_name_res}' for '{sub_id_res}' on event '{event_key}': {result}", exc_info=result)
                else:
                    self.logger.debug(f"EVENT_BUS_DISPATCH_SUCCESS: Callback '{cb_name_res}' for '{sub_id_res}' on event '{event_key}' completed.")
        elif not sub_dict_for_key and '*' not in self.subscribers: # Only log if no specific AND no wildcard listeners
             self.logger.debug(f"EVENT_BUS_DISPATCHING: No callbacks (specific or wildcard) to run for event '{event_key}'.")


    def get_event_history(self, count: Optional[int] = None, event_type: Optional[Union[EventType, str]] = None) -> List[Event]:
        history_snapshot = list(self.event_history)
        if event_type is not None:
            key_filter = event_type.name if isinstance(event_type, EventType) else str(event_type)
            history_snapshot = [e for e in history_snapshot if (isinstance(e.event_type, EventType) and e.event_type.name == key_filter) or (isinstance(e.event_type, str) and e.event_type == key_filter)]
        return history_snapshot[-count:] if count is not None and count >= 0 else history_snapshot

# --- (Rest of your PresenceOS_kernel.py) ---





#

# --- ConfigManager ---
class ConfigManager:
    def __init__(self, config_dir: str, logger: logging.Logger):
        self.config_dir = Path(config_dir).resolve()
        self.logger = logger
        self.system_config_file = self.config_dir / "system_config.json"
        self.module_config_dir = self.config_dir / "modules"
        self.event_bus: Optional[AsyncEventBus] = None
        self._config_lock = threading.RLock() # RLock for re-entrant scenarios if any

        self.system_config: Dict[str, Any] = {
            "log_level": "INFO", "log_file": "presenceos.log", "modules_dir": "modules",
            "enable_diagnostics": True, "health_check_interval": 60, "history_size": 1000,
            "autostart_modules": True, "module_timeout": 60 # Example new default
        }
        self.module_configs: Dict[str, Dict[str, Any]] = {} # Cache for loaded module configs

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.module_config_dir.mkdir(exist_ok=True)
        except OSError as e:
            self.logger.critical(f"FATAL: Failed to create config directories: {e}", exc_info=True)
            raise
        self._load_system_config()

    def set_event_bus(self, event_bus: AsyncEventBus) -> None: self.event_bus = event_bus

    def _load_system_config(self) -> None:
        with self._config_lock:
            if self.system_config_file.is_file():
                try:
                    with open(self.system_config_file, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                    self.system_config.update(loaded_config) # Update defaults with loaded values
                    self.logger.info(f"System config loaded from {self.system_config_file}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error decoding system_config.json: {e}. Using defaults/previous.")
                except Exception as e:
                    self.logger.error(f"Error loading system config: {e}. Using defaults/previous.", exc_info=True)
            else:
                self.logger.info("System config file not found. Saving default system configuration.")
                self._save_system_config() # Save defaults if file doesn't exist

    def _save_system_config(self) -> None:
        # Assumes lock is held or called from a context that holds it
        try:
            with open(self.system_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.system_config, f, indent=4, sort_keys=True)
            self.logger.info(f"System config saved to {self.system_config_file}")
        except Exception as e:
            self.logger.error(f"Error saving system config: {e}", exc_info=True)

    def get_system_config(self) -> Dict[str, Any]:
        with self._config_lock:
            return copy.deepcopy(self.system_config)

    async def update_system_config(self, config_updates: Dict[str, Any]) -> None:
        changed_keys = []
        with self._config_lock:
            for key, value in config_updates.items():
                if self.system_config.get(key) != value:
                    self.system_config[key] = value
                    changed_keys.append(key)
            if changed_keys:
                self.logger.info(f"System config updated for keys: {changed_keys}. Saving.")
                self._save_system_config()
        
        if changed_keys and self.event_bus:
            await self.event_bus.publish(Event(
                EventType.CONFIG_CHANGED, "ConfigManager",
                data={"config_type": "system", "changes": changed_keys}
            ))

    def load_module_config(self, module_id: str, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._config_lock:
            if module_id in self.module_configs: # Return cached if available
                return copy.deepcopy(self.module_configs[module_id])

            final_config = copy.deepcopy(defaults) if defaults else {}
            config_file = self.module_config_dir / f"{module_id}_config.json"
            
            if config_file.is_file():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                    final_config.update(loaded_config) # Override defaults with file content
                    self.logger.debug(f"Loaded module config for '{module_id}' from {config_file}.")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error decoding config file {config_file}: {e}. Using defaults.")
                except Exception as e:
                    self.logger.error(f"Error loading config file {config_file}: {e}. Using defaults.", exc_info=True)
            else:
                self.logger.debug(f"Module config file not found for '{module_id}' at {config_file}. Using defaults.")
            
            self.module_configs[module_id] = copy.deepcopy(final_config) # Cache it
            return final_config

    async def update_module_config(self, module_id: str, config_updates: Dict[str, Any], persist: bool = True) -> None:
        changed_keys = []
        config_file = self.module_config_dir / f"{module_id}_config.json"
        with self._config_lock:
            # Ensure current config (including defaults and file) is loaded into cache
            if module_id not in self.module_configs:
                # This might need the module's default_config from its manifest if not already cached
                # For simplicity, assume it's loaded or defaults are handled by caller if this is first update
                self.logger.warning(f"Updating module config for '{module_id}' which was not pre-cached. Loading with empty defaults.")
                self.load_module_config(module_id, {}) # Load with empty defaults if not found

            current_module_config = self.module_configs.setdefault(module_id, {}) # Get from cache or initialize
            
            for key, value in config_updates.items():
                if current_module_config.get(key) != value:
                    current_module_config[key] = value
                    changed_keys.append(key)

            if changed_keys and persist:
                self.logger.info(f"Module '{module_id}' config updated for keys: {changed_keys}. Saving.")
                try:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(current_module_config, f, indent=4, sort_keys=True)
                except Exception as e:
                    self.logger.error(f"Error saving config for module '{module_id}': {e}", exc_info=True)
        
        if changed_keys and self.event_bus:
            await self.event_bus.publish(Event(
                EventType.CONFIG_CHANGED, "ConfigManager",
                data={"config_type": "module", "module_id": module_id, "changes": changed_keys}
            ))

# --- ModuleInterface and BaseModule ---
class ModuleInterface:
    def __init__(self, module_id: str, event_bus: AsyncEventBus, config: Dict[str, Any], logger: logging.Logger):
        self.module_id = module_id
        self.event_bus = event_bus
        self.config = config # This will be a copy of the module's config
        self.logger = logger
        self._running = False # Internal state, managed by BaseModule start/stop
        self._state_lock = asyncio.Lock() # For synchronizing access to _running if needed

    @property
    def running(self) -> bool: return self._running

    async def initialize(self) -> bool: raise NotImplementedError("Module must implement initialize()")
    async def start(self) -> bool: raise NotImplementedError("Module must implement start()")
    async def stop(self) -> bool: raise NotImplementedError("Module must implement stop()")
    async def pause(self) -> bool: self.logger.info(f"Module {self.module_id}: pause() not implemented."); return True
    async def resume(self) -> bool: self.logger.info(f"Module {self.module_id}: resume() not implemented."); return True
    async def get_status(self) -> Dict[str, Any]: return {"running": self._running, "module_id": self.module_id}
    async def handle_event(self, event: Event) -> None: self.logger.debug(f"Module {self.module_id} received event {event.event_type} but handle_event() not implemented."); pass
    async def cleanup(self) -> None: self.logger.debug(f"Module {self.module_id}: cleanup() not implemented."); pass
    async def on_config_change(self, changed_keys: List[str], new_config: Dict[str, Any]) -> None:
        self.logger.info(f"Module {self.module_id}: Config changed for keys {changed_keys}. Updating internal config.")
        self.config = new_config # Base implementation updates the config ref

class BaseModule(ModuleInterface):
    def __init__(self, module_id: str, event_bus: AsyncEventBus, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(module_id, event_bus, config, logger)
        self._managed_tasks: Dict[str, asyncio.Task] = {}

    async def initialize(self) -> bool:
        self.logger.info(f"BaseModule '{self.module_id}' initialized.")
        return True

    async def start(self) -> bool:
        async with self._state_lock:
            if self._running:
                self.logger.warning(f"BaseModule '{self.module_id}' start called but already running.")
                return True # Or False if this is an error state
            self._running = True
        self.logger.info(f"BaseModule '{self.module_id}' started.")
        return True

    async def stop(self) -> bool:
        async with self._state_lock:
            if not self._running:
                self.logger.info(f"BaseModule '{self.module_id}' stop called but not running.")
                return True
            self._running = False # Signal tasks to stop
        self.logger.info(f"BaseModule '{self.module_id}' stopping managed tasks...")
        await self.stop_all_managed_tasks()
        self.logger.info(f"BaseModule '{self.module_id}' stopped.")
        return True

    async def cleanup(self) -> None:
        await self.stop_all_managed_tasks(timeout_per_task=2.0) # Shorter timeout for cleanup
        self.logger.debug(f"BaseModule '{self.module_id}' cleaned up.")

    async def get_status(self) -> Dict[str, Any]:
        base_status = await super().get_status()
        task_status = {name: ("done" if task.done() else "running") for name, task in self._managed_tasks.items()}
        if task_status: base_status["managed_tasks"] = task_status
        return base_status

    def start_managed_task(self, name: str, coro: Coroutine[Any,Any,Any]) -> bool:
        if name in self._managed_tasks and not self._managed_tasks[name].done():
            self.logger.warning(f"Managed task '{name}' for module '{self.module_id}' already running."); return False
        
        # Ensure the coroutine is created on the correct event loop if module runs in different context
        # loop = asyncio.get_running_loop() # Or self.event_bus._loop if accessible and appropriate
        task = asyncio.create_task(coro, name=f"{self.module_id}-{name}")
        self._managed_tasks[name] = task
        self.logger.info(f"Started managed task: '{name}' for module '{self.module_id}'.")
        task.add_done_callback(lambda t: self._handle_task_completion(t, name)) # Pass name for logging
        return True

    def _handle_task_completion(self, task: asyncio.Task, task_name: str) -> None:
        # task_name = task.get_name() # get_name() might be generic if not set well
        try:
            exception = task.exception()
            if exception:
                self.logger.error(f"Managed task '{task_name}' for module '{self.module_id}' finished with error: {exception}", exc_info=exception)
            else:
                self.logger.info(f"Managed task '{task_name}' for module '{self.module_id}' completed.")
        except asyncio.CancelledError:
            self.logger.info(f"Managed task '{task_name}' for module '{self.module_id}' was cancelled.")
        # Remove task from dict? Or leave for inspection in get_status
        # if task_name in self._managed_tasks and self._managed_tasks[task_name].done():
        #     del self._managed_tasks[task_name]


    async def stop_managed_task(self, name: str, timeout: float = 5.0) -> None:
        task = self._managed_tasks.get(name)
        if task and not task.done():
            self.logger.info(f"Stopping managed task: '{name}' for module '{self.module_id}'")
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError: self.logger.warning(f"Managed task '{name}' (mod: {self.module_id}) cancel timed out.")
            except asyncio.CancelledError: self.logger.info(f"Managed task '{name}' (mod: {self.module_id}) confirmed cancelled.")
            except Exception as e: self.logger.error(f"Error waiting for task '{name}' (mod: {self.module_id}) stop: {e}")
        elif task: self.logger.debug(f"Managed task '{name}' (mod: {self.module_id}) was already done.")
        else: self.logger.warning(f"Cannot stop non-existent managed task: '{name}' (mod: {self.module_id})")

    async def stop_all_managed_tasks(self, timeout_per_task: float = 3.0) -> None:
        tasks_to_stop = [task for task in self._managed_tasks.values() if not task.done()]
        if not tasks_to_stop: return

        self.logger.info(f"Stopping all {len(tasks_to_stop)} managed tasks for module '{self.module_id}'...")
        for task in tasks_to_stop:
            task.cancel()
        
        # Wait for all tasks to finish cancellation
        # This might not be ideal if timeout_per_task is too short for some tasks
        # Consider asyncio.wait for more fine-grained control if needed.
        results = await asyncio.gather(*tasks_to_stop, return_exceptions=True)
        
        for i, result in enumerate(results):
            task_name = tasks_to_stop[i].get_name() # Or derive from self._managed_tasks if names are keys
            if isinstance(result, asyncio.CancelledError):
                self.logger.info(f"Managed task '{task_name}' (mod: {self.module_id}) confirmed stopped during stop_all.")
            elif isinstance(result, Exception):
                self.logger.error(f"Error in managed task '{task_name}' (mod: {self.module_id}) during stop_all: {result}")
        self.logger.info(f"Finished stopping all managed tasks for module '{self.module_id}'.")

    async def run_sync(self, func: Callable[..., Any], *args: Any) -> Any:
        """Runs a synchronous function in an executor to avoid blocking the event loop."""
        loop = asyncio.get_running_loop() # Assumes this method is called from an async context
        return await loop.run_in_executor(None, func, *args) # None uses default ThreadPoolExecutor


# --- ModuleLoader ---
class ModuleLoader:
    def __init__(self, modules_dir: str, event_bus: AsyncEventBus, config_manager: ConfigManager, logger: logging.Logger):
        self.modules_dir = Path(modules_dir).resolve()
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.logger = logger
        self.modules: Dict[str, ModuleInfo] = {} # Store ModuleInfo objects
        self.load_lock = asyncio.Lock() # To protect module loading/unloading operations
        # Subscribe to config changes that might affect modules
        asyncio.create_task(self.event_bus.subscribe(
            EventType.CONFIG_CHANGED, self._handle_config_change, "ModuleLoaderConfigWatcher"
        ))

    async def _handle_config_change(self, event: Event) -> None:
        if event.data.get("config_type") == "module":
            module_id = event.data.get("module_id")
            changed_keys = event.data.get("changes", [])
            if not module_id or not changed_keys: return

            async with self.load_lock: # Ensure module list isn't modified concurrently
                module_info = self.modules.get(module_id)

            if module_info and module_info.instance and \
               module_info.state in [ModuleState.RUNNING, ModuleState.PAUSED] and \
               hasattr(module_info.instance, 'on_config_change'):
                try:
                    # Get the latest full config for the module
                    new_config = self.config_manager.load_module_config(module_id, module_info.config)
                    module_info.config = new_config # Update ModuleInfo's copy too
                    self.logger.info(f"Notifying module '{module_id}' of config changes: {changed_keys}.")
                    await module_info.instance.on_config_change(changed_keys, copy.deepcopy(new_config))
                except Exception as e:
                    self.logger.error(f"Error notifying module '{module_id}' of config change: {e}", exc_info=True)

    def discover_modules(self) -> List[ModuleInfo]:
        discovered: List[ModuleInfo] = []
        if not self.modules_dir.is_dir():
            self.logger.error(f"Modules directory '{self.modules_dir}' is not a valid directory. Module discovery aborted.")
            return discovered
        
        self.logger.info(f"Scanning for modules in '{self.modules_dir}'...")
        for manifest_file in self.modules_dir.glob("*/module.json"): # Look in subdirectories
            module_dir = manifest_file.parent
            module_id_from_dir = module_dir.name # e.g., "01_prompt_interface"
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                required_fields = ['id', 'name', 'version', 'module_class']
                if not all(field in manifest for field in required_fields):
                    self.logger.warning(f"Manifest {manifest_file}: Missing one or more required fields ({required_fields}). Skipping.")
                    continue

                module_id = manifest.get('id') # e.g., "prompt_interface"
                if module_id != module_id_from_dir and not module_id_from_dir.endswith(module_id): # Allow for prefixes like "01_"
                    self.logger.warning(f"Manifest {manifest_file}: ID '{module_id}' does not match directory name '{module_id_from_dir}' convention. Using manifest ID.")

                if any(d.id == module_id for d in discovered): # Check for duplicates by manifest ID
                    self.logger.warning(f"Duplicate module ID '{module_id}' found at {manifest_file}. Skipping.")
                    continue
                module_config = manifest.get('config', {})

                priority_str = manifest.get('startup_priority', 'NORMAL').upper()
                try:
                    startup_priority = Priority[priority_str]
                except KeyError:
                    self.logger.warning(f"Manifest {manifest_file}: Invalid startup_priority '{priority_str}'. Using NORMAL.")
                    startup_priority = Priority.NORMAL
                
                module_info = ModuleInfo(
                    id=module_id,
                    name=manifest.get('name', module_id),
                    version=manifest.get('version', '0.0.0'),
                    description=manifest.get('description', ''),
                    path=str(module_dir.resolve()), # Absolute path to module's directory
                    module_class=manifest['module_class'],
                    dependencies=manifest.get('dependencies', []),
                    startup_priority=startup_priority,
                    #config=module_config, # Use the config from manifest
                    config=manifest.get('default_config', {}) # Default config from manifest
                )
                discovered.append(module_info)
                self.logger.debug(f"Discovered module: {module_info.name} (ID: {module_info.id}) at {module_info.path}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Error decoding manifest file {manifest_file}: {e}. Skipping.")
            except Exception as e:
                self.logger.error(f"Error processing manifest {manifest_file}: {e}. Skipping.", exc_info=True)
        
        self.logger.info(f"Module discovery found {len(discovered)} potential modules.")
        return discovered

    async def register_module(self, module_info: ModuleInfo) -> bool:
        async with self.load_lock:
            if module_info.id in self.modules:
                self.logger.warning(f"Module '{module_info.id}' already registered. Skipping registration."); return False
            
            # Load/merge config: defaults from manifest + persisted module config file
            try:
                # module_info.config holds defaults from manifest. Pass this to load_module_config.
                final_config = self.config_manager.load_module_config(module_info.id, defaults=module_info.config)
                module_info.config = final_config # Update ModuleInfo with the merged/loaded config
                # Optionally persist if load_module_config created/updated a file with merged defaults
                # await self.config_manager.update_module_config(module_info.id, final_config, persist=True) # This might be redundant if load_module_config handles saving.
            except Exception as e:
                self.logger.error(f"Failed to load/process config for module '{module_info.id}' during registration: {e}", exc_info=True)
                return False # Fail registration if config handling fails

            module_info.state = ModuleState.REGISTERED
            self.modules[module_info.id] = module_info
            await self.event_bus.publish(Event(EventType.MODULE_REGISTERED, "ModuleLoader", data={"module_id": module_info.id}))
            self.logger.info(f"Module '{module_info.id}' ({module_info.name}) registered.")
            return True

    async def load_module(self, module_id: str) -> bool:
        async with self.load_lock:
            module_info = self.modules.get(module_id)
            if not module_info:
                self.logger.error(f"Cannot load module '{module_id}': Not registered."); return False
            
            if module_info.state not in [ModuleState.REGISTERED, ModuleState.STOPPED, ModuleState.ERROR]:
                self.logger.warning(f"Cannot load module '{module_id}': Current state is {module_info.state.name}. Load only from REGISTERED, STOPPED, or ERROR.")
                return module_info.state in [ModuleState.RUNNING, ModuleState.PAUSED] # True if already running/paused

            if module_info.state == ModuleState.ERROR:
                self.logger.warning(f"Attempting to load module '{module_id}' which is in ERROR state. Clearing previous error.")
                module_info.state = ModuleState.LOADING # Reset state to LOADING

                module_info.error = None # Clear previous error before attempting reload
                instance = None
                cleanup_import_func = lambda: None # Default no-op cleanup function

            # Initialize instance variable before the first try block
            instance = None
            cleanup_import_func = lambda: None # Default no-op cleanup function
                
            # self.logger.info(f"Loading module '{module_id}' ({module_info.name})...")
            try:
                for dep_id in module_info.dependencies:
                    dep_info = self.modules.get(dep_id)
                    if not dep_info:
                        return await self._set_module_error(module_info, f"Dependency '{dep_id}' not registered.")
                    if dep_info.state != ModuleState.RUNNING:
                            raise Exception(f"Dependency '{dep_id}' is not running.")
                imported_module_obj, _, cleanup_import_func = self._import_module_code(module_info)
                if not imported_module_obj:
                    raise Exception(f"Failed to import module code for '{module_id}'. Check module path and __init__.py presence.")
                if not hasattr(imported_module_obj, module_info.module_class):
                    raise Exception(f"Class '{module_info.module_class}' not found in module '{module_id}'.")
                
                    return False
                ModuleClass = getattr(imported_module_obj, module_info.module_class)
                config_for_instance = copy.deepcopy(module_info.config) # Use the already merged config
                module_logger = logging.getLogger(f"module.{module_id}") # Module-specific logger
                self.logger.debug(f"Instantiating '{module_info.module_class}' for module '{module_id}' with config: {json.dumps(config_for_instance)}")

                instance = ModuleClass(module_id, self.event_bus, config_for_instance, module_logger)
                if not isinstance(instance, ModuleInterface):
                    raise Exception(f"Class '{module_info.module_class}' does not implement ModuleInterface.")
                
                module_info.instance = instance
                if not await instance.initialize():
                    raise Exception(f"Module '{module_id}' initialize() returned False.")
                self.logger.info(f"Module '{module_id}' initialized successfully.")

                if not await instance.start():
                    raise Exception(f"Module '{module_id}' start() returned False.")

                module_info.state = ModuleState.RUNNING
                self.logger.info(f"Module '{module_id}' loaded and started successfully.")
                await self.event_bus.publish(Event(EventType.MODULE_LOADED, "ModuleLoader", data={"module_id": module_id}))
                return True
            except Exception as e:
                self.logger.error(f"Error during load/init/start of module '{module_id}': {e}", exc_info=True)
                cleanup_import_func() # Ensure import cleanup on any exception
                if hasattr(self, '_set_module_error'):
                    await self._set_module_error(module_info, f"Load/start error: {e}", call_cleanup=(instance is not None))
                else:
                    module_info.state = ModuleState.ERROR
                    module_info.error = str(e) # Set error message
                return False
            module_info.state = ModuleState.LOADING
            module_info.error = None # Clear any previous error message

            # Check dependencies
            for dep_id in module_info.dependencies:
                dep_info = self.modules.get(dep_id)
                if not dep_info:
                    return await self._set_module_error(module_info, f"Dependency '{dep_id}' not registered.")
                if dep_info.state != ModuleState.RUNNING:
                    return await self._set_module_error(module_info, f"Dependency '{dep_id}' not running (State: {dep_info.state.name}).")

            # Import module code
            imported_module_obj, spec_name, cleanup_import_func = self._import_module_code(module_info)
            if not imported_module_obj:
                # _import_module_code already calls _set_module_error if it fails critically
                return False # Error should have been set by _import_module_code

            instance = None # Holder for the module instance
            try:
                if not hasattr(imported_module_obj, module_info.module_class):
                    cleanup_import_func() # Clean up import if class not found
                    return await self._set_module_error(module_info, f"Class '{module_info.module_class}' not found in module '{module_id}'.")

                ModuleClass = getattr(imported_module_obj, module_info.module_class)
                
                # Get the latest config for the module instance
                # Pass the already merged config from module_info (which includes defaults and persisted file)
                latest_config = copy.deepcopy(module_info.config) 
                                
                module_logger = logging.getLogger(f"module.{module_id}") # Module-specific logger
                
                self.logger.debug(f"Instantiating class '{module_info.module_class}' for module '{module_id}'.")
                instance = ModuleClass(module_id, self.event_bus, latest_config, module_logger)
                
                if not isinstance(instance, ModuleInterface): # Ensure it adheres to the interface
                    cleanup_import_func()
                    return await self._set_module_error(module_info, f"Class '{module_info.module_class}' does not implement ModuleInterface.")

                module_info.instance = instance # Store instance in ModuleInfo

                self.logger.debug(f"Initializing module '{module_id}'...")
                if not await instance.initialize():
                    cleanup_import_func()
                    return await self._set_module_error(module_info, "Module initialize() returned False.", call_cleanup=True)
                self.logger.info(f"Module '{module_id}' initialized.")
                await self.event_bus.publish(Event(EventType.MODULE_LOADED, "ModuleLoader", data={"module_id": module_id}))

                self.logger.debug(f"Starting module '{module_id}'...")
                if not await instance.start():
                    cleanup_import_func()
                    return await self._set_module_error(module_info, "Module start() returned False.", call_cleanup=True)
                
                # instance._running should be set by instance.start() internally
                module_info.state = ModuleState.RUNNING
                self.logger.info(f"Module '{module_id}' started successfully.")
                await self.event_bus.publish(Event(EventType.MODULE_STARTED, "ModuleLoader", data={"module_id": module_id}))
                return True

            except Exception as e:
                self.logger.error(f"Error during load/init/start of module '{module_id}': {e}", exc_info=True)
                cleanup_import_func() # Ensure import cleanup on any exception
                await self._set_module_error(module_info, f"Load/start error: {e}", call_cleanup=(instance is not None))
                return False

    def _import_module_code(self, module_info: ModuleInfo) -> Tuple[Optional[Any], Optional[str], Callable[[], None]]:
        """
        Imports the module's code.
        Returns (module_object, spec_name, cleanup_function) or (None, None, noop_cleanup) on failure.
        The ModuleLoader is responsible for calling the cleanup_function if the module load fails after import
        or when the module is unloaded.
        """
        module_py_init = Path(module_info.path) / "__init__.py"
        module_py_file = Path(module_info.path) / f"{module_info.id}.py" # Fallback if no __init__.py
        
        # Spec name should be unique, e.g., based on module ID to avoid collisions
        # Using a prefix helps group them if looking at sys.modules
        spec_name = f"presenceos_modules.{module_info.id}"
        
        module_entry_point_path: Optional[Path] = None
        import_base_dir_path_str = "" # Path to add to sys.path if importing as part of a larger package structure

        # Prefer __init__.py as the entry point for the module package
        if module_py_init.is_file():
            module_entry_point_path = module_py_init
            # If __init__.py is used, the module_info.path (directory) itself acts like the package root.
            # For importlib.util.spec_from_file_location, the "name" is key.
            # If module_info.path is "modules/01_foo", and __init__.py is there,
            # spec_name "presenceos_modules.01_foo" might work if "modules" is importable.
            # Or, more simply, treat module_info.path as a standalone package.
            # Let's use a simpler approach: spec_name is unique, path is direct.
        elif module_py_file.is_file():
            self.logger.debug(f"Module '{module_info.id}': Using '{module_info.id}.py' as entry point (no __init__.py found).")
            module_entry_point_path = module_py_file
        else:
            # This case should ideally be caught by ensuring __init__.py exists and imports correctly
            msg = f"Module entry point not found for '{module_info.id}'. Expected __init__.py (preferred) or {module_info.id}.py in {module_info.path}."
            # Cannot call async _set_module_error from sync method directly. Schedule it.
            loop = asyncio.get_running_loop() # Assume called from an async context or kernel's loop
            asyncio.run_coroutine_threadsafe(self._set_module_error(module_info, msg), loop)
            return None, None, lambda: None # No-op cleanup

        # sys.path manipulation for isolated module loading
        added_to_path = False
        # The parent of the module's directory needs to be in sys.path if module_info.path is part of package
        # For simple structure modules/module_id/__init__.py, module_info.path is the package.
        # If module_info.path is '.../modules/01_foo', then '.../modules' could be added.
        # For now, assume direct loading from module_info.path is primary.
        # The __init__.py pattern (from .file import Class) handles relative imports within the module.
        
        # Cleanup function to remove from sys.modules and potentially sys.path
        def cleanup_import():
            if spec_name in sys.modules:
                try:
                    del sys.modules[spec_name]
                    self.logger.debug(f"Removed '{spec_name}' from sys.modules for module '{module_info.id}'.")
                except KeyError: pass # Should not happen if check passes
            # If sys.path was modified:
            # if added_to_path and import_base_dir_path_str in sys.path:
            #     try: sys.path.remove(import_base_dir_path_str)
            #     except ValueError: pass

        try:
            # Remove if already loaded to ensure fresh import (important for reload)
            if spec_name in sys.modules:
                self.logger.debug(f"Module spec '{spec_name}' already in sys.modules. Removing for fresh import.")
                cleanup_import() # Call to remove it

            spec = importlib.util.spec_from_file_location(spec_name, str(module_entry_point_path))
            if spec is None or spec.loader is None: # Check spec.loader too
                msg = f"Failed to create module spec for '{module_info.id}' from {module_entry_point_path}."
                loop = asyncio.get_running_loop(); asyncio.run_coroutine_threadsafe(self._set_module_error(module_info, msg), loop)
                return None, None, lambda: None

            imported_module_obj = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = imported_module_obj # Add to sys.modules *before* exec_module
            spec.loader.exec_module(imported_module_obj) # Execute the module's code
            
            self.logger.debug(f"Successfully imported and executed module code for '{module_info.id}' as '{spec_name}'.")
            return imported_module_obj, spec_name, cleanup_import
        except Exception as e:
            self.logger.error(f"Failed during import execution for module '{module_info.id}': {e}", exc_info=True)
            cleanup_import() # Attempt cleanup on error
            loop = asyncio.get_running_loop(); asyncio.run_coroutine_threadsafe(self._set_module_error(module_info, f"Import execution failed: {e}"), loop)
            return None, None, lambda: None

    async def unload_module(self, module_id: str, force: bool = False) -> bool:
        module_info: Optional[ModuleInfo] = None
        spec_name_to_remove: Optional[str] = None

        async with self.load_lock: # Protect access to self.modules
            module_info = self.modules.get(module_id)
            if not module_info:
                self.logger.error(f"Cannot unload module '{module_id}': Not registered."); return False

            initial_state = module_info.state
            if initial_state in [ModuleState.STOPPED, ModuleState.REGISTERED, ModuleState.UNREGISTERED]:
                self.logger.info(f"Unload no-op for '{module_id}', already in state {initial_state.name}. Ensuring clean state.")
                module_info.state = ModuleState.STOPPED # Ensure it's marked as stopped
                module_info.instance = None; module_info.error = None
                # Try to clean up import from sys.modules if it was loaded before
                spec_name_to_remove = f"presenceos_modules.{module_id}"
                # No need to call instance.stop() or cleanup() as it should already be in that state.
            else:
                self.logger.info(f"Unloading module '{module_id}' (State: {initial_state.name}, Force: {force})...")
                if not force:
                    # Check for active dependents
                    active_dependents = [
                        f"{oid}({oinfo.state.name})" for oid, oinfo in self.modules.items()
                        if module_id in oinfo.dependencies and oinfo.state not in [ModuleState.STOPPED, ModuleState.REGISTERED, ModuleState.ERROR, ModuleState.UNREGISTERED]
                    ]
                    if active_dependents:
                        self.logger.error(f"Cannot unload '{module_id}': Active dependents: {', '.join(active_dependents)}. Use force=True to override.")
                        return False
                
                instance = module_info.instance
                unload_error_message: Optional[str] = None

                if instance and initial_state in [ModuleState.RUNNING, ModuleState.PAUSED]:
                    self.logger.debug(f"Stopping module instance '{module_id}'...")
                    try:
                        if not await instance.stop(): # Calls BaseModule.stop which handles _running and tasks
                            self.logger.warning(f"Module '{module_id}' stop() returned False.")
                    except Exception as e:
                        unload_error_message = f"Error during module stop(): {e}"
                        self.logger.error(unload_error_message, exc_info=True)
                
                # Unsubscribe from event bus
                await self.event_bus.unsubscribe_all(module_id)
                self.logger.debug(f"Unsubscribed module '{module_id}' from all events.")

                if instance: # Call cleanup if instance exists
                    self.logger.debug(f"Cleaning up module instance '{module_id}'...")
                    try:
                        await instance.cleanup()
                    except Exception as e:
                        if not unload_error_message: unload_error_message = f"Error during module cleanup(): {e}"
                        self.logger.error(f"Error during module '{module_id}' cleanup(): {e}", exc_info=True)
                
                module_info.instance = None # Clear instance reference

                # If an error occurred during stop/cleanup, set module to error state
                if unload_error_message:
                    await self._set_module_error(module_info, unload_error_message) # This sets state to ERROR
                    # Don't return False immediately; proceed to cleanup import if possible
                else:
                    module_info.state = ModuleState.STOPPED
                    module_info.error = None
                
                # Signal module stopped if it was running/paused/loading
                if initial_state in [ModuleState.RUNNING, ModuleState.PAUSED, ModuleState.LOADING]:
                    await self.event_bus.publish(Event(EventType.MODULE_STOPPED, "ModuleLoader", data={"module_id": module_id}))

                spec_name_to_remove = f"presenceos_modules.{module_id}" # Used after lock release

        # Perform sys.modules cleanup outside the lock if spec_name_to_remove is set
        if spec_name_to_remove and spec_name_to_remove in sys.modules:
            try:
                del sys.modules[spec_name_to_remove]
                self.logger.debug(f"Removed '{spec_name_to_remove}' from sys.modules after unloading '{module_id}'.")
            except KeyError:
                self.logger.warning(f"Tried to remove '{spec_name_to_remove}' from sys.modules, but key was not found.")
        
        # Re-check state after potential _set_module_error
        if module_info and module_info.state == ModuleState.ERROR:
            self.logger.warning(f"Module '{module_id}' unloaded but ended in ERROR state.")
            return False # Unload completed, but with errors.
        elif module_info:
            self.logger.info(f"Module '{module_id}' unloaded successfully. Final state: {module_info.state.name}.")
            return True
        return False # Should not be reached if module_info exists

    async def unregister_module(self, module_id: str) -> bool:
        async with self.load_lock:
            module_info = self.modules.get(module_id)
            if not module_info:
                self.logger.error(f"Cannot unregister module '{module_id}': Not registered."); return False

            if module_info.state not in [ModuleState.REGISTERED, ModuleState.STOPPED, ModuleState.UNREGISTERED, ModuleState.ERROR]:
                self.logger.info(f"Module '{module_id}' is in state {module_info.state.name}. Forcing unload before unregister...")
                # Call unload without holding the lock for its entirety if unload itself needs the lock
                # This requires making unload re-entrant or careful design.
                # For now, assume unload is called and then we re-check.
                # This part is tricky. Let's simplify: unload will be called, then we pop.
                # The `await self.unload_module` might need to be outside this lock or structured differently
                # if unload_module itself tries to acquire load_lock.
                # For now, assuming it's okay for this sequence.
                # Releasing and re-acquiring the lock is safer:
                # Drop lock, unload, re-acquire lock, then pop.
                pass # Placeholder for more complex lock management if unload is also locked

        # Unload the module (forcefully) if it's in a state that requires it
        # This call to unload_module will acquire its own lock.
        if module_info.state not in [ModuleState.REGISTERED, ModuleState.STOPPED, ModuleState.UNREGISTERED, ModuleState.ERROR]:
            unload_success = await self.unload_module(module_id, force=True)
            if not unload_success:
                self.logger.warning(f"Unload of module '{module_id}' failed or had errors during unregister. Proceeding with unregister attempt anyway.")
        
        async with self.load_lock: # Re-acquire lock to modify self.modules
            if module_id in self.modules:
                removed_info = self.modules.pop(module_id)
                removed_info.state = ModuleState.UNREGISTERED # Mark its final state
                await self.event_bus.publish(Event(EventType.MODULE_UNREGISTERED, "ModuleLoader", data={"module_id": module_id}))
                self.logger.info(f"Module '{module_id}' unregistered.")
                return True
            else: # Should not happen if initial check passed and it wasn't removed by another thread
                self.logger.warning(f"Module '{module_id}' was not found for final removal during unregister.")
                return False

    def get_module_info(self, module_id: str) -> Optional[ModuleInfo]:
        # Does not need lock for read if ModuleInfo objects are not modified outside locks
        return self.modules.get(module_id)

    def get_all_modules(self) -> List[ModuleInfo]: # Return list of ModuleInfo for easier iteration
        # Return a copy of values
        return list(self.modules.values())

    async def _set_module_error(self, module_info: ModuleInfo, message: str, call_cleanup: bool = False) -> bool:
        """Internal helper to set module to error state and publish event."""
        self.logger.error(f"Module '{module_info.id}' error: {message}")
        module_info.state = ModuleState.ERROR
        module_info.error = message
        
        instance_to_cleanup = module_info.instance # Get instance before clearing it
        module_info.instance = None # Clear instance on error

        if call_cleanup and instance_to_cleanup and hasattr(instance_to_cleanup, 'cleanup'):
            self.logger.debug(f"Attempting cleanup for module '{module_info.id}' after error state set...")
            try:
                await instance_to_cleanup.cleanup()
            except Exception as e_cleanup:
                self.logger.error(f"Error during cleanup for module '{module_info.id}' after error: {e_cleanup}", exc_info=True)
        
        await self.event_bus.publish(Event(
            EventType.MODULE_ERROR, "ModuleLoader", priority=Priority.HIGH,
            data={"module_id": module_info.id, "error_message": message}
        ))
        return False # Standard return for functions that set error (indicates failure of operation)


# --- Diagnostics ---
class Diagnostics:
    def __init__(self, event_bus: AsyncEventBus, config_manager: ConfigManager, module_loader: ModuleLoader, logger: logging.Logger):
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.module_loader = module_loader # Now ModuleLoader instance
        self.logger = logger
        self.start_time = time.monotonic() # Use monotonic for uptime
        self.last_health_check_time = 0.0
        self.health_check_interval = 60 # Default, will be updated from config
        self._diag_lock = threading.RLock() # For thread-safe access to metrics if updated by different threads
        
        self.psutil_available = False
        self.psutil_module: Optional[Any] = None # To store imported psutil module
        
        self.system_metrics: Dict[str, Any] = {
            "uptime_seconds": 0, "cpu_usage_percent": -1.0, 
            "memory_usage_mb": -1.0, "threads_active": -1,
            "event_rate_per_sec": 0.0
        }
        self.event_timestamps: List[float] = [] # For event rate calculation
        self.max_event_timestamps_for_rate = 1000 # Store last 1000 event timestamps for rate calc
        self.last_health_status: Dict[str, Any] = {} # Cache last health check result

    async def initialize(self) -> None:
        with self._diag_lock:
            system_config = self.config_manager.get_system_config()
            self.health_check_interval = system_config.get("health_check_interval", 60)
            self.max_event_timestamps_for_rate = system_config.get("history_size", 1000) # Reuse history_size
            self._check_psutil()
        
        await self.event_bus.subscribe("*", self._track_event_for_rate, "DiagnosticsEventRateTracker")
        self.logger.info(f"Async Diagnostics initialized. Health check interval: {self.health_check_interval}s.")

    async def shutdown(self) -> None:
        self.logger.info("Shutting down diagnostics...")
        await self.event_bus.unsubscribe("*", "DiagnosticsEventRateTracker")

    def _check_psutil(self):
        # This is a synchronous check, usually done at init
        if not self.psutil_module: # Only try to import once
            try:
                import psutil
                self.psutil_module = psutil
                self.psutil_available = True
                self.logger.info("psutil library found, enabling detailed process metrics.")
            except ImportError:
                self.psutil_available = False
                self.logger.warning("psutil library not found. Install 'psutil' for detailed CPU/memory metrics.")
            except Exception as e: # Catch other potential errors during import
                self.psutil_available = False
                self.logger.warning(f"Failed to import or use psutil: {e}")

    async def _track_event_for_rate(self, event: Event) -> None:
        # This callback is async as required by AsyncEventBus
        with self._diag_lock: # Protect access to self.event_timestamps
            self.event_timestamps.append(time.monotonic())
            # Trim timestamps list to keep it bounded
            if len(self.event_timestamps) > self.max_event_timestamps_for_rate:
                self.event_timestamps = self.event_timestamps[-self.max_event_timestamps_for_rate:]

    def _update_system_metrics(self) -> None:
        # This method is called synchronously from run_health_check
        now = time.monotonic()
        with self._diag_lock: # Protect metrics
            self.system_metrics["uptime_seconds"] = int(now - self.start_time)

            # Calculate event rate (events per second over the last minute or uptime)
            if self.event_timestamps:
                window_duration = min(60.0, self.system_metrics["uptime_seconds"])
                relevant_ts_start = now - window_duration
                # Count events within the window
                events_in_window = sum(1 for ts in self.event_timestamps if ts >= relevant_ts_start)
                if window_duration > 0:
                    self.system_metrics["event_rate_per_sec"] = round(events_in_window / window_duration, 2)
                else:
                    self.system_metrics["event_rate_per_sec"] = 0.0
            else:
                self.system_metrics["event_rate_per_sec"] = 0.0

            if self.psutil_available and self.psutil_module:
                try:
                    p = self.psutil_module.Process(os.getpid())
                    with p.oneshot(): # Efficiently get multiple stats
                        self.system_metrics["cpu_usage_percent"] = p.cpu_percent(interval=None) # Use None for non-blocking
                        mem_info = p.memory_info()
                        self.system_metrics["memory_usage_mb"] = round(mem_info.rss / (1024 * 1024), 2) # RSS in MB
                        self.system_metrics["threads_active"] = p.num_threads()
                except self.psutil_module.NoSuchProcess:
                    self.logger.warning("Diagnostics: psutil.NoSuchProcess error. Process may have exited.")
                    self.system_metrics.update({"cpu_usage_percent": -1.0, "memory_usage_mb": -1.0, "threads_active": -1})
                except Exception as e:
                    self.logger.warning(f"Error updating metrics with psutil: {e}")
                    self.system_metrics.update({"cpu_usage_percent": -1.0, "memory_usage_mb": -1.0, "threads_active": -1})
            else: # psutil not available
                self.system_metrics.update({"cpu_usage_percent": -1.0, "memory_usage_mb": -1.0, "threads_active": -1})


    async def run_health_check(self, force: bool = False) -> Dict[str, Any]:
        now = time.monotonic() # Use monotonic time for intervals
        with self._diag_lock: # Protect last_health_check_time and last_health_status
            if not force and (now - self.last_health_check_time < self.health_check_interval):
                return copy.deepcopy(self.last_health_status) # Return cached if not forced and within interval
            
            self._update_system_metrics() # Update base system metrics
            self.last_health_check_time = now # Record time of this check

        # --- Module Health ---
        all_module_infos = self.module_loader.get_all_modules() # Gets list of ModuleInfo
        module_health_reports: Dict[str, Dict[str, Any]] = {}
        
        status_tasks: List[Tuple[str, asyncio.Task]] = [] # Store (module_id, task)

        for mod_info in all_module_infos:
            base_report = {
                "id": mod_info.id, "name": mod_info.name, "state": mod_info.state.name,
                "healthy": mod_info.state not in [ModuleState.ERROR, ModuleState.LOADING], # Basic health
                "error": mod_info.error, "details": None,
                "priority": mod_info.startup_priority.name
            }
            module_health_reports[mod_info.id] = base_report

            if mod_info.instance and mod_info.state in [ModuleState.RUNNING, ModuleState.PAUSED] and \
               hasattr(mod_info.instance, 'get_status') and callable(mod_info.instance.get_status):
                # Create task to get status, store with module_id to map results back
                status_tasks.append(
                    (mod_info.id, asyncio.create_task(mod_info.instance.get_status(), name=f"get_status_{mod_info.id}"))
                )
        
        # Gather results from all get_status tasks
        if status_tasks:
            task_results = await asyncio.gather(*[task for _, task in status_tasks], return_exceptions=True)
            for i, result_or_exc in enumerate(task_results):
                module_id_for_status = status_tasks[i][0] # Get corresponding module_id
                report_to_update = module_health_reports[module_id_for_status] # Get its report
                
                if isinstance(result_or_exc, Exception):
                    self.logger.warning(f"Error getting status for module '{module_id_for_status}': {result_or_exc}")
                    report_to_update["healthy"] = False
                    report_to_update["error"] = report_to_update["error"] or f"get_status() failed: {result_or_exc}"
                elif isinstance(result_or_exc, dict): # Assume get_status returns a dict
                    report_to_update["details"] = result_or_exc
                    if result_or_exc.get('healthy') is False: # Module can explicitly report unhealthy
                        report_to_update["healthy"] = False
                        report_to_update["error"] = report_to_update["error"] or result_or_exc.get('error', 'Module reported unhealthy')
        
        # Determine overall health
        critical_module_failure = any(
            not report['healthy'] and self.module_loader.get_module_info(mod_id).startup_priority == Priority.CRITICAL # type: ignore
            for mod_id, report in module_health_reports.items() if self.module_loader.get_module_info(mod_id) # Ensure mod_info exists
        )
        # Overall healthy if no critical failures and all non-background modules are healthy
        # (This definition of overall_healthy can be tuned)
        non_background_modules_ok = all(
            report['healthy'] for mod_id, report in module_health_reports.items()
            if self.module_loader.get_module_info(mod_id) and self.module_loader.get_module_info(mod_id).startup_priority != Priority.BACKGROUND # type: ignore
        )
        overall_system_healthy = not critical_module_failure and non_background_modules_ok

        # Final health status object
        current_health_status = {
            "timestamp": time.time(), # Wall clock time for the report
            "overall_healthy": overall_system_healthy,
            "system_metrics": copy.deepcopy(self.system_metrics), # Snapshot of metrics
            "module_health": module_health_reports,
            # "event_counts_snapshot": copy.deepcopy(self.event_counts) # If you still track raw counts
        }
        with self._diag_lock: # Protect update to cached status
            self.last_health_status = current_health_status
        return copy.deepcopy(current_health_status)


    def get_health_status(self) -> Dict[str, Any]: # Synchronous access to cached status
        with self._diag_lock:
            # If cache is empty (e.g. first call before any check ran), return minimal
            if not self.last_health_status:
                return {"timestamp": 0, "overall_healthy": None, "system_metrics": self.system_metrics, "module_health": {}}
            return copy.deepcopy(self.last_health_status)

    def get_module_status_summary(self, module_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """ Provides a formatted summary from ModuleInfo, not live instance status. """
        all_mod_infos = self.module_loader.get_all_modules() # List[ModuleInfo]
        
        def format_info(mod_info: ModuleInfo) -> Dict[str, Any]:
            return {
                "id": mod_info.id, "name": mod_info.name, "version": mod_info.version,
                "state": mod_info.state.name, "priority": mod_info.startup_priority.name,
                "error": mod_info.error, "dependencies": mod_info.dependencies,
                "path": mod_info.path, "description": mod_info.description
            }

        if module_id:
            mod_info_obj = self.module_loader.get_module_info(module_id) # Gets ModuleInfo object
            return format_info(mod_info_obj) if mod_info_obj else {"error": f"Module '{module_id}' not found."}
        else:
            return [format_info(mi) for mi in sorted(all_mod_infos, key=lambda m: m.id)]


# --- KernelAPI ---
class KernelAPI:
    def __init__(self, kernel: 'PresenceKernel'): # Forward reference 'PresenceKernel'
        self._kernel = kernel
        # Direct references for convenience, ensure these are set in kernel before API is used
        self._module_loader: ModuleLoader = kernel.module_loader
        self._config_manager: ConfigManager = kernel.config_manager
        self._event_bus: AsyncEventBus = kernel.event_bus
        self._diagnostics: Diagnostics = kernel.diagnostics
        self.logger = kernel.logger.getChild('api')

        self.llm_manager: Optional[LLMManager] = None
        self._redis_stream_logger_ref: Optional[RedisStreamLogger] = self._kernel.redis_stream_logger
        self._kernel_redis_pool_ref: Optional[aioredis.Redis] = self._kernel.redis_pool
        self._ui_manager: Optional[UIManagerModule] = None

    def set_ui_manager(self, ui_manager: UIManagerModule):
        self._ui_manager = ui_manager
        self.logger.info(f"KernelAPI: UIManager reference set to {ui_manager.manager_id}.")

    async def submit_prompt_from_ui(self, request_id: str, prompt_text: str, session_id: str, selected_agents_override: Optional[List[str]], attached_files: List[Dict[str, Any]], user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: 
        """Receives a user prompt directly from the UI via the API server. Publishes it to an EventBus event for the PromptInterfaceModule or Orchestrator to handle."""
        if not session_id:
            self.logger.error("submit_prompt_from_ui: 'session_id' is required for UI prompts.")
            raise ValueError("session_id is required")
        

        #request_id = request_id # Generate a unique request ID
        self.logger.info(f"KernelAPI: UI prompt (ReqID: {request_id}) received for session {session_id}. Prompt: '{prompt_text[:50]}...'")
        event_data = {
            "request_id": request_id,
            "session_id": session_id,
            "prompt_text": prompt_text,
            "selected_agents_override": selected_agents_override or [],
            "attached_files": attached_files,
            "user_context": user_context
        }
        if self._ui_manager:
            # Send to UIManager for immediate UI feedback
            self.logger.info(f"DEBUG: _ui_manager exists, sending thinking status to session {session_id}")
            thinking_message = {
                "type": "thinking_status",
                "request_id": request_id,
                "data": {
                    "description": f"AetherPro is orchestrating agent responses for request {request_id}..."
                }
            }
    #        await self._ui_manager._send_to_specific_websocket(session_id, {
     #           "type": "thinking_status",
     #           "request_id": request_id,
     #           "data": {
      #              "description": f"AetherPro is orchestrating agent responses for request {request_id}..."
       #         }
        #    })
            self.logger.info(f"DEBUG: About to send thinking message {thinking_message} to session {session_id}")
            await self._ui_manager._send_to_specific_websocket(session_id, thinking_message)
            self.logger.info(f"DEBUG: Thinking status sent succesfully")
        else:
            self.logger.warning(f"DEBUG: _ui_manager is None, cannot send thinking status")
            
        try:
            await self._event_bus.publish(Event(
                event_type="presence_ui:user_prompt_received",
                source="KernelAPI_UI",
                data=event_data,
                priority=Priority.HIGH
            ))
            self.logger.debug(f"KernelAPI: Prompt event published successfully for session {session_id}.")
            return {"success": True, "request_id": request_id}
        except Exception as e:
            self.logger.error(f"KernelAPI: Failed to publish 'presence_ui:user_prompt_received' for ReqID {request_id}: {e}", exc_info=True)
            if self._ui_manager: asyncio.create_task(self._ui_manager._send_to_ui(session_id, {
                "type": "error",
                "request_id": request_id,
                "error": f"Kernel internal error: Failed to initiate prompt processing: {e}"
            }))
            raise RuntimeError(f"Failed to publish prompt event: {e}")

    def get_redis_stream_logger(self) -> Optional[RedisStreamLogger]:
        """ Returns the RedisStreamLogger instance if available. """
        if not hasattr(self._kernel, 'redis_stream_logger') or self._kernel.redis_stream_logger is None:
            self.logger.debug("KernelAPI: get_redis_stream_logger() called, but no RedisStreamLogger available.")
            return None
        self.logger.debug(f"KernelAPI: Returning kernel.redis._stream_logger of type {type(self._kernel.redis_stream_logger)}")
        return self._kernel.redis_stream_logger
        
      #  if not self._redis_stream_logger_ref:
       #     self._redis_stream_logger_ref = self._kernel.redis_stream_logger

        # return self._redis_stream_logger_ref
    async def get_redis_pool(self) -> Optional[aioredis.Redis]:
        """ Returns the aioredis.Redis connection pool if available. """
        self.logger.debug(f"KernelAPI: get_redis_pool() called, checking kernel.redis_pool.")
        if not hasattr(self._kernel, 'redis_pool') or self._kernel.redis_pool is None:
            self.logger.debug("KernelAPI: get_redis_pool() called, but no Redis connection pool available.")
            return None
        try:
            self.logger.debug(f"KernelAPI: Returning kernel.redis_pool of type {type(self._kernel.redis_pool)}")
            return self._kernel.redis_pool
        except Exception as e:
            self.logger.error(f"KernelAPI: Error accessing Redis connection pool: {e}", exc_info=True)
            return None
            
                



    def get_kernel_base_dir_path(self) -> Optional[Path]:
        """ Returns the base directory path of the kernel. """
        if hasattr(self._kernel, '_kernel_dir_path'):
            return self._kernel._kernel_dir_path
        self.logger.warning("KernelAPI: _kernel_base_dir_path() called, but no kernel directory path available.")
        return None

    def get_module_info(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Gets static info from ModuleInfo, not live status from instance."""
        mi = self._module_loader.get_module_info(module_id) # ModuleInfo object
        if not mi: return None
        # Convert ModuleInfo dataclass to dict, excluding instance field
        info_dict = {
            "id": mi.id,
            "name": mi.name,
            "version": mi.version,
            "description": mi.description,
            "path": mi.path,
            "module_class": mi.module_class,
            "dependencies": mi.dependencies,
            "startup_priority": mi.startup_priority.name,
            "config": copy.deepcopy(mi.config), # Return a copy of config
            "state": mi.state.name, # Convert enum to string
            "error": mi.error, # Error message if any
        }
#        del info_dict['instance'] # Don't expose instance object via API
        # Convert enums to names for serialization
 #       info_dict['state'] = mi.state.name
  #      info_dict['startup_priority'] = mi.startup_priority.name
        return info_dict

    def get_all_modules(self) -> List[Dict[str, Any]]:
        """Gets static info for all modules."""
        all_module_infos = self._module_loader.get_all_modules() # List[ModuleInfo]
        # Sort by ID before converting, as ModuleLoader might return dict internally
        sorted_infos = sorted(all_module_infos, key=lambda m: m.id)
        return [self.get_module_info(mi.id) for mi in sorted_infos if self.get_module_info(mi.id) is not None] # type: ignore

    async def load_module(self, module_id: str) -> bool:
        self.logger.info(f"API: Requesting load for module '{module_id}'.")
        return await self._module_loader.load_module(module_id)

    async def unload_module(self, module_id: str, force: bool = False) -> bool:
        self.logger.info(f"API: Requesting unload for module '{module_id}' (force={force}).")
        return await self._module_loader.unload_module(module_id, force=force)

    async def reload_module(self, module_id: str, force: bool = False) -> bool:
        self.logger.info(f"API: Requesting reload for module '{module_id}' (force unload={force}).")
        # Force unload for reload to ensure it stops regardless of dependents for this operation
        unload_success = await self._module_loader.unload_module(module_id, force=True) 
        if not unload_success:
            self.logger.error(f"API Reload: Unload step failed for '{module_id}'. Reload aborted.")
            return False
        
        await asyncio.sleep(0.1) # Brief pause for any resource release
        
        load_success = await self._module_loader.load_module(module_id)
        if not load_success:
            self.logger.error(f"API Reload: Load step failed for '{module_id}'.")
            return False
        self.logger.info(f"API: Module '{module_id}' reloaded successfully.")
        return True

    async def register_module_from_manifest_path(self, manifest_path_str: str) -> bool:
        """Experimental: Discover and register a single module from a manifest path."""
        self.logger.info(f"API: Requesting registration from manifest '{manifest_path_str}'.")
        manifest_path = Path(manifest_path_str).resolve()
        if not manifest_path.is_file() or manifest_path.name != 'module.json':
            self.logger.error(f"API Register: Invalid manifest path '{manifest_path_str}'. Must be 'module.json'.")
            return False
        
        # This is a simplified discovery for one module.
        # ModuleLoader.discover_modules scans a whole directory.
        # We might need a new method in ModuleLoader or adapt.
        # For now, let's try to parse this one manifest and create ModuleInfo.
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f: manifest = json.load(f)
            module_id = manifest['id']
            
            if self._module_loader.get_module_info(module_id):
                self.logger.warning(f"API Register: Module '{module_id}' already registered."); return False

            priority_str = manifest.get('startup_priority', 'NORMAL').upper()
            startup_priority = Priority[priority_str] if priority_str in Priority.__members__ else Priority.NORMAL
            
            module_info = ModuleInfo(
                id=module_id, name=manifest.get('name', module_id), version=manifest.get('version', '0.0.0'),
                description=manifest.get('description', ''), path=str(manifest_path.parent.resolve()),
                module_class=manifest['module_class'], dependencies=manifest.get('dependencies', []),
                startup_priority=startup_priority, config=manifest.get('default_config', {})
            )
            return await self._module_loader.register_module(module_info)
        except Exception as e:
            self.logger.error(f"API Register: Failed to process manifest or register '{manifest_path_str}': {e}", exc_info=True)
            return False

    async def unregister_module(self, module_id: str) -> bool:
        self.logger.info(f"API: Requesting unregister for module '{module_id}'.")
        return await self._module_loader.unregister_module(module_id)

    def get_module_status(self, module_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Gets summary status, not live get_status() from instance. For that, use health check."""
        return self._diagnostics.get_module_status_summary(module_id)

    def get_system_health(self) -> Dict[str, Any]: # Sync, returns cached
        return self._diagnostics.get_health_status()

    async def run_health_check(self) -> Dict[str, Any]: # Async, forces new check
        self.logger.debug("API: Forcing new health check run.")
        return await self._diagnostics.run_health_check(force=True)

    def get_system_config(self) -> Dict[str, Any]:
        return self._config_manager.get_system_config()

    async def update_system_config(self, updates: Dict[str, Any]) -> None:
        await self._config_manager.update_system_config(updates)

    def get_module_config(self, module_id: str) -> Dict[str, Any]:
        mod_info = self._module_loader.get_module_info(module_id)
        if not mod_info:
            raise ValueError(f"Module '{module_id}' not found, cannot get config.")
        # Pass defaults from ModuleInfo (which has manifest defaults)
        return self._config_manager.load_module_config(module_id, defaults=mod_info.config)

    async def update_module_config(self, module_id: str, updates: Dict[str, Any]) -> None:
        if not self._module_loader.get_module_info(module_id):
            raise ValueError(f"Module '{module_id}' not found, cannot update config.")
        await self._config_manager.update_module_config(module_id, updates, persist=True)

    async def publish_event(self, etype: Union[EventType, str], src: str, 
                            data: Optional[Dict[str, Any]] = None, 
                            prio: Priority = Priority.NORMAL) -> None:
        if not src: raise ValueError("Event source ('src') is required for publishing.")
        event_to_publish = Event(event_type=etype, source=src, data=data or {}, priority=prio)
        await self._event_bus.publish(event_to_publish)

    def get_event_history(self, count: Optional[int] = None, etype: Optional[Union[EventType, str]] = None) -> List[Dict[str, Any]]:
        events = self._event_bus.get_event_history(count=count, event_type=etype)
        return [e.to_dict() for e in events] # Convert Event objects to dicts

    async def shutdown_kernel(self) -> None:
        self.logger.warning("API: Kernel shutdown requested via API.")
        await self._kernel.shutdown() # Call kernel's shutdown method

    async def restart_kernel(self) -> None:
        self.logger.warning("API: Kernel restart requested via API (Experimental).")
        await self._kernel.restart() # Call kernel's restart


# In class KernelAPI:
# ... (other KernelAPI methods) ...

    async def submit_prompt_to_interface_for_api(
        self, 
        prompt_text: str, 
        session_id: Optional[str] = None, 
        selected_agents_override: Optional[List[str]] = None,
        timeout: float = 120.0 # Default timeout for waiting for response
        
    ) -> Optional[Dict[str, Any]]:
        """
        Submits a prompt via the PromptInterfaceModule and awaits its merged response.
        Designed to be called by external APIs (like FastAPI).
        """
        self.logger.info(f"KernelAPI: Received prompt for API: '{prompt_text[:50]}...' SessID: {session_id} Agents: {selected_agents_override}")
    
        if not self._kernel or not self._kernel.module_loader:
            self.logger.error("KernelAPI: Kernel or ModuleLoader not available.")
            return {"error": "Kernel components not ready.", "request_id": None, "session_id": session_id}

        pim_info = self._kernel.module_loader.get_module_info("prompt_interface")
        if not pim_info or not pim_info.instance:
            self.logger.error("KernelAPI: PromptInterfaceModule not found or not instantiated.")
            return {"error": "PromptInterfaceModule not available.", "request_id": None, "session_id": session_id}

        if hasattr(pim_info.instance, "process_user_prompt_for_api"):
            try:
                
                self.logger.debug(f"KernelAPI: Calling process_user_prompt_for_api on PromptInterfaceModule.")
                # Call the method on PromptInterfaceModule that returns a Future/awaited result
                response_data = await pim_info.instance.process_user_prompt_for_api(
                    prompt_text=prompt_text,
                    session_id=session_id,
                    selected_agents=selected_agents_override, # Pass the override
                    timeout=timeout 
            )
            # process_user_prompt_for_api should return a dict including request_id, merged_text etc.
            # or a dict with an "error" key if processing failed.
                return response_data
            except AttributeError as ae: # Method exists but called wrong or internal error
                self.logger.error(f"KernelAPI: AttributeError calling PIM.process_user_prompt_for_api: {ae}", exc_info=True)
                return {"error": f"Error in PromptInterfaceModule: {ae}", "request_id": None, "session_id": session_id}
            except Exception as e:
                self.logger.error(f"KernelAPI: Error submitting prompt via PromptInterfaceModule: {e}", exc_info=True)
                return {"error": f"Kernel processing error: {e}", "request_id": None, "session_id": session_id}
        else:
            self.logger.error("KernelAPI: PromptInterfaceModule instance is missing 'process_user_prompt_for_api' method.")
        return {"error": "PromptInterfaceModule method not found.", "request_id": None, "session_id": session_id}

# In PresenceOS_kernel.py -> class KernelAPI:
# ...
# self._redis_stream_logger_ref: Optional[RedisStreamLogger] = self._kernel.redis_stream_logger 
# self._kernel_redis_pool_ref: Optional[aioredis.Redis] = self._kernel.redis_pool
# ...

  #  def get_redis_stream_logger(self) -> Optional[RedisStreamLogger]:
   #         if not self._redis_stream_logger_ref:
    #            self.logger.debug("KernelAPI: Attempted to get RedisStreamLogger, but it's not initialized on kernel reference.")
     #           return self._redis_stream_logger_ref#
#
 #   async def get_redis_pool(self) -> Optional[aioredis.Redis]:
  #          if self._kernel_redis_pool_ref:
   #             try:
    #                await self._kernel_redis_pool_ref.ping() # Quick check
     #               return self._kernel_redis_pool_ref
      #          except Exception as e:
       #             self.logger.error(f"KernelAPI: Kernel's Redis pool ping failed: {e}. Assuming unavailable.")
        #            return None
         #   self.logger.warning("KernelAPI: Kernel's Redis pool is not initialized or reference not set.")
          #  return None


# --- PresenceKernel ---
class PresenceKernel:
    def __init__(self, config_dir: str = "config", modules_dir: str = "modules"):
        self._configure_root_logger() # Basic stdout logging first
        self.logger = logging.getLogger("Kernel")
        self.logger.info("--- PresenceOS Async Kernel Initializing ---")

        self.event_loop: Optional[asyncio.AbstractEventLoop] = None # Will be set in boot()

       # self.event_bus = AsyncEventBus(logging.getLogger("EventBus"))
        #self.config_manager.set_event_bus(self.event_bus)
        
        self.state = SystemState.INITIALIZING
        self.config_dir = Path(config_dir).resolve()
        self._initial_modules_dir_str = modules_dir # Store as passed before resolving with config

        self.config_manager = ConfigManager(str(self.config_dir), logging.getLogger("ConfigMgr"))
        self._update_logging_from_config() # Update logging based on loaded config

        # Determine final modules directory (config overrides passed arg)
        system_config = self.config_manager.get_system_config()
        final_modules_dir_str = system_config.get("modules_dir", self._initial_modules_dir_str)
        self.modules_dir_path = Path(final_modules_dir_str)
        if not self.modules_dir_path.is_absolute():
            # Resolve relative to kernel's script location if not absolute
            self.modules_dir_path = (_kernel_dir_path / self.modules_dir_path).resolve()
            self.logger.info(f"Modules directory '{final_modules_dir_str}' was relative, resolved to: {self.modules_dir_path}")
        else:
            self.modules_dir_path = self.modules_dir_path.resolve()

        self._kernel_dir_path = _kernel_dir_path
        self.logger.info(f"Kernel's base directory set to: {self._kernel_dir_path}")


        self.event_bus = AsyncEventBus(logging.getLogger("EventBus"))
        self.config_manager.set_event_bus(self.event_bus) # Link event bus to config manager

        self.redis_pool: Optional[aioredis.Redis] = None
        self.redis_stream_logger: Optional[RedisStreamLogger] = None # Redis connection pool, if used


        self.llm_manager: Optional[LLMManager] = None # Will be set if LLMManager module is loaded

        self.module_loader = ModuleLoader(str(self.modules_dir_path), self.event_bus, self.config_manager, logging.getLogger("ModLoader"))
        self.diagnostics = Diagnostics(self.event_bus, self.config_manager, self.module_loader, logging.getLogger("Diag"))
        self.api = KernelAPI(self) # API provides access to kernel components

        self.ui_manager_instance = UIManagerModule("Kernel_UIManager", self.event_bus, logging.getLogger("UIManager"))
        self.api.set_ui_manager(self.ui_manager_instance) # Pass to KernelAPI


        setattr(self.event_bus, 'kernel_api', self.api) # Set API on event bus for access in events
        self.logger.info("Kernel API initialized and linked to event bus.")

        self.cli: Optional[AsyncCommandLineInterface] = None # Type hinted with forward referenced class
        self._cli_thread: Optional[threading.Thread] = None
        
        self._running = asyncio.Event() # Signals if the kernel's main operational loop should run
        self._main_loop_task: Optional[asyncio.Task] = None # Task for kernel's own periodic activities
        
        self._shutdown_requested = False
        self._restart_requested = False
        self._signal_handlers_set = False
        self.logger.info(f"Async Kernel initialized. Config: '{self.config_dir}', Modules: '{self.modules_dir_path}'.")

    def _configure_root_logger(self, level_str: str = "INFO"):
        # Basic initial configuration. Will be refined by _update_logging_from_config.
        log_format = '%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S,'
        
        # Clear existing handlers from root logger to avoid duplicates if re-initialized
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close() # Close handler before removing

        try:
            log_level_int = logging.getLevelName(level_str.upper())
            if not isinstance(log_level_int, int): # Check if getLevelName succeeded
                log_level_int = logging.INFO
                print(f"Warning: Invalid initial log level '{level_str}'. Defaulting to INFO.")
        except Exception:
            log_level_int = logging.INFO
            print(f"Warning: Exception setting initial log level '{level_str}'. Defaulting to INFO.")

        logging.basicConfig(level=log_level_int, format=log_format, datefmt=date_format, stream=sys.stdout)
        # Ensure our logger also gets this level
        if hasattr(self, 'logger'):
            self.logger.setLevel(log_level_int)


    def _update_logging_from_config(self):
        try:
            cfg = self.config_manager.get_system_config() # Already loaded in __init__
            level_str = cfg.get("log_level", "INFO").upper()
            log_level_int = logging.getLevelName(level_str)

            root_logger = logging.getLogger()
            if not isinstance(log_level_int, int):
                self.logger.warning(f"Invalid log_level '{level_str}' in config. Using current level or INFO.")
                log_level_int = root_logger.level if root_logger.level else logging.INFO # Fallback

            root_logger.setLevel(log_level_int)
            for handler in root_logger.handlers: # Update existing handlers (like stdout from basicConfig)
                handler.setLevel(log_level_int)
            
            self.logger.info(f"Log level set to {logging.getLevelName(log_level_int)} from config.")

            log_file_name = cfg.get("log_file")
            if log_file_name:
                log_dir = self.config_dir / "logs" # Store logs inside config directory
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                    log_path = (log_dir / log_file_name).resolve()
                    
                    # Check if a file handler for this path already exists
                    file_handler_exists = any(
                        isinstance(h, logging.FileHandler) and Path(h.baseFilename).resolve() == log_path # type: ignore
                        for h in root_logger.handlers
                    )

                    if not file_handler_exists:
                        fh = logging.FileHandler(log_path, encoding='utf-8', mode='a') # Append mode
                        log_formatter = logging.Formatter('%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S,')
                        fh.setFormatter(log_formatter)
                        fh.setLevel(log_level_int)
                        root_logger.addHandler(fh)
                        self.logger.info(f"Logging additionally to file: {log_path}")
                    else: # If handler exists, just ensure its level is updated
                        for h in root_logger.handlers:
                            if isinstance(h, logging.FileHandler) and Path(h.baseFilename).resolve() == log_path: # type: ignore
                                h.setLevel(log_level_int)
                except Exception as e_fh:
                    self.logger.error(f"Error setting up file logger for {log_file_name}: {e_fh}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Error updating logging configuration from system_config: {e}", exc_info=True)


    def setup_signal_handlers(self) -> None:
        if self._signal_handlers_set or not self.event_loop: return # Guard: no loop, no handlers
        
        loop_for_signals = self.event_loop # Use the captured event loop

        def _shutdown_signal_handler(sig_num: int):
            try: sig_name = signal.Signals(sig_num).name
            except ValueError: sig_name = f"Signal {sig_num}"

            if self._shutdown_requested:
                self.logger.warning(f"{sig_name} received, but shutdown already in progress.")
            else:
                self.logger.warning(f"{sig_name} received. Initiating graceful shutdown...")
                self._shutdown_requested = True # Set flag early
                # Schedule kernel shutdown on its own event loop
                if loop_for_signals and loop_for_signals.is_running():
                    asyncio.run_coroutine_threadsafe(self.shutdown(), loop_for_signals)
                else: # Fallback if loop isn't running or available when signal hits
                    self.logger.warning("Cannot schedule async shutdown from signal: Kernel event loop not running/available.")
                    # Potentially trigger a more forceful synchronous stop if needed, but risky.
                    # For now, rely on the fact that self._shutdown_requested is set.

        sig_types_to_handle = (signal.SIGINT, signal.SIGTERM)
        if sys.platform != "win32": # SIGHUP and SIGQUIT are not typically on Windows
            sig_types_to_handle += (signal.SIGHUP, signal.SIGQUIT) # type: ignore

        for sig_type in sig_types_to_handle:
            try:
                if hasattr(loop_for_signals, 'add_signal_handler'): # Preferred asyncio way
                    loop_for_signals.add_signal_handler(sig_type, _shutdown_signal_handler, sig_type)
                else: # Fallback for environments where add_signal_handler isn't available (e.g. Windows default loop)
                    signal.signal(sig_type, lambda s,f: _shutdown_signal_handler(s)) # type: ignore
                self.logger.debug(f"Registered signal handler for {signal.Signals(sig_type).name}.")
            except (NotImplementedError, ValueError, OSError, AttributeError) as e_sig:
                self.logger.warning(f"Could not set signal handler for {signal.Signals(sig_type).name}: {e_sig}. Trying basic signal.signal if not already tried.")
                # Fallback for specific signals if loop.add_signal_handler failed
                if not hasattr(loop_for_signals, 'add_signal_handler'): # Only if the primary method isn't there
                    try:
                        signal.signal(sig_type, lambda s,f: _shutdown_signal_handler(s)) # type: ignore
                        self.logger.info(f"Registered basic signal.signal handler for {signal.Signals(sig_type).name}.")
                    except Exception as e_sig_fb:
                        self.logger.error(f"Failed to set basic signal.signal handler for {signal.Signals(sig_type).name}: {e_sig_fb}")

        self._signal_handlers_set = True


    async def boot(self) -> bool:
        if self.state != SystemState.INITIALIZING:
            self.logger.error(f"Cannot boot from state {self.state.name}."); return False
        self.logger.info("--- PresenceOS Async Kernel Booting ---")
        self.state = SystemState.BOOTING
        self._shutdown_requested = False; self._restart_requested = False

        try:
            llm_config_path = os.path.join(self.config_dir, "llm_clients.json")
            self.llm_manager = LLMManager(
                config_path=llm_config_path,
                logger=self.logger.getChild('LLMManager'),
                # Pass KernelAPI instance
                kernel_base_dir=str(self._kernel_dir_path) # Pass kernel base directory
            )
            self.llm_manager.load_clients() # Load LLM clients from config
            self.logger.info(f"LLM Manager initialized with {len(self.llm_manager.clients)} active clients.")
            self.api.llm_manager = self.llm_manager # Set LLMManager in KernelAPI
        except Exception as e:
            self.logger.critical(f"FATAL: LLMManager failed to initialize: {e}", exc_info=True)
            self.state = SystemState.ERROR
            return False

        try:
            self.event_loop = asyncio.get_running_loop()
            self.logger.info(f"Kernel captured event loop during boot: {self.event_loop}")
        except RuntimeError:
            self.logger.critical("CRITICAL: Kernel could not obtain running event loop during boot. Cannot proceed.")
            self.state = SystemState.ERROR
            return False

        self.setup_signal_handlers() # Setup signal handlers using self.event_loop
####
        sys_cfg = self.config_manager.get_system_config()

 #       llm_config_path = os.path.join(self.config_dir, "llm_clients.json")
  #      self.api.llm_manager = LLMManager(
 #           config_path=llm_config_path,
  #          logger=self.logger,
 #            # Pass KernelAPI instance
  #          kernel_base_dir=self._kernel_dir_path,
             # Pass kernel base directory
   #     )
    #    self.llm_manager.load_clients()
     #   self.logger.info(f"LLM Manager initalized with {len(self.llm_manager.clients)} active clients.")
      #  self.llm_manager = self.llm_manager
        redis_url = os.getenv("REDIS_URL")
        print(f"[DEBUG] REDIS_URL from env: {redis_url}") # Debug print to check env var
        if not redis_url:
            self.logger.critical("KERNEL_BOOT: REDIS_URL environment variable not set. Cannot connect to Redis.")
            
            raise ValueError("REDIS_URL environment variable is required for Redis connection.")
        self.logger.info(f"KERNEL_BOOT: Using REDIS_URL from environment: {redis_url}")
        # --- REDIS INITIALIZATION ---





####
#        redis_host = os.getenv("REDIS_HOST", sys_cfg.get("redis_host"))
#        if redis_host.startswith("10."):
#            try:
 #               socket.gethostbyname(redis_host)
 #           except:
 #               redis_host = "redis" # Fallback to localhost if DNS resolution fails
  #      redis_port = int(os.getenv("REDIS_PORT", sys_cfg.get("redis_port", 6379)))
  #      redis_db = int(os.getenv("REDIS_DB", sys_cfg.get("redis_db", 0)))
  #      redis_password = os.getenv("REDIS_PASSWORD", sys_cfg.get("redis_password"))


#        redis_host = os.getenv("REDIS_HOST", "localhost")
#        redis_port = int(os.getenv("REDIS_PORT", 6379))
#        redis_db = int(os.getenv("REDIS_DB", 0))
#        redis_password = os.getenv("REDIS_PASSWORD", "") # Can be empty string if not set
   #     sys_cfg = self.config_manager.get_system_config()
#        redis_host = sys_cfg.get("redis_host", "localhost")

#        redis_port = int(sys_cfg.get("redis_port", 6379))
#        redis_db = int(sys_cfg.get("redis_db", 0))
#        redis_password = sys_cfg.get("redis_password") # Can be None or empty string

  #      redis_url = f"redis://{':'+redis_password+'@' if redis_password else ''}{redis_host}:{redis_port}/{redis_db}"
        
        try:
            self.logger.info(f"KERNEL_BOOT: Attempting to connect to Redis at URL: {redis_url}")
            self.redis_pool = await aioredis.from_url(
                redis_url,
                decode_responses=True,
                health_check_interval=30 
            )
            await self.redis_pool.ping() # This is the crucial test
            self.logger.info(f"KERNEL_BOOT: Successfully connected and authenticated to Redis. self.redis_pool is now: {type(self.redis_pool)}")

            if REDIS_STREAM_LOGGER_AVAILABLE: # Global flag from top of file
                self.redis_stream_logger = RedisStreamLogger(
                    self.redis_pool, # Pass the successfully connected pool
                    base_stream_prefix=sys_cfg.get("redis_log_stream_prefix", "aetherpro_logs")
                )
                self.logger.info(f"KERNEL_BOOT: RedisStreamLogger initialized. self.redis_stream_logger is type: {type(self.redis_stream_logger)}")
            else:
                self.logger.warning("KERNEL_BOOT: RedisStreamLogger class not available (import failed at top of kernel.py). Stream logging disabled globally.")
                self.redis_stream_logger = None 
        except aioredis.exceptions.AuthenticationError as auth_err:
            self.logger.error(f"KERNEL_BOOT: Redis AuthenticationError: {auth_err}. Check redis_password in system_config.json.", exc_info=True)
            self.redis_pool = None # Ensure it's None on failure
            self.redis_stream_logger = None
        except (aioredis.exceptions.ConnectionError, ConnectionRefusedError, asyncio.TimeoutError) as conn_err:
            self.logger.error(f"KERNEL_BOOT: Redis ConnectionError/Timeout: {conn_err}. Check Redis server and network.", exc_info=True)
            self.redis_pool = None 
            self.redis_stream_logger = None
        except Exception as e_redis: 
            self.logger.error(f"KERNEL_BOOT: Generic Redis/StreamLogger init failed: {e_redis}", exc_info=True)
            self.redis_pool = None 
            self.redis_stream_logger = None
        # --- END REDIS INITIALIZATION ---

        # Start EventBus AFTER Redis pool might be needed by modules getting KernelAPI
        # (Though KernelAPI getters are called during module init, which is after this block)
       

        try:
            await self.event_bus.start()
            await self.diagnostics.initialize()
            await self.event_bus.publish(Event(EventType.SYSTEM_BOOT, "Kernel", priority=Priority.CRITICAL))

            await self.ui_manager_instance.initialize() # Initialize UIManagerModule
            self.logger.info("UI Manager module initialized.")

            self.logger.info("Discovering and registering modules...")
            discovered_modules = self.module_loader.discover_modules()
            reg_results = await asyncio.gather(*(self.module_loader.register_module(m) for m in discovered_modules), return_exceptions=True)
            successful_regs = sum(1 for r in reg_results if isinstance(r, bool) and r)
            self.logger.info(f"Registered {successful_regs}/{len(discovered_modules)} modules.")

            system_config = self.config_manager.get_system_config()
            if system_config.get("autostart_modules", True):
                self.logger.info("Auto-starting registered modules...")
                await self.start_modules() # Start modules based on priority
            else:
                self.logger.info("Module auto-start is disabled in system configuration.")

            # Schedule CLI initialization for after kernel is fully booted
            # This prevents circular import issues during boot
            if self.event_loop:
                cli_init_task = self.event_loop.create_task(self._initialize_cli_after_boot())
                # Wait for CLI initialization to complete before proceeding
                await cli_init_task
            else:
                self.logger.warning("CLI initialization deferred: No event loop available during boot.")

            self.state = SystemState.RUNNING
            self._running.set() # Signal that kernel is now running

            # Set kernel readiness flag for CLI and other modules
            setattr(sys, '_presence_os_kernel_ready', True)

            await self.event_bus.publish(Event(EventType.SYSTEM_READY, "Kernel", priority=Priority.HIGH))

            # Start kernel's main internal loop (e.g., for periodic health checks)
            if self.event_loop:
                if not self._main_loop_task or self._main_loop_task.done():
                    self._main_loop_task = self.event_loop.create_task(self._main_loop(), name="AsyncKernelMainLoop")
            else: # Should be caught earlier
                self.logger.critical("Kernel event_loop is None. Cannot start kernel's main internal loop.")
                raise RuntimeError("Kernel event_loop not set.")

            self.logger.info("--- PresenceOS Async Kernel Boot Sequence Complete ---")
            return True

        except Exception as e_boot_main:
            self.logger.critical(f"CRITICAL ASYNC KERNEL BOOT FAILURE: {e_boot_main}", exc_info=True)
            self.state = SystemState.ERROR
            self._running.clear() # Ensure _running is cleared if boot fails
            if hasattr(self, '_cleanup_after_boot_failure'): await self._cleanup_after_boot_failure()
            # Try to publish system error event if event bus started
            if self.event_bus and self.event_bus._running:
                try:
                              await self.event_bus.publish(Event(EventType.SYSTEM_ERROR, "Kernel", time.time(), id="SYSTEM_ERROR", data={"error": str(e_boot_main)}, priority=Priority.CRITICAL))
                except Exception as e_pub_err: self.logger.error(f"Failed to publish boot error event: {e_pub_err}")
            return False
    
    def _handle_cli_init_completion(self, task):
        """Handle completion of CLI initialization task"""
        try:
            if task.exception():
                self.logger.error(f"CLI initialization task failed: {task.exception()}", exc_info=task.exception())
            else:
                self.logger.info("CLI initialization task completed successfully")
        except Exception as e:
            self.logger.error(f"Error handling CLI initialization completion: {e}", exc_info=True)

    async def _initialize_cli_after_boot(self):
        """Initialize CLI after kernel is fully booted to avoid circular imports"""
        try:
            self.logger.info("CLI initialization: Starting CLI initialization after boot...")
            # Small delay to ensure kernel is fully ready
            await asyncio.sleep(0.1)

            # Use importlib to import/reload the CLI module
            import importlib
            if 'cli' in sys.modules:
                self.logger.info("CLI initialization: Reloading existing cli module...")
                importlib.reload(sys.modules['cli'])

            self.logger.info("CLI initialization: Finding CLI module spec...")
            cli_module_spec = importlib.util.find_spec("cli")
            if cli_module_spec:
                self.logger.info("CLI initialization: Importing CLI module...")
                cli_py_module = importlib.import_module("cli")
                self.logger.info(f"CLI initialization: CLI module imported. Checking for AsyncCommandLineInterface class...")

                if hasattr(cli_py_module, "AsyncCommandLineInterface"):
                    self.logger.info("CLI initialization: AsyncCommandLineInterface class found. Creating instance...")
                    AsyncCLIClass = getattr(cli_py_module, "AsyncCommandLineInterface")
                    if self.event_loop:
                        self.logger.info("CLI initialization: Creating CLI instance with kernel API and event loop...")
                        self.cli = AsyncCLIClass(self.api, self.event_loop)
                        self.logger.info("CLI initialization: AsyncCommandLineInterface initialized successfully.")
                        self.start_cli() # Starts CLI in its own thread
                        self.logger.info("CLI initialization: CLI thread started. CLI initialization completed successfully.")
                    else:
                        self.logger.error("CLI initialization: Cannot initialize CLI: Kernel event_loop is None.")
                else:
                    self.logger.warning("CLI initialization: cli.py found, but 'AsyncCommandLineInterface' class missing. CLI disabled.")
                    # Debug: List all attributes in the module
                    attrs = [attr for attr in dir(cli_py_module) if not attr.startswith('_')]
                    self.logger.warning(f"CLI initialization: Available attributes in cli module: {attrs}")
            else:
                self.logger.warning("CLI initialization: CLI module (cli.py) not found by importlib. CLI disabled.")

        except ImportError as e_imp:
            self.logger.warning(f"CLI initialization: Could not import CLI module (cli.py): {e_imp}. CLI disabled.")
        except Exception as e_cli:
            self.logger.error(f"CLI initialization: Failed to initialize CLI: {e_cli}", exc_info=True)

    async def _cleanup_after_boot_failure(self):
        self.logger.warning("Attempting async cleanup after boot failure...")
        if self.cli and self._cli_thread and self._cli_thread.is_alive():
            try:
                if hasattr(self.cli, 'stop'): self.cli.stop() # type: ignore
                # Join might be problematic if CLI thread is stuck
            except Exception as e: self.logger.error(f"Error stopping CLI during boot cleanup: {e}")
        
        # Unregister modules that might have been registered
        if self.module_loader:
            module_ids_to_unreg = list(self.module_loader.modules.keys())
            if module_ids_to_unreg:
                self.logger.debug(f"Unregistering modules after boot fail: {module_ids_to_unreg}")
                await asyncio.gather(*(self.module_loader.unregister_module(mid) for mid in module_ids_to_unreg), return_exceptions=True)

        if self.diagnostics and hasattr(self.diagnostics, 'shutdown'): 
            try: await self.diagnostics.shutdown()
            except Exception as e: self.logger.error(f"Error shutting down diagnostics during boot cleanup: {e}")
        
        if self.event_bus and self.event_bus._running:
            try: await self.event_bus.stop()
            except Exception as e: self.logger.error(f"Error stopping EventBus during boot cleanup: {e}")
        self.logger.warning("Async cleanup after boot failure finished.")


    async def _main_loop(self) -> None:
        self.logger.info("Async Kernel main internal loop started.")
        try:
            # Get initial interval, can be updated if config changes
            health_interval = self.diagnostics.health_check_interval if self.diagnostics else 60
            last_health_check = time.monotonic()

            while self._running.is_set(): # Loop as long as kernel is running
                now = time.monotonic()
                # Re-fetch config in case it changed (e.g. diagnostics interval)
                current_sys_config = self.config_manager.get_system_config()
                diagnostics_enabled = current_sys_config.get("enable_diagnostics", True)
                if self.diagnostics: # Update interval if diagnostics object exists
                    health_interval = self.diagnostics.health_check_interval = current_sys_config.get("health_check_interval", health_interval)

                if diagnostics_enabled and self.diagnostics and (now - last_health_check >= health_interval):
                    try:
                        await self.diagnostics.run_health_check(force=False) # Use cached if within interval
                        last_health_check = now
                    except Exception as e_health:
                        self.logger.error(f"Periodic health check failed: {e_health}", exc_info=True)
                        last_health_check = now # Still update time to avoid rapid retries on persistent error
                
                # Determine wait time until next health check or a short sleep
                time_to_next_check = (last_health_check + health_interval) - now
                sleep_duration = max(0.1, min(time_to_next_check, 5.0)) if diagnostics_enabled else 5.0 # Sleep at most 5s, or less if check is due

                try:
                    # Wait for a short duration or until _running is cleared
                    await asyncio.wait_for(self._running.wait(), timeout=sleep_duration)
                    # If wait() returned, it means _running was cleared. Break loop.
                    if not self._running.is_set(): break 
                except asyncio.TimeoutError:
                    continue # Timeout is normal, means _running is still set, continue loop

        except asyncio.CancelledError:
            self.logger.info("Async Kernel main internal loop cancelled.")
        except Exception as e_main_loop:
            self.logger.critical(f"FATAL ERROR IN KERNEL MAIN INTERNAL LOOP: {e_main_loop}", exc_info=True)
            self.state = SystemState.ERROR
            self._running.clear() # Stop the kernel
            # Trigger emergency shutdown if not already requested
            if not self._shutdown_requested:
                self.logger.critical("Emergency shutdown triggered due to main internal loop error.")
                if self.event_loop and self.event_loop.is_running(): # Ensure loop exists
                    self.event_loop.create_task(self.shutdown()) # Schedule shutdown on its own loop
                else: # Fallback if loop is gone
                    asyncio.run(self.shutdown()) # This is risky if called from within a running loop context
        finally:
            self.logger.info("Async Kernel main internal loop stopped.")


    def start_cli(self):
        if not self.cli: self.logger.error("Cannot start CLI: Not initialized."); return
        if self._cli_thread and self._cli_thread.is_alive(): self.logger.warning("CLI thread already running."); return

        if hasattr(self.cli, 'start') and callable(self.cli.start):
            self._cli_thread = threading.Thread(target=self.cli.start, name="KernelCLI", daemon=False) # Non-daemon
            self._cli_thread.start()
            self.logger.info("CLI started in dedicated thread.")
        else:
            self.logger.error("CLI object is missing a callable 'start' method.")


    async def start_modules(self) -> None:
        all_module_infos = self.module_loader.get_all_modules() # List[ModuleInfo]
        if not all_module_infos: self.logger.info("No modules registered to start."); return

        # Sort modules by priority (lower number = higher priority), then by ID for stable order
        sorted_modules_to_start = sorted(all_module_infos, key=lambda mi: (mi.startup_priority.value, mi.id))
        
        self.logger.info(f"Async module startup sequence: {', '.join(mi.id for mi in sorted_modules_to_start)}")
        started_count, failed_count, skipped_count = 0, 0, 0

        for mod_info in sorted_modules_to_start:
            if mod_info.state in [ModuleState.REGISTERED, ModuleState.STOPPED, ModuleState.ERROR]:
                self.logger.debug(f"Attempting auto-start for '{mod_info.id}' (State: {mod_info.state.name})")
                if await self.module_loader.load_module(mod_info.id):
                    started_count += 1
                else:
                    failed_count += 1 # load_module sets state to ERROR if it fails
            else: # Already RUNNING, PAUSED, LOADING, etc.
                 skipped_count += 1
                 self.logger.debug(f"Skipping auto-start for '{mod_info.id}' (already in state {mod_info.state.name}).")
        self.logger.info(f"Async module startup finished. Started: {started_count}, Failed: {failed_count}, Skipped: {skipped_count}.")


    async def shutdown(self) -> None:
        if self.state == SystemState.SHUTTING_DOWN and self._shutdown_requested: # Avoid re-entry
            self.logger.warning("Shutdown already in progress."); return
        
        self.logger.warning("--- PresenceOS Async Kernel Shutting Down ---")
        self._shutdown_requested = True # Primary flag to signal shutdown
        self.state = SystemState.SHUTTING_DOWN
        self._running.clear() # Signal main loops and waits to stop

        # Publish shutdown event (best effort)
        if self.event_bus and self.event_bus._running:
            try:
                await self.event_bus.publish(Event(EventType.SYSTEM_SHUTDOWN, "Kernel", priority=Priority.CRITICAL))
                await asyncio.sleep(0.05) # Allow event to propagate if possible
            except Exception as e_pub: self.logger.error(f"Error publishing shutdown event: {e_pub}")

        # Stop CLI
        if self.cli and self._cli_thread and self._cli_thread.is_alive():
            self.logger.info("Stopping CLI...")
            try:
                if hasattr(self.cli, 'stop'): self.cli.stop() # type: ignore
                self._cli_thread.join(timeout=2.0) # Wait for CLI thread
                if self._cli_thread.is_alive(): self.logger.warning("CLI thread did not exit cleanly.")
            except Exception as e_cli_stop: self.logger.error(f"Error stopping CLI: {e_cli_stop}")

        if self.ui_manager_instance:
            self.logger.debug("Shutting down UI Manager module...")
            try: await self.ui_manager_instance.stop()
            except Exception as e_ui_stop: self.logger.error(f"Error shutting down UI Manager: {e_ui_stop}")

        # Unload modules (reverse priority order)
        if self.module_loader:
            self.logger.info("Unloading all modules (forced, reverse priority)...")
            all_mod_infos = self.module_loader.get_all_modules()
            # Sort reverse by priority value (higher value = lower priority, so unload first), then by ID
            sorted_modules_to_unload = sorted(all_mod_infos, key=lambda mi: (mi.startup_priority.value, mi.id), reverse=True)
            self.logger.debug(f"Module unload order: {', '.join(mi.id for mi in sorted_modules_to_unload)}")
            
            unload_results = await asyncio.gather(
                *(self.module_loader.unload_module(mi.id, force=True) for mi in sorted_modules_to_unload),
                return_exceptions=True
            )
            for i, res_exc in enumerate(unload_results):
                mod_id_unloaded = sorted_modules_to_unload[i].id
                if isinstance(res_exc, Exception) or res_exc is False:
                    self.logger.error(f"Error or failure unloading module '{mod_id_unloaded}' during shutdown: {res_exc}")
        
        # Shutdown diagnostics
        if self.diagnostics and hasattr(self.diagnostics, 'shutdown'):
            self.logger.debug("Shutting down diagnostics...")
            try: await self.diagnostics.shutdown()
            except Exception as e_diag: self.logger.error(f"Error shutting down diagnostics: {e_diag}")

        # Stop event bus
        if self.event_bus and self.event_bus._running:
             self.logger.info("Stopping Async Event Bus...");
             try: await self.event_bus.stop()
             except Exception as e_bus: self.logger.error(f"Error stopping event bus: {e_bus}")

        # Cancel kernel's main internal loop task
        if self._main_loop_task and not self._main_loop_task.done():
            self.logger.debug("Cancelling kernel's main internal loop task...")
            self._main_loop_task.cancel()
            try:
                await asyncio.wait_for(self._main_loop_task, timeout=2.0)
            except asyncio.CancelledError: self.logger.debug("Kernel main internal loop task confirmed cancelled.")
            except asyncio.TimeoutError: self.logger.warning("Kernel main internal loop task did not cancel cleanly within timeout.")
            except Exception as e_task_wait: self.logger.error(f"Error waiting for main internal loop task cancellation: {e_task_wait}")
        
        self.logger.warning("--- PresenceOS Async Kernel Shutdown Complete ---")
        # self.state = SystemState.STOPPED # Or some final state if needed, though process will exit

        if self._restart_requested:
            # This needs to be handled by the launcher script now, kernel cannot restart itself easily from within asyncio.run
            self.logger.warning("Kernel restart was requested. The launcher script should handle the actual restart process.")
            # Signal launcher if possible (e.g. specific exit code, or launcher checks _restart_requested)
        else:
            # Python's logging.shutdown() is called by launcher's finally block
            pass
        if self.llm_manager:
            self.llm_manager.shutdown_clients()

    async def restart(self) -> None: # This method now mostly signals intent
        if self.state == SystemState.SHUTTING_DOWN:
            self.logger.error("Cannot initiate restart while already shutting down."); return
        if self._restart_requested:
            self.logger.warning("Restart already requested."); return

        self.logger.warning("--- PresenceOS Async Kernel Restart Requested ---")
        self.logger.warning("Kernel will shut down. The external launcher is responsible for restarting the process.")
        self._restart_requested = True # Launcher can check this flag after shutdown completes

        if not self._shutdown_requested: # If shutdown hasn't started, initiate it
            self.logger.info("Initiating shutdown as part of restart process.")
            # Schedule shutdown on its own loop to avoid blocking current context if called from sync
            if self.event_loop and self.event_loop.is_running():
                self.event_loop.create_task(self.shutdown())
            else: # Fallback if called when loop isn't running (less ideal)
                await self.shutdown()

    # _perform_restart method is removed as kernel can't reliably restart itself from within asyncio.run
    # Restart logic should be in the launcher script (run_presence_os.py)