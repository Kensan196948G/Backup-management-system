# AOMEI Integration Quick Start Guide

## Prerequisites

- Backup Management System running
- AOMEI Backupper installed on Windows
- PowerShell 5.1 or higher
- Network connectivity between Windows and API server

## Step 1: Configure API Key

### Set API Key in Application

Edit your configuration file or set environment variable:

**Option A: config.py**
```python
AOMEI_API_KEY = "aomei-secure-key-2025-production"
```

**Option B: Environment Variable**
```bash
export AOMEI_API_KEY="aomei-secure-key-2025-production"
```

**Option C: .env file**
```bash
AOMEI_API_KEY=aomei-secure-key-2025-production
```

### Update PowerShell Configuration

Edit `scripts/powershell/config.json`:
```json
{
  "api_url": "http://YOUR_SERVER:5000/api/v1",
  "api_key": "aomei-secure-key-2025-production",
  "log_level": "INFO"
}
```

## Step 2: Register AOMEI Backup Job

### Option A: Using PowerShell Script

```powershell
# Navigate to scripts directory
cd C:\BackupSystem\scripts\powershell

# Register new job (job_id=0)
$body = @{
    job_id = 0
    task_name = "My AOMEI Backup"
    job_type = "system_image"
    target_server = "MYSERVER"
    target_path = "D:\Backups\System"
    description = "Daily system backup"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://YOUR_SERVER:5000/api/v1/aomei/register" `
    -Method POST `
    -Headers @{"X-API-Key"="aomei-secure-key-2025-production"; "Content-Type"="application/json"} `
    -Body $body
