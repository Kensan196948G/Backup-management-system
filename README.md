# 3-2-1-1-0 バックアップ管理システム

企業向け包括的バックアップ管理・監視システム

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Flask: 3.0+](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

## 📋 概要

3-2-1-1-0バックアップルールに準拠した、企業向けバックアップ管理システムです。
複数のバックアップツール（Veeam、Windows Server Backup、AOMEI Backupper）を統合管理し、
ISO 27001/19650に準拠したコンプライアンス監視機能を提供します。

### 3-2-1-1-0 ルールとは？

- **3つのコピー**: オリジナル + 2つのバックアップ
- **2種類のメディア**: 異なる記録媒体を使用
- **1つのオフサイト**: 物理的に離れた場所に保管
- **1つのオフライン**: ネットワークから切り離されたコピー
- **0エラー**: 定期的な検証で完全性を保証

## ✨ 主な機能

### 🎯 コア機能
- ✅ 3-2-1-1-0 ルール自動チェック
- ✅ 複数バックアップツール統合管理
- ✅ リアルタイム監視ダッシュボード
- ✅ アラート・通知機能（メール/Teams）
- ✅ コンプライアンスレポート自動生成

### 🔍 対応バックアップツール
- **Veeam Backup & Replication** - PowerShell統合による自動ステータス送信
- **Windows Server Backup** - タスクスケジューラー連携
- **AOMEI Backupper** - ログ監視・解析による自動連携

### 📊 レポート機能
- 日次/週次/月次バックアップレポート
- ISO 27001監査対応レポート
- ISO 19650 BIMデータ管理レポート
- カスタマイズ可能なレポートテンプレート

## 🚀 クイックスタート

### 前提条件

- Python 3.11以上
- Node.js 18以上（MCP機能用）
- Git 2.30以上

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/Kensan196948G/backup-management-system.git
cd backup-management-system

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows

# 依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
nano .env  # トークンとAPIキーを設定

# データベースの初期化
flask db upgrade

# 開発サーバーの起動
flask run
```

ブラウザで http://localhost:5000 にアクセス

## 🎮 カスタムコマンド

開発を効率化するための3つのカスタムコマンドを用意しています：

### `/commit` - コミット＆プッシュ
変更をコミットしてリモートにプッシュします。
```
/commit
```

### `/pr` - プルリクエスト作成
既にプッシュ済みの変更に対してPRを作成します。
```
/pr
```

### `/commit-and-pr` - 一括実行
コミット、プッシュ、PR作成を一括で実行します。
```
/commit-and-pr
```

詳細は [カスタムコマンドガイド](docs/CUSTOM_COMMANDS.md) を参照してください。

## 📚 ドキュメント

**すべてのドキュメントは整理されたカテゴリー別に配置されています。**

### 📖 スタートガイド

- 🗺️ **[ドキュメント構造マップ](docs/00_ドキュメント構造（documentation-map）.md)** - 全ドキュメント索引（72ファイル）
- 🚀 **[クイックスタート](docs/02_セットアップ（setup）/クイックスタート（quickstart）.md)** - 最速5分で起動
- 💻 **[インストールガイド](docs/02_セットアップ（setup）/インストールガイド（installation）.md)** - 詳細インストール手順

### 📋 要件と設計

- 📋 [要件定義書](docs/01_要件・設計（requirements-design）/要件定義書（requirements）.md) - システム要件
- 🏗️ [設計仕様書](docs/01_要件・設計（requirements-design）/設計仕様書（design-spec）.md) - 詳細設計仕様

### 👨‍💻 開発者向け

- 🏛️ [アーキテクチャ概要](docs/09_アーキテクチャ（architecture）/アーキテクチャ概要（architecture-overview）.md) - システム全体像
- 🔧 [アプリケーション構造](docs/03_開発（development）/実装サマリー（implementation）/アプリケーション構造（application-structure）.md) - コード構造
- 🎉 [フェーズ8-10 MVP達成](docs/03_開発（development）/フェーズレポート（phase-reports）/フェーズ8-10 MVP達成（phase8-10-mvp）.md) - **MVP 100%達成報告**

### 🔌 API統合

- 📡 [API使用例](docs/04_API（api）/API使用例（api-usage-examples）.md) - API使用方法
- 🔐 [認証実装](docs/04_API（api）/認証実装（auth-implementation）.md) - 認証・認可

### 🚀 デプロイメント

#### Windows本番環境
- 🎯 **[Windows本番環境移行手順書](docs/WINDOWS_PRODUCTION_MIGRATION.md)** - **最新・完全版ガイド（推奨）**
- 🚀 [クイックスタート](deployment/windows/QUICKSTART.md) - 30分で完了
- 📘 [クリーンインストールガイド](WINDOWS_CLEAN_INSTALL_GUIDE.md) - 簡易版

#### 一般ガイド
- 🚀 [デプロイガイド](docs/05_デプロイメント（deployment）/デプロイガイド（deployment-guide）.md) - Windows/Linux デプロイ手順
- 📖 [本番運用マニュアル](docs/05_デプロイメント（deployment）/本番運用マニュアル（production-operations）.md) - 運用ガイド
- 🔧 [Veeam統合ガイド](docs/05_デプロイメント（deployment）/Veeam統合ガイド（veeam-integration）.md) - Veeam連携

### PowerShell統合

- [PowerShell統合 README](scripts/powershell/README.md) - Windows環境向けバックアップツール連携
- [テスト手順書](scripts/powershell/TESTING_GUIDE.md) - 動作テストとトラブルシューティング
- [実装サマリー](scripts/powershell/IMPLEMENTATION_SUMMARY.md) - 実装詳細と技術仕様

## 🛠️ 技術スタック

### バックエンド
- **フレームワーク**: Flask 3.0+
- **ORM**: SQLAlchemy
- **データベース**: SQLite（開発）/ PostgreSQL（本番）
- **スケジューラー**: APScheduler
- **認証**: Flask-Login

### フロントエンド
- **テンプレート**: Jinja2
- **CSS**: Bootstrap 5
- **JavaScript**: Chart.js, jQuery

### 開発環境
- **OS**: Linux (Ubuntu 22.04/24.04 LTS)
- **エディタ**: VSCode + Claude Code
- **バージョン管理**: Git + GitHub
- **AI支援**: Claude Code + MCP（Model Context Protocol）

### 本番環境
- **OS**: Windows 11 Enterprise
- **サービス化**: NSSM (Non-Sucking Service Manager)

## 🤖 AI支援開発

本プロジェクトは、Claude Code + MCPを活用した次世代開発手法を採用しています。

### MCPサーバー構成

1. **Filesystem MCP** - ファイルシステム操作
2. **GitHub MCP** - リポジトリ管理・自動コミット
3. **SQLite MCP** - データベース操作
4. **Context7 MCP** - 長期記憶・コンテキスト管理
5. **Brave Search MCP** - 技術情報検索
6. **Serena MCP** - Webスクレイピング
7. **Chrome DevTools MCP** - ブラウザ自動化・デバッグ
8. **Memory MCP** - 永続的メモリ管理
9. **Sequential Thinking MCP** - 複雑な問題の段階的思考
10. **Puppeteer MCP** - ヘッドレスブラウザ制御

詳細は [MCP設定ガイド](docs/MCP_SETUP_GUIDE.md) を参照してください。

### Agent構成（並列開発）

10体のサブエージェントによる並列開発を実現：

1. プロジェクトマネージャー
2. データベースアーキテクト
3. バックエンドAPI開発者
4. フロントエンド開発者
5. 認証・セキュリティエンジニア
6. ビジネスロジック開発者
7. スケジューラー・通知開発者
8. PowerShell統合エンジニア
9. テストエンジニア
10. DevOps/デプロイエンジニア

## 📁 プロジェクト構造

```
backup-management-system/
├── app/                    # アプリケーション本体
│   ├── api/               # REST API エンドポイント
│   ├── auth/              # 認証・認可
│   ├── models.py          # データベースモデル
│   ├── services/          # ビジネスロジック
│   ├── scheduler/         # スケジュールタスク
│   ├── templates/         # HTMLテンプレート
│   ├── static/            # 静的ファイル（CSS/JS）
│   └── utils/             # ユーティリティ
├── data/                  # データベースファイル
├── docs/                  # ドキュメント
├── deployment/            # デプロイスクリプト
│   ├── linux/            # Linux用スクリプト
│   └── windows/          # Windows用スクリプト
├── migrations/            # データベースマイグレーション
├── scripts/               # 開発用スクリプト
│   └── powershell/       # Windows統合スクリプト
│       ├── common_functions.ps1    # 共通関数
│       ├── veeam_integration.ps1   # Veeam連携
│       ├── wsb_integration.ps1     # WSB連携
│       ├── aomei_integration.ps1   # AOMEI連携
│       ├── register_scheduled_tasks.ps1  # タスク管理
│       ├── install.ps1             # インストーラー
│       ├── config.json             # 設定ファイル
│       └── README.md               # 詳細ドキュメント
├── tests/                 # テストコード
├── .claude/               # Claude Code設定
├── .env.example           # 環境変数テンプレート
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt       # Python依存パッケージ
```

## 🔒 セキュリティ

### 認証・認可
- ロールベースアクセス制御（RBAC）
- パスワードハッシュ化（bcrypt）
- セッション管理

### データ保護
- 機密情報の環境変数管理
- データベース暗号化
- 監査ログの記録

### コンプライアンス
- ISO 27001準拠
- ISO 19650準拠
- GDPR対応

## 🧪 テスト

```bash
# 単体テストの実行
pytest tests/

# カバレッジ測定
pytest --cov=app tests/

# 統合テストの実行
pytest tests/integration/
```

## 📦 デプロイ

### Linux環境

```bash
cd deployment/linux
./deploy.sh
```

### Windows環境

```powershell
cd deployment\windows
.\deploy.ps1
```

詳細は各スクリプト内のコメントを参照してください。

## 🤝 コントリビューション

貢献は大歓迎です！以下の手順でお願いします：

1. このリポジトリをフォーク
2. 機能ブランチを作成（`git checkout -b feature/amazing-feature`）
3. 変更をコミット（`git commit -m 'Add amazing feature'`）
4. ブランチをプッシュ（`git push origin feature/amazing-feature`）
5. プルリクエストを作成

## 📝 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 📧 サポート・問い合わせ

- **Issues**: https://github.com/Kensan196948G/backup-management-system/issues
- **Discussions**: https://github.com/Kensan196948G/backup-management-system/discussions

## 🙏 謝辞

- Anthropic Claude - AI支援開発
- Model Context Protocol - 外部システム連携
- すべてのオープンソースコントリビューター

---

**開発状況**: 🚧 初期開発フェーズ
**最終更新**: 2025年10月30日
