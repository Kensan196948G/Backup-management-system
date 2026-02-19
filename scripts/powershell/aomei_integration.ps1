# ==============================================================================
# Backup Management System - AOMEI Backupper Integration
# PowerShell 5.1+ Compatible
# ==============================================================================

<#
.SYNOPSIS
    AOMEI Backupperとの連携スクリプト
.DESCRIPTION
    AOMEI Backupperのログファイルを監視・解析し、バックアップステータスを
    バックアップ管理システムのREST APIに送信する
.NOTES
    - AOMEI Backupper がインストールされている必要がある
    - ログファイルへのアクセス権限が必要
    - タスクスケジューラーから定期実行
#>

param(
    [Parameter(Mandatory = $false)]
    [int]$JobId = 0,

    [Parameter(Mandatory = $false)]
    [string]$TaskName = "",

    [Parameter(Mandatory = $false)]
    [string]$LogPath = "",

    [Parameter(Mandatory = $false)]
    [switch]$TestMode,

    [Parameter(Mandatory = $false)]
    [switch]$MonitorMode,

    [Parameter(Mandatory = $false)]
    [int]$MonitorIntervalSeconds = 60
)

# 共通関数のインポート
$commonFunctionsPath = Join-Path $PSScriptRoot "common_functions.ps1"
if (-not (Test-Path $commonFunctionsPath)) {
    Write-Error "共通関数モジュールが見つかりません: $commonFunctionsPath"
    exit 1
}

. $commonFunctionsPath

# ==============================================================================
# AOMEI Backupper 設定
# ==============================================================================

# デフォルトのログパス
$script:DefaultLogPaths = @(
    "C:\Program Files (x86)\AOMEI Backupper\log",
    "C:\ProgramData\AOMEI\Backupper\log",
    "$env:LOCALAPPDATA\AOMEI\Backupper\log"
)

# ==============================================================================
# AOMEI ログファイル検索
# ==============================================================================

<#
.SYNOPSIS
    AOMEI Backupperのログディレクトリを検索する
.RETURNS
    ログディレクトリパス
#>
function Find-AOMEILogDirectory {
    [CmdletBinding()]
    param()

    try {
        Write-BackupLog -Level "INFO" -Message "AOMEIログディレクトリを検索中..."

        foreach ($path in $script:DefaultLogPaths) {
            if (Test-Path $path) {
                Write-BackupLog -Level "INFO" -Message "ログディレクトリが見つかりました: $path"
                return $path
            }
        }

        # レジストリから検索
        try {
            $regPath = "HKLM:\SOFTWARE\AOMEI\Backupper"
            if (Test-Path $regPath) {
                $installPath = (Get-ItemProperty -Path $regPath -Name "InstallPath" -ErrorAction SilentlyContinue).InstallPath
                if ($installPath) {
                    $logPath = Join-Path $installPath "log"
                    if (Test-Path $logPath) {
                        Write-BackupLog -Level "INFO" -Message "レジストリからログディレクトリを検出: $logPath"
                        return $logPath
                    }
                }
            }
        }
        catch {
            Write-BackupLog -Level "WARNING" -Message "レジストリからの検索に失敗: $_"
        }

        throw "AOMEIログディレクトリが見つかりませんでした"
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "AOMEIログディレクトリの検索に失敗: $_"
        throw
    }
}

<#
.SYNOPSIS
    指定されたタスク名の最新ログファイルを取得する
.PARAMETER LogDirectory
    ログディレクトリパス
.PARAMETER TaskName
    タスク名
.RETURNS
    ログファイルパス
#>
function Get-AOMEILatestLogFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogDirectory,

        [Parameter(Mandatory = $false)]
        [string]$TaskName = ""
    )

    try {
        Write-BackupLog -Level "INFO" -Message "最新のAOMEIログファイルを検索中..."

        if (-not (Test-Path $LogDirectory)) {
            throw "ログディレクトリが存在しません: $LogDirectory"
        }

        # ログファイルのパターン
        $pattern = if ($TaskName) {
            "*$TaskName*.log"
        }
        else {
            "*.log"
        }

        # 最新のログファイルを取得
        $logFiles = Get-ChildItem -Path $LogDirectory -Filter $pattern -File |
            Sort-Object LastWriteTime -Descending

        if (-not $logFiles -or $logFiles.Count -eq 0) {
            throw "ログファイルが見つかりませんでした: $LogDirectory\$pattern"
        }

        $latestLog = $logFiles[0].FullName
        Write-BackupLog -Level "INFO" -Message "最新ログファイル: $latestLog"

        return $latestLog
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "ログファイルの検索に失敗: $_"
        throw
    }
}

