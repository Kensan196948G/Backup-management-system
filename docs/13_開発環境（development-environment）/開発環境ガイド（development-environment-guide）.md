# 開発環境での動作確認ガイド

## 概要

8エージェント統合後の開発環境での動作確認手順を説明します。

---

## 前提条件

- Python 3.11+
- SQLite または PostgreSQL
- Git Worktree環境構築済み
- 全8エージェントがdevelopブランチに統合済み

---

## Step 1: 環境セットアップ

### 1-1. 仮想環境のアクティベート

```bash
cd /mnt/Linux-ExHDD/backup-management-system

# 仮想環境がなければ作成
python3 -m venv venv

# アクティベート
source venv/bin/activate
```

### 1-2. 依存関係のインストール

```bash
# 開発依存を含む全パッケージ
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 1-3. 環境変数の設定

```bash
# .envファイル作成
cp .env.example .env

# SECRET_KEY生成
python -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')" >> .env

# .envファイル編集
cat >> .env << EOF
FLASK_ENV=development
FLASK_APP=run.py
DATABASE_URL=sqlite:///instance/backup_system.db
EOF
```

---

## Step 2: データベース初期化

### 2-1. データベースマイグレーション

```bash
# マイグレーション実行
flask db upgrade

# 管理者ユーザー作成
python scripts/create_admin.py
```

### 2-2. テストデータ投入（オプション）

```bash
# サンプルバックアップジョブ作成
python -c "
from app import create_app, db
from app.models import BackupJob
from datetime import datetime

app = create_app()
with app.app_context():
    job = BackupJob(
        job_name='Daily System Backup',
        source_path='/home/user/documents',
        destination_paths='/backup/primary,/backup/secondary',
        schedule='0 2 * * *',
        created_at=datetime.utcnow()
    )
    db.session.add(job)
    db.session.commit()
    print(f'✅ Created backup job #{job.id}')
"
```

---

## Step 3: Flask開発サーバー起動

### 3-1. サーバー起動

```bash
# 方法1: run.pyから起動
python run.py

# 方法2: Flask CLIから起動
flask run --host=0.0.0.0 --port=5000

# 方法3: デバッグモードで起動
FLASK_DEBUG=1 flask run
```

### 3-2. サーバー起動確認

別ターミナルで:
```bash
curl http://localhost:5000/
# 期待: ログインページへのリダイレクト（302）

