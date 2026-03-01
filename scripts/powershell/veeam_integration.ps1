# ==============================================================================
# Backup Management System - Veeam Backup & Replication Integration
# PowerShell 5.1+ Compatible
# ==============================================================================

<#
.SYNOPSIS
    Veeam Backup & Replicationとの連携スクリプト
.DESCRIPTION
    Veeamバックアップジョブの実行後フックとして動作し、ジョブステータスを
    バックアップ管理システムのREST APIに送信する
.NOTES
    - Veeam PowerShell SnapInが必要
    - 管理者権限で実行
    - Veeamジョブのポストジョブスクリプトとして設定
#>

param(
    [Parameter(Mandatory = $false)]
    [int]$JobId = 0,

    [Parameter(Mandatory = $false)]
    [string]$JobName = "",

    [Parameter(Mandatory = $false)]
    [switch]$TestMode
)

# 共通関数のインポート
$commonFunctionsPath = Join-Path $PSScriptRoot "common_functions.ps1"
if (-not (Test-Path $commonFunctionsPath)) {
    Write-Error "共通関数モジュールが見つかりません: $commonFunctionsPath"
    exit 1
}

. $commonFunctionsPath

# ==============================================================================
# Veeam PowerShell SnapIn 読み込み
# ==============================================================================

function Import-VeeamSnapIn {
    [CmdletBinding()]
    param()

    try {
        if (-not (Get-PSSnapin -Name VeeamPSSnapIn -ErrorAction SilentlyContinue)) {
            Write-BackupLog -Level "INFO" -Message "Veeam PowerShell SnapInを読み込んでいます..."
            Add-PSSnapin -Name VeeamPSSnapIn -ErrorAction Stop
            Write-BackupLog -Level "INFO" -Message "Veeam PowerShell SnapIn読み込み成功"
        }
        return $true
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "Veeam PowerShell SnapInの読み込みに失敗: $_"
        return $false
    }
}

# ==============================================================================
# Veeamジョブ情報取得
# ==============================================================================

<#
.SYNOPSIS
    Veeamバックアップジョブの情報を取得する
.PARAMETER JobName
    ジョブ名
.RETURNS
    ジョブ情報オブジェクト
#>
function Get-VeeamJobInfo {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$JobName
    )

    try {
        Write-BackupLog -Level "INFO" -Message "Veeamジョブ情報を取得中: $JobName"

        # ジョブを取得
        $job = Get-VBRJob -Name $JobName -ErrorAction Stop

        if (-not $job) {
            throw "ジョブが見つかりません: $JobName"
        }

        # 最新のセッションを取得
        $session = Get-VBRBackupSession | Where-Object { $_.JobName -eq $JobName } |
            Sort-Object EndTime -Descending | Select-Object -First 1

        if (-not $session) {
            throw "ジョブセッションが見つかりません: $JobName"
        }

        # ステータスの変換
        $status = switch ($session.Result) {
            "Success" { "success" }
            "Warning" { "warning" }
            "Failed"  { "failed" }
            default   { "failed" }
        }

        # バックアップサイズの取得
        $backupSize = 0
        try {
            $taskSessions = Get-VBRTaskSession -Session $session
            $backupSize = ($taskSessions | Measure-Object -Property TransferedSize -Sum).Sum
        }
        catch {
            Write-BackupLog -Level "WARNING" -Message "バックアップサイズの取得に失敗: $_"
        }

        # 実行時間の計算
        $duration = 0
        if ($session.EndTime -and $session.CreationTime) {
            $duration = [int]($session.EndTime - $session.CreationTime).TotalSeconds
        }

        # エラーメッセージの取得
        $errorMessage = ""
        if ($session.Result -ne "Success") {
            $errorMessage = $session.Info.Reason
            if ([string]::IsNullOrEmpty($errorMessage)) {
                $errorMessage = "Veeamジョブが失敗しました"
            }
        }

        $jobInfo = @{
            JobName = $job.Name
            JobType = $job.JobType
            Status = $status
            StartTime = $session.CreationTime
            EndTime = $session.EndTime
            Duration = $duration
            BackupSize = $backupSize
            ErrorMessage = $errorMessage
            SessionId = $session.Id
            Result = $session.Result
        }

        Write-BackupLog -Level "INFO" -Message "Veeamジョブ情報取得成功: Status=$status, Size=$(Convert-BytesToHumanReadable $backupSize), Duration=$(Convert-SecondsToHumanReadable $duration)"

        return $jobInfo
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "Veeamジョブ情報の取得に失敗: $_"
        throw
    }
}

<#
.SYNOPSIS
    Veeamレプリケーションジョブの情報を取得する
.PARAMETER JobName
    ジョブ名
.RETURNS
    ジョブ情報オブジェクト
#>
function Get-VeeamReplicationJobInfo {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$JobName
    )

    try {
        Write-BackupLog -Level "INFO" -Message "Veeamレプリケーションジョブ情報を取得中: $JobName"

        $job = Get-VBRJob -Name $JobName -ErrorAction Stop

        if (-not $job -or $job.JobType -ne "Replica") {
            throw "レプリケーションジョブが見つかりません: $JobName"
        }

        # 最新のセッションを取得
        $session = Get-VBRSession | Where-Object { $_.JobName -eq $JobName } |
            Sort-Object EndTime -Descending | Select-Object -First 1

        if (-not $session) {
            throw "レプリケーションセッションが見つかりません: $JobName"
        }

        $status = switch ($session.Result) {
            "Success" { "success" }
            "Warning" { "warning" }
            "Failed"  { "failed" }
            default   { "failed" }
        }

        $duration = 0
        if ($session.EndTime -and $session.CreationTime) {
            $duration = [int]($session.EndTime - $session.CreationTime).TotalSeconds
        }

        $transferredSize = 0
        try {
            $taskSessions = Get-VBRTaskSession -Session $session
            $transferredSize = ($taskSessions | Measure-Object -Property TransferedSize -Sum).Sum
        }
        catch {
            Write-BackupLog -Level "WARNING" -Message "転送サイズの取得に失敗: $_"
        }

        $errorMessage = ""
        if ($session.Result -ne "Success") {
            $errorMessage = $session.Info.Reason
        }

        return @{
            JobName = $job.Name
            Status = $status
            StartTime = $session.CreationTime
            EndTime = $session.EndTime
            Duration = $duration
            TransferredSize = $transferredSize
            ErrorMessage = $errorMessage
        }
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "Veeamレプリケーションジョブ情報の取得に失敗: $_"
        throw
    }
}

