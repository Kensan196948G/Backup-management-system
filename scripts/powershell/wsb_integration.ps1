# ==============================================================================
# Backup Management System - Windows Server Backup Integration
# PowerShell 5.1+ Compatible
# ==============================================================================

<#
.SYNOPSIS
    Windows Server Backupとの連携スクリプト
.DESCRIPTION
    Windows Server Backupのジョブ実行履歴を取得し、ステータスを
    バックアップ管理システムのREST APIに送信する
.NOTES
    - Windows Server Backup機能が必要
    - 管理者権限で実行
    - タスクスケジューラーから定期実行
#>

param(
    [Parameter(Mandatory = $false)]
    [int]$JobId = 0,

    [Parameter(Mandatory = $false)]
    [string]$BackupPolicy = "",

    [Parameter(Mandatory = $false)]
    [switch]$TestMode,

    [Parameter(Mandatory = $false)]
    [switch]$CheckLatest
)

# 共通関数のインポート
$commonFunctionsPath = Join-Path $PSScriptRoot "common_functions.ps1"
if (-not (Test-Path $commonFunctionsPath)) {
    Write-Error "共通関数モジュールが見つかりません: $commonFunctionsPath"
    exit 1
}

. $commonFunctionsPath

# ==============================================================================
# Windows Server Backup モジュール読み込み
# ==============================================================================

function Import-WSBModule {
    [CmdletBinding()]
    param()

    try {
        Write-BackupLog -Level "INFO" -Message "Windows Server Backupモジュールを確認中..."

        # Windows Server Backup コマンドレットの確認
        if (-not (Get-Command Get-WBJob -ErrorAction SilentlyContinue)) {
            throw "Windows Server Backup機能が利用できません。WindowsにWindows Server Backup機能がインストールされているか確認してください。"
        }

        Write-BackupLog -Level "INFO" -Message "Windows Server Backup機能が利用可能です"
        return $true
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "Windows Server Backup機能の確認に失敗: $_"
        return $false
    }
}

# ==============================================================================
# Windows Server Backup ジョブ情報取得
# ==============================================================================

<#
.SYNOPSIS
    Windows Server Backupの最新ジョブ情報を取得する
.RETURNS
    ジョブ情報オブジェクト
#>
function Get-WSBJobInfo {
    [CmdletBinding()]
    param()

    try {
        Write-BackupLog -Level "INFO" -Message "Windows Server Backupジョブ情報を取得中..."

        # 最新のジョブを取得
        $jobs = Get-WBJob -Previous 1 -ErrorAction Stop

        if (-not $jobs -or $jobs.Count -eq 0) {
            throw "バックアップジョブが見つかりませんでした"
        }

        $latestJob = $jobs[0]

        # ジョブステータスの変換
        $status = switch ($latestJob.JobState) {
            "Completed"  { "success" }
            "Failed"     { "failed" }
            "Stopped"    { "failed" }
            "Running"    { "warning" }  # 実行中の場合は警告
            default      { "failed" }
        }

        # ハッシュテーブル形式でエラー詳細を取得
        $errorMessage = ""
        if ($latestJob.JobState -ne "Completed") {
            $errorMessage = "ジョブステータス: $($latestJob.JobState)"
            if ($latestJob.ErrorDescription) {
                $errorMessage += " | エラー: $($latestJob.ErrorDescription)"
            }
        }

        # バックアップサイズの取得
        $backupSize = 0
        if ($latestJob.BytesTransferred) {
            $backupSize = $latestJob.BytesTransferred
        }

        # 実行時間の計算
        $duration = 0
        if ($latestJob.StartTime -and $latestJob.EndTime) {
            $duration = [int]($latestJob.EndTime - $latestJob.StartTime).TotalSeconds
        }

        # バックアップターゲットの取得
        $targetVolume = "Unknown"
        if ($latestJob.CurrentOperation) {
            $targetVolume = $latestJob.CurrentOperation
        }

        $jobInfo = @{
            JobType = $latestJob.JobType
            JobState = $latestJob.JobState
            Status = $status
            StartTime = $latestJob.StartTime
            EndTime = $latestJob.EndTime
            Duration = $duration
            BackupSize = $backupSize
            ErrorMessage = $errorMessage
            TargetVolume = $targetVolume
            HResult = $latestJob.HResult
        }

        Write-BackupLog -Level "INFO" -Message "WSBジョブ情報取得成功: Status=$status, Size=$(Convert-BytesToHumanReadable $backupSize), Duration=$(Convert-SecondsToHumanReadable $duration)"

        return $jobInfo
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "WSBジョブ情報の取得に失敗: $_"
        throw
    }
}

