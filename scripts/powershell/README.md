# Backup Management System - PowerShell統合

Windows環境のバックアップツール（Veeam、Windows Server Backup、AOMEI Backupper）とバックアップ管理システムを連携させるためのPowerShellスクリプト集です。

## 📋 目次

- [概要](#概要)
- [システム要件](#システム要件)
- [インストール](#インストール)
- [設定](#設定)
- [各スクリプトの説明](#各スクリプトの説明)
- [使用方法](#使用方法)
- [トラブルシューティング](#トラブルシューティング)

---

## 🎯 概要

このスクリプト集は以下の機能を提供します：

- **Veeam Backup & Replication連携**: ジョブ実行後のステータス自動送信
- **Windows Server Backup連携**: ジョブ履歴の定期取得とステータス送信
- **AOMEI Backupper連携**: ログファイル監視とステータス送信
- **自動スケジュール実行**: Windowsタスクスケジューラーによる自動実行
- **統一ログ管理**: すべての実行ログを一元管理
- **エラーハンドリング**: 詳細なエラー記録とリトライ機能

---

## 🖥️ システム要件

### 必須要件

- **OS**: Windows Server 2012 R2以降、またはWindows 10/11
- **PowerShell**: 5.1以降
- **.NET Framework**: 4.5以降
- **管理者権限**: スクリプトの実行とタスクスケジューラー登録に必要

### バックアップツール（いずれか1つ以上）

- **Veeam Backup & Replication**: 9.5以降（PowerShell SnapIn付属）
- **Windows Server Backup**: Windows Server標準機能
- **AOMEI Backupper**: Professional/Server/Technician Edition

---

## 🚀 インストール

### 1. スクリプトの配置

このディレクトリ全体を適切な場所にコピーします。

推奨パス:
```
C:\BackupManagementSystem\scripts\powershell\
```

### 2. 自動インストール（推奨）

管理者権限でPowerShellを起動し、以下を実行：

```powershell
cd C:\BackupManagementSystem\scripts\powershell
.\install.ps1 -ApiUrl "http://your-server:5000" -ApiToken "your-api-token"
```

#### インストールオプション

```powershell
# APIトークンなしでインストール（後で設定）
.\install.ps1 -ApiUrl "http://your-server:5000"

# タスクスケジューラー登録をスキップ
.\install.ps1 -ApiUrl "http://your-server:5000" -SkipTaskRegistration

# テストモードで動作確認のみ
.\install.ps1 -TestOnly
```

### 3. 手動インストール

#### 3.1 スクリプト実行ポリシーの設定

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 3.2 設定ファイルの編集

`config.json`を開いて以下を設定：

```json
{
  "api_url": "http://your-server:5000",
  "api_token": "your-api-token-here",
  "backup_tools": {
    "veeam": {
      "enabled": true,
      "job_ids": [1, 2]
    },
    "wsb": {
      "enabled": true,
      "job_ids": [3]
    },
    "aomei": {
      "enabled": true,
      "job_ids": [4]
    }
  }
}
```

#### 3.3 ログディレクトリの作成

```powershell
New-Item -ItemType Directory -Path ".\logs" -Force
```

#### 3.4 タスクスケジューラーへの登録

```powershell
.\register_scheduled_tasks.ps1
```

---

## ⚙️ 設定

### config.json の詳細設定

```json
{
  "api_url": "http://localhost:5000",
  "api_token": "",

  "backup_tools": {
    "veeam": {
      "enabled": true,
      "job_ids": [1, 2],
      "description": "Veeam Backup & Replication統合"
    },
    "wsb": {
      "enabled": true,
      "job_ids": [3],
      "check_interval_minutes": 60
    },
    "aomei": {
      "enabled": true,
      "job_ids": [4],
      "log_path": "",
      "check_interval_minutes": 60
    }
  },

  "logging": {
    "enabled": true,
    "level": "INFO",
    "retention_days": 30,
    "event_log_enabled": true
  },

  "retry": {
    "enabled": true,
    "max_retries": 3,
    "retry_interval_seconds": 60
  }
}
```

### 設定項目の説明

| 項目 | 説明 | デフォルト値 |
|------|------|-------------|
| `api_url` | バックアップ管理システムのベースURL | `http://localhost:5000` |
| `api_token` | API認証トークン（Bearer認証） | 空文字列 |
| `job_ids` | 各バックアップツールのジョブID配列 | `[1, 2, 3, 4]` |
| `check_interval_minutes` | 定期チェック間隔（分） | `60` |
| `retention_days` | ログファイル保持期間（日） | `30` |
| `max_retries` | API送信失敗時のリトライ回数 | `3` |

---

## 📜 各スクリプトの説明

### 1. common_functions.ps1

共通関数モジュール。他のスクリプトから読み込まれます。

**主な関数**:
- `Get-BackupSystemConfig`: 設定ファイル読み込み
- `Write-BackupLog`: ログ記録
- `Send-BackupStatus`: バックアップステータス送信
- `Send-BackupCopyStatus`: コピーステータス送信
- `Send-BackupExecution`: 実行記録送信

### 2. veeam_integration.ps1

Veeam Backup & Replication連携スクリプト。

**使用方法**:

```powershell
# テストモード
.\veeam_integration.ps1 -TestMode

# ジョブ実行（Veeamポストジョブスクリプトから）
.\veeam_integration.ps1 -JobId 1 -JobName "Backup Job Name"
```

**Veeam設定手順**:

1. Veeam Backup & Replicationコンソールを開く
2. 対象ジョブを右クリック → **Edit**
3. **Storage** → **Advanced** → **Scripts** タブを開く
4. **Run the following script after the job** にチェック
5. スクリプトパスを指定:
   ```
   C:\BackupManagementSystem\scripts\powershell\veeam_integration.ps1
   ```
6. 引数を指定:
   ```
   -JobId 1 -JobName "%job_name%"
   ```

### 3. wsb_integration.ps1

Windows Server Backup連携スクリプト。

**使用方法**:

```powershell
# テストモード
.\wsb_integration.ps1 -TestMode

# 最新ジョブ取得と送信
.\wsb_integration.ps1 -JobId 3
```

**タスクスケジューラー設定**:

タスクスケジューラーで1時間ごとに自動実行されます（自動登録済み）。

### 4. aomei_integration.ps1

AOMEI Backupper連携スクリプト。

**使用方法**:

```powershell
# テストモード
.\aomei_integration.ps1 -TestMode

# 最新ログ解析と送信
.\aomei_integration.ps1 -JobId 4 -TaskName "SystemBackup"

# ログ監視モード（継続的監視）
.\aomei_integration.ps1 -JobId 4 -MonitorMode -MonitorIntervalSeconds 300
```

### 5. register_scheduled_tasks.ps1

タスクスケジューラー管理スクリプト。

**使用方法**:

```powershell
# タスク一括登録
.\register_scheduled_tasks.ps1

# 登録済みタスク一覧表示
.\register_scheduled_tasks.ps1 -List

# タスク削除
.\register_scheduled_tasks.ps1 -Remove

# テストモード
.\register_scheduled_tasks.ps1 -TestMode
```

### 6. install.ps1

インストールスクリプト。セットアップを自動化します。

**使用方法**:

```powershell
# 基本インストール
.\install.ps1 -ApiUrl "http://your-server:5000" -ApiToken "your-token"

# タスク登録をスキップ
.\install.ps1 -ApiUrl "http://your-server:5000" -SkipTaskRegistration

# テストモード
.\install.ps1 -TestOnly
```

---

## 📖 使用方法

### セットアップ完了後の確認

#### 1. 設定ファイルの確認

```powershell
Get-Content .\config.json | ConvertFrom-Json | ConvertTo-Json
```

#### 2. タスクスケジューラーの確認

```powershell
.\register_scheduled_tasks.ps1 -List
```

または、GUIから確認:
1. `Win + R` → `taskschd.msc`
2. **BackupManagementSystem** フォルダーを展開
3. 登録されたタスクを確認

#### 3. テスト実行

各スクリプトをテストモードで実行:

```powershell
.\veeam_integration.ps1 -TestMode
.\wsb_integration.ps1 -TestMode
.\aomei_integration.ps1 -TestMode
```

### 日常運用

#### 自動実行

タスクスケジューラーに登録されたタスクが自動実行されます。

- **WSB**: 1時間ごと
- **AOMEI**: 1時間ごと
- **Veeam**: ジョブ実行後（ポストジョブスクリプト）

#### 手動実行

必要に応じて手動実行できます:

```powershell
# Windows Server Backupの最新ステータスを即座に送信
.\wsb_integration.ps1 -JobId 3

# AOMEIの最新ログを解析して送信
.\aomei_integration.ps1 -JobId 4
```

### ログ確認

#### ログファイルの場所

```
.\logs\backup_integration_YYYYMMDD.log
```

#### ログ確認コマンド

```powershell
# 最新ログを表示
Get-Content .\logs\backup_integration_$(Get-Date -Format 'yyyyMMdd').log -Tail 50

# エラーログのみ表示
Get-Content .\logs\backup_integration_*.log | Select-String "ERROR"

# Windowsイベントログの確認
Get-EventLog -LogName Application -Source BackupManagementSystem -Newest 10
```

---

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. スクリプト実行エラー

**エラー**: `このシステムではスクリプトの実行が無効になっているため...`

**解決方法**:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. API接続エラー

**エラー**: `API送信失敗: 接続できませんでした`

**確認事項**:
- バックアップ管理システムが起動しているか
- `config.json`の`api_url`が正しいか
- ファイアウォールがポートをブロックしていないか

**テスト**:
```powershell
Invoke-RestMethod -Uri "http://your-server:5000/api/health" -Method Get
```

#### 3. 認証エラー

**エラー**: `401 Unauthorized`

**解決方法**:
- `config.json`の`api_token`が正しいか確認
- APIトークンが期限切れでないか確認

#### 4. Veeam SnapIn読み込みエラー

**エラー**: `Veeam PowerShell SnapInの読み込みに失敗`

**解決方法**:
```powershell
# Veeam SnapInの確認
Get-PSSnapin -Registered | Where-Object { $_.Name -like "*Veeam*" }

# 手動で読み込み
Add-PSSnapin VeeamPSSnapIn
```

#### 5. Windows Server Backup が見つからない

**エラー**: `Windows Server Backup機能が利用できません`

**解決方法**:
```powershell
# 機能のインストール（Windows Server）
Install-WindowsFeature Windows-Server-Backup -IncludeManagementTools

# Windows 10/11の場合
# GUIから「Windowsの機能」でWindows Backupを有効化
```

#### 6. AOMEIログが見つからない

**エラー**: `AOMEIログディレクトリが見つかりませんでした`

**解決方法**:
- AOMEI Backupperがインストールされているか確認
- `config.json`の`aomei.log_path`を明示的に設定:

```json
{
  "backup_tools": {
    "aomei": {
      "log_path": "C:\\Program Files (x86)\\AOMEI Backupper\\log"
    }
  }
}
```

#### 7. タスクスケジューラー登録失敗

**エラー**: `タスク登録に失敗`

**確認事項**:
- 管理者権限で実行しているか
- タスクスケジューラーサービスが起動しているか

**サービス確認**:
```powershell
Get-Service Schedule
Start-Service Schedule
```

### ログレベルの変更

デバッグ情報を詳しく記録したい場合:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

### スクリプトの再インストール

問題が解決しない場合、クリーンインストールを試してください:

```powershell
# 既存タスクの削除
.\register_scheduled_tasks.ps1 -Remove

# 再インストール
.\install.ps1 -ApiUrl "http://your-server:5000" -ApiToken "your-token"
```

---

## 📞 サポート

### ログの収集

サポートを依頼する際は、以下の情報を提供してください:

```powershell
# 1. システム情報
$PSVersionTable
Get-ComputerInfo | Select-Object WindowsVersion, OsArchitecture

# 2. 設定ファイル
Get-Content .\config.json

# 3. 最新ログ
Get-Content .\logs\backup_integration_$(Get-Date -Format 'yyyyMMdd').log -Tail 100

# 4. タスク一覧
.\register_scheduled_tasks.ps1 -List
```

---

## 📝 更新履歴

### Version 1.0.0 (2025-10-30)
- 初回リリース
- Veeam、WSB、AOMEI統合機能
- タスクスケジューラー自動登録
- 包括的なエラーハンドリング

---

## 📄 ライセンス

このスクリプト集はバックアップ管理システムの一部として提供されています。

---

## 🔗 関連リンク

- [バックアップ管理システム メインドキュメント](../../README.md)
- [REST API仕様](../../docs/API_SPECIFICATION.md)
- [インストールガイド](../../INSTALLATION.md)

---

**注意**: このREADMEは定期的に更新されます。最新情報は常にGitリポジトリを確認してください。
