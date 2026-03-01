#!/bin/bash
# PostgreSQL PITR（Point-in-Time Recovery）設定スクリプト
# Phase 13: バックアップ戦略
#
# 使用方法:
#   sudo ./scripts/backup/setup_pitr.sh

set -e

WAL_ARCHIVE_DIR="/mnt/Linux-ExHDD/backup-management-system/backups/postgres/wal_archive"
CONFIG_FILE="/etc/postgresql/16/main/postgresql.conf"

echo "============================================================"
echo "PostgreSQL PITR設定"
echo "============================================================"

# 1. WALアーカイブディレクトリ作成
echo ""
echo "[1] WALアーカイブディレクトリを作成中..."
mkdir -p "$WAL_ARCHIVE_DIR"
chown postgres:postgres "$WAL_ARCHIVE_DIR"
chmod 700 "$WAL_ARCHIVE_DIR"
echo "✅ ディレクトリ作成完了: $WAL_ARCHIVE_DIR"

# 2. PostgreSQL設定確認
echo ""
echo "[2] 現在のWAL設定を確認中..."
sudo -u postgres psql -p 5434 -c "SHOW wal_level;"
sudo -u postgres psql -p 5434 -c "SHOW archive_mode;"

# 3. PITR設定を追加（まだ設定されていない場合）
echo ""
echo "[3] PITR設定を追加中..."

if grep -q "^wal_level = replica" "$CONFIG_FILE"; then
    echo "   ⚠️  wal_level は既に設定済みです"
else
    echo "   wal_level を設定中..."
    echo "" >> "$CONFIG_FILE"
    echo "# PITR設定 (Phase 13)" >> "$CONFIG_FILE"
    echo "wal_level = replica" >> "$CONFIG_FILE"
    echo "archive_mode = on" >> "$CONFIG_FILE"
    echo "archive_command = 'test ! -f $WAL_ARCHIVE_DIR/%f && cp %p $WAL_ARCHIVE_DIR/%f'" >> "$CONFIG_FILE"
    echo "archive_timeout = 300  # 5分" >> "$CONFIG_FILE"
    echo "wal_keep_size = 1GB" >> "$CONFIG_FILE"
    echo "max_wal_senders = 3" >> "$CONFIG_FILE"
    echo "   ✅ PITR設定追加完了"
fi

# 4. PostgreSQL再起動が必要
echo ""
echo "[4] 設定を有効にするにはPostgreSQLの再起動が必要です"
echo ""
read -p "今すぐ再起動しますか？ (yes/no): " RESTART

if [ "$RESTART" = "yes" ]; then
    echo "   PostgreSQLを再起動中..."
    systemctl restart postgresql
    sleep 3
    systemctl status postgresql --no-pager | head -10
    echo "   ✅ 再起動完了"

    # 設定確認
    echo ""
    echo "   設定確認:"
    sudo -u postgres psql -p 5434 -c "SHOW wal_level;"
    sudo -u postgres psql -p 5434 -c "SHOW archive_mode;"
    sudo -u postgres psql -p 5434 -c "SHOW archive_command;"
fi

echo ""
echo "============================================================"
echo "✅ PITR設定が完了しました"
echo "============================================================"
echo ""
echo "WALアーカイブディレクトリ: $WAL_ARCHIVE_DIR"
echo ""
echo "PITRリストア手順:"
echo "  1. PostgreSQL停止"
echo "  2. データディレクトリをバックアップ"
echo "  3. ベースバックアップをリストア"
echo "  4. recovery.confを作成"
echo "  5. PostgreSQL起動（自動的にリカバリー開始）"
echo ""
echo "詳細は docs/14_開発ロードマップ/Phase13_PostgreSQL最適化・監視.md を参照"
echo ""
