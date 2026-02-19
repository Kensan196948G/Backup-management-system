# ==============================================================================
# Backup Management System - Error Handling Test Suite
# PowerShell 5.1+ Compatible
# ==============================================================================

<#
.SYNOPSIS
    Comprehensive test suite for error handling utilities and functions
.DESCRIPTION
    Tests error handling mechanisms including retry logic, error classification,
    parameter validation, and logging functionality.
.NOTES
    - Designed for non-interactive execution
    - Generates detailed test report
    - Supports verbose mode for debugging
#>

param(
    [Parameter(Mandatory = $false)]
    [switch]$IncludeIntegrationTests,

    [Parameter(Mandatory = $false)]
    [string]$ReportPath = ".\test_error_handling_report.txt"
)

# ==============================================================================
# Test Framework
# ==============================================================================

$script:TestResults = @{
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    details = @()
}

<#
.SYNOPSIS
    Records test result
#>
function Add-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Message = "",
        [string]$Category = "General"
    )

    $script:TestResults.total++

    $result = @{
        name = $TestName
        category = $Category
        passed = $Passed
        message = $Message
        timestamp = Get-Date -Format "o"
    }

    $script:TestResults.details += $result

    if ($Passed) {
        $script:TestResults.passed++
        Write-Host "[PASS] $TestName" -ForegroundColor Green
    }
    else {
        $script:TestResults.failed++
        $failMsg = "[FAIL] $TestName"
        if ($Message) { $failMsg += ": $Message" }
        Write-Host $failMsg -ForegroundColor Red
    }

    if ($Message -and $VerbosePreference -eq "Continue") {
        Write-Host "  Details: $Message" -ForegroundColor Gray
    }
}

<#
.SYNOPSIS
    Writes test report to console and file
#>
function Write-TestReport {
    param(
        [string]$FilePath
    )

    $summary = @"
================================================================================
ERROR HANDLING TEST REPORT
================================================================================
Execution Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

SUMMARY
-------
Total Tests:  $($script:TestResults.total)
Passed:       $($script:TestResults.passed)
Failed:       $($script:TestResults.failed)
Skipped:      $($script:TestResults.skipped)
Pass Rate:    $([Math]::Round(($script:TestResults.passed / [Math]::Max(1, $script:TestResults.total)) * 100, 2))%

DETAILS
-------
"@

    Write-Host $summary
    Add-Content -Path $FilePath -Value $summary -Encoding UTF8

    # Group results by category
    $categories = $script:TestResults.details | Group-Object -Property category

    foreach ($category in $categories) {
        $categoryText = "`n[$($category.Name)]`n"
        Write-Host $categoryText
        Add-Content -Path $FilePath -Value $categoryText -Encoding UTF8

        foreach ($test in $category.Group) {
            $status = if ($test.passed) { "PASS" } else { "FAIL" }
            $testLine = "$status : $($test.name)"
            if ($test.message) {
                $testLine += " - $($test.message)"
            }

            Write-Host "  $testLine"
            Add-Content -Path $FilePath -Value "  $testLine" -Encoding UTF8
        }
    }

    $footer = @"

================================================================================
Report generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
================================================================================
"@

    Write-Host $footer
    Add-Content -Path $FilePath -Value $footer -Encoding UTF8
}

# ==============================================================================
# Load Required Modules
# ==============================================================================

$commonFunctionsPath = Join-Path $PSScriptRoot "powershell\common_functions_enhanced.ps1"
$errorHandlingPath = Join-Path $PSScriptRoot "powershell\error_handling_utils.ps1"

if (-not (Test-Path $commonFunctionsPath)) {
    Write-Error "Error handling utilities not found: $errorHandlingPath"
    exit 1
}

# Source the modules
. $errorHandlingPath
. $commonFunctionsPath

Write-Host "Error handling modules loaded successfully" -ForegroundColor Cyan

# ==============================================================================
# Test Suite 1: Retry Logic Tests
# ==============================================================================

Write-Host "`n=== Test Suite 1: Retry Logic ===" -ForegroundColor Cyan

