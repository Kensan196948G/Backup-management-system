# Phase 13: PostgreSQL最適化・バックアップ・監視

**開始日**: 2025-12-02
**ステータス**: 🚧 実装中
**目的**: エンタープライズグレードのデータベース運用基盤を構築

---

## 🎯 Phase 13の目標

### 1. パフォーマンス最適化
- クエリチューニング（スロークエリ検出・最適化）
- インデックス最適化（使用状況分析・追加）
- 接続プーリング（PgBouncer導入）

### 2. バックアップ戦略
- 自動pg_dumpスケジュール（日次・週次）
- PITR（Point-in-Time Recovery）設定
- バックアップ世代管理

### 3. 監視・アラート
- PostgreSQL監視ダッシュボード
- パフォーマンスアラート（CPU、メモリ、接続数）
- スロークエリアラート

---

## 📋 実装計画

### A. パフォーマンス最適化

#### 1. スロークエリ検出

**pg_stat_statements拡張の有効化**:

```sql
-- PostgreSQLで実行
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 設定確認
SELECT * FROM pg_stat_statements LIMIT 5;
```

**設定ファイル** (`postgresql.conf`):
```ini
# スロークエリ検出
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.max = 10000
pg_stat_statements.track = all

# スロークエリログ
log_min_duration_statement = 1000  # 1秒以上のクエリをログ
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_duration = off
log_statement = 'ddl'  # DDLのみログ
```

#### 2. インデックス最適化

**未使用インデックス検出**:
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

**推奨インデックス追加**:
```sql
-- backup_jobs: 検索条件に応じて
CREATE INDEX IF NOT EXISTS idx_backup_jobs_created_at
    ON backup_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_jobs_is_active
    ON backup_jobs(is_active) WHERE is_active = true;

-- audit_logs: アクションタイプとユーザーで頻繁に検索
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action
    ON audit_logs(user_id, action_type, created_at DESC);

-- alerts: 未確認アラート検索用
CREATE INDEX IF NOT EXISTS idx_alerts_unacknowledged
    ON alerts(severity, created_at DESC)
    WHERE is_acknowledged = false;
```

#### 3. PgBouncer接続プーリング

**インストール**:
```bash
sudo apt install pgbouncer
```

**設定ファイル** (`/etc/pgbouncer/pgbouncer.ini`):
```ini
[databases]
backup_management = host=localhost port=5434 dbname=backup_management

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 100
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 5
max_db_connections = 50
```

**接続URL変更**:
```python
# Before
DATABASE_URL=postgresql://user:pass@localhost:5434/backup_management

# After (PgBouncer経由)
DATABASE_URL=postgresql://user:pass@localhost:6432/backup_management
```

---

### B. バックアップ戦略

#### 1. 自動pg_dumpスケジュール

**日次バックアップスクリプト** (`scripts/backup/postgres_daily_backup.sh`):

```bash
#!/bin/bash
# PostgreSQL 日次バックアップスクリプト

BACKUP_DIR="/mnt/backups/postgres/daily"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="backup_management"
DB_USER="backupmgmt"
DB_HOST="localhost"
DB_PORT="5434"

# バックアップディレクトリ作成
mkdir -p "$BACKUP_DIR"

# pg_dump実行（カスタム形式）
PGPASSWORD='password' pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    -f "$BACKUP_DIR/backup_${TIMESTAMP}.dump"

# gzip圧縮
gzip "$BACKUP_DIR/backup_${TIMESTAMP}.dump"

# 7日以上古いバックアップを削除
find "$BACKUP_DIR" -name "backup_*.dump.gz" -mtime +7 -delete

# ログ記録
echo "$(date): Daily backup completed - backup_${TIMESTAMP}.dump.gz" >> \
    /var/log/postgres_backup.log
```

**週次バックアップスクリプト** (`scripts/backup/postgres_weekly_backup.sh`):

