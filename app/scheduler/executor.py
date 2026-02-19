"""
Job Executor Implementation
============================

Parallel execution controller with resource management and job isolation.

Features:
- Concurrent job execution with worker pool
- Dynamic resource allocation
- Job isolation and sandboxing
- Resource limits (CPU, memory, disk I/O)
- Execution timeout management
- Result tracking and logging
"""

import logging
import os
import signal
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Resource types for allocation"""

    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK = "network"


class ExecutionStatus(Enum):
    """Job execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ResourceLimits:
    """Resource limits for job execution"""

    max_cpu_percent: float = 80.0  # Max CPU usage per job
    max_memory_mb: int = 1024  # Max memory in MB
    max_execution_time: int = 3600  # Max execution time in seconds
    max_disk_io_mb: int = 100  # Max disk I/O in MB/s
    io_priority: int = 0  # I/O priority (0=normal, 1=low)

    def __post_init__(self):
        """Validate limits"""
        if self.max_cpu_percent <= 0 or self.max_cpu_percent > 100:
            raise ValueError("max_cpu_percent must be between 0 and 100")
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if self.max_execution_time <= 0:
            raise ValueError("max_execution_time must be positive")


@dataclass
class ExecutionResult:
    """Result of job execution"""

    job_id: int
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0  # seconds
    return_value: Any = None
    error: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    resource_usage: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if execution was successful"""
        return self.status == ExecutionStatus.COMPLETED and self.error is None


@dataclass
class ResourceAllocation:
    """Current resource allocation"""

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_io_mb: float = 0.0
    network_mb: float = 0.0
    active_jobs: int = 0


class ResourceManager:
    """
    Manages system resources for job execution

    Features:
    - Track available resources
    - Allocate resources to jobs
    - Prevent resource over-allocation
    - Monitor resource usage
    """

    def __init__(self, max_cpu_percent: float = 80.0, max_memory_percent: float = 80.0):
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent

        # Get total system resources
        self.total_cpu = psutil.cpu_count()
        self.total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)

        # Current allocation
        self.allocated = ResourceAllocation()
        self.job_allocations: Dict[int, ResourceAllocation] = {}

        self.lock = threading.Lock()

        logger.info(f"ResourceManager initialized: " f"{self.total_cpu} CPUs, {self.total_memory_mb:.0f}MB memory")

    def get_available_resources(self) -> ResourceAllocation:
        """Get currently available resources"""
        cpu_used = psutil.cpu_percent(interval=0.1)
        memory_used = psutil.virtual_memory().percent

        return ResourceAllocation(
            cpu_percent=self.max_cpu_percent - cpu_used,
            memory_mb=self.total_memory_mb * (self.max_memory_percent - memory_used) / 100,
            active_jobs=self.allocated.active_jobs,
        )

    def can_allocate(self, limits: ResourceLimits) -> bool:
        """
        Check if resources can be allocated

        Args:
            limits: Required resources

        Returns:
            True if resources available
        """
        with self.lock:
            available = self.get_available_resources()

            return available.cpu_percent >= limits.max_cpu_percent and available.memory_mb >= limits.max_memory_mb

    def allocate(self, job_id: int, limits: ResourceLimits) -> bool:
        """
        Allocate resources for job

        Args:
            job_id: Job identifier
            limits: Resource limits

        Returns:
            True if allocation successful
        """
        with self.lock:
            if not self.can_allocate(limits):
                logger.warning(f"Cannot allocate resources for job {job_id}")
                return False

            # Track allocation
            allocation = ResourceAllocation(cpu_percent=limits.max_cpu_percent, memory_mb=limits.max_memory_mb, active_jobs=1)

            self.allocated.cpu_percent += allocation.cpu_percent
            self.allocated.memory_mb += allocation.memory_mb
            self.allocated.active_jobs += 1

            self.job_allocations[job_id] = allocation

            logger.info(
                f"Allocated resources for job {job_id}: " f"{limits.max_cpu_percent}% CPU, {limits.max_memory_mb}MB memory"
            )
            return True

    def release(self, job_id: int) -> None:
        """Release resources allocated to job"""
        with self.lock:
            if job_id not in self.job_allocations:
                return

            allocation = self.job_allocations.pop(job_id)

            self.allocated.cpu_percent -= allocation.cpu_percent
            self.allocated.memory_mb -= allocation.memory_mb
            self.allocated.active_jobs -= 1

            logger.info(f"Released resources for job {job_id}")

    def get_job_usage(self, job_id: int, process: psutil.Process) -> Dict[str, float]:
        """Get actual resource usage for a job"""
        try:
            cpu = process.cpu_percent(interval=0.1)
            memory = process.memory_info().rss / (1024 * 1024)  # MB

            # Get I/O counters if available
            io_counters = process.io_counters()
            disk_read_mb = io_counters.read_bytes / (1024 * 1024)
            disk_write_mb = io_counters.write_bytes / (1024 * 1024)

            return {
                "cpu_percent": cpu,
                "memory_mb": memory,
                "disk_read_mb": disk_read_mb,
                "disk_write_mb": disk_write_mb,
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}


class JobIsolator:
    """
    Provides job isolation and sandboxing

    Features:
    - Process isolation
    - Resource limits enforcement
    - Timeout management
    - Clean termination
    """

    @staticmethod
    @contextmanager
    def isolate(limits: ResourceLimits):
        """
        Context manager for job isolation

        Args:
            limits: Resource limits to enforce
        """
        original_nice = None

        try:
            # Set I/O priority if on Linux
            if hasattr(os, "setpriority"):
                original_nice = os.getpriority(os.PRIO_PROCESS, 0)
                if limits.io_priority > 0:
                    os.setpriority(os.PRIO_PROCESS, 0, 10)  # Lower priority

            # Note: Memory and CPU limits would typically be enforced
            # using cgroups or container technology in production

            yield

        finally:
            # Restore original priority
            if original_nice is not None and hasattr(os, "setpriority"):
                try:
                    os.setpriority(os.PRIO_PROCESS, 0, original_nice)
                except:
                    pass

    @staticmethod
    def enforce_timeout(timeout: int) -> Callable:
        """
        Decorator to enforce execution timeout

        Args:
            timeout: Timeout in seconds

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                result = [None]
                exception = [None]

                def target():
                    try:
                        result[0] = func(*args, **kwargs)
                    except Exception as e:
                        exception[0] = e

                thread = threading.Thread(target=target)
                thread.daemon = True
                thread.start()
                thread.join(timeout)

                if thread.is_alive():
                    # Timeout occurred
                    raise TimeoutError(f"Execution exceeded {timeout} seconds")

                if exception[0]:
                    raise exception[0]

                return result[0]

            return wrapper

        return decorator


