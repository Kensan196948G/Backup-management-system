#!/bin/bash
# ========================================
# 開発環境起動スクリプト（Linux）
# 3-2-1-1-0 Backup Management System
# ========================================

set -e

echo "========================================="
echo "Backup Management System [開発環境] 起動"
echo "========================================="

# プロジェクトルートディレクトリに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "プロジェクトディレクトリ: $PROJECT_ROOT"

# 開発環境の.envファイルを使用
if [ -f ".env.development" ]; then
    echo "✅ 開発環境設定ファイル (.env.development) を読み込んでいます..."
    export $(grep -v '^#' .env.development | xargs)
else
    echo "⚠️  警告: .env.development が見つかりません"
    echo "    .env.example.development をコピーして作成してください"
    exit 1
fi

# 環境変数の確認
echo ""
echo "環境設定:"
echo "  - 環境: ${ENVIRONMENT:-development}"
echo "  - ポート: ${SERVER_PORT:-5001}"
echo "  - ホスト: ${SERVER_HOST:-0.0.0.0}"
echo "  - デバッグ: ${DEBUG:-true}"
echo ""

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
mkdir -p reports/dev
mkdir -p data

# Redisの起動確認
echo ""
echo "Redisの起動状態を確認しています..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: 起動中"
else
    echo "⚠️  Redis: 停止中"
    echo "Redisを起動してください: sudo systemctl start redis-server"
fi

# PostgreSQLの起動確認
echo ""
echo "PostgreSQLの起動状態を確認しています..."
if pg_isready -h localhost -p 5434 > /dev/null 2>&1; then
    echo "✅ PostgreSQL: 起動中"
else
    echo "⚠️  PostgreSQL: 停止中"
    echo "PostgreSQLを起動してください: sudo systemctl start postgresql"
fi

# Celery Workerの起動（バックグラウンド）
echo ""
echo "Celery Workerを起動しています..."
celery -A celery_worker.celery worker --loglevel=info --logfile=logs/celery_worker_dev.log --detach

# Celery Beatの起動（バックグラウンド）
echo "Celery Beatを起動しています..."
celery -A celery_worker.celery beat --loglevel=info --logfile=logs/celery_beat_dev.log --detach

# Flowerの起動（オプション - タスク監視UI）
echo "Flower（タスク監視UI）を起動しています..."
celery -A celery_worker.celery flower --port=5555 --loglevel=info > logs/flower_dev.log 2>&1 &
echo "✅ Flower UI: http://localhost:5555"

echo ""
echo "========================================="
echo "✅ バックグラウンドサービスの起動完了"
echo "========================================="
echo ""

# Flaskアプリケーションの起動
echo "Flaskアプリケーションを起動しています..."
echo ""
echo "アクセスURL: http://localhost:${SERVER_PORT:-5001}"
echo "ブックマーク: [開発] http://localhost:${SERVER_PORT:-5001}"
echo ""
echo "停止方法: Ctrl+C"
echo ""

# Flaskアプリケーションの起動（フォアグラウンド）
python run.py

echo ""
echo "========================================="
echo "開発環境を停止しています..."
echo "========================================="

# Celeryプロセスの停止
echo "Celery Workerを停止しています..."
pkill -f "celery worker" || true

echo "Celery Beatを停止しています..."
pkill -f "celery beat" || true

echo "Flowerを停止しています..."
pkill -f "celery flower" || true

echo ""
echo "✅ すべてのプロセスを停止しました"
echo ""