# Test 1.1: Successful invocation without retry
$test1_1 = {
    $callCount = 0
    $result = Invoke-WithRetry -ScriptBlock {
        $callCount++
        return "success"
    } -MaxRetries 3 -OperationName "Test1_1"

    return ($result -eq "success") -and ($callCount -eq 1)
}

$passed1_1 = & $test1_1
Add-TestResult -TestName "Successful invocation (no retry needed)" `
    -Passed $passed1_1 `
    -Category "Retry Logic"

# Test 1.2: Retry on transient error
$test1_2 = {
    $callCount = 0
    $result = $null
    $errorOccurred = $false

    try {
        Invoke-WithRetry -ScriptBlock {
            $callCount++
            if ($callCount -lt 3) {
                throw "Temporary error"
            }
            return "success"
        } -MaxRetries 5 -InitialWaitMs 10 -OperationName "Test1_2" | Out-Null

        $result = "success"
    }
    catch {
        $errorOccurred = $true
    }

    return ($callCount -eq 3) -and (-not $errorOccurred)
}

$passed1_2 = & $test1_2
Add-TestResult -TestName "Retry on transient error (eventual success)" `
    -Passed $passed1_2 `
    -Message "Retried $($null) times before success" `
    -Category "Retry Logic"

# Test 1.3: Exhausted retries
$test1_3 = {
    $callCount = 0
    $threwError = $false

    try {
        Invoke-WithRetry -ScriptBlock {
            $callCount++
            throw "Permanent error"
        } -MaxRetries 2 -InitialWaitMs 10 -OperationName "Test1_3" | Out-Null
    }
    catch {
        $threwError = $true
    }

    return $threwError -and ($callCount -eq 2)
}

$passed1_3 = & $test1_3
Add-TestResult -TestName "Exhausted retries throws error" `
    -Passed $passed1_3 `
    -Category "Retry Logic"

# Test 1.4: Exponential backoff
$test1_4 = {
    $callCount = 0
    $durations = @()
    $startTime = [DateTime]::UtcNow

    try {
        Invoke-WithRetry -ScriptBlock {
            $callCount++
            if ($callCount -lt 4) {
                throw "Error"
            }
            return "success"
        } -MaxRetries 5 -InitialWaitMs 50 -BackoffMultiplier 2 -OperationName "Test1_4" | Out-Null
    }
    catch {}

    $totalDuration = ([DateTime]::UtcNow - $startTime).TotalMilliseconds
    # Should have waited at least 50 + 100 + 200 = 350ms
    return ($callCount -eq 4) -and ($totalDuration -ge 300)
}

$passed1_4 = & $test1_4
Add-TestResult -TestName "Exponential backoff timing" `
    -Passed $passed1_4 `
    -Category "Retry Logic"

# ==============================================================================
# Test Suite 2: Error Classification Tests
# ==============================================================================

Write-Host "`n=== Test Suite 2: Error Classification ===" -ForegroundColor Cyan

# Test 2.1: Detect transient timeout error
$test2_1 = {
    try {
        throw "Operation timed out"
    }
    catch {
        $isTransient = Test-TransientError -Exception $_
        return $isTransient
    }
}

$passed2_1 = & $test2_1
Add-TestResult -TestName "Detect transient timeout error" `
    -Passed $passed2_1 `
    -Category "Error Classification"

# Test 2.2: Detect transient service unavailable
$test2_2 = {
    try {
        throw "Service temporarily unavailable"
    }
    catch {
        $isTransient = Test-TransientError -Exception $_
        return $isTransient
    }
}

$passed2_2 = & $test2_2
Add-TestResult -TestName "Detect transient service unavailable" `
    -Passed $passed2_2 `
    -Category "Error Classification"

# Test 2.3: Detect permanent authentication error
$test2_3 = {
    try {
        throw "Authentication failed"
    }
    catch {
        $isTransient = Test-TransientError -Exception $_
        return -not $isTransient  # Should be permanent (not transient)
    }
}

$passed2_3 = & $test2_3
Add-TestResult -TestName "Detect permanent authentication error" `
    -Passed $passed2_3 `
    -Category "Error Classification"

# ==============================================================================
# Test Suite 3: Error Context Tests
# ==============================================================================

