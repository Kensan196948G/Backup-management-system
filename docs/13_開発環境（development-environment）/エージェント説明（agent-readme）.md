# Agent-04: Scheduler & Job Manager

## Overview

Agent-04 implements a comprehensive job scheduling and management system for the Backup Management System. This includes cron-like scheduling, priority queues, parallel execution, and resource management.

## Implementation Status

### ✅ Completed Components

#### 1. **app/scheduler/__init__.py**
Module initialization exporting all major components:
- `BackupScheduler`: Main scheduling orchestrator
- `CronScheduler`: Cron expression parser and scheduler
- `CalendarScheduler`: Calendar-based scheduling
- `JobQueue`: Priority queue with dependency management
- `JobPriority`: Priority level enumeration
- `JobDependencyManager`: Dependency graph management
- `JobExecutor`: Parallel execution controller
- `ResourceManager`: System resource management
- `JobIsolator`: Job isolation utilities

#### 2. **app/scheduler/scheduler.py**
Advanced scheduling system with:
- **Cron Expression Parsing**: Full support for 5-field cron expressions
  - Wildcards (*), ranges (n-m), lists (n,m), steps (*/n)
  - Examples: "0 2 * * *" (daily at 2 AM), "0 */6 * * *" (every 6 hours)
- **Calendar-Based Scheduling**: Business days, month-end, quarter-end
- **Event-Driven Triggers**: File changes, system events, webhooks
- **Next Run Calculation**: Timezone-aware next execution time
- **Schedule Validation**: Detect conflicts and invalid expressions

**Classes:**
- `CronScheduler`: Cron expression scheduling
- `CalendarScheduler`: Business day/holiday scheduling
- `BackupScheduler`: Unified scheduler combining all types
- `ScheduleConfig`: Schedule configuration dataclass
- `CronExpression`: Parsed cron expression
- `ScheduleType`: Schedule type enumeration
- `EventType`: Event trigger types

#### 3. **app/scheduler/job_queue.py**
Priority queue system with:
- **Priority Queue**: Heap-based priority ordering
- **Dependency Management**: Directed acyclic graph (DAG) for dependencies
- **Job Chaining**: Sequential job execution
- **Retry Logic**: Exponential backoff for failed jobs
- **Dead Letter Queue**: Permanently failed jobs tracking
- **Queue Statistics**: Comprehensive metrics

**Classes:**
- `JobQueue`: Main priority queue implementation
- `JobPriority`: Priority levels (CRITICAL, HIGH, NORMAL, LOW, BACKGROUND)
- `JobDependencyManager`: Dependency graph with cycle detection
- `QueuedJob`: Job data structure
- `RetryConfig`: Retry configuration with backoff
- `JobStatus`: Job status enumeration

**Key Features:**
- Thread-safe operations with locks
- Circular dependency detection
- Automatic dependent job triggering
- Configurable retry strategies
- Manual retry from dead letter queue

#### 4. **app/scheduler/executor.py**
Parallel execution controller with:
- **Thread Pool Execution**: Concurrent job execution
- **Resource Management**: CPU, memory, disk I/O tracking
- **Job Isolation**: Process isolation and sandboxing
- **Timeout Enforcement**: Automatic timeout handling
- **Resource Limits**: Per-job resource constraints

**Classes:**
- `JobExecutor`: Main execution controller
- `ResourceManager`: System resource allocation
- `JobIsolator`: Job isolation utilities
- `ExecutionResult`: Execution result tracking
- `ResourceLimits`: Resource limit configuration
- `ResourceAllocation`: Current resource usage

**Key Features:**
- Dynamic resource allocation
- Resource availability checking
- Execution monitoring with psutil
- Batch job execution
- Job cancellation support

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BackupScheduler                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │CronScheduler │  │  Calendar    │  │Event Handlers│     │
│  │              │  │  Scheduler   │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                       JobQueue                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Priority Heap (min-heap)                     │  │
│  │  Priority → Scheduled Time → Job ID                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         JobDependencyManager                          │  │
│  │  Dependency DAG with cycle detection                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                      JobExecutor                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         ThreadPoolExecutor                            │  │
│  │  Worker 1 │ Worker 2 │ Worker 3 │ Worker 4          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         ResourceManager                               │  │
│  │  CPU | Memory | Disk I/O | Network                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Usage Examples

### 1. Cron Scheduling

```python
from app.scheduler import BackupScheduler, JobExecutor, JobQueue

# Initialize components
scheduler = BackupScheduler()
queue = JobQueue()
executor = JobExecutor(max_workers=4)

# Define job callback
def run_backup(job_id, **kwargs):
    print(f"Running backup job {job_id}")
    # Backup logic here
    return {"status": "success"}

# Schedule daily backup at 2 AM
scheduler.schedule_cron(
    job_id=1,
    cron_expression="0 2 * * *",
    callback=run_backup,
    timezone="Asia/Tokyo"
)

# Schedule every 6 hours
scheduler.schedule_cron(
    job_id=2,
    cron_expression="0 */6 * * *",
    callback=run_backup
)

# Schedule first Monday of month at 3:30 AM
scheduler.schedule_cron(
    job_id=3,
    cron_expression="30 3 1-7 * 1",
    callback=run_backup
)
```