```

### Option B: Using curl

```bash
curl -X POST http://YOUR_SERVER:5000/api/v1/aomei/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: aomei-secure-key-2025-production" \
  -d '{
    "job_id": 0,
    "task_name": "My AOMEI Backup",
    "job_type": "system_image",
    "target_server": "MYSERVER",
    "target_path": "D:\\Backups\\System",
    "description": "Daily system backup"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Job registered successfully with ID 1",
  "data": {
    "job_id": 1,
    "job_name": "My AOMEI Backup",
    "backup_tool": "aomei"
  }
}
```

**Note the job_id (e.g., 1) for next steps!**

## Step 3: Test AOMEI Integration Script

### Run Test Mode

```powershell
cd C:\BackupSystem\scripts\powershell
.\aomei_integration.ps1 -TestMode
```

This will:
- Check configuration file
- Search for AOMEI log directory
- List recent log files
- Parse latest log (if available)

## Step 4: Send Test Status

### Manual Status Update

```powershell
$statusBody = @{
    job_id = 1  # Use the job_id from Step 2
    status = "success"
    backup_size = 10737418240  # 10 GB in bytes
    duration = 3600  # 1 hour in seconds
    task_name = "My AOMEI Backup"
    copy_type = "primary"
    storage_path = "D:\Backups\System\2025-11-02"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://YOUR_SERVER:5000/api/v1/aomei/status" `
    -Method POST `
    -Headers @{"X-API-Key"="aomei-secure-key-2025-production"; "Content-Type"="application/json"} `
    -Body $statusBody
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Status updated successfully for job 1"
}
```

## Step 5: Verify Status in Dashboard

### Using API (requires JWT token)

```bash
# Login to get JWT token
TOKEN=$(curl -X POST http://YOUR_SERVER:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.access_token')

# Get job status
curl -X GET http://YOUR_SERVER:5000/api/v1/aomei/jobs/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Using Web Dashboard

1. Login to web dashboard: http://YOUR_SERVER:5000
2. Navigate to: Backups → Jobs
3. Find job: "My AOMEI Backup"
4. Check status: Should show "success" with size and duration

## Step 6: Setup Automatic Status Reporting

### Option A: Run After Each Backup

Execute PowerShell script with specific job ID:

```powershell
.\aomei_integration.ps1 -JobId 1 -TaskName "My AOMEI Backup"
```

### Option B: Continuous Monitoring Mode

Monitor AOMEI logs and auto-report:

```powershell
.\aomei_integration.ps1 -JobId 1 -MonitorMode -MonitorIntervalSeconds 300
```

This will:
- Check for new/updated log files every 5 minutes (300 seconds)
- Automatically parse and send status
- Continue running indefinitely

### Option C: Windows Scheduled Task

Create scheduled task to run after AOMEI backup:

```powershell
$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\BackupSystem\scripts\powershell\aomei_integration.ps1 -JobId 1 -TaskName 'My AOMEI Backup'"

$trigger = New-ScheduledTaskTrigger -Daily -At "04:00AM"

Register-ScheduledTask `
    -TaskName "AOMEI Status Reporter" `
    -Action $action `
    -Trigger $trigger `
    -User "SYSTEM" `
    -RunLevel Highest `
    -Description "Report AOMEI backup status to management system"
```

## Step 7: Configure AOMEI Task

### Link PowerShell Script to AOMEI Task

1. Open AOMEI Backupper
2. Edit your backup task
3. Go to: Schedule → Advanced → After backup completes
4. Add command:
   ```
   PowerShell.exe -ExecutionPolicy Bypass -File "C:\BackupSystem\scripts\powershell\aomei_integration.ps1" -JobId 1
   ```

## Troubleshooting

### Issue: "API key is required"

**Solution**: Check X-API-Key header is set correctly
```powershell
# Verify in PowerShell
$headers = @{"X-API-Key"="aomei-secure-key-2025-production"}
$headers
```

### Issue: "Job ID X not found"

**Solution**: Register the job first (Step 2) or verify job_id
```bash
# List all AOMEI jobs
curl -X GET http://YOUR_SERVER:5000/api/v1/aomei/jobs \
  -H "Authorization: Bearer $TOKEN"
```

### Issue: "AOMEI log directory not found"

**Solution**: Manually specify log path
```powershell
.\aomei_integration.ps1 -JobId 1 -LogPath "C:\Program Files (x86)\AOMEI Backupper\log"
```

### Issue: PowerShell script execution blocked

**Solution**: Set execution policy
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Verification Checklist

- [ ] API key configured in application
- [ ] API key configured in PowerShell config.json
- [ ] AOMEI job registered (received job_id)
- [ ] Test status update successful
- [ ] Status visible in dashboard
- [ ] PowerShell script runs without errors
- [ ] AOMEI log directory detected
- [ ] Database records created (BackupJob, BackupExecution, BackupCopy)

## Next Steps

1. **Setup Multiple Jobs**: Repeat Steps 2-7 for each AOMEI task
2. **Configure Alerts**: Set up email/Teams notifications for failures
3. **Review Reports**: Check daily/weekly backup reports
4. **Test Restore**: Verify backup integrity with restore test
5. **Monitor Compliance**: Check 3-2-1-1-0 rule compliance status

## Support

- **Full Documentation**: `/docs/AOMEI_INTEGRATION.md`
- **Implementation Details**: `/docs/AOMEI_IMPLEMENTATION_SUMMARY.md`
- **PowerShell Script**: `/scripts/powershell/aomei_integration.ps1`
- **API Reference**: `/docs/API.md`

## Example: Complete Workflow

```powershell
# 1. Register job
$register = @{
    job_id = 0
    task_name = "Production DB Backup"
    job_type = "database"
    target_server = "SQLSERVER01"
    target_path = "D:\Backups\Database"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://backupsrv:5000/api/v1/aomei/register" `
    -Method POST `
    -Headers @{"X-API-Key"="aomei-secure-key-2025-production"; "Content-Type"="application/json"} `
    -Body $register

$jobId = $result.data.job_id
Write-Host "Registered job ID: $jobId"

# 2. Configure AOMEI to run script after backup
# Add to AOMEI task: PowerShell.exe -File "C:\...\aomei_integration.ps1" -JobId $jobId

# 3. Wait for AOMEI backup to complete...

# 4. Verify status
.\aomei_integration.ps1 -JobId $jobId -TaskName "Production DB Backup"

# 5. Check in dashboard
# Login and navigate to Backups → Jobs → "Production DB Backup"
```

## Success!

If all steps completed successfully, you now have:
- AOMEI Backupper integrated with Backup Management System
- Automatic status reporting after each backup
- Centralized monitoring and reporting
- Compliance tracking (3-2-1-1-0 rule)
- Alert notifications for failures
