# Linux本番環境デプロイメントガイド

3-2-1-1-0 Backup Management System のUbuntu/Debian環境への本番デプロイメント手順

## 目次

- [システム要件](#システム要件)
- [セットアップ手順](#セットアップ手順)
- [SSL証明書設定](#ssl証明書設定)
- [サービス管理](#サービス管理)
- [ログ管理](#ログ管理)
- [トラブルシューティング](#トラブルシューティング)
- [セキュリティ設定](#セキュリティ設定)
- [バックアップと復旧](#バックアップと復旧)
- [アンインストール](#アンインストール)

## システム要件

### OS

- Ubuntu 20.04 LTS以上
- Debian 11以上

### ハードウェア

- CPU: 2コア以上
- RAM: 4GB以上
- ディスク: 50GB以上

### ソフトウェア

- Python 3.9以上
- systemd
- nginx 1.18以上

### ネットワーク

- インバウンド: HTTP (80), HTTPS (443)
- アウトバウンド: Let's Encrypt DNS解決用

## セットアップ手順

### 1. 前提条件の確認

セットアップを開始する前に、以下の条件を確認してください:

```bash
# root権限で実行していることを確認
sudo whoami

# OSを確認
cat /etc/os-release

# Pythonバージョンを確認
python3 --version

# ディスク空き容量を確認
df -h /

# ネットワーク接続を確認
ping -c 1 google.com
```

### 2. リポジトリの準備

```bash
# リポジトリをクローン
cd /tmp
git clone https://github.com/your-org/backup-management-system.git
cd backup-management-system

# デプロイメントスクリプトをコピー
sudo cp -r deployment /opt/deployment-scripts
```

### 3. セットアップスクリプトの実行

```bash
# スクリプトに実行権限を付与
sudo chmod +x /opt/deployment-scripts/linux/setup.sh

# セットアップを実行
sudo /opt/deployment-scripts/linux/setup.sh
```

セットアップスクリプトは以下の処理を実行します:

1. **前提条件チェック**
   - OS互換性の確認
   - Pythonバージョンの確認
   - root権限の確認

2. **システムパッケージのインストール**
   - Python仮想環境ツール
   - nginxウェブサーバー
   - systemdサービスマネージャー
   - その他の依存パッケージ

3. **ユーザー・ディレクトリの作成**
   - アプリケーションユーザー (backupmgmt)
   - アプリケーションディレクトリ (/opt/backup-management-system)
   - ログディレクトリ (/var/log/backup-management-system)
   - データディレクトリ (/var/lib/backup-management-system)

4. **アプリケーションのセットアップ**
   - ファイルのコピー
   - Python仮想環境の作成
   - 依存パッケージのインストール
   - データベースの初期化

5. **サービスの登録**
   - systemdユニットの登録
   - nginxリバースプロキシの設定

### 4. 環境変数の設定

セットアップ後、環境変数ファイルを編集します:

```bash
# .envファイルを編集
sudo nano /opt/backup-management-system/.env
```

重要な設定項目:

```env
# Flask設定
FLASK_ENV=production
SECRET_KEY=<自動生成済み>

# データベース
DATABASE_URL=sqlite:////var/lib/backup-management-system/backup_management.db

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=/var/log/backup-management-system/app.log

# バックアップ設定
BACKUP_DIR=/mnt/backups
RETENTION_DAYS=30

# メール通知（オプション）
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=<アプリパスワード>
```

### 5. データベースの初期化（必要に応じて）

```bash
# データベースをアップグレード
sudo /opt/backup-management-system/venv/bin/flask db upgrade

# データベースを確認
sudo sqlite3 /var/lib/backup-management-system/backup_management.db ".tables"
```

## SSL証明書設定

### 1. ドメイン名の準備

セットアップ前にドメイン名とDNS設定を準備してください:

```bash
# ドメイン名の疎通確認
nslookup backup.example.com

# または
dig backup.example.com
```

### 2. SSL証明書の取得

```bash
# スクリプトに実行権限を付与
sudo chmod +x /opt/deployment-scripts/linux/setup_ssl.sh

# SSL証明書を取得
sudo /opt/deployment-scripts/linux/setup_ssl.sh
```

スクリプトを実行すると以下を入力するよう促されます:

- **ドメイン名**: backup.example.com
- **メールアドレス**: admin@example.com (通知用)

### 3. 証明書の確認

```bash
# 取得した証明書を確認
sudo certbot certificates

# 証明書の詳細を確認
sudo openssl x509 -in /etc/letsencrypt/live/backup.example.com/fullchain.pem -text -noout
```

### 4. 自動更新の確認

```bash
# certbotタイマーのステータス確認
sudo systemctl status certbot.timer

# 更新テスト
sudo certbot renew --dry-run

# ログ確認
sudo journalctl -u certbot.service -n 20
```

## サービス管理

### サービスの起動

```bash
# サービスを起動
sudo systemctl start backup-management.service

# 自動起動を有効化
sudo systemctl enable backup-management.service

# ステータス確認
sudo systemctl status backup-management.service
```

### サービスの停止・再起動

```bash
# サービスを停止
sudo systemctl stop backup-management.service

# サービスを再起動
sudo systemctl restart backup-management.service

# サービスを再読み込み
sudo systemctl reload backup-management.service
```

### nginx の管理

```bash
# nginx設定テスト
sudo nginx -t

# nginxを再起動
sudo systemctl restart nginx

# nginxをリロード
sudo systemctl reload nginx

# ステータス確認
sudo systemctl status nginx
```

## ログ管理

### アプリケーションログ

```bash
# 最新100行を表示
sudo tail -100f /var/log/backup-management-system/app.log

# すべてのログを表示
sudo cat /var/log/backup-management-system/app.log | less

# ログレベルでフィルター
sudo grep "ERROR" /var/log/backup-management-system/app.log

# 日付でフィルター
sudo grep "2024-01-15" /var/log/backup-management-system/app.log
```

### systemdログ

```bash
# サービスログを表示
sudo journalctl -u backup-management.service -f

# 過去1時間のログ
sudo journalctl -u backup-management.service --since "1 hour ago"

# エラーのみ表示
sudo journalctl -u backup-management.service -p err

# ブート時のログ
sudo journalctl -u backup-management.service -b
```

### nginxログ

```bash
# アクセスログ
sudo tail -100f /var/log/nginx/backup-management-access.log

# エラーログ
sudo tail -100f /var/log/nginx/backup-management-error.log

# 特定のIPをフィルター
sudo grep "192.168.1.100" /var/log/nginx/backup-management-access.log
```

### ログのローテーション

ログローテーション設定ファイル:

```bash
# logrotateの設定を作成
sudo cat > /etc/logrotate.d/backup-management << 'EOF'
/var/log/backup-management-system/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 backupmgmt backupmgmt
    sharedscripts
    postrotate
        systemctl reload backup-management.service > /dev/null 2>&1 || true
    endscript
}
EOF

# 設定をテスト
sudo logrotate -d /etc/logrotate.d/backup-management
```

## トラブルシューティング

### サービスが起動しない

```bash
# ステータス確認
sudo systemctl status backup-management.service

# systemdログ確認
sudo journalctl -u backup-management.service -n 50

# アプリケーションログ確認
sudo tail -50f /var/log/backup-management-system/app.log

# 手動実行テスト
sudo -u backupmgmt /opt/backup-management-system/venv/bin/python /opt/backup-management-system/run.py
```

### パーミッションエラー

```bash
# ファイルオーナー確認
ls -la /opt/backup-management-system

# パーミッション修正
sudo chown -R backupmgmt:backupmgmt /opt/backup-management-system
sudo chown -R backupmgmt:backupmgmt /var/log/backup-management-system
sudo chown -R backupmgmt:backupmgmt /var/lib/backup-management-system

chmod -R 755 /opt/backup-management-system
chmod -R 755 /var/log/backup-management-system
chmod -R 755 /var/lib/backup-management-system
```

### ポート競合

```bash
# ポート5000の使用状況を確認
sudo netstat -tulpn | grep 5000

# または
sudo lsof -i :5000

# プロセスを終了
sudo kill -9 <PID>
```

### メモリ不足

```bash
# メモリ使用状況を確認
free -h

# サービスのメモリ使用量を確認
ps aux | grep backup-management

# ディスク使用状況を確認
du -sh /opt/backup-management-system
du -sh /var/log/backup-management-system
du -sh /var/lib/backup-management-system
```

### SSL証明書エラー

```bash
# 証明書の有効性を確認
sudo certbot certificates

# 証明書を手動更新
sudo certbot renew --force-renewal

# Let's Encryptログを確認
sudo tail -50f /var/log/letsencrypt/letsencrypt.log

# nginx SSL設定をテスト
sudo nginx -t
```

## セキュリティ設定

### ファイアウォール設定

```bash
# UFWを有効化
sudo ufw enable

# SSHポートを許可
sudo ufw allow 22/tcp

# HTTPポートを許可
sudo ufw allow 80/tcp

# HTTPSポートを許可
sudo ufw allow 443/tcp

# ステータス確認
sudo ufw status
```

### SSH キーベース認証

```bash
# SSH設定を編集
sudo nano /etc/ssh/sshd_config

# 以下の設定を推奨:
# PasswordAuthentication no
# PermitRootLogin no
# PubkeyAuthentication yes

# SSHサービスを再起動
sudo systemctl restart ssh
```

### セキュリティアップデート

```bash
# セキュリティアップデートをチェック
sudo apt update
sudo apt list --upgradable

# セキュリティアップデートをインストール
sudo apt install -y unattended-upgrades
sudo systemctl enable unattended-upgrades
```

### Fail2Ban（ブルートフォース対策）

```bash
# Fail2Banをインストール
sudo apt install -y fail2ban

# nginx用フィルタを設定
sudo nano /etc/fail2ban/jail.local

# サービスを有効化
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## バックアップと復旧

### データベースのバックアップ

```bash
# SQLiteデータベースをバックアップ
sudo cp /var/lib/backup-management-system/backup_management.db \
        /backup/backup_management.db.$(date +%Y%m%d-%H%M%S)

# または圧縮してバックアップ
sudo tar czf /backup/backup-management-system-db-$(date +%Y%m%d).tar.gz \
             /var/lib/backup-management-system/
```

### ログのバックアップ

```bash
# ログをバックアップ
sudo tar czf /backup/backup-management-system-logs-$(date +%Y%m%d).tar.gz \
             /var/log/backup-management-system/
```

### 設定のバックアップ

```bash
# アプリケーション全体をバックアップ
sudo tar czf /backup/backup-management-system-$(date +%Y%m%d).tar.gz \
             /opt/backup-management-system/
```

### システム全体のバックアップ

```bash
# 自動バックアップスクリプト例
sudo cat > /usr/local/bin/backup-system.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d-%H%M%S)

# ディレクトリ作成
mkdir -p "$BACKUP_DIR"

# データベースバックアップ
tar czf "$BACKUP_DIR/backup-management-db-$DATE.tar.gz" \
    /var/lib/backup-management-system/

# ログバックアップ
tar czf "$BACKUP_DIR/backup-management-logs-$DATE.tar.gz" \
    /var/log/backup-management-system/

# 7日以上前のバックアップを削除
find "$BACKUP_DIR" -name "backup-management-*" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

# 実行権限を付与
sudo chmod +x /usr/local/bin/backup-system.sh

# cronで毎日実行
sudo crontab -e

# 以下を追加:
# 0 2 * * * /usr/local/bin/backup-system.sh
```

### 復旧手順

```bash
# 1. サービスを停止
sudo systemctl stop backup-management.service

# 2. バックアップから復旧
sudo tar xzf /backup/backup-management-system-db-20240115.tar.gz -C /

# 3. パーミッションを修正
sudo chown -R backupmgmt:backupmgmt /var/lib/backup-management-system

# 4. サービスを起動
sudo systemctl start backup-management.service

# 5. ステータス確認
sudo systemctl status backup-management.service
```

## アンインストール

### 完全なアンインストール

```bash
# スクリプトに実行権限を付与
sudo chmod +x /opt/deployment-scripts/linux/uninstall.sh

# アンインストールを実行
sudo /opt/deployment-scripts/linux/uninstall.sh
```

アンインストールスクリプトは以下を削除します:

- サービスの停止
- アプリケーションディレクトリの削除
- ログディレクトリの削除（オプション）
- データディレクトリの削除（オプション）
- systemdユニットの削除
- ユーザーの削除
- nginxコンフィグの削除

### 手動アンインストール

```bash
# 1. サービスを停止
sudo systemctl stop backup-management.service
sudo systemctl disable backup-management.service

# 2. ディレクトリを削除
sudo rm -rf /opt/backup-management-system
sudo rm -rf /var/log/backup-management-system
sudo rm -rf /var/lib/backup-management-system

# 3. systemdユニットを削除
sudo rm /etc/systemd/system/backup-management.service
sudo systemctl daemon-reload

# 4. ユーザーを削除
sudo userdel backupmgmt

# 5. nginxコンフィグを削除
sudo rm /etc/nginx/sites-available/backup-management.conf
sudo rm /etc/nginx/sites-enabled/backup-management.conf
sudo systemctl reload nginx

# 6. SSL証明書を削除（オプション）
sudo certbot delete --cert-name backup.example.com
```

## パフォーマンスチューニング

### Python ワーカー数の設定

```bash
# systemdユニットを編集
sudo systemctl edit backup-management.service

# 以下をExecStartに追加:
# --workers 4 --threads 2 --worker-class gthread
```

### nginx キャッシュ設定

```bash
# キャッシュディレクトリを作成
sudo mkdir -p /var/cache/nginx/backup-management

# キャッシュ設定をnginx.confに追加
proxy_cache_path /var/cache/nginx/backup-management levels=1:2 keys_zone=backup_cache:10m max_size=100m inactive=60m;
```

### メモリ制限の設定

```bash
# systemdサービスファイルを編集
sudo systemctl edit backup-management.service

# 以下を[Service]セクションに追加:
# MemoryLimit=512M
# MemoryMax=1G
```

## 監視とアラート

### systemd-notify を使用

```bash
# アプリケーション内で使用する例
NotifyAccess=main
WatchdogSec=30s
```

### 定期的なヘルスチェック

```bash
# ヘルスチェッククロンジョブ
sudo crontab -e

# 以下を追加:
# */5 * * * * curl -s http://localhost:5000/health || systemctl restart backup-management.service
```

## サポート・トラブルシューティングのお問い合わせ

問題が解決しない場合:

1. ログファイルを確認
2. 関連するシステムコマンドを実行
3. 本番環境マニュアルを参照
4. GitHub Issues で報告

---

**最終更新**: 2024年1月15日
**バージョン**: 1.0.0
