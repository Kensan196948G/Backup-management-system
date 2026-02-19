# ==============================================================================
# Backup Management System - Common Functions Module
# PowerShell 5.1+ Compatible
# ==============================================================================

# グローバル変数
$script:ConfigPath = Join-Path $PSScriptRoot "config.json"
$script:LogPath = Join-Path $PSScriptRoot "logs"
$script:Config = $null

# ==============================================================================
# 設定ファイル管理
# ==============================================================================

<#
.SYNOPSIS
    設定ファイルを読み込む
.DESCRIPTION
    config.jsonファイルを読み込み、グローバル変数に格納する
.EXAMPLE
    $config = Get-BackupSystemConfig
#>
function Get-BackupSystemConfig {
    [CmdletBinding()]
    param()

    try {
        if (-not (Test-Path $script:ConfigPath)) {
            throw "設定ファイルが見つかりません: $script:ConfigPath"
        }

        $configContent = Get-Content $script:ConfigPath -Raw -Encoding UTF8
        $script:Config = $configContent | ConvertFrom-Json

        # 必須項目の検証
        if (-not $script:Config.api_url) {
            throw "設定ファイルにapi_urlが定義されていません"
        }

        Write-BackupLog -Level "INFO" -Message "設定ファイルを読み込みました: $script:ConfigPath"
        return $script:Config
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "設定ファイルの読み込みに失敗: $_"
        throw
    }
}

<#
.SYNOPSIS
    設定ファイルを保存する
.DESCRIPTION
    設定オブジェクトをJSON形式で保存する
.PARAMETER Config
    保存する設定オブジェクト
.EXAMPLE
    Save-BackupSystemConfig -Config $config
#>
function Save-BackupSystemConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Config
    )

    try {
        $Config | ConvertTo-Json -Depth 10 | Set-Content $script:ConfigPath -Encoding UTF8
        Write-BackupLog -Level "INFO" -Message "設定ファイルを保存しました: $script:ConfigPath"
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "設定ファイルの保存に失敗: $_"
        throw
    }
}

# ==============================================================================
# ログ記録機能
# ==============================================================================

<#
.SYNOPSIS
    ログメッセージを記録する
.DESCRIPTION
    ログファイルとWindowsイベントログにメッセージを記録する
.PARAMETER Level
    ログレベル (INFO, WARNING, ERROR)
.PARAMETER Message
    ログメッセージ
.PARAMETER JobId
    バックアップジョブID (オプション)
.EXAMPLE
    Write-BackupLog -Level "INFO" -Message "バックアップ開始" -JobId 1
