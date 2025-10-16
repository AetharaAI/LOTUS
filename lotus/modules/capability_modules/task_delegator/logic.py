"""
Task Delegator Module - Intelligent Task Routing

Analyzes task complexity and delegates to optimal LLM provider.
"""

import asyncio
from typing import Dict, List, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from lib.module import BaseModule
from lib.decorators import on_event, tool
from lib.logging import get_logger

logger = get_logger("task_delegator")


class TaskComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class TaskAnalysis:
    """Task analysis result"""
    complexity: TaskComplexity
    estimated_tokens: int
    reasoning_required: bool
    parallelizable: bool
    suggested_provider: str
    confidence: float


class TaskDelegator(BaseModule):
    """Analyze tasks and delegate to optimal providers"""
    
    async def initialize(self) -> None:
        """Initialize task delegator"""
        self.logger.info("🎯 Initializing Task Delegator Module")
    
    @on_event("cognition.task")
    async def handle_task(self, event: Dict[str, Any]) -> None:
        """Handle incoming task"""
        task = event.get("task", "")
        self.logger.info(f"📋 Received task: {task[:50]}...")
        
        # Analyze
        analysis = await self.analyze_task(task)
        self.logger.info(f"📊 Analysis: {analysis.complexity.value} complexity")
        
        # Delegate
        result = await self.delegate_task(task, analysis)
        
        await self.publish("task.delegated", {
            "task": task,
            "analysis": {
                "complexity": analysis.complexity.value,
                "provider": analysis.suggested_provider
            },
            "result": result
        })
    
    async def analyze_task(self, task: str) -> TaskAnalysis:
        """Analyze task complexity"""
        # Simple heuristics for task analysis
        word_count = len(task.split())
        
        # Token estimate (rough: 1.3 tokens per word)
        estimated_tokens = int(word_count * 1.3)
        
        # Complexity assessment
        if word_count < 20:
            complexity = TaskComplexity.SIMPLE
        elif word_count < 100:
            complexity = TaskComplexity.MODERATE
        elif word_count < 300:
            complexity = TaskComplexity.COMPLEX
        else:
            complexity = TaskComplexity.EXPERT
        
        # Reasoning requirement
        reasoning_required = any(keyword in task.lower() 
                                for keyword in ["why", "how", "analyze", "explain"])
        
        # Parallelizable
        parallelizable = "and" in task.lower() or ";" in task
        
        # Provider recommendation
        if complexity == TaskComplexity.SIMPLE:
            provider = "grok-4-fast"  # Cheapest for simple
        elif complexity == TaskComplexity.MODERATE:
            provider = "grok-4-fast"  # Still fast enough
        elif complexity == TaskComplexity.COMPLEX:
            provider = "claude-sonnet-4.5"  # Need better reasoning
        else:
            provider = "claude-opus-4"  # Complex work
        
        return TaskAnalysis(
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            reasoning_required=reasoning_required,
            parallelizable=parallelizable,
            suggested_provider=provider,
            confidence=0.75
        )
    
    async def delegate_task(self, task: str, analysis: TaskAnalysis) -> Dict[str, Any]:
        """Delegate task to provider"""
        self.logger.info(f"🚀 Delegating to {analysis.suggested_provider}")
        
        # Create completion request
        completion_event = {
            "prompt": task,
            "provider": analysis.suggested_provider,
            "max_tokens": min(analysis.estimated_tokens * 3, 8000),
            "temperature": 0.7 if not analysis.reasoning_required else 0.5
        }
        
        # Publish to provider module
        await self.publish("llm.complete", completion_event)
        
        return {
            "delegated_to": analysis.suggested_provider,
            "complexity": analysis.complexity.value
        }
    
    @tool("analyze_task")
    async def analyze_task_tool(self, task: str) -> Dict[str, Any]:
        """Analyze task and return recommendations"""
        analysis = await self.analyze_task(task)
        return {
            "complexity": analysis.complexity.value,
            "tokens_estimated": analysis.estimated_tokens,
            "suggested_provider": analysis.suggested_provider,
            "confidence": analysis.confidence
        }