# ==============================================================================
# Backup Management System - Common Functions Module (Enhanced)
# PowerShell 5.1+ Compatible
# ==============================================================================

# Global variables
$script:ConfigPath = Join-Path $PSScriptRoot "config.json"
$script:LogPath = Join-Path $PSScriptRoot "logs"
$script:Config = $null

# Load error handling utilities
$errorHandlingPath = Join-Path $PSScriptRoot "error_handling_utils.ps1"
if (Test-Path $errorHandlingPath) {
    . $errorHandlingPath
}

# ==============================================================================
# Configuration Management
# ==============================================================================

<#
.SYNOPSIS
    Loads the backup system configuration file
.DESCRIPTION
    Reads config.json and loads it into a global variable with validation
    of required fields. Implements error handling with detailed logging.
.EXAMPLE
    $config = Get-BackupSystemConfig
.RETURNS
    Configuration object (PSCustomObject)
.THROWS
    Throws exception if config file not found or invalid JSON
#>
function Get-BackupSystemConfig {
    [CmdletBinding()]
    param()

    try {
        # Validate config file exists
        if (-not (Test-Path $script:ConfigPath)) {
            throw "Configuration file not found: $script:ConfigPath"
        }

        Write-BackupLog -Level "INFO" -Message "Loading configuration from: $script:ConfigPath"

        # Read and parse JSON
        $configContent = Get-Content $script:ConfigPath -Raw -Encoding UTF8
        $script:Config = $configContent | ConvertFrom-Json

        # Validate required fields
        if (-not $script:Config.api_url) {
            throw "Required field 'api_url' missing from configuration"
        }

        # Validate API URL format
        if (-not (Test-ValidUri -Uri $script:Config.api_url)) {
            throw "Invalid API URL format: $($script:Config.api_url)"
        }

        Write-BackupLog -Level "INFO" -Message "Configuration loaded successfully: API=$($script:Config.api_url)"
        return $script:Config
    }
    catch {
        $errorContext = New-ErrorContext -Exception $_ -FunctionName "Get-BackupSystemConfig"
        Write-ErrorContext -ErrorContext $errorContext
        Add-ErrorStatistic -ErrorContext $errorContext
        throw
    }
}

<#
.SYNOPSIS
    Saves the backup system configuration to file
.DESCRIPTION
    Persists configuration object to JSON file with proper encoding and
    error handling.
.PARAMETER Config
    Configuration object to save
.EXAMPLE
    Save-BackupSystemConfig -Config $config
#>
function Save-BackupSystemConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNull()]
        [PSCustomObject]$Config
    )

    try {
        Write-BackupLog -Level "INFO" -Message "Saving configuration to: $script:ConfigPath"

        # Ensure directory exists
        $configDir = Split-Path -Parent $script:ConfigPath
        if (-not (Test-Path $configDir)) {
            New-Item -ItemType Directory -Path $configDir -Force | Out-Null
        }

        # Save with pretty formatting
        $Config | ConvertTo-Json -Depth 10 | Set-Content $script:ConfigPath -Encoding UTF8

        Write-BackupLog -Level "INFO" -Message "Configuration saved successfully"
    }
    catch {
        $errorContext = New-ErrorContext -Exception $_ `
            -FunctionName "Save-BackupSystemConfig" `
            -Context @{ config_path = $script:ConfigPath }
        Write-ErrorContext -ErrorContext $errorContext
        Add-ErrorStatistic -ErrorContext $errorContext
        throw
    }
}

# ==============================================================================
# Logging Functions
# ==============================================================================

<#
.SYNOPSIS
    Writes a formatted log message
.DESCRIPTION
    Logs messages to file and console with timestamp, level, and optional job ID.
    Supports ERROR, WARNING, and INFO levels. Attempts to write to Windows Event Log
    for ERROR and WARNING levels.
.PARAMETER Level
    Log level: INFO, WARNING, or ERROR
.PARAMETER Message
    Log message content
.PARAMETER JobId
    Associated backup job ID (optional)
