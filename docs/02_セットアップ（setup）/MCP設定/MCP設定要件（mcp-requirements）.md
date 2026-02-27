================================================================================
                    MCP設定要件書
           3-2-1-1-0バックアップ管理システム
================================================================================

文書番号: MCP-CONFIG-001
版番号: 1.0
作成日: 2025年10月30日
プロジェクト: backup-management-system
GitHubリポジトリ: https://github.com/Kensan196948G/backup-management-system

================================================================================
目次
================================================================================

1. プロジェクト概要
2. MCP（Model Context Protocol）概要
3. 必要なMCPサーバー一覧
4. MCP設定ファイル
5. 各MCPの詳細説明
6. セットアップ手順
7. Agent機能構成
8. セキュリティ要件
9. 動作確認手順
10. トラブルシューティング

================================================================================
1. プロジェクト概要
================================================================================

【プロジェクト名】
3-2-1-1-0バックアップ管理システム

【開発環境】
- OS: Linux (Ubuntu 22.04/24.04 LTS)
- プロジェクトパス: /mnt/Linux-ExHDD/backup-management-system
- 開発ツール: VSCode + Claude Code
- バージョン管理: Git + GitHub

【本番環境】
- OS: Windows 11 Enterprise
- デプロイ方式: NSSM サービス化

【開発手法】
- Agent機能による並列開発（10体のサブエージェント）
- Hooksによる並列実行
- Context7による長期記憶管理

================================================================================
2. MCP（Model Context Protocol）概要
================================================================================

MCPは、Claude（AI）が外部システムと連携するためのプロトコルです。

【MCPの役割】
- ファイルシステムへのアクセス
- GitHubリポジトリ操作
- データベース操作
- Web検索・スクレイピング
- 各種APIとの統合

【設定ファイル場所】
~/.config/Claude/claude_desktop_config.json

================================================================================
3. 必要なMCPサーバー一覧
================================================================================

【フェーズ1: 初期開発（必須）】

1. Filesystem MCP ✅
   役割: ファイル・ディレクトリ操作
   パッケージ: @modelcontextprotocol/server-filesystem
   優先度: 必須

2. GitHub MCP 🔴
   役割: リポジトリ操作、コミット、プッシュ、イシュー管理
   パッケージ: @modelcontextprotocol/server-github
   優先度: 必須

3. SQLite MCP 🟡
   役割: データベーススキーマ確認、クエリ実行
   パッケージ: @modelcontextprotocol/server-sqlite
   優先度: 推奨

4. Brave Search MCP 🟢
   役割: 技術情報検索、エラー解決方法検索
   パッケージ: @modelcontextprotocol/server-brave-search
   優先度: 推奨（オプション）

【フェーズ2: 機能拡張（将来）】

5. Serena MCP 🟡
   役割: Webスクレイピング、ドキュメント収集
   パッケージ: @oraios/serena-mcp
   URL: https://github.com/oraios/serena
   優先度: オプション
   用途:
     - Veeam/WSB/AOMAIドキュメント収集
     - ISO 27001/19650最新情報収集
     - 競合製品調査

6. PostgreSQL MCP 🟡
   役割: 大規模運用時のDB管理
   パッケージ: @modelcontextprotocol/server-postgres
   優先度: 将来対応

7. Chrome DevTools MCP 🟢
   役割: WebUIデバッグ、フロントエンド開発支援
   優先度: 推奨（UI実装時）

8. Context7 MCP 🟢
   役割: プロジェクト全体のコンテキスト管理、長期記憶
   優先度: 推奨

================================================================================
4. MCP設定ファイル
================================================================================

【ファイルパス】
~/.config/Claude/claude_desktop_config.json

【設定内容（初期開発用）】

{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/mnt/Linux-ExHDD/backup-management-system"
      ]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_YOUR_TOKEN_HERE"
      }
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "YOUR_BRAVE_API_KEY_HERE"
      }
    },
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "--db-path",
        "/mnt/Linux-ExHDD/backup-management-system/data/backup_mgmt.db"
      ]
    }
  }
}

