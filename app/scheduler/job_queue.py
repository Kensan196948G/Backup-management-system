"""
Job Queue Implementation
========================

Priority queue system for backup jobs with dependency management,
retry logic, and exponential backoff.

Features:
- Priority-based job ordering
- Job dependency tracking and resolution
- Job chaining for sequential operations
- Retry failed jobs with exponential backoff
- Dead letter queue for permanently failed jobs
- Queue statistics and monitoring
"""

import heapq
import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class JobPriority(IntEnum):
    """Job priority levels (lower number = higher priority)"""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class JobStatus(IntEnum):
    """Job status enumeration"""

    PENDING = 1
    READY = 2
    RUNNING = 3
    COMPLETED = 4
    FAILED = 5
    BLOCKED = 6  # Waiting for dependencies
    RETRYING = 7
    DEAD = 8  # Permanently failed


@dataclass(order=True)
class QueuedJob:
    """
    Job in the priority queue

    Ordered by priority, then by scheduled time, then by job_id
    """

    priority: int
    scheduled_time: datetime = field(compare=True)
    job_id: int = field(compare=False)
    job_data: Dict[str, Any] = field(default_factory=dict, compare=False)
    dependencies: Set[int] = field(default_factory=set, compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    created_at: datetime = field(default_factory=datetime.utcnow, compare=False)
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self):
        # Ensure priority is int for comparison
        self.priority = int(self.priority)


@dataclass
class RetryConfig:
    """Retry configuration with exponential backoff"""

    max_retries: int = 3
    base_delay: int = 60  # seconds
    max_delay: int = 3600  # seconds
    backoff_multiplier: float = 2.0

    def calculate_delay(self, attempt: int) -> int:
        """Calculate delay for given retry attempt"""
        delay = self.base_delay * (self.backoff_multiplier**attempt)
        return min(int(delay), self.max_delay)


class JobDependencyManager:
    """
    Manages job dependencies and chains

    Features:
    - Dependency graph management
    - Circular dependency detection
    - Dependency resolution
    - Job chaining for sequential execution
    """

    def __init__(self):
        self.dependencies: Dict[int, Set[int]] = defaultdict(set)  # job -> dependencies
        self.dependents: Dict[int, Set[int]] = defaultdict(set)  # job -> dependents
        self.completed: Set[int] = set()
        self.lock = threading.Lock()

    def add_dependency(self, job_id: int, depends_on: int) -> None:
        """
        Add dependency: job_id depends on depends_on

        Args:
            job_id: Job that has the dependency
            depends_on: Job that must complete first

        Raises:
            ValueError: If circular dependency detected
        """
        with self.lock:
            # Check for circular dependency
            if self._would_create_cycle(job_id, depends_on):
                raise ValueError(f"Circular dependency detected: {job_id} -> {depends_on}")

            self.dependencies[job_id].add(depends_on)
            self.dependents[depends_on].add(job_id)
            logger.debug(f"Added dependency: job {job_id} depends on {depends_on}")

    def add_dependencies(self, job_id: int, depends_on: List[int]) -> None:
        """Add multiple dependencies"""
        for dep in depends_on:
            self.add_dependency(job_id, dep)

    def create_chain(self, job_ids: List[int]) -> None:
        """
        Create a job chain where each job depends on the previous

        Args:
            job_ids: List of job IDs in execution order
        """
        for i in range(1, len(job_ids)):
            self.add_dependency(job_ids[i], job_ids[i - 1])
        logger.info(f"Created job chain: {' -> '.join(map(str, job_ids))}")

    def _would_create_cycle(self, job_id: int, depends_on: int) -> bool:
        """Check if adding dependency would create a cycle"""
        # Use BFS to check if depends_on leads back to job_id
        visited = set()
        queue = deque([depends_on])

        while queue:
            current = queue.popleft()
            if current == job_id:
                return True

            if current in visited:
                continue
            visited.add(current)

            # Add all dependencies of current
            queue.extend(self.dependencies.get(current, set()))

        return False

    def is_ready(self, job_id: int) -> bool:
        """
        Check if job is ready to run (all dependencies completed)

        Args:
            job_id: Job to check

        Returns:
            True if all dependencies are completed
        """
        with self.lock:
            deps = self.dependencies.get(job_id, set())
            return deps.issubset(self.completed)

    def mark_completed(self, job_id: int) -> List[int]:
        """
        Mark job as completed and return newly ready jobs

        Args:
            job_id: Completed job ID

        Returns:
            List of job IDs that became ready
        """
        with self.lock:
            self.completed.add(job_id)
            newly_ready = []

            # Check all dependents
            for dependent in self.dependents.get(job_id, set()):
                if self.is_ready(dependent):
                    newly_ready.append(dependent)

            logger.info(f"Job {job_id} completed. Newly ready: {newly_ready}")
            return newly_ready

    def get_dependencies(self, job_id: int) -> Set[int]:
        """Get all dependencies for a job"""
        return self.dependencies.get(job_id, set()).copy()

    def get_dependents(self, job_id: int) -> Set[int]:
        """Get all jobs that depend on this job"""
        return self.dependents.get(job_id, set()).copy()

    def remove_job(self, job_id: int) -> None:
        """Remove job from dependency graph"""
        with self.lock:
            # Remove from dependencies of dependents
            for dependent in self.dependents.get(job_id, set()):
                self.dependencies[dependent].discard(job_id)

            # Remove from dependents of dependencies
            for dependency in self.dependencies.get(job_id, set()):
                self.dependents[dependency].discard(job_id)

            # Clean up
            self.dependencies.pop(job_id, None)
            self.dependents.pop(job_id, None)
            self.completed.discard(job_id)