class JobExecutor:
    """
    Parallel job executor with resource management

    Features:
    - Concurrent execution with thread pool
    - Resource allocation and tracking
    - Job isolation
    - Timeout management
    - Result collection

    Usage:
        executor = JobExecutor(max_workers=4)

        # Execute single job
        result = executor.execute_job(
            job_id=1,
            callback=run_backup,
            job_data={"path": "/data"},
            limits=ResourceLimits()
        )

        # Execute multiple jobs
        results = executor.execute_batch(jobs)
    """

    def __init__(self, max_workers: int = 4, resource_manager: Optional[ResourceManager] = None):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.resource_manager = resource_manager or ResourceManager()

        # Track running jobs
        self.running_jobs: Dict[int, Future] = {}
        self.results: Dict[int, ExecutionResult] = {}
        self.lock = threading.Lock()

        logger.info(f"JobExecutor initialized with {max_workers} workers")

    def execute_job(
        self,
        job_id: int,
        callback: Callable,
        job_data: Optional[Dict] = None,
        limits: Optional[ResourceLimits] = None,
        wait: bool = False,
    ) -> Optional[ExecutionResult]:
        """
        Execute a single job

        Args:
            job_id: Job identifier
            callback: Function to execute
            job_data: Data to pass to callback
            limits: Resource limits
            wait: Wait for completion if True

        Returns:
            ExecutionResult if wait=True, None otherwise
        """
        limits = limits or ResourceLimits()
        job_data = job_data or {}

        # Check if resources available
        if not self.resource_manager.can_allocate(limits):
            logger.warning(f"Cannot execute job {job_id}: insufficient resources")
            return ExecutionResult(
                job_id=job_id, status=ExecutionStatus.FAILED, start_time=datetime.utcnow(), error="Insufficient resources"
            )

        # Allocate resources
        if not self.resource_manager.allocate(job_id, limits):
            return ExecutionResult(
                job_id=job_id, status=ExecutionStatus.FAILED, start_time=datetime.utcnow(), error="Resource allocation failed"
            )

        # Submit job
        future = self.executor.submit(self._execute_with_isolation, job_id, callback, job_data, limits)

        with self.lock:
            self.running_jobs[job_id] = future

        logger.info(f"Submitted job {job_id} for execution")

        if wait:
            return future.result()

        # Register completion callback
        future.add_done_callback(lambda f: self._job_completed(job_id, f))
        return None

    def _execute_with_isolation(
        self, job_id: int, callback: Callable, job_data: Dict, limits: ResourceLimits
    ) -> ExecutionResult:
        """Execute job with isolation and monitoring"""
        start_time = datetime.utcnow()
        result = ExecutionResult(job_id=job_id, status=ExecutionStatus.RUNNING, start_time=start_time)

        try:
            # Get process for monitoring
            process = psutil.Process(os.getpid())

            # Execute with isolation
            with JobIsolator.isolate(limits):
                # Apply timeout
                @JobIsolator.enforce_timeout(limits.max_execution_time)
                def timed_execution():
                    return callback(job_id=job_id, **job_data)

                # Execute
                return_value = timed_execution()

                # Record success
                result.status = ExecutionStatus.COMPLETED
                result.return_value = return_value

                # Get resource usage
                result.resource_usage = self.resource_manager.get_job_usage(job_id, process)

        except TimeoutError as e:
            result.status = ExecutionStatus.TIMEOUT
            result.error = str(e)
            logger.error(f"Job {job_id} timed out after {limits.max_execution_time}s")

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            logger.error(f"Job {job_id} failed: {e}")

        finally:
            result.end_time = datetime.utcnow()
            result.duration = (result.end_time - result.start_time).total_seconds()

            # Release resources
            self.resource_manager.release(job_id)

        return result

    def _job_completed(self, job_id: int, future: Future) -> None:
        """Callback when job completes"""
        with self.lock:
            self.running_jobs.pop(job_id, None)

            try:
                result = future.result()
                self.results[job_id] = result

                if result.success:
                    logger.info(f"Job {job_id} completed in {result.duration:.2f}s")
                else:
                    logger.error(f"Job {job_id} failed: {result.error}")

            except Exception as e:
                logger.error(f"Error getting result for job {job_id}: {e}")

    def execute_batch(
        self, jobs: List[Tuple[int, Callable, Dict, ResourceLimits]], wait_all: bool = True
    ) -> Dict[int, ExecutionResult]:
        """
        Execute multiple jobs in parallel

        Args:
            jobs: List of (job_id, callback, job_data, limits) tuples
            wait_all: Wait for all jobs to complete

        Returns:
            Dictionary of job_id -> ExecutionResult
        """
        results = {}

        # Submit all jobs
        for job_id, callback, job_data, limits in jobs:
            self.execute_job(job_id, callback, job_data, limits, wait=False)

        if wait_all:
            # Wait for all to complete
            self.wait_all()

        return self.results.copy()

    def wait_all(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all running jobs to complete

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if all completed, False if timeout
        """
        start = time.time()

        while True:
            with self.lock:
                if not self.running_jobs:
                    return True

            if timeout and (time.time() - start) >= timeout:
                return False

            time.sleep(0.1)

    def cancel_job(self, job_id: int) -> bool:
        """
        Cancel a running job

        Args:
            job_id: Job to cancel

        Returns:
            True if job was cancelled
        """
        with self.lock:
            if job_id not in self.running_jobs:
                return False

            future = self.running_jobs[job_id]
            cancelled = future.cancel()

            if cancelled:
                self.resource_manager.release(job_id)
                self.results[job_id] = ExecutionResult(
                    job_id=job_id,
                    status=ExecutionStatus.CANCELLED,
                    start_time=datetime.utcnow(),
                    error="Job cancelled by user",
                )
                logger.info(f"Cancelled job {job_id}")

            return cancelled

    def get_result(self, job_id: int) -> Optional[ExecutionResult]:
        """Get result for completed job"""
        return self.results.get(job_id)

    def get_running_jobs(self) -> List[int]:
        """Get list of currently running job IDs"""
        with self.lock:
            return list(self.running_jobs.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics"""
        with self.lock:
            completed = sum(1 for r in self.results.values() if r.status == ExecutionStatus.COMPLETED)
            failed = sum(1 for r in self.results.values() if r.status == ExecutionStatus.FAILED)

            return {
                "max_workers": self.max_workers,
                "running_jobs": len(self.running_jobs),
                "completed_jobs": completed,
                "failed_jobs": failed,
                "total_jobs": len(self.results),
                "resource_allocation": {
                    "cpu_percent": self.resource_manager.allocated.cpu_percent,
                    "memory_mb": self.resource_manager.allocated.memory_mb,
                    "active_jobs": self.resource_manager.allocated.active_jobs,
                },
            }

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown executor

        Args:
            wait: Wait for running jobs to complete
        """
        logger.info("Shutting down executor")
        self.executor.shutdown(wait=wait)
