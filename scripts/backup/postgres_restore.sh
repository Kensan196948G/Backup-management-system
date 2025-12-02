#!/bin/bash
# PostgreSQL リストアスクリプト
# Phase 13: バックアップ戦略
#
# 使用方法:
#   ./scripts/backup/postgres_restore.sh <backup_file>
#
# 例:
#   ./scripts/backup/postgres_restore.sh backups/postgres/daily/backup_20251202.dump

set -e

# ============================================================
# 引数チェック
# ============================================================

if [ $# -lt 1 ]; then
    echo "使用方法: $0 <backup_file>"
    echo ""
    echo "例:"
    echo "  $0 backups/postgres/daily/backup_20251202.dump"
    echo "  $0 backups/postgres/weekly/weekly_backup_week48.dump"
    echo ""
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ エラー: バックアップファイルが見つかりません: $BACKUP_FILE"
    exit 1
fi

# ============================================================
# 設定
# ============================================================

DB_NAME="backup_management"
DB_USER="backupmgmt"
DB_HOST="localhost"
DB_PORT="5434"
DB_PASSWORD="${POSTGRES_PASSWORD:-b68pmA9ooombxmxOgTEmRjOx}"

# ============================================================
# 警告表示
# ============================================================

echo "============================================================"
echo "⚠️  PostgreSQL リストア"
echo "============================================================"
echo ""
echo "バックアップファイル: $BACKUP_FILE"
echo "ターゲットDB: $DB_NAME @ $DB_HOST:$DB_PORT"
echo ""
echo "⚠️  警告: このスクリプトは既存のデータベースを上書きします！"
echo ""
read -p "続行しますか？ (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "リストアをキャンセルしました"
    exit 0
fi

# ============================================================
# リストア前の準備
# ============================================================

echo ""
echo "[1] リストア前の準備..."

# アクティブ接続を確認
echo "   アクティブ接続を確認中..."
ACTIVE_CONNECTIONS=$(PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid != pg_backend_pid()")

echo "   アクティブ接続数: $ACTIVE_CONNECTIONS"

if [ "$ACTIVE_CONNECTIONS" -gt 0 ]; then
    echo "   ⚠️  警告: アクティブな接続があります"
    read -p "   接続を強制終了してリストアを続行しますか？ (yes/no): " TERMINATE

    if [ "$TERMINATE" = "yes" ]; then
        echo "   接続を終了中..."
        PGPASSWORD="$DB_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U postgres \
            -d postgres \
            -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid != pg_backend_pid()"
        sleep 2
    else
        echo "リストアをキャンセルしました"
        exit 0
    fi
fi

# 現在のデータベースをバックアップ
echo ""
echo "   現在のDBをバックアップ中..."
SAFETY_BACKUP="/tmp/backup_mgmt_before_restore_$(date +%Y%m%d_%H%M%S).dump"
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    -f "$SAFETY_BACKUP"
echo "   ✅ 安全バックアップ作成: $SAFETY_BACKUP"

# ============================================================
# リストア実行
# ============================================================

echo ""
echo "[2] データベースをリストア中..."
echo ""

# データベースを削除して再作成
echo "   データベースを再作成中..."
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U postgres \
    -d postgres \
    -c "DROP DATABASE IF EXISTS ${DB_NAME}_temp"

PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U postgres \
    -d postgres \
    -c "CREATE DATABASE ${DB_NAME}_temp OWNER $DB_USER"

# リストア実行
echo "   pg_restore実行中..."
PGPASSWORD="$DB_PASSWORD" pg_restore \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "${DB_NAME}_temp" \
    --verbose \
    --no-owner \
    --no-privileges \
    "$BACKUP_FILE"

# データベース入れ替え
echo ""
echo "   データベースを入れ替え中..."
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U postgres \
    -d postgres \
    <<EOF
ALTER DATABASE $DB_NAME RENAME TO ${DB_NAME}_old;
ALTER DATABASE ${DB_NAME}_temp RENAME TO $DB_NAME;
DROP DATABASE ${DB_NAME}_old;
EOF

echo "   ✅ データベース入れ替え完了"

# ============================================================
# リストア後の検証
# ============================================================

echo ""
echo "[3] リストア後の検証..."

# テーブル数確認
TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")

echo "   テーブル数: $TABLE_COUNT"

# ユーザー数確認
USER_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM users")

echo "   ユーザー数: $USER_COUNT"

# ============================================================
# サマリー
# ============================================================

echo ""
echo "============================================================"
echo "✅ リストアが正常に完了しました"
echo "============================================================"
echo ""
echo "リストア元: $BACKUP_FILE"
echo "安全バックアップ: $SAFETY_BACKUP"
echo ""
echo "ロールバック方法:"
echo "  $0 $SAFETY_BACKUP"
echo ""
