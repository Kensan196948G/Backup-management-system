# ==============================================================================
# Backup Management System - Installation Script
# PowerShell 5.1+ Compatible
# ==============================================================================

<#
.SYNOPSIS
    バックアップ管理システム PowerShell統合のインストールスクリプト
.DESCRIPTION
    - 依存関係チェック
    - 設定ファイルの初期化
    - ログディレクトリの作成
    - タスクスケジューラーへの登録
    - 動作確認テスト
.NOTES
    管理者権限で実行してください
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ApiUrl = "http://localhost:5000",

    [Parameter(Mandatory = $false)]
    [string]$ApiToken = "",

    [Parameter(Mandatory = $false)]
    [switch]$SkipTaskRegistration,

    [Parameter(Mandatory = $false)]
    [switch]$TestOnly
)

# ==============================================================================
# 初期設定
# ==============================================================================

$ErrorActionPreference = "Stop"
$script:InstallPath = $PSScriptRoot
$script:ConfigPath = Join-Path $script:InstallPath "config.json"
$script:LogPath = Join-Path $script:InstallPath "logs"

# ==============================================================================
# ヘルパー関数
# ==============================================================================

function Write-InstallLog {
    param(
        [string]$Message,
        [ValidateSet("Info", "Success", "Warning", "Error")]
        [string]$Level = "Info"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "Success" { "Green" }
        "Warning" { "Yellow" }
        "Error"   { "Red" }
        default   { "White" }
    }

    $prefix = switch ($Level) {
        "Success" { "[✓]" }
        "Warning" { "[!]" }
        "Error"   { "[✗]" }
        default   { "[i]" }
    }

    Write-Host "$prefix $Message" -ForegroundColor $color
}

function Test-AdminPrivilege {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    return $isAdmin
}

# ==============================================================================
# 依存関係チェック
# ==============================================================================

function Test-Dependencies {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "依存関係チェック" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    $allPassed = $true

    # PowerShell バージョンチェック
    Write-InstallLog "PowerShell バージョン確認中..."
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -ge 5) {
        Write-InstallLog "PowerShell $($psVersion.ToString()) が検出されました" "Success"
    }
    else {
        Write-InstallLog "PowerShell 5.1以上が必要です (現在: $($psVersion.ToString()))" "Error"
        $allPassed = $false
    }

    # .NET Framework チェック
    Write-InstallLog ".NET Framework 確認中..."
    try {
        $dotNetVersion = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" -ErrorAction Stop).Release
        if ($dotNetVersion -ge 378389) {
            Write-InstallLog ".NET Framework 4.5以上が検出されました" "Success"
        }
        else {
            Write-InstallLog ".NET Framework 4.5以上が推奨されます" "Warning"
        }
    }
    catch {
        Write-InstallLog ".NET Framework バージョン確認に失敗しました" "Warning"
    }

    # スクリプト実行ポリシーチェック
    Write-InstallLog "スクリプト実行ポリシー確認中..."
    $executionPolicy = Get-ExecutionPolicy
    if ($executionPolicy -eq "Restricted") {
        Write-InstallLog "スクリプト実行ポリシーが制限されています (現在: $executionPolicy)" "Warning"
        Write-InstallLog "以下のコマンドで変更してください: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser" "Info"
    }
    else {
        Write-InstallLog "スクリプト実行ポリシー: $executionPolicy" "Success"
    }

    # 必須スクリプトファイルの確認
    Write-InstallLog "必須スクリプトファイル確認中..."
    $requiredScripts = @(
        "common_functions.ps1",
        "veeam_integration.ps1",
        "wsb_integration.ps1",
        "aomei_integration.ps1",
        "register_scheduled_tasks.ps1"
    )

    foreach ($script in $requiredScripts) {
        $scriptPath = Join-Path $script:InstallPath $script
        if (Test-Path $scriptPath) {
            Write-InstallLog "  ✓ $script" "Success"
        }
        else {
            Write-InstallLog "  ✗ $script が見つかりません" "Error"
            $allPassed = $false
        }
    }

    return $allPassed
}

# ==============================================================================
# バックアップツール検出
# ==============================================================================