<#
.SYNOPSIS
    Windows Server Backupのジョブ履歴を取得する
.PARAMETER Count
    取得するジョブ数
.RETURNS
    ジョブ情報配列
#>
function Get-WSBJobHistory {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [int]$Count = 10
    )

    try {
        Write-BackupLog -Level "INFO" -Message "WSBジョブ履歴を取得中... (最大$Count件)"

        $jobs = Get-WBJob -Previous $Count -ErrorAction Stop

        $jobHistory = @()

        foreach ($job in $jobs) {
            $status = switch ($job.JobState) {
                "Completed"  { "success" }
                "Failed"     { "failed" }
                "Stopped"    { "failed" }
                "Running"    { "running" }
                default      { "unknown" }
            }

            $backupSize = 0
            if ($job.BytesTransferred) {
                $backupSize = $job.BytesTransferred
            }

            $duration = 0
            if ($job.StartTime -and $job.EndTime) {
                $duration = [int]($job.EndTime - $job.StartTime).TotalSeconds
            }

            $jobHistory += @{
                JobType = $job.JobType
                JobState = $job.JobState
                Status = $status
                StartTime = $job.StartTime
                EndTime = $job.EndTime
                Duration = $duration
                BackupSize = $backupSize
                HResult = $job.HResult
            }
        }

        Write-BackupLog -Level "INFO" -Message "WSBジョブ履歴取得成功: $($jobHistory.Count)件"
        return $jobHistory
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "WSBジョブ履歴の取得に失敗: $_"
        throw
    }
}

<#
.SYNOPSIS
    Windows Server Backupの設定情報を取得する
.RETURNS
    バックアップポリシー情報
#>
function Get-WSBPolicyInfo {
    [CmdletBinding()]
    param()

    try {
        Write-BackupLog -Level "INFO" -Message "WSBバックアップポリシーを取得中..."

        $policy = Get-WBPolicy -ErrorAction Stop

        if (-not $policy) {
            Write-BackupLog -Level "WARNING" -Message "バックアップポリシーが設定されていません"
            return $null
        }

        # スケジュール情報
        $schedule = Get-WBSchedule -Policy $policy

        # バックアップターゲット
        $targets = Get-WBBackupTarget -Policy $policy

        $policyInfo = @{
            Schedule = $schedule
            Targets = $targets
            VolumesToBackup = $policy.VolumesToBackup
        }

        Write-BackupLog -Level "INFO" -Message "WSBポリシー情報取得成功"
        return $policyInfo
    }
    catch {
        Write-BackupLog -Level "WARNING" -Message "WSBポリシー情報の取得に失敗: $_"
        return $null
    }
}

# ==============================================================================
# ステータス送信
# ==============================================================================

<#
.SYNOPSIS
    WSBジョブステータスをバックアップ管理システムに送信する
.PARAMETER JobId
    バックアップ管理システムのジョブID
.PARAMETER JobInfo
    WSBジョブ情報