### 2. Priority Queue with Dependencies

```python
from app.scheduler import JobQueue, JobPriority

queue = JobQueue()

# Add high-priority job
queue.add_job(
    job_id=1,
    priority=JobPriority.HIGH,
    job_data={"path": "/data/critical"}
)

# Add job with dependencies
queue.add_job(
    job_id=2,
    priority=JobPriority.NORMAL,
    job_data={"path": "/data/app"},
    dependencies=[1]  # Depends on job 1
)

# Create job chain (sequential execution)
queue.create_chain([1, 2, 3, 4])

# Get next ready job
job = queue.get_next_job()
if job:
    print(f"Executing job {job.job_id}")
    # Execute job...
    
    # Mark as completed
    queue.mark_completed(job.job_id)
```

### 3. Parallel Execution with Resource Limits

```python
from app.scheduler import JobExecutor, ResourceLimits

executor = JobExecutor(max_workers=4)

# Define resource limits
limits = ResourceLimits(
    max_cpu_percent=50.0,
    max_memory_mb=512,
    max_execution_time=1800,  # 30 minutes
    io_priority=0
)

# Execute job with limits
result = executor.execute_job(
    job_id=1,
    callback=run_backup,
    job_data={"path": "/data"},
    limits=limits,
    wait=True
)

if result.success:
    print(f"Job completed in {result.duration:.2f}s")
    print(f"CPU usage: {result.resource_usage['cpu_percent']}%")
else:
    print(f"Job failed: {result.error}")
```

### 4. Calendar-Based Scheduling

```python
# Schedule on business days at 6 PM
scheduler.schedule_business_days(
    job_id=4,
    time="18:00",
    callback=run_daily_report,
    timezone="Asia/Tokyo"
)

# Schedule on month end
scheduler.schedule_month_end(
    job_id=5,
    time="23:00",
    callback=run_monthly_report
)

# Add holidays
from datetime import datetime
holidays = [
    datetime(2025, 1, 1),  # New Year
    datetime(2025, 12, 25),  # Christmas
]
scheduler.calendar_scheduler.add_holidays(holidays)
```

### 5. Event-Driven Triggers

```python
from app.scheduler import EventType

# Schedule on file change event
scheduler.schedule_event(
    job_id=6,
    event_type=EventType.FILE_CHANGE,
    callback=run_verification
)

# Trigger event manually
triggered = scheduler.trigger_event(
    EventType.FILE_CHANGE,
    file_path="/data/backup.tar",
    change_type="modified"
)
```

### 6. Complete Integration Example

```python
from app.scheduler import (
    BackupScheduler, JobQueue, JobExecutor,
    JobPriority, ResourceLimits
)
from datetime import datetime

# Initialize
scheduler = BackupScheduler()
queue = JobQueue()
executor = JobExecutor(max_workers=4)

# Define backup function
def run_backup(job_id, path, backup_type):
    print(f"Running {backup_type} backup: {path}")
    # Actual backup logic
    return {"status": "success", "size": 1024}

# Schedule critical daily backup
scheduler.schedule_cron(
    job_id=1,
    cron_expression="0 2 * * *",
    callback=lambda **kw: queue.add_job(
        job_id=1,
        priority=JobPriority.CRITICAL,
        job_data={"path": "/data/critical", "backup_type": "full"}
    )
)

# Schedule weekly backup chain
queue.create_chain([10, 11, 12])  # Sequential execution

# Execute pending jobs
pending = scheduler.get_pending_jobs()
for job_id in pending:
    job = queue.get_next_job()
    if job:
        limits = ResourceLimits(
            max_cpu_percent=60.0,
            max_memory_mb=1024
        )
        
        executor.execute_job(
            job_id=job.job_id,
            callback=run_backup,
            job_data=job.job_data,
            limits=limits
        )

# Monitor execution
stats = executor.get_stats()
print(f"Running: {stats['running_jobs']}")
print(f"Completed: {stats['completed_jobs']}")
```

## API Reference

### BackupScheduler

```python
scheduler = BackupScheduler()

# Cron scheduling
scheduler.schedule_cron(job_id, cron_expression, callback, **kwargs)

# Calendar scheduling
scheduler.schedule_business_days(job_id, time, callback, **kwargs)
scheduler.schedule_month_end(job_id, time, callback, **kwargs)

# Event scheduling
scheduler.schedule_event(job_id, event_type, callback)
scheduler.trigger_event(event_type, **event_data)

# Management
scheduler.get_pending_jobs(check_time=None) -> List[int]
scheduler.calculate_next_run(job_id, from_time=None) -> datetime
scheduler.remove_schedule(job_id)
scheduler.enable()
scheduler.disable()
```

### JobQueue

