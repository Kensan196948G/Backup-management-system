# 環境変数設定ガイド

バックアップ管理システムで使用する全環境変数の詳細説明です。

## 目次

1. [設定ファイルの場所](#設定ファイルの場所)
2. [Flask設定](#flask設定)
3. [データベース設定](#データベース設定)
4. [サーバー設定](#サーバー設定)
5. [セキュリティ設定](#セキュリティ設定)
6. [Veeam統合設定](#veeam統合設定)
7. [メール通知設定](#メール通知設定)
8. [Webhook通知設定](#webhook通知設定)
9. [ログ設定](#ログ設定)
10. [オプション設定](#オプション設定)
11. [環境別テンプレート](#環境別テンプレート)

---

## 設定ファイルの場所

### Linux環境

```bash
# アプリケーションディレクトリ
/opt/backup-management-system/.env

# パーミッション設定（重要）
chmod 600 /opt/backup-management-system/.env
sudo chown backup-mgmt:backup-mgmt /opt/backup-management-system/.env
```

### Windows環境

```cmd
C:\Program Files\BackupManagementSystem\.env

REM アクセス権限設定
icacls "C:\Program Files\BackupManagementSystem\.env" /grant:r "%USERNAME%:F"
```

---

## Flask設定

### FLASK_APP

**用途**: Flaskアプリケーションのエントリーポイント指定

```ini
FLASK_APP=app
```

| 項目 | 値 |
|------|-----|
| 必須 | はい |
| デフォルト | app |
| 説明 | アプリケーションモジュール名 |
| 値の例 | app, application |

### FLASK_ENV

**用途**: 実行環境の指定

```ini
FLASK_ENV=production
```

| 項目 | 値 |
|------|-----|
| 必須 | はい |
| デフォルト | development |
| 有効な値 | development, production |
| 説明 | 環境モード切替 |

**各モードの違い**:

| 項目 | Development | Production |
|------|-------------|-----------|
| デバッグモード | 有効 | 無効 |
| トレースバック | 詳細表示 | 非表示 |
| リロード | 自動 | なし |
| パフォーマンス | 低い | 高い |
| エラーハンドリング | 詳細 | 簡潔 |

### FLASK_DEBUG

**用途**: デバッグモードの有効化（任意）

```ini
FLASK_DEBUG=0
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 0 |
| 有効な値 | 0, 1 |
| 説明 | 1の場合、自動リロードとデバッガーが有効 |

**セキュリティ注意**:
```ini
# 本番環境では必ず 0 に設定
FLASK_DEBUG=0

# 開発環境のみで 1 に設定
# FLASK_DEBUG=1
```

---

## データベース設定

### DATABASE_PATH

**用途**: SQLiteデータベースファイルのパス

```ini
# Linux環境
DATABASE_PATH=/var/lib/backup-mgmt/backup_mgmt.db

# Windows環境
DATABASE_PATH=C:\ProgramData\BackupManagementSystem\data\backup_mgmt.db
```

| 項目 | 値 |
|------|-----|
| 必須 | はい |
| デフォルト | ./backup_mgmt.db |
| パス | 絶対パス推奨 |
| 説明 | SQLiteデータベースファイルの位置 |

**注意事項**:
- ディレクトリは事前に作成しておく
- Flaskプロセスが読み書き可能な権限が必要
- SSDに配置することを推奨
- バックアップ対象に含める

**初期化**:

```bash
# ディレクトリ作成
mkdir -p /var/lib/backup-mgmt

# 所有権設定
sudo chown backup-mgmt:backup-mgmt /var/lib/backup-mgmt
sudo chmod 700 /var/lib/backup-mgmt
```

### SQLALCHEMY_ECHO

**用途**: SQLクエリのログ出力（デバッグ用）

```ini
SQLALCHEMY_ECHO=false
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | false |
| 有効な値 | true, false |
| 説明 | SQLAlchemy実行クエリを標準出力に出力 |

**使用時期**:
- 開発時: `true` (クエリの確認)
- 本番環境: `false` (パフォーマンス重視)

---

## サーバー設定

### HOST

**用途**: バインドするIPアドレス

```ini
# Linux本番環境
HOST=127.0.0.1

# Windows本番環境
HOST=127.0.0.1

# 開発環境（全インターフェイス）
# HOST=0.0.0.0
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 127.0.0.1 |
| 有効な値 | IPアドレス |
| 説明 | Flaskサーバーがリッスンするインターフェイス |

**セキュリティ考慮**:
```ini
# 推奨: ローカルループバック（Nginxプロキシ経由）
HOST=127.0.0.1

# 避ける: すべてのインターフェイス（リバースプロキシなしの場合のみ）
# HOST=0.0.0.0
```

### PORT

**用途**: リッスンするポート番号

```ini
PORT=5000
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 5000 |
| 範囲 | 1-65535 |
| 説明 | Flaskサーバーのポート |

**ポート選択ガイド**:
- 1024未満: 管理者権限必要
- 5000: 開発用デフォルト
- 8000: テスト用
- 3000: フロントエンド

**確認方法**:

```bash
# ポート使用状況確認（Linux）
ss -tlnp | grep 5000

# ポート使用状況確認（Windows）
netstat -ano | findstr :5000
```

---

## セキュリティ設定

### SECRET_KEY

**用途**: セッションとCRFトークンの暗号化キー

```ini
SECRET_KEY=your-very-secure-secret-key-here-min-32-chars
```

| 項目 | 値 |
|------|-----|
| 必須 | はい |
| 最小長 | 32文字 |
| 推奨長 | 64文字以上 |
| 更新頻度 | 3-6ヶ月ごと |
| 説明 | セッション暗号化キー |

**セキュリティ要件**:
- 十分にランダム
- 推測困難
- 本番環境ごとに異なる値
- ソース管理に含めない

**生成方法**:

```bash
# Linux/Mac
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 出力例
# 3eFk7_QhX-mZ9pL2wR8sT4vB5nC6dM0jPqWxYzAu1V
```

**Windows PowerShell**:

```powershell
# 方法1: Base64エンコード
$bytes = [byte[]]::new(32)
$rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
$rng.GetBytes($bytes)
[Convert]::ToBase64String($bytes)

# 方法2: Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**設定例**:

```ini
# 本番環境（例）
SECRET_KEY=8f4a9b2c1d3e5f6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r

# 重要: .envファイルは .gitignore に含める
# .gitignore
.env
```

### SESSION_COOKIE_SECURE

**用途**: HTTPS接続でのみCookieを送信

```ini
SESSION_COOKIE_SECURE=true
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | false |
| 有効な値 | true, false |
| 説明 | HTTPS接続でのみCookie送信 |

**設定ガイド**:
```ini
# HTTPS環境（本番）
SESSION_COOKIE_SECURE=true

# HTTP環境（開発のみ）
SESSION_COOKIE_SECURE=false
```

### SESSION_COOKIE_HTTPONLY

**用途**: JavaScriptからのCookie アクセスを禁止

```ini
SESSION_COOKIE_HTTPONLY=true
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | false |
| 有効な値 | true, false |
| 説明 | XSS対策 |

### SESSION_COOKIE_SAMESITE

**用途**: CSRF攻撃対策

```ini
SESSION_COOKIE_SAMESITE=Lax
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | Lax |
| 有効な値 | Strict, Lax, None |
| 説明 | CSRF保護レベル |

**各オプションの説明**:
- `Strict`: 最も厳密、クロスサイトリクエストでCookie送信なし
- `Lax`: クリック時のみ送信（推奨）
- `None`: Secure属性が必須

### ENABLE_CSRF_PROTECTION

**用途**: CSRF保護の有効化

```ini
ENABLE_CSRF_PROTECTION=true
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | true |
| 有効な値 | true, false |
| 説明 | CSRF保護の有効無効 |

---

## Veeam統合設定

### VEEAM_ENABLED

**用途**: Veeam統合機能の有効化

```ini
VEEAM_ENABLED=true
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | false |
| 有効な値 | true, false |
| 説明 | Veeam統合機能の有効無効 |

### VEEAM_API_URL

**用途**: Veeam REST APIのベースURL

```ini
# Windows環境
VEEAM_API_URL=http://veeam-server:9398

# Linux環境
VEEAM_API_URL=http://192.168.1.100:9398
```

| 項目 | 値 |
|------|-----|
| 必須 | VEEAM_ENABLED=true の場合、はい |
| デフォルト | http://localhost:9398 |
| プロトコル | http または https |
| ポート | デフォルト: 9398 |
| 説明 | Veeamサーバーのアドレス |

**確認方法**:

```bash
# 接続テスト
curl -I http://veeam-server:9398/api/about
```

### VEEAM_USERNAME

**用途**: Veeam API認証ユーザー名

```ini
VEEAM_USERNAME=api-backup-mgmt
```

| 項目 | 値 |
|------|-----|
| 必須 | VEEAM_ENABLED=true の場合、はい |
| 形式 | domain\username または username |
| 説明 | Veeam REST API用のユーザー |

**ユーザー作成方法**:
Veeamコンソール → 設定 → ユーザー管理 → 新規ユーザー追加
- ロール: `Backup Operator`

### VEEAM_PASSWORD

**用途**: Veeam API認証パスワード

```ini
VEEAM_PASSWORD=SecurePassword123!
```

| 項目 | 値 |
|------|-----|
| 必須 | VEEAM_ENABLED=true の場合、はい |
| 最小長 | 12文字以上推奨 |
| 説明 | Veeam API用のパスワード |

**セキュリティ注意**:
```ini
# 本番環境では強力なパスワード
VEEAM_PASSWORD=Com9x#Km$7pL!2qW@5vB&0rT

# .env はバージョン管理外に
echo ".env" >> .gitignore
```

### VEEAM_API_VERSION

**用途**: Veeam REST API バージョン指定

```ini
VEEAM_API_VERSION=1.4
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 1.4 |
| サポート | 1.0-1.5 |
| 説明 | Veeam APIバージョン |

**バージョンマッピング**:
| Veeam Version | API Version |
|---------------|-------------|
| 9.5-10.0 | 1.0-1.1 |
| 11.0 | 1.2-1.3 |
| 12.0 | 1.4-1.5 |

### VEEAM_VERIFY_SSL

**用途**: SSL証明書検証

```ini
# 本番環境（自己署名証明書がない場合）
VEEAM_VERIFY_SSL=true

# 開発環境（自己署名証明書がある場合）
VEEAM_VERIFY_SSL=false
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | true |
| 有効な値 | true, false |
| 説明 | SSL証明書検証の有効無効 |

### VEEAM_POLLING_INTERVAL

**用途**: ジョブ進行状況ポーリング間隔（秒）

```ini
VEEAM_POLLING_INTERVAL=30
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 30 |
| 範囲 | 10-300秒 |
| 説明 | ステータス確認の間隔 |

---

## メール通知設定

### MAIL_SERVER

**用途**: メール送信サーバーのホスト名

```ini
# Gmail
MAIL_SERVER=smtp.gmail.com

# Microsoft 365
MAIL_SERVER=smtp.office365.com

# オンプレミス Exchange
MAIL_SERVER=exchange.company.local

# その他
MAIL_SERVER=mail.example.com
```

| 項目 | 値 |
|------|-----|
| 必須 | メール通知を使用する場合、はい |
| デフォルト | smtp.gmail.com |
| 説明 | SMTPサーバーのアドレス |

### MAIL_PORT

**用途**: SMTPサーバーのポート番号

```ini
# TLS接続（推奨）
MAIL_PORT=587

# SSL接続
MAIL_PORT=465

# 非暗号化（非推奨）
MAIL_PORT=25
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 25 |
| ポート一覧 | 25, 465, 587, 2525 |
| 説明 | SMTP接続ポート |

### MAIL_USE_TLS

**用途**: TLS暗号化接続の有効化

```ini
MAIL_USE_TLS=true
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | false |
| 有効な値 | true, false |
| 説明 | TLS暗号化の有効無効 |

**ポート対応**:
```ini
# ポート 587 → TLS有効
MAIL_PORT=587
MAIL_USE_TLS=true

# ポート 465 → SSL有効
MAIL_PORT=465
MAIL_USE_TLS=false
```

### MAIL_USERNAME

**用途**: メール認証ユーザー名

```ini
# Gmail
MAIL_USERNAME=your-email@gmail.com

# Microsoft 365
MAIL_USERNAME=user@company.onmicrosoft.com

# その他
MAIL_USERNAME=noreply@company.com
```

| 項目 | 値 |
|------|-----|
| 必須 | メール認証が必要な場合、はい |
| 形式 | メールアドレス またはユーザー名 |
| 説明 | SMTP認証ユーザー |

### MAIL_PASSWORD

**用途**: メール認証パスワード

```ini
# Gmail: アプリパスワード（2段階認証有効時）
MAIL_PASSWORD=xxxx xxxx xxxx xxxx

# Microsoft 365: パスワード
MAIL_PASSWORD=YourPassword123!
```

| 項目 | 値 |
|------|-----|
| 必須 | メール認証が必要な場合、はい |
| 説明 | SMTP認証パスワード |

**Gmail設定例**:

1. 2段階認証を有効化
2. アプリパスワードを生成
3. 生成されたパスワード（16文字）をコピー
4. スペースを除いて設定

### MAIL_DEFAULT_SENDER

**用途**: デフォルト送信元アドレス

```ini
MAIL_DEFAULT_SENDER=noreply@company.com
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | noreply@localhost |
| 説明 | 通知メールの送信元 |

---

## Webhook通知設定

### TEAMS_WEBHOOK_URL

**用途**: Microsoft Teams チャネルへの通知

```ini
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxxx/xxxxx/xxxxx
```

| 項目 | 値 |
|------|-----|
| 必須 | Teams通知を使用する場合、はい |
| 説明 | Teams Incoming Webhook URL |
| プロトコル | HTTPS必須 |

**設定方法**:

1. Teams チャネル → コネクタを構成
2. "Incoming Webhook" を追加
3. 表示名と（オプション）イメージを設定
4. URLをコピー

### SLACK_WEBHOOK_URL

**用途**: Slack チャネルへの通知

```ini
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

| 項目 | 値 |
|------|-----|
| 必須 | Slack通知を使用する場合、はい |
| 説明 | Slack Incoming Webhook URL |
| プロトコル | HTTPS必須 |

---

## ログ設定

### LOG_DIR

**用途**: アプリケーションログ保存ディレクトリ

```ini
# Linux
LOG_DIR=/var/log/backup-mgmt

# Windows
LOG_DIR=C:\ProgramData\BackupManagementSystem\logs
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | ./logs |
| パス | 絶対パス推奨 |
| 説明 | ログファイルディレクトリ |

**初期化**:

```bash
# ディレクトリ作成
mkdir -p /var/log/backup-mgmt

# 権限設定
sudo chown backup-mgmt:backup-mgmt /var/log/backup-mgmt
sudo chmod 755 /var/log/backup-mgmt
```

### LOG_LEVEL

**用途**: ログレベル設定

```ini
# 本番環境
LOG_LEVEL=INFO

# 開発環境
LOG_LEVEL=DEBUG
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | INFO |
| 有効な値 | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| 説明 | ログ出力レベル |

**レベルの説明**:
- `DEBUG`: 詳細な開発情報
- `INFO`: 重要な情報
- `WARNING`: 警告
- `ERROR`: エラー
- `CRITICAL`: 重大なエラー

### LOG_MAX_BYTES

**用途**: ログファイルの最大サイズ（バイト）

```ini
LOG_MAX_BYTES=104857600
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 104857600 (100MB) |
| 説明 | ログローテーション時のファイルサイズ |

### LOG_BACKUP_COUNT

**用途**: ログバックアップファイル数

```ini
LOG_BACKUP_COUNT=10
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 10 |
| 説明 | ローテーション後に保持するファイル数 |

---

## オプション設定

### TIMEZONE

**用途**: タイムゾーン設定

```ini
# Japan
TIMEZONE=Asia/Tokyo

# UTC
TIMEZONE=UTC

# USA
TIMEZONE=America/New_York
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | UTC |
| 説明 | システムのタイムゾーン |

### MAX_CONTENT_LENGTH

**用途**: アップロードファイルの最大サイズ（バイト）

```ini
# 100MB
MAX_CONTENT_LENGTH=104857600

# 500MB
MAX_CONTENT_LENGTH=524288000
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 16777216 (16MB) |
| 説明 | POSTリクエストの最大サイズ |

### SESSION_TIMEOUT

**用途**: セッションタイムアウト時間（秒）

```ini
SESSION_TIMEOUT=1800
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 3600 (1時間) |
| 推奨 | 1800-3600 |
| 説明 | 無操作時のセッション有効期間 |

### PAGINATION_PER_PAGE

**用途**: ページネーション1ページあたりのアイテム数

```ini
PAGINATION_PER_PAGE=20
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | 20 |
| 範囲 | 10-100 |
| 説明 | リスト表示件数 |

### ALLOW_REGISTRATION

**用途**: ユーザー自動登録の有効化

```ini
# 本番環境（推奨）
ALLOW_REGISTRATION=false

# 開発環境
ALLOW_REGISTRATION=true
```

| 項目 | 値 |
|------|-----|
| 必須 | いいえ |
| デフォルト | false |
| 有効な値 | true, false |
| 説明 | 新規ユーザー登録の許可 |

---

## 環境別テンプレート

### 開発環境 (.env.development)

```ini
# Flask
FLASK_APP=app
FLASK_ENV=development
FLASK_DEBUG=1

# Database
DATABASE_PATH=./backup_mgmt.db
SQLALCHEMY_ECHO=true

# Server
HOST=0.0.0.0
PORT=5000

# Security
SECRET_KEY=dev-secret-key-not-secure-for-development-only-1234567890ab
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true
ENABLE_CSRF_PROTECTION=true

# Veeam (オプション)
VEEAM_ENABLED=true
VEEAM_API_URL=http://localhost:9398
VEEAM_USERNAME=admin
VEEAM_PASSWORD=password
VEEAM_VERIFY_SSL=false

# Email (オプション)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=test@gmail.com
MAIL_PASSWORD=test-password

# Logging
LOG_LEVEL=DEBUG
LOG_DIR=./logs

# Options
TIMEZONE=Asia/Tokyo
ALLOW_REGISTRATION=true
```

### テスト環境 (.env.testing)

```ini
FLASK_APP=app
FLASK_ENV=testing
FLASK_DEBUG=0

DATABASE_PATH=/tmp/test_backup_mgmt.db
SQLALCHEMY_ECHO=false

HOST=127.0.0.1
PORT=5555

SECRET_KEY=test-secret-key-for-testing-environment-1234567890abcdef
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true

VEEAM_ENABLED=false

MAIL_SERVER=smtp.localhost
MAIL_PORT=1025

LOG_LEVEL=WARNING
LOG_DIR=/tmp/logs

TIMEZONE=Asia/Tokyo
```

### ステージング環境 (.env.staging)

```ini
FLASK_APP=app
FLASK_ENV=production
FLASK_DEBUG=0

DATABASE_PATH=/var/lib/backup-mgmt-staging/backup_mgmt.db
SQLALCHEMY_ECHO=false

HOST=127.0.0.1
PORT=5000

SECRET_KEY=staging-secret-key-change-this-before-deployment-abcdefghij
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
ENABLE_CSRF_PROTECTION=true

VEEAM_ENABLED=true
VEEAM_API_URL=http://veeam-staging:9398
VEEAM_USERNAME=api-backup-mgmt
VEEAM_PASSWORD=staging-password
VEEAM_VERIFY_SSL=true

MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=noreply@company.onmicrosoft.com
MAIL_PASSWORD=staging-app-password

TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/staging/webhook/url

LOG_LEVEL=INFO
LOG_DIR=/var/log/backup-mgmt-staging
LOG_MAX_BYTES=104857600
LOG_BACKUP_COUNT=14

TIMEZONE=Asia/Tokyo
MAX_CONTENT_LENGTH=104857600
SESSION_TIMEOUT=3600
PAGINATION_PER_PAGE=20
ALLOW_REGISTRATION=false
```

### 本番環境 (.env.production)

```ini
FLASK_APP=app
FLASK_ENV=production
FLASK_DEBUG=0

DATABASE_PATH=/var/lib/backup-mgmt/backup_mgmt.db
SQLALCHEMY_ECHO=false

HOST=127.0.0.1
PORT=5000

SECRET_KEY=production-secret-key-very-secure-random-string-minimum-32-chars-xxxxxxxxxxxx
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Strict
ENABLE_CSRF_PROTECTION=true

VEEAM_ENABLED=true
VEEAM_API_URL=http://veeam-prod:9398
VEEAM_USERNAME=api-backup-mgmt
VEEAM_PASSWORD=production-secure-password
VEEAM_VERIFY_SSL=true
VEEAM_RETRY_COUNT=3
VEEAM_POLLING_INTERVAL=60

MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=noreply@company.com
MAIL_PASSWORD=production-mail-app-password

TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/production/webhook/url

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/production/webhook/url

LOG_LEVEL=WARNING
LOG_DIR=/var/log/backup-mgmt
LOG_MAX_BYTES=104857600
LOG_BACKUP_COUNT=30

TIMEZONE=Asia/Tokyo
MAX_CONTENT_LENGTH=104857600
SESSION_TIMEOUT=1800
PAGINATION_PER_PAGE=20
ALLOW_REGISTRATION=false
```

---

## セッション設定ガイド

### セキュリティ設定チェックリスト

本番環境デプロイメント前の確認:

- [ ] `SECRET_KEY` が十分にランダム（最小32文字）
- [ ] `FLASK_ENV=production`
- [ ] `FLASK_DEBUG=0`
- [ ] `SESSION_COOKIE_SECURE=true` （HTTPS環境）
- [ ] `SESSION_COOKIE_HTTPONLY=true`
- [ ] `ENABLE_CSRF_PROTECTION=true`
- [ ] `.env` ファイルが `.gitignore` に含まれている
- [ ] `.env` ファイルのパーミッションが 600
- [ ] Veeam認証情報が正確
- [ ] メール送信テスト完了
- [ ] ログディレクトリが作成済み
- [ ] SSL証明書が有効（HTTPS環境）

---

## 環境変数の読み込み

### Python コードでの読み込み

```python
import os
from dotenv import load_dotenv

# .env ファイルを読み込み
load_dotenv()

# 変数へのアクセス
SECRET_KEY = os.getenv('SECRET_KEY')
DATABASE_PATH = os.getenv('DATABASE_PATH', './backup_mgmt.db')
VEEAM_ENABLED = os.getenv('VEEAM_ENABLED', 'false').lower() == 'true'
```

### Systemd でのロード

**ファイル: `/etc/systemd/system/backup-management.service`**

```ini
[Service]
EnvironmentFile=/opt/backup-management-system/.env
ExecStart=...
```

---

## トラブルシューティング

### 環境変数が読み込まれない

```bash
# 確認
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('SECRET_KEY'))"

# .env ファイルの確認
cat /opt/backup-management-system/.env | head -5
```

### パスの解釈エラー

```bash
# Windows パスの確認
echo "DATABASE_PATH=C:\\ProgramData\\BackupManagementSystem\\data\\backup_mgmt.db"

# スラッシュでも動作
echo "DATABASE_PATH=C:/ProgramData/BackupManagementSystem/data/backup_mgmt.db"
```

---

**最終更新**: 2024年1月
**バージョン**: 1.0