【セキュリティ重要事項】
⚠️ トークンやAPIキーは環境変数で管理することを推奨
⚠️ 設定ファイルはGitにコミットしないこと
⚠️ 定期的にトークンをローテーションすること

================================================================================
5. 各MCPの詳細説明
================================================================================

5.1 Filesystem MCP
------------------

【機能】
- ファイルの読み込み・書き込み
- ディレクトリ作成・削除
- ファイル検索
- パーミッション管理

【対象パス】
/mnt/Linux-ExHDD/backup-management-system

【使用例】
- プロジェクト構造の作成
- ソースコード生成
- 設定ファイル編集
- ログファイル確認

【注意事項】
- 読み取り専用ディレクトリへの書き込み不可
- シンボリックリンクの扱いに注意

5.2 GitHub MCP
--------------

【機能】
- リポジトリ操作（clone, pull, push）
- ブランチ管理
- コミット作成
- Pull Request作成・管理
- Issue作成・管理
- レビュー機能

【必要な権限】
- repo（フルアクセス）
- workflow

【リポジトリ情報】
- URL: https://github.com/Kensan196948G/backup-management-system
- メインブランチ: main
- 開発ブランチ: develop

【使用例】
- 自動コミット・プッシュ
- Agent別のfeatureブランチ作成
- Issueによるタスク管理
- PRレビュー支援

【トークン管理】
1. 取得: https://github.com/settings/tokens
2. 権限: repo, workflow
3. 有効期限: 90日推奨
4. 定期ローテーション必須

5.3 SQLite MCP
--------------

【機能】
- スキーマ確認
- テーブル作成・変更
- データ挿入・更新・削除
- クエリ実行
- インデックス管理

【データベースパス】
/mnt/Linux-ExHDD/backup-management-system/data/backup_mgmt.db

【対象テーブル】
- users
- backup_jobs
- backup_copies
- offline_media
- verification_tests
- audit_logs
- alerts
- reports
（全14テーブル）

【使用例】
- マイグレーション実行
- データ確認
- 統計情報取得
- デバッグ用クエリ実行

【注意事項】
- 本番データへの直接操作は慎重に
- トランザクション管理を適切に
- バックアップを事前に取得

5.4 Brave Search MCP
---------------------

【機能】
- Web検索
- 技術情報検索
- APIドキュメント検索
- エラーメッセージ検索

【API Key取得】
1. https://brave.com/search/api/ にアクセス
2. アカウント作成（無料プラン可）
3. API Key取得
4. 月2000リクエストまで無料

【使用例】
- Flask最新情報検索
- SQLAlchemyエラー解決
- ベストプラクティス検索
- セキュリティ情報収集

【制限事項】
- 無料プラン: 2000リクエスト/月
- レート制限あり

5.5 Serena MCP (将来追加)
--------------------------

【機能】
- Webスクレイピング
- 構造化データ抽出
- ドキュメント収集
- コンテンツ分析

【リポジトリ】
https://github.com/oraios/serena

【本プロジェクトでの用途】
1. バックアップツールドキュメント収集
   - Veeam API仕様
   - Windows Server Backup技術情報
   - AOMEI Backupper機能一覧

2. 規格・標準情報収集
   - ISO 27001更新情報
   - ISO 19650ガイドライン
   - ベストプラクティス事例

3. 競合調査
   - 他社製品機能比較
   - UI/UX参考事例
   - 価格調査

【セットアップ】
npm install -g @oraios/serena-mcp

【設定追加】
"serena": {
  "command": "npx",
  "args": ["-y", "@oraios/serena-mcp"]
}

【注意事項】
- 対象サイトの利用規約確認
- robots.txt遵守
- レート制限設定
- 著作権・ライセンス確認

5.6 Context7 MCP (推奨)
-----------------------

【機能】
- プロジェクト全体のコンテキスト管理
- 長期記憶として設計書・要件定義保持
- セッション間での情報共有
- 進捗状況追跡

