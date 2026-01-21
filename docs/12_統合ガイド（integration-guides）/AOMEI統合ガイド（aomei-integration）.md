# AOMEI Backupper Integration Guide

## Overview

This document describes the complete integration between AOMEI Backupper and the Backup Management System. The integration allows automatic status reporting from AOMEI Backupper to the centralized management system via PowerShell scripts and REST API.

## Architecture

```
AOMEI Backupper
       ↓
   Log Files
       ↓
PowerShell Script (aomei_integration.ps1)
       ↓
   REST API (/api/v1/aomei/*)
       ↓
  AOMEIService
       ↓
   Database (BackupJob, BackupExecution, BackupCopy)
```

## Components

### 1. PowerShell Script
**Location**: `/scripts/powershell/aomei_integration.ps1`

**Features**:
- AOMEI log file detection and parsing
- Status extraction (success/failed/warning)
- Backup size and duration calculation
- Automatic status reporting to REST API

**Usage**:
```powershell
# One-time execution for specific job
.\aomei_integration.ps1 -JobId 123 -TaskName "System Backup"

# Continuous monitoring mode
.\aomei_integration.ps1 -JobId 123 -MonitorMode -MonitorIntervalSeconds 300

# Test mode
.\aomei_integration.ps1 -TestMode
```

### 2. REST API Endpoints
**Base URL**: `/api/v1/aomei`

#### POST /api/v1/aomei/register
Register or update AOMEI backup job in the system.

**Authentication**: API Key (X-API-Key header)

**Request Body**:
```json
{
  "job_id": 0,
  "task_name": "System Backup Daily",
  "job_type": "system_image",
  "target_server": "SERVER01",
  "target_path": "D:\\Backups\\System",
  "description": "Daily system image backup"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Job registered successfully with ID 123",
  "data": {
    "job_id": 123,
    "job_name": "System Backup Daily",
    "backup_tool": "aomei"
  }
}
```

#### POST /api/v1/aomei/status
Receive backup status update from PowerShell script.

**Authentication**: API Key (X-API-Key header)

**Request Body**:
```json
{
  "job_id": 123,
  "status": "success",
  "backup_size": 10737418240,
  "duration": 3600,
  "error_message": null,
  "task_name": "System Backup Daily",
  "start_time": "2025-11-02T01:00:00",
  "end_time": "2025-11-02T02:00:00",
  "details": "AOMEI Task: System Backup Daily | Log: backup_20251102.log",
  "copy_type": "primary",
  "storage_path": "D:\\Backups\\System\\2025-11-02"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Status updated successfully for job 123"
}
```

#### POST /api/v1/aomei/log-analysis
Process AOMEI log analysis results from PowerShell script.

**Authentication**: API Key (X-API-Key header)

**Request Body**:
```json
{
  "job_id": 123,
  "log_file_path": "C:\\Program Files\\AOMEI\\Backupper\\log\\backup_20251102.log",
  "parsed_data": {
    "task_name": "System Backup Daily",
    "status": "success",
    "start_time": "2025-11-02T01:00:00",
    "end_time": "2025-11-02T02:00:00",
    "duration": 3600,
    "backup_size": 10737418240,
    "error_message": "",
    "details": "Backup completed successfully"
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "Log analysis processed successfully"
}
```

#### GET /api/v1/aomei/jobs
List all AOMEI backup jobs.

**Authentication**: JWT Token (Bearer)

**Query Parameters**:
- `active_only`: boolean (default: true) - Return only active jobs
- `include_executions`: boolean (default: false) - Include execution history

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "job_name": "System Backup Daily",
      "job_type": "system_image",
      "target_server": "SERVER01",
      "target_path": "D:\\Backups\\System",
      "is_active": true,
      "schedule_type": "manual",
      "retention_days": 30,
      "created_at": "2025-11-01T00:00:00",
      "updated_at": "2025-11-02T02:00:00"
    }
  ],
  "total": 1
}
```

#### GET /api/v1/aomei/jobs/{id}
Get AOMEI job status and details.

**Authentication**: JWT Token (Bearer)

**Response**:
```json
{
  "success": true,
  "data": {
    "job_id": 123,
    "job_name": "System Backup Daily",
    "job_type": "system_image",
    "is_active": true,
    "latest_execution": {
      "date": "2025-11-02T02:00:00",
      "result": "success",
      "size": 10737418240,
      "duration": 3600,
      "error": null
    },
    "copies": [
      {
        "type": "primary",
        "media": "disk",
        "status": "success",
        "last_backup": "2025-11-02T02:00:00",
        "size": 10737418240,
        "path": "D:\\Backups\\System\\2025-11-02"
      }
    ],
    "updated_at": "2025-11-02T02:00:00"
  }
}
```

### 3. AOMEIService
**Location**: `/app/services/aomei_service.py`

**Features**:
- Job registration and management
- Status update processing
- Log analysis result handling
- Database synchronization
- API key validation

**Key Methods**:
```python
# Register or update AOMEI job
success, message, job = AOMEIService.register_job(
    job_id=0,
    task_name="System Backup",
    job_type="system_image",
    target_server="SERVER01",
    target_path="D:\\Backups"
)

# Receive status update
success, message = AOMEIService.receive_status(
    job_id=123,
    status="success",
    backup_size=10737418240,
    duration=3600
)

# Get job status
status = AOMEIService.get_job_status(job_id=123)

