# systemd サービスファイル

Backup Management System用のsystemdサービス定義ファイルです。

## 前提条件

### Redis インストール

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# CentOS/RHEL
sudo yum install epel-release
sudo yum install redis
sudo systemctl enable redis
sudo systemctl start redis
```

### ユーザー作成

```bash
sudo useradd -r -s /bin/false backupmgmt
```

### ディレクトリ作成

```bash
sudo mkdir -p /var/log/backup-management
sudo mkdir -p /var/run/celery
sudo chown backupmgmt:backupmgmt /var/log/backup-management
sudo chown backupmgmt:backupmgmt /var/run/celery
```

## インストール

```bash
# サービスファイルをコピー
sudo cp celery-worker.service /etc/systemd/system/
sudo cp celery-beat.service /etc/systemd/system/

# systemdをリロード
sudo systemctl daemon-reload

# サービスを有効化
sudo systemctl enable celery-worker
sudo systemctl enable celery-beat
```

## 使用方法

### サービス起動

```bash
# Celery Workerを起動
sudo systemctl start celery-worker

# Celery Beatを起動 (定期タスク)
sudo systemctl start celery-beat
```

### サービス停止

```bash
sudo systemctl stop celery-worker
sudo systemctl stop celery-beat
```

### ステータス確認

```bash
sudo systemctl status celery-worker
sudo systemctl status celery-beat
```

### ログ確認

```bash
# journalctlで確認
sudo journalctl -u celery-worker -f
sudo journalctl -u celery-beat -f

# ログファイル直接確認
sudo tail -f /var/log/backup-management/celery-worker.log
sudo tail -f /var/log/backup-management/celery-beat.log
```

## 環境変数のカスタマイズ

サービスファイルの`Environment`セクションを編集するか、
別途環境ファイルを作成して読み込むことができます:

```bash
# /etc/backup-management/celery.env を作成
FLASK_ENV=production
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
SECRET_KEY=your-secret-key
```

サービスファイルに追加:
```ini
EnvironmentFile=/etc/backup-management/celery.env
```

## トラブルシューティング

### Redisに接続できない

```bash
# Redisの状態確認
sudo systemctl status redis-server
redis-cli ping
```

### Celeryが起動しない

```bash
# 詳細ログを確認
sudo journalctl -u celery-worker -n 50 --no-pager

# 手動で起動してエラー確認
sudo -u backupmgmt /opt/backup-management-system/venv/bin/celery \
    -A celery_worker.celery_app worker --loglevel=DEBUG
```
