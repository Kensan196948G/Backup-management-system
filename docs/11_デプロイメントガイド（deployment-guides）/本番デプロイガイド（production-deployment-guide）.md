# 🚀 本番環境デプロイガイド - 3-2-1-1-0 Backup Management System

**最終更新**: 2025年11月2日
**対象環境**: Windows 11 Enterprise (本番) / Linux (開発)
**バージョン**: 1.0.0

---

## 📋 目次

1. [事前準備](#事前準備)
2. [環境設定](#環境設定)
3. [データベース移行](#データベース移行)
4. [セキュリティ設定](#セキュリティ設定)
5. [サービス化](#サービス化)
6. [動作確認](#動作確認)
7. [トラブルシューティング](#トラブルシューティング)

---

## 📦 事前準備

### 必要なソフトウェア

#### Windows本番環境
- ✅ Windows 11 Enterprise (64-bit)
- ✅ Python 3.11.x または 3.12.x
- ✅ NSSM (Non-Sucking Service Manager) 2.24+
- ✅ AOMEI Backupper Professional (オプション)

#### 確認コマンド
```powershell
# Python バージョン確認
python --version

# pip バージョン確認
pip --version

# Git バージョン確認
git --version
```

### システム要件

| 項目 | 最小要件 | 推奨要件 |
|------|---------|---------|
| CPU | 2コア | 4コア以上 |
| RAM | 4GB | 8GB以上 |
| ストレージ | 20GB | 100GB以上 (SSD推奨) |
| OS | Windows 10 | Windows 11 Enterprise |

---

## ⚙️ 環境設定

### 1. プロジェクトディレクトリの準備

```powershell
# 本番用ディレクトリの作成
New-Item -ItemType Directory -Path "C:\BackupSystem" -Force

# プロジェクトファイルのコピー（開発環境から）
# 方法A: Git Clone
cd C:\BackupSystem
git clone https://github.com/Kensan196948G/backup-management-system.git .

# 方法B: 直接コピー（開発環境が同じマシンの場合）
Copy-Item -Path "/mnt/Linux-ExHDD/backup-management-system/*" -Destination "C:\BackupSystem\" -Recurse
```

### 2. Python仮想環境の作成

```powershell
# 仮想環境作成
cd C:\BackupSystem
python -m venv venv

# 仮想環境アクティベート
.\venv\Scripts\Activate.ps1

# 依存パッケージのインストール
pip install --upgrade pip
pip install -r requirements.txt
```

**重要**: WeasyPrintの依存関係に注意
```powershell
# WeasyPrint用の追加ライブラリ（Windows）
# GTK3 Runtime が必要な場合があります
# https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
```

### 3. 本番環境設定ファイルの作成

**.env.production** を作成:

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_APP=run.py
SECRET_KEY=<生成したセキュアキー>

# Server Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Database Configuration
DATABASE_URL=sqlite:///C:/BackupSystem/data/backup_system_production.db
# または PostgreSQL
# DATABASE_URL=postgresql://user:password@localhost:5432/backup_system

# Security Settings
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PREFERRED_URL_SCHEME=https

# AOMEI Integration
AOMEI_API_KEY=<生成したAPIキー>

# Email Configuration (Optional)
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=backup-system@example.com
MAIL_PASSWORD=<メールパスワード>
MAIL_DEFAULT_SENDER=backup-system@example.com

# Teams Webhook (Optional)
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...

# Logging
LOG_LEVEL=INFO
LOG_FILE=C:/BackupSystem/logs/production.log

# Backup Configuration
BACKUP_DATA_DIR=C:/BackupSystem/data
REPORT_OUTPUT_DIR=C:/BackupSystem/reports
TEMP_RESTORE_DIR=C:/BackupSystem/temp/restore

# Compliance Settings
MIN_COPIES=3
MIN_MEDIA_TYPES=2
OFFLINE_MEDIA_UPDATE_WARNING_DAYS=7

# Performance
WORKERS=4
TIMEOUT=120
```

### 4. セキュアキーの生成

```powershell
# PowerShellでセキュアキー生成
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 出力例:
# xK7n2QpL9mR5vW8yB4cE6gH1jM3oP0sT2uV4xY6zA8bC5dF7gH9iJ1kL3mN5oP7q
```

このキーを `.env.production` の `SECRET_KEY` に設定します。

### 5. API Keyの生成

```powershell
# AOMEI用API Key生成
python -c "from app.models_api_key import ApiKey; print(ApiKey.generate_key())"

# 出力例:
# bms_xK7n2QpL9mR5vW8yB4cE6gH1jM3oP0sT2uV4xY6zA8bC5dF7g
```

このAPI Keyを以下に設定:
1. `.env.production` の `AOMEI_API_KEY`
2. `scripts/powershell/config.json` の `api_key`

---

## 🗄️ データベース移行

### 1. データベースディレクトリの作成

```powershell
# データディレクトリ作成
New-Item -ItemType Directory -Path "C:\BackupSystem\data" -Force
New-Item -ItemType Directory -Path "C:\BackupSystem\logs" -Force
New-Item -ItemType Directory -Path "C:\BackupSystem\reports" -Force
New-Item -ItemType Directory -Path "C:\BackupSystem\temp\restore" -Force
```

### 2. マイグレーションの実行

```powershell
# 環境変数設定
$env:FLASK_ENV = "production"

# データベーステーブル作成
flask db upgrade

# 成功確認
# Output: INFO  [alembic.runtime.migration] Running upgrade -> add_api_key_tables, Add API Key and Refresh Token tables
```

### 3. 管理者ユーザーの作成

```powershell
# 管理者ユーザー作成スクリプト実行
python scripts/create_admin.py
```

または手動で作成:

```python
# Python対話シェルで実行
python
>>> from app import create_app
>>> from app.models import User, db
>>> app = create_app('production')
>>> with app.app_context():
...     admin = User(
...         username='admin',
...         email='admin@example.com',
...         role='admin',
...         is_active=True
...     )
...     admin.set_password('Admin123!')  # 強力なパスワードに変更
...     db.session.add(admin)
...     db.session.commit()
...     print(f"Admin user created: {admin.username}")
```

### 4. データベースバックアップ設定

```powershell
# 自動バックアップスクリプト作成
$backupScript = @"
`$date = Get-Date -Format "yyyyMMdd_HHmmss"
`$source = "C:\BackupSystem\data\backup_system_production.db"
`$destination = "C:\BackupSystem\data\backups\backup_system_`$date.db"
Copy-Item `$source `$destination -Force
# 30日以上古いバックアップを削除
Get-ChildItem "C:\BackupSystem\data\backups" -Filter "*.db" |
    Where-Object { `$_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Force
"@

$backupScript | Out-File -FilePath "C:\BackupSystem\scripts\backup_database.ps1" -Encoding UTF8

# タスクスケジューラーに登録（毎日3:00 AM）
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\BackupSystem\scripts\backup_database.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "BackupSystem-DBBackup" -Action $action -Trigger $trigger -Principal $principal
```

---

## 🔒 セキュリティ設定

### 1. SSL/TLS証明書の設定

#### 自己署名証明書の作成（開発/テスト用）

```powershell
# OpenSSLをインストール（まだの場合）
# https://slproweb.com/products/Win32OpenSSL.html

# 証明書ディレクトリ作成
New-Item -ItemType Directory -Path "C:\BackupSystem\ssl" -Force

# 自己署名証明書生成
openssl req -x509 -newkey rsa:4096 -nodes -out C:\BackupSystem\ssl\cert.pem -keyout C:\BackupSystem\ssl\key.pem -days 365 -subj "/CN=localhost"
```

#### Let's Encrypt証明書（本番用）

```powershell
# Certbotをインストール
# https://certbot.eff.org/

# 証明書取得（nginx経由を推奨）
certbot certonly --standalone -d your-domain.com
```

### 2. ファイアウォール設定

```powershell
# Windows Firewallでポート5000を開放
New-NetFirewallRule -DisplayName "Backup System" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow

# HTTPS用にポート443も開放（リバースプロキシ使用時）
New-NetFirewallRule -DisplayName "Backup System HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
```

### 3. ディレクトリアクセス権限の設定

```powershell
# BackupSystemディレクトリのアクセス権限設定
$acl = Get-Acl "C:\BackupSystem"
$permission = "BUILTIN\Administrators","FullControl","ContainerInherit,ObjectInherit","None","Allow"
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
$acl.SetAccessRule($accessRule)
Set-Acl "C:\BackupSystem" $acl

# データディレクトリはより制限的に
icacls "C:\BackupSystem\data" /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F"
```

### 4. リバースプロキシ設定（オプション - 推奨）

#### nginx設定例

```nginx
# C:\nginx\conf\nginx.conf

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate C:/BackupSystem/ssl/cert.pem;
    ssl_certificate_key C:/BackupSystem/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static {
        alias C:/BackupSystem/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 🔧 サービス化

### NSSM (Non-Sucking Service Manager) を使用

#### 1. NSSMのインストール

```powershell
# Chocolateyでインストール（推奨）
choco install nssm

# または手動ダウンロード
# https://nssm.cc/download
```

#### 2. サービスの登録

```powershell
# サービス登録スクリプト
$serviceName = "BackupManagementSystem"
$pythonExe = "C:\BackupSystem\venv\Scripts\python.exe"
$scriptPath = "C:\BackupSystem\run.py"
$workingDir = "C:\BackupSystem"

# NSSM でサービス登録
nssm install $serviceName $pythonExe $scriptPath --production

# サービス設定
nssm set $serviceName AppDirectory $workingDir
nssm set $serviceName DisplayName "3-2-1-1-0 Backup Management System"
nssm set $serviceName Description "Enterprise Backup Management and Monitoring System"
nssm set $serviceName Start SERVICE_AUTO_START
nssm set $serviceName AppStdout "C:\BackupSystem\logs\service_stdout.log"
nssm set $serviceName AppStderr "C:\BackupSystem\logs\service_stderr.log"
nssm set $serviceName AppRotateFiles 1
nssm set $serviceName AppRotateOnline 1
nssm set $serviceName AppRotateBytes 10485760  # 10MB

# 環境変数設定
nssm set $serviceName AppEnvironmentExtra FLASK_ENV=production

# サービス開始
nssm start $serviceName

# サービスステータス確認
nssm status $serviceName
```

#### 3. サービスの管理

```powershell
# サービス開始
Start-Service BackupManagementSystem

# サービス停止
Stop-Service BackupManagementSystem

# サービス再起動
Restart-Service BackupManagementSystem

# サービスステータス確認
Get-Service BackupManagementSystem

# サービス削除（必要な場合）
nssm remove BackupManagementSystem confirm
```

---

## ✅ 動作確認

### 1. サービス起動確認

```powershell
# サービスステータス確認
Get-Service BackupManagementSystem

# ログ確認
Get-Content C:\BackupSystem\logs\service_stdout.log -Tail 50

# プロセス確認
Get-Process | Where-Object { $_.ProcessName -like "*python*" }
```

### 2. Web UI アクセス確認

```powershell
# ブラウザでアクセス
Start-Process "http://localhost:5000"

# または HTTPS（nginxリバースプロキシ使用時）
Start-Process "https://your-domain.com"
```

### 3. API エンドポイント確認

```powershell
# ヘルスチェック
Invoke-RestMethod -Uri "http://localhost:5000/api/health" -Method GET

# ログイン
$body = @{
    username = "admin"
    password = "Admin123!"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/login" -Method POST -Body $body -ContentType "application/json"
$token = $response.access_token

# 認証確認
$headers = @{
    Authorization = "Bearer $token"
}
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/verify" -Method GET -Headers $headers
```

### 4. AOMEI統合確認

```powershell
# AOMEIスクリプトのテスト実行
cd C:\BackupSystem\scripts\powershell
.\aomei_integration.ps1 -TestMode

# 期待される出力:
# ========================================
# AOMEI Backupper統合スクリプト テストモード
# ========================================
#
# 1. 設定ファイル読み込みテスト... ✓ 成功
# 2. AOMEIログディレクトリ検索テスト... ✓ 成功
# ...
```

### 5. データベース接続確認

```powershell
# Pythonシェルでデータベース確認
python
>>> from app import create_app
>>> from app.models import User, BackupJob, db
>>> app = create_app('production')
>>> with app.app_context():
...     user_count = User.query.count()
...     job_count = BackupJob.query.count()
...     print(f"Users: {user_count}, Jobs: {job_count}")
>>> exit()
```

---

## 🔍 トラブルシューティング

### 問題1: サービスが起動しない

#### 確認事項
```powershell
# サービスログ確認
Get-Content C:\BackupSystem\logs\service_stderr.log -Tail 100

# Python環境確認
C:\BackupSystem\venv\Scripts\python.exe --version

# 依存パッケージ確認
C:\BackupSystem\venv\Scripts\pip.exe list
```

#### 解決策
1. 仮想環境の再作成
2. 依存パッケージの再インストール
3. `.env.production` の設定確認

### 問題2: データベースエラー

```powershell
# データベースファイルの権限確認
icacls "C:\BackupSystem\data\backup_system_production.db"

# マイグレーション状態確認
flask db current

# 必要に応じてマイグレーション再実行
flask db upgrade
```

### 問題3: AOMEI統合が動作しない

```powershell
# API Key確認
$apiKey = $env:AOMEI_API_KEY
Write-Host "API Key: $apiKey"

# config.json確認
Get-Content C:\BackupSystem\scripts\powershell\config.json

# 手動でAPIテスト
$headers = @{ "X-API-Key" = $apiKey }
$body = @{ job_id = 0; task_name = "Test" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/aomei/register" -Method POST -Headers $headers -Body $body -ContentType "application/json"
```

### 問題4: PDF生成エラー

```powershell
# WeasyPrint依存関係確認
python -c "import weasyprint; print(weasyprint.__version__)"

# GTK3 Runtime確認（Windowsの場合）
# https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
# から最新版をダウンロード・インストール

# フォント確認
python -c "from reportlab.pdfbase import pdfmetrics; print(pdfmetrics.getRegisteredFontNames())"
```

---

## 📊 パフォーマンスチューニング

### 1. Waitress設定の最適化

**run.py** の本番設定:

```python
serve(
    app,
    host='0.0.0.0',
    port=5000,
    threads=8,  # CPUコア数に応じて調整 (推奨: コア数 x 2)
    channel_timeout=120,
    cleanup_interval=30,
    max_request_body_size=104857600,  # 100MB
)
```

### 2. データベース最適化

```python
# config.py に追加
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 20
}
```

### 3. キャッシュ設定（Redis使用時）

```python
# config.py
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://localhost:6379/0'
CACHE_DEFAULT_TIMEOUT = 300
```

---

## 📝 運用チェックリスト

### デプロイ前
- [ ] `.env.production` 設定完了
- [ ] SECRET_KEY生成・設定
- [ ] API Key生成・設定
- [ ] SSL証明書設定（本番環境）
- [ ] データベースマイグレーション実行
- [ ] 管理者ユーザー作成
- [ ] ファイアウォール設定
- [ ] ディレクトリアクセス権限設定

### デプロイ後
- [ ] サービス起動確認
- [ ] Web UI アクセス確認
- [ ] API エンドポイント確認
- [ ] ログイン機能確認
- [ ] AOMEI統合確認
- [ ] レポート生成確認
- [ ] 検証機能確認
- [ ] スケジューラー動作確認

### 運用開始後
- [ ] 日次バックアップ設定
- [ ] ログローテーション設定
- [ ] モニタリング設定
- [ ] アラート設定
- [ ] ユーザートレーニング実施

---

## 📞 サポート

### 問い合わせ先
- GitHub Issues: https://github.com/Kensan196948G/backup-management-system/issues
- Email: support@backup-system.com

### ドキュメント
- [README.md](README.md)
- [IMPLEMENTATION_COMPLETE_2025.md](IMPLEMENTATION_COMPLETE_2025.md)
- [docs/](docs/)

---

**最終更新**: 2025年11月2日
**バージョン**: 1.0.0
