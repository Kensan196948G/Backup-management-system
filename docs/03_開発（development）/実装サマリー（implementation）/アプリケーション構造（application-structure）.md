# Application Structure - Backup Management System

## アプリケーション構造説明

### コアファイル

#### 1. `run.py` - アプリケーションエントリーポイント

メインの起動スクリプト。開発環境と本番環境の両方に対応。

**主な機能:**
- コマンドライン引数の解析
- 環境変数による設定切り替え
- Flask開発サーバー起動（開発環境）
- Waitress WSGIサーバー起動（本番環境）
- データベース初期化

**使用方法:**
```bash
# 開発環境
python run.py

# 本番環境
python run.py --production

# カスタムホスト・ポート
python run.py --host 0.0.0.0 --port 8080

# 設定を指定
python run.py --config production
```

#### 2. `app/__init__.py` - アプリケーションファクトリー

Flask application factoryパターンの実装。全ての初期化ロジックを含む。

**主な機能:**

##### create_app()
アプリケーションインスタンスを作成する工場関数

**初期化フロー:**
1. Flask app作成
2. 設定の読み込み（config.py）
3. ディレクトリの確認・作成
4. ロギング初期化
5. 拡張機能の初期化
6. ブループリントの登録
7. エラーハンドラーの登録
8. スケジューラーの初期化
9. テンプレートコンテキストプロセッサの登録
10. CLIコマンドの登録

##### 初期化される拡張機能

| 拡張機能 | 用途 | 変数名 |
|---------|------|--------|
| SQLAlchemy | データベースORM | `db` |
| Flask-Migrate | データベースマイグレーション | `migrate` |
| Flask-Login | ユーザー認証 | `login_manager` |
| Flask-Mail | メール送信 | `mail` |
| Flask-WTF | フォーム・CSRF保護 | `csrf` |
| APScheduler | バックグラウンドジョブ | `scheduler` |

##### ブループリント

| ブループリント | URLプレフィックス | 説明 |
|-------------|----------------|------|
| `auth_bp` | `/auth` | 認証・ログイン |
| `dashboard_bp` | `/` | ダッシュボード |
| `jobs_bp` | `/jobs` | バックアップジョブ管理 |
| `media_bp` | `/media` | オフラインメディア管理 |
| `verification_bp` | `/verification` | 検証テスト管理 |
| `reports_bp` | `/reports` | レポート管理 |
| `api_bp` | `/api/v1` | REST API |

##### エラーハンドラー

- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **500**: Internal Server Error
- **503**: Service Unavailable
- **Exception**: すべての例外をキャッチ

JSON/APIリクエストとHTML/Webリクエストで異なるレスポンスを返す。

##### スケジューラータスク

| タスク | 実行間隔 | 説明 |
|-------|---------|------|
| `check_compliance_status` | 1時間毎 | 3-2-1-1-0ルール準拠チェック |
| `check_offline_media_updates` | 毎日9:00 | オフラインメディア更新確認 |
| `check_verification_reminders` | 毎日10:00 | 検証テストリマインダー |
| `cleanup_old_logs` | 毎日3:00 | 古いログのクリーンアップ |
| `generate_daily_report` | 毎日8:00 | 日次レポート生成 |

##### テンプレートコンテキスト

全てのテンプレートで利用可能な変数と関数:

**変数:**
- `app_name`: アプリケーション名
- `app_version`: バージョン
- `platform`: プラットフォーム（'nt' / 'posix'）
- `environment`: 環境（development / production）

**関数:**
- `format_datetime(dt, format)`: 日時のフォーマット
- `format_filesize(bytes)`: ファイルサイズの人間可読形式変換
- `compliance_badge_class(is_compliant)`: 準拠バッジのCSSクラス取得

##### Flask CLIコマンド

```bash
# データベース初期化
flask init-db

# 管理者ユーザー作成
flask create-admin

# ルート一覧表示
flask list-routes

# メール送信テスト
flask test-email
```

### 設定管理

#### `app/config.py`

環境別の設定を管理。

**設定クラス:**
- `Config`: 基本設定（共通）
- `DevelopmentConfig`: 開発環境設定
- `ProductionConfig`: 本番環境設定
- `TestingConfig`: テスト環境設定

**主要な設定項目:**

##### Flask基本設定
- `SECRET_KEY`: セッション暗号化キー
- `DEBUG`: デバッグモード
- `TESTING`: テストモード

##### データベース設定
- `SQLALCHEMY_DATABASE_URI`: データベース接続URL
- `SQLALCHEMY_TRACK_MODIFICATIONS`: 変更追跡（False推奨）
- `SQLALCHEMY_ECHO`: SQL出力（開発時のみTrue）

##### セキュリティ設定
- `WTF_CSRF_ENABLED`: CSRF保護
- `SESSION_COOKIE_HTTPONLY`: HTTPOnlyクッキー
- `SESSION_COOKIE_SECURE`: HTTPS限定（本番のみ）
- `PERMANENT_SESSION_LIFETIME`: セッション有効期限

##### パスワードポリシー
- `PASSWORD_MIN_LENGTH`: 最小文字数（8）
- `PASSWORD_REQUIRE_UPPERCASE`: 大文字必須
- `PASSWORD_REQUIRE_LOWERCASE`: 小文字必須
- `PASSWORD_REQUIRE_DIGIT`: 数字必須
- `PASSWORD_REQUIRE_SPECIAL`: 特殊文字必須
- `PASSWORD_EXPIRY_DAYS`: パスワード有効期限（90日）

