# ==============================================================================
# Backup Management System - Error Handling Utilities
# PowerShell 5.1+ Compatible
# ==============================================================================

# Define error categories for proper handling
enum ErrorCategory {
    Transient      # Network timeouts, temporary service unavailable
    Permanent      # Authentication failures, invalid parameters
    Partial        # Non-critical failures (e.g., optional data missing)
    Unknown        # Unknown error type
}

# ==============================================================================
# Retry Logic with Exponential Backoff
# ==============================================================================

<#
.SYNOPSIS
    Invokes a script block with exponential backoff retry logic
.DESCRIPTION
    Executes a script block with automatic retries on failure using exponential
    backoff. Useful for handling transient network errors.
.PARAMETER ScriptBlock
    The script block to execute
.PARAMETER MaxRetries
    Maximum number of retry attempts (default: 3)
.PARAMETER InitialWaitMs
    Initial wait time in milliseconds (default: 1000)
.PARAMETER MaxWaitMs
    Maximum wait time between retries in milliseconds (default: 30000)
.PARAMETER BackoffMultiplier
    Multiplier for exponential backoff (default: 2)
.PARAMETER ErrorAction
    Error action preference
.EXAMPLE
    Invoke-WithRetry -ScriptBlock { Invoke-RestMethod -Uri $uri -Method Post } -MaxRetries 3
.RETURNS
    Result of successful script block execution
#>
function Invoke-WithRetry {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ScriptBlock]$ScriptBlock,

        [Parameter(Mandatory = $false)]
        [int]$MaxRetries = 3,

        [Parameter(Mandatory = $false)]
        [int]$InitialWaitMs = 1000,

        [Parameter(Mandatory = $false)]
        [int]$MaxWaitMs = 30000,

        [Parameter(Mandatory = $false)]
        [double]$BackoffMultiplier = 2.0,

        [Parameter(Mandatory = $false)]
        [string]$OperationName = "Operation"
    )

    [ValidateScript({$_ -gt 0})]
    $MaxRetries = [Math]::Max(1, $MaxRetries)

    $attempt = 0
    $lastException = $null
    $currentWaitMs = $InitialWaitMs

    while ($attempt -lt $MaxRetries) {
        try {
            $attempt++
            $result = & $ScriptBlock

            if ($attempt -gt 1) {
                Write-BackupLog -Level "INFO" -Message "$OperationName succeeded on attempt $attempt"
            }

            return $result
        }
        catch {
            $lastException = $_

            if ($attempt -lt $MaxRetries) {
                Write-BackupLog -Level "WARNING" `
                    -Message "$OperationName failed (attempt $attempt/$MaxRetries): $($_.Exception.Message). Retrying in $currentWaitMs ms..."

                Start-Sleep -Milliseconds $currentWaitMs

                # Calculate next wait time with exponential backoff
                $currentWaitMs = [Math]::Min(
                    [int]($currentWaitMs * $BackoffMultiplier),
                    $MaxWaitMs
                )
            }
            else {
                Write-BackupLog -Level "ERROR" `
                    -Message "$OperationName failed after $MaxRetries attempts: $($_.Exception.Message)"
            }
        }
    }

    # All retries exhausted
    throw $lastException
}

# ==============================================================================
# Error Classification and Handling
# ==============================================================================

<#
.SYNOPSIS
    Determines if an error is transient and potentially recoverable
.DESCRIPTION
    Analyzes an error to determine if it's a transient error that may succeed
    on retry (e.g., network timeout) or a permanent error (e.g., auth failure)
.PARAMETER Exception
    The exception to classify
.RETURNS
    $true if error is transient (retry-worthy), $false if permanent
