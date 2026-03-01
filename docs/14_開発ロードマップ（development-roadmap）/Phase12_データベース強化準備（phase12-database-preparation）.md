# Phase 12: データベース & インフラ強化 (準備完了)

**準備日**: 2025年12月2日
**ステータス**: 🟡 準備完了 (移行待ち)
**担当**: Claude Code

---

## 📋 概要

Phase 12では、SQLiteからPostgreSQLへの移行を行い、
エンタープライズグレードのデータ永続性を実現します。

### 目標

| 項目 | 目標 |
|------|------|
| データベース | SQLite → PostgreSQL 15+ |
| 可用性 | 99.99% |
| RPO | 15分以内 |
| RTO | 30分以内 |

---

## 📁 準備済みファイル

```
scripts/database/
├── setup_postgres.sh           # PostgreSQLセットアップスクリプト
└── migrate_sqlite_to_postgres.py  # データ移行スクリプト

requirements.txt                # psycopg2-binary追加済み
app/config.py                   # Celery設定追加済み
```

---

## 🚀 移行手順

### 1. PostgreSQLインストール

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# サービス起動
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. データベース作成

```bash
# セットアップスクリプト実行
cd /path/to/backup-management-system
./scripts/database/setup_postgres.sh setup

# または手動で
sudo -u postgres createuser -P backupmgmt
sudo -u postgres createdb -O backupmgmt backup_management
```

### 3. 環境変数設定

`.env`ファイルに追加:

```bash
# PostgreSQL接続
DATABASE_URL=postgresql://backupmgmt:password@localhost:5432/backup_management

# または個別設定
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=backup_management
POSTGRES_USER=backupmgmt
POSTGRES_PASSWORD=your_secure_password
```

### 4. データ移行

```bash
# 移行スクリプト実行
python scripts/database/migrate_sqlite_to_postgres.py \
    --sqlite-path data/backup_mgmt.db \
    --postgres-url postgresql://backupmgmt:password@localhost/backup_management
```

### 5. アプリケーション設定更新

`app/config.py`の`ProductionConfig`は既に環境変数からDATABASE_URLを読み込むようになっています。

---

## 📊 移行スクリプトの機能

### migrate_sqlite_to_postgres.py

| 機能 | 説明 |
|------|------|
| 接続検証 | SQLite/PostgreSQL両方の接続確認 |
| スキーマ作成 | SQLAlchemyモデルからテーブル生成 |
| バッチ移行 | 1000行ずつバッチ処理 |
| 依存順序 | 外部キー制約を考慮した順序で移行 |
| シーケンスリセット | PostgreSQLのシーケンス値を調整 |
| 検証 | 行数比較による移行検証 |

### 使用例

```bash
# 基本実行
python scripts/database/migrate_sqlite_to_postgres.py \
    --sqlite-path data/backup_mgmt.db \
    --postgres-url postgresql://user:pass@localhost/dbname

# スキーマ作成をスキップ (既存テーブルがある場合)
python scripts/database/migrate_sqlite_to_postgres.py \
    --sqlite-path data/backup_mgmt.db \
    --postgres-url postgresql://user:pass@localhost/dbname \
    --skip-schema

# バッチサイズ変更
python scripts/database/migrate_sqlite_to_postgres.py \
    --sqlite-path data/backup_mgmt.db \
    --postgres-url postgresql://user:pass@localhost/dbname \
    --batch-size 500
```

---

## 🔒 セキュリティ考慮事項

### PostgreSQLセキュリティ設定

1. **強力なパスワード**
   - 最低24文字のランダムパスワード
   - setup_postgres.shが自動生成可能

2. **接続制限**
   - pg_hba.confでローカル接続のみ許可
   - 必要に応じてSSL接続を有効化

3. **権限最小化**
   - アプリケーション用ユーザーは対象DBのみアクセス可能

### 推奨設定 (postgresql.conf)

```ini
# 接続
listen_addresses = 'localhost'
max_connections = 100

# メモリ
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB

# ログ
log_statement = 'ddl'
log_connections = on
log_disconnections = on
```

---

## 📈 移行後の確認事項

### 1. 接続テスト

```bash
psql -h localhost -U backupmgmt -d backup_management -c "SELECT COUNT(*) FROM users;"
```

### 2. アプリケーション動作確認

```bash
# Flaskアプリケーション起動
FLASK_ENV=production python run.py

# APIテスト
curl http://localhost:5000/api/health
```

### 3. パフォーマンス確認

```sql
-- テーブルサイズ確認
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🔄 ロールバック手順

移行に問題が発生した場合:

1. **アプリケーション停止**
   ```bash
   sudo systemctl stop backup-management
   ```

2. **環境変数をSQLiteに戻す**
   ```bash
   # .envファイル編集
   DATABASE_URL=sqlite:///data/backup_mgmt.db
   ```

3. **アプリケーション再起動**
   ```bash
   sudo systemctl start backup-management
   ```

SQLiteのバックアップは移行前に自動的に作成されます。

---

## 📝 次のステップ (Phase 12完了後)

### レプリケーション設定 (オプション)

```
┌─────────────┐     ┌─────────────┐
│   Primary   │────▶│   Replica   │
│ PostgreSQL  │     │ PostgreSQL  │
│  (Read/Write)│     │  (Read-only) │
└─────────────┘     └─────────────┘
```

### バックアップ自動化

- pg_dump定期実行 (cron)
- WALアーカイブ設定
- オフサイトバックアップ

---

## 🔧 追加された依存関係

```
# requirements.txt
psycopg2-binary==2.9.9
```

---

**準備完了日**: 2025年12月2日
**移行推奨時期**: システムメンテナンス時間帯

---

🤖 Generated by Claude Code
