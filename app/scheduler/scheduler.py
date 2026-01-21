"""
Job Scheduler Implementation
=============================

Advanced scheduling system with cron-like expressions, calendar-based rules,
and event-driven triggers.

Features:
- Cron expression parsing (minute, hour, day, month, weekday)
- Calendar-based scheduling (business days, holidays, specific dates)
- Event-driven triggers (file changes, system events, webhooks)
- Schedule validation and conflict detection
- Next run calculation with timezone support
- Dynamic schedule updates
"""

import calendar
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Schedule type enumeration"""

    CRON = "cron"
    CALENDAR = "calendar"
    EVENT = "event"
    MANUAL = "manual"


class EventType(Enum):
    """Event trigger types"""

    FILE_CHANGE = "file_change"
    SYSTEM_EVENT = "system_event"
    WEBHOOK = "webhook"
    DEPENDENCY_COMPLETE = "dependency_complete"
    THRESHOLD_EXCEEDED = "threshold_exceeded"


@dataclass
class CronExpression:
    """Parsed cron expression"""

    minute: Set[int] = field(default_factory=lambda: set(range(60)))
    hour: Set[int] = field(default_factory=lambda: set(range(24)))
    day: Set[int] = field(default_factory=lambda: set(range(1, 32)))
    month: Set[int] = field(default_factory=lambda: set(range(1, 13)))
    weekday: Set[int] = field(default_factory=lambda: set(range(7)))

    def matches(self, dt: datetime) -> bool:
        """Check if datetime matches cron expression"""
        return (
            dt.minute in self.minute
            and dt.hour in self.hour
            and dt.day in self.day
            and dt.month in self.month
            and dt.weekday() in self.weekday
        )


@dataclass
class ScheduleConfig:
    """Schedule configuration"""

    job_id: int
    schedule_type: ScheduleType
    expression: Optional[str] = None  # Cron expression or calendar rule
    timezone: str = "UTC"
    enabled: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_runs: Optional[int] = None
    callback: Optional[Callable] = None
    metadata: Dict = field(default_factory=dict)


class CronScheduler:
    """
    Cron-style scheduler with expression parsing

    Cron format: minute hour day month weekday
    - *: any value
    - */n: every n units
    - n-m: range from n to m
    - n,m: specific values n and m

    Examples:
    - "0 2 * * *": Daily at 2:00 AM
    - "0 */6 * * *": Every 6 hours
    - "0 0 * * 1": Every Monday at midnight
    - "30 3 1 * *": First day of month at 3:30 AM
    """

    def __init__(self):
        self.schedules: Dict[int, Tuple[CronExpression, ScheduleConfig]] = {}
        self.run_counts: Dict[int, int] = {}

    def parse_cron_field(self, field: str, min_val: int, max_val: int) -> Set[int]:
        """
        Parse a single cron field

        Args:
            field: Cron field string
            min_val: Minimum valid value
            max_val: Maximum valid value

        Returns:
            Set of matching values
        """
        result = set()

        # Handle wildcards
        if field == "*":
            return set(range(min_val, max_val + 1))

        # Handle step values (*/n)
        if "/" in field:
            parts = field.split("/")
            step = int(parts[1])
            if parts[0] == "*":
                result = set(range(min_val, max_val + 1, step))
            else:
                base = int(parts[0])
                result = set(range(base, max_val + 1, step))
            return result

        # Handle ranges and lists
        for part in field.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                result.update(range(start, end + 1))
            else:
                result.add(int(part))

        return result

    def parse_cron_expression(self, expression: str) -> CronExpression:
        """
        Parse cron expression string

        Args:
            expression: Cron expression (5 fields: minute hour day month weekday)

        Returns:
            Parsed CronExpression object

        Raises:
            ValueError: If expression is invalid
        """
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}. Expected 5 fields.")

        try:
            cron = CronExpression(
                minute=self.parse_cron_field(parts[0], 0, 59),
                hour=self.parse_cron_field(parts[1], 0, 23),
                day=self.parse_cron_field(parts[2], 1, 31),
                month=self.parse_cron_field(parts[3], 1, 12),
                weekday=self.parse_cron_field(parts[4], 0, 6),
            )
            return cron
        except (ValueError, IndexError) as e:
            raise ValueError(f"Error parsing cron expression '{expression}': {e}")

    def schedule_cron(self, job_id: int, cron_expression: str, callback: Callable, **kwargs) -> None:
        """
        Schedule a job with cron expression

        Args:
            job_id: Unique job identifier
            cron_expression: Cron expression string
            callback: Function to call when job runs
            **kwargs: Additional schedule configuration
        """
        cron = self.parse_cron_expression(cron_expression)
        config = ScheduleConfig(
            job_id=job_id, schedule_type=ScheduleType.CRON, expression=cron_expression, callback=callback, **kwargs
        )
        self.schedules[job_id] = (cron, config)
        self.run_counts[job_id] = 0
        logger.info(f"Scheduled job {job_id} with cron: {cron_expression}")

    def calculate_next_run(self, job_id: int, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Calculate next run time for a job

        Args:
            job_id: Job identifier
            from_time: Calculate from this time (default: now)

        Returns:
            Next run datetime or None if no more runs
        """
        if job_id not in self.schedules:
            return None

        cron, config = self.schedules[job_id]

        # Check if schedule is enabled
        if not config.enabled:
            return None

        # Check if max runs exceeded
        if config.max_runs and self.run_counts.get(job_id, 0) >= config.max_runs:
            return None

        # Get timezone
        tz = ZoneInfo(config.timezone)
        current = from_time or datetime.now(tz)

        # Check start/end dates
        if config.start_date and current < config.start_date:
            current = config.start_date
        if config.end_date and current > config.end_date:
            return None

        # Find next matching time (check up to 4 years ahead)
        max_iterations = 366 * 4 * 24 * 60  # 4 years in minutes
        check_time = current.replace(second=0, microsecond=0) + timedelta(minutes=1)

        for _ in range(max_iterations):
            if cron.matches(check_time):
                if config.end_date and check_time > config.end_date:
                    return None
                return check_time
            check_time += timedelta(minutes=1)

        logger.warning(f"Could not find next run time for job {job_id}")
        return None

    def should_run(self, job_id: int, check_time: Optional[datetime] = None) -> bool:
        """
        Check if job should run at given time

        Args:
            job_id: Job identifier
            check_time: Time to check (default: now)

        Returns:
            True if job should run
        """
        if job_id not in self.schedules:
            return False

        cron, config = self.schedules[job_id]

        if not config.enabled:
            return False

        tz = ZoneInfo(config.timezone)
        now = check_time or datetime.now(tz)

        # Check constraints
        if config.start_date and now < config.start_date:
            return False
        if config.end_date and now > config.end_date:
            return False
        if config.max_runs and self.run_counts.get(job_id, 0) >= config.max_runs:
            return False

        return cron.matches(now)

    def mark_run(self, job_id: int) -> None:
        """Mark job as run (increment counter)"""
        self.run_counts[job_id] = self.run_counts.get(job_id, 0) + 1

    def remove_schedule(self, job_id: int) -> None:
        """Remove job schedule"""
        self.schedules.pop(job_id, None)
        self.run_counts.pop(job_id, None)
        logger.info(f"Removed schedule for job {job_id}")