# List all AOMEI jobs
jobs = AOMEIService.get_aomei_jobs(active_only=True)
```

## Setup and Configuration

### 1. API Key Configuration

Set the AOMEI API key in the application configuration:

**config.py**:
```python
AOMEI_API_KEY = "your-secure-api-key-here"
```

**Environment Variable**:
```bash
export AOMEI_API_KEY="your-secure-api-key-here"
```

### 2. PowerShell Script Configuration

Update the configuration file for PowerShell scripts:

**scripts/powershell/config.json**:
```json
{
  "api_url": "http://localhost:5000/api/v1",
  "api_key": "your-secure-api-key-here",
  "log_level": "INFO"
}
```

### 3. Task Scheduler Setup (Windows)

Create scheduled task to run PowerShell script after AOMEI backup:

```powershell
# Create scheduled task
$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\BackupSystem\scripts\powershell\aomei_integration.ps1 -JobId 123"

$trigger = New-ScheduledTaskTrigger -Daily -At "03:00AM"

Register-ScheduledTask `
    -TaskName "AOMEI Backup Status Report" `
    -Action $action `
    -Trigger $trigger `
    -Description "Report AOMEI backup status to management system"
```

## Data Flow

### Backup Execution Flow

1. **AOMEI Backupper** executes backup task
2. **AOMEI** writes log file to log directory
3. **PowerShell Script** (scheduled or triggered):
   - Detects new/updated log file
   - Parses log file for status information
   - Sends status to REST API
4. **REST API** receives status:
   - Validates API key
   - Processes status data
   - Creates/updates database records
5. **Database** stores:
   - BackupExecution record (execution history)
   - BackupCopy record (copy status)
   - Updates BackupJob (last update time)

### Database Schema

**BackupJob** (backup_jobs table):
- `id`: Job ID
- `job_name`: AOMEI task name
- `job_type`: system_image/file/database/vm
- `backup_tool`: "aomei"
- `target_server`: Server name
- `target_path`: Backup destination path

**BackupExecution** (backup_executions table):
- `job_id`: Foreign key to BackupJob
- `execution_date`: Backup end time
- `execution_result`: success/failed/warning
- `backup_size_bytes`: Backup size in bytes
- `duration_seconds`: Execution duration
- `source_system`: "aomei_powershell"

**BackupCopy** (backup_copies table):
- `job_id`: Foreign key to BackupJob
- `copy_type`: primary/secondary/offsite/offline
- `media_type`: disk/tape/cloud/external_hdd
- `last_backup_date`: Last backup timestamp
- `last_backup_size`: Last backup size
- `status`: success/failed/warning

## Status Mapping

AOMEI status values are mapped to system-wide status values:

| AOMEI Status | System Status |
|--------------|---------------|
| success      | success       |
| failed       | failed        |
| warning      | warning       |
| unknown      | warning       |

## Error Handling

### PowerShell Script Errors
- Log file not found → Warning logged, retry on next run
- API connection failed → Error logged, retry mechanism
- Invalid response → Error logged, alert generated

### API Errors
- Invalid API key → 401 Unauthorized
- Job not found → 400 Bad Request
- Invalid request data → 400 Bad Request with validation errors
- Database error → 500 Internal Server Error, transaction rollback

## Monitoring and Alerts

The system automatically generates alerts for:
- Backup failures (status = failed)
- Extended duration (> threshold)
- Missing backups (no execution in expected timeframe)
- API authentication failures

## Testing

### Test PowerShell Integration
```powershell
# Run test mode
.\aomei_integration.ps1 -TestMode
```

### Test API Endpoints
```bash
# Register job
curl -X POST http://localhost:5000/api/v1/aomei/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "job_id": 0,
    "task_name": "Test Backup",
    "job_type": "system_image"
  }'

# Send status
curl -X POST http://localhost:5000/api/v1/aomei/status \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "job_id": 123,
    "status": "success",
    "backup_size": 1073741824,
    "duration": 600
  }'

# List jobs
curl -X GET http://localhost:5000/api/v1/aomei/jobs \
  -H "Authorization: Bearer your-jwt-token"
```

## Troubleshooting

### Common Issues

**Issue**: PowerShell script cannot find AOMEI log directory
- **Solution**: Verify AOMEI installation path and log directory permissions

**Issue**: API returns 401 Unauthorized
- **Solution**: Check API key configuration in both config.json and application settings

**Issue**: Status not updating in database
- **Solution**: Check job_id exists and backup_tool is set to "aomei"

**Issue**: Log parsing fails
- **Solution**: Verify log file encoding (UTF-8) and format compatibility

## Security Considerations

1. **API Key Protection**:
   - Store API keys securely (environment variables, Azure Key Vault)
   - Rotate keys periodically
   - Use different keys for different environments

2. **Network Security**:
   - Use HTTPS for production API endpoints
   - Implement IP whitelisting if possible
   - Monitor for unusual API access patterns

3. **Access Control**:
   - API key endpoints require API key authentication
   - Query endpoints require JWT authentication
   - Implement role-based access control

## File Locations

| Component | Path |
|-----------|------|
| PowerShell Script | `/scripts/powershell/aomei_integration.ps1` |
| Common Functions | `/scripts/powershell/common_functions.ps1` |
| API Endpoints | `/app/api/v1/aomei.py` |
| Service Layer | `/app/services/aomei_service.py` |
| Schemas | `/app/api/schemas.py` |
| Documentation | `/docs/AOMEI_INTEGRATION.md` |

## References

- [AOMEI Backupper Official Documentation](https://www.aomeitech.com/)
- [PowerShell Integration Guide](../scripts/powershell/README.md)
- [REST API Documentation](../docs/API.md)
- [Database Schema](../docs/DATABASE_SCHEMA.md)
