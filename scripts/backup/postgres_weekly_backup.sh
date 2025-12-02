#!/bin/bash
# PostgreSQL 週次バックアップスクリプト
# Phase 13: バックアップ戦略
#
# 使用方法:
#   ./scripts/backup/postgres_weekly_backup.sh
#
# Cron設定例:
#   0 3 * * 0 /path/to/scripts/backup/postgres_weekly_backup.sh

set -e

# ============================================================
# 設定
# ============================================================

BACKUP_BASE_DIR="/mnt/Linux-ExHDD/backup-management-system/backups"
BACKUP_DIR="$BACKUP_BASE_DIR/postgres/weekly"

DB_NAME="backup_management"
DB_USER="backupmgmt"
DB_HOST="localhost"
DB_PORT="5434"
DB_PASSWORD="${POSTGRES_PASSWORD:-b68pmA9ooombxmxOgTEmRjOx}"

# 保持期間（週数）
RETENTION_WEEKS=4

LOG_FILE="$BACKUP_BASE_DIR/postgres_backup.log"
TIMESTAMP=$(date +%Y%m%d)
WEEK_NUMBER=$(date +%U)

# ============================================================
# 週次バックアップ実行
# ============================================================

echo "============================================================" | tee -a "$LOG_FILE"
echo "PostgreSQL 週次バックアップ開始" | tee -a "$LOG_FILE"
echo "開始時刻: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "週番号: Week $WEEK_NUMBER" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

mkdir -p "$BACKUP_DIR"

# カスタム形式でダンプ
BACKUP_FILE="$BACKUP_DIR/weekly_backup_week${WEEK_NUMBER}_${TIMESTAMP}.dump"

echo ""
echo "[1] 週次pg_dump実行中..." | tee -a "$LOG_FILE"

PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    -Z 9 \
    -f "$BACKUP_FILE" \
    --verbose 2>&1 | tee -a "$LOG_FILE"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ バックアップ完了: $BACKUP_FILE ($BACKUP_SIZE)" | tee -a "$LOG_FILE"

# グローバルオブジェクト（ユーザー、ロール）もバックアップ
echo ""
echo "[2] グローバルオブジェクトをバックアップ中..." | tee -a "$LOG_FILE"

GLOBALS_FILE="$BACKUP_DIR/globals_week${WEEK_NUMBER}_${TIMESTAMP}.sql"

PGPASSWORD="$DB_PASSWORD" pg_dumpall \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    --globals-only \
    -f "$GLOBALS_FILE" 2>&1 | tee -a "$LOG_FILE"

gzip "$GLOBALS_FILE"
echo "✅ グローバルバックアップ完了: $GLOBALS_FILE.gz" | tee -a "$LOG_FILE"

# ============================================================
# 古いバックアップの削除（4週間保持）
# ============================================================

echo ""
echo "[3] 古い週次バックアップを削除中（保持: ${RETENTION_WEEKS}週間）..." | tee -a "$LOG_FILE"

# 28日以上古いファイルを削除
DELETED=$(find "$BACKUP_DIR" -name "weekly_backup_*.dump" -mtime +28 -delete -print | wc -l)
echo "   削除: ${DELETED}個のバックアップファイル" | tee -a "$LOG_FILE"

# ============================================================
# バックアップ検証
# ============================================================

echo ""
echo "[4] バックアップファイルの整合性確認中..." | tee -a "$LOG_FILE"

pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1

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
echo "週次バックアップサマリー" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
echo "完了時刻: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "バックアップファイル:" | tee -a "$LOG_FILE"
echo "  - データベース: $BACKUP_FILE ($BACKUP_SIZE)" | tee -a "$LOG_FILE"
echo "  - グローバル: $GLOBALS_FILE.gz" | tee -a "$LOG_FILE"
echo "削除した古いファイル: ${DELETED}個" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
echo "✅ 週次バックアップが正常に完了しました" | tee -a "$LOG_FILE"
echo ""

# オプション: 成功通知をSlackやTeamsに送信
# curl -X POST $TEAMS_WEBHOOK_URL -H 'Content-Type: application/json' \
#     -d "{\"text\": \"PostgreSQL週次バックアップ完了: Week $WEEK_NUMBER\"}"