#>
function Test-TransientError {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        $Exception
    )

    # Check for network-related errors
    $transientPatterns = @(
        "timeout",
        "temporarily",
        "unavailable",
        "service.*unavailable",
        "connection.*refused",
        "no.*route",
        "network.*unreachable",
        "reset.*by.*peer",
        "Operation.*timed.*out"
    )

    $errorMessage = $Exception.Exception.Message + " " + ($Exception.InvocationInfo.PositionMessage -join " ")

    foreach ($pattern in $transientPatterns) {
        if ($errorMessage -match $pattern) {
            return $true
        }
    }

    # Check HTTP response codes (5xx are transient, 4xx are usually permanent)
    if ($Exception.Exception.Response) {
        $statusCode = [int]$Exception.Exception.Response.StatusCode
        if ($statusCode -ge 500) {
            return $true  # Server error - transient
        }
    }

    return $false
}

<#
.SYNOPSIS
    Creates a detailed error context object for logging
.DESCRIPTION
    Captures comprehensive error information including stack trace, parameters,
    and context for detailed debugging
.PARAMETER Exception
    The exception object
.PARAMETER FunctionName
    Name of the function where error occurred
.PARAMETER Context
    Additional context information (hashtable)
.RETURNS
    Error context object
#>
function New-ErrorContext {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        $Exception,

        [Parameter(Mandatory = $false)]
        [string]$FunctionName = "Unknown",

        [Parameter(Mandatory = $false)]
        [hashtable]$Context = @{}
    )

    $errorContext = @{
        timestamp = Get-Date -Format "O"  # ISO 8601 format
        function_name = $FunctionName
        error_message = $Exception.Exception.Message
        error_type = $Exception.Exception.GetType().FullName
        script_stack_trace = $Exception.ScriptStackTrace
        invocation_info = @{
            script_name = $Exception.InvocationInfo.ScriptName
            line_number = $Exception.InvocationInfo.ScriptLineNumber
            line = $Exception.InvocationInfo.Line -replace '^\s+', ''
        }
        context = $Context
        is_transient = Test-TransientError -Exception $Exception
    }

    return $errorContext
}

<#
.SYNOPSIS
    Logs error context in structured format
.DESCRIPTION
    Outputs error information in a structured, parseable format for better
    analysis and troubleshooting
.PARAMETER ErrorContext
    Error context object from New-ErrorContext
.PARAMETER JobId
    Associated backup job ID (optional)
#>
function Write-ErrorContext {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$ErrorContext,

        [Parameter(Mandatory = $false)]
        [int]$JobId = 0
    )

    $contextJson = $ErrorContext | ConvertTo-Json -Depth 5

    Write-BackupLog -Level "ERROR" `
        -Message "Error Context: $contextJson" `
        -JobId $JobId
}

# ==============================================================================
# Parameter Validation Helpers
# ==============================================================================

<#
.SYNOPSIS
    Validates backup job ID parameter
.DESCRIPTION
    Ensures job ID is valid (positive integer)
.PARAMETER JobId
    Job ID to validate
.RETURNS
    $true if valid, $false otherwise
#>
function Test-ValidJobId {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        $JobId
    )

    if ($null -eq $JobId) {
        Write-BackupLog -Level "ERROR" -Message "JobId is null"
        return $false
    }

    if (-not ($JobId -is [int])) {
        Write-BackupLog -Level "ERROR" -Message "JobId must be integer: $($JobId.GetType().Name)"
        return $false
    }

    if ($JobId -le 0) {
        Write-BackupLog -Level "ERROR" -Message "JobId must be positive: $JobId"
        return $false
    }

    return $true
}

<#
.SYNOPSIS
    Validates string parameter is not null or empty
.DESCRIPTION
    Ensures string parameter contains meaningful content
.PARAMETER Value
    String to validate
.PARAMETER ParameterName
    Name of parameter (for error messages)
.RETURNS
    $true if valid, $false otherwise