```python
queue = JobQueue(retry_config=None)

# Add jobs
queue.add_job(job_id, priority, job_data, dependencies, **kwargs)
queue.add_dependency(job_id, depends_on)
queue.create_chain(job_ids)

# Get jobs
queue.get_next_job(current_time=None) -> QueuedJob

# Update status
queue.mark_completed(job_id)
queue.mark_failed(job_id, error) -> bool

# Statistics
queue.get_status(job_id) -> JobStatus
queue.get_stats() -> Dict
queue.get_queue_size() -> int
queue.get_dead_letter_queue() -> List

# Management
queue.retry_dead_job(job_id) -> bool
queue.remove_job(job_id) -> bool
queue.clear_queue()
```

### JobExecutor

```python
executor = JobExecutor(max_workers=4, resource_manager=None)

# Execute jobs
executor.execute_job(job_id, callback, job_data, limits, wait) -> ExecutionResult
executor.execute_batch(jobs, wait_all) -> Dict[int, ExecutionResult]

# Management
executor.wait_all(timeout=None) -> bool
executor.cancel_job(job_id) -> bool
executor.get_result(job_id) -> ExecutionResult
executor.get_running_jobs() -> List[int]
executor.get_stats() -> Dict
executor.shutdown(wait=True)
```

## Testing

```python
# Test cron parsing
from app.scheduler import CronScheduler

cron = CronScheduler()
expr = cron.parse_cron_expression("0 2 * * 1-5")
print(expr.minute)  # {0}
print(expr.hour)    # {2}
print(expr.weekday) # {0, 1, 2, 3, 4}

# Test queue operations
from app.scheduler import JobQueue, JobPriority

queue = JobQueue()
queue.add_job(1, JobPriority.HIGH)
queue.add_job(2, JobPriority.LOW)
job = queue.get_next_job()
assert job.job_id == 1  # High priority first

# Test executor
from app.scheduler import JobExecutor, ResourceLimits

def test_job(job_id):
    return "success"

executor = JobExecutor(max_workers=2)
result = executor.execute_job(1, test_job, wait=True)
assert result.success
```

## Integration with Existing System

### 1. Update app/models.py

```python
# Add scheduling fields to BackupJob
class BackupJob(db.Model):
    # ... existing fields ...
    
    # Scheduling
    cron_expression = db.Column(db.String(50))
    next_run = db.Column(db.DateTime)
    priority = db.Column(db.Integer, default=3)  # JobPriority.NORMAL
    max_retries = db.Column(db.Integer, default=3)
    
    # Dependencies
    depends_on = db.Column(db.JSON)  # List of job IDs
```

### 2. Create Scheduler Service

```python
# app/services/scheduler_service.py
from app.scheduler import BackupScheduler, JobQueue, JobExecutor
from app.models import BackupJob

class SchedulerService:
    def __init__(self):
        self.scheduler = BackupScheduler()
        self.queue = JobQueue()
        self.executor = JobExecutor(max_workers=4)
    
    def load_jobs_from_db(self):
        """Load all active jobs from database"""
        jobs = BackupJob.query.filter_by(is_active=True).all()
        for job in jobs:
            if job.cron_expression:
                self.scheduler.schedule_cron(
                    job.id,
                    job.cron_expression,
                    self.run_backup
                )
    
    def run_backup(self, job_id):
        """Execute backup job"""
        job = BackupJob.query.get(job_id)
        # Run backup logic
        pass
```

## Performance Considerations

1. **Thread Pool Size**: Default 4 workers, adjust based on system resources
2. **Resource Limits**: Set appropriate CPU/memory limits per job
3. **Queue Size**: Monitor queue size to prevent memory issues
4. **Retry Strategy**: Use exponential backoff to prevent overwhelming system
5. **Dependency Depth**: Limit dependency chain depth to prevent stack issues

## Error Handling

All components include comprehensive error handling:
- Invalid cron expressions raise `ValueError`
- Circular dependencies raise `ValueError`
- Resource allocation failures return `False`
- Execution timeouts are caught and logged
- Dead letter queue tracks permanently failed jobs

## Logging

All components log to `app.scheduler` logger:
- INFO: Job scheduling, execution, completion
- WARNING: Resource constraints, retry attempts
- ERROR: Job failures, execution errors

## Next Steps

1. **Integration**: Connect scheduler to existing backup engine
2. **API Endpoints**: Create REST endpoints for schedule management
3. **UI Components**: Add scheduling interface to web UI
4. **Testing**: Write comprehensive unit and integration tests
5. **Documentation**: Add API documentation and examples
6. **Monitoring**: Add metrics and alerting for job execution

## Maintenance

- Monitor dead letter queue for recurring failures
- Review and adjust resource limits based on usage
- Update holiday calendars annually
- Archive old job execution results
- Monitor executor statistics for performance tuning

---

**Author**: Agent-04: Scheduler & Job Manager  
**Version**: 1.0.0  
**Last Updated**: 2025-11-01
