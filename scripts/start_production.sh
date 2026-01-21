#!/bin/bash
# ========================================
# 本番環境起動スクリプト（Linux）
# 3-2-1-1-0 Backup Management System
# ========================================

set -e

echo "========================================="
echo "Backup Management System [本番環境] 起動"
echo "========================================="

# プロジェクトルートディレクトリに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "プロジェクトディレクトリ: $PROJECT_ROOT"

# root権限チェック（本番環境ではポート443を使用するため）
if [ "$EUID" -ne 0 ] && [ "${USE_HTTPS}" = "true" ]; then
    echo "⚠️  警告: HTTPS（ポート443）を使用する場合はroot権限が必要です"
    echo "sudo $0 を実行してください"
    exit 1
fi

# 本番環境の.envファイルを使用
if [ -f ".env.production" ]; then
    echo "✅ 本番環境設定ファイル (.env.production) を読み込んでいます..."
    export $(grep -v '^#' .env.production | xargs)
else
    echo "❌ エラー: .env.production が見つかりません"
    echo "    .env.example.production をコピーして作成してください"
    exit 1
fi

# 重要な設定の検証
if [ "${SECRET_KEY}" = "CHANGE_THIS_TO_STRONG_RANDOM_SECRET_KEY_MIN_50_CHARS" ]; then
    echo "❌ エラー: SECRET_KEYが変更されていません"
    echo "    .env.production を編集して強力なSECRET_KEYを設定してください"
    echo "    生成方法: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    exit 1
fi

# 環境変数の確認
echo ""
echo "環境設定:"
echo "  - 環境: ${ENVIRONMENT:-production}"
echo "  - ポート（HTTP）: ${SERVER_PORT:-5000}"
echo "  - ポート（HTTPS）: ${HTTPS_PORT:-443}"
echo "  - HTTPS: ${USE_HTTPS:-false}"
echo "  - ホスト: ${SERVER_HOST:-0.0.0.0}"
echo "  - デバッグ: ${DEBUG:-false}"
echo ""

# SSL証明書の確認（HTTPS使用時）
if [ "${USE_HTTPS}" = "true" ]; then
    echo "SSL証明書を確認しています..."
    if [ ! -f "${SSL_CERT_PATH}" ]; then
        echo "❌ エラー: SSL証明書が見つかりません: ${SSL_CERT_PATH}"
        echo "    scripts/setup/generate_ssl_cert.sh を実行してください"
        exit 1
    fi
    if [ ! -f "${SSL_KEY_PATH}" ]; then
        echo "❌ エラー: SSL秘密鍵が見つかりません: ${SSL_KEY_PATH}"
        echo "    scripts/setup/generate_ssl_cert.sh を実行してください"
        exit 1
    fi
    echo "✅ SSL証明書: 確認完了"
fi

# Python仮想環境のアクティベート（存在する場合）
if [ -d "venv" ]; then
    echo "Python仮想環境をアクティベートしています..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Python仮想環境をアクティベートしています..."
    source .venv/bin/activate
else
    echo "⚠️  警告: Python仮想環境が見つかりません"
fi

# 必要なディレクトリの作成
echo "必要なディレクトリを作成しています..."
mkdir -p logs
mkdir -p reports/prod
mkdir -p data
mkdir -p /var/backups/backup-system/database

# Redisの起動確認
echo ""
echo "Redisの起動状態を確認しています..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: 起動中"
else
    echo "❌ エラー: Redisが起動していません"
    echo "Redisを起動してください: sudo systemctl start redis-server"
    exit 1
fi

# PostgreSQLの起動確認
echo ""
echo "PostgreSQLの起動状態を確認しています..."
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "✅ PostgreSQL: 起動中"
else
    echo "❌ エラー: PostgreSQLが起動していません"
    echo "PostgreSQLを起動してください: sudo systemctl start postgresql"
    exit 1
fi

# データベースマイグレーションの実行
echo ""
echo "データベースマイグレーションを実行しています..."
flask db upgrade

# 本番環境ではsystemdサービスとして起動することを推奨
echo ""
echo "========================================="
echo "⚠️  本番環境では systemd サービスとして起動することを推奨します"
echo "========================================="
echo ""
echo "systemd サービスとして起動する方法:"
echo "  1. sudo systemctl start backup-management"
echo "  2. sudo systemctl enable backup-management  # 自動起動を有効化"
echo ""
echo "このスクリプトで起動する場合:"
echo "  - 開発・テスト目的のみ"
echo "  - プロセスがフォアグラウンドで実行されます"
echo "  - Ctrl+C で停止できます"
echo ""

read -p "このまま起動しますか? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "起動をキャンセルしました"
    exit 0
fi

# Celery Workerの起動（バックグラウンド）
echo ""
echo "Celery Workerを起動しています..."
celery -A celery_worker.celery worker --loglevel=info --logfile=logs/celery_worker_prod.log --detach

# Celery Beatの起動（バックグラウンド）
echo "Celery Beatを起動しています..."
celery -A celery_worker.celery beat --loglevel=info --logfile=logs/celery_beat_prod.log --detach

echo ""
echo "========================================="
echo "✅ バックグラウンドサービスの起動完了"
echo "========================================="
echo ""

# Flaskアプリケーションの起動
echo "Flaskアプリケーションを起動しています..."
echo ""
if [ "${USE_HTTPS}" = "true" ]; then
    echo "アクセスURL: https://localhost:${HTTPS_PORT:-443}"
    echo "ブックマーク: [本番] https://YOUR_IP_ADDRESS"
else
    echo "アクセスURL: http://localhost:${SERVER_PORT:-5000}"
    echo "ブックマーク: [本番] http://YOUR_IP_ADDRESS:${SERVER_PORT:-5000}"
fi
echo ""
echo "停止方法: Ctrl+C"
echo ""

# Gunicornを使用した本番環境での起動（推奨）
if command -v gunicorn &> /dev/null; then
    echo "Gunicornで起動しています..."
    if [ "${USE_HTTPS}" = "true" ]; then
        gunicorn --bind 0.0.0.0:${HTTPS_PORT:-443} \
                 --workers 4 \
                 --threads 2 \
                 --certfile="${SSL_CERT_PATH}" \
                 --keyfile="${SSL_KEY_PATH}" \
                 --access-logfile logs/access_prod.log \
                 --error-logfile logs/error_prod.log \
                 "app:create_app()"
    else
        gunicorn --bind 0.0.0.0:${SERVER_PORT:-5000} \
                 --workers 4 \
                 --threads 2 \
                 --access-logfile logs/access_prod.log \
                 --error-logfile logs/error_prod.log \
                 "app:create_app()"
    fi
else
    echo "⚠️  警告: Gunicornがインストールされていません"
    echo "    本番環境ではGunicornの使用を推奨します"
    echo "    インストール: pip install gunicorn"
    echo ""
    echo "Flaskの開発サーバーで起動しています..."
    python run.py
fi

echo ""
echo "========================================="
echo "本番環境を停止しています..."
echo "========================================="

# Celeryプロセスの停止
echo "Celery Workerを停止しています..."
pkill -f "celery worker" || true

echo "Celery Beatを停止しています..."
pkill -f "celery beat" || true

echo ""
echo "✅ すべてのプロセスを停止しました"
echo ""