##### ログイン保護
- `LOGIN_ATTEMPT_LIMIT`: ログイン試行回数制限（5回）
- `LOGIN_ATTEMPT_WINDOW`: 試行回数リセット時間（10分）
- `ACCOUNT_LOCKOUT_DURATION`: アカウントロック時間（10分）

##### メール設定
- `MAIL_SERVER`: SMTPサーバー
- `MAIL_PORT`: ポート番号（587）
- `MAIL_USE_TLS`: TLS使用
- `MAIL_USERNAME`: ユーザー名
- `MAIL_PASSWORD`: パスワード

##### スケジューラー設定
- `SCHEDULER_API_ENABLED`: スケジューラーAPI有効化
- `SCHEDULER_TIMEZONE`: タイムゾーン（'Asia/Tokyo'）

##### 3-2-1-1-0ルール設定
- `MIN_COPIES`: 最小コピー数（3）
- `MIN_MEDIA_TYPES`: 最小メディア種類（2）
- `OFFLINE_MEDIA_UPDATE_WARNING_DAYS`: オフラインメディア更新警告日数（7）

### ロギング

#### ログファイル

| ファイル | 内容 | ローテーション |
|---------|------|--------------|
| `logs/backup_system.log` | アプリケーションログ | サイズ（10MB） |
| `logs/errors.log` | エラーログ | 日次（midnight） |

#### ログレベル

- **DEBUG**: 詳細なデバッグ情報（開発時）
- **INFO**: 一般的な情報
- **WARNING**: 警告
- **ERROR**: エラー
- **CRITICAL**: 致命的なエラー

#### ログフォーマット

```
[2024-10-30 10:00:00] INFO [app.init:100] Application started
[2024-10-30 10:00:01] ERROR [app.views.jobs:250] Failed to save job: Database error
```

### クロスプラットフォーム対応

#### 開発環境（Linux）

- Flask開発サーバー
- SQLite データベース
- UNIX パス（`/`区切り）
- systemd サービス（オプション）

#### 本番環境（Windows 11）

- Waitress WSGIサーバー
- SQLite / PostgreSQL
- Windows パス（`\`区切り）
- NSSM サービス管理
- Windows Event Log統合（将来対応）

#### パス処理

`pathlib.Path`を使用してクロスプラットフォーム対応:

```python
from pathlib import Path

# 正しい
log_dir = Path(app.root_path).parent / 'logs'

# 避ける
log_dir = app.root_path + '/../logs'  # プラットフォーム依存
```

### セキュリティ機能

1. **CSRF保護**: Flask-WTFによるトークン検証
2. **セッション管理**: サーバーサイドセッション
3. **パスワードハッシュ**: bcryptによる暗号化
4. **SQLインジェクション対策**: SQLAlchemy ORM
5. **XSS対策**: Jinjaテンプレートの自動エスケープ
6. **ログイン試行制限**: レート制限とアカウントロック

### パフォーマンス最適化

1. **データベースコネクションプール**: SQLAlchemyによる管理
2. **静的ファイルキャッシング**: ブラウザキャッシュ
3. **遅延ローディング**: relationship lazy='dynamic'
4. **インデックス最適化**: 頻繁にクエリされるカラムにインデックス

### 監視とメンテナンス

1. **ヘルスチェック**: `/api/health` エンドポイント
2. **バージョン情報**: `/api/version` エンドポイント
3. **ログローテーション**: 自動ローテーションと古いログの削除
4. **データベースバックアップ**: 定期バックアップ推奨

### 拡張ポイント

新機能を追加する場合:

1. **新しいモデル**: `app/models.py`に追加
2. **新しいAPI**: `app/api/`に新しいモジュール
3. **新しいビュー**: `app/views/`に新しいモジュール
4. **新しいサービス**: `app/services/`に新しいモジュール
5. **新しいスケジュールタスク**: `app/scheduler/tasks.py`に追加

### デプロイ

#### 開発環境デプロイ

```bash
./start_dev.sh
```

#### 本番環境デプロイ

```bash
./start_prod.sh
```

#### Dockerデプロイ（将来対応）

```bash
docker-compose up -d
```

### トラブルシューティング

#### アプリケーションが起動しない

1. Python バージョン確認: `python --version` (3.9+)
2. 依存パッケージ確認: `pip list`
3. ログ確認: `logs/backup_system.log`

#### データベースエラー

1. マイグレーション実行: `flask db upgrade`
2. データベースファイル確認: `data/backup_mgmt.db`
3. 権限確認: `chmod 666 data/backup_mgmt.db`

#### スケジューラーエラー

1. タスクモジュール確認: `app/scheduler/tasks.py`
2. サービスモジュール確認: `app/services/`
3. スケジューラーログ確認

### 参考資料

- Flask公式ドキュメント: https://flask.palletsprojects.com/
- SQLAlchemy公式ドキュメント: https://docs.sqlalchemy.org/
- APScheduler公式ドキュメント: https://apscheduler.readthedocs.io/
- Waitress公式ドキュメント: https://docs.pylonsproject.org/projects/waitress/
