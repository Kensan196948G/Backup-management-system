================================================================================
ERROR HANDLING TEST REPORT
================================================================================
Execution Time: 2025-10-31 18:25:42

SUMMARY
-------
Total Tests:  22
Passed:       18
Failed:       4
Skipped:      0
Pass Rate:    81.82%

DETAILS
-------

[Error Classification]

  PASS : Detect transient timeout error
  PASS : Detect transient service unavailable
  PASS : Detect permanent authentication error

[Error Context]

  PASS : Create error context with metadata
  PASS : Error context includes ISO 8601 timestamp
  PASS : Error context includes stack trace

[Error Statistics]

  PASS : Record error statistic
  PASS : Count permanent errors

[Parameter Validation]

  PASS : Valid JobId (positive integer)
  PASS : Invalid JobId (zero)
  PASS : Invalid JobId (negative)
  PASS : Valid string parameter
  PASS : Empty string validation fails
  PASS : Valid HTTPS URI
  PASS : Invalid URI (FTP scheme)

[Retry Logic]

  FAIL : Successful invocation (no retry needed)
  FAIL : Retry on transient error (eventual success) - Retried  times before success
  FAIL : Exhausted retries throws error
  FAIL : Exponential backoff timing

[Utility Functions]

  PASS : Convert bytes to GB - Result: 1.00 GB
  PASS : Convert seconds to human readable - Result: 1 hour 1 minute 1 second
  PASS : Convert zero bytes

================================================================================
Report generated: 2025-10-31 18:25:42
================================================================================
