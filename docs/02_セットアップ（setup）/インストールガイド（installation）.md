# Backup Management System - Installation Guide

## 3-2-1-1-0 バックアップ管理システム インストールガイド

### 前提条件

- Python 3.9 以上
- pip (Python package manager)
- SQLite (開発環境) / PostgreSQL (本番環境推奨)
- Git

### インストール手順

#### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd backup-management-system
```

#### 2. 仮想環境の作成（推奨）

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

#### 4. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成:

```bash
cp .env.example .env
```

`.env`ファイルを編集して、必要な設定を追加:

```bash
# Flask設定
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# データベース設定
DATABASE_URL=sqlite:///data/backup_mgmt.db

# メール設定（通知機能用）
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password

# Microsoft Teams Webhook (オプション)
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
```

#### 5. データベースの初期化

```bash
# データベーステーブルの作成
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# または
python run.py  # 自動的にテーブルが作成されます
```

#### 6. 管理者ユーザーの作成

```bash
flask create-admin
```

対話形式で以下の情報を入力:
- Username: admin
- Email: admin@example.com
- Password: (secure password)
- Full Name: System Administrator

### 起動方法

#### 開発環境（Linux/macOS）

```bash
# 方法1: run.pyを使用
python run.py

# 方法2: Flask CLIを使用
flask run

# 方法3: デバッグモードで起動
FLASK_ENV=development python run.py
```

#### 本番環境（Windows/Linux）

```bash
# Waitress WSGIサーバーで起動
python run.py --production

# または環境変数で指定
FLASK_ENV=production python run.py

# ホストとポートを指定
python run.py --production --host 0.0.0.0 --port 8080
```

#### アクセス

ブラウザで以下のURLにアクセス:

```
http://127.0.0.1:5000  (開発環境)
http://localhost:8080  (本番環境)
```

### ディレクトリ構造

```
backup-management-system/
├── app/                    # アプリケーションコード
│   ├── __init__.py        # アプリケーション初期化
│   ├── config.py          # 設定
│   ├── models.py          # データモデル
│   ├── auth/              # 認証モジュール
│   ├── api/               # REST API
│   ├── views/             # Webビュー
│   ├── services/          # ビジネスロジック
│   ├── scheduler/         # スケジューラー
│   ├── utils/             # ユーティリティ
│   ├── static/            # 静的ファイル
│   └── templates/         # テンプレート
├── data/                   # データベースファイル
├── logs/                   # ログファイル
├── reports/                # 生成されたレポート
├── migrations/             # データベースマイグレーション
├── tests/                  # テストコード
├── run.py                  # アプリケーションエントリーポイント
├── requirements.txt        # Python依存パッケージ
├── .env                    # 環境変数（作成が必要）
└── .env.example           # 環境変数のサンプル
```

### Flask CLIコマンド

```bash
# データベース初期化
flask init-db

# 管理者ユーザー作成
flask create-admin

# ルート一覧表示
flask list-routes

# メール送信テスト
flask test-email

# データベースマイグレーション
flask db migrate -m "Migration message"
flask db upgrade
flask db downgrade
```

### トラブルシューティング

#### データベースエラー

```bash
# マイグレーションをリセット
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

#### ポートが既に使用されている

```bash
# 別のポートを指定
python run.py --port 8080
```

#### パッケージのインストールエラー

```bash
# pipをアップグレード
pip install --upgrade pip

# 再インストール
pip install -r requirements.txt --force-reinstall
```

### 開発環境 vs 本番環境

| 項目 | 開発環境 | 本番環境 |
|------|---------|----------|
| WSGIサーバー | Flask dev server | Waitress |
| データベース | SQLite | SQLite / PostgreSQL |
| デバッグモード | ON | OFF |
| ログレベル | DEBUG | INFO/WARNING |
| CSRF保護 | OFF | ON |
| セッション | HTTP | HTTPS推奨 |

### セキュリティ設定

本番環境では以下の設定を必ず行ってください:

1. `SECRET_KEY`を強力なランダム文字列に変更
2. `DATABASE_URL`を環境変数で設定
3. HTTPS通信を有効化
4. ファイアウォール設定
5. 定期的なバックアップ

### システム要件

- CPU: 2コア以上
- メモリ: 4GB以上
- ストレージ: 10GB以上（ログとレポート用）
- OS: Linux (Ubuntu 20.04+) / Windows 11 / macOS

### サポート

- ドキュメント: `/docs/`
- 設計仕様書: `/docs/設計仕様書_3-2-1-1-0バックアップ管理システム.txt`
- Issue Tracker: (GitHub Issues)