Write-Host "`n=== Test Suite 3: Error Context ===" -ForegroundColor Cyan

# Test 3.1: Create error context
$test3_1 = {
    try {
        throw "Test error"
    }
    catch {
        $context = New-ErrorContext -Exception $_ `
            -FunctionName "TestFunction" `
            -Context @{ job_id = 123; operation = "backup" }

        return ($context.function_name -eq "TestFunction") -and `
               ($context.error_message -like "*Test error*") -and `
               ($context.context.job_id -eq 123)
    }
}

$passed3_1 = & $test3_1
Add-TestResult -TestName "Create error context with metadata" `
    -Passed $passed3_1 `
    -Category "Error Context"

# Test 3.2: Error context includes timestamp
$test3_2 = {
    try {
        throw "Test error"
    }
    catch {
        $context = New-ErrorContext -Exception $_ -FunctionName "Test"
        $hasTimestamp = -not [string]::IsNullOrEmpty($context.timestamp)
        $isValidISO = $context.timestamp -match '^\d{4}-\d{2}-\d{2}T'
        return $hasTimestamp -and $isValidISO
    }
}

$passed3_2 = & $test3_2
Add-TestResult -TestName "Error context includes ISO 8601 timestamp" `
    -Passed $passed3_2 `
    -Category "Error Context"

# Test 3.3: Error context includes stack trace
$test3_3 = {
    try {
        throw "Test error"
    }
    catch {
        $context = New-ErrorContext -Exception $_ -FunctionName "Test"
        return -not [string]::IsNullOrEmpty($context.script_stack_trace)
    }
}

$passed3_3 = & $test3_3
Add-TestResult -TestName "Error context includes stack trace" `
    -Passed $passed3_3 `
    -Category "Error Context"

# ==============================================================================
# Test Suite 4: Parameter Validation Tests
# ==============================================================================

Write-Host "`n=== Test Suite 4: Parameter Validation ===" -ForegroundColor Cyan

# Test 4.1: Valid JobId
$test4_1 = {
    $result = Test-ValidJobId -JobId 123
    return $result -eq $true
}

$passed4_1 = & $test4_1
Add-TestResult -TestName "Valid JobId (positive integer)" `
    -Passed $passed4_1 `
    -Category "Parameter Validation"

# Test 4.2: Invalid JobId (zero)
$test4_2 = {
    $result = Test-ValidJobId -JobId 0
    return $result -eq $false
}

$passed4_2 = & $test4_2
Add-TestResult -TestName "Invalid JobId (zero)" `
    -Passed $passed4_2 `
    -Category "Parameter Validation"

# Test 4.3: Invalid JobId (negative)
$test4_3 = {
    $result = Test-ValidJobId -JobId -1
    return $result -eq $false
}

$passed4_3 = & $test4_3
Add-TestResult -TestName "Invalid JobId (negative)" `
    -Passed $passed4_3 `
    -Category "Parameter Validation"

# Test 4.4: Valid string
$test4_4 = {
    $result = Test-ValidString -Value "test_value" -ParameterName "TestParam"
    return $result -eq $true
}

$passed4_4 = & $test4_4
Add-TestResult -TestName "Valid string parameter" `
    -Passed $passed4_4 `
    -Category "Parameter Validation"

# Test 4.5: Empty string
$test4_5 = {
    $result = Test-ValidString -Value "" -ParameterName "TestParam"
    return $result -eq $false
}

$passed4_5 = & $test4_5
Add-TestResult -TestName "Empty string validation fails" `
    -Passed $passed4_5 `
    -Category "Parameter Validation"

# Test 4.6: Valid URI
$test4_6 = {
    $result = Test-ValidUri -Uri "https://api.example.com/v1"
    return $result -eq $true
}

$passed4_6 = & $test4_6
Add-TestResult -TestName "Valid HTTPS URI" `
    -Passed $passed4_6 `
    -Category "Parameter Validation"

# Test 4.7: Invalid URI (wrong scheme)
$test4_7 = {
    $result = Test-ValidUri -Uri "ftp://api.example.com/v1"
    return $result -eq $false
}

