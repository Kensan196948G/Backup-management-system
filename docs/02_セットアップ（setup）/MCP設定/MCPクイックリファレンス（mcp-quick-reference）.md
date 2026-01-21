# MCP クイックリファレンス
# 3-2-1-1-0 バックアップ管理システム

## 🚀 すぐに使えるMCP（3個）

### 1. Context7 - ドキュメント取得 ✅

```
Context7を使用して、Flaskの最新ドキュメントを取得してください
Context7でSQLAlchemyのクエリ構文を調べてください
Context7を使用して、Bootstrap 5のグリッドシステムを確認してください
```

**用途:**
- Pythonライブラリの公式ドキュメント
- フレームワークのAPIリファレンス
- ベストプラクティスの確認

---

### 2. Chrome DevTools - ブラウザ制御 ✅

```
Chrome DevToolsを使用して、localhost:5000のページを開いてください
Chrome DevToolsでDOMの構造を確認してください
Chrome DevToolsを使用して、スクリーンショットを取得してください
```

**用途:**
- フロントエンドのデバッグ
- UI/UXの検証
- パフォーマンス測定

---

### 3. Brave Search - Web検索 ✅ **NEW!**

```
Brave Searchを使用して、Pythonバックアップのベストプラクティスを検索してください
Brave SearchでFlask 3.0の新機能を検索してください
Brave Searchを使用して、最新のセキュリティ情報を確認してください
```

**用途:**
- 最新技術情報の検索
- エラーメッセージの解決方法
- セキュリティ情報の確認

---

## ⚠️ トラブルシューティング中（2個）

### Serena MCP Server ⚠️

**状態**: 接続失敗（調査中）

**期待される機能（22ツール）:**
- プロジェクト構造の分析
- シンボル検索（クラス、関数）
- 依存関係の可視化
- コードメトリクス

**代替手段:**
```
# ファイル検索
すべての.pyファイルを検索してください

# コンテンツ検索
"backup_job"という関数を探してください

# 依存関係確認
すべてのimport文を検索してください
```

---

### GitHub MCP ⚠️

**状態**: 接続失敗（調査中）

**期待される機能:**
- リポジトリ管理
- Issue管理
- Pull Request操作

**代替手段:**
```bash
# カスタムコマンドを使用
/commit          # コミット＋プッシュ
/pr              # PR作成
/commit-and-pr   # 一括実行

# GitHub CLI（gh）を使用
gh issue list
gh pr list
gh repo view
```

---

## 📋 MCPステータス確認

```bash
# MCP接続状況の確認
/mcp

# または
claude mcp list
```

**期待される出力:**
```
✅ context7        - Connected
⚠️ serena          - Failed to connect
✅ chrome-devtools - Connected
✅ brave-search    - Connected
⚠️ github          - Failed to connect
```

---

## 🛠️ Claude Code標準ツール（MCP不要）

### ファイル操作

```
# 読み込み
app.pyを読んでください

# 作成
新しいPythonファイルを作成してください

# 編集
5行目を修正してください

# 検索
すべての.pyファイルを検索してください
```

### コード検索

```
# パターン検索
"Flask"を含むファイルを検索してください

# 関数検索
def backupという関数を探してください
```

### Git操作

```
# 状態確認
git statusを実行してください

# カスタムコマンド
/commit          # コミット＋プッシュ
/pr              # PR作成
/commit-and-pr   # 一括実行
```

---

## 💡 開発ワークフロー例

### パターン1: 新機能の実装

```
1. Context7でドキュメント確認
   └─ "Context7を使用して、Flaskのファイルアップロードについて調べてください"

2. Brave Searchで最新情報確認
   └─ "Brave Searchで、Flask 3.0のファイルアップロード例を検索してください"

3. Write/Editで実装
   └─ "app.pyに新しいルートを追加してください"

4. pytestでテスト
   └─ "pytestを実行してください"

5. /commit-and-pr
   └─ "変更をコミットしてPRを作成してください"
```

---

### パターン2: エラー修正

```
1. エラー箇所の特定
   └─ "エラーが発生しているコードを読んでください"

2. Brave Searchで解決方法検索
   └─ "Brave Searchで'IntegrityError SQLAlchemy'を検索してください"

3. Context7で正しい使い方確認
   └─ "Context7でSQLAlchemyのユニーク制約について調べてください"

4. 修正実装
   └─ "5行目を修正してください"

5. /commit
   └─ "修正をコミットしてプッシュしてください"
```

---

### パターン3: フロントエンド開発

