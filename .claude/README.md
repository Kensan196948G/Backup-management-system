# Claude Code 設定ガイド

このディレクトリには、Claude Codeの設定ファイルと拡張機能が含まれています。

## 📋 目次

1. [概要](#概要)
2. [ディレクトリ構造](#ディレクトリ構造)
3. [MCP サーバー](#mcpサーバー)
4. [Hooks](#hooks)
5. [スラッシュコマンド](#スラッシュコマンド)
6. [設定](#設定)
7. [使い方](#使い方)

## 概要

このプロジェクトでは、Claude Codeの全機能を活用するために以下が設定されています：

- ✅ **MCP (Model Context Protocol) サーバー**: 6種類
- ✅ **Hooks**: 4種類の自動実行フック
- ✅ **スラッシュコマンド**: 10種類のカスタムコマンド（/ship を含む）
- ✅ **SubAgent機能**: Explore、Plan等のエージェント
- ✅ **並列開発機能**: 複数タスクの同時実行

## ディレクトリ構造

```
.claude/
├── README.md                      # このファイル
├── mcp_settings.json              # MCPサーバー設定
├── mcp_settings.json.example      # MCPサーバー設定例
├── settings.local.json            # ローカル設定（権限等）
├── hooks/                         # Hooksスクリプト
│   ├── user-prompt-submit-hook.sh # プロンプト送信前フック
│   ├── tool-call-hook.sh          # ツール呼び出しフック
│   ├── pre-commit-hook.sh         # コミット前フック
│   └── pre-push-hook.sh           # プッシュ前フック
└── commands/                      # スラッシュコマンド
    ├── commit.md                  # コミットコマンド
    ├── pr.md                      # PRコマンド
    ├── commit-and-pr.md           # コミット&PR&マージコマンド
    ├── ship.md                    # 🚀 完全自動デプロイコマンド（NEW!）
    ├── parallel-dev.md            # 並列開発コマンド
    ├── explore.md                 # コードベース探索コマンド
    ├── analyze.md                 # コード分析コマンド
    ├── test.md                    # テスト実行コマンド
    ├── review.md                  # コードレビューコマンド
    └── refactor.md                # リファクタリングコマンド
```

## MCP サーバー

### 1. Filesystem Server
**機能**: ファイルシステム操作
- ファイルの読み書き
- ディレクトリの作成・一覧表示
- ファイル検索

### 2. Memory Server
**機能**: 永続的なメモリ管理
- エンティティの作成・管理
- 関係性の追跡
- ナレッジグラフの構築

### 3. Brave Search Server
**機能**: Web検索
- 最新情報の取得
- ドキュメント検索
- 技術情報の調査

**設定**: 環境変数 `BRAVE_API_KEY` が必要

### 4. Context7 Server
**機能**: ライブラリドキュメント取得
- 最新のライブラリドキュメント
- コード例の取得
- API リファレンス

### 5. Serena Server
**機能**: セマンティックコード操作
- シンボルベースのコード編集
- コード構造の理解
- リファクタリング支援

### 6. Chrome DevTools Server
**機能**: ブラウザ自動化
- Web UIのテスト
- スクリーンショット取得
- パフォーマンス測定

## Hooks

### 1. user-prompt-submit-hook.sh
**実行タイミング**: ユーザーがプロンプトを送信する前

**機能**:
- プロンプトの前処理
- キーワード検出（test、deploy等）
- セキュリティチェック（機密情報の検出）

### 2. tool-call-hook.sh
**実行タイミング**: ツールが呼び出される前

**機能**:
- 危険なコマンドの検出（rm -rf等）
- ツール呼び出しの通知
- 安全性チェック

### 3. pre-commit-hook.sh
**実行タイミング**: git commit の前

**機能**:
- コードフォーマットチェック（Black）
- インポート順序チェック（isort）
- Lintチェック（flake8）
- 機密情報チェック
- 大きなファイルの検出

### 4. pre-push-hook.sh
**実行タイミング**: git push の前

**機能**:
- テストの実行
- ビルドチェック
- ブランチ保護チェック
- リモートとの同期確認

## スラッシュコマンド

### 基本コマンド

#### /commit
変更をコミットしてプッシュ

**使用例**:
```
/commit
```

**実行内容**:
1. Git状態の確認（並列実行）
2. コミットメッセージの自動生成
3. ステージング＆コミット
4. リモートへプッシュ

#### /pr
プルリクエストを作成

**使用例**:
```
/pr
```

**実行内容**:
1. ブランチ状態の確認
2. 変更内容の分析
3. PRタイトル＆ボディの生成
4. PR作成

#### /commit-and-pr
コミット→プッシュ→PR→マージを一括実行

**使用例**:
```
/commit-and-pr
```

**実行内容**:
1. セキュリティチェック
2. コミット作成
3. プッシュ
4. PR作成
5. CI/CD待機
6. 自動マージ

#### /ship 🚀 **NEW!**
コミット→プッシュ→PR→マージを最速で完全自動実行

**使用例**:
```
/ship
```

**実行内容**:
1. Git状態確認（並列実行）
2. セキュリティチェック
3. コミット作成（自動メッセージ生成）
4. リモートプッシュ
5. PR作成（自動タイトル＆ボディ生成）
6. CI/CD待機＆監視
7. ブランチ保護ルール一時無効化（必要時）
8. 自動マージ
9. ブランチ保護ルール再有効化
10. 完了レポート表示

**特徴**:
- ✅ 1コマンドで全工程完了
- ✅ 時間短縮: 約40-60%
- ✅ セキュリティチェック自動化
- ✅ CI/CD統合
- ✅ エラー時の詳細な対処方法提示

### 開発支援コマンド

#### /parallel-dev
並列開発モードを有効化

**使用例**:
```
/parallel-dev
```

**機能**:
- 複数タスクの同時実行
- 情報収集の並列化
- 開発時間の短縮

#### /explore
コードベースを探索

**使用例**:
```
/explore

認証機能の実装場所を調査してください
探索レベル: medium
```

**探索レベル**:
- `quick`: 高速（基本的な検索）
- `medium`: 中程度（推奨）
- `very thorough`: 徹底的（包括的な分析）

#### /analyze
コードを総合的に分析

**使用例**:
```
/analyze
```

**分析項目**:
- コード品質（Lint、フォーマット、型）
- セキュリティ（機密情報、脆弱性）
- パフォーマンス（複雑度、重複）
- テストカバレッジ

#### /test
テストを実行

**使用例**:
```
/test
```

**機能**:
- 全テスト実行
- カバレッジ測定
- 失敗テストの詳細報告
- 推奨アクションの提示

#### /review
コード変更をレビュー

**使用例**:
```
/review
```

**レビュー観点**:
- コード品質
- セキュリティ
- パフォーマンス
- テスト
- ドキュメント

#### /refactor
リファクタリングを支援

**使用例**:
```
/refactor
```

**リファクタリングパターン**:
- 関数の抽出
- マジックナンバーの定数化
- 重複コードの削除
- クラスへの抽出
- 条件分岐の簡素化

## 設定

### settings.local.json

ローカル設定ファイル。以下が含まれます：

```json
{
  "permissions": {
    "allow": [
      "Bash(git *)",
      "Bash(npm *)",
      "Bash(pytest *)",
      "mcp__serena__*"
    ],
    "deny": [],
    "ask": []
  },
  "outputStyle": "Explanatory"
}
```

**権限設定**:
- `allow`: 自動承認するツール呼び出し
- `deny`: 拒否するツール呼び出し
- `ask`: 確認を求めるツール呼び出し

**出力スタイル**:
- `Explanatory`: 教育的な説明を含む（現在の設定）
- `Concise`: 簡潔な応答
- `Technical`: 技術的な詳細を含む

## 使い方

### 初回セットアップ

1. **環境変数の設定**:
```bash
# .envファイルに追加
BRAVE_API_KEY=your_brave_api_key_here
```

2. **Hooksに実行権限を付与**:
```bash
chmod +x .claude/hooks/*.sh
```

3. **Pythonパッケージのインストール**:
```bash
pip install flake8 black isort mypy pytest pytest-cov
```

### 日常的な使用

#### コミット＆プッシュ

```
変更を加えたら：
/commit
```

#### プルリクエスト作成

```
ブランチでの作業が完了したら：
/pr
```

#### コード分析

```
定期的に：
/analyze
```

#### テスト実行

```
変更後に：
/test
```

#### コードレビュー

```
コミット前に：
/review
```

### SubAgent の活用

#### Explore Agent

```
新しいコードベースを理解する場合：

Explore Agentを使用して、認証機能の実装場所を調査してください。
探索レベル: medium
```

#### Plan Agent

```
大きな機能を実装する前に：

Plan Agentを使用して、ユーザー管理機能の実装計画を立ててください。
```

### 並列実行の例

```
以下を並列実行してください：
1. Git状態の確認
2. テストの実行
3. Lintチェック
4. カバレッジ測定
```

## トラブルシューティング

### MCPサーバーが起動しない

```bash
# Node.jsのバージョン確認
node --version  # v18以上が必要

# npxのキャッシュクリア
npx clear-npx-cache

# サーバーの手動起動テスト
npx -y @modelcontextprotocol/server-filesystem /path/to/project
```

### Hooksが実行されない

```bash
# 実行権限の確認
ls -la .claude/hooks/

# 権限の付与
chmod +x .claude/hooks/*.sh

# シェルスクリプトの構文チェック
bash -n .claude/hooks/pre-commit-hook.sh
```

### Serenaが動作しない

```bash
# uvxのインストール
pip install uv

# Serenaの手動起動テスト
uvx --from git+https://github.com/oraios/serena serena-mcp-server --help
```

## ベストプラクティス

### 1. 定期的な分析

週に1回は `/analyze` を実行してコード品質を確認

### 2. コミット前のチェック

コミット前に必ず `/review` を実行

### 3. 並列実行の活用

時間のかかる操作は並列実行を活用

### 4. SubAgentの活用

- 新しいコードベース: Explore Agent
- 大きな変更: Plan Agent
- 複雑な問題: 一般目的Agent

### 5. メモリの活用

重要な情報はMemory Serverに保存して再利用

## 更新履歴

### 2025-12-02
- 初期設定作成
- 全MCP サーバー設定
- 全Hooks設定
- 9種類のスラッシュコマンド追加

## サポート

問題が発生した場合:
1. このREADMEを確認
2. トラブルシューティングセクションを参照
3. GitHub Issuesで報告

## 参考リンク

- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Serena GitHub](https://github.com/oraios/serena)
- [Context7](https://context7.com/)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