# ==============================================================================
# AOMEI ログ解析
# ==============================================================================

<#
.SYNOPSIS
    AOMEIログファイルを解析してバックアップステータスを取得する
.PARAMETER LogFilePath
    ログファイルパス
.RETURNS
    ジョブ情報オブジェクト
#>
function Get-AOMEIJobInfoFromLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogFilePath
    )

    try {
        Write-BackupLog -Level "INFO" -Message "AOMEIログファイルを解析中: $LogFilePath"

        if (-not (Test-Path $LogFilePath)) {
            throw "ログファイルが存在しません: $LogFilePath"
        }

        # ログファイルを読み込み（UTF-8またはシステムデフォルトエンコーディング）
        $logContent = Get-Content $LogFilePath -Encoding UTF8 -ErrorAction Stop

        # ジョブ情報の初期化
        $jobInfo = @{
            TaskName = [System.IO.Path]::GetFileNameWithoutExtension($LogFilePath)
            Status = "unknown"
            StartTime = $null
            EndTime = $null
            Duration = 0
            BackupSize = 0
            ErrorMessage = ""
            Details = ""
        }

        # ステータス判定パターン
        $successPatterns = @(
            "successfully completed",
            "backup completed successfully",
            "task completed",
            "successfully"
        )

        $failurePatterns = @(
            "failed",
            "error",
            "cannot",
            "unable to"
        )

        $warningPatterns = @(
            "warning",
            "skipped",
            "incomplete"
        )

        # ログを解析
        $status = "unknown"
        $startTime = $null
        $endTime = $null
        $backupSize = 0
        $errorLines = @()

        foreach ($line in $logContent) {
            # 開始時刻の検出
            if ($line -match "^\[?(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})\]?\s+.*start" -or
                $line -match "^\[?(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})\]?\s+Task\s+start") {
                $startTime = [datetime]::ParseExact($Matches[1], "yyyy-MM-dd HH:mm:ss", $null)
            }

            # 終了時刻の検出
            if ($line -match "^\[?(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})\]?\s+.*complet" -or
                $line -match "^\[?(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})\]?\s+.*finish" -or
                $line -match "^\[?(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})\]?\s+Task\s+end") {
                $endTime = [datetime]::ParseExact($Matches[1], "yyyy-MM-dd HH:mm:ss", $null)
            }

            # バックアップサイズの検出
            if ($line -match "(\d+(?:\.\d+)?)\s*(MB|GB|TB)") {
                $size = [double]$Matches[1]
                $unit = $Matches[2]
                $multiplier = switch ($unit) {
                    "MB" { 1MB }
                    "GB" { 1GB }
                    "TB" { 1TB }
                    default { 1 }
                }
                $backupSize = [long]($size * $multiplier)
            }

            # 成功パターンのチェック
            foreach ($pattern in $successPatterns) {
                if ($line -match $pattern) {
                    $status = "success"
                    break
                }
            }

            # 失敗パターンのチェック
            foreach ($pattern in $failurePatterns) {
                if ($line -match $pattern) {
                    $status = "failed"
                    $errorLines += $line.Trim()
                    break
                }
            }

            # 警告パターンのチェック
            if ($status -ne "failed") {
                foreach ($pattern in $warningPatterns) {
                    if ($line -match $pattern) {
                        $status = "warning"
                        $errorLines += $line.Trim()
                        break
                    }
                }
            }
        }

        # デフォルトの時刻設定
        if (-not $startTime) {
            $fileInfo = Get-Item $LogFilePath
            $startTime = $fileInfo.CreationTime
            Write-BackupLog -Level "WARNING" -Message "開始時刻が検出できないため、ファイル作成日時を使用"
        }

        if (-not $endTime) {
            $fileInfo = Get-Item $LogFilePath
            $endTime = $fileInfo.LastWriteTime
            Write-BackupLog -Level "WARNING" -Message "終了時刻が検出できないため、ファイル更新日時を使用"
        }

        # 実行時間の計算
        $duration = 0
        if ($startTime -and $endTime) {
            $duration = [int]($endTime - $startTime).TotalSeconds
        }

        # エラーメッセージの構築
        $errorMessage = if ($errorLines.Count -gt 0) {
            ($errorLines | Select-Object -First 5) -join " | "
        }
        else {
            ""
        }

        # ジョブ情報の更新
        $jobInfo.Status = if ($status -eq "unknown") { "warning" } else { $status }
        $jobInfo.StartTime = $startTime
        $jobInfo.EndTime = $endTime
        $jobInfo.Duration = $duration
        $jobInfo.BackupSize = $backupSize
        $jobInfo.ErrorMessage = $errorMessage
        $jobInfo.Details = "AOMEI Task: $($jobInfo.TaskName) | Log: $([System.IO.Path]::GetFileName($LogFilePath))"

        Write-BackupLog -Level "INFO" -Message "AOMEI解析完了: Status=$($jobInfo.Status), Size=$(Convert-BytesToHumanReadable $jobInfo.BackupSize), Duration=$(Convert-SecondsToHumanReadable $jobInfo.Duration)"

        return $jobInfo
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "AOMEIログ解析に失敗: $_"
        throw
    }
}