【本プロジェクトでの用途】
- 要件定義書の長期保持
- 設計仕様書の参照
- Agent間の情報共有
- 開発履歴追跡

【設定方法】
（詳細はContext7ドキュメント参照）

================================================================================
6. セットアップ手順
================================================================================

6.1 前提条件
------------

【必要なソフトウェア】
- Node.js 18以上
- npm 9以上
- Git 2.30以上
- Claude Desktop最新版

【確認コマンド】
node --version   # v18.x.x以上
npm --version    # 9.x.x以上
git --version    # 2.30.x以上

6.2 MCP設定ファイル作成
------------------------

【ステップ1: ディレクトリ作成】
mkdir -p ~/.config/Claude

【ステップ2: 設定ファイル作成】
nano ~/.config/Claude/claude_desktop_config.json

【ステップ3: 内容を貼り付け】
（上記の「4. MCP設定ファイル」の内容をコピー）

【ステップ4: トークン設定】
1. GitHub Personal Access Token取得
   https://github.com/settings/tokens
   
2. 必要な権限:
   - repo (フルアクセス)
   - workflow
   
3. トークンを設定ファイルに貼り付け
   "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxx..."

4. （オプション）Brave API Key取得
   https://brave.com/search/api/
   
5. API Keyを設定ファイルに貼り付け
   "BRAVE_API_KEY": "xxxx..."

【ステップ5: 設定ファイル検証】
python3 -m json.tool ~/.config/Claude/claude_desktop_config.json

エラーが出なければOK

【ステップ6: ファイル権限設定】
chmod 600 ~/.config/Claude/claude_desktop_config.json

（機密情報を含むため、所有者のみ読み書き可能に）

6.3 Claude Desktop再起動
-------------------------

【方法1: プロセスを終了して再起動】
pkill -f "Claude"
# その後、アプリケーションメニューからClaude Desktopを起動

【方法2: コマンドラインから起動】
nohup claude-desktop &

6.4 動作確認
------------

Claude Desktop再起動後、新しい会話で以下をテスト:

【テスト1: MCP接続確認】
プロンプト:
「利用可能なMCPサーバーのリストを表示してください」

期待結果:
- filesystem
- github
- sqlite
- brave-search
が表示される

【テスト2: Filesystem MCP】
プロンプト:
「/mnt/Linux-ExHDD/backup-management-system/docs/ の
ファイル一覧を表示してください」

期待結果:
- 要件定義書_3-2-1-1-0バックアップ管理システム.txt
- 設計仕様書_3-2-1-1-0バックアップ管理システム.txt
が表示される

【テスト3: GitHub MCP】
プロンプト:
「GitHubリポジトリ Kensan196948G/backup-management-system の
ブランチ一覧を表示してください」

期待結果:
- main
- develop
が表示される

【テスト4: SQLite MCP（DB作成後）】
プロンプト:
「backup_mgmt.db のテーブル一覧を表示してください」

期待結果:
データベース作成後に実行

6.5 トラブルシューティング
--------------------------

【問題: MCPサーバーが起動しない】

原因1: Node.jsバージョンが古い
→ Node.js 18以上にアップデート

原因2: npxコマンドが見つからない
→ npm install -g npx

原因3: ネットワークエラー
→ プロキシ設定確認
→ npm config set proxy http://proxy.example.com:8080

【問題: GitHub MCPでエラー】

原因1: トークンが無効
→ https://github.com/settings/tokens で確認
→ 新しいトークンを生成

原因2: 権限不足
→ トークンにrepo権限を追加

原因3: レート制限
→ 5分後に再試行

【問題: SQLite MCPでエラー】

原因1: DBファイルが存在しない
→ data/ディレクトリを作成
→ flask db upgrade でDB初期化

原因2: パス指定ミス
→ 絶対パスで指定
→ /mnt/Linux-ExHDD/backup-management-system/data/backup_mgmt.db

【問題: 設定ファイルのJSON形式エラー】

確認コマンド:
python3 -m json.tool ~/.config/Claude/claude_desktop_config.json

