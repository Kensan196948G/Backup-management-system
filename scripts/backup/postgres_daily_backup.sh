#!/bin/bash
# PostgreSQL 日次バックアップスクリプト
# Phase 13: バックアップ戦略
#
# 使用方法:
#   ./scripts/backup/postgres_daily_backup.sh
#
# Cron設定例:
#   0 2 * * * /path/to/scripts/backup/postgres_daily_backup.sh

set -e

# ============================================================
# 設定
# ============================================================

# バックアップディレクトリ
BACKUP_BASE_DIR="/mnt/Linux-ExHDD/backup-management-system/backups"
BACKUP_DIR="$BACKUP_BASE_DIR/postgres/daily"

# PostgreSQL接続情報
DB_NAME="backup_management"
DB_USER="backupmgmt"
DB_HOST="localhost"
DB_PORT="5434"
DB_PASSWORD="${POSTGRES_PASSWORD:-b68pmA9ooombxmxOgTEmRjOx}"

# バックアップ保持期間（日数）
RETENTION_DAYS=7

# ログファイル
LOG_FILE="$BACKUP_BASE_DIR/postgres_backup.log"

# タイムスタンプ
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)

# ============================================================
# バックアップ実行
# ============================================================

echo "============================================================" | tee -a "$LOG_FILE"
echo "PostgreSQL 日次バックアップ開始" | tee -a "$LOG_FILE"
echo "開始時刻: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

# バックアップディレクトリ作成
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# 1. カスタム形式でダンプ（圧縮、並列リストア可能）
echo ""
echo "[1] pg_dump実行中（カスタム形式）..." | tee -a "$LOG_FILE"

BACKUP_FILE="$BACKUP_DIR/backup_${DATE_ONLY}_${TIMESTAMP}.dump"

PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    -f "$BACKUP_FILE" \
    --verbose 2>&1 | tee -a "$LOG_FILE"

# ファイルサイズ確認
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ バックアップ完了: $BACKUP_FILE ($BACKUP_SIZE)" | tee -a "$LOG_FILE"

# 2. 追加でSQL形式も保存（可読性のため）
echo ""
echo "[2] SQL形式でもダンプ..." | tee -a "$LOG_FILE"

SQL_FILE="$BACKUP_DIR/backup_${DATE_ONLY}_${TIMESTAMP}.sql"

PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$SQL_FILE" 2>&1 | tee -a "$LOG_FILE"

# 圧縮
gzip "$SQL_FILE"
SQL_SIZE=$(du -h "$SQL_FILE.gz" | cut -f1)
echo "✅ SQL形式バックアップ完了: $SQL_FILE.gz ($SQL_SIZE)" | tee -a "$LOG_FILE"

# 3. スキーマのみバックアップ（DDL）
echo ""
echo "[3] スキーマのみバックアップ..." | tee -a "$LOG_FILE"

SCHEMA_FILE="$BACKUP_DIR/schema_${DATE_ONLY}.sql"

PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --schema-only \
    -f "$SCHEMA_FILE" 2>&1 | tee -a "$LOG_FILE"

gzip "$SCHEMA_FILE"
echo "✅ スキーマバックアップ完了: $SCHEMA_FILE.gz" | tee -a "$LOG_FILE"

# ============================================================
# 古いバックアップの削除
# ============================================================

echo ""
echo "[4] 古いバックアップを削除中（保持期間: ${RETENTION_DAYS}日）..." | tee -a "$LOG_FILE"

# カスタム形式（.dump）
DELETED_DUMP=$(find "$BACKUP_DIR" -name "backup_*.dump" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
echo "   削除: ${DELETED_DUMP}個の.dumpファイル" | tee -a "$LOG_FILE"

# SQL形式（.sql.gz）
DELETED_SQL=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
echo "   削除: ${DELETED_SQL}個の.sql.gzファイル" | tee -a "$LOG_FILE"

# スキーマファイル（30日保持）
DELETED_SCHEMA=$(find "$BACKUP_DIR" -name "schema_*.sql.gz" -mtime +30 -delete -print | wc -l)
echo "   削除: ${DELETED_SCHEMA}個のschemaファイル" | tee -a "$LOG_FILE"

# ============================================================
# バックアップ検証
# ============================================================

echo ""
echo "[5] バックアップファイルの整合性確認中..." | tee -a "$LOG_FILE"

# pg_restoreでリスト表示（エラーチェック）
PGPASSWORD="$DB_PASSWORD" pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ バックアップファイルの整合性OK" | tee -a "$LOG_FILE"
else
    echo "❌ バックアップファイルの整合性エラー" | tee -a "$LOG_FILE"
    exit 1
fi

# ============================================================
# サマリー
# ============================================================

echo ""
echo "============================================================" | tee -a "$LOG_FILE"
echo "バックアップサマリー" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
echo "完了時刻: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "バックアップファイル:" | tee -a "$LOG_FILE"
echo "  - カスタム形式: $BACKUP_FILE ($BACKUP_SIZE)" | tee -a "$LOG_FILE"
echo "  - SQL形式: $SQL_FILE.gz ($SQL_SIZE)" | tee -a "$LOG_FILE"
echo "  - スキーマのみ: $SCHEMA_FILE.gz" | tee -a "$LOG_FILE"
echo "削除した古いファイル: $((DELETED_DUMP + DELETED_SQL + DELETED_SCHEMA))個" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
echo "✅ 日次バックアップが正常に完了しました" | tee -a "$LOG_FILE"
echo ""