# ==============================================================================
# ステータス送信
# ==============================================================================

<#
.SYNOPSIS
    AOMEIジョブステータスをバックアップ管理システムに送信する
.PARAMETER JobId
    バックアップ管理システムのジョブID
.PARAMETER JobInfo
    AOMEIジョブ情報
#>
function Send-AOMEIJobStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$JobId,

        [Parameter(Mandatory = $true)]
        [hashtable]$JobInfo
    )

    try {
        Write-BackupLog -Level "INFO" -Message "AOMEIジョブステータスを送信中..." -JobId $JobId

        # バックアップステータスの送信
        $result = Send-BackupStatus `
            -JobId $JobId `
            -Status $JobInfo.Status `
            -BackupSize $JobInfo.BackupSize `
            -Duration $JobInfo.Duration `
            -ErrorMessage $JobInfo.ErrorMessage

        Write-BackupLog -Level "INFO" -Message "AOMEIジョブステータス送信成功" -JobId $JobId

        # 実行記録の送信
        if ($JobInfo.StartTime -and $JobInfo.EndTime) {
            Send-BackupExecution `
                -JobId $JobId `
                -StartTime $JobInfo.StartTime `
                -EndTime $JobInfo.EndTime `
                -Status $JobInfo.Status `
                -BackupSize $JobInfo.BackupSize `
                -Details $JobInfo.Details

            Write-BackupLog -Level "INFO" -Message "AOMEI実行記録送信成功" -JobId $JobId
        }

        return $result
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "AOMEIジョブステータス送信に失敗: $_" -JobId $JobId
        throw
    }
}

# ==============================================================================
# ログ監視モード
# ==============================================================================

<#
.SYNOPSIS
    AOMEIログファイルを継続的に監視する
.PARAMETER LogDirectory
    ログディレクトリパス
.PARAMETER JobId
    バックアップ管理システムのジョブID
.PARAMETER IntervalSeconds
    監視間隔（秒）
#>
function Start-AOMEILogMonitor {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogDirectory,

        [Parameter(Mandatory = $true)]
        [int]$JobId,

        [Parameter(Mandatory = $false)]
        [int]$IntervalSeconds = 60
    )

    Write-BackupLog -Level "INFO" -Message "AOMEIログ監視モード開始: 監視間隔=${IntervalSeconds}秒" -JobId $JobId

    $lastProcessedFile = ""
    $lastProcessedTime = [DateTime]::MinValue

    while ($true) {
        try {
            # 最新のログファイルを取得
            $latestLog = Get-AOMEILatestLogFile -LogDirectory $LogDirectory

            # 新しいログファイルまたは更新されたログを検出
            $fileInfo = Get-Item $latestLog
            if ($latestLog -ne $lastProcessedFile -or $fileInfo.LastWriteTime -gt $lastProcessedTime) {
                Write-BackupLog -Level "INFO" -Message "新しいログまたは更新を検出: $latestLog" -JobId $JobId

                # ログを解析して送信
                $jobInfo = Get-AOMEIJobInfoFromLog -LogFilePath $latestLog
                Send-AOMEIJobStatus -JobId $JobId -JobInfo $jobInfo

                $lastProcessedFile = $latestLog
                $lastProcessedTime = $fileInfo.LastWriteTime
            }

            # 指定された間隔で待機
            Start-Sleep -Seconds $IntervalSeconds
        }
        catch {
            Write-BackupLog -Level "ERROR" -Message "ログ監視中にエラーが発生: $_" -JobId $JobId
            Start-Sleep -Seconds $IntervalSeconds
        }
    }
}

# ==============================================================================
# テストモード
# ==============================================================================

function Test-AOMEIIntegration {
    [CmdletBinding()]
    param()

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "AOMEI Backupper統合スクリプト テストモード" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    try {
        # 設定ファイルの読み込みテスト
        Write-Host "1. 設定ファイル読み込みテスト..." -ForegroundColor Yellow
        $config = Get-BackupSystemConfig
        Write-Host "   ✓ 成功: API URL = $($config.api_url)" -ForegroundColor Green

        # ログディレクトリ検索テスト
        Write-Host "`n2. AOMEIログディレクトリ検索テスト..." -ForegroundColor Yellow
        try {
            $logDir = Find-AOMEILogDirectory
            Write-Host "   ✓ 成功: ログディレクトリ = $logDir" -ForegroundColor Green

            # ログファイル一覧
            Write-Host "`n3. ログファイル一覧..." -ForegroundColor Yellow
            $logFiles = Get-ChildItem -Path $logDir -Filter "*.log" -File |
                Sort-Object LastWriteTime -Descending | Select-Object -First 5

            if ($logFiles) {
                Write-Host "   ✓ 成功: $($logFiles.Count)個のログファイルが見つかりました" -ForegroundColor Green
                foreach ($file in $logFiles) {
                    Write-Host "      [$($file.LastWriteTime)] $($file.Name)" -ForegroundColor Gray
                }

                # 最新ログの解析テスト
                if ($logFiles.Count -gt 0) {
                    Write-Host "`n4. 最新ログ解析テスト..." -ForegroundColor Yellow
                    $jobInfo = Get-AOMEIJobInfoFromLog -LogFilePath $logFiles[0].FullName
                    Write-Host "   ✓ 成功: ログ解析完了" -ForegroundColor Green
                    Write-Host "      タスク名: $($jobInfo.TaskName)" -ForegroundColor Gray
                    Write-Host "      ステータス: $($jobInfo.Status)" -ForegroundColor Gray
                    Write-Host "      バックアップサイズ: $(Convert-BytesToHumanReadable $jobInfo.BackupSize)" -ForegroundColor Gray
                    Write-Host "      実行時間: $(Convert-SecondsToHumanReadable $jobInfo.Duration)" -ForegroundColor Gray
                }
            }
            else {
                Write-Host "   ⚠ 警告: ログファイルが見つかりませんでした" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "   ✗ 失敗: $_" -ForegroundColor Red
            Write-Host "   AOMEI Backupperがインストールされていない可能性があります" -ForegroundColor Yellow
        }

        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "テスト完了" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Cyan
    }
    catch {
        Write-Host "`n✗ エラー: $_" -ForegroundColor Red
        Write-Host "`nスタックトレース:" -ForegroundColor Yellow
        Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    }
}

