#!/bin/bash
# =============================================================================
# Celery Worker & Beat Scheduler インストールスクリプト
# 3-2-1-1-0 Backup Management System
# =============================================================================
# 使用方法:
#   sudo bash deployment/linux/install_celery.sh
# =============================================================================
set -e

INSTALL_DIR="${INSTALL_DIR:-/opt/backup-management-system}"
SERVICE_USER="${SERVICE_USER:-backupmgmt}"
LOG_DIR="/var/log/backup-management"
RUN_DIR="/var/run/celery"
DATA_DIR="/var/lib/backup-management"

echo "=== Celery Worker セットアップ開始 ==="

# Redisのインストール確認
if ! command -v redis-server &> /dev/null; then
    echo "Redisをインストールしています..."
    apt-get update -qq && apt-get install -y redis-server
    systemctl enable redis-server
    systemctl start redis-server
    echo "✅ Redis インストール完了"
else
    echo "✅ Redis 既にインストール済み"
fi

# Redis接続テスト
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis 接続確認OK"
else
    echo "⚠️  Redis 接続失敗 - 手動で確認してください"
fi

# ディレクトリ作成
echo "ディレクトリを作成しています..."
mkdir -p "$LOG_DIR" "$RUN_DIR" "$DATA_DIR"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$LOG_DIR" "$RUN_DIR" "$DATA_DIR" 2>/dev/null || true
echo "✅ ディレクトリ作成完了"

# systemdサービスファイルのインストール
echo "systemdサービスファイルをインストールしています..."
SYSTEMD_DIR="/etc/systemd/system"

# WorkingDirectory を実際のインストールパスに置換
for service in backup-celery-worker.service backup-celery-beat.service; do
    src="$INSTALL_DIR/deployment/linux/systemd/$service"
    dst="$SYSTEMD_DIR/$service"
    if [ -f "$src" ]; then
        sed "s|/opt/backup-management-system|$INSTALL_DIR|g" "$src" > "$dst"
        echo "✅ インストール: $dst"
    else
        echo "⚠️  見つかりません: $src"
    fi
done

# systemdリロード
systemctl daemon-reload

# サービスの有効化と起動
echo "Celery Workerを起動しています..."
systemctl enable backup-celery-worker backup-celery-beat
systemctl start backup-celery-worker && echo "✅ Celery Worker 起動完了"
systemctl start backup-celery-beat && echo "✅ Celery Beat 起動完了"

echo ""
echo "=== Celery セットアップ完了 ==="
echo ""
echo "サービス状態確認:"
echo "  systemctl status backup-celery-worker"
echo "  systemctl status backup-celery-beat"
echo ""
echo "ログ確認:"
echo "  tail -f $LOG_DIR/celery-worker.log"
echo "  tail -f $LOG_DIR/celery-beat.log"
echo ""
echo "Flower監視ツール起動（任意）:"
echo "  $INSTALL_DIR/venv/bin/celery -A celery_worker.celery_app flower --port=5555"