```
1. Context7でドキュメント確認
   └─ "Context7を使用して、Bootstrap 5のモーダルについて調べてください"

2. HTML/CSS実装
   └─ "templates/index.htmlを編集してください"

3. Chrome DevToolsで確認
   └─ "Chrome DevToolsでlocalhost:5000を開いてください"

4. スクリーンショット取得
   └─ "Chrome DevToolsでスクリーンショットを取得してください"

5. /commit-and-pr
   └─ "変更をコミットしてPRを作成してください"
```

---

## 🔧 MCP設定ファイル

### プロジェクトローカル設定

**場所**: `.claude/mcp_settings.json`

**現在の設定:**
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp"]
    },
    "serena-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/oraios/serena",
        "serena-mcp-server",
        "--context",
        "ide-assistant",
        "--project",
        "/mnt/Linux-ExHDD/backup-management-system"
      ]
    },
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "@executeautomation/chrome-devtools-mcp"]
    }
  }
}
```

### グローバル設定

**場所**: `~/.claude.json`

**追加されたMCP:**
- brave-search（✅ 接続成功）
- github（⚠️ 接続失敗）

---

## 📚 環境変数

**場所**: `.env`

```bash
# GitHub
GITHUB_TOKEN=your_github_token_here
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here

# Brave Search
BRAVE_API_KEY=BSAg8mI-C1724Gro5K1UHthSdPNurDT
```

**注意**: `.gitignore`で除外されています

---

## 🎯 次にすべきこと

### 1. VSCodeの完全再起動 🔴

```
1. VSCodeを完全に終了（Ctrl+Q）
2. VSCodeを再起動
3. プロジェクトを開く
4. `/mcp`で接続確認
```

### 2. MCP機能のテスト 🟡

```
# Context7
Context7を使用して、Flaskのドキュメントを取得してください

# Chrome DevTools
Chrome DevToolsを使用して、localhost:5000を開いてください

# Brave Search
Brave Searchで最新のPythonバックアップツールを検索してください
```

### 3. 失敗しているMCPの修正 🟢

- Serena: デバッグログの取得
- GitHub: Docker環境変数の修正

---

## 🆘 困ったときは

### MCP接続の問題

```bash
# MCP接続状況の確認
claude mcp list

# 特定のMCPを削除
claude mcp remove <mcp-name>

# MCPを再追加
claude mcp add <mcp-name> ...
```

### エラーログの確認

```bash
# VSCodeのログ
Ctrl+Shift+P → "Developer: Show Logs"

# Claude Codeのログ
Ctrl+Shift+P → "Claude Code: Show Logs"
```

### 設定ファイルの確認

```bash
# プロジェクトローカル設定
cat .claude/mcp_settings.json

# グローバル設定（大きすぎる場合はclaude mcp listを使用）
claude mcp list
```

---

## 📊 機能一覧

| カテゴリ | 機能名 | 状態 | 用途 |
|---------|--------|------|------|
| **MCP** | Context7 | ✅ | ドキュメント取得 |
| **MCP** | Chrome DevTools | ✅ | ブラウザ制御 |
| **MCP** | Brave Search | ✅ | Web検索 |
| **MCP** | Serena | ⚠️ | コード解析 |
| **MCP** | GitHub | ⚠️ | リポジトリ管理 |
| **標準** | Read | ✅ | ファイル読み込み |
| **標準** | Write | ✅ | ファイル作成 |
| **標準** | Edit | ✅ | ファイル編集 |
| **標準** | Glob | ✅ | ファイル検索 |
| **標準** | Grep | ✅ | コンテンツ検索 |
| **標準** | Bash | ✅ | コマンド実行 |
| **標準** | WebSearch | ✅ | Web検索 |
| **標準** | WebFetch | ✅ | ページ取得 |
| **カスタム** | /commit | ✅ | コミット・プッシュ |
| **カスタム** | /pr | ✅ | PR作成 |
| **カスタム** | /commit-and-pr | ✅ | 一括実行 |

**合計**: 16の機能（利用可能: 14個、調査中: 2個）

---

## ✅ まとめ

**利用可能:**
- 3つのMCPが正常動作
- 8つの標準ツール
- 3つのカスタムコマンド
- **合計14の機能**

**調査中:**
- Serena MCP（コード解析）
- GitHub MCP（リポジトリ管理）

**推奨事項:**
1. VSCodeを完全再起動
2. 動作しているMCPで開発を開始
3. 失敗しているMCPは後で修正

**次のステップ:**
1. `/mcp`で接続確認
2. 各MCPの機能をテスト
3. 開発ワークフローの確立

---

**作成日**: 2025年10月30日
**動作確認済みMCP**: 3個（Context7、Chrome DevTools、Brave Search）
**ステータス**: ✅ 開発可能な状態