#>
function Write-BackupLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("INFO", "WARNING", "ERROR")]
        [string]$Level,

        [Parameter(Mandatory = $true)]
        [string]$Message,

        [Parameter(Mandatory = $false)]
        [int]$JobId
    )

    try {
        # ログディレクトリの作成
        if (-not (Test-Path $script:LogPath)) {
            New-Item -ItemType Directory -Path $script:LogPath -Force | Out-Null
        }

        # ログファイル名（日付ごと）
        $logFile = Join-Path $script:LogPath "backup_integration_$(Get-Date -Format 'yyyyMMdd').log"

        # タイムスタンプ付きメッセージ
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $jobIdText = if ($JobId) { " [JobID:$JobId]" } else { "" }
        $logMessage = "[$timestamp] [$Level]$jobIdText $Message"

        # ファイルに追記
        Add-Content -Path $logFile -Value $logMessage -Encoding UTF8

        # コンソールにも出力
        switch ($Level) {
            "ERROR"   { Write-Host $logMessage -ForegroundColor Red }
            "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
            "INFO"    { Write-Host $logMessage -ForegroundColor Green }
        }

        # Windowsイベントログに記録（エラーと警告のみ）
        if ($Level -in @("ERROR", "WARNING")) {
            try {
                $eventType = switch ($Level) {
                    "ERROR"   { "Error" }
                    "WARNING" { "Warning" }
                }

                # イベントソースの確認・作成
                $sourceName = "BackupManagementSystem"
                if (-not [System.Diagnostics.EventLog]::SourceExists($sourceName)) {
                    New-EventLog -LogName Application -Source $sourceName
                }

                Write-EventLog -LogName Application -Source $sourceName `
                    -EventId 1000 -EntryType $eventType -Message $logMessage
            }
            catch {
                # イベントログ書き込みエラーは無視（権限不足の可能性）
                Write-Host "イベントログへの書き込みに失敗: $_" -ForegroundColor Yellow
            }
        }
    }
    catch {
        Write-Host "ログ記録に失敗: $_" -ForegroundColor Red
    }
}

# ==============================================================================
# REST API 通信機能
# ==============================================================================

<#
.SYNOPSIS
    バックアップステータスをREST APIに送信する
.DESCRIPTION
    バックアップジョブの実行結果をREST API経由でバックアップ管理システムに送信する
.PARAMETER JobId
    バックアップジョブID
.PARAMETER Status
    ステータス (success, failed, warning)
.PARAMETER BackupSize
    バックアップサイズ（バイト）
.PARAMETER Duration
    実行時間（秒）
.PARAMETER ErrorMessage
    エラーメッセージ（オプション）
.EXAMPLE
    Send-BackupStatus -JobId 1 -Status "success" -BackupSize 1073741824 -Duration 300
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
        # 設定読み込み
        if (-not $script:Config) {
            Get-BackupSystemConfig | Out-Null
        }

        $apiUrl = $script:Config.api_url.TrimEnd('/') + "/api/backup/update-status"

        # リクエストボディの作成
        $body = @{
            job_id = $JobId
            status = $Status
            backup_size = $BackupSize
            duration_seconds = $Duration
        }

        if ($ErrorMessage) {
            $body["error_message"] = $ErrorMessage
        }

        $jsonBody = $body | ConvertTo-Json

        # HTTPヘッダーの設定
        $headers = @{
            "Content-Type" = "application/json"
        }

        # API トークンの追加
        if ($script:Config.api_token) {
            $headers["Authorization"] = "Bearer $($script:Config.api_token)"
        }

        Write-BackupLog -Level "INFO" -Message "ステータスをAPIに送信: JobID=$JobId, Status=$Status" -JobId $JobId

        # REST API 呼び出し
        $response = Invoke-RestMethod -Uri $apiUrl -Method Post `
            -Headers $headers -Body $jsonBody -ContentType "application/json" `
            -ErrorAction Stop

        Write-BackupLog -Level "INFO" -Message "API送信成功: $($response | ConvertTo-Json -Compress)" -JobId $JobId
        return $response
    }
    catch {
        $errorMsg = "API送信失敗: $($_.Exception.Message)"
        Write-BackupLog -Level "ERROR" -Message $errorMsg -JobId $JobId

        # 詳細なエラー情報
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-BackupLog -Level "ERROR" -Message "APIレスポンス: $responseBody" -JobId $JobId
        }

        throw
    }
}

<#
.SYNOPSIS
    バックアップコピーステータスをREST APIに送信する
.DESCRIPTION
    バックアップコピー（オフサイト転送）の実行結果を送信する
.PARAMETER JobId
    バックアップジョブID
.PARAMETER Status
    ステータス (success, failed, warning)
.PARAMETER CopySize
    コピーサイズ（バイト）
.PARAMETER Duration
    実行時間（秒）
.PARAMETER ErrorMessage
    エラーメッセージ（オプション）
.EXAMPLE
    Send-BackupCopyStatus -JobId 1 -Status "success" -CopySize 1073741824 -Duration 600
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
        # 設定読み込み
        if (-not $script:Config) {
            Get-BackupSystemConfig | Out-Null
        }

        $apiUrl = $script:Config.api_url.TrimEnd('/') + "/api/backup/update-copy-status"

        # リクエストボディの作成
        $body = @{
            job_id = $JobId
            status = $Status
            copy_size = $CopySize
            duration_seconds = $Duration
        }

        if ($ErrorMessage) {
            $body["error_message"] = $ErrorMessage
        }

        $jsonBody = $body | ConvertTo-Json

        # HTTPヘッダーの設定
        $headers = @{
            "Content-Type" = "application/json"
        }

        if ($script:Config.api_token) {
            $headers["Authorization"] = "Bearer $($script:Config.api_token)"
        }

        Write-BackupLog -Level "INFO" -Message "コピーステータスをAPIに送信: JobID=$JobId, Status=$Status" -JobId $JobId

        # REST API 呼び出し
        $response = Invoke-RestMethod -Uri $apiUrl -Method Post `
            -Headers $headers -Body $jsonBody -ContentType "application/json" `
            -ErrorAction Stop

        Write-BackupLog -Level "INFO" -Message "コピーステータスAPI送信成功" -JobId $JobId
        return $response
    }
    catch {
        $errorMsg = "コピーステータスAPI送信失敗: $($_.Exception.Message)"
        Write-BackupLog -Level "ERROR" -Message $errorMsg -JobId $JobId
        throw
    }
}

<#
.SYNOPSIS
    バックアップ実行記録をREST APIに送信する
.DESCRIPTION
    バックアップの実行記録を詳細情報とともに送信する
.PARAMETER JobId
    バックアップジョブID
.PARAMETER StartTime
    開始時刻
.PARAMETER EndTime
    終了時刻
.PARAMETER Status
    ステータス
.PARAMETER BackupSize
    バックアップサイズ（バイト）
.PARAMETER Details
    詳細情報（オプション）
.EXAMPLE
    Send-BackupExecution -JobId 1 -StartTime $start -EndTime $end -Status "success" -BackupSize 1073741824
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
        if (-not $script:Config) {
            Get-BackupSystemConfig | Out-Null
        }

        $apiUrl = $script:Config.api_url.TrimEnd('/') + "/api/backup/record-execution"

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

        Write-BackupLog -Level "INFO" -Message "実行記録をAPIに送信: JobID=$JobId" -JobId $JobId

        $response = Invoke-RestMethod -Uri $apiUrl -Method Post `
            -Headers $headers -Body $jsonBody -ContentType "application/json" `
            -ErrorAction Stop

        Write-BackupLog -Level "INFO" -Message "実行記録API送信成功" -JobId $JobId
        return $response
    }
    catch {
        $errorMsg = "実行記録API送信失敗: $($_.Exception.Message)"
        Write-BackupLog -Level "ERROR" -Message $errorMsg -JobId $JobId
        throw
    }
}

# ==============================================================================
# ユーティリティ関数
# ==============================================================================

<#
.SYNOPSIS
    バイト数を人間が読みやすい形式に変換する
.DESCRIPTION
    バイト数をKB, MB, GB, TBなどの単位に変換する
.PARAMETER Bytes
    バイト数
.EXAMPLE
    Convert-BytesToHumanReadable -Bytes 1073741824
    # 出力: "1.00 GB"
#>
function Convert-BytesToHumanReadable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
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
    時間スパンを人間が読みやすい形式に変換する
.DESCRIPTION
    時間スパンを時間、分、秒の形式に変換する
.PARAMETER Seconds
    秒数
.EXAMPLE
    Convert-SecondsToHumanReadable -Seconds 3661
    # 出力: "1時間 1分 1秒"
#>
function Convert-SecondsToHumanReadable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$Seconds
    )

    $timeSpan = [TimeSpan]::FromSeconds($Seconds)

    $parts = @()
    if ($timeSpan.Hours -gt 0) { $parts += "$($timeSpan.Hours)時間" }
    if ($timeSpan.Minutes -gt 0) { $parts += "$($timeSpan.Minutes)分" }
    if ($timeSpan.Seconds -gt 0 -or $parts.Count -eq 0) { $parts += "$($timeSpan.Seconds)秒" }

    return $parts -join " "
}

<#
.SYNOPSIS
    ジョブIDに対応する設定を取得する
.DESCRIPTION
    設定ファイルから指定されたジョブIDの設定を取得する
.PARAMETER JobId
    バックアップジョブID
.EXAMPLE
    $jobConfig = Get-JobConfig -JobId 1
#>
function Get-JobConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$JobId
    )

    try {
        if (-not $script:Config) {
            Get-BackupSystemConfig | Out-Null
        }

        # 各バックアップツールの設定を検索
        foreach ($tool in $script:Config.backup_tools.PSObject.Properties) {
            if ($tool.Value.enabled -and $tool.Value.job_ids -contains $JobId) {
                return @{
                    tool_name = $tool.Name
                    job_id = $JobId
                    enabled = $tool.Value.enabled
                }
            }
        }

        Write-BackupLog -Level "WARNING" -Message "ジョブID $JobId の設定が見つかりません" -JobId $JobId
        return $null
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "ジョブ設定の取得に失敗: $_" -JobId $JobId
        throw
    }
}

# ==============================================================================
# モジュールのエクスポート
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
    'Get-JobConfig'
)