function Test-BackupTools {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "バックアップツール検出" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    $detectedTools = @{
        veeam = $false
        wsb = $false
        aomei = $false
    }

    # Veeam Backup & Replication
    Write-InstallLog "Veeam Backup & Replication を検索中..."
    try {
        if (Get-PSSnapin -Name VeeamPSSnapIn -Registered -ErrorAction SilentlyContinue) {
            Write-InstallLog "Veeam Backup & Replication が検出されました" "Success"
            $detectedTools.veeam = $true
        }
        else {
            Write-InstallLog "Veeam Backup & Replication が見つかりません" "Warning"
        }
    }
    catch {
        Write-InstallLog "Veeam Backup & Replication が見つかりません" "Warning"
    }

    # Windows Server Backup
    Write-InstallLog "Windows Server Backup を検索中..."
    if (Get-Command Get-WBJob -ErrorAction SilentlyContinue) {
        Write-InstallLog "Windows Server Backup が検出されました" "Success"
        $detectedTools.wsb = $true
    }
    else {
        Write-InstallLog "Windows Server Backup が見つかりません" "Warning"
        Write-InstallLog "インストール方法: Install-WindowsFeature Windows-Server-Backup" "Info"
    }

    # AOMEI Backupper
    Write-InstallLog "AOMEI Backupper を検索中..."
    $aomeiPaths = @(
        "C:\Program Files (x86)\AOMEI Backupper",
        "C:\Program Files\AOMEI Backupper"
    )

    $aomeiFound = $false
    foreach ($path in $aomeiPaths) {
        if (Test-Path $path) {
            Write-InstallLog "AOMEI Backupper が検出されました: $path" "Success"
            $detectedTools.aomei = $true
            $aomeiFound = $true
            break
        }
    }

    if (-not $aomeiFound) {
        Write-InstallLog "AOMEI Backupper が見つかりません" "Warning"
    }

    return $detectedTools
}

# ==============================================================================
# 設定ファイル初期化
# ==============================================================================

function Initialize-Configuration {
    param(
        [hashtable]$DetectedTools
    )

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "設定ファイル初期化" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    try {
        # 既存の設定ファイルの確認
        if (Test-Path $script:ConfigPath) {
            Write-InstallLog "既存の設定ファイルが見つかりました" "Warning"
            $overwrite = Read-Host "設定ファイルを上書きしますか？ (Y/N)"
            if ($overwrite -ne "Y" -and $overwrite -ne "y") {
                Write-InstallLog "設定ファイルの初期化をスキップしました" "Info"
                return $true
            }
        }

        # 設定ファイルの読み込み（テンプレートとして）
        $config = Get-Content $script:ConfigPath -Raw | ConvertFrom-Json

        # API設定の更新
        Write-InstallLog "API設定を構成中..."
        $config.api_url = $ApiUrl
        $config.api_token = $ApiToken

        # 検出されたツールに基づいて有効/無効を設定
        $config.backup_tools.veeam.enabled = $DetectedTools.veeam
        $config.backup_tools.wsb.enabled = $DetectedTools.wsb
        $config.backup_tools.aomei.enabled = $DetectedTools.aomei

        # 更新日時の設定
        $config.last_updated = (Get-Date -Format "yyyy-MM-dd")

        # 設定ファイルの保存
        $config | ConvertTo-Json -Depth 10 | Set-Content $script:ConfigPath -Encoding UTF8

        Write-InstallLog "設定ファイルを保存しました: $script:ConfigPath" "Success"

        # 設定内容の表示
        Write-Host "`n設定内容:" -ForegroundColor Yellow
        Write-Host "  API URL: $($config.api_url)" -ForegroundColor Gray
        Write-Host "  API Token: $(if ($config.api_token) { '設定済み' } else { '未設定' })" -ForegroundColor Gray
        Write-Host "  Veeam: $(if ($config.backup_tools.veeam.enabled) { '有効' } else { '無効' })" -ForegroundColor Gray
        Write-Host "  Windows Server Backup: $(if ($config.backup_tools.wsb.enabled) { '有効' } else { '無効' })" -ForegroundColor Gray
        Write-Host "  AOMEI Backupper: $(if ($config.backup_tools.aomei.enabled) { '有効' } else { '無効' })`n" -ForegroundColor Gray

        return $true
    }
    catch {
        Write-InstallLog "設定ファイルの初期化に失敗しました: $_" "Error"
        return $false
    }
}

# ==============================================================================
# ログディレクトリ作成
# ==============================================================================

function Initialize-LogDirectory {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "ログディレクトリ作成" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    try {
        if (-not (Test-Path $script:LogPath)) {
            New-Item -ItemType Directory -Path $script:LogPath -Force | Out-Null
            Write-InstallLog "ログディレクトリを作成しました: $script:LogPath" "Success"
        }
        else {
            Write-InstallLog "ログディレクトリは既に存在します: $script:LogPath" "Info"
        }

        # アクセス権限の確認
        $testFile = Join-Path $script:LogPath "test.log"
        "Test" | Out-File $testFile -ErrorAction Stop
        Remove-Item $testFile -ErrorAction SilentlyContinue

        Write-InstallLog "ログディレクトリへの書き込み権限を確認しました" "Success"
        return $true
    }
    catch {
        Write-InstallLog "ログディレクトリの作成に失敗しました: $_" "Error"
        return $false
    }
}

# ==============================================================================
# タスクスケジューラー登録
# ==============================================================================

