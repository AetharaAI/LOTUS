# modules/core_modules/context_orchestrator/logic.py
"""
LOTUS Context Orchestrator Module

This module acts as an intelligent intermediary between raw perception data
and the Reasoning Engine. Its responsibilities include:

1.  **Ingestion of Raw Perception:** Subscribes to `perception.raw.*` channels.
2.  **Data Compression/Condensation:** Applies logic (e.g., summarization, diffing) to reduce the volume of large inputs without losing meaning.
3.  **Durable Storage:** Stores both full-fidelity raw data and condensed representations into the 4-tier Memory System.
4.  **Intelligent Triage:** Decides *when* a perceived event is significant enough to warrant engaging the `ReasoningEngine`.
5.  **Selective Reasoning Trigger:** Publishes `cognition.orchestrated_input` with a condensed summary and references to full memory for the `ReasoningEngine` to act upon.

This ensures the Reasoning Engine (Ash persona) is always fed with relevant,
pre-processed context, optimizing LLM token usage and system efficiency for
an always-on intelligence.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
import logging # For dedicated module logger

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic
from lib.memory import MemoryItem, MemoryType, RetrievalConfig, RetrievalStrategy

class ContextOrchestrator(BaseModule):
    """
    Intelligent Orchestrator for Perception and Context Management.

    Triage, compress, persist raw perception data, and selectively alert
    the Reasoning Engine with condensed, high-value information.
    """

    def __init__(self, name: str, metadata: Dict, message_bus: Any, config: Any, logger: logging.Logger):
        super().__init__(name, metadata, message_bus, config, logger)
        self.logger = logging.getLogger(f"lotus.module.{self.name}") # Ensure dedicated logger

        self.last_reasoning_trigger_time: Dict[str, float] = {} # {content_hash: timestamp}
        self.cooldown_period_seconds: float = 0.0

    async def initialize(self):
        """Initialize the Context Orchestrator."""
        self.logger.info("Context Orchestrator initializing...")

        # Configuration for triage and compression
        self.min_importance_threshold = self.config.get("context_orchestrator.min_importance_threshold", 0.3)
        self.summarize_threshold_chars = self.config.get("context_orchestrator.summarize_threshold_chars", 500)
        self.screen_update_diff_threshold = self.config.get("context_orchestrator.screen_update_diff_threshold", 0.1)
        self.cooldown_period_seconds = self.config.get("context_orchestrator.cooldown_period_seconds", 5.0)

        # Ensure memory and LLM services are available
        self.memory = self.config.get("services.memory")
        if not self.memory:
            self.logger.critical("Memory service not available. Context Orchestrator cannot function.")
            raise RuntimeError("Memory service not found.")
        self.llm = self.config.get("services.llm")
        if not self.llm:
            self.logger.warning("LLM service not available. Context Orchestrator's summarization capabilities will be limited.")

        self.logger.info("Context Orchestrator initialized successfully.")
    
    @on_event("perception.raw.user_input")
    async def handle_raw_user_input(self, event: Dict) -> None:
        """
        Handles raw user input (e.g., from CLI, voice).
        This is typically short and directly relevant, so it usually triggers reasoning.
        """
        raw_text = event.data.get("text", "")
        context_data = event.data.get("context", {})
        source_module = event.get("source", self.name)
        
        self.logger.debug(f"Received raw user input: {raw_text[:100]}...")

        # Store raw input (L2 for full fidelity)
        raw_memory_id = await self._store_raw_perception(
            content=raw_text,
            memory_type=MemoryType.EPISODIC,
            metadata={"original_channel": event.channel, **context_data},
            source_module=source_module
        )

        # For user input, a direct trigger to reasoning is usually desired
        await self._trigger_reasoning(
            summary=raw_text, # User input is its own summary
            memory_references=[raw_memory_id],
            original_event_context=context_data,
            importance=0.9, # User input is generally high importance
            user_query=raw_text,
            source_module=source_module
        )

    @on_event("perception.raw.clipboard_changed")
    async def handle_raw_clipboard_changed(self, event: Dict) -> None:
        """
        Handles raw clipboard content. Compresses if large, stores, then triages.
        """
        raw_content = event.data.get("content", "")
        length = event.data.get("length", 0)
        context_data = event.data.get("context", {})
        source_module = event.get("source", self.name)

        self.logger.debug(f"Received raw clipboard content (length: {length}): {raw_content[:100]}...")

        # Store raw content (L2 for full fidelity)
        raw_memory_id = await self._store_raw_perception(
            content=raw_content,
            memory_type=MemoryType.WORKING, # Consider working as it's transient
            metadata={"original_channel": event.channel, "length": length, **context_data},
            source_module=source_module
        )

        condensed_content = raw_content
        # Condense if content is large
        if length > self.summarize_threshold_chars and self.llm:
            self.logger.debug("Clipboard content is large, attempting summarization...")
            try:
                # Basic summarization - this could be a more sophisticated LLM call
                summarization_prompt = f"Condense the following text without losing key information:\n\n{raw_content}"
                response = await self.llm.complete(
                    prompt=summarization_prompt,
                    provider=self.config.get("providers.default_summarization", "claude-haiku"),
                    max_tokens=200,
                    temperature=0.3
                )
                condensed_content = response.content.strip()
                self.logger.debug(f"Clipboard content summarized. Original: {length}, Condensed: {len(condensed_content)}")
            except Exception as e:
                self.logger.error(f"Error summarizing clipboard content: {e}", exc_info=True)
                # Fallback to original content or truncation if summarization fails
                condensed_content = raw_content[:self.summarize_threshold_chars * 2] + "..." if len(raw_content) > self.summarize_threshold_chars * 2 else raw_content

        # Store condensed content (L3 for semantic meaning)
        condensed_memory_id = await self._store_semantic_summary(
            summary=condensed_content,
            original_memory_id=raw_memory_id,
            metadata={"original_channel": event.channel, "original_length": length, **context_data},
            source_module=source_module
        )

        # Triage: Decide if this clipboard change warrants a reasoning trigger
        # For now, if content is novel enough or significantly condensed, trigger.
        # This could involve diffing against previous clipboard content.
        trigger_reasoning = (len(condensed_content) > 50 and raw_memory_id != self.last_reasoning_trigger_time.get("clipboard_content_hash", ""))
        
        # Simple heuristic: if content is sufficiently unique or important, trigger reasoning
        if trigger_reasoning and self._is_cooldown_over(raw_content):
            await self._trigger_reasoning(
                summary=f"Clipboard updated with: {condensed_content[:200]}...",
                memory_references=[raw_memory_id, condensed_memory_id],
                original_event_context=context_data,
                importance=0.5, # Moderate importance
                source_module=source_module
            )
            self.last_reasoning_trigger_time["clipboard_content_hash"] = raw_content # Store raw content for simple diff check

    @on_event("perception.raw.screen_update")
    async def handle_raw_screen_update(self, event: Dict) -> None:
        """
        Handles raw screen capture data (text extracted from screen, image ref).
        Compresses by diffing, stores, then triages.
        """
        raw_text_content = event.data.get("text_content", "") # Text extracted from screen
        screen_image_ref = event.data.get("image_ref") # Reference to stored image if applicable
        change_percentage = event.data.get("change_percentage", 0.0) # From Perception's diffing
        context_data = event.data.get("context", {})
        source_module = event.get("source", self.name)

        self.logger.debug(f"Received raw screen update (text length: {len(raw_text_content)}, change: {change_percentage:.2f}%).")

        # Only process if there's significant change or new text content
        if change_percentage < self.screen_update_diff_threshold and not raw_text_content.strip():
            self.logger.debug("Screen update below diff threshold and no new text, skipping orchestration.")
            return

        # Store raw screen text (L2 for full fidelity)
        raw_memory_id = await self._store_raw_perception(
            content=raw_text_content,
            memory_type=MemoryType.WORKING, # Working memory for transient screen state
            metadata={"original_channel": event.channel, "change_percentage": change_percentage, "image_ref": screen_image_ref, **context_data},
            source_module=source_module
        )

        condensed_content = raw_text_content
        # Condense if content is large or complex
        if len(raw_text_content) > self.summarize_threshold_chars and self.llm:
            self.logger.debug("Screen text content is large, attempting summarization...")
            try:
                summarization_prompt = f"Condense the key information from the following screen text:\n\n{raw_text_content}"
                response = await self.llm.complete(
                    prompt=summarization_prompt,
                    provider=self.config.get("providers.default_summarization", "claude-haiku"),
                    max_tokens=200,
                    temperature=0.3
                )
                condensed_content = response.content.strip()
                self.logger.debug(f"Screen text summarized. Original: {len(raw_text_content)}, Condensed: {len(condensed_content)}")
            except Exception as e:
                self.logger.error(f"Error summarizing screen text: {e}", exc_info=True)
                condensed_content = raw_text_content[:self.summarize_threshold_chars * 2] + "..." if len(raw_text_content) > self.summarize_threshold_chars * 2 else raw_text_content


        # Store condensed content (L3 for semantic meaning)
        condensed_memory_id = await self._store_semantic_summary(
            summary=condensed_content,
            original_memory_id=raw_memory_id,
            metadata={"original_channel": event.channel, "change_percentage": change_percentage, **context_data},
            source_module=source_module
        )

        # Triage: Decide if this screen update warrants a reasoning trigger
        # If there's new significant condensed content and not on cooldown
        if len(condensed_content) > 50 and self._is_cooldown_over(raw_text_content): # Cooldown based on screen text hash
            await self._trigger_reasoning(
                summary=f"Screen updated with notable content: {condensed_content[:200]}...",
                memory_references=[raw_memory_id, condensed_memory_id],
                original_event_context=context_data,
                importance=0.4, # Screen updates usually lower importance unless user is stuck
                source_module=source_module
            )
            self.last_reasoning_trigger_time["screen_content_hash"] = raw_text_content # Store raw content hash for cooldown


    async def _store_raw_perception(self, content: str, memory_type: MemoryType, metadata: Dict, source_module: str) -> Optional[str]:
        """Helper to store raw perception data into memory (L2 for full fidelity)."""
        if not self.memory: return None
        try:
            memory_id = await self.memory.store_raw_data(
                content=content,
                memory_type=memory_type.value,
                importance=0.1, # Raw data initially low importance unless identified otherwise
                metadata=metadata,
                source_module=source_module
            )
            self.logger.debug(f"Stored raw perception ({memory_type.value}) with ID: {memory_id[:15]}...")
            return memory_id
        except Exception as e:
            self.logger.error(f"Failed to store raw perception data: {e}", exc_info=True)
            return None

    async def _store_semantic_summary(self, summary: str, original_memory_id: Optional[str], metadata: Dict, source_module: str) -> Optional[str]:
        """Helper to store semantic summaries into memory (L3 for meaning)."""
        if not self.memory: return None
        try:
            # We want to use the specific L3 store method which generates embeddings.
            # `self.memory.remember` acts as a facade. We can directly call L3.store if exposed,
            # or ensure `remember` routes correctly. For now, we'll use `remember`
            # and set type/importance to encourage L3 storage.
            
            # The `remember` method of MemoryModule will handle tiering
            memory_id = await self.memory.remember(
                content=summary,
                memory_type=MemoryType.SEMANTIC.value, # Explicitly semantic
                importance=0.6, # Higher importance for condensed meaning
                metadata={"original_memory_id": original_memory_id, **metadata},
                source_module=source_module
            )
            self.logger.debug(f"Stored semantic summary with ID: {memory_id[:15]}...")
            return memory_id
        except Exception as e:
            self.logger.error(f"Failed to store semantic summary: {e}", exc_info=True)
            return None

    async def _trigger_reasoning(self, summary: str, memory_references: List[str], 
                                 original_event_context: Dict, importance: float, user_query: Optional[str] = None, source_module: str = "") -> None:
        """
        Publishes a concise event to the Reasoning Engine, pointing to relevant memories.
        This is the new entry point for Ash's main cognitive loop.
        """
        self.logger.info(f"Triggering Reasoning Engine with summary: {summary[:100]}...")
        
        # Reset cooldown timer for this content (using a simple overall cooldown for now)
        self.last_reasoning_trigger_time["_overall_cooldown"] = time.time()
        
        # Publish to the new channel for ReasoningEngine
        await self.publish(
            "cognition.orchestrated_input",
            {
                "summary": summary,
                "memory_references": memory_references, # IDs to pull full data if needed
                "original_event_context": original_event_context,
                "importance": importance,
                "user_query": user_query, # Pass through direct user queries if applicable
                "source_module": source_module
            }
        )

    def _is_cooldown_over(self, content_hash_key: str = "_overall_cooldown") -> bool:
        """Checks if the reasoning engine is on cooldown for similar content or globally."""
        last_trigger = self.last_reasoning_trigger_time.get(content_hash_key, 0.0)
        now = time.time()
        cooldown_status = (now - last_trigger) > self.cooldown_period_seconds
        if not cooldown_status:
            self.logger.debug(f"Reasoning cooldown active for '{content_hash_key}'. Skipping trigger.")
        return cooldown_status

    async def shutdown(self):
        self.logger.info("Context Orchestrator shutting down.")
        # Any cleanup specific to the orchestrator module


# Add logging setup for ContextOrchestrator to match other modules
import logging
# This ensures that when the ContextOrchestrator is loaded, its logger is configured
logging.getLogger("lotus.module.context_orchestrator").addHandler(logging.NullHandler())