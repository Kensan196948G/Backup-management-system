# Backup Verification Service Guide

## Overview

The Verification Service provides comprehensive backup verification and restore testing capabilities for the Backup Management System. It supports three types of verification tests:

1. **Full Restore Test** - Complete backup restoration
2. **Partial Restore Test** - Selective file restoration
3. **Integrity Check** - Checksum-only validation

## Architecture

```
app/services/verification_service.py   # Main verification service
app/verification/                       # Verification module
  ├── __init__.py                      # Type definitions and evaluation logic
  ├── checksum.py                      # Checksum calculation
  ├── validator.py                     # File validation
  └── interfaces.py                    # Abstract interfaces
app/scheduler/tasks.py                 # Automated verification tasks
```

## Features

### 1. Verification Test Types

#### Full Restore Test
- Restores complete backup to temporary location
- Verifies all restored files against original checksums
- Records detailed restoration metrics
- Auto-cleanup of test data

#### Partial Restore Test
- Selectively restores sample files
- Configurable sample size
- Faster than full restore
- Suitable for regular automated testing

#### Integrity Check
- Checksum-only verification
- No restoration required
- Fast and efficient
- Ideal for daily automated checks

### 2. Automated Scheduling

- Monthly, quarterly, semi-annual, annual frequencies
- Auto-calculation of next test dates
- Overdue test detection
- Integration with scheduler system

### 3. Test Result Recording

- Detailed test execution logs
- Duration tracking
- Error and issue recording
- Historical test data

## Usage Examples

### Basic Verification Test

```python
from app.services.verification_service import (
    get_verification_service,
    VerificationType,
)

# Get service instance
service = get_verification_service()

# Execute integrity check
result, details = service.execute_verification_test(
    job_id=1,
    test_type=VerificationType.INTEGRITY,
    tester_id=1
)

print(f"Test Result: {result.value}")
print(f"Details: {details}")
```

### Full Restore Test

```python
# Execute full restore test with custom target
result, details = service.execute_verification_test(
    job_id=1,
    test_type=VerificationType.FULL_RESTORE,
    tester_id=1,
    restore_target="/tmp/restore_test"
)

print(f"Files Restored: {details['total_files_restored']}")
print(f"Files Verified: {details['total_files_verified']}")
print(f"Verification Rate: {details['verification_rate']:.2f}%")
```

### Partial Restore Test

```python
# Test specific files
sample_files = ["file1.txt", "file2.txt", "file3.txt"]

result, details = service.execute_verification_test(
    job_id=1,
    test_type=VerificationType.PARTIAL,
    tester_id=1,
    sample_files=sample_files
)

print(f"Files Tested: {details['files_tested']}")
print(f"Success Rate: {details['success_rate']:.2f}%")
```

### Schedule Verification Tests

```python
# Schedule monthly verification
schedule = service.schedule_verification_test(
    job_id=1,
    test_frequency="monthly",
    assigned_to=1
)

print(f"Next test: {schedule.next_test_date}")
```

### Check Overdue Tests

```python
# Get overdue verification tests
overdue = service.get_overdue_verification_tests()

for schedule in overdue:
    print(f"Job {schedule.job_id} - Due: {schedule.next_test_date}")
```

### Async Execution

```python
import asyncio

async def run_verification():
    result, details = await service.execute_verification_test_async(
        job_id=1,
        test_type=VerificationType.INTEGRITY,
        tester_id=1
    )
    return result, details

# Run async
result, details = asyncio.run(run_verification())
```

## Integration with Scheduler

The verification service integrates with the scheduler system through tasks:

### 1. Scheduled Verification Execution
**Task**: `execute_scheduled_verification_tests`
**Schedule**: Daily at 2:00 AM
**Function**: Executes all due verification tests

### 2. Verification Reminders
**Task**: `check_verification_reminders`
**Schedule**: Daily at 10:00 AM
**Function**: Sends reminders for upcoming tests

### 3. Data Cleanup
**Task**: `cleanup_verification_test_data`
**Schedule**: Weekly on Sunday at 4:00 AM
**Function**: Removes old verification test records

## Configuration

### Environment Variables

```python
# config.py
VERIFICATION_REMINDER_DAYS = 7           # Days before test to send reminder
VERIFICATION_TEST_RETENTION_DAYS = 365   # How long to keep test records
```

### Test Thresholds

```python
from app.verification import get_verification_thresholds

thresholds = get_verification_thresholds()
# {
#     'full_restore': 95.0,   # 95% success required
#     'partial': 90.0,        # 90% success required
#     'integrity': 98.0       # 98% success required
# }
```

## Database Models

### VerificationTest
Records of executed verification tests:
- `job_id`: Backup job being tested
- `test_type`: full_restore/partial/integrity
- `test_date`: When test was executed
- `tester_id`: User who ran the test
- `test_result`: success/failed/warning/error
- `duration_seconds`: How long test took
- `issues_found`: Any problems detected

### VerificationSchedule
Scheduled verification tests:
- `job_id`: Backup job to test
- `test_frequency`: monthly/quarterly/semi-annual/annual
- `next_test_date`: When next test is due
- `last_test_date`: When last test was run
- `assigned_to`: User assigned to run test
- `is_active`: Whether schedule is active

## API Endpoints (Future)

```python
# Example API usage (when routes are implemented)

# Execute verification test
POST /api/verification/test
{
    "job_id": 1,
    "test_type": "integrity",
    "tester_id": 1
}

# Get verification history
GET /api/verification/history?job_id=1

# Schedule verification
POST /api/verification/schedule
{
    "job_id": 1,
    "frequency": "monthly",
    "assigned_to": 1
}

# Get overdue tests
GET /api/verification/overdue
```

## Best Practices

### 1. Test Frequency Recommendations
- **Critical backups**: Monthly full restore + weekly integrity
- **Important backups**: Quarterly full restore + monthly integrity
- **Standard backups**: Semi-annual full restore + monthly integrity

### 2. Performance Optimization
- Use `INTEGRITY` checks for daily automation
- Schedule `FULL_RESTORE` tests during off-hours
- Use `PARTIAL` tests for quick verification

### 3. Error Handling
- Always check test result status
- Review `issues_found` for failures
- Monitor overdue test alerts

### 4. Cleanup
- Test directories are auto-cleaned by default
- Manual cleanup available if needed
- Configure retention period appropriately

## Monitoring and Alerts

The verification service integrates with the alert system:

```python
# Verification failures generate alerts
if result == TestResult.FAILED:
    # Alert created automatically
    # Notification sent to assigned user
    pass
```

## Troubleshooting

### Common Issues

**1. Test fails with "Backup source not found"**
- Check BackupCopy.storage_path exists
- Verify file permissions
- Ensure backup is not on disconnected media

**2. Low verification rate**
- Check for file corruption
- Verify backup copy is complete
- Review error messages in test details

**3. Tests not executing on schedule**
- Check VerificationSchedule.is_active
- Verify scheduler is running
- Check for errors in scheduler logs

**4. Permission errors during restore**
- Ensure test_root_dir is writable
- Check restore_target permissions
- Verify source file access

## Statistics and Reporting

```python
# Get service statistics
stats = service.get_statistics()

print(f"Total Tests: {stats['total_tests']}")
print(f"Success Rate: {stats['db_success_rate']:.2f}%")
print(f"Last Test: {stats['last_test']}")
```

## Example: Complete Workflow

```python
from datetime import datetime
from app.services.verification_service import (
    get_verification_service,
    VerificationType,
)

# Initialize service
service = get_verification_service()

# 1. Schedule monthly verification
schedule = service.schedule_verification_test(
    job_id=1,
    test_frequency="monthly",
    assigned_to=1
)
print(f"Scheduled: Next test on {schedule.next_test_date}")

# 2. Execute immediate test
result, details = service.execute_verification_test(
    job_id=1,
    test_type=VerificationType.INTEGRITY,
    tester_id=1
)

# 3. Check result
if result.value == "success":
    print(f"✓ Verification passed: {details['validity_rate']:.1f}%")
else:
    print(f"✗ Verification failed: {details.get('error', 'Unknown error')}")
    if details.get('errors'):
        for error in details['errors']:
            print(f"  - {error}")

# 4. Check for overdue tests
overdue = service.get_overdue_verification_tests()
if overdue:
    print(f"\n⚠ {len(overdue)} overdue verification tests")
    for s in overdue:
        print(f"  - Job {s.job_id}: Due {s.next_test_date}")

# 5. Get statistics
stats = service.get_statistics()
print(f"\nVerification Statistics:")
print(f"  Total Tests: {stats['db_total_tests']}")
print(f"  Success Rate: {stats['db_success_rate']:.1f}%")
```

## See Also

- [Compliance Checker Guide](compliance_checker_guide.md)
- [Scheduler Guide](scheduler_guide.md)
- [Alert Manager Guide](alert_manager_guide.md)