#>
function Test-ValidString {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        $Value,

        [Parameter(Mandatory = $false)]
        [string]$ParameterName = "String"
    )

    if ($null -eq $Value) {
        Write-BackupLog -Level "ERROR" -Message "$ParameterName is null"
        return $false
    }

    if ([string]::IsNullOrWhiteSpace($Value)) {
        Write-BackupLog -Level "ERROR" -Message "$ParameterName is empty or whitespace"
        return $false
    }

    return $true
}

<#
.SYNOPSIS
    Validates URI parameter
.DESCRIPTION
    Ensures URI is properly formatted and accessible
.PARAMETER Uri
    URI to validate
.RETURNS
    $true if valid, $false otherwise
#>
function Test-ValidUri {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Uri
    )

    try {
        $uriObject = [System.Uri]$Uri

        if ($uriObject.Scheme -notmatch '^https?$') {
            Write-BackupLog -Level "ERROR" -Message "URI must use HTTP or HTTPS: $Uri"
            return $false
        }

        return $true
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "Invalid URI format: $Uri - $_"
        return $false
    }
}

# ==============================================================================
# Error Statistics and Reporting
# ==============================================================================

$script:ErrorStats = @{
    total_errors = 0
    transient_errors = 0
    permanent_errors = 0
    by_type = @{}
    by_function = @{}
}

<#
.SYNOPSIS
    Records error statistics for analysis
.DESCRIPTION
    Tracks error occurrences by type and function for monitoring and alerting
.PARAMETER ErrorContext
    Error context object
#>
function Add-ErrorStatistic {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$ErrorContext
    )

    $script:ErrorStats.total_errors++

    if ($ErrorContext.is_transient) {
        $script:ErrorStats.transient_errors++
    }
    else {
        $script:ErrorStats.permanent_errors++
    }

    $errorType = $ErrorContext.error_type
    if (-not $script:ErrorStats.by_type.ContainsKey($errorType)) {
        $script:ErrorStats.by_type[$errorType] = 0
    }
    $script:ErrorStats.by_type[$errorType]++

    $funcName = $ErrorContext.function_name
    if (-not $script:ErrorStats.by_function.ContainsKey($funcName)) {
        $script:ErrorStats.by_function[$funcName] = 0
    }
    $script:ErrorStats.by_function[$funcName]++
}

<#
.SYNOPSIS
    Gets current error statistics
.DESCRIPTION
    Returns accumulated error statistics
.RETURNS
    Error statistics hashtable
#>
function Get-ErrorStatistics {
    [CmdletBinding()]
    param()

    return $script:ErrorStats
}

<#
.SYNOPSIS
    Writes error statistics report
.DESCRIPTION
    Outputs error statistics in human-readable format
.PARAMETER IncludeDetails
    Include detailed breakdown by type/function
#>
function Write-ErrorStatisticsReport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [switch]$IncludeDetails
    )

    $stats = Get-ErrorStatistics

    Write-BackupLog -Level "INFO" -Message "=== Error Statistics Report ==="
    Write-BackupLog -Level "INFO" -Message "Total Errors: $($stats.total_errors)"
    Write-BackupLog -Level "INFO" -Message "Transient Errors: $($stats.transient_errors)"
    Write-BackupLog -Level "INFO" -Message "Permanent Errors: $($stats.permanent_errors)"

    if ($IncludeDetails) {
        Write-BackupLog -Level "INFO" -Message "--- Errors by Type ---"
        foreach ($type in $stats.by_type.Keys | Sort-Object) {
            Write-BackupLog -Level "INFO" -Message "$type`: $($stats.by_type[$type])"
        }

        Write-BackupLog -Level "INFO" -Message "--- Errors by Function ---"
        foreach ($func in $stats.by_function.Keys | Sort-Object) {
            Write-BackupLog -Level "INFO" -Message "$func`: $($stats.by_function[$func])"
        }
    }
}

# ==============================================================================
# Module Exports
# ==============================================================================

Export-ModuleMember -Function @(
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

Export-ModuleMember -Variable @(
    'ErrorCategory'
)