class CalendarScheduler:
    """
    Calendar-based scheduler with business day and holiday support

    Features:
    - Business day scheduling (Mon-Fri)
    - Holiday exclusion
    - Specific date scheduling
    - Month-end scheduling
    - Quarter-end scheduling
    """

    def __init__(self):
        self.schedules: Dict[int, ScheduleConfig] = {}
        self.holidays: Set[datetime] = set()
        self.business_days = {0, 1, 2, 3, 4}  # Mon-Fri

    def add_holiday(self, date: datetime) -> None:
        """Add a holiday date"""
        self.holidays.add(date.replace(hour=0, minute=0, second=0, microsecond=0))

    def add_holidays(self, dates: List[datetime]) -> None:
        """Add multiple holiday dates"""
        for date in dates:
            self.add_holiday(date)

    def is_business_day(self, date: datetime) -> bool:
        """Check if date is a business day (not weekend or holiday)"""
        date_only = date.replace(hour=0, minute=0, second=0, microsecond=0)
        return date.weekday() in self.business_days and date_only not in self.holidays

    def is_month_end(self, date: datetime) -> bool:
        """Check if date is last business day of month"""
        last_day = calendar.monthrange(date.year, date.month)[1]
        last_date = date.replace(day=last_day)

        # Find last business day
        while not self.is_business_day(last_date):
            last_date -= timedelta(days=1)

        return date.date() == last_date.date()

    def is_quarter_end(self, date: datetime) -> bool:
        """Check if date is last business day of quarter"""
        quarter_months = [3, 6, 9, 12]
        return date.month in quarter_months and self.is_month_end(date)

    def schedule_business_days(self, job_id: int, time: str, callback: Callable, **kwargs) -> None:
        """
        Schedule job on business days at specific time

        Args:
            job_id: Job identifier
            time: Time in HH:MM format
            callback: Function to call
            **kwargs: Additional configuration
        """
        hour, minute = map(int, time.split(":"))
        config = ScheduleConfig(
            job_id=job_id,
            schedule_type=ScheduleType.CALENDAR,
            expression=f"business_days {time}",
            callback=callback,
            metadata={"hour": hour, "minute": minute, "type": "business_days"},
            **kwargs,
        )
        self.schedules[job_id] = config
        logger.info(f"Scheduled job {job_id} on business days at {time}")

    def schedule_month_end(self, job_id: int, time: str, callback: Callable, **kwargs) -> None:
        """Schedule job on last business day of month"""
        hour, minute = map(int, time.split(":"))
        config = ScheduleConfig(
            job_id=job_id,
            schedule_type=ScheduleType.CALENDAR,
            expression=f"month_end {time}",
            callback=callback,
            metadata={"hour": hour, "minute": minute, "type": "month_end"},
            **kwargs,
        )
        self.schedules[job_id] = config
        logger.info(f"Scheduled job {job_id} on month end at {time}")

    def should_run(self, job_id: int, check_time: Optional[datetime] = None) -> bool:
        """Check if calendar job should run"""
        if job_id not in self.schedules:
            return False

        config = self.schedules[job_id]
        if not config.enabled:
            return False

        tz = ZoneInfo(config.timezone)
        now = check_time or datetime.now(tz)

        meta = config.metadata
        schedule_type = meta.get("type")

        # Check time matches
        if now.hour != meta.get("hour") or now.minute != meta.get("minute"):
            return False

        # Check schedule type
        if schedule_type == "business_days":
            return self.is_business_day(now)
        elif schedule_type == "month_end":
            return self.is_month_end(now)
        elif schedule_type == "quarter_end":
            return self.is_quarter_end(now)

        return False


