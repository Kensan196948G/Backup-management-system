# CLAUDE.md - 3-2-1-1-0 Backup Management System

## プロジェクト概要
企業向けバックアップ管理・監視システム（3-2-1-1-0ルール準拠）
- **言語**: Python 3.11+ (現環境: 3.14.0)
- **フレームワーク**: Flask 3.0+, SQLAlchemy 2.0
- **DB**: SQLite（開発）/ PostgreSQL（本番）
- **WSGI**: Waitress（本番）/ Flask内蔵（開発）

## 開発環境セットアップ

### 仮想環境
```bash
# 仮想環境作成（初回のみ）
python -m venv venv

# アクティベート（Linux/Mac）
source venv/bin/activate

# アクティベート（Windows）
venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### アプリケーション起動
```bash
# 開発サーバー起動
python run.py --config development
# URL: http://127.0.0.1:5000
# 認証: admin / Admin123!
```

## アーキテクチャ

### ディレクトリ構造
```
app/
  __init__.py     # アプリファクトリー
  models.py       # 16データベースモデル
  config.py       # 設定クラス（Dev/Prod/Test）
  api/            # REST API v1（97エンドポイント）
  auth/           # 認証・認可（RBAC）
  core/           # バックアップエンジン・ルール検証
  scheduler/      # APSchedulerベーススケジューラー
  services/       # ビジネスロジック（9サービス）
  storage/        # ストレージプロバイダー
  verification/   # バックアップ検証
  views/          # Flaskビューコントローラー
  utils/          # キャッシュ・メトリクス・セキュリティ
  templates/      # Jinja2テンプレート（42ファイル）
  static/         # CSS/JS
```

### 主要データモデル（16個）
1. User / BackupJob / BackupCopy / BackupExecution
2. OfflineMedia / MediaRotationSchedule / MediaLending
3. VerificationTest / VerificationSchedule
4. ComplianceStatus / Alert / AuditLog
5. Report / SystemSetting / NotificationLog / APIKey

## カスタムコマンド
- `/commit` - コミット＆プッシュ
- `/pr` - プルリクエスト作成
- `/commit-and-pr` - コミット・PR・マージ一括実行
- `/code-review` - コードレビュー

## 開発フェーズ状況

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1-4 | コア実装、DB、API、WebUI | ✅ 完了 |
| Phase 5-7 | テスト品質、ルート統合、デプロイ | ✅ 完了 |
| Phase 8-10 | 通知、テスト品質向上、本番最適化 | ✅ 完了（MVP 100%） |
| Phase 11 | UIウィザード、モーダル、Celery | ✅ 完了 |
| Phase 12 | PostgreSQL移行 | ✅ 完了（develop） |
| Phase 13 | PostgreSQL最適化・監視 | ✅ 完了（develop） |
| Phase 14 | 環境分離・クロスプラットフォーム | 🔄 PR #25 OPEN |
| Phase 15 | 次フェーズ（要定義） | ⏳ 未着手 |

## GitHub状態

### 未クローズPR
- **PR #25** (OPEN): Phase 14 - 環境分離とクロスプラットフォーム対応 (develop → main)
- **PR #26** (DRAFT): 自己修復ループシステム (copilot/implement-self-healing-loop)

### 未解決Issue
- **Issue #10, #11**: 自動検出バグ（2025-11-01）

## テスト実行
```bash
# 全テスト
pytest tests/ -v

# カバレッジ付き
pytest tests/ --cov=app --cov-report=html

# 特定テスト
pytest tests/unit/ -v
pytest tests/integration/ -v

# リント
flake8 app/ tests/
black app/ tests/
isort app/ tests/
```

## 本番デプロイ
- Windows: `scripts/powershell/install.ps1`
- Linux: `deployment/linux/QUICKSTART.md`
- HTTPS: ポート8443（自己署名SSL）
- サービス: systemd（Linux）/ NSSM（Windows）

## 統合バックアップツール
- **Veeam**: `scripts/powershell/veeam_integration.ps1`
- **Windows Server Backup**: `scripts/powershell/wsb_integration.ps1`
- **AOMEI Backupper**: `scripts/powershell/aomei_integration.ps1`

## MCP設定（README参照）
1. filesystem, github, sqlite, context7
2. brave-search, serena, playwright, memory
3. sequential-thinking（Phase 14追加）

## 重要な技術的注意事項
- `datetime.utcnow()` 使用箇所11件 → 将来的に`datetime.now(timezone.utc)`へ移行必要
- Python 3.14.0環境 → pip直接インストール不可のためvenv経由を使用
- テストカバレッジ: 42%（目標80%）
- 239テストケース中176成功（90%成功率）
