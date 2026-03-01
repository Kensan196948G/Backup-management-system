# ==============================================================================
# Backup Management System - Register Scheduled Tasks
# PowerShell 5.1+ Compatible
# ==============================================================================

<#
.SYNOPSIS
    バックアップ統合スクリプトのWindowsタスクスケジューラー登録
.DESCRIPTION
    各バックアップツールの統合スクリプトをWindowsタスクスケジューラーに登録し、
    定期実行またはイベントトリガーで自動実行を設定する
.NOTES
    - 管理者権限で実行
    - タスク名は "BackupManagementSystem_*" の形式
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [switch]$Remove,

    [Parameter(Mandatory = $false)]
    [switch]$List,

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
# タスクスケジューラー設定
# ==============================================================================

$script:TaskPrefix = "BackupManagementSystem"
$script:TaskFolder = "\BackupManagementSystem"

<#
.SYNOPSIS
    タスクスケジューラーにタスクを登録する
.PARAMETER TaskName
    タスク名
.PARAMETER Description
    タスクの説明
.PARAMETER ScriptPath
    実行するスクリプトのパス
.PARAMETER Arguments
    スクリプトの引数
.PARAMETER TriggerType
    トリガータイプ (Daily, AtLogon, Manual)
.PARAMETER Schedule
    スケジュール（Dailyの場合の実行時刻）
#>
function Register-BackupTask {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$TaskName,

        [Parameter(Mandatory = $true)]
        [string]$Description,

        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,

        [Parameter(Mandatory = $false)]
        [string]$Arguments = "",

        [Parameter(Mandatory = $false)]
        [ValidateSet("Daily", "AtLogon", "Manual", "Hourly")]
        [string]$TriggerType = "Daily",

        [Parameter(Mandatory = $false)]
        [string]$Schedule = "03:00",

        [Parameter(Mandatory = $false)]
        [int]$IntervalHours = 1
    )

    try {
        $fullTaskName = "$script:TaskPrefix`_$TaskName"

        Write-BackupLog -Level "INFO" -Message "タスク登録中: $fullTaskName"

        # スクリプトパスの検証
        if (-not (Test-Path $ScriptPath)) {
            throw "スクリプトが見つかりません: $ScriptPath"
        }

        # 既存タスクの削除
        $existingTask = Get-ScheduledTask -TaskName $fullTaskName -ErrorAction SilentlyContinue
        if ($existingTask) {
            Write-BackupLog -Level "WARNING" -Message "既存のタスクを削除します: $fullTaskName"
            Unregister-ScheduledTask -TaskName $fullTaskName -Confirm:$false -ErrorAction Stop
        }

        # アクションの作成
        $actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
        if ($Arguments) {
            $actionArgs += " $Arguments"
        }

        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument $actionArgs

        # トリガーの作成
        $trigger = switch ($TriggerType) {
            "Daily" {
                $triggerTime = [DateTime]::Today.Add([TimeSpan]::Parse($Schedule))
                New-ScheduledTaskTrigger -Daily -At $triggerTime
            }
            "Hourly" {
                # 毎時実行（1時間ごと）
                $triggerTime = [DateTime]::Today
                $trigger = New-ScheduledTaskTrigger -Once -At $triggerTime -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)
                $trigger
            }
            "AtLogon" {
                New-ScheduledTaskTrigger -AtLogon
            }
            "Manual" {
                # 手動実行のみ（トリガーなし）
                $null
            }
        }

        # プリンシパルの作成（最高特権で実行）
        $principal = New-ScheduledTaskPrincipal `
            -UserId "SYSTEM" `
            -LogonType ServiceAccount `
            -RunLevel Highest

        # 設定の作成
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 1)

        # タスクの登録
        if ($trigger) {
            Register-ScheduledTask `
                -TaskName $fullTaskName `
                -Description $Description `
                -Action $action `
                -Trigger $trigger `
                -Principal $principal `
                -Settings $settings `
                -Force | Out-Null
        }
        else {
            # トリガーなし（手動実行のみ）
            Register-ScheduledTask `
                -TaskName $fullTaskName `
                -Description $Description `
                -Action $action `
                -Principal $principal `
                -Settings $settings `
                -Force | Out-Null
        }

        Write-BackupLog -Level "INFO" -Message "タスク登録成功: $fullTaskName"
        return $true
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "タスク登録に失敗: $fullTaskName - $_"
        return $false
    }
}

<#
.SYNOPSIS
    登録済みのバックアップタスクを一覧表示する