# ==============================================================================
# ステータス送信
# ==============================================================================

<#
.SYNOPSIS
    Veeamジョブステータスをバックアップ管理システムに送信する
.PARAMETER JobId
    バックアップ管理システムのジョブID
.PARAMETER JobInfo
    Veeamジョブ情報
#>
function Send-VeeamJobStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$JobId,

        [Parameter(Mandatory = $true)]
        [hashtable]$JobInfo
    )

    try {
        Write-BackupLog -Level "INFO" -Message "Veeamジョブステータスを送信中..." -JobId $JobId

        # バックアップステータスの送信
        $result = Send-BackupStatus `
            -JobId $JobId `
            -Status $JobInfo.Status `
            -BackupSize $JobInfo.BackupSize `
            -Duration $JobInfo.Duration `
            -ErrorMessage $JobInfo.ErrorMessage

        Write-BackupLog -Level "INFO" -Message "Veeamジョブステータス送信成功" -JobId $JobId

        # 実行記録の送信
        if ($JobInfo.StartTime -and $JobInfo.EndTime) {
            $details = "Veeam Job: $($JobInfo.JobName) | Type: $($JobInfo.JobType) | Result: $($JobInfo.Result)"

            Send-BackupExecution `
                -JobId $JobId `
                -StartTime $JobInfo.StartTime `
                -EndTime $JobInfo.EndTime `
                -Status $JobInfo.Status `
                -BackupSize $JobInfo.BackupSize `
                -Details $details

            Write-BackupLog -Level "INFO" -Message "Veeam実行記録送信成功" -JobId $JobId
        }

        return $result
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "Veeamジョブステータス送信に失敗: $_" -JobId $JobId
        throw
    }
}

# ==============================================================================
# テストモード
# ==============================================================================

function Test-VeeamIntegration {
    [CmdletBinding()]
    param()

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Veeam統合スクリプト テストモード" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    try {
        # 設定ファイルの読み込みテスト
        Write-Host "1. 設定ファイル読み込みテスト..." -ForegroundColor Yellow
        $config = Get-BackupSystemConfig
        Write-Host "   ✓ 成功: API URL = $($config.api_url)" -ForegroundColor Green

        # Veeam SnapIn読み込みテスト
        Write-Host "`n2. Veeam SnapIn読み込みテスト..." -ForegroundColor Yellow
        if (Import-VeeamSnapIn) {
            Write-Host "   ✓ 成功: Veeam SnapIn読み込み完了" -ForegroundColor Green

            # ジョブ一覧の取得
            Write-Host "`n3. Veeamジョブ一覧取得..." -ForegroundColor Yellow
            $jobs = Get-VBRJob
            if ($jobs) {
                Write-Host "   ✓ 成功: $($jobs.Count) 個のジョブが見つかりました" -ForegroundColor Green
                foreach ($job in $jobs) {
                    Write-Host "      - $($job.Name) ($($job.JobType))" -ForegroundColor Gray
                }
            }
            else {
                Write-Host "   ⚠ 警告: ジョブが見つかりませんでした" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "   ✗ 失敗: Veeam SnapInの読み込みに失敗しました" -ForegroundColor Red
            Write-Host "   Veeam Backup & Replicationがインストールされていない可能性があります" -ForegroundColor Yellow
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
        Write-BackupLog -Level "INFO" -Message "===== Veeam統合スクリプト開始 ====="

        # テストモード
        if ($TestMode) {
            Test-VeeamIntegration
            return
        }

        # パラメータチェック
        if ($JobId -eq 0 -and [string]::IsNullOrEmpty($JobName)) {
            throw "JobIdまたはJobNameを指定してください"
        }

        # 設定ファイルの読み込み
        $config = Get-BackupSystemConfig

        # JobNameからJobIdを解決
        if ([string]::IsNullOrEmpty($JobName)) {
            Write-BackupLog -Level "ERROR" -Message "JobNameが指定されていません"
            throw "JobNameが必要です"
        }

        # Veeam SnapInの読み込み
        if (-not (Import-VeeamSnapIn)) {
            throw "Veeam PowerShell SnapInの読み込みに失敗しました"
        }

        # Veeamジョブ情報の取得
        $jobInfo = Get-VeeamJobInfo -JobName $JobName

        # バックアップ管理システムのジョブIDが指定されている場合のみ送信
        if ($JobId -gt 0) {
            Send-VeeamJobStatus -JobId $JobId -JobInfo $jobInfo
        }
        else {
            Write-BackupLog -Level "WARNING" -Message "JobIdが0のため、API送信をスキップします"
        }

        Write-BackupLog -Level "INFO" -Message "===== Veeam統合スクリプト正常終了 ====="
        exit 0
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "Veeam統合スクリプトでエラーが発生: $_"
        Write-BackupLog -Level "ERROR" -Message "スタックトレース: $($_.ScriptStackTrace)"
        exit 1
    }
}

# スクリプト実行
Main
