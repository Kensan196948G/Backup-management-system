# Windows本番環境デプロイメントガイド

## 目次

1. [前提条件](#前提条件)
2. [インストール手順](#インストール手順)
3. [設定](#設定)
4. [サービス管理](#サービス管理)
5. [トラブルシューティング](#トラブルシューティング)
6. [アンインストール](#アンインストール)
7. [セキュリティ設定](#セキュリティ設定)

---

## 前提条件

### システム要件

- **OS**: Windows Server 2019以上 / Windows 10/11 Pro以上
- **CPU**: 2コア以上推奨
- **メモリ**: 4GB以上推奨
- **ディスク**: 10GB以上の空き容量

### 必須ソフトウェア

- **Python**: 3.11以上
  - 公式サイト: https://www.python.org/downloads/
  - インストール時は「Add Python to PATH」を有効化

- **管理者権限**: すべてのスクリプトは管理者権限で実行してください

### ネットワーク要件

- ポート5000（HTTP）が利用可能であること
- ファイアウォール設定権限があること

---

## インストール手順

### ステップ1: リポジトリクローン

```powershell
# Gitが利用可能な場合
git clone https://github.com/your-org/backup-management-system.git C:\BackupSystem

# または、ZIPファイルをダウンロードして展開
```

### ステップ2: 環境セットアップ

管理者権限でPowerShellを起動し、以下を実行：

```powershell
cd C:\BackupSystem\deployment\windows

# スクリプト実行ポリシーの設定（初回のみ）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 環境セットアップ実行
.\setup.ps1
```

セットアップスクリプトは以下を自動実行します：

- Python環境の検証
- 仮想環境の作成
- 依存パッケージのインストール
- ディレクトリ構造の作成
- データベースの初期化
- 管理者ユーザーの作成

**対話型プロンプト**:
- 管理者ユーザー名
- 管理者メールアドレス
- 管理者パスワード

### ステップ3: サービスインストール

```powershell
.\install_service.ps1
```

このスクリプトは以下を実行します：

- NSSM（Non-Sucking Service Manager）の取得
- Windowsサービスとして登録
- サービスの起動
- エンドポイント接続確認

### ステップ4: ファイアウォール設定

```powershell
.\configure_firewall.ps1
```

デフォルトでは以下の設定が適用されます：
- HTTPポート: 5000
- 許可ネットワーク: 192.168.3.0/24

カスタム設定:

```powershell
# ポート変更
.\configure_firewall.ps1 -Port 8080

# ネットワーク範囲変更
.\configure_firewall.ps1 -AllowedNetwork "10.0.0.0/8"

# HTTPS有効化
.\configure_firewall.ps1 -AllowHTTPS
```

### ステップ5: インストール確認

```powershell
.\verify_installation.ps1
```

確認項目:
- Python環境
- ディレクトリ構造
- 設定ファイル
- サービス稼働状態
- ネットワークリスニング
- HTTPエンドポイント
- データベース接続

---

## 設定

### 環境設定ファイル (.env)

デフォルトでは `C:\BackupSystem\.env` が作成されます。

#### SECRET_KEY変更（必須）

```powershell
# Pythonでランダムキー生成
python -c "import secrets; print(secrets.token_urlsafe(50))"

# .envファイルを編集
notepad C:\BackupSystem\.env
```

#### メール通知設定（オプション）

```ini
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=backup-system@example.com
MAIL_ADMIN_RECIPIENTS=admin@example.com
```

#### Microsoft Teams通知設定（オプション）

```ini
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxxx
TEAMS_NOTIFY_ON_ERROR=true
TEAMS_NOTIFY_ON_DAILY_REPORT=true
```

### 設定反映

設定変更後はサービスを再起動：

```powershell
Restart-Service BackupManagementSystem
```

---

## サービス管理

### 基本操作

```powershell
# サービス起動
Start-Service BackupManagementSystem

# サービス停止
Stop-Service BackupManagementSystem

# サービス再起動
Restart-Service BackupManagementSystem

# サービス状態確認
Get-Service BackupManagementSystem

# 詳細情報表示
Get-Service BackupManagementSystem | Format-List *
```

### ログ確認

```powershell
# アプリケーションログ
Get-Content C:\BackupSystem\logs\app.log -Tail 50

# サービス標準出力
Get-Content C:\BackupSystem\logs\service_stdout.log -Tail 50

# サービスエラー出力
Get-Content C:\BackupSystem\logs\service_stderr.log -Tail 50

# リアルタイムログ監視
Get-Content C:\BackupSystem\logs\app.log -Wait
```

### NSSM詳細管理

```powershell
# サービス編集
C:\BackupSystem\nssm\nssm.exe edit BackupManagementSystem

# サービス設定確認
C:\BackupSystem\nssm\nssm.exe dump BackupManagementSystem
```

---

## トラブルシューティング

### サービスが起動しない

#### 1. ログファイル確認

```powershell
Get-Content C:\BackupSystem\logs\service_stderr.log -Tail 50
```

#### 2. 手動起動テスト

```powershell
cd C:\BackupSystem
.\venv\Scripts\python.exe .\run.py --production
```

エラーメッセージを確認してください。

#### 3. Python環境確認

```powershell
C:\BackupSystem\venv\Scripts\python.exe --version
C:\BackupSystem\venv\Scripts\pip.exe list
```

#### 4. 依存パッケージ再インストール

```powershell
cd C:\BackupSystem
.\venv\Scripts\pip.exe install -r requirements.txt --force-reinstall
```

### ポートが使用できない

#### ポート使用状況確認

```powershell
Get-NetTCPConnection -LocalPort 5000 -State Listen
netstat -ano | findstr :5000
```

#### プロセス終了

```powershell
# PIDを確認後
Stop-Process -Id <PID> -Force
```

#### ポート変更

1. サービス停止
2. `run.py`のポート設定変更
3. ファイアウォールルール再設定
4. サービス再起動

### データベースエラー

#### データベース再初期化（注意：全データ削除）

```powershell
cd C:\BackupSystem

# バックアップ
Copy-Item .\data\backup_mgmt.db .\data\backup_mgmt.db.backup

# 再初期化
.\venv\Scripts\python.exe .\scripts\init_db.py

# 管理者再作成
.\venv\Scripts\python.exe .\scripts\create_admin.py
```

### ファイアウォールが機能しない

#### ルール確認

```powershell
Get-NetFirewallRule -DisplayName "*Backup Management*" | Format-List *
```

#### ルール再作成

```powershell
cd C:\BackupSystem\deployment\windows
.\configure_firewall.ps1
```

#### Windowsファイアウォール状態確認

```powershell
Get-NetFirewallProfile | Select-Object Name, Enabled
```

### アクセスできない

#### 1. サービス状態確認

```powershell
Get-Service BackupManagementSystem
```

#### 2. ポートリスニング確認

```powershell
Get-NetTCPConnection -LocalPort 5000 -State Listen
```

#### 3. ローカルアクセステスト

```powershell
Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing
```

#### 4. ファイアウォール一時無効化（テスト用のみ）

```powershell
# 無効化（注意）
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# テスト後、必ず有効化
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

---

## アンインストール

### 標準アンインストール（データ保持）

```powershell
cd C:\BackupSystem\deployment\windows
.\uninstall.ps1
```

### データバックアップ付きアンインストール

```powershell
.\uninstall.ps1 -BackupData
```

バックアップは `%TEMP%\BackupSystem_Backup_*` に保存されます。

### 完全アンインストール（データ削除）

```powershell
.\uninstall.ps1 -RemoveData
```

**警告**: データディレクトリも削除されます。必要に応じて事前にバックアップしてください。

---

## セキュリティ設定

### 推奨セキュリティ対策

#### 1. SECRET_KEY変更

デフォルトのSECRET_KEYは必ず変更してください。

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

生成された文字列を `.env` の `SECRET_KEY` に設定。

#### 2. HTTPSの使用

本番環境ではHTTPSを使用することを強く推奨します。

**nginx導入手順**:

1. nginxをダウンロード: http://nginx.org/en/download.html
2. SSL証明書取得（Let's EncryptまたはCA）
3. `deployment/windows/nginx.conf` を参考に設定
4. nginxサービス起動

#### 3. ファイアウォール設定

特定のIPアドレス範囲のみアクセス許可：

```powershell
.\configure_firewall.ps1 -AllowedNetwork "192.168.3.0/24"
```

#### 4. Basic認証追加（nginx使用時）

```powershell
# .htpasswdファイル作成
htpasswd -c C:\nginx\conf\.htpasswd admin
```

nginx.confに以下を追加：

```nginx
auth_basic "Backup Management System";
auth_basic_user_file C:/nginx/conf/.htpasswd;
```

#### 5. データベースバックアップ

定期バックアップスクリプト作成：

```powershell
# backup_database.ps1
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = "C:\BackupSystem\data\backups\backup_mgmt_$timestamp.db"
Copy-Item "C:\BackupSystem\data\backup_mgmt.db" $backupPath
Write-Host "バックアップ完了: $backupPath"

# 30日以上前のバックアップ削除
Get-ChildItem "C:\BackupSystem\data\backups" -Filter "*.db" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item
```

タスクスケジューラで毎日実行：

```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "C:\BackupSystem\backup_database.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
Register-ScheduledTask -TaskName "BackupSystemDBBackup" -Action $action -Trigger $trigger -User "SYSTEM"
```

#### 6. ログローテーション

NSSMのログローテーション設定は自動で有効化されています：

- 最大ファイルサイズ: 10MB
- ローテーション間隔: 24時間

#### 7. 最小権限の原則

専用サービスアカウントでの実行を推奨：

```powershell
# サービスアカウント作成
New-LocalUser -Name "BackupServiceUser" -NoPassword

# サービス実行アカウント変更
sc.exe config BackupManagementSystem obj= ".\BackupServiceUser"

# 必要なディレクトリへのアクセス権付与
icacls "C:\BackupSystem" /grant "BackupServiceUser:(OI)(CI)F" /T
```

---

## パフォーマンスチューニング

### メモリ使用量制限

```powershell
# NSSMでメモリ制限設定
C:\BackupSystem\nssm\nssm.exe set BackupManagementSystem AppThrottle 1500
```

### ワーカープロセス数増加（高負荷環境）

`run.py`を編集：

```python
if __name__ == '__main__':
    app.run(
        host=args.host,
        port=args.port,
        debug=False,
        threaded=True,
        processes=4  # ワーカープロセス数
    )
```

---

## 追加リソース

### 公式ドキュメント

- Flask: https://flask.palletsprojects.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- NSSM: https://nssm.cc/

### コミュニティサポート

- Issues: https://github.com/your-org/backup-management-system/issues
- Wiki: https://github.com/your-org/backup-management-system/wiki

---

## ライセンス

MIT License

---

## 変更履歴

- **2025-10-30**: 初版作成