class JobQueue:
    """
    Priority queue for backup jobs

    Features:
    - Priority-based ordering
    - Dependency management
    - Retry with exponential backoff
    - Dead letter queue for failed jobs
    - Queue statistics

    Usage:
        queue = JobQueue()

        # Add job with priority
        queue.add_job(job_id=1, priority=JobPriority.HIGH, job_data={...})

        # Add dependencies
        queue.add_dependency(job_id=2, depends_on=[1])

        # Get next ready job
        job = queue.get_next_job()

        # Mark as completed or failed
        queue.mark_completed(job.job_id)
        queue.mark_failed(job.job_id, error="...")
    """

    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.queue: List[QueuedJob] = []
        self.jobs: Dict[int, QueuedJob] = {}  # job_id -> QueuedJob
        self.status: Dict[int, JobStatus] = {}  # job_id -> status
        self.dependency_manager = JobDependencyManager()
        self.retry_config = retry_config or RetryConfig()
        self.dead_letter_queue: List[Tuple[QueuedJob, str]] = []  # Failed jobs with reason
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            "total_added": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retries": 0,
            "total_dead": 0,
        }

    def add_job(
        self,
        job_id: int,
        priority: JobPriority = JobPriority.NORMAL,
        job_data: Optional[Dict] = None,
        dependencies: Optional[List[int]] = None,
        scheduled_time: Optional[datetime] = None,
        **kwargs,
    ) -> None:
        """
        Add job to queue

        Args:
            job_id: Unique job identifier
            priority: Job priority level
            job_data: Job data/configuration
            dependencies: List of job IDs this job depends on
            scheduled_time: When to run (default: now)
            **kwargs: Additional job metadata
        """
        with self.lock:
            if job_id in self.jobs:
                logger.warning(f"Job {job_id} already in queue, skipping")
                return

            deps = set(dependencies) if dependencies else set()

            job = QueuedJob(
                priority=int(priority),
                scheduled_time=scheduled_time or datetime.utcnow(),
                job_id=job_id,
                job_data=job_data or {},
                dependencies=deps,
                max_retries=kwargs.get("max_retries", self.retry_config.max_retries),
                metadata=kwargs,
            )

            # Add to dependency manager
            if deps:
                self.dependency_manager.add_dependencies(job_id, list(deps))

            # Add to queue
            self.jobs[job_id] = job
            self.status[job_id] = JobStatus.BLOCKED if deps else JobStatus.PENDING

            if not deps:
                heapq.heappush(self.queue, job)

            self.stats["total_added"] += 1
            logger.info(f"Added job {job_id} with priority {priority} and {len(deps)} dependencies")

    def add_dependency(self, job_id: int, depends_on: List[int]) -> None:
        """Add dependencies to existing job"""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not in queue")

        self.dependency_manager.add_dependencies(job_id, depends_on)
        self.jobs[job_id].dependencies.update(depends_on)

        # Update status if now blocked
        if not self.dependency_manager.is_ready(job_id):
            with self.lock:
                self.status[job_id] = JobStatus.BLOCKED

    def create_chain(self, job_ids: List[int]) -> None:
        """Create sequential job chain"""
        self.dependency_manager.create_chain(job_ids)

        # Update job dependencies
        for i in range(1, len(job_ids)):
            if job_ids[i] in self.jobs:
                self.jobs[job_ids[i]].dependencies.add(job_ids[i - 1])

    def get_next_job(self, current_time: Optional[datetime] = None) -> Optional[QueuedJob]:
        """
        Get next ready job from queue

        Args:
            current_time: Current time for scheduling check

        Returns:
            Next job to execute or None if queue empty
        """
        now = current_time or datetime.utcnow()

        with self.lock:
            # Remove and check jobs until we find a ready one
            while self.queue:
                job = heapq.heappop(self.queue)

                # Check if scheduled time reached
                if job.scheduled_time > now:
                    # Put back and wait
                    heapq.heappush(self.queue, job)
                    return None

                # Check dependencies
                if not self.dependency_manager.is_ready(job.job_id):
                    # Still blocked, check status
                    self.status[job.job_id] = JobStatus.BLOCKED
                    continue

                # Job is ready
                self.status[job.job_id] = JobStatus.RUNNING
                logger.info(f"Dequeued job {job.job_id} for execution")
                return job

            return None

    def mark_completed(self, job_id: int) -> None:
        """
        Mark job as successfully completed

        Args:
            job_id: Job identifier
        """
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} not found in queue")
                return

            self.status[job_id] = JobStatus.COMPLETED
            self.stats["total_completed"] += 1

            # Check for newly ready dependents
            newly_ready = self.dependency_manager.mark_completed(job_id)

            # Add newly ready jobs to queue
            for ready_job_id in newly_ready:
                if ready_job_id in self.jobs:
                    job = self.jobs[ready_job_id]
                    self.status[ready_job_id] = JobStatus.READY
                    heapq.heappush(self.queue, job)

            logger.info(f"Job {job_id} marked as completed. Released {len(newly_ready)} dependents.")

    def mark_failed(self, job_id: int, error: str = "") -> bool:
        """
        Mark job as failed and handle retry logic

        Args:
            job_id: Job identifier
            error: Error message

        Returns:
            True if job will be retried, False if moved to dead letter queue
        """
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} not found in queue")
                return False

            job = self.jobs[job_id]
            job.retry_count += 1
            self.stats["total_failed"] += 1

            # Check if should retry
            if job.retry_count <= job.max_retries:
                # Calculate retry delay
                delay = self.retry_config.calculate_delay(job.retry_count)
                retry_time = datetime.utcnow() + timedelta(seconds=delay)

                # Update job
                job.scheduled_time = retry_time
                self.status[job_id] = JobStatus.RETRYING

                # Re-add to queue
                heapq.heappush(self.queue, job)

                self.stats["total_retries"] += 1
                logger.warning(
                    f"Job {job_id} failed (attempt {job.retry_count}/{job.max_retries}). "
                    f"Retrying in {delay}s. Error: {error}"
                )
                return True
            else:
                # Max retries exceeded, move to dead letter queue
                self.status[job_id] = JobStatus.DEAD
                self.dead_letter_queue.append((job, error))
                self.stats["total_dead"] += 1

                logger.error(f"Job {job_id} permanently failed after {job.retry_count} attempts. " f"Error: {error}")
                return False

    def get_status(self, job_id: int) -> Optional[JobStatus]:
        """Get job status"""
        return self.status.get(job_id)

    def get_queue_size(self) -> int:
        """Get number of jobs in queue"""
        return len(self.queue)

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        with self.lock:
            return {
                **self.stats,
                "queue_size": len(self.queue),
                "dead_letter_size": len(self.dead_letter_queue),
                "pending": sum(1 for s in self.status.values() if s == JobStatus.PENDING),
                "running": sum(1 for s in self.status.values() if s == JobStatus.RUNNING),
                "blocked": sum(1 for s in self.status.values() if s == JobStatus.BLOCKED),
            }

    def get_dead_letter_queue(self) -> List[Tuple[QueuedJob, str]]:
        """Get all permanently failed jobs"""
        return self.dead_letter_queue.copy()

    def retry_dead_job(self, job_id: int) -> bool:
        """
        Manually retry a job from dead letter queue

        Args:
            job_id: Job to retry

        Returns:
            True if job was found and re-queued
        """
        with self.lock:
            # Find in dead letter queue
            for i, (job, _) in enumerate(self.dead_letter_queue):
                if job.job_id == job_id:
                    # Reset and re-queue
                    job.retry_count = 0
                    job.scheduled_time = datetime.utcnow()
                    self.status[job_id] = JobStatus.PENDING
                    heapq.heappush(self.queue, job)

                    # Remove from dead letter queue
                    self.dead_letter_queue.pop(i)
                    self.stats["total_dead"] -= 1

                    logger.info(f"Manually retrying dead job {job_id}")
                    return True

            return False

    def clear_queue(self) -> None:
        """Clear all jobs from queue (use with caution)"""
        with self.lock:
            self.queue.clear()
            self.jobs.clear()
            self.status.clear()
            self.dependency_manager = JobDependencyManager()
            logger.warning("Queue cleared")

    def remove_job(self, job_id: int) -> bool:
        """
        Remove job from queue

        Args:
            job_id: Job to remove

        Returns:
            True if job was removed
        """
        with self.lock:
            if job_id not in self.jobs:
                return False

            # Remove from all structures
            self.jobs.pop(job_id, None)
            self.status.pop(job_id, None)
            self.dependency_manager.remove_job(job_id)

            # Rebuild heap without this job
            self.queue = [job for job in self.queue if job.job_id != job_id]
            heapq.heapify(self.queue)

            logger.info(f"Removed job {job_id} from queue")
            return True