function Register-Tasks {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "タスクスケジューラー登録" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    try {
        $registerScript = Join-Path $script:InstallPath "register_scheduled_tasks.ps1"

        if (-not (Test-Path $registerScript)) {
            Write-InstallLog "タスク登録スクリプトが見つかりません: $registerScript" "Error"
            return $false
        }

        Write-InstallLog "タスクスケジューラーにタスクを登録中..."

        # タスク登録スクリプトの実行
        & $registerScript

        if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
            Write-InstallLog "タスクスケジューラーへの登録が完了しました" "Success"
            return $true
        }
        else {
            Write-InstallLog "タスクスケジューラーへの登録に失敗しました" "Error"
            return $false
        }
    }
    catch {
        Write-InstallLog "タスクスケジューラーへの登録中にエラーが発生しました: $_" "Error"
        return $false
    }
}

# ==============================================================================
# 動作確認テスト
# ==============================================================================

function Test-Installation {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "動作確認テスト" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    $allPassed = $true

    # 共通関数モジュールのテスト
    Write-InstallLog "共通関数モジュールをテスト中..."
    try {
        . (Join-Path $script:InstallPath "common_functions.ps1")
        $config = Get-BackupSystemConfig
        Write-InstallLog "共通関数モジュール: OK" "Success"
    }
    catch {
        Write-InstallLog "共通関数モジュール: FAILED - $_" "Error"
        $allPassed = $false
    }

    # 各統合スクリプトのテスト
    $scripts = @(
        @{ Name = "Veeam統合"; Script = "veeam_integration.ps1" },
        @{ Name = "Windows Server Backup統合"; Script = "wsb_integration.ps1" },
        @{ Name = "AOMEI統合"; Script = "aomei_integration.ps1" }
    )

    foreach ($scriptInfo in $scripts) {
        Write-InstallLog "$($scriptInfo.Name)スクリプトをテスト中..."
        try {
            $scriptPath = Join-Path $script:InstallPath $scriptInfo.Script
            & $scriptPath -TestMode 2>&1 | Out-Null
            Write-InstallLog "$($scriptInfo.Name): OK" "Success"
        }
        catch {
            Write-InstallLog "$($scriptInfo.Name): WARNING (ツールが未インストールの可能性があります)" "Warning"
        }
    }

    return $allPassed
}

# ==============================================================================
# メイン処理
# ==============================================================================

function Main {
    Write-Host "`n" -NoNewline
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Backup Management System" -ForegroundColor Cyan
    Write-Host "PowerShell統合 インストーラー" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # 管理者権限チェック
    if (-not (Test-AdminPrivilege)) {
        Write-InstallLog "このスクリプトは管理者権限で実行する必要があります" "Error"
        Write-Host "`nPowerShellを管理者として実行し、再度お試しください`n" -ForegroundColor Yellow
        exit 1
    }

    Write-InstallLog "管理者権限で実行されています" "Success"
    Write-InstallLog "インストールパス: $script:InstallPath" "Info"

    # テストモード
    if ($TestOnly) {
        Test-Installation
        return
    }

    # 依存関係チェック
    if (-not (Test-Dependencies)) {
        Write-InstallLog "依存関係チェックに失敗しました。問題を解決してから再実行してください。" "Error"
        exit 1
    }

    # バックアップツール検出
    $detectedTools = Test-BackupTools

    # 設定ファイル初期化
    if (-not (Initialize-Configuration -DetectedTools $detectedTools)) {
        Write-InstallLog "設定ファイルの初期化に失敗しました" "Error"
        exit 1
    }

    # ログディレクトリ作成
    if (-not (Initialize-LogDirectory)) {
        Write-InstallLog "ログディレクトリの作成に失敗しました" "Error"
        exit 1
    }

    # タスクスケジューラー登録
    if (-not $SkipTaskRegistration) {
        Register-Tasks
    }
    else {
        Write-InstallLog "タスクスケジューラーへの登録をスキップしました" "Info"
    }

    # 動作確認テスト
    Test-Installation

    # インストール完了
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "インストール完了" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    Write-Host "次のステップ:" -ForegroundColor Yellow
    Write-Host "1. 設定ファイルを編集してください: $script:ConfigPath" -ForegroundColor Gray
    Write-Host "   - api_url: バックアップ管理システムのURL" -ForegroundColor Gray
    Write-Host "   - api_token: API認証トークン" -ForegroundColor Gray
    Write-Host "   - job_ids: 各バックアップツールのジョブID" -ForegroundColor Gray
    Write-Host "`n2. タスクスケジューラーで登録されたタスクを確認してください" -ForegroundColor Gray
    Write-Host "   - タスクスケジューラーを開く > BackupManagementSystem フォルダー" -ForegroundColor Gray
    Write-Host "`n3. READMEを参照して各ツールの設定を完了してください" -ForegroundColor Gray
    Write-Host "   - README.md: $(Join-Path $script:InstallPath 'README.md')" -ForegroundColor Gray
    Write-Host ""
}

# スクリプト実行
try {
    Main
}
catch {
    Write-InstallLog "インストール中に予期しないエラーが発生しました: $_" "Error"
    Write-Host "`nスタックトレース:" -ForegroundColor Yellow
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    exit 1
}