```bash
#!/bin/bash
# PostgreSQL 週次フルバックアップ

BACKUP_DIR="/mnt/backups/postgres/weekly"
TIMESTAMP=$(date +%Y%m%d)
DB_NAME="backup_management"

mkdir -p "$BACKUP_DIR"

# SQL形式でダンプ（復元が容易）
PGPASSWORD='password' pg_dump \
    -h localhost \
    -p 5434 \
    -U backupmgmt \
    -d "$DB_NAME" \
    -f "$BACKUP_DIR/backup_${TIMESTAMP}.sql"

# 圧縮
gzip "$BACKUP_DIR/backup_${TIMESTAMP}.sql"

# 4週間（28日）保持
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +28 -delete
```

**Cronジョブ設定**:
```bash
# /etc/cron.d/postgres-backup
# 毎日午前2時に日次バックアップ
0 2 * * * backupmgmt /path/to/scripts/backup/postgres_daily_backup.sh

# 毎週日曜日午前3時に週次バックアップ
0 3 * * 0 backupmgmt /path/to/scripts/backup/postgres_weekly_backup.sh
```

#### 2. PITR（Point-in-Time Recovery）設定

**WALアーカイブ設定** (`postgresql.conf`):

```ini
# WAL設定
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /mnt/backups/postgres/wal_archive/%f && cp %p /mnt/backups/postgres/wal_archive/%f'
archive_timeout = 300  # 5分ごとにWALを切り替え

# WAL保持
wal_keep_size = 1GB
max_wal_senders = 3
```

**ベースバックアップスクリプト** (`scripts/backup/postgres_base_backup.sh`):

```bash
#!/bin/bash
# PostgreSQL PITRベースバックアップ

BACKUP_DIR="/mnt/backups/postgres/base"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# pg_basebackup実行
PGPASSWORD='password' pg_basebackup \
    -h localhost \
    -p 5434 \
    -U backupmgmt \
    -D "$BACKUP_DIR/base_${TIMESTAMP}" \
    -Ft \
    -z \
    -P \
    -X stream

echo "Base backup completed: base_${TIMESTAMP}" >> \
    /var/log/postgres_backup.log
```

---

### C. 監視・アラート

#### 1. PostgreSQL監視ダッシュボード

**Web UIベース監視** (`app/views/admin/postgres_monitor.py`):

```python
"""PostgreSQL監視ダッシュボード"""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.decorators import admin_required
from app.services.postgres_monitor_service import PostgresMonitorService

bp = Blueprint('postgres_monitor', __name__, url_prefix='/admin/postgres')

@bp.route('/')
@login_required
@admin_required
def dashboard():
    """PostgreSQL監視ダッシュボード"""
    return render_template('admin/postgres_monitor.html')

@bp.route('/api/stats')
@login_required
@admin_required
def get_stats():
    """PostgreSQL統計情報取得API"""
    service = PostgresMonitorService()

    return jsonify({
        'connections': service.get_connection_stats(),
        'database_size': service.get_database_size(),
        'table_sizes': service.get_table_sizes(),
        'slow_queries': service.get_slow_queries(),
        'cache_hit_ratio': service.get_cache_hit_ratio(),
        'index_usage': service.get_index_usage(),
        'locks': service.get_active_locks(),
    })
```

#### 2. パフォーマンスアラート

**Celeryタスクで定期監視** (`app/tasks/postgres_monitoring_tasks.py`):

```python
"""PostgreSQL監視タスク"""
from app.tasks import celery_app
from app.services.postgres_monitor_service import PostgresMonitorService
from app.tasks.notification_tasks import send_multi_channel_notification

@celery_app.task(name='app.tasks.postgres_monitoring.check_performance')
def check_postgres_performance():
    """PostgreSQLパフォーマンスチェック"""
    service = PostgresMonitorService()

    # 接続数チェック
    conn_stats = service.get_connection_stats()
    if conn_stats['active'] > 80:  # 80接続以上
        send_multi_channel_notification.apply_async(
            kwargs={
                'channels': ['email', 'teams', 'dashboard'],
                'title': 'PostgreSQL接続数警告',
                'message': f"アクティブ接続数: {conn_stats['active']}",
                'severity': 'warning',
            }
        )

    # キャッシュヒット率チェック
    cache_ratio = service.get_cache_hit_ratio()
    if cache_ratio < 0.90:  # 90%未満
        send_multi_channel_notification.apply_async(
            kwargs={
                'channels': ['email', 'dashboard'],
                'title': 'PostgreSQLキャッシュヒット率低下',
                'message': f"キャッシュヒット率: {cache_ratio:.2%}",
                'severity': 'warning',
            }
        )

    # スロークエリチェック
    slow_queries = service.get_slow_queries(min_duration_ms=5000)
    if slow_queries:
        send_multi_channel_notification.apply_async(
            kwargs={
                'channels': ['dashboard'],
                'title': f'スロークエリ検出 ({len(slow_queries)}件)',
                'message': '5秒以上かかるクエリが検出されました',
                'severity': 'info',
            }
        )
```

