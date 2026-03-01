#!/bin/bash
# ========================================
# クイックセットアップスクリプト
# すべてのステップを一括実行
# ========================================

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║     🚀 Backup Management System - クイックセットアップ       ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# プロジェクトルートに移動
cd /mnt/LinuxHDD/Backup-Management-System

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ0: Redisのインストールと起動"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Redisのインストール確認
if ! command -v redis-server &> /dev/null; then
    echo "Redisがインストールされていません。インストールしています..."
    sudo apt-get update -qq
    sudo apt-get install -y redis-server
    echo "✅ Redis: インストール完了"
else
    echo "✅ Redis: 既にインストール済み"
fi

# Redisの起動
sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null || true
sudo systemctl enable redis-server 2>/dev/null || sudo systemctl enable redis 2>/dev/null || true

# 起動確認
sleep 2
echo "Redis起動確認..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: 起動成功"
else
    echo "❌ Redis: 起動失敗"
    echo "手動で起動してください: sudo systemctl start redis-server"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ1: SSL証明書の生成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 自動入力でSSL証明書を生成
echo -e "192.168.0.187\nBackup Management System\n" | sudo ./scripts/setup/generate_ssl_cert.sh

echo ""
echo "証明書生成確認..."
if [ -f "/etc/ssl/certs/backup-system-selfsigned.crt" ]; then
    echo "✅ SSL証明書: 生成成功"
    ls -lh /etc/ssl/certs/backup-system-selfsigned.crt
else
    echo "❌ SSL証明書: 生成失敗"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ2: systemdサービスのインストール"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# PIDディレクトリの作成
sudo mkdir -p /var/run/celery
sudo chown www-data:www-data /var/run/celery

# サービスファイルのコピー
echo "サービスファイルをコピーしています..."
sudo cp deployment/systemd/backup-management-production.service /etc/systemd/system/
sudo cp deployment/systemd/celery-worker-prod.service /etc/systemd/system/
sudo cp deployment/systemd/celery-beat-prod.service /etc/systemd/system/

echo "✅ サービスファイル: コピー完了"

# systemdデーモンのリロード
echo "systemdデーモンをリロードしています..."
sudo systemctl daemon-reload

echo "✅ systemd: リロード完了"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ3: サービスの起動"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# サービスの起動
echo "Celery Workerを起動しています..."
sudo systemctl start celery-worker-prod

echo "Celery Beatを起動しています..."
sudo systemctl start celery-beat-prod

echo "メインアプリケーションを起動しています..."
sudo systemctl start backup-management-production

# 自動起動の有効化
echo ""
echo "自動起動を有効化しています..."
sudo systemctl enable celery-worker-prod
sudo systemctl enable celery-beat-prod
sudo systemctl enable backup-management-production

echo "✅ サービス: 起動・自動起動設定完了"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ4: サービス状態の確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# サービスの状態確認
echo "【backup-management-production】"
sudo systemctl is-active backup-management-production && echo "  ✅ 起動中" || echo "  ❌ 停止中"

echo ""
echo "【celery-worker-prod】"
sudo systemctl is-active celery-worker-prod && echo "  ✅ 起動中" || echo "  ❌ 停止中"

echo ""
echo "【celery-beat-prod】"
sudo systemctl is-active celery-beat-prod && echo "  ✅ 起動中" || echo "  ❌ 停止中"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║              ✅ セットアップが完了しました！                  ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 アクセスURL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "開発環境: http://192.168.0.187:5001"
echo "本番環境: https://192.168.0.187:8443"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 サービス管理コマンド"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "状態確認: sudo systemctl status backup-management-production"
echo "ログ確認: sudo journalctl -u backup-management-production -f"
echo "再起動:   sudo systemctl restart backup-management-production"
echo "停止:     sudo systemctl stop backup-management-production"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