#>
function Get-BackupTasks {
    [CmdletBinding()]
    param()

    try {
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "登録済みバックアップタスク一覧" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Cyan

        $tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like "$script:TaskPrefix*" }

        if (-not $tasks -or $tasks.Count -eq 0) {
            Write-Host "登録済みタスクはありません" -ForegroundColor Yellow
            return
        }

        foreach ($task in $tasks) {
            $info = Get-ScheduledTaskInfo -TaskName $task.TaskName

            Write-Host "タスク名: $($task.TaskName)" -ForegroundColor Green
            Write-Host "  説明: $($task.Description)" -ForegroundColor Gray
            Write-Host "  状態: $($task.State)" -ForegroundColor Gray
            Write-Host "  最終実行: $($info.LastRunTime)" -ForegroundColor Gray
            Write-Host "  次回実行: $($info.NextRunTime)" -ForegroundColor Gray
            Write-Host "  最終結果: $($info.LastTaskResult)" -ForegroundColor Gray
            Write-Host ""
        }

        Write-Host "合計: $($tasks.Count) 個のタスク`n" -ForegroundColor Cyan
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "タスク一覧取得に失敗: $_"
    }
}

<#
.SYNOPSIS
    登録済みのバックアップタスクを削除する
#>
function Remove-BackupTasks {
    [CmdletBinding()]
    param()

    try {
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "バックアップタスク削除" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Cyan

        $tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like "$script:TaskPrefix*" }

        if (-not $tasks -or $tasks.Count -eq 0) {
            Write-Host "削除対象のタスクはありません" -ForegroundColor Yellow
            return
        }

        Write-Host "以下のタスクを削除します:" -ForegroundColor Yellow
        foreach ($task in $tasks) {
            Write-Host "  - $($task.TaskName)" -ForegroundColor Gray
        }

        $confirmation = Read-Host "`n削除を続行しますか？ (Y/N)"
        if ($confirmation -ne "Y" -and $confirmation -ne "y") {
            Write-Host "削除をキャンセルしました" -ForegroundColor Yellow
            return
        }

        foreach ($task in $tasks) {
            try {
                Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false -ErrorAction Stop
                Write-Host "✓ 削除成功: $($task.TaskName)" -ForegroundColor Green
                Write-BackupLog -Level "INFO" -Message "タスク削除成功: $($task.TaskName)"
            }
            catch {
                Write-Host "✗ 削除失敗: $($task.TaskName) - $_" -ForegroundColor Red
                Write-BackupLog -Level "ERROR" -Message "タスク削除失敗: $($task.TaskName) - $_"
            }
        }

        Write-Host "`n削除完了`n" -ForegroundColor Cyan
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "タスク削除処理に失敗: $_"
    }
}

# ==============================================================================
# タスク登録メイン処理
# ==============================================================================

function Register-AllBackupTasks {
    [CmdletBinding()]
    param()

    try {
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "バックアップタスク一括登録" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Cyan

        # 設定ファイルの読み込み
        $config = Get-BackupSystemConfig

        $successCount = 0
        $failureCount = 0

        # Windows Server Backup タスク
        if ($config.backup_tools.wsb.enabled) {
            Write-Host "Windows Server Backupタスクを登録中..." -ForegroundColor Yellow

            foreach ($jobId in $config.backup_tools.wsb.job_ids) {
                $result = Register-BackupTask `
                    -TaskName "WSB_Job$jobId" `
                    -Description "Windows Server Backup統合 (Job ID: $jobId)" `
                    -ScriptPath (Join-Path $PSScriptRoot "wsb_integration.ps1") `
                    -Arguments "-JobId $jobId" `
                    -TriggerType "Hourly" `
                    -IntervalHours 1

                if ($result) { $successCount++ } else { $failureCount++ }
            }
        }

        # AOMEI Backupper タスク
        if ($config.backup_tools.aomei.enabled) {
            Write-Host "AOMEI Backupperタスクを登録中..." -ForegroundColor Yellow

            foreach ($jobId in $config.backup_tools.aomei.job_ids) {
                $result = Register-BackupTask `
                    -TaskName "AOMEI_Job$jobId" `
                    -Description "AOMEI Backupper統合 (Job ID: $jobId)" `
                    -ScriptPath (Join-Path $PSScriptRoot "aomei_integration.ps1") `
                    -Arguments "-JobId $jobId" `
                    -TriggerType "Hourly" `
                    -IntervalHours 1

                if ($result) { $successCount++ } else { $failureCount++ }
            }
        }

        # Veeam Backup & Replication タスク（手動実行用）
        if ($config.backup_tools.veeam.enabled) {
            Write-Host "Veeam Backup & Replicationタスクを登録中..." -ForegroundColor Yellow
            Write-Host "  ※ Veeamタスクは手動実行用として登録されます（Veeamのポストジョブスクリプトとして使用）" -ForegroundColor Gray

            foreach ($jobId in $config.backup_tools.veeam.job_ids) {
                $result = Register-BackupTask `
                    -TaskName "Veeam_Job$jobId" `
                    -Description "Veeam Backup統合 (Job ID: $jobId) - 手動実行またはVeeamポストジョブスクリプトから実行" `
                    -ScriptPath (Join-Path $PSScriptRoot "veeam_integration.ps1") `
                    -Arguments "-JobId $jobId -JobName `"VeeamJobName`"" `
                    -TriggerType "Manual"

                if ($result) { $successCount++ } else { $failureCount++ }
            }
        }

        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "タスク登録完了" -ForegroundColor Cyan
        Write-Host "  成功: $successCount 個" -ForegroundColor Green
        Write-Host "  失敗: $failureCount 個" -ForegroundColor $(if ($failureCount -gt 0) { "Red" } else { "Gray" })
        Write-Host "========================================`n" -ForegroundColor Cyan

        Write-Host "※ Veeamタスクをポストジョブスクリプトとして設定する場合:" -ForegroundColor Yellow
        Write-Host "   1. Veeam Backup & Replicationコンソールを開く" -ForegroundColor Gray
        Write-Host "   2. 対象ジョブを右クリック > Edit" -ForegroundColor Gray
        Write-Host "   3. Storage > Advanced > Scripts タブを開く" -ForegroundColor Gray
        Write-Host "   4. Run the following script after the job: にチェック" -ForegroundColor Gray
        Write-Host "   5. スクリプトパスを指定: $(Join-Path $PSScriptRoot 'veeam_integration.ps1')" -ForegroundColor Gray
        Write-Host "   6. 引数を指定: -JobId <JobID> -JobName `"%job_name%`"`n" -ForegroundColor Gray
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "タスク一括登録に失敗: $_"
        throw
    }
}

