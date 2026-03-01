# テストスイート - 3-2-1-1-0 バックアップ管理システム

## 概要

このディレクトリには、3-2-1-1-0バックアップ管理システムの包括的なテストスイートが含まれています。

- **総テスト数**: 195テストケース
- **単体テスト**: 97テスト
- **統合テスト**: 98テスト

## ディレクトリ構造

```
tests/
├── __init__.py              # テストパッケージ初期化
├── conftest.py              # pytest設定とfixtures (568行)
├── unit/                    # 単体テスト
│   ├── __init__.py
│   ├── test_models.py       # モデルテスト (665行, 36テスト)
│   ├── test_auth.py         # 認証テスト (401行, 29テスト)
│   └── test_services.py     # サービステスト (458行, 32テスト)
└── integration/             # 統合テスト
    ├── __init__.py
    ├── test_api_endpoints.py   # APIテスト (715行, 51テスト)
    ├── test_auth_flow.py       # 認証フロー (403行, 16テスト)
    └── test_workflows.py       # ワークフロー (620行, 31テスト)
```

## クイックスタート

### 1. 依存関係のインストール

```bash
# 仮想環境のアクティベート
source venv/bin/activate

# テスト依存関係のインストール
pip install pytest pytest-cov pytest-mock pytest-flask
```

### 2. 全テスト実行

```bash
pytest tests/ -v
```

### 3. カバレッジレポート生成

```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
```

HTMLレポートは `htmlcov/index.html` に生成されます。

## テスト実行例

### 単体テストのみ実行

```bash
pytest tests/unit/ -v
```

### 統合テストのみ実行

```bash
pytest tests/integration/ -v
```

### 特定のテストクラス実行

```bash
pytest tests/unit/test_models.py::TestUserModel -v
```

### 特定のテスト関数実行

```bash
pytest tests/unit/test_models.py::TestUserModel::test_create_user -v
```

### 並列実行 (高速化)

```bash
pip install pytest-xdist
pytest tests/ -n auto
```

### マーカーを使用した実行

```bash
# 遅いテストをスキップ
pytest tests/ -v -m "not slow"

# 統合テストのみ
pytest tests/ -v -m integration
```

## テストカテゴリ

### 単体テスト (Unit Tests)

#### 1. モデルテスト (`test_models.py`)
全14モデルの包括的なテスト:

- **User**: 認証、役割、権限
- **BackupJob**: ジョブ定義、CRUD
- **BackupCopy**: 3-2-1-1-0ルール対応
- **OfflineMedia**: オフラインメディア管理
- **MediaRotationSchedule**: ローテーションスケジュール
- **MediaLending**: メディア貸出管理
- **VerificationTest**: 検証テスト記録
- **VerificationSchedule**: 検証スケジュール
- **BackupExecution**: 実行履歴
- **ComplianceStatus**: コンプライアンス状態
- **Alert**: アラート管理
- **AuditLog**: 監査ログ
- **Report**: レポート生成
- **SystemSetting**: システム設定

#### 2. 認証テスト (`test_auth.py`)
認証・認可システムのテスト:

- ログイン/ログアウト
- パスワード管理
- 役割ベースアクセス制御 (RBAC)
- セッション管理
- ユーザー登録
- アカウントセキュリティ

#### 3. サービステスト (`test_services.py`)
ビジネスロジックのテスト:

- **ComplianceChecker**: 3-2-1-1-0ルール検証
- **AlertManager**: アラート作成・管理
- **ReportGenerator**: レポート生成

### 統合テスト (Integration Tests)

#### 1. APIエンドポイントテスト (`test_api_endpoints.py`)
43+APIエンドポイントのテスト:

- **Backup API**: ステータス更新
- **Jobs API**: ジョブ管理 (CRUD + 実行)
- **Alerts API**: アラート管理
- **Reports API**: レポート生成
- **Dashboard API**: ダッシュボードデータ
- **Media API**: メディア管理
- **Verification API**: 検証テスト

#### 2. 認証フローテスト (`test_auth_flow.py`)
エンドツーエンド認証フロー:

- ログイン/ログアウトフロー
- 役割別アクセスフロー
- パスワード変更フロー
- セッション永続性
- 監査ログ記録

#### 3. ワークフローテスト (`test_workflows.py`)
複雑なビジネスワークフロー:

- バックアップライフサイクル
- コンプライアンスチェック
- アラートハンドリング
- レポート生成
- メディアローテーション
- 検証テストワークフロー

## Fixtures