# ==============================================================================
# メイン処理
# ==============================================================================

function Main {
    try {
        Write-BackupLog -Level "INFO" -Message "===== AOMEI Backupper統合スクリプト開始 ====="

        # テストモード
        if ($TestMode) {
            Test-AOMEIIntegration
            return
        }

        # パラメータチェック
        if ($JobId -eq 0) {
            throw "JobIdを指定してください"
        }

        # 設定ファイルの読み込み
        $config = Get-BackupSystemConfig

        # ログディレクトリの取得
        $logDirectory = if ($LogPath -and (Test-Path $LogPath)) {
            $LogPath
        }
        else {
            Find-AOMEILogDirectory
        }

        # 監視モード
        if ($MonitorMode) {
            Start-AOMEILogMonitor -LogDirectory $logDirectory -JobId $JobId -IntervalSeconds $MonitorIntervalSeconds
            return
        }

        # 最新ログの取得と解析
        $latestLog = Get-AOMEILatestLogFile -LogDirectory $logDirectory -TaskName $TaskName
        $jobInfo = Get-AOMEIJobInfoFromLog -LogFilePath $latestLog

        # ステータス送信
        Send-AOMEIJobStatus -JobId $JobId -JobInfo $jobInfo

        Write-BackupLog -Level "INFO" -Message "===== AOMEI Backupper統合スクリプト正常終了 ====="
        exit 0
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "AOMEI Backupper統合スクリプトでエラーが発生: $_"
        Write-BackupLog -Level "ERROR" -Message "スタックトレース: $($_.ScriptStackTrace)"
        exit 1
    }
}

# スクリプト実行
Main