# ==============================================================================
# テストモード
# ==============================================================================

function Test-ScheduledTasksRegistration {
    [CmdletBinding()]
    param()

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "スケジュールタスク登録 テストモード" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    try {
        # 管理者権限チェック
        Write-Host "1. 管理者権限チェック..." -ForegroundColor Yellow
        $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if ($isAdmin) {
            Write-Host "   ✓ 成功: 管理者権限で実行されています" -ForegroundColor Green
        }
        else {
            Write-Host "   ✗ 失敗: 管理者権限が必要です" -ForegroundColor Red
            return
        }

        # 設定ファイル確認
        Write-Host "`n2. 設定ファイル確認..." -ForegroundColor Yellow
        $config = Get-BackupSystemConfig
        Write-Host "   ✓ 成功: 設定ファイル読み込み完了" -ForegroundColor Green

        # スクリプトファイル確認
        Write-Host "`n3. スクリプトファイル確認..." -ForegroundColor Yellow
        $scripts = @(
            "common_functions.ps1",
            "veeam_integration.ps1",
            "wsb_integration.ps1",
            "aomei_integration.ps1"
        )

        foreach ($script in $scripts) {
            $scriptPath = Join-Path $PSScriptRoot $script
            if (Test-Path $scriptPath) {
                Write-Host "   ✓ $script" -ForegroundColor Green
            }
            else {
                Write-Host "   ✗ $script (見つかりません)" -ForegroundColor Red
            }
        }

        # タスクスケジューラーアクセス確認
        Write-Host "`n4. タスクスケジューラーアクセス確認..." -ForegroundColor Yellow
        $testTask = Get-ScheduledTask -TaskName "BackupManagementSystem_Test" -ErrorAction SilentlyContinue
        Write-Host "   ✓ 成功: タスクスケジューラーにアクセス可能" -ForegroundColor Green

        # 登録済みタスク一覧
        Write-Host "`n5. 登録済みタスク一覧..." -ForegroundColor Yellow
        Get-BackupTasks

        Write-Host "========================================" -ForegroundColor Cyan
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
        # 管理者権限チェック
        $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if (-not $isAdmin) {
            Write-Host "`n✗ エラー: このスクリプトは管理者権限で実行する必要があります`n" -ForegroundColor Red
            Write-Host "PowerShellを管理者として実行し、再度お試しください`n" -ForegroundColor Yellow
            exit 1
        }

        Write-BackupLog -Level "INFO" -Message "===== スケジュールタスク登録スクリプト開始 ====="

        # テストモード
        if ($TestMode) {
            Test-ScheduledTasksRegistration
            return
        }

        # タスク一覧表示
        if ($List) {
            Get-BackupTasks
            return
        }

        # タスク削除
        if ($Remove) {
            Remove-BackupTasks
            return
        }

        # タスク一括登録
        Register-AllBackupTasks

        Write-BackupLog -Level "INFO" -Message "===== スケジュールタスク登録スクリプト正常終了 ====="
    }
    catch {
        Write-BackupLog -Level "ERROR" -Message "スケジュールタスク登録スクリプトでエラーが発生: $_"
        Write-BackupLog -Level "ERROR" -Message "スタックトレース: $($_.ScriptStackTrace)"
        exit 1
    }
}

# スクリプト実行
Main