#>
function Send-WSBJobStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$JobId,

        [Parameter(Mandatory = $true)]
        [hashtable]$JobInfo
    )

    try {
        Write-BackupLog -Level "INFO" -Message "WSBジョブステータスを送信中..." -JobId $JobId

        # バックアップステータスの送信
        $result = Send-BackupStatus `
            -JobId $JobId `
            -Status $JobInfo.Status `
            -BackupSize $JobInfo.BackupSize `
            -Duration $JobInfo.Duration `
            -ErrorMessage $JobInfo.ErrorMessage

        Write-BackupLog -Level "INFO" -Message "WSBジョブステータス送信成功" -JobId $JobId

        # 実行記録の送信
        if ($JobInfo.StartTime -and $JobInfo.EndTime) {
            $details = "WSB JobType: $($JobInfo.JobType) | State: $($JobInfo.JobState) | Target: $($JobInfo.TargetVolume)"

            Send-BackupExecution `
                -JobId $JobId `
                -StartTime $JobInfo.StartTime `
                -EndTime $JobInfo.EndTime `
                -Status $JobInfo.Status `
                -BackupSize $JobInfo.BackupSize `
                -Details $details

            Write-BackupLog -Level "INFO" -Message "WSB実行記録送信成功" -JobId $JobId
        }

        return $result
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "WSBジョブステータス送信に失敗: $_" -JobId $JobId
        throw
    }
}

# ==============================================================================
# テストモード
# ==============================================================================

function Test-WSBIntegration {
    [CmdletBinding()]
    param()

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Windows Server Backup統合スクリプト テストモード" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    try {
        # 設定ファイルの読み込みテスト
        Write-Host "1. 設定ファイル読み込みテスト..." -ForegroundColor Yellow
        $config = Get-BackupSystemConfig
        Write-Host "   ✓ 成功: API URL = $($config.api_url)" -ForegroundColor Green

        # WSB モジュール確認テスト
        Write-Host "`n2. Windows Server Backup機能確認テスト..." -ForegroundColor Yellow
        if (Import-WSBModule) {
            Write-Host "   ✓ 成功: Windows Server Backup機能が利用可能" -ForegroundColor Green

            # ポリシー情報の取得
            Write-Host "`n3. バックアップポリシー取得..." -ForegroundColor Yellow
            $policy = Get-WSBPolicyInfo
            if ($policy) {
                Write-Host "   ✓ 成功: バックアップポリシーが設定されています" -ForegroundColor Green
                if ($policy.Schedule) {
                    Write-Host "      スケジュール: $($policy.Schedule -join ', ')" -ForegroundColor Gray
                }
            }
            else {
                Write-Host "   ⚠ 警告: バックアップポリシーが設定されていません" -ForegroundColor Yellow
            }

            # ジョブ履歴の取得
            Write-Host "`n4. ジョブ履歴取得..." -ForegroundColor Yellow
            $jobs = Get-WSBJobHistory -Count 5
            if ($jobs -and $jobs.Count -gt 0) {
                Write-Host "   ✓ 成功: $($jobs.Count)件のジョブ履歴が見つかりました" -ForegroundColor Green
                foreach ($job in $jobs) {
                    $statusColor = switch ($job.Status) {
                        "success" { "Green" }
                        "failed"  { "Red" }
                        default   { "Yellow" }
                    }
                    Write-Host "      [$($job.StartTime)] $($job.JobType) - $($job.Status)" -ForegroundColor $statusColor
                }
            }
            else {
                Write-Host "   ⚠ 警告: ジョブ履歴が見つかりませんでした" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "   ✗ 失敗: Windows Server Backup機能が利用できません" -ForegroundColor Red
            Write-Host "   Windows Server Backup機能がインストールされていない可能性があります" -ForegroundColor Yellow
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
        Write-BackupLog -Level "INFO" -Message "===== Windows Server Backup統合スクリプト開始 ====="

        # テストモード
        if ($TestMode) {
            Test-WSBIntegration
            return
        }

        # パラメータチェック
        if ($JobId -eq 0) {
            throw "JobIdを指定してください"
        }

        # 設定ファイルの読み込み
        $config = Get-BackupSystemConfig

        # WSB モジュールの確認
        if (-not (Import-WSBModule)) {
            throw "Windows Server Backup機能が利用できません"
        }

        # 最新ジョブ情報の取得
        $jobInfo = Get-WSBJobInfo

        # ステータス送信
        Send-WSBJobStatus -JobId $JobId -JobInfo $jobInfo

        Write-BackupLog -Level "INFO" -Message "===== Windows Server Backup統合スクリプト正常終了 ====="
        exit 0
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "Windows Server Backup統合スクリプトでエラーが発生: $_"
        Write-BackupLog -Level "ERROR" -Message "スタックトレース: $($_.ScriptStackTrace)"
        exit 1
    }
}

# スクリプト実行
Main
