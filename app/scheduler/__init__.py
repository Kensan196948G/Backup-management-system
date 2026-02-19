"""
Scheduler Module
================

Advanced job scheduling system with cron-like scheduling, priority queues,
and parallel execution management.

Features:
- Cron-style scheduling with calendar-based rules
- Priority queue for backup jobs
- Job dependencies and chaining
- Parallel execution with resource management
- Event-driven triggers
- Retry mechanisms with exponential backoff
- Job isolation and resource allocation

Components:
- scheduler: Main scheduling engine with cron and calendar support
- job_queue: Priority queue with dependency management
- executor: Parallel execution controller with resource limits
- tasks: Legacy APScheduler tasks (deprecated)

Usage:
    from app.scheduler import BackupScheduler, JobQueue, JobExecutor
    
    scheduler = BackupScheduler()
    queue = JobQueue()
    executor = JobExecutor(max_workers=4)
    
    # Schedule a job
    scheduler.schedule_cron(
        job_id=1,
        cron_expression="0 2 * * *",
        callback=run_backup
    )
    
    # Add to queue with priority
    queue.add_job(
        job_id=1,
        priority=1,
        dependencies=[2, 3]
    )
    
    # Execute with resource limits
    executor.execute_job(job_data)
"""

from .executor import JobExecutor, JobIsolator, ResourceManager
from .job_queue import JobDependencyManager, JobPriority, JobQueue
from .scheduler import BackupScheduler, CalendarScheduler, CronScheduler

__all__ = [
    "BackupScheduler",
    "CronScheduler",
    "CalendarScheduler",
    "JobQueue",
    "JobPriority",
    "JobDependencyManager",
    "JobExecutor",
    "ResourceManager",
    "JobIsolator",
]

__version__ = "1.0.0"
__author__ = "Agent-04: Scheduler & Job Manager"
