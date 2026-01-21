# デプロイメント完全ガイド

バックアップ管理システムの本番環境デプロイメント手順書です。Windows/Linux両環境に対応しています。

## 目次

1. [前提条件](#前提条件)
2. [Windowsデプロイメント](#windowsデプロイメント)
3. [Linuxデプロイメント](#linuxデプロイメント)
4. [セキュリティ設定](#セキュリティ設定)
5. [パフォーマンスチューニング](#パフォーマンスチューニング)
6. [トラブルシューティング](#トラブルシューティング)
7. [ロールバック手順](#ロールバック手順)

---

## 前提条件

### 必須ソフトウェア

#### Windows環境

- **OS**: Windows Server 2016以上 または Windows 10/11 Pro以上
- **Python**: 3.9以上
- **Git**: 最新バージョン（オプション）

チェックリスト:
- [ ] Pythonがインストール済みであることを確認
- [ ] `python --version` で確認（3.9以上）
- [ ] pip が利用可能であることを確認
- [ ] 管理者権限でコマンドプロンプトを開く権限がある

#### Linux環境

- **OS**: CentOS 7以上、Ubuntu 18.04以上、Debian 9以上
- **Python**: 3.9以上
- **systemd**: システム管理用

チェックリスト:
- [ ] `python3 --version` で確認（3.9以上）
- [ ] pip3 がインストール済み
- [ ] systemd が利用可能（`systemctl --version` で確認）
- [ ] sudo 権限がある
- [ ] ポート 5000（デフォルト）が利用可能

### ハードウェア要件

| 項目 | 最小要件 | 推奨要件 |
|------|----------|----------|
| CPU | 2コア | 4コア |
| メモリ | 4GB | 8GB |
| ストレージ | 10GB | 50GB |
| ネットワーク | 1Gbps | 10Gbps |

### 事前準備

#### 1. リポジトリの取得

```bash
# Gitを使用する場合
git clone <リポジトリURL> /opt/backup-management-system

# または手動でダウンロード
# リリースページからzipをダウンロード
unzip backup-management-system.zip -d /opt/
```

#### 2. ディレクトリ所有権の確認

**Linux環境の場合:**

```bash
# 専用ユーザーの作成（推奨）
sudo useradd -m -d /var/lib/backup-mgmt -s /bin/bash backup-mgmt

# ディレクトリの所有権設定
sudo chown -R backup-mgmt:backup-mgmt /opt/backup-management-system
sudo chown -R backup-mgmt:backup-mgmt /var/lib/backup-mgmt
```

**Windows環境の場合:**

```cmd
# アプリケーションディレクトリの作成
mkdir "C:\Program Files\BackupManagementSystem"
mkdir "C:\ProgramData\BackupManagementSystem\logs"
mkdir "C:\ProgramData\BackupManagementSystem\data"
```

#### 3. ネットワークの確認

```bash
# ファイアウォール設定確認
# ポート5000がインバウンド許可されているか確認
# Veeamサーバーからのアクセスが可能か確認
```

---

## Windowsデプロイメント

### ステップ1: Python仮想環境のセットアップ

#### 1.1 仮想環境の作成

```cmd
REM コマンドプロンプトを管理者として実行

cd C:\Program Files\BackupManagementSystem

REM 仮想環境の作成
python -m venv venv

REM 仮想環境の有効化
venv\Scripts\activate.bat
```

**確認:**
```cmd
REM プロンプトが (venv) で始まるか確認
(venv) C:\Program Files\BackupManagementSystem>
```

#### 1.2 依存ライブラリのインストール

```cmd
REM 仮想環境が有効化されている状態で実行

pip install --upgrade pip setuptools wheel

REM 依存ライブラリのインストール
pip install -r requirements.txt

REM インストール確認
pip list
```

**トラブル時:**
- `pip install -r requirements.txt --no-cache-dir` で再度実行
- 特定のパッケージでエラーが出た場合は、ログを確認してください

### ステップ2: 環境設定

#### 2.1 環境変数ファイルの作成

```cmd
REM .env.example をコピーして .env を作成
copy .env.example .env

REM メモ帳で編集
notepad .env
```

#### 2.2 必須環境変数の設定

`.env` ファイルで以下を設定してください:

```ini
# Flask設定
FLASK_APP=app
FLASK_ENV=production
SECRET_KEY=your-very-secure-secret-key-here-min-32-chars

# データベース（推奨: C:\ProgramData配下）
DATABASE_PATH=C:\ProgramData\BackupManagementSystem\data\backup_mgmt.db

# ログディレクトリ
LOG_DIR=C:\ProgramData\BackupManagementSystem\logs

# サーバー設定
HOST=0.0.0.0
PORT=5000

# セキュリティ
ENABLE_CSRF_PROTECTION=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

# Veeam連携（必要に応じて設定）
VEEAM_API_URL=http://veeam-server:9398
VEEAM_API_TOKEN=your-token-here

# メール通知（オプション）
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

**SECRET_KEY生成方法:**

```cmd
REM Python対話シェルで実行
python

import secrets
secrets.token_urlsafe(32)
# 出力をコピーして使用
```

#### 2.3 ディレクトリの作成

```cmd
REM ログディレクトリ作成
mkdir "C:\ProgramData\BackupManagementSystem\logs"
mkdir "C:\ProgramData\BackupManagementSystem\data"

REM アプリケーションディレクトリの確認
dir /B C:\Program Files\BackupManagementSystem
```

### ステップ3: データベース初期化

```cmd
REM 仮想環境が有効化されている状態で実行

python
```

```python
# Pythonシェル内で実行
from app import create_app, db
from app.models import User, BackupJob, BackupHistory

app = create_app()
with app.app_context():
    db.create_all()
    print("データベース初期化完了")
    
exit()
```

### ステップ4: Windowsサービスとして登録

#### 4.1 nssm（Non-Sucking Service Manager）のインストール

```cmd
REM nssmダウンロード
REM https://nssm.cc/download からダウンロード

REM または、WinGetを使用（Windows 11の場合）
winget install nssm
```

#### 4.2 サービスの登録

```cmd
REM 管理者権限で実行

cd C:\Program Files\nssm\win64

REM サービスの登録
nssm install BackupManagementSystem "C:\Program Files\BackupManagementSystem\venv\Scripts\python.exe" "-m flask run"

REM サービスの詳細設定
nssm set BackupManagementSystem AppDirectory "C:\Program Files\BackupManagementSystem"
nssm set BackupManagementSystem AppEnvironmentExtra FLASK_APP=app
nssm set BackupManagementSystem AppEnvironmentExtra FLASK_ENV=production
nssm set BackupManagementSystem AppStdout "C:\ProgramData\BackupManagementSystem\logs\app.log"
nssm set BackupManagementSystem AppStderr "C:\ProgramData\BackupManagementSystem\logs\error.log"

REM ログファイルの自動ローテーション設定
nssm set BackupManagementSystem AppRotateFiles 1
nssm set BackupManagementSystem AppRotateOnline 1
nssm set BackupManagementSystem AppRotateSeconds 86400
nssm set BackupManagementSystem AppRotateBytes 104857600
```

#### 4.3 サービスの起動

```cmd
REM サービスの起動
net start BackupManagementSystem

REM ステータス確認
nssm status BackupManagementSystem

REM ログの確認
type "C:\ProgramData\BackupManagementSystem\logs\app.log"
```

### ステップ5: Nginxのセットアップ（リバースプロキシ）

#### 5.1 Nginxのインストール

```cmd
REM WinGetでインストール
winget install nginx

REM または手動ダウンロード
REM https://nginx.org/en/download.html
```

#### 5.2 Nginx設定

**ファイル: `C:\nginx\conf\nginx.conf`**

```nginx
upstream backup_mgmt {
    server localhost:5000;
    keepalive 32;
}

server {
    listen 80;
    server_name localhost;

    # リダイレクト設定（HTTPSへ）
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://backup_mgmt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静的ファイルのキャッシュ
    location /static/ {
        proxy_pass http://backup_mgmt;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 5.3 Nginxサービスの起動

```cmd
REM Nginxの起動テスト
nginx -t

REM Nginxサービスとして登録
nssm install Nginx "C:\nginx\nginx.exe"

REM サービスの起動
net start Nginx
```

### ステップ6: ファイアウォール設定

```cmd
REM ポート5000をファイアウォールで許可
netsh advfirewall firewall add rule name="Flask Application" dir=in action=allow protocol=tcp localport=5000

REM ポート80をファイアウォールで許可
netsh advfirewall firewall add rule name="Nginx HTTP" dir=in action=allow protocol=tcp localport=80

REM ポート443をファイアウォールで許可（HTTPS使用時）
netsh advfirewall firewall add rule name="Nginx HTTPS" dir=in action=allow protocol=tcp localport=443

REM ルール確認
netsh advfirewall firewall show rule name="Flask Application"
```

### ステップ7: 動作確認

```cmd
REM ブラウザで確認
REM http://localhost/

REM または、コマンドラインで確認
curl http://localhost/

REM アプリケーションログの確認
type "C:\ProgramData\BackupManagementSystem\logs\app.log"
```

---

## Linuxデプロイメント

### ステップ1: システム準備

#### 1.1 パッケージ更新

```bash
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL の場合
# sudo yum update -y
```

#### 1.2 依存パッケージのインストール

```bash
# Debian/Ubuntu
sudo apt install -y python3.9 python3-pip python3-venv git nginx curl

# CentOS/RHEL
# sudo yum install -y python39 python39-pip python39-devel nginx curl git

# Python 3.9 が デフォルトであることを確認
python3 --version
```

### ステップ2: アプリケーションディレクトリのセットアップ

```bash
# アプリケーションディレクトリの作成
sudo mkdir -p /opt/backup-management-system
sudo mkdir -p /var/lib/backup-mgmt
sudo mkdir -p /var/log/backup-mgmt

# 専用ユーザーの作成（既に作成済みの場合はスキップ）
sudo useradd -m -d /var/lib/backup-mgmt -s /bin/bash backup-mgmt 2>/dev/null || true

# 所有権の設定
sudo chown -R backup-mgmt:backup-mgmt /opt/backup-management-system
sudo chown -R backup-mgmt:backup-mgmt /var/lib/backup-mgmt
sudo chown -R backup-mgmt:backup-mgmt /var/log/backup-mgmt

# パーミッション設定
sudo chmod 755 /opt/backup-management-system
sudo chmod 755 /var/lib/backup-mgmt
sudo chmod 755 /var/log/backup-mgmt
```

### ステップ3: リポジトリのセットアップ

```bash
# リポジトリのクローン（またはダウンロード）
cd /opt/backup-management-system
sudo git clone <リポジトリURL> . 2>/dev/null || echo "リポジトリは手動でセットアップしてください"

# ファイルの所有権確認
sudo chown -R backup-mgmt:backup-mgmt /opt/backup-management-system
```

### ステップ4: Python仮想環境のセットアップ

```bash
# backup-mgmt ユーザーで実行するために、スイッチ
sudo -u backup-mgmt bash -c 'cd /opt/backup-management-system && python3 -m venv venv'

# 仮想環境の有効化
source /opt/backup-management-system/venv/bin/activate

# 依存ライブラリのインストール
pip install --upgrade pip setuptools wheel
pip install -r /opt/backup-management-system/requirements.txt
```

### ステップ5: 環境設定

```bash
# 環境変数ファイルの作成
sudo -u backup-mgmt cp /opt/backup-management-system/.env.example /opt/backup-management-system/.env

# 編集
sudo nano /opt/backup-management-system/.env
```

`.env` ファイルの内容例:

```ini
# Flask設定
FLASK_APP=app
FLASK_ENV=production
SECRET_KEY=your-very-secure-secret-key-here-min-32-chars

# データベース
DATABASE_PATH=/var/lib/backup-mgmt/backup_mgmt.db

# ログディレクトリ
LOG_DIR=/var/log/backup-mgmt

# サーバー設定
HOST=127.0.0.1
PORT=5000

# セキュリティ
ENABLE_CSRF_PROTECTION=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

# Veeam連携（必要に応じて）
VEEAM_API_URL=http://veeam-server:9398
VEEAM_API_TOKEN=your-token-here

# メール通知（オプション）
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

**SECRET_KEY生成:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### ステップ6: データベース初期化

```bash
# backup-mgmt ユーザーで実行
sudo -u backup-mgmt bash -c 'cd /opt/backup-management-system && source venv/bin/activate && python3 << EOF
from app import create_app, db
from app.models import User, BackupJob, BackupHistory

app = create_app()
with app.app_context():
    db.create_all()
    print("データベース初期化完了")
EOF'
```

### ステップ7: systemd サービスの設定

#### 7.1 サービスファイルの作成

**ファイル: `/etc/systemd/system/backup-management.service`**

```ini
[Unit]
Description=Backup Management System
After=network.target

[Service]
Type=notify
User=backup-mgmt
Group=backup-mgmt
WorkingDirectory=/opt/backup-management-system
Environment="PATH=/opt/backup-management-system/venv/bin"
Environment="FLASK_APP=app"
Environment="FLASK_ENV=production"
ExecStart=/opt/backup-management-system/venv/bin/python -m flask run --host=127.0.0.1 --port=5000
Restart=on-failure
RestartSec=5s

# セキュリティ設定
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true

# ログ設定
StandardOutput=journal
StandardError=journal
SyslogIdentifier=backup-mgmt

[Install]
WantedBy=multi-user.target
```

#### 7.2 サービスの有効化と起動

```bash
# サービスファイルの再読み込み
sudo systemctl daemon-reload

# サービスの有効化（自動起動）
sudo systemctl enable backup-management.service

# サービスの起動
sudo systemctl start backup-management.service

# ステータス確認
sudo systemctl status backup-management.service

# ログの確認
sudo journalctl -u backup-management.service -f
```

### ステップ8: Nginxのセットアップ

#### 8.1 Nginx設定ファイルの作成

**ファイル: `/etc/nginx/sites-available/backup-management`**

```nginx
upstream backup_mgmt {
    server 127.0.0.1:5000;
    keepalive 32;
}

server {
    listen 80;
    server_name _;
    client_max_body_size 100M;

    # HTTPをHTTPSにリダイレクト（HTTPS設定後）
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://backup_mgmt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # タイムアウト設定
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # バッファ設定
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }

    location /static/ {
        alias /opt/backup-management-system/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # ヘルスチェック
    location /health {
        proxy_pass http://backup_mgmt;
        access_log off;
    }

    # セキュリティヘッダー
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

#### 8.2 Nginxサイトの有効化

```bash
# サイト有効化
sudo ln -s /etc/nginx/sites-available/backup-management /etc/nginx/sites-enabled/

# デフォルトサイトの無効化（必要に応じて）
sudo rm /etc/nginx/sites-enabled/default

# 設定ファイルのテスト
sudo nginx -t

# Nginxの再起動
sudo systemctl restart nginx

# ステータス確認
sudo systemctl status nginx
```

### ステップ9: ファイアウォール設定

```bash
# UFWを使用する場合（Ubuntu）
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# firewalld を使用する場合（CentOS/RHEL）
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### ステップ10: HTTPS設定（Let's Encrypt）

```bash
# Certbotのインストール
sudo apt install certbot python3-certbot-nginx

# 証明書の取得（ドメイン必須）
sudo certbot certonly --nginx -d your-domain.com

# Nginx設定の更新
sudo nano /etc/nginx/sites-available/backup-management
```

**HTTPS対応のNginx設定例:**

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 残りの設定は上記と同じ
    location / {
        proxy_pass http://backup_mgmt;
        # ...
    }
}

# HTTPからHTTPSへのリダイレクト
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

```bash
# Nginxの再起動
sudo systemctl restart nginx

# 証明書の自動更新確認
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### ステップ11: 動作確認

```bash
# ローカルテスト
curl http://localhost/

# サービスステータス確認
sudo systemctl status backup-management.service
sudo systemctl status nginx

# ログ確認
sudo journalctl -u backup-management.service -n 50
sudo tail -50 /var/log/nginx/access.log
sudo tail -50 /var/log/nginx/error.log

# ディスク使用量確認
df -h /var/lib/backup-mgmt
du -sh /var/log/backup-mgmt
```

---

## セキュリティ設定

### 1. SECRET_KEY の生成と管理

```bash
# 安全な SECRET_KEY の生成
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**推奨:**
- 最小32文字以上
- 環境変数で管理（ファイルに記録しない）
- 本番環境ごとに異なるキーを使用
- 定期的に更新（3-6ヶ月ごと）

### 2. データベースセキュリティ

#### パスワード管理
```ini
# .env ファイル
# ファイルパーミッション設定
chmod 600 /opt/backup-management-system/.env
sudo chown backup-mgmt:backup-mgmt /opt/backup-management-system/.env
```

#### SQLインジェクション対策
- SQLAlchemy ORM を使用（クエリパラメータ化）
- ユーザー入力の検証を実施

### 3. ネットワークセキュリティ

#### ファイアウォール設定
- **Windows**: Windows Defender ファイアウォール
- **Linux**: UFW または firewalld

#### HTTPSの強制化

```nginx
# Nginxでセキュリティヘッダーを設定
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### 4. 認証・認可

- [ ] デフォルトアカウントの削除
- [ ] 強力なパスワードポリシーの実装
- [ ] 多要素認証（MFA）の有効化
- [ ] セッションタイムアウトの設定（推奨: 30分）

### 5. ログとモニタリング

```bash
# ログファイルの権限設定
sudo chmod 640 /var/log/backup-mgmt/*
sudo chown backup-mgmt:adm /var/log/backup-mgmt/*

# ログローテーション設定（logrotate）
sudo nano /etc/logrotate.d/backup-mgmt
```

**logrotate設定例:**
```
/var/log/backup-mgmt/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 backup-mgmt adm
    sharedscripts
    postrotate
        systemctl reload backup-management.service > /dev/null 2>&1 || true
    endscript
}
```

### 6. API セキュリティ

- [ ] CORS設定の確認
- [ ] CSRF トークンの有効化
- [ ] レート制限の実装
- [ ] APIドキュメントの非公開化

---

## パフォーマンスチューニング

### 1. Flask設定の最適化

**.env ファイル:**
```ini
# ワーカープロセス数（CPU コア数）
GUNICORN_WORKERS=4

# スレッド数
GUNICORN_THREADS=2

# タイムアウト設定
GUNICORN_TIMEOUT=120

# キープアライブ設定
GUNICORN_KEEPALIVE=5
```

### 2. Gunicornでの本番実行

```bash
# Gunicornのインストール
pip install gunicorn

# サービスファイルの更新
sudo nano /etc/systemd/system/backup-management.service
```

**更新内容:**
```ini
ExecStart=/opt/backup-management-system/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --timeout 120 \
    --access-logfile /var/log/backup-mgmt/access.log \
    --error-logfile /var/log/backup-mgmt/error.log \
    --log-level info \
    app:app
```

### 3. データベースパフォーマンス

```python
# SQLAlchemy設定
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}

# インデックスの確認
sqlite3 /var/lib/backup-mgmt/backup_mgmt.db
> .indices
```

### 4. Nginxパフォーマンス

```nginx
# worker プロセス数（CPU コア数）
worker_processes auto;

# 接続数
worker_connections 1024;

# キープアライブ
keepalive_timeout 65;

# gzip圧縮
gzip on;
gzip_types text/plain text/css application/json;
gzip_comp_level 6;
gzip_min_length 1000;
```

### 5. キャッシング戦略

```nginx
# ブラウザキャッシュ
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# HTMLはキャッシュなし
location ~* \.html?$ {
    expires -1;
    add_header Cache-Control "public, must-revalidate";
}
```

### 6. メモリ設定

```bash
# メモリ使用量の監視
free -h

# プロセスごとの使用量
ps aux | grep python
```

### 7. ディスク I/O 最適化

```bash
# ディスク使用量の確認
du -sh /var/lib/backup-mgmt/

# ログファイルのサイズ確認
du -sh /var/log/backup-mgmt/

# 古いログの削除
find /var/log/backup-mgmt -type f -mtime +30 -delete
```

---

## トラブルシューティング

### 一般的な問題

#### 1. アプリケーションが起動しない

**Windows:**
```cmd
REM ログの確認
type "C:\ProgramData\BackupManagementSystem\logs\app.log"

REM サービスの再起動
net stop BackupManagementSystem
net start BackupManagementSystem

REM ポート競合の確認
netstat -ano | findstr :5000
```

**Linux:**
```bash
# ログの確認
sudo journalctl -u backup-management.service -n 100

# サービスの再起動
sudo systemctl restart backup-management.service

# ポート競合の確認
sudo ss -tlnp | grep 5000

# セキュリティコンテキストの確認（SELinux）
getenforce
```

#### 2. ポートが既に使用されている

```bash
# 使用中のプロセスを特定
lsof -i :5000

# プロセスの強制終了（必要に応じて）
kill -9 <PID>
```

#### 3. データベース接続エラー

```bash
# データベースファイルの確認
ls -la /var/lib/backup-mgmt/backup_mgmt.db

# パーミッションの確認
stat /var/lib/backup-mgmt/backup_mgmt.db

# 所有権の修正
sudo chown backup-mgmt:backup-mgmt /var/lib/backup-mgmt/backup_mgmt.db
sudo chmod 640 /var/lib/backup-mgmt/backup_mgmt.db
```

#### 4. メモリ不足

```bash
# メモリ使用量確認
free -h

# プロセスの使用量
ps aux --sort=-%mem | head -n 10

# スワップの確認
swapon --show
```

#### 5. ファイアウォール通信エラー

**Windows:**
```cmd
REM ルールの確認
netsh advfirewall firewall show rule name="Flask Application"

REM ルールの削除と再作成
netsh advfirewall firewall delete rule name="Flask Application"
netsh advfirewall firewall add rule name="Flask Application" dir=in action=allow protocol=tcp localport=5000
```

**Linux:**
```bash
# UFWルールの確認
sudo ufw status numbered

# ポート許可（UFW）
sudo ufw allow 5000

# firewalld ルール確認
sudo firewall-cmd --list-all
```

#### 6. Nginxが503エラーを返す

```bash
# バックエンドサービスの確認
sudo systemctl status backup-management.service

# Nginxログの確認
sudo tail -50 /var/log/nginx/error.log

# バックエンドへの接続テスト
curl http://127.0.0.1:5000/
```

### 詳細なログ出力

#### Flask アプリケーションログレベルの変更

```python
# app/__init__.py
import logging

if app.config['ENV'] == 'production':
    # INFO レベル
    app.logger.setLevel(logging.INFO)
else:
    # DEBUG レベル
    app.logger.setLevel(logging.DEBUG)
```

#### systemd ログの確認

```bash
# 全ログ表示
sudo journalctl -u backup-management.service

# 直近50行
sudo journalctl -u backup-management.service -n 50

# リアルタイム監視
sudo journalctl -u backup-management.service -f

# エラーのみ表示
sudo journalctl -u backup-management.service -p err
```

#### Nginxログの確認

```bash
# アクセスログ
sudo tail -f /var/log/nginx/access.log

# エラーログ
sudo tail -f /var/log/nginx/error.log

# ログ検索（特定のIPアドレス）
sudo grep "192.168.1.100" /var/log/nginx/access.log
```

---

## ロールバック手順

### バージョン管理とバックアップ

```bash
# 現在のバージョンの記録
git describe --tags > VERSION.txt

# ディレクトリのバックアップ
sudo tar -czf /backup/backup-mgmt-$(date +%Y%m%d_%H%M%S).tar.gz \
    /opt/backup-management-system \
    /var/lib/backup-mgmt/backup_mgmt.db
```

### ロールバック実行手順

#### ステップ1: サービスの停止

**Linux:**
```bash
sudo systemctl stop backup-management.service
sudo systemctl stop nginx
```

**Windows:**
```cmd
net stop BackupManagementSystem
net stop Nginx
```

#### ステップ2: バックアップファイルの復元

```bash
# 前のバージョンのバックアップを確認
ls -lh /backup/backup-mgmt-*.tar.gz

# 復元（日付を適切に変更）
sudo tar -xzf /backup/backup-mgmt-20231201_143022.tar.gz -C /

# データベースのロールバック
sudo cp /backup/backup_mgmt.db.bak /var/lib/backup-mgmt/backup_mgmt.db
```

#### ステップ3: 依存ライブラリの復元

```bash
# 仮想環境の再構築
sudo -u backup-mgmt bash -c 'cd /opt/backup-management-system && \
    rm -rf venv && \
    python3 -m venv venv && \
    venv/bin/pip install -r requirements.txt'
```

#### ステップ4: サービスの再起動

```bash
# サービスの再起動
sudo systemctl start backup-management.service
sudo systemctl start nginx

# ステータス確認
sudo systemctl status backup-management.service
```

#### ステップ5: 動作確認

```bash
# サービスのヘルスチェック
curl http://localhost/health

# ログの確認
sudo journalctl -u backup-management.service -n 20
```

### 緊急ロールバック（git使用時）

```bash
# コミット履歴の確認
git log --oneline | head -20

# 特定のコミットまでロールバック
git revert <commit-hash>

# または強制的にリセット（危険）
git reset --hard <commit-hash>

# 変更の確認
git status
```

---

## 定期メンテナンスチェックリスト

### 日次

- [ ] アプリケーションログのエラーを確認
- [ ] サービスが起動しているか確認
- [ ] ディスク容量の確認

### 週次

- [ ] ログファイルのサイズと古さを確認
- [ ] データベース接続数を確認
- [ ] バックアップジョブの実行状況を確認

### 月次

- [ ] セキュリティアップデートの確認
- [ ] ディスク容量の分析
- [ ] パフォーマンス指標の確認
- [ ] ユーザーアクティビティレポートの確認

### 四半期ごと

- [ ] SECRET_KEY の更新を検討
- [ ] 依存ライブラリのアップデート
- [ ] セキュリティスキャンの実施
- [ ] ディザスタリカバリテストの実施

---

## サポートとドキュメント

詳細な情報は以下を参照してください：

- [環境変数設定ガイド](docs/ENVIRONMENT_VARIABLES.md)
- [本番運用マニュアル](PRODUCTION_OPERATIONS_MANUAL.md)
- [Veeam統合ガイド](docs/VEEAM_INTEGRATION_GUIDE.md)
- [デプロイメントアーキテクチャ](docs/DEPLOYMENT_ARCHITECTURE.md)

---

## 更新履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|----------|
| 2024-01-01 | 1.0 | 初版作成 |

---

**最後の更新**: 2024年1月
**作成者**: バックアップ管理システムチーム
