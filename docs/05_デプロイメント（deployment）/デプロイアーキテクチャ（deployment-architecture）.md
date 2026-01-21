# デプロイメントアーキテクチャ

バックアップ管理システムの本番環境における技術アーキテクチャ、ネットワーク構成、コンポーネント間の相互作用を説明します。

## 目次

1. [システム全体図](#システム全体図)
2. [ネットワークアーキテクチャ](#ネットワークアーキテクチャ)
3. [コンポーネント詳細](#コンポーネント詳細)
4. [データフロー](#データフロー)
5. [認証フロー](#認証フロー)
6. [通知フロー](#通知フロー)
7. [バックアップツール連携](#バックアップツール連携)
8. [デプロイメントパターン](#デプロイメントパターン)

---

## システム全体図

### C4 モデル - Context（コンテキスト図）

```
┌────────────────────────────────────────────────────────────────┐
│                          End Users                              │
│                    (管理者、バックアップ担当者)                  │
│                                                                  │
│                 Web UI / REST API                               │
└────────────┬───────────────────────────────────────────────────┘
             │
             │ HTTP/HTTPS
             │
┌────────────▼───────────────────────────────────────────────────┐
│                                                                  │
│         Backup Management System (バックアップ管理システム)      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Flask Web Application                            │  │
│  │    ・ダッシュボード ・ジョブ管理 ・レポート              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         REST API / Business Logic                         │  │
│  │   ・バックアップジョブ ・スケジューリング ・通知          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         SQLite Database                                   │  │
│  │   ・ユーザー情報 ・ジョブ定義 ・実行履歴                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────┬──────────────────┬──────────────────┬─────────────┘
              │                  │                  │
              │ Veeam API        │ SMTP             │ Webhook
              │ (BackupJob)      │ (E-mail)         │ (Teams)
              │                  │                  │
┌─────────────▼─┐      ┌─────────▼──┐    ┌─────────▼────────────┐
│ Veeam Backup  │      │ Mail Server│    │  Microsoft Teams /   │
│ & Replication │      │ (SMTP)     │    │ Slack Webhook        │
└───────────────┘      └────────────┘    └──────────────────────┘
```

### C4 モデル - Container（コンテナ図）

```
┌─────────────────────────────────────────────────────────────┐
│                    User's Web Browser                        │
│              (Windows / macOS / Linux)                       │
└────────────┬──────────────────────────────────────────────┬─┘
             │                                              │
             │ HTTP/HTTPS (Port 80/443)                    │
             │                                              │
┌────────────▼──────────────────────────────────────────────▼─┐
│                                                              │
│                        Nginx                                 │
│                  (Reverse Proxy)                             │
│         ・SSL/TLS Termination                               │
│         ・Load Balancing                                    │
│         ・Static File Serving                               │
│                                                              │
│                (Port: 80/443 Listening)                     │
└────────────┬───────────────────────────────────────────────┘
             │
             │ HTTP (Port 5000 - Internal)
             │
┌────────────▼───────────────────────────────────────────────┐
│                                                              │
│              Flask Web Application                           │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Web UI Routes                                       │  │
│   │  ・GET  /dashboard      ・GET  /jobs               │  │
│   │  ・POST /login          ・POST /job/create         │  │
│   └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  REST API Routes                                     │  │
│   │  ・GET  /api/jobs/:id   ・POST /api/jobs            │  │
│   │  ・GET  /api/history    ・DELETE /api/jobs/:id      │  │
│   └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Business Logic Services                             │  │
│   │  ・VeeamService (backup job management)             │  │
│   │  ・NotificationService (alert notification)         │  │
│   │  ・SchedulerService (background tasks)              │  │
│   │  ・ReportService (report generation)                │  │
│   └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Authentication & Authorization                      │  │
│   │  ・JWT Token Validation                              │  │
│   │  ・Role-Based Access Control (RBAC)                 │  │
│   └──────────────────────────────────────────────────────┘  │
│                                                              │
└────────────┬────────────────┬──────────────────┬────────────┘
             │                │                  │
    SQLite   │ Veeam API      │ SMTP/Webhook    │
    Database │                │                 │
             │                │                 │
┌────────────▼─┐   ┌──────────▼─┐   ┌──────────▼────────────┐
│              │   │            │   │                       │
│  SQLite DB   │   │  Veeam B&R │   │  Email / Teams        │
│              │   │  Server    │   │  Notification         │
│              │   │            │   │                       │
│ ・User Info  │   │ REST API   │   │ ・Alerts              │
│ ・Job Config │   │ (Backup)   │   │ ・Reports             │
│ ・History    │   │            │   │                       │
│              │   │            │   │                       │
└──────────────┘   └────────────┘   └───────────────────────┘
```

---

## ネットワークアーキテクチャ

### ネットワーク構成図（Linux環境）

```
┌──────────────────────────────────────────────────────────┐
│                       インターネット                       │
│                    (HTTPS接続のみ推奨)                    │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Port 443 (HTTPS)
                         │
┌────────────────────────▼─────────────────────────────────┐
│                                                            │
│                   Firewall / WAF                           │
│               ・DDoS Protection                            │
│               ・Intrusion Detection                        │
│                                                            │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Port 443 → 80 (Forward)
                         │
┌────────────────────────▼─────────────────────────────────┐
│                                                            │
│                    Nginx (リバースプロキシ)                │
│                                                            │
│  ・Listening: 0.0.0.0:80, 0.0.0.0:443                    │
│  ・SSL/TLS Termination (Let's Encrypt)                   │
│  ・Request Forwarding to Flask (127.0.0.1:5000)          │
│  ・Static File Caching                                    │
│  ・Gzip Compression                                       │
│                                                            │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ localhost:5000
                         │ (Internal Network Only)
                         │
┌────────────────────────▼─────────────────────────────────┐
│                                                            │
│            Flask Web Application (Gunicorn)               │
│                                                            │
│  ・Process: /opt/backup-management-system/venv/...      │
│  ・User: backup-mgmt                                      │
│  ・Workers: 4 (CPU cores dependent)                      │
│  ・Threads: 2 per worker                                  │
│                                                            │
└──┬────────────┬──────────────────┬─────────────────────┘
   │            │                  │
   │ SQLite     │ HTTP/REST        │ Notifications
   │            │ (Veeam API)      │ (SMTP/Webhook)
   │            │                  │
┌──▼──┐    ┌────▼────┐  ┌─────────▼──────────┐
│ DB  │    │ Veeam   │  │ Mail Server /      │
│ Dir │    │ Server  │  │ Teams Endpoint     │
│     │    │ (Port   │  │                    │
│ File│    │ 9398)   │  │ (External Network) │
│ I/O │    │         │  │                    │
└─────┘    └─────────┘  └────────────────────┘
```

### ネットワーク構成図（Windows環境）

```
┌──────────────────────────────────────────────────────────┐
│                    Windows ローカルネットワーク           │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │
┌────────────────────────▼─────────────────────────────────┐
│                                                            │
│           Windows Defender Firewall                       │
│                                                            │
│  ・Inbound Rules:                                         │
│    - Port 5000 (Flask) from localhost                    │
│    - Port 80 (Nginx) from any                             │
│    - Port 443 (Nginx HTTPS) from any                      │
│                                                            │
└────────────────────────┬─────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────┐ ┌────────▼────┐ ┌───────▼──────┐
│              │ │              │ │              │
│ Nginx        │ │ Flask App    │ │ Services     │
│ Service      │ │ Service      │ │ (nssm)       │
│              │ │              │ │              │
│ Port 80/443  │ │ Port 5000    │ │ Other Apps   │
│ → localhost  │ │              │ │              │
│   :5000      │ │              │ │              │
│              │ │              │ │              │
└───────┬──────┘ └────────┬─────┘ └───────┬──────┘
        │                 │                │
        │                 │                │
        └─────────────────┼────────────────┘
                          │
                          │ File I/O
                          │
        ┌─────────────────┼────────────────┐
        │                 │                │
┌───────▼──────┐ ┌────────▼────┐ ┌────────▼─────┐
│              │ │              │ │              │
│ C:\ Drive    │ │ Database     │ │ Logs         │
│ (App)        │ │ (backup_mgmt)│ │              │
│              │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘


┌─────────────────────────────────────────────────────────┐
│        External Network Communication                    │
└────────────────┬────────────────┬──────────────┬────────┘
                 │                │              │
        ┌────────▼────┐  ┌────────▼───┐ ┌──────▼────┐
        │              │  │             │ │           │
        │ Veeam Server │  │ SMTP Server │ │ Webhook   │
        │ (API)        │  │             │ │ (Teams)   │
        │ Port 9398    │  │ Port 587    │ │           │
        │              │  │             │ │           │
        └──────────────┘  └─────────────┘ └───────────┘
```

### ポートマッピング

| サービス | ポート | プロトコル | 範囲 | 説明 |
|----------|--------|-----------|------|------|
| Nginx HTTP | 80 | TCP | 0.0.0.0 | ウェブトラフィック（HTTPSリダイレクト） |
| Nginx HTTPS | 443 | TCP | 0.0.0.0 | セキュアウェブトラフィック |
| Flask | 5000 | TCP | 127.0.0.1 | ローカルのみ（リバースプロキシ経由） |
| SQLite | - | ファイル | ローカル | データベースファイルアクセス |
| Veeam API | 9398 | HTTP | リモート | Veeamサーバーとの通信 |
| SMTP | 587 | TCP | リモート | メール送信 |
| Webhook | 443 | HTTPS | リモート | Teams/Slack通知 |

---

## コンポーネント詳細

### 1. Webサーバー層（Nginx）

**役割**: リバースプロキシ、SSL/TLS終端、静的ファイル配信

**設定**:
```nginx
upstream backup_mgmt {
    server 127.0.0.1:5000;
    keepalive 32;
}

server {
    listen 80;
    listen 443 ssl http2;
    server_name _;
    
    client_max_body_size 100M;
    
    # SSL設定
    ssl_certificate /etc/letsencrypt/live/domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/domain/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # セキュリティヘッダー
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # プロキシ設定
    location / {
        proxy_pass http://backup_mgmt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静的ファイル
    location /static/ {
        alias /opt/backup-management-system/app/static/;
        expires 30d;
    }
}
```

**メリット**:
- SSL/TLSの一元管理
- 複数ワーカーへの負荷分散
- 静的ファイルの高速配信
- セキュリティヘッダー統一

### 2. アプリケーション層（Flask + Gunicorn）

**役割**: ビジネスロジック実行、API提供、認証・認可

**コンポーネント**:

```
Flask Application
├── Web UI Routes
│   ├── /dashboard        - ダッシュボード表示
│   ├── /jobs             - バックアップジョブ一覧
│   ├── /login            - ログイン処理
│   └── /settings         - 設定画面
├── REST API Routes
│   ├── GET  /api/jobs    - ジョブ一覧取得
│   ├── POST /api/jobs    - ジョブ作成
│   ├── GET  /api/jobs/:id- ジョブ詳細取得
│   └── DELETE /api/jobs/:id - ジョブ削除
├── Services
│   ├── VeeamService      - Veeam API連携
│   ├── NotificationService - 通知送信
│   ├── SchedulerService  - スケジューリング
│   └── ReportService     - レポート生成
└── Models
    ├── User              - ユーザー情報
    ├── BackupJob         - バックアップジョブ定義
    └── BackupHistory     - 実行履歴
```

**Gunicorn設定**:
```bash
# Gunicornワーカー構成
gunicorn \
  --bind 127.0.0.1:5000 \
  --workers 4 \
  --threads 2 \
  --worker-class gthread \
  --timeout 120 \
  --access-logfile /var/log/backup-mgmt/access.log \
  --error-logfile /var/log/backup-mgmt/error.log \
  app:app
```

### 3. データストレージ層（SQLite）

**役割**: アプリケーションデータの永続化

**スキーマ**:
```
user
├── id (PK)
├── username (UNIQUE)
├── email
├── password_hash
├── role
└── created_at

backup_job
├── id (PK)
├── name
├── user_id (FK)
├── veeam_id
├── schedule
├── status
└── created_at

backup_history
├── id (PK)
├── job_id (FK)
├── start_time
├── end_time
├── status
├── error_message
└── created_at
```

**最適化**:
- インデックス: job_id, status, created_at
- キャッシング: SQLAlchemy接続プール
- バックアップ: 定期的な完全バックアップ

---

## データフロー

### ジョブ実行フロー

```
┌─────────────────────┐
│   ユーザー操作      │
│  (UI/APIリクエスト) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│  Flask Request Handler  │
│ ・認証・認可チェック    │
│ ・入力値検証           │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Business Logic         │
│ ・BackupJob生成        │
│ ・スケジュール設定     │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Database Save          │
│ ・backup_job テーブル   │
│ ・backup_history記録    │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Veeam API Call         │
│ ・POST /backups/jobs    │
│ ・ポストスクリプト登録  │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Veeam Backup Execution │
│ ・バックアップ実行      │
│ ・進捗レポート送信      │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Post-Job Script        │
│ (Veeam実行)             │
│ ・結果ポーリング        │
│ ・ステータス更新        │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Notification Send      │
│ ・メール送信           │
│ ・Teams通知            │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Completion             │
│ ・フロントエンド更新    │
│ ・ログ記録              │
└─────────────────────────┘
```

### データベース変更フロー

```
Flask App Request
        │
        ▼
SQLAlchemy ORM
        │
        ├─ INSERT/UPDATE/DELETE
        │
        ▼
Connection Pool
        │
        ├─ Connection from pool
        │
        ▼
SQLite Engine
        │
        ├─ Query Parsing
        │ ├─ Optimization
        │ ├─ Execution Plan
        │
        ▼
ACID Transactions
        │
        ├─ Write-Ahead Logging (WAL)
        │ ├─ Transaction Journal
        │ ├─ Durability Guarantee
        │
        ▼
File System (disk-mgmt.db)
        │
        └─ Persistent Storage
```

---

## 認証フロー

### ログイン認証フロー

```
┌─────────────────────────────────────┐
│  ユーザー: ID/パスワード入力        │
│           (Web UI Form)              │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Flask: POST /login                 │
│  ・入力値検証                        │
│  ・SQLインジェクション対策          │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Database Lookup                    │
│  SELECT * FROM user                 │
│  WHERE username = ?                 │
└─────────────┬───────────────────────┘
              │
       ┌──────┴──────┐
       │             │
    見つかった    見つからない
       │             │
       ▼             ▼
┌────────────────┐ エラー
│パスワード検証  │ (ユーザー不在)
│check_password()│
└────────┬───────┘
         │
    ┌────┴────┐
    │          │
  正常      エラー
    │          │
    ▼          ▼
┌──────────────┐ エラー
│JWT Token生成 │ (パスワード誤り)
│encode()      │
└────────┬─────┘
         │
         ▼
┌──────────────┐
│レスポンス    │
│token: xxxxx  │
└────────┬─────┘
         │
         ▼
┌──────────────────────────────────┐
│ ブラウザ: トークンをLocalStorage │
│          または Cookie に保存     │
└──────────────────────────────────┘
```

### API認証フロー

```
┌─────────────────────────────────────┐
│  API Request                        │
│  GET /api/jobs                      │
│  Header: Authorization: Bearer xxx  │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Flask Middleware                   │
│  @auth_required                     │
│  ・トークン抽出                     │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  JWT Validation                     │
│  decode(token, SECRET_KEY)          │
│  ・署名検証                         │
│  ・有効期限確認                     │
└─────────────┬───────────────────────┘
              │
         ┌────┴────┐
         │          │
      有効       無効
         │          │
         ▼          ▼
┌──────────────┐ 401 Unauthorized
│ロード: user  │ Error
│ ID抽出        │
└────────┬─────┘
         │
         ▼
┌──────────────────────────────────┐
│ RBAC Check                       │
│ user.role == 'admin'?           │
└────────┬─────────────────────────┘
         │
    ┌────┴────┐
    │          │
  許可      拒否
    │          │
    ▼          ▼
┌──────────────┐ 403 Forbidden
│リクエスト    │ Error
│処理実行      │
└──────────────┘
```

---

## 通知フロー

### メール通知フロー

```
┌──────────────────────────────┐
│ イベント発火                 │
│ (Backup Job完了)             │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ NotificationService呼び出し  │
│ .send_email()                │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Email Template Render        │
│ Jinja2 Template処理          │
│ ・タイトル、本文、スタイル   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ SMTP接続                     │
│ Server: smtp.gmail.com       │
│ Port: 587 (TLS)              │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Email送信                    │
│ FROM: app@example.com        │
│ TO: user@example.com         │
└──────────┬───────────────────┘
           │
    ┌──────┴──────┐
    │             │
  成功        失敗
    │             │
    ▼             ▼
ログ記録      リトライ
            (最大3回)
```

### Teams Webhook 通知フロー

```
┌──────────────────────────────┐
│ イベント発火                 │
│ (Backup Job失敗)             │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ NotificationService呼び出し  │
│ .send_teams_notification()   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Team メッセージ構築          │
│ (JSON形式)                   │
│ ・タイトル、説明、リンク     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ HTTPS POST                   │
│ TO: Team Webhook URL         │
│ Content-Type: application/json
└──────────┬───────────────────┘
           │
    ┌──────┴──────┐
    │             │
  成功        失敗
    │             │
    ▼             ▼
Teams投稿    エラーログ
```

---

## バックアップツール連携

### Veeam Backup & Replication 統合アーキテクチャ

```
┌─────────────────────────────────────┐
│ Veeam Backup & Replication Server   │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Backup Job Configuration    │  │
│  │  ・ジョブ定義                │  │
│  │  ・スケジュール              │  │
│  │  ・リソース割当              │  │
│  └──────────────────────────────┘  │
│                  │                  │
│                  ▼                  │
│  ┌──────────────────────────────┐  │
│  │  REST API Interface          │  │
│  │  ・Port: 9398                │  │
│  │  ・Authentication: OAuth2    │  │
│  │  ・Endpoints: /backups/jobs  │  │
│  └──────────────────────────────┘  │
│                                     │
└────────────────┬────────────────────┘
                 │
                 │ API Calls
                 │ (HTTP)
                 │
┌────────────────▼────────────────────┐
│ Backup Management System             │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ VeeamService                   │ │
│  │ ・Job CRUD Operations          │ │
│  │ ・Status Polling               │ │
│  │ ・Error Handling               │ │
│  └────────────────────────────────┘ │
│                   │                  │
│                   ▼                  │
│  ┌────────────────────────────────┐ │
│  │ Async Task Queue               │ │
│  │ (Celery / APScheduler)         │ │
│  │ ・Background Job Processing    │ │
│  │ ・Status Updates               │ │
│  │ ・Notifications                │ │
│  └────────────────────────────────┘ │
│                   │                  │
│                   ▼                  │
│  ┌────────────────────────────────┐ │
│  │ Database Update                │ │
│  │ ・Job Status                   │ │
│  │ ・Execution History            │ │
│  └────────────────────────────────┘ │
│                                      │
└──────────────────────────────────────┘


┌──────────────────────────────────────┐
│ Veeam Post-Job Script                │
│ (PowerShell / Bash)                  │
│                                      │
│ ┌────────────────────────────────┐  │
│ │ curl -X POST                   │  │
│ │ http://backup-mgmt:5000/api    │  │
│ │ /veeam/job-complete            │  │
│ │ -d '{status, result, ...}'     │  │
│ └────────────────────────────────┘  │
│                                      │
└──────────────────────────────────────┘
```

### API連携シーケンス図

```
Veeam Server         Backup Mgmt System    Database     User/Teams
     │                       │               │              │
     │                       │               │              │
     │<──────GET /jobs───────│               │              │
     │                       │               │              │
     │──────Job List─────────>               │              │
     │                       │               │              │
     │                       │─────Query──────              │
     │                       │<──────────────|              │
     │                       │               │              │
     │<──POST /jobs (new)────│               │              │
     │                       │               │              │
     │───────Job Created─────>               │              │
     │                       │               │              │
     │  [Job Execution]      │               │              │
     │                       │               │              │
     │ (Post-Job Script)     │               │              │
     │─────Call Webhook──────>               │              │
     │                       │               │              │
     │                       │─────Insert────>              │
     │                       │<──────────────|              │
     │                       │               │              │
     │                       │──────Send Alert────────────>
     │                       │               │              │
     │                       │<────────ACK──────────────────
```

---

## デプロイメントパターン

### シングルサーバーデプロイメント（中小企業向け）

```
┌──────────────────────────────────────┐
│        Single Server                 │
│    (Linux or Windows)                │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ Nginx + Flask + SQLite         │ │
│  │ ・Web Server                   │ │
│  │ ・Application                  │ │
│  │ ・Database                     │ │
│  └────────────────────────────────┘ │
│                                      │
│  Storage:                            │
│  ・/var/lib/backup-mgmt/             │
│  ・/var/log/backup-mgmt/             │
│                                      │
└──────────────────────────────────────┘

利点:
・シンプル
・低コスト
・管理容易

制限:
・スケーラビリティ低い
・SPOF（Single Point of Failure）
・パフォーマンス限定
```

### マルチサーバーデプロイメント（エンタープライズ向け）

```
┌──────────────────────────────────────────┐
│         Load Balancer                    │
│      (Nginx / HAProxy)                   │
└───────────┬──────────────────────────────┘
            │
     ┌──────┴──────┬──────────┐
     │             │          │
┌────▼──┐ ┌────────▼──┐ ┌─────▼─────┐
│Web 1  │ │Web 2      │ │Web 3      │
│Nginx+ │ │Nginx+     │ │Nginx+     │
│Flask  │ │Flask      │ │Flask      │
│:5001  │ │:5002      │ │:5003      │
└────┬──┘ └────┬──────┘ └─────┬─────┘
     │         │              │
     └─────────┬──────────────┘
               │
      ┌────────▼────────┐
      │  Shared Database│
      │  (PostgreSQL)   │
      │  + Replication  │
      └────────────────┘

利点:
・高可用性
・スケーラビリティ
・負荷分散
・冗長性

構成:
・複数のWeb/App層
・共有データベース
・セッション管理の統一
・ロードバランシング
```

---

## パフォーマンスと スケーラビリティ

### 推奨構成

| 企業規模 | ユーザー数 | サーバー | CPU | メモリ | DB |
|---------|-----------|---------|-----|--------|-----|
| 小規模 | < 50 | 1台 | 4cores | 8GB | SQLite |
| 中規模 | 50-500 | 2-3台 | 4cores | 16GB | PostgreSQL |
| 大規模 | > 500 | 4+台 | 8cores | 32GB+ | PostgreSQL + Replication |

### キャッシング戦略

```
ブラウザキャッシュ (30日)
        │
        ▼
CDN キャッシュ (1時間)
        │
        ▼
Nginx キャッシュ (5分)
        │
        ▼
Flask/アプリケーション層
        │
        ▼
Redis キャッシュ (セッション、ジョブ状態)
        │
        ▼
SQLite / Database
```

---

## セキュリティアーキテクチャ

```
┌────────────────────────────────────────┐
│         Firewall / WAF                 │
│    DDoS Protection, Rate Limiting      │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│      HTTPS/TLS Encryption              │
│     (Let's Encrypt Certificate)        │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│    Nginx Security Headers              │
│  X-Frame-Options, CSP, HSTS            │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│   Flask Authentication & CSRF          │
│   JWT Tokens, CSRF Protection          │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│   Application-level Authorization      │
│   RBAC (Role-Based Access Control)     │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│   Database Encryption                  │
│   Sensitive Data Hashing                │
└────────────────────────────────────────┘
```

---

## 監視とロギング

### 監視レイヤー

```
Application Logs
├─ /var/log/backup-mgmt/app.log
├─ /var/log/backup-mgmt/error.log
└─ /var/log/backup-mgmt/access.log

System Logs
├─ journalctl (systemd)
├─ /var/log/nginx/access.log
└─ /var/log/nginx/error.log

Metrics
├─ CPU Usage
├─ Memory Usage
├─ Disk I/O
├─ Request Count
└─ Response Time

Alerts
├─ High Error Rate
├─ Service Down
├─ Disk Full
└─ Memory Warning
```

---

## まとめ

このアーキテクチャは以下を実現しています:

1. **スケーラビリティ**: 需要に応じた拡張が可能
2. **高可用性**: 障害時の冗長性確保
3. **セキュリティ**: 多層防御と暗号化
4. **保守性**: モジュール化された設計
5. **パフォーマンス**: 最適化されたリソース利用

---

**最終更新**: 2024年1月
**バージョン**: 1.0