class BackupScheduler:
    """
    Main scheduler combining cron, calendar, and event-driven scheduling

    Usage:
        scheduler = BackupScheduler()

        # Cron scheduling
        scheduler.schedule_cron(1, "0 2 * * *", run_backup)

        # Business day scheduling
        scheduler.schedule_business_days(2, "18:00", run_report)

        # Event-driven
        scheduler.schedule_event(3, EventType.FILE_CHANGE, run_verify)
    """

    def __init__(self):
        self.cron_scheduler = CronScheduler()
        self.calendar_scheduler = CalendarScheduler()
        self.event_handlers: Dict[EventType, List[Tuple[int, Callable]]] = {}
        self.enabled = True

    def schedule_cron(self, job_id: int, cron_expression: str, callback: Callable, **kwargs) -> None:
        """Schedule job with cron expression"""
        self.cron_scheduler.schedule_cron(job_id, cron_expression, callback, **kwargs)

    def schedule_business_days(self, job_id: int, time: str, callback: Callable, **kwargs) -> None:
        """Schedule job on business days"""
        self.calendar_scheduler.schedule_business_days(job_id, time, callback, **kwargs)

    def schedule_month_end(self, job_id: int, time: str, callback: Callable, **kwargs) -> None:
        """Schedule job on month end"""
        self.calendar_scheduler.schedule_month_end(job_id, time, callback, **kwargs)

    def schedule_event(self, job_id: int, event_type: EventType, callback: Callable) -> None:
        """
        Schedule job to run on specific event

        Args:
            job_id: Job identifier
            event_type: Type of event to trigger on
            callback: Function to call when event occurs
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append((job_id, callback))
        logger.info(f"Scheduled job {job_id} for event {event_type.value}")

    def trigger_event(self, event_type: EventType, **event_data) -> List[int]:
        """
        Trigger event and run associated jobs

        Args:
            event_type: Type of event
            **event_data: Event data to pass to callbacks

        Returns:
            List of triggered job IDs
        """
        if not self.enabled:
            return []

        triggered = []
        handlers = self.event_handlers.get(event_type, [])

        for job_id, callback in handlers:
            try:
                callback(job_id=job_id, **event_data)
                triggered.append(job_id)
                logger.info(f"Triggered job {job_id} for event {event_type.value}")
            except Exception as e:
                logger.error(f"Error triggering job {job_id}: {e}")

        return triggered

    def calculate_next_run(self, job_id: int, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate next run time for any job type"""
        next_run = self.cron_scheduler.calculate_next_run(job_id, from_time)
        if next_run:
            return next_run

        # Calendar jobs need custom calculation
        # (simplified - full implementation would check business days)
        return None

    def get_pending_jobs(self, check_time: Optional[datetime] = None) -> List[int]:
        """
        Get list of jobs that should run at given time

        Args:
            check_time: Time to check (default: now)

        Returns:
            List of job IDs that should run
        """
        if not self.enabled:
            return []

        pending = []

        # Check cron jobs
        for job_id in self.cron_scheduler.schedules.keys():
            if self.cron_scheduler.should_run(job_id, check_time):
                pending.append(job_id)

        # Check calendar jobs
        for job_id in self.calendar_scheduler.schedules.keys():
            if self.calendar_scheduler.should_run(job_id, check_time):
                pending.append(job_id)

        return pending

    def enable(self) -> None:
        """Enable scheduler"""
        self.enabled = True
        logger.info("Scheduler enabled")

    def disable(self) -> None:
        """Disable scheduler"""
        self.enabled = False
        logger.info("Scheduler disabled")

    def remove_schedule(self, job_id: int) -> None:
        """Remove job from all schedulers"""
        self.cron_scheduler.remove_schedule(job_id)
        self.calendar_scheduler.schedules.pop(job_id, None)

        # Remove from event handlers
        for event_type in self.event_handlers:
            self.event_handlers[event_type] = [(jid, cb) for jid, cb in self.event_handlers[event_type] if jid != job_id]

        logger.info(f"Removed all schedules for job {job_id}")
