"""
UnityKernel Priority Queue Processor

Tiered parallel processing with priority queues.
Multiple worker pools for different priority levels.
"""

import asyncio
from asyncio import Queue, PriorityQueue
from typing import Dict, Optional, Callable
from datetime import datetime
import time

from .types import Event, Priority, QueueItem


class AsyncPriorityProcessor:
    """
    Multi-tiered async queue processor

    Architecture:
    - CRITICAL: 4 workers, processes immediately
    - HIGH: 8 workers, <100ms latency
    - NORMAL: 16 workers, best effort
    - LOW: 4 workers, opportunistic
    - DEFERRED: 2 workers, runs when idle

    Each tier is independent. Critical tasks never wait for low-priority work.
    """

    def __init__(self, event_bus: any):
        """
        Initialize priority processor

        Args:
            event_bus: Reference to event bus for publishing results
        """
        self.event_bus = event_bus

        # One queue per priority level
        self.queues: Dict[Priority, PriorityQueue] = {
            Priority.CRITICAL: PriorityQueue(),
            Priority.HIGH: PriorityQueue(),
            Priority.NORMAL: PriorityQueue(),
            Priority.LOW: PriorityQueue(),
            Priority.DEFERRED: PriorityQueue()
        }

        # Worker configuration
        self.worker_counts = {
            Priority.CRITICAL: 4,
            Priority.HIGH: 8,
            Priority.NORMAL: 16,
            Priority.LOW: 4,
            Priority.DEFERRED: 2
        }

        # Worker tasks
        self.workers: Dict[Priority, list] = {p: [] for p in Priority}

        # Statistics
        self.stats = {
            'tasks_queued': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_retried': 0
        }

        # Running state
        self.running = False

    async def start(self) -> None:
        """Start all worker pools"""
        self.running = True

        # Start workers for each priority level
        for priority, count in self.worker_counts.items():
            for i in range(count):
                worker = asyncio.create_task(
                    self._worker(priority, i)
                )
                self.workers[priority].append(worker)

        print(f"✓ Priority processor started with {sum(self.worker_counts.values())} workers")

    async def stop(self) -> None:
        """Stop all workers gracefully"""
        self.running = False

        # Wait for all workers to finish
        for priority_workers in self.workers.values():
            for worker in priority_workers:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass

    async def enqueue(self, item: QueueItem) -> None:
        """
        Enqueue a task for processing

        Args:
            item: Queue item with event and metadata
        """
        await self.queues[item.priority].put(item)
        self.stats['tasks_queued'] += 1

    async def _worker(self, priority: Priority, worker_id: int) -> None:
        """
        Worker coroutine that processes tasks from its queue

        Args:
            priority: Priority level this worker handles
            worker_id: Unique ID for this worker
        """
        queue = self.queues[priority]

        while self.running:
            try:
                # Get next item (blocks until available)
                item: QueueItem = await queue.get()

                # Process the task
                await self._process_item(item, priority, worker_id)

                queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠ Worker {priority.name}-{worker_id} error: {e}")

    async def _process_item(self, item: QueueItem, priority: Priority, worker_id: int) -> None:
        """
        Process a single queue item

        Args:
            item: Item to process
            priority: Priority level
            worker_id: Worker processing this item
        """
        start_time = time.time()

        try:
            # Call the handler
            if item.handler:
                if asyncio.iscoroutinefunction(item.handler):
                    await item.handler(item.event)
                else:
                    item.handler(item.event)

            # Success
            self.stats['tasks_completed'] += 1

            # Publish completion event
            completion_event = Event(
                event_type="task.completed",
                source="priority_processor",
                data={
                    'original_event_id': item.event.event_id,
                    'priority': priority.name,
                    'worker_id': worker_id,
                    'processing_time_ms': (time.time() - start_time) * 1000
                },
                correlation_id=item.event.event_id
            )
            await self.event_bus.publish(completion_event, persist=False)

        except Exception as e:
            # Failure - should we retry?
            self.stats['tasks_failed'] += 1

            if item.retries < item.max_retries:
                # Retry
                item.retries += 1
                self.stats['tasks_retried'] += 1

                # Re-queue with exponential backoff
                await asyncio.sleep(2 ** item.retries)
                await self.enqueue(item)

                print(f"⚠ Task retry {item.retries}/{item.max_retries}: {item.event.event_type}")
            else:
                # Max retries exceeded
                print(f"❌ Task failed after {item.max_retries} retries: {item.event.event_type}: {e}")

                # Publish failure event
                failure_event = Event(
                    event_type="task.failed",
                    source="priority_processor",
                    data={
                        'original_event_id': item.event.event_id,
                        'priority': priority.name,
                        'error': str(e),
                        'retries': item.retries
                    },
                    correlation_id=item.event.event_id
                )
                await self.event_bus.publish(failure_event, persist=True)

    def get_statistics(self) -> Dict[str, any]:
        """Get processor statistics"""
        queue_depths = {
            priority.name: queue.qsize()
            for priority, queue in self.queues.items()
        }

        return {
            **self.stats,
            'queue_depths': queue_depths,
            'total_queued': sum(queue_depths.values()),
            'worker_counts': {p.name: c for p, c in self.worker_counts.items()}
        }
