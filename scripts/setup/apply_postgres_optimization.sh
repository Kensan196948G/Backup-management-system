#!/bin/bash
# PostgreSQL最適化設定適用スクリプト
# Phase 13: パフォーマンス最適化
#
# 使用方法:
#   sudo ./scripts/setup/apply_postgres_optimization.sh

set -e

CONFIG_FILE="/etc/postgresql/16/main/postgresql.conf"
BACKUP_FILE="/etc/postgresql/16/main/postgresql.conf.backup_$(date +%Y%m%d_%H%M%S)"
OPTIMIZED_CONFIG="deployment/postgresql/postgresql.conf.optimized"

echo "============================================================"
echo "PostgreSQL最適化設定適用"
echo "============================================================"

# 1. 現在の設定をバックアップ
echo "[1] 現在の設定をバックアップ中..."
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "✅ バックアップ完了: $BACKUP_FILE"

# 2. 最適化設定を追加
echo ""
echo "[2] 最適化設定を追加中..."
cat "$OPTIMIZED_CONFIG" >> "$CONFIG_FILE"
echo "✅ 設定追加完了"

# 3. 設定の妥当性チェック
echo ""
echo "[3] 設定の妥当性をチェック中..."
sudo -u postgres /usr/lib/postgresql/16/bin/postgres -C config_file="$CONFIG_FILE" -D /var/lib/postgresql/16/main --check
echo "✅ 設定チェック完了"

# 4. PostgreSQL再起動
echo ""
echo "[4] PostgreSQLを再起動中..."
systemctl restart postgresql
sleep 3

# 5. 起動確認
echo ""
echo "[5] 起動確認中..."
systemctl status postgresql --no-pager | head -10

# 6. 設定値確認
echo ""
echo "[6] 適用された設定値を確認中..."
echo ""
sudo -u postgres psql -p 5434 -c "SHOW shared_buffers;"
sudo -u postgres psql -p 5434 -c "SHOW effective_cache_size;"
sudo -u postgres psql -p 5434 -c "SHOW work_mem;"
sudo -u postgres psql -p 5434 -c "SHOW max_connections;"

echo ""
echo "============================================================"
echo "✅ PostgreSQL最適化設定の適用が完了しました"
echo "============================================================"
echo ""
echo "バックアップファイル: $BACKUP_FILE"
echo ""
echo "ロールバック方法:"
echo "  sudo cp $BACKUP_FILE $CONFIG_FILE"
echo "  sudo systemctl restart postgresql"
echo ""