エラー箇所を修正:
- カンマの過不足
- 括弧の閉じ忘れ
- ダブルクォートの欠落

================================================================================
7. Agent機能構成
================================================================================

7.1 Agent構成（10体）
----------------------

【Agent 1: プロジェクトマネージャー】
役割:
  - 全体統括
  - タスク分解・割り当て
  - 進捗管理
  - ドキュメント更新
  - 他Agentへの指示

担当ファイル:
  - README.md
  - docs/開発進捗.md
  - GitHub Issues管理

【Agent 2: データベースアーキテクト】
役割:
  - app/models.py実装
  - マイグレーションスクリプト作成
  - SQLiteスキーマ設計
  - インデックス最適化

担当ファイル:
  - app/models.py
  - migrations/versions/*
  - scripts/init_db.py

【Agent 3: バックエンドAPI開発者】
役割:
  - REST API実装
  - エンドポイント設計
  - リクエスト/レスポンス処理
  - エラーハンドリング

担当ファイル:
  - app/api/__init__.py
  - app/api/backup.py
  - app/api/jobs.py
  - app/api/reports.py

【Agent 4: フロントエンド開発者】
役割:
  - テンプレート実装
  - CSS/JavaScript作成
  - ダッシュボードUI
  - レスポンシブデザイン

担当ファイル:
  - app/templates/*
  - app/static/css/*
  - app/static/js/*

【Agent 5: 認証・セキュリティエンジニア】
役割:
  - Flask-Login統合
  - 権限管理（RBAC）
  - パスワードハッシュ化
  - セッション管理

担当ファイル:
  - app/auth/__init__.py
  - app/auth/decorators.py
  - app/models.py (Userモデル)

【Agent 6: ビジネスロジック開発者】
役割:
  - 3-2-1-1-0チェックロジック
  - アラート生成
  - コンプライアンスチェック
  - レポート生成

担当ファイル:
  - app/services/compliance_checker.py
  - app/services/alert_manager.py
  - app/services/report_generator.py

【Agent 7: スケジューラー・通知開発者】
役割:
  - APScheduler設定
  - メール送信機能
  - Teams通知機能
  - 定期タスク管理

担当ファイル:
  - app/scheduler/tasks.py
  - app/utils/email.py
  - app/utils/notifications.py

【Agent 8: PowerShell統合エンジニア】
役割:
  - PowerShellスクリプト作成
  - Windows環境連携
  - API呼び出しスクリプト
  - デプロイスクリプト

担当ファイル:
  - deployment/windows/*.ps1
  - scripts/windows/*

【Agent 9: テストエンジニア】
役割:
  - 単体テスト作成
  - 統合テスト作成
  - カバレッジ測定
  - テスト自動化

担当ファイル:
  - tests/test_models.py
  - tests/test_api.py
  - tests/test_services.py

【Agent 10: DevOps/デプロイエンジニア】
役割:
  - デプロイスクリプト作成
  - CI/CD設定
  - 環境構築自動化
  - 監視設定

担当ファイル:
  - deployment/linux/*.sh
  - deployment/windows/*.ps1
  - .github/workflows/*

7.2 Agent間連携フロー
----------------------

【開発フロー】

1. Agent 1 (PM) がタスク分解
   ↓
2. 各Agentに担当タスク割り当て
   ↓
3. Hooks並列実行
   ├─ Agent 2: DB実装
   ├─ Agent 3: API実装
   ├─ Agent 4: UI実装
   ├─ Agent 5: 認証実装
   ├─ Agent 6: ロジック実装
   ├─ Agent 7: 通知実装
   ├─ Agent 8: PowerShell実装
   ├─ Agent 9: テスト実装
   └─ Agent 10: デプロイ準備
   ↓
4. GitHub MCP経由で統合
   ↓
5. Agent 9 がテスト実行
   ↓
6. Agent 1 がレビュー・マージ

【Git戦略】

main ブランチ (本番)
  ↑
develop ブランチ (統合)
  ↑
  ├─ feature/database (Agent 2)
  ├─ feature/api (Agent 3)
  ├─ feature/ui (Agent 4)
  ├─ feature/auth (Agent 5)
  ├─ feature/logic (Agent 6)
  ├─ feature/notification (Agent 7)
  ├─ feature/powershell (Agent 8)
  ├─ feature/tests (Agent 9)
  └─ feature/deployment (Agent 10)

7.3 並列開発の実現方法
----------------------

【Hooksによる並列実行】

方法1: Git Hooks
  - pre-commit: コード品質チェック
  - pre-push: テスト実行
  - post-merge: 依存関係更新

方法2: GitHub Actions
  - PR作成時に自動テスト
  - develop マージ時に統合テスト
  - main マージ時にデプロイ

方法3: 手動並列開発
  - 各Agent担当者が独立して開発
  - 定期的にdevelopにマージ
  - コンフリクト解消

【推奨ツール】
- GitHub Projects: タスク管理
- GitHub Issues: 課題追跡
- Pull Requests: コードレビュー
- GitHub Actions: CI/CD

================================================================================
8. セキュリティ要件
================================================================================

8.1 トークン管理
----------------

【GitHub Personal Access Token】

⚠️ 重要事項:
1. トークンは機密情報として扱う
2. Gitにコミットしない
3. 定期的にローテーション（90日推奨）
4. 最小権限の原則
5. 使用後は無効化

【推奨管理方法】

方法1: 環境変数
~/.bashrc または ~/.zshrc に追加:
export GITHUB_TOKEN="ghp_xxxx..."

設定ファイルでは:
"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"

方法2: .envファイル
プロジェクトルートに.env作成:
GITHUB_TOKEN=ghp_xxxx...

.gitignoreに追加:
.env

方法3: キーチェーン（macOS/Linux）
pass, gnome-keyring等のツール使用

【トークン権限設定】
最小限の権限:
  ✓ repo (必須)
  ✓ workflow (CI/CD使用時)
  
不要な権限:
  × admin:org
  × delete_repo
  × admin:gpg_key

【トークンローテーション手順】
1. https://github.com/settings/tokens にアクセス
2. 古いトークンを削除
3. 新しいトークンを生成（同じ権限）
4. 設定ファイルを更新
5. Claude Desktop再起動
6. 動作確認

8.2 Brave API Key管理
----------------------

【保護対象】
BRAVE_API_KEY

【推奨管理方法】
GitHub Tokenと同様、環境変数または.envファイル

【制限事項】
- 無料プラン: 2000リクエスト/月
- APIキーの共有禁止
- レート制限監視

8.3 設定ファイルのセキュリティ
------------------------------

【ファイル権限】
chmod 600 ~/.config/Claude/claude_desktop_config.json

所有者のみ読み書き可能（600）
- Owner: read + write
- Group: none
- Others: none

【バックアップ】
cp ~/.config/Claude/claude_desktop_config.json \
   ~/.config/Claude/claude_desktop_config.json.backup

【バージョン管理】
設定ファイルはGitに含めない
.gitignoreに追加:
.config/
*.json

テンプレートのみ管理:
claude_desktop_config.json.example

8.4 監査・ログ
--------------

【MCP操作ログ】
Claude Desktopのログを定期確認:
~/.config/Claude/logs/

【GitHub操作履歴】
https://github.com/Kensan196948G/backup-management-system/settings/audit-log

【セキュリティアラート】
GitHub Security Alerts有効化:
Settings → Security & analysis → Dependabot alerts

================================================================================
9. 動作確認手順
================================================================================

9.1 基本動作確認
----------------

【確認1: MCP接続テスト】

Claude Desktopで新しい会話を開始:

プロンプト:
```
MCPサーバーの接続状態を確認してください。
以下が利用可能か教えてください:
- filesystem
- github
- sqlite
- brave-search
```

期待結果:
各MCPサーバーが"利用可能"と表示される

【確認2: Filesystemアクセス】

プロンプト:
```
/mnt/Linux-ExHDD/backup-management-system/
ディレクトリの構造を表示してください
```

期待結果:
- docs/
- .git/
- README.md
- .gitignore
等が表示される

【確認3: GitHub連携】

プロンプト:
```
GitHubリポジトリ Kensan196948G/backup-management-system
の情報を取得してください:
- リポジトリの説明
- ブランチ一覧
- 最新コミット
```

期待結果:
- main, developブランチが表示
- 最新コミット情報が表示

【確認4: SQLite接続（DB作成後）】

プロンプト:
```
/mnt/Linux-ExHDD/backup-management-system/data/backup_mgmt.db
のテーブル一覧を表示してください
```

期待結果:
14テーブルが表示される（DB作成後）

9.2 統合動作確認
----------------

【シナリオ1: ファイル作成→Git操作】

1. 新しいファイルを作成
   プロンプト:
   「test.txtファイルを作成し、"Hello MCP"と書き込んでください」

2. Gitステータス確認
   プロンプト:
   「Gitステータスを確認してください」

3. コミット
   プロンプト:
   「test.txtをコミットしてください（メッセージ: Test MCP integration）」

4. プッシュ
   プロンプト:
   「developブランチにプッシュしてください」

5. GitHub上で確認
   https://github.com/Kensan196948G/backup-management-system/blob/develop/test.txt

【シナリオ2: データベース操作】

（DB作成後に実施）

1. テーブル作成確認
   プロンプト:
   「usersテーブルのスキーマを表示してください」

2. データ挿入
   プロンプト:
   「usersテーブルにテストユーザーを1件追加してください」

3. データ確認
   プロンプト:
   「usersテーブルの全データを表示してください」

【シナリオ3: Web検索→ドキュメント作成】

1. 技術情報検索
   プロンプト:
   「Flask 3.0の新機能について検索してください」

2. ドキュメント作成
   プロンプト:
   「検索結果をもとに、docs/flask3-features.mdを作成してください」

3. Git操作
   プロンプト:
   「作成したドキュメントをコミット・プッシュしてください」

9.3 パフォーマンス確認
----------------------

【応答時間測定】

測定項目:
- Filesystem操作: < 1秒
- GitHub操作: < 3秒
- SQLite操作: < 2秒
- Web検索: < 5秒

測定方法:
各操作の実行時刻を記録

【リソース使用量】

確認コマンド:
top -p $(pgrep -f "Claude")

監視項目:
- CPU使用率
- メモリ使用量
- ネットワークI/O

9.4 エラーハンドリング確認
--------------------------

【意図的なエラー発生】

テスト1: 存在しないファイルアクセス
プロンプト:
「/non/existent/file.txtを読み込んでください」

期待動作:
適切なエラーメッセージが表示される

テスト2: GitHub権限エラー
（別のリポジトリで試す）
プロンプト:
「他人のプライベートリポジトリにアクセスしてください」

期待動作:
権限エラーが表示される

テスト3: SQLite不正クエリ
プロンプト:
「存在しないテーブルからSELECTしてください」

期待動作:
SQLエラーが表示される

================================================================================
10. トラブルシューティング
================================================================================

10.1 一般的な問題
-----------------

【問題: MCPサーバーが見つからない】

症状:
「MCPサーバーが利用できません」というエラー

原因と対処:

1. Node.jsバージョン確認
   node --version
   → 18.x.x未満なら更新

2. npm確認
   npm --version
   → インストールされているか確認

3. npxコマンド確認
   which npx
   → パスが通っているか確認

4. Claude Desktop再起動
   pkill -f "Claude"
   # 再起動

5. 設定ファイル確認
   cat ~/.config/Claude/claude_desktop_config.json
   → JSON形式が正しいか確認

【問題: GitHub MCP接続エラー】

症状:
「GitHub APIに接続できません」

原因と対処:

1. トークン確認
   https://github.com/settings/tokens
   → トークンが有効か確認

2. 権限確認
   → repo権限があるか確認

3. レート制限確認
   curl -H "Authorization: token ghp_xxxx..." \
        https://api.github.com/rate_limit
   → 残りリクエスト数確認

4. ネットワーク確認
   ping github.com
   → 接続可能か確認

5. プロキシ設定（必要な場合）
   export https_proxy=http://proxy.example.com:8080

【問題: SQLite MCP接続エラー】

症状:
「データベースに接続できません」

原因と対処:

1. DBファイル存在確認
   ls -la /mnt/Linux-ExHDD/backup-management-system/data/backup_mgmt.db
   → ファイルが存在するか確認

2. パーミッション確認
   ls -la /mnt/Linux-ExHDD/backup-management-system/data/
   → 読み書き権限があるか確認

3. ディレクトリ作成
   mkdir -p /mnt/Linux-ExHDD/backup-management-system/data

4. DB初期化（まだDBが無い場合）
   cd /mnt/Linux-ExHDD/backup-management-system
   flask db upgrade

【問題: Brave Search API エラー】

症状:
「API Keyが無効です」

原因と対処:

1. API Key確認
   → 正しいキーが設定されているか

2. クォータ確認
   https://brave.com/search/api/dashboard
   → 残りリクエスト数確認

3. APIキー再生成
   → 新しいキーを取得して設定更新

10.2 パフォーマンス問題
-----------------------

【問題: 応答が遅い】

症状:
MCPサーバーの応答に10秒以上かかる

原因と対処:

1. ネットワーク速度確認
   speedtest-cli
   → ダウンロード/アップロード速度確認

2. ディスクI/O確認
   iostat -x 1
   → ディスク待機時間確認

3. メモリ確認
   free -h
   → 空きメモリ確認

4. プロセス確認
   ps aux | grep node
   → MCPサーバープロセスのリソース使用状況

5. ログ確認
   ~/.config/Claude/logs/
   → エラーログ確認

【問題: メモリ不足】

症状:
Claude Desktopが遅い、または落ちる

原因と対処:

1. メモリ使用量確認
   top -o %MEM
   → メモリを多く使用しているプロセス確認

2. 不要なプロセス終了
   → 他のアプリケーションを閉じる

3. スワップ確認
   swapon --show
   → スワップが使用されているか

4. システムリソース増強
   → RAM増設検討

10.3 セキュリティ関連問題
-------------------------

【問題: トークンが漏洩した可能性】

対処手順:

1. 即座にトークン無効化
   https://github.com/settings/tokens
   → 該当トークンを削除

2. 新しいトークン生成
   → 最小権限で新規作成

3. 設定ファイル更新
   nano ~/.config/Claude/claude_desktop_config.json
   → 新しいトークンに更新

4. 監査ログ確認
   https://github.com/Kensan196948G/backup-management-system/settings/audit-log
   → 不正なアクセスがないか確認

5. パスワード変更（念のため）
   https://github.com/settings/security
   → GitHubパスワード変更

6. 2FA有効化
   https://github.com/settings/security
   → 2段階認証を有効化

【問題: 設定ファイルがGitにコミットされた】

対処手順:

1. コミット履歴から削除
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch \
      ~/.config/Claude/claude_desktop_config.json" \
     --prune-empty --tag-name-filter cat -- --all

2. リモートに強制プッシュ
   git push origin --force --all

3. トークン無効化・再生成
   （上記手順参照）

4. .gitignore に追加
   echo ".config/" >> .gitignore
   git add .gitignore
   git commit -m "Add .config/ to .gitignore"

10.4 開発環境問題
-----------------

【問題: VSCode統合が動作しない】

症状:
VSCodeでMCP機能が使えない

原因と対処:

1. VSCode拡張機能確認
   → Claude拡張機能がインストールされているか

2. 設定同期確認
   → VSCodeとClaude Desktop間の連携設定

3. ワークスペース設定
   .vscode/settings.json
   → プロジェクト固有の設定確認

【問題: Linux開発とWindows本番の差異】

症状:
Linuxで動作するがWindowsで動作しない

原因と対処:

1. パス区切り文字
   → pathlib使用を徹底

2. 改行コード
   git config core.autocrlf true
   → 自動変換有効化

3. ファイルパーミッション
   → Windows側で適切に設定

4. 環境変数
   → .env.exampleを両環境で用意

10.5 サポート・問い合わせ
-------------------------

【Claude Desktop関連】
- 公式ドキュメント: https://docs.claude.ai/
- サポート: https://support.anthropic.com/

【MCP関連】
- MCP仕様: https://modelcontextprotocol.io/
- GitHub: https://github.com/modelcontextprotocol

【GitHub関連】
- ヘルプ: https://docs.github.com/
- サポート: https://support.github.com/

【プロジェクト固有】
- Issues: https://github.com/Kensan196948G/backup-management-system/issues
- Discussions: https://github.com/Kensan196948G/backup-management-system/discussions

================================================================================
付録A: コマンドリファレンス
================================================================================

【設定ファイル編集】
nano ~/.config/Claude/claude_desktop_config.json
code ~/.config/Claude/claude_desktop_config.json

【設定ファイル確認】
cat ~/.config/Claude/claude_desktop_config.json
python3 -m json.tool ~/.config/Claude/claude_desktop_config.json

【パーミッション設定】
chmod 600 ~/.config/Claude/claude_desktop_config.json

【Claude Desktop操作】
pkill -f "Claude"                  # プロセス終了
nohup claude-desktop &             # バックグラウンド起動

【環境変数設定】
export GITHUB_TOKEN="ghp_xxxx..."
export BRAVE_API_KEY="xxxx..."

【Git操作】
git status                         # ステータス確認
git branch                         # ブランチ一覧
git checkout develop               # ブランチ切り替え
git add .                          # 全ファイル追加
git commit -m "message"            # コミット
git push origin develop            # プッシュ

【データベース操作】
sqlite3 data/backup_mgmt.db        # SQLiteコンソール起動
.tables                            # テーブル一覧
.schema users                      # スキーマ表示

【システム確認】
node --version                     # Node.jsバージョン
npm --version                      # npmバージョン
git --version                      # Gitバージョン
python3 --version                  # Pythonバージョン

================================================================================
付録B: チェックリスト
================================================================================

【初期セットアップチェックリスト】

□ Node.js 18以上インストール済み
□ npm 9以上インストール済み
□ Git 2.30以上インストール済み
□ Claude Desktop最新版インストール済み
□ 設定ディレクトリ作成済み (~/.config/Claude/)
□ MCP設定ファイル作成済み
□ GitHub Personal Access Token取得済み
□ トークン権限設定済み (repo, workflow)
□ Brave API Key取得済み（オプション）
□ 設定ファイルにトークン設定済み
□ 設定ファイルのJSON形式確認済み
□ ファイルパーミッション設定済み (600)
□ Claude Desktop再起動済み
□ MCP接続確認済み
□ Filesystem MCP動作確認済み
□ GitHub MCP動作確認済み
□ SQLite MCP動作確認済み（DB作成後）
□ Brave Search MCP動作確認済み（設定した場合）

【セキュリティチェックリスト】

□ トークンを環境変数で管理している
□ 設定ファイルをGitに含めていない
□ .gitignoreに.config/追加済み
□ ファイルパーミッションが600
□ トークンの有効期限設定済み（90日推奨）
□ 最小権限の原則適用済み
□ 2FA有効化済み（推奨）
□ 監査ログを定期確認する仕組みがある
□ トークンローテーション計画がある

【開発環境チェックリスト】

□ プロジェクトディレクトリ作成済み
□ Gitリポジトリ初期化済み
□ GitHub リモートリポジトリ接続済み
□ main, develop ブランチ作成済み
□ docs/に要件定義書・設計仕様書配置済み
□ VSCodeでプロジェクトを開ける
□ .gitignore設定済み
□ .env.example作成済み
□ requirements.txt作成済み
□ 仮想環境作成済み（venv/）

================================================================================
改訂履歴
================================================================================

版番号  日付         改訂内容                           承認者
------  -----------  ---------------------------------  --------------------
1.0     2025/10/30   初版作成                           [承認者名]


================================================================================
以上
================================================================================