.EXAMPLE
    Write-BackupLog -Level "INFO" -Message "Backup started" -JobId 1
#>
function Write-BackupLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("INFO", "WARNING", "ERROR")]
        [string]$Level,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$Message,

        [Parameter(Mandatory = $false)]
        [ValidateScript({$_ -gt 0})]
        [int]$JobId
    )

    try {
        # Ensure log directory exists
        if (-not (Test-Path $script:LogPath)) {
            New-Item -ItemType Directory -Path $script:LogPath -Force | Out-Null
        }

        # Format log message with timestamp and job ID
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        $jobIdText = if ($JobId) { " [JobID:$JobId]" } else { "" }
        $logMessage = "[$timestamp] [$Level]$jobIdText $Message"

        # Log to file
        $logFile = Join-Path $script:LogPath "backup_integration_$(Get-Date -Format 'yyyyMMdd').log"
        Add-Content -Path $logFile -Value $logMessage -Encoding UTF8

        # Output to console with color coding
        switch ($Level) {
            "ERROR"   { Write-Host $logMessage -ForegroundColor Red }
            "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
            "INFO"    { Write-Host $logMessage -ForegroundColor Green }
        }

        # Write to Windows Event Log (ERROR and WARNING only)
        if ($Level -in @("ERROR", "WARNING")) {
            try {
                $eventType = if ($Level -eq "ERROR") { "Error" } else { "Warning" }
                $sourceName = "BackupManagementSystem"

                # Create event source if it doesn't exist (requires admin)
                if (-not [System.Diagnostics.EventLog]::SourceExists($sourceName)) {
                    try {
                        New-EventLog -LogName Application -Source $sourceName -ErrorAction SilentlyContinue
                    }
                    catch {
                        # Silently ignore - user may not have admin rights
                    }
                }

                # Write to event log
                Write-EventLog -LogName Application -Source $sourceName `
                    -EventId 1000 -EntryType $eventType -Message $logMessage -ErrorAction SilentlyContinue
            }
            catch {
                # Silently ignore event log failures (insufficient permissions)
            }
        }
    }
    catch {
        # Fallback: write directly to console if logging fails
        Write-Host "LOGGING ERROR: $_" -ForegroundColor Red
        Write-Host $Message -ForegroundColor Red
    }
}

# ==============================================================================
# REST API Communication
# ==============================================================================

<#
.SYNOPSIS
    Sends backup job status to the REST API
.DESCRIPTION
    Reports backup job completion status with automatic retry on transient errors.
    Validates all input parameters before sending.
.PARAMETER JobId
    Backup job ID (must be positive integer)
.PARAMETER Status
    Job status: success, failed, or warning
.PARAMETER BackupSize
    Backup size in bytes (optional)
.PARAMETER Duration
    Job duration in seconds (optional)
.PARAMETER ErrorMessage
    Error message if job failed (optional)
.EXAMPLE
    Send-BackupStatus -JobId 1 -Status "success" -BackupSize 1073741824 -Duration 300
.RETURNS
    API response object
.THROWS
    Throws after all retry attempts exhausted
#>
function Send-BackupStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$JobId,

        [Parameter(Mandatory = $true)]
        [ValidateSet("success", "failed", "warning")]
        [string]$Status,

        [Parameter(Mandatory = $false)]
        [long]$BackupSize = 0,

        [Parameter(Mandatory = $false)]
        [int]$Duration = 0,

        [Parameter(Mandatory = $false)]
        [string]$ErrorMessage = ""
    )

    try {
        # Validate parameters
        if (-not (Test-ValidJobId -JobId $JobId)) {
            throw "Invalid JobId: $JobId"
        }

        if ($BackupSize -lt 0) {
            throw "BackupSize cannot be negative: $BackupSize"
        }

        if ($Duration -lt 0) {
            throw "Duration cannot be negative: $Duration"
        }

        # Load configuration if not already loaded
        if (-not $script:Config) {
            Get-BackupSystemConfig | Out-Null
        }

        $apiUrl = $script:Config.api_url.TrimEnd('/') + "/api/backup/update-status"

        # Build request body
        $body = @{
            job_id = $JobId
            status = $Status
            backup_size = $BackupSize
            duration_seconds = $Duration
        }

        if (-not [string]::IsNullOrEmpty($ErrorMessage)) {
            $body["error_message"] = $ErrorMessage
        }

        $jsonBody = $body | ConvertTo-Json

        # Build headers
        $headers = @{
            "Content-Type" = "application/json"
        }

        if ($script:Config.api_token) {
            $headers["Authorization"] = "Bearer $($script:Config.api_token)"
        }

        Write-BackupLog -Level "INFO" `
            -Message "Sending backup status to API: JobID=$JobId, Status=$Status" `
            -JobId $JobId

        # Execute with retry
        $response = Invoke-WithRetry `
            -ScriptBlock {
                Invoke-RestMethod -Uri $apiUrl -Method Post `
                    -Headers $headers -Body $jsonBody -ContentType "application/json" `
                    -ErrorAction Stop
            } `
            -MaxRetries 3 `
            -OperationName "Send-BackupStatus" `
            -ErrorAction Stop

        Write-BackupLog -Level "INFO" `
            -Message "Backup status sent successfully" `
            -JobId $JobId

        return $response
    }
    catch {
        $errorContext = New-ErrorContext -Exception $_ `
            -FunctionName "Send-BackupStatus" `
            -Context @{
                job_id = $JobId
                status = $Status
                backup_size = $BackupSize
            }
        Write-ErrorContext -ErrorContext $errorContext -JobId $JobId
        Add-ErrorStatistic -ErrorContext $errorContext

        throw
    }
}

<#
.SYNOPSIS
    Sends backup copy status to the REST API
.DESCRIPTION
    Reports off-site backup copy completion with retry logic and validation.
.PARAMETER JobId
    Backup job ID
.PARAMETER Status
    Copy status: success, failed, or warning
.PARAMETER CopySize
    Data copied in bytes (optional)
.PARAMETER Duration
    Copy duration in seconds (optional)
.PARAMETER ErrorMessage
    Error message if copy failed (optional)
.EXAMPLE
    Send-BackupCopyStatus -JobId 1 -Status "success" -CopySize 1073741824
.RETURNS
    API response object
#>
function Send-BackupCopyStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$JobId,

        [Parameter(Mandatory = $true)]
        [ValidateSet("success", "failed", "warning")]
        [string]$Status,

        [Parameter(Mandatory = $false)]
        [long]$CopySize = 0,

        [Parameter(Mandatory = $false)]
        [int]$Duration = 0,

        [Parameter(Mandatory = $false)]
        [string]$ErrorMessage = ""
    )

    try {
        # Validate parameters
        if (-not (Test-ValidJobId -JobId $JobId)) {
            throw "Invalid JobId: $JobId"
        }

        if ($CopySize -lt 0) {
            throw "CopySize cannot be negative: $CopySize"
        }

        if (-not $script:Config) {
            Get-BackupSystemConfig | Out-Null
        }

        $apiUrl = $script:Config.api_url.TrimEnd('/') + "/api/backup/update-copy-status"

        # Build request
        $body = @{
            job_id = $JobId
            status = $Status
            copy_size = $CopySize
            duration_seconds = $Duration
        }

        if (-not [string]::IsNullOrEmpty($ErrorMessage)) {
            $body["error_message"] = $ErrorMessage
        }

        $jsonBody = $body | ConvertTo-Json

        $headers = @{
            "Content-Type" = "application/json"
        }

        if ($script:Config.api_token) {
            $headers["Authorization"] = "Bearer $($script:Config.api_token)"
        }

        Write-BackupLog -Level "INFO" `
            -Message "Sending backup copy status to API: JobID=$JobId, Status=$Status" `
            -JobId $JobId

        # Execute with retry
        $response = Invoke-WithRetry `
            -ScriptBlock {
                Invoke-RestMethod -Uri $apiUrl -Method Post `
                    -Headers $headers -Body $jsonBody -ContentType "application/json" `
                    -ErrorAction Stop
            } `
            -MaxRetries 3 `
            -OperationName "Send-BackupCopyStatus"

        Write-BackupLog -Level "INFO" -Message "Backup copy status sent successfully" -JobId $JobId
        return $response
    }
    catch {
        $errorContext = New-ErrorContext -Exception $_ `
            -FunctionName "Send-BackupCopyStatus" `
            -Context @{ job_id = $JobId; status = $Status }
        Write-ErrorContext -ErrorContext $errorContext -JobId $JobId
        Add-ErrorStatistic -ErrorContext $errorContext

        throw
    }
}

<#
.SYNOPSIS
    Sends backup execution record to the REST API
.DESCRIPTION
    Records detailed backup execution information with timestamps and metrics.
.PARAMETER JobId
    Backup job ID
.PARAMETER StartTime
    Backup start time
.PARAMETER EndTime
    Backup end time
.PARAMETER Status
    Execution status
.PARAMETER BackupSize
    Backup size in bytes (optional)
.PARAMETER Details
    Additional execution details (optional)
.EXAMPLE
    Send-BackupExecution -JobId 1 -StartTime $start -EndTime $end -Status "success"
#>
function Send-BackupExecution {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$JobId,

        [Parameter(Mandatory = $true)]
        [datetime]$StartTime,

        [Parameter(Mandatory = $true)]
        [datetime]$EndTime,

        [Parameter(Mandatory = $true)]
        [ValidateSet("success", "failed", "warning")]
        [string]$Status,

        [Parameter(Mandatory = $false)]
        [long]$BackupSize = 0,

        [Parameter(Mandatory = $false)]
        [string]$Details = ""
    )

    try {
        # Validate parameters
        if (-not (Test-ValidJobId -JobId $JobId)) {
            throw "Invalid JobId: $JobId"
        }

        if ($EndTime -le $StartTime) {
            throw "EndTime must be after StartTime"
        }

        if (-not $script:Config) {
            Get-BackupSystemConfig | Out-Null
        }

        $apiUrl = $script:Config.api_url.TrimEnd('/') + "/api/backup/record-execution"

        # Build request
        $body = @{
            job_id = $JobId
            start_time = $StartTime.ToString("yyyy-MM-ddTHH:mm:ss")
            end_time = $EndTime.ToString("yyyy-MM-ddTHH:mm:ss")
            status = $Status
            backup_size = $BackupSize
            details = $Details
        }

        $jsonBody = $body | ConvertTo-Json

        $headers = @{
            "Content-Type" = "application/json"
        }

        if ($script:Config.api_token) {
            $headers["Authorization"] = "Bearer $($script:Config.api_token)"
        }

        Write-BackupLog -Level "INFO" `
            -Message "Sending backup execution record: JobID=$JobId" `
            -JobId $JobId

        # Execute with retry
        $response = Invoke-WithRetry `
            -ScriptBlock {
                Invoke-RestMethod -Uri $apiUrl -Method Post `
                    -Headers $headers -Body $jsonBody -ContentType "application/json" `
                    -ErrorAction Stop
            } `
            -MaxRetries 3 `
            -OperationName "Send-BackupExecution"

        Write-BackupLog -Level "INFO" -Message "Backup execution record sent successfully" -JobId $JobId
        return $response
    }
    catch {
        $errorContext = New-ErrorContext -Exception $_ `
            -FunctionName "Send-BackupExecution" `
            -Context @{ job_id = $JobId; status = $Status }
        Write-ErrorContext -ErrorContext $errorContext -JobId $JobId
        Add-ErrorStatistic -ErrorContext $errorContext

        throw
    }
}

# ==============================================================================
# Utility Functions
# ==============================================================================

<#
.SYNOPSIS
    Converts bytes to human-readable format
.DESCRIPTION
    Formats byte values as KB, MB, GB, or TB with appropriate precision
.PARAMETER Bytes
    Number of bytes
.EXAMPLE
    Convert-BytesToHumanReadable -Bytes 1073741824
    # Output: "1.00 GB"
.RETURNS
    Formatted string (e.g., "1.50 GB")
#>
function Convert-BytesToHumanReadable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateScript({$_ -ge 0})]
        [long]$Bytes
    )

    $units = @("B", "KB", "MB", "GB", "TB", "PB")
    $index = 0
    $size = [double]$Bytes

    while ($size -ge 1024 -and $index -lt $units.Length - 1) {
        $size = $size / 1024
        $index++
    }

    return "{0:N2} {1}" -f $size, $units[$index]
}

<#
.SYNOPSIS
    Converts seconds to human-readable time format
.DESCRIPTION
    Formats duration as "X hours Y minutes Z seconds"
.PARAMETER Seconds
    Duration in seconds
.EXAMPLE
    Convert-SecondsToHumanReadable -Seconds 3661
    # Output: "1 hour 1 minute 1 second"
.RETURNS
    Formatted time string
#>
function Convert-SecondsToHumanReadable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateScript({$_ -ge 0})]
        [int]$Seconds
    )

    $timeSpan = [TimeSpan]::FromSeconds($Seconds)

    $parts = @()
    if ($timeSpan.Hours -gt 0) { $parts += "$($timeSpan.Hours) hour$(if ($timeSpan.Hours -gt 1) { 's' })" }
    if ($timeSpan.Minutes -gt 0) { $parts += "$($timeSpan.Minutes) minute$(if ($timeSpan.Minutes -gt 1) { 's' })" }
    if ($timeSpan.Seconds -gt 0 -or $parts.Count -eq 0) { $parts += "$($timeSpan.Seconds) second$(if ($timeSpan.Seconds -gt 1) { 's' })" }

    return $parts -join " "
}

<#
.SYNOPSIS
    Retrieves job configuration for specified job ID
.DESCRIPTION
    Looks up configuration for a backup job across all configured tools
.PARAMETER JobId
    Backup job ID
.EXAMPLE
    $jobConfig = Get-JobConfig -JobId 1
.RETURNS
    Job configuration object or $null if not found
#>
function Get-JobConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateScript({$_ -gt 0})]
        [int]$JobId
    )

    try {
        if (-not $script:Config) {
            Get-BackupSystemConfig | Out-Null
        }

        # Search across all backup tools
        foreach ($tool in $script:Config.backup_tools.PSObject.Properties) {
            if ($tool.Value.enabled -and $tool.Value.job_ids -contains $JobId) {
                Write-BackupLog -Level "INFO" `
                    -Message "Found configuration for JobID $JobId in tool: $($tool.Name)" `
                    -JobId $JobId

                return @{
                    tool_name = $tool.Name
                    job_id = $JobId
                    enabled = $tool.Value.enabled
                }
            }
        }

        Write-BackupLog -Level "WARNING" `
            -Message "No configuration found for JobID $JobId" `
            -JobId $JobId

        return $null
    }
    catch {
        $errorContext = New-ErrorContext -Exception $_ `
            -FunctionName "Get-JobConfig" `
            -Context @{ job_id = $JobId }
        Write-ErrorContext -ErrorContext $errorContext -JobId $JobId
        Add-ErrorStatistic -ErrorContext $errorContext

        throw
    }
}

# ==============================================================================
# Module Exports
# ==============================================================================

Export-ModuleMember -Function @(
    'Get-BackupSystemConfig',
    'Save-BackupSystemConfig',
    'Write-BackupLog',
    'Send-BackupStatus',
    'Send-BackupCopyStatus',
    'Send-BackupExecution',
    'Convert-BytesToHumanReadable',
    'Convert-SecondsToHumanReadable',
    'Get-JobConfig',
    'Invoke-WithRetry',
    'Test-TransientError',
    'New-ErrorContext',
    'Write-ErrorContext',
    'Test-ValidJobId',
    'Test-ValidString',
    'Test-ValidUri',
    'Add-ErrorStatistic',
    'Get-ErrorStatistics',
    'Write-ErrorStatisticsReport'
)