**スケジュール設定** (`app/celery_config.py`):

```python
from celery.schedules import crontab

class CeleryConfig:
    beat_schedule = {
        # ... 既存のスケジュール ...

        # PostgreSQL監視（5分毎）
        'postgres-performance-check': {
            'task': 'app.tasks.postgres_monitoring.check_performance',
            'schedule': crontab(minute='*/5'),
        },

        # スロークエリレポート（日次）
        'postgres-slow-query-report': {
            'task': 'app.tasks.postgres_monitoring.generate_slow_query_report',
            'schedule': crontab(hour=9, minute=0),
        },
    }
```

---

## 📁 ファイル構成

```
backup-management-system/
├── scripts/
│   ├── backup/
│   │   ├── postgres_daily_backup.sh       # 日次バックアップ
│   │   ├── postgres_weekly_backup.sh      # 週次バックアップ
│   │   ├── postgres_base_backup.sh        # PITRベースバックアップ
│   │   └── postgres_restore.sh            # リストアスクリプト
│   └── monitoring/
│       ├── setup_monitoring.sh            # 監視セットアップ
│       └── check_postgres_health.sh       # ヘルスチェック
│
├── app/
│   ├── services/
│   │   └── postgres_monitor_service.py    # 監視サービス
│   ├── tasks/
│   │   └── postgres_monitoring_tasks.py   # 監視Celeryタスク
│   └── views/
│       └── admin/
│           └── postgres_monitor.py         # 監視ダッシュボード
│
├── app/templates/
│   └── admin/
│       └── postgres_monitor.html          # 監視UI
│
└── deployment/
    ├── pgbouncer/
    │   ├── pgbouncer.ini                  # PgBouncer設定
    │   └── userlist.txt                   # 認証情報
    └── systemd/
        ├── pgbouncer.service              # PgBouncer systemdサービス
        └── postgres-backup.timer          # バックアップタイマー
```

---

## 🔧 設定詳細

### 1. PostgreSQL最適化設定

**メモリ設定**（システムRAM: 8GBの場合）:

```ini
# postgresql.conf

# メモリ
shared_buffers = 2GB              # RAMの25%
effective_cache_size = 6GB        # RAMの75%
work_mem = 16MB                   # 複雑クエリ用
maintenance_work_mem = 512MB      # VACUUM, CREATE INDEX用

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9
min_wal_size = 1GB
max_wal_size = 4GB

# クエリプランナー
random_page_cost = 1.1            # SSD使用時
effective_io_concurrency = 200    # SSD使用時

# 並列クエリ
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
max_worker_processes = 4
```

### 2. 接続プーリング設定

**PgBouncer** (`/etc/pgbouncer/pgbouncer.ini`):

```ini
[databases]
backup_management = host=localhost port=5434 dbname=backup_management

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# プーリングモード
pool_mode = transaction          # トランザクション単位でプール
max_client_conn = 100            # クライアント最大接続数
default_pool_size = 25           # DB接続プールサイズ
min_pool_size = 5                # 最小プールサイズ
reserve_pool_size = 5            # 予約プール
reserve_pool_timeout = 5         # 予約プールタイムアウト

# タイムアウト
server_idle_timeout = 600        # アイドル接続のタイムアウト
server_lifetime = 3600           # 接続の最大生存時間

# ログ
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
```

**userlist.txt**:
```
"backupmgmt" "md5<md5ハッシュ>"
```

生成方法:
```bash
echo -n "passwordbackupmgmt" | md5sum
# 結果をuserlist.txtに記載
```

### 3. バックアップ戦略

#### バックアップタイプと頻度

