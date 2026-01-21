# PowerShell統合 - 動作テスト手順書

このドキュメントでは、PowerShell統合スクリプトの動作テスト手順を説明します。

## 📋 目次

- [テスト環境の準備](#テスト環境の準備)
- [構文チェック](#構文チェック)
- [単体テスト](#単体テスト)
- [統合テスト](#統合テスト)
- [本番環境テスト](#本番環境テスト)
- [トラブルシューティング](#トラブルシューティング)

---

## 🔧 テスト環境の準備

### 1. 前提条件

```powershell
# PowerShellバージョン確認
$PSVersionTable.PSVersion
# 期待値: 5.1以上

# 管理者権限確認
([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
# 期待値: True

# スクリプト実行ポリシー確認
Get-ExecutionPolicy
# 期待値: RemoteSigned または Unrestricted
```

### 2. テスト環境セットアップ

```powershell
cd C:\BackupManagementSystem\scripts\powershell

# テスト用ディレクトリ作成
New-Item -ItemType Directory -Path ".\test_logs" -Force
New-Item -ItemType Directory -Path ".\test_config" -Force
```

---

## 🔍 構文チェック

PowerShellスクリプトの構文エラーをチェックします。

### 自動構文チェック

```powershell
# すべてのスクリプトの構文チェック
$scripts = Get-ChildItem -Filter "*.ps1"
foreach ($script in $scripts) {
    Write-Host "Checking: $($script.Name)..." -ForegroundColor Yellow
    $errors = $null
    [System.Management.Automation.PSParser]::Tokenize((Get-Content $script.FullName -Raw), [ref]$errors)

    if ($errors.Count -eq 0) {
        Write-Host "  ✓ OK" -ForegroundColor Green
    } else {
        Write-Host "  ✗ ERRORS:" -ForegroundColor Red
        $errors | ForEach-Object { Write-Host "    Line $($_.Token.StartLine): $($_.Message)" -ForegroundColor Red }
    }
}
```

### 個別スクリプト構文チェック

```powershell
# 個別スクリプトのテスト実行（実行せずに構文のみチェック）
Get-Command .\common_functions.ps1 -Syntax
Get-Command .\veeam_integration.ps1 -Syntax
Get-Command .\wsb_integration.ps1 -Syntax
Get-Command .\aomei_integration.ps1 -Syntax
Get-Command .\register_scheduled_tasks.ps1 -Syntax
Get-Command .\install.ps1 -Syntax
```

---

## 🧪 単体テスト

各スクリプトを個別にテストします。

### 1. common_functions.ps1 のテスト

```powershell
# 共通関数モジュールの読み込みテスト
. .\common_functions.ps1

# 設定ファイル読み込みテスト
try {
    $config = Get-BackupSystemConfig
    Write-Host "✓ 設定ファイル読み込み成功" -ForegroundColor Green
    Write-Host "  API URL: $($config.api_url)" -ForegroundColor Gray
} catch {
    Write-Host "✗ 設定ファイル読み込み失敗: $_" -ForegroundColor Red
}

# ログ記録テスト
try {
    Write-BackupLog -Level "INFO" -Message "テストログメッセージ" -JobId 1
    Write-Host "✓ ログ記録成功" -ForegroundColor Green
} catch {
    Write-Host "✗ ログ記録失敗: $_" -ForegroundColor Red
}

# ユーティリティ関数テスト
try {
    $sizeStr = Convert-BytesToHumanReadable -Bytes 1073741824
    Write-Host "✓ バイト変換: $sizeStr" -ForegroundColor Green

    $timeStr = Convert-SecondsToHumanReadable -Seconds 3661
    Write-Host "✓ 時間変換: $timeStr" -ForegroundColor Green
} catch {
    Write-Host "✗ ユーティリティ関数失敗: $_" -ForegroundColor Red
}
```

### 2. veeam_integration.ps1 のテスト

```powershell
# テストモードで実行
.\veeam_integration.ps1 -TestMode
```

**期待される出力**:
- ✓ 設定ファイル読み込み成功
- Veeam SnapInの読み込み結果（インストールされている場合）
- ジョブ一覧の表示（ジョブがある場合）

### 3. wsb_integration.ps1 のテスト

```powershell
# テストモードで実行
.\wsb_integration.ps1 -TestMode
```

**期待される出力**:
- ✓ 設定ファイル読み込み成功
- Windows Server Backup機能の検出
- ジョブ履歴の表示（ジョブがある場合）

### 4. aomei_integration.ps1 のテスト

```powershell
# テストモードで実行
.\aomei_integration.ps1 -TestMode
```

**期待される出力**:
- ✓ 設定ファイル読み込み成功
- AOMEIログディレクトリの検出
- ログファイル一覧の表示
- 最新ログの解析結果

### 5. register_scheduled_tasks.ps1 のテスト

```powershell
# テストモードで実行
.\register_scheduled_tasks.ps1 -TestMode
```

**期待される出力**:
- ✓ 管理者権限確認
- ✓ 設定ファイル確認
- ✓ スクリプトファイル確認
- 登録済みタスク一覧

### 6. install.ps1 のテスト

```powershell
# テストモードで実行
.\install.ps1 -TestOnly
```

**期待される出力**:
- ✓ 共通関数モジュール: OK
- 各統合スクリプトのテスト結果

---

## 🔗 統合テスト

複数のスクリプトを連携させてテストします。

### 1. インストールプロセス全体のテスト

```powershell
# バックアップ管理システムが起動していることを確認
Invoke-RestMethod -Uri "http://localhost:5000/api/health" -Method Get

# インストール実行（テスト用API URL）
.\install.ps1 `
    -ApiUrl "http://localhost:5000" `
    -ApiToken "test-token-12345" `
    -Verbose

# インストール結果の確認
Write-Host "`n=== インストール結果確認 ===" -ForegroundColor Cyan

# 1. 設定ファイルの確認
Write-Host "1. 設定ファイル:" -ForegroundColor Yellow
Get-Content .\config.json | ConvertFrom-Json | ConvertTo-Json -Depth 5

# 2. ログディレクトリの確認
Write-Host "`n2. ログディレクトリ:" -ForegroundColor Yellow
Get-ChildItem .\logs -ErrorAction SilentlyContinue

# 3. タスクスケジューラーの確認
Write-Host "`n3. 登録済みタスク:" -ForegroundColor Yellow
.\register_scheduled_tasks.ps1 -List
```

### 2. API接続テスト

```powershell
# 共通関数の読み込み
. .\common_functions.ps1

# 設定の読み込み
$config = Get-BackupSystemConfig

# 簡易的なAPIテスト（テストステータス送信）
try {
    $testResult = Send-BackupStatus `
        -JobId 999 `
        -Status "success" `
        -BackupSize 1073741824 `
        -Duration 300 `
        -ErrorMessage ""

    Write-Host "✓ API送信テスト成功" -ForegroundColor Green
    Write-Host "  レスポンス: $($testResult | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "✗ API送信テスト失敗: $_" -ForegroundColor Red
}
```

### 3. エンドツーエンドテスト

#### Windows Server Backupテスト

```powershell
# 1. WSBジョブが存在することを確認
Get-WBJob -Previous 1

# 2. 統合スクリプトを実行
.\wsb_integration.ps1 -JobId 3

# 3. ログを確認
$logFile = ".\logs\backup_integration_$(Get-Date -Format 'yyyyMMdd').log"
Get-Content $logFile -Tail 20

# 4. バックアップ管理システムでステータス確認
Invoke-RestMethod -Uri "http://localhost:5000/api/backup/jobs/3" -Method Get
```

#### AOMEIテスト

```powershell
# 1. AOMEIログディレクトリ確認
$logDir = "C:\Program Files (x86)\AOMEI Backupper\log"
Get-ChildItem $logDir -Filter "*.log" | Select-Object -First 5

# 2. 統合スクリプトを実行
.\aomei_integration.ps1 -JobId 4

# 3. ログを確認
$logFile = ".\logs\backup_integration_$(Get-Date -Format 'yyyyMMdd').log"
Get-Content $logFile -Tail 20

# 4. バックアップ管理システムでステータス確認
Invoke-RestMethod -Uri "http://localhost:5000/api/backup/jobs/4" -Method Get
```

---

## 🚀 本番環境テスト

### 1. タスクスケジューラーの動作確認

```powershell
# 登録されたタスクを即座に実行
$taskName = "BackupManagementSystem_WSB_Job3"
Start-ScheduledTask -TaskName $taskName

# タスクの実行状態を確認
Get-ScheduledTaskInfo -TaskName $taskName

# 実行結果の確認（数秒待機後）
Start-Sleep -Seconds 5
$logFile = ".\logs\backup_integration_$(Get-Date -Format 'yyyyMMdd').log"
Get-Content $logFile -Tail 30 | Select-String "WSB"
```

### 2. 長期間監視テスト

```powershell
# AOMEIログ監視モードを開始（バックグラウンド）
Start-Job -ScriptBlock {
    Set-Location "C:\BackupManagementSystem\scripts\powershell"
    .\aomei_integration.ps1 -JobId 4 -MonitorMode -MonitorIntervalSeconds 300
}

# ジョブの確認
Get-Job

# ログを確認（別のPowerShellセッションから）
Get-Content ".\logs\backup_integration_$(Get-Date -Format 'yyyyMMdd').log" -Wait

# ジョブの停止
Get-Job | Stop-Job
Get-Job | Remove-Job
```

### 3. Veeamポストジョブスクリプトテスト

手動でVeeamジョブを実行し、ポストジョブスクリプトが動作することを確認します。

**手順**:
1. Veeam Backup & Replicationコンソールを開く
2. テスト用ジョブを右クリック → **Start**
3. ジョブ完了後、以下を確認:

```powershell
# ログファイルの確認
$logFile = ".\logs\backup_integration_$(Get-Date -Format 'yyyyMMdd').log"
Get-Content $logFile | Select-String "Veeam"

# APIに送信されたか確認
Invoke-RestMethod -Uri "http://localhost:5000/api/backup/jobs/1/history" -Method Get
```

---

## 🔧 パフォーマンステスト

### スクリプト実行時間の測定

```powershell
# 各スクリプトの実行時間測定
$scripts = @(
    @{ Name = "WSB統合"; Script = ".\wsb_integration.ps1"; Args = @("-JobId", "3") },
    @{ Name = "AOMEI統合"; Script = ".\aomei_integration.ps1"; Args = @("-JobId", "4") }
)

foreach ($test in $scripts) {
    Write-Host "`nテスト: $($test.Name)" -ForegroundColor Cyan
    $elapsed = Measure-Command {
        & $test.Script @($test.Args) 2>&1 | Out-Null
    }
    Write-Host "  実行時間: $($elapsed.TotalSeconds) 秒" -ForegroundColor Gray
}
```

---

## 🐛 トラブルシューティング

### デバッグモードでの実行

```powershell
# PowerShell詳細ログを有効化
$VerbosePreference = "Continue"
$DebugPreference = "Continue"

# スクリプトを実行
.\wsb_integration.ps1 -JobId 3 -Verbose -Debug

# 元に戻す
$VerbosePreference = "SilentlyContinue"
$DebugPreference = "SilentlyContinue"
```

### トランスクリプトログの記録

```powershell
# トランスクリプト開始
$transcriptPath = ".\test_logs\transcript_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $transcriptPath

# テスト実行
.\install.ps1 -TestOnly

# トランスクリプト停止
Stop-Transcript

# トランスクリプトの確認
Get-Content $transcriptPath
```

### エラー詳細の取得

```powershell
# エラー発生時の詳細情報取得
try {
    .\wsb_integration.ps1 -JobId 3
} catch {
    Write-Host "エラー詳細:" -ForegroundColor Red
    Write-Host "  メッセージ: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  スタックトレース:" -ForegroundColor Yellow
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    Write-Host "  エラーレコード:" -ForegroundColor Yellow
    $_ | Format-List * -Force
}
```

---

## ✅ テストチェックリスト

### 必須テスト項目

- [ ] PowerShellバージョン確認（5.1以上）
- [ ] 管理者権限確認
- [ ] スクリプト実行ポリシー確認
- [ ] すべてのスクリプトの構文チェック
- [ ] 共通関数モジュールのテスト
- [ ] 設定ファイルの読み書きテスト
- [ ] ログ記録機能のテスト
- [ ] API接続テスト
- [ ] 各統合スクリプトのテストモード実行
- [ ] タスクスケジューラー登録テスト
- [ ] インストールスクリプトのテスト

### バックアップツール別テスト

#### Veeam Backup & Replication
- [ ] Veeam SnapIn読み込みテスト
- [ ] ジョブ情報取得テスト
- [ ] ポストジョブスクリプト設定
- [ ] 実際のジョブ実行後の動作確認

#### Windows Server Backup
- [ ] WSBコマンドレット利用可能性確認
- [ ] ジョブ履歴取得テスト
- [ ] タスクスケジューラー自動実行テスト

#### AOMEI Backupper
- [ ] ログディレクトリ検出テスト
- [ ] ログファイル解析テスト
- [ ] 監視モードテスト

### 統合テスト
- [ ] インストールプロセス全体
- [ ] エンドツーエンドテスト
- [ ] 長期間監視テスト
- [ ] エラーハンドリングテスト
- [ ] パフォーマンステスト

---

## 📊 テスト結果記録

テスト実施時は以下の形式で結果を記録してください:

```
テスト日時: YYYY-MM-DD HH:MM:SS
テスト環境: Windows Server 2019 / Windows 10
PowerShell: 5.1.XXXXX
管理者権限: はい/いいえ

[構文チェック]
- common_functions.ps1: ✓ PASS
- veeam_integration.ps1: ✓ PASS
- wsb_integration.ps1: ✓ PASS
- aomei_integration.ps1: ✓ PASS
- register_scheduled_tasks.ps1: ✓ PASS
- install.ps1: ✓ PASS

[単体テスト]
- 共通関数: ✓ PASS
- Veeam統合: ✓ PASS
- WSB統合: ✓ PASS
- AOMEI統合: ✓ PASS

[統合テスト]
- インストール: ✓ PASS
- API接続: ✓ PASS
- E2Eテスト: ✓ PASS

[備考]
- 特記事項や問題点
```

---

**このテスト手順書は定期的に更新されます。新しいテストケースや問題が見つかった場合は追記してください。**