### データベース関連
```python
@pytest.fixture
def app():
    """Flask application with test config"""

@pytest.fixture
def client(app):
    """Test client for HTTP requests"""

@pytest.fixture
def db_session(app):
    """Database session with rollback"""
```

### ユーザー関連
```python
@pytest.fixture
def admin_user(app):
    """Admin user with full permissions"""

@pytest.fixture
def operator_user(app):
    """Operator user with edit permissions"""

@pytest.fixture
def auditor_user(app):
    """Auditor user with read-only permissions"""
```

### バックアップ関連
```python
@pytest.fixture
def backup_job(app, admin_user):
    """Single backup job"""

@pytest.fixture
def multiple_backup_jobs(app, admin_user):
    """Multiple backup jobs"""

@pytest.fixture
def backup_copies(app, backup_job):
    """Backup copies following 3-2-1-1-0 rule"""
```

### 認証関連
```python
@pytest.fixture
def authenticated_client(client, app):
    """Client authenticated as admin"""

@pytest.fixture
def operator_authenticated_client(client, app):
    """Client authenticated as operator"""

@pytest.fixture
def auditor_authenticated_client(client, app):
    """Client authenticated as auditor"""
```

## テスト規約

### ファイル命名
- テストファイル: `test_*.py`
- テストクラス: `Test*`
- テスト関数: `test_*`

### テスト構造
```python
class TestFeature:
    """Test cases for feature X."""

    def test_normal_case(self, fixture):
        """Test normal operation."""
        # Arrange
        # Act
        # Assert

    def test_edge_case(self, fixture):
        """Test edge case."""
        # Arrange
        # Act
        # Assert

    def test_error_case(self, fixture):
        """Test error handling."""
        # Arrange
        # Act
        # Assert
```

### アサーション
```python
# 良い例
assert user.is_admin() is True
assert response.status_code == 200
assert "error" in response.data.lower()

# 避けるべき例
assert user.is_admin()  # ブール値の明示的比較
assert response.status_code  # 値の範囲チェック不足
```

## カバレッジ目標

### 現在のカバレッジ
- **モデル**: 90%以上
- **サービス**: 85%以上
- **API**: 80%以上
- **認証**: 95%以上

### カバレッジレポート生成
```bash
# HTMLレポート
pytest tests/ --cov=app --cov-report=html

# ターミナル表示
pytest tests/ --cov=app --cov-report=term-missing

# XML (CI/CD用)
pytest tests/ --cov=app --cov-report=xml
```

### カバレッジ確認
```bash
# ブラウザでHTMLレポートを開く
xdg-open htmlcov/index.html
```

## CI/CD統合

### GitHub Actions例
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-flask
      - name: Run tests
        run: pytest tests/ --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## トラブルシューティング

### テストが遅い
```bash
# 並列実行を使用
pip install pytest-xdist
pytest tests/ -n auto

# 失敗時に停止
pytest tests/ -x

# 最後の失敗したテストから再開
pytest tests/ --lf
```

### データベースエラー
```bash
# テストデータベースをクリーン
rm -f data/test.db

# マイグレーション再実行
flask db upgrade
```

### Import エラー
```bash
# PYTHONPATHを設定
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# または環境変数を使用
PYTHONPATH=. pytest tests/
```

## ベストプラクティス

### 1. テスト分離
- 各テストは独立して実行可能
- テスト間でデータを共有しない
- fixtureでクリーンな状態を保証

### 2. 明確性
- テスト名が目的を表現
- Docstringで詳細を説明
- AAA (Arrange-Act-Assert) パターン

### 3. 保守性
- DRY (Don't Repeat Yourself)
- Fixtureの再利用
- ヘルパー関数の使用

### 4. カバレッジ
- 正常系と異常系の両方
- エッジケース
- セキュリティテスト

## パフォーマンステスト

### ロードテスト (未実装)
```python
# 将来の実装例
def test_api_load():
    """Test API under load."""
    # Locust or Apache JMeter
```

### ストレステスト (未実装)
```python
# 将来の実装例
def test_database_stress():
    """Test database under stress."""
    # 大量データのCRUD操作
```

## セキュリティテスト

### 認証テスト
- パスワードハッシュ化
- セッション管理
- CSRF保護
- XSS防止

### 認可テスト
- 役割ベースアクセス
- リソースレベル権限
- API認証

## 参考資料

- [pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## 貢献

新しいテストを追加する際は:

1. 適切なディレクトリ (unit/integration) を選択
2. 既存の規約に従う
3. Docstringを追加
4. カバレッジを確認
5. 全テストがパスすることを確認

## ライセンス

このテストスイートは、メインプロジェクトと同じライセンスの下で提供されます。