curl -I http://localhost:5000/
# 期待: HTTP/1.1 302 FOUND
```

---

## Step 4: WebUIアクセステスト

### 4-1. ログインページ

ブラウザで以下にアクセス:
```
http://localhost:5000/
または
http://192.168.3.135:5000/
```

**確認項目:**
- [ ] ログインフォームが表示される
- [ ] パスワード表示/非表示トグルが動作する
- [ ] デモクレデンシャルが表示される

**ログイン:**
- Username: `admin`
- Password: `(create_admin.pyで設定したパスワード)`

### 4-2. ダッシュボード

ログイン後、ダッシュボードにリダイレクトされます。

**確認項目:**
- [ ] 4つの統計カードが表示される
- [ ] 各カードクリックでモーダルが開く
- [ ] Chart.jsグラフが表示される
- [ ] ESCキーでモーダルが閉じる

### 4-3. スケジュール管理UI（Agent-06）

```
http://localhost:5000/backup/schedule
```

**確認項目:**
- [ ] スケジュール一覧が表示される
- [ ] Cron式ビルダーが動作する
- [ ] プリセットスケジュールが選択できる
- [ ] 次回実行時刻が表示される

### 4-4. ストレージ設定UI（Agent-06）

```
http://localhost:5000/backup/storage-config
```

**確認項目:**
- [ ] ストレージプロバイダー一覧が表示される
- [ ] 接続テストボタンが動作する
- [ ] 容量バーが表示される

---

## Step 5: API動作確認

### 5-1. 認証テスト

```bash
# JWT トークン取得
TOKEN=$(curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

### 5-2. バックアップAPI テスト

```bash
# バックアップジョブ一覧取得
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/backups | jq .

# 期待: JSONでバックアップジョブ一覧が返る
```

### 5-3. ストレージAPI テスト

```bash
# ストレージプロバイダー一覧
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/storage/providers | jq .

# 期待: 登録済みストレージプロバイダーのリスト
```

### 5-4. 検証API テスト

```bash
# 検証開始
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/verify/1 | jq .

# 期待: 検証ジョブ開始の確認
```

---

## Step 6: 統合テスト実行

### 6-1. Agent-01/02統合テスト

```bash
# Agent-01とAgent-02の統合テスト
pytest tests/integration/test_agent_01_02_integration.py -v

# 期待: 5個のテストがパス
```

### 6-2. 全システムテスト

```bash
# 全システム統合テスト
pytest tests/integration/test_full_system.py -v

# システムコンポーネントimportテスト実行
```

### 6-3. カバレッジレポート

```bash
# テストカバレッジ計測
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# HTMLレポート確認
# htmlcov/index.html をブラウザで開く
```

---

## Step 7: 機能テスト

### 7-1. BackupEngine動作テスト

```bash
python -c "
from app import create_app
from app.core.backup_engine import BackupEngine
from pathlib import Path
import tempfile

app = create_app()
with app.app_context():
    # テストファイル作成
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'Test backup content')
        source = f.name

    # BackupEngine初期化
    engine = BackupEngine()

    # コピー実行
    result = engine.copy_file(source, '/tmp/backup_test.txt')

    print(f'✅ Backup successful')
    print(f'   Bytes: {result[\"bytes_copied\"]}')
    print(f'   Checksum: {result[\"checksum\"]}')
    print(f'   Duration: {result[\"duration\"]}s')
"
```

### 7-2. StorageProvider動作テスト

```bash
python -c "
from app.storage.providers.local_storage import LocalStorageProvider
from app.storage.interfaces import StorageLocation

# LocalStorageProvider初期化
storage = LocalStorageProvider('test', '/tmp/backup', StorageLocation.ONSITE)

# 接続
connected = storage.connect()
print(f'✅ Connected: {connected}')

# 容量確認
info = storage.get_storage_info()
print(f'✅ Storage Info:')
print(f'   Total: {info.total_bytes / (1024**3):.2f} GB')
print(f'   Available: {info.available_bytes / (1024**3):.2f} GB')
print(f'   Usage: {info.usage_percent:.1f}%')
"
```

### 7-3. 3-2-1-1-0ルールバリデーター動作テスト

```bash
python -c "
from app import create_app
from app.core.rule_validator import Rule321110Validator

app = create_app()
with app.app_context():
    validator = Rule321110Validator()

    # モックジョブIDでテスト（実際のジョブがある場合は実IDを使用）
    # result = validator.validate(1, raise_on_violation=False)

    print('✅ Rule321110Validator initialized')
    print('   Validator ready for 3-2-1-1-0 rule checking')
"
```

---

## Step 8: トラブルシューティング

### 8-1. データベース接続エラー

```bash
# データベースファイル確認
ls -lh instance/backup_system.db

# 存在しない場合、初期化
flask db upgrade
python scripts/init_db.py
```

### 8-2. モジュールimportエラー

```bash
# Pythonパスに追加
export PYTHONPATH=/mnt/Linux-ExHDD/backup-management-system:$PYTHONPATH

# または、開発モードでインストール
pip install -e .
```

### 8-3. ポート競合エラー

```bash
# 別のポートで起動
flask run --port=5001

# または、既存のプロセスを停止
lsof -ti:5000 | xargs kill -9
```

---

## 📊 動作確認チェックリスト

### WebUI
- [ ] ログインページ表示
- [ ] ダッシュボード表示
- [ ] 4つのモーダル動作
- [ ] ナビゲーション機能
- [ ] スケジュール管理UI表示
- [ ] ストレージ設定UI表示

### API
- [ ] JWT認証動作
- [ ] バックアップAPI応答
- [ ] ストレージAPI応答
- [ ] 検証API応答

### Backend
- [ ] BackupEngine動作
- [ ] LocalStorageProvider動作
- [ ] 3-2-1-1-0バリデーター動作

### Tests
- [ ] Agent-01/02統合テストパス
- [ ] 全システムテストパス
- [ ] カバレッジ > 70%

---

## 🚀 次のステップ

動作確認完了後:
1. Windows本番環境構築
2. PostgreSQL移行
3. HTTPS/SSL設定
4. 本番デプロイ

---

**作成日**: 2025-11-01
**対象**: 開発環境動作確認