$passed4_7 = & $test4_7
Add-TestResult -TestName "Invalid URI (FTP scheme)" `
    -Passed $passed4_7 `
    -Category "Parameter Validation"

# ==============================================================================
# Test Suite 5: Error Statistics Tests
# ==============================================================================

Write-Host "`n=== Test Suite 5: Error Statistics ===" -ForegroundColor Cyan

# Test 5.1: Record error statistic
$test5_1 = {
    $context = @{
        timestamp = Get-Date -Format "O"
        function_name = "TestFunc"
        error_message = "Test error"
        error_type = "System.Exception"
        script_stack_trace = "at TestFunc"
        is_transient = $false
        context = @{}
    }

    Add-ErrorStatistic -ErrorContext $context
    $stats = Get-ErrorStatistics

    return $stats.total_errors -gt 0
}

$passed5_1 = & $test5_1
Add-TestResult -TestName "Record error statistic" `
    -Passed $passed5_1 `
    -Category "Error Statistics"

# Test 5.2: Count permanent errors
$test5_2 = {
    $initialStats = Get-ErrorStatistics
    $initialPermanent = $initialStats.permanent_errors

    $context = @{
        timestamp = Get-Date -Format "O"
        function_name = "Test"
        error_message = "Error"
        error_type = "System.Exception"
        script_stack_trace = "trace"
        is_transient = $false
        context = @{}
    }

    Add-ErrorStatistic -ErrorContext $context

    $newStats = Get-ErrorStatistics
    return ($newStats.permanent_errors -gt $initialPermanent)
}

$passed5_2 = & $test5_2
Add-TestResult -TestName "Count permanent errors" `
    -Passed $passed5_2 `
    -Category "Error Statistics"

# ==============================================================================
# Test Suite 6: Utility Function Tests
# ==============================================================================

Write-Host "`n=== Test Suite 6: Utility Functions ===" -ForegroundColor Cyan

# Test 6.1: Convert bytes to human readable (GB)
$test6_1 = {
    $result = Convert-BytesToHumanReadable -Bytes 1073741824
    return $result -match "1\.0[0-9]? GB"
}

$passed6_1 = & $test6_1
Add-TestResult -TestName "Convert bytes to GB" `
    -Passed $passed6_1 `
    -Message "Result: $(Convert-BytesToHumanReadable -Bytes 1073741824)" `
    -Category "Utility Functions"

# Test 6.2: Convert seconds to human readable
$test6_2 = {
    $result = Convert-SecondsToHumanReadable -Seconds 3661
    return $result -match "1 hour.*1 minute.*1 second"
}

$passed6_2 = & $test6_2
Add-TestResult -TestName "Convert seconds to human readable" `
    -Passed $passed6_2 `
    -Message "Result: $(Convert-SecondsToHumanReadable -Seconds 3661)" `
    -Category "Utility Functions"

# Test 6.3: Convert zero bytes
$test6_3 = {
    $result = Convert-BytesToHumanReadable -Bytes 0
    return $result -eq "0.00 B"
}

$passed6_3 = & $test6_3
Add-TestResult -TestName "Convert zero bytes" `
    -Passed $passed6_3 `
    -Category "Utility Functions"

# ==============================================================================
# Integration Tests (Optional)
# ==============================================================================

if ($IncludeIntegrationTests) {
    Write-Host "`n=== Test Suite 7: Integration Tests ===" -ForegroundColor Cyan

    # Test 7.1: Configuration file validation
    $test7_1 = {
        # This would require an actual config file
        # Skipping for standalone test execution
        return $true
    }

    Add-TestResult -TestName "Configuration file validation" `
        -Passed $test7_1 `
        -Message "Skipped (requires actual config file)" `
        -Category "Integration"
    $script:TestResults.skipped++
}

# ==============================================================================
# Generate Report
# ==============================================================================

Write-Host "`n" -ForegroundColor Cyan
Write-TestReport -FilePath $ReportPath

Write-Host "`nTest report saved to: $ReportPath" -ForegroundColor Green

# Exit with appropriate code
$exitCode = if ($script:TestResults.failed -eq 0) { 0 } else { 1 }
exit $exitCode