| タイプ | 頻度 | 保持期間 | 用途 |
|--------|------|----------|------|
| 日次ダンプ | 毎日2:00 | 7日 | 日常復旧 |
| 週次ダンプ | 日曜3:00 | 4週間 | 長期保管 |
| ベースバックアップ | 週1回 | 2週間 | PITR用 |
| WALアーカイブ | 継続的 | 7日 | PITR用 |

#### PITR復旧手順

```bash
# 1. PostgreSQL停止
sudo systemctl stop postgresql

# 2. データディレクトリをバックアップ
mv /var/lib/postgresql/16/main /var/lib/postgresql/16/main.old

# 3. ベースバックアップをリストア
mkdir /var/lib/postgresql/16/main
cd /var/lib/postgresql/16/main
tar -xzf /mnt/backups/postgres/base/base_20251201.tar.gz

# 4. recovery.conf作成
cat > /var/lib/postgresql/16/main/recovery.conf <<EOF
restore_command = 'cp /mnt/backups/postgres/wal_archive/%f %p'
recovery_target_time = '2025-12-02 10:30:00 JST'
recovery_target_action = 'promote'
EOF

# 5. PostgreSQL起動
sudo systemctl start postgresql

# 6. 復旧確認
psql -h localhost -p 5434 -U backupmgmt -d backup_management \
    -c "SELECT NOW();"
```

---

### D. 監視ダッシュボード

#### メトリクス

**収集する指標**:

1. **接続統計**
   - アクティブ接続数
   - アイドル接続数
   - 待機中の接続数

2. **データベースサイズ**
   - 総サイズ
   - テーブル別サイズ
   - インデックスサイズ

3. **パフォーマンス**
   - キャッシュヒット率
   - トランザクション/秒
   - コミット/ロールバック率

4. **クエリ統計**
   - 実行回数トップ10
   - 実行時間トップ10
   - 平均実行時間

5. **リソース使用状況**
   - CPU使用率
   - メモリ使用率
   - ディスクI/O

---

## 🎯 期待される効果

### パフォーマンス

| 項目 | Before | After | 改善率 |
|------|--------|-------|--------|
| 同時接続処理 | ~10 | 100+ | +900% |
| クエリ応答時間 | - | <100ms | - |
| キャッシュヒット率 | - | >95% | - |
| 接続オーバーヘッド | 高 | 低（プーリング） | -80% |

### 可用性

| 項目 | 目標値 | 実装 |
|------|--------|------|
| RPO (目標復旧時点) | 15分 | WALアーカイブ（5分） |
| RTO (目標復旧時間) | 30分 | 自動バックアップ+手順書 |
| バックアップ頻度 | 日次 | 日次+週次+継続的WAL |
| データ保持 | 7日 | 日次7日+週次4週間 |

---

## 🔍 監視アラート基準

### 警告レベル

| メトリクス | 警告 | 危険 | アクション |
|-----------|------|------|-----------|
| 接続数 | >80 | >95 | メール+Teams |
| CPU使用率 | >70% | >90% | メール+Teams |
| ディスク使用率 | >80% | >90% | メール+Teams+ダッシュボード |
| キャッシュヒット率 | <90% | <80% | ダッシュボード |
| スロークエリ | >5秒 | >10秒 | ダッシュボード |
| レプリケーション遅延 | >30秒 | >60秒 | メール+Teams |

---

## 📊 実装スケジュール

### Week 1: パフォーマンス最適化
- Day 1-2: pg_stat_statements設定、スロークエリ検出
- Day 3-4: インデックス分析・最適化
- Day 5: PgBouncerインストール・設定

### Week 2: バックアップ戦略
- Day 1-2: 日次・週次バックアップスクリプト作成
- Day 3-4: PITR設定（WALアーカイブ）
- Day 5: リストアテスト

### Week 3: 監視・アラート
- Day 1-2: 監視サービス実装
- Day 3-4: ダッシュボードUI作成
- Day 5: アラート機能実装

---

## 📝 備考

- PostgreSQLポート: 5434（デフォルト5432から変更）
- PgBouncerポート: 6432（推奨）
- IPアドレス: 192.168.3.135
- Flower監視UI: http://192.168.3.135:5555

---

**作成日**: 2025-12-02
**更新日**: 2025-12-02
**Phase**: 13
**ステータス**: 実装中
