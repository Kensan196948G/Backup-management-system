# Serena MCP 正しいセットアップガイド
# 3-2-1-1-0 バックアップ管理システム

## 🎯 正しいSerena MCPの設定方法

### 重要な発見

Serenaは **uvx** と **GitHub** から直接インストールする必要があります。
npmパッケージ（`@oraios/serena-mcp`）ではなく、GitHubリポジトリから取得します。

---

## ✅ 新しいMCP設定

### 完全な設定ファイル

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

---

## 🔧 Serena設定の詳細

### コマンド構造

```bash
uvx --from git+https://github.com/oraios/serena serena-mcp-server \
  --context ide-assistant \
  --project /mnt/Linux-ExHDD/backup-management-system
```

**各パラメータの説明:**

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| `command` | `uvx` | Python実行ツール（uv経由） |
| `--from` | `git+https://github.com/oraios/serena` | GitHubから直接取得 |
| `serena-mcp-server` | - | 実行するパッケージ名 |
| `--context` | `ide-assistant` | IDE向けモード（22個のツール） |
| `--project` | プロジェクトパス | 分析対象のプロジェクト |

---

## 📊 Serenaのコンテキストモード

### 3つのコンテキスト

#### 1. desktop-app（デフォルト）
```bash
uvx --from git+https://github.com/oraios/serena serena-mcp-server \
  --context desktop-app
```
**用途:** Claude Desktopアプリ向け

#### 2. ide-assistant（推奨）✅
```bash
uvx --from git+https://github.com/oraios/serena serena-mcp-server \
  --context ide-assistant \
  --project $(pwd)
```
**用途:** IDE（VSCode + Claude Code）向け
**ツール数:** 22個
**特徴:** プロジェクト固有の分析

#### 3. agent
```bash
uvx --from git+https://github.com/oraios/serena serena-mcp-server \
  --context agent
```
**用途:** Angoなどのエージェントフレームワーク向け

---

## 🛠️ ide-assistantで利用可能な22個のツール

### カテゴリ別ツール

#### プロジェクト分析
1. `analyze_project_structure` - プロジェクト構造の分析
2. `get_project_summary` - プロジェクトサマリー取得
3. `analyze_dependencies` - 依存関係の分析
4. `find_circular_dependencies` - 循環依存の検出

#### コード検索
5. `search_code` - コード全体を検索
6. `find_symbol` - シンボル（クラス、関数）検索
7. `find_references` - 参照箇所の検索
8. `find_definition` - 定義箇所の検索

#### ファイル操作
9. `list_files` - ファイル一覧取得
10. `read_file` - ファイル読み込み
11. `get_file_info` - ファイル情報取得
12. `compare_files` - ファイル比較

#### コード分析
13. `analyze_function` - 関数分析
14. `analyze_class` - クラス分析
15. `get_call_hierarchy` - 呼び出し階層
16. `find_unused_code` - 未使用コード検出

#### リファクタリング支援
17. `suggest_refactoring` - リファクタリング提案
18. `extract_method` - メソッド抽出提案
19. `rename_symbol` - シンボル名変更

#### ドキュメント
20. `generate_documentation` - ドキュメント生成
21. `explain_code` - コード説明
22. `get_code_metrics` - コードメトリクス

---

## 🚀 使用例

### プロジェクト構造の分析

```
Serenaを使用して、このプロジェクトの構造を分析してください
```

**実行される処理:**
- プロジェクトディレクトリのスキャン
- ファイル構造の把握
- 依存関係の分析

### 関数の検索

```
Serenaで"backup_job"という名前の関数を検索してください
```

**実行される処理:**
- シンボル検索
- 定義箇所の特定
- 使用箇所の一覧

### 循環依存の検出

```
Serenaを使用して、循環依存がないか確認してください
```

**実行される処理:**
- インポート関係の分析
- 循環参照の検出
- 問題箇所の報告

### 未使用コードの検出

```
Serenaで未使用の関数やクラスを検出してください
```

**実行される処理:**
- 定義されているシンボルの一覧
- 参照箇所のチェック
- 未使用コードのリスト化

---

## 📋 前提条件

### 必要なソフトウェア

1. **uv（uvx）**
   ```bash
   # インストール確認
   uvx --version

   # インストール（未インストールの場合）
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Git**
   ```bash
   git --version
   ```

3. **Python 3.8+**
   ```bash
   python3 --version
   ```

---

## 🔍 トラブルシューティング

### 問題1: uvxが見つからない

**症状:** `uvx: command not found`

**解決策:**
```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# パスを追加（必要に応じて）
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 確認
uvx --version
```

### 問題2: Serenaがfailedになる

**症状:** `/mcp`で`serena-mcp-server: failed`

**解決策:**

1. **手動でインストールを試す:**
   ```bash
   cd /mnt/Linux-ExHDD/backup-management-system
   uvx --from git+https://github.com/oraios/serena serena-mcp-server --help
   ```

2. **プロジェクトパスを確認:**
   ```bash
   pwd
   # /mnt/Linux-ExHDD/backup-management-system
   ```

3. **uvxのキャッシュをクリア:**
   ```bash
   rm -rf ~/.cache/uv
   ```

4. **VSCodeの完全再起動**

### 問題3: GitHubからのクローンに失敗

**症状:** `git clone`エラー

**解決策:**
```bash
# Git設定の確認
git config --global http.postBuffer 524288000

# プロキシ設定（必要に応じて）
git config --global http.proxy http://proxy:port
```

---

## ✅ セットアップ手順

### ステップ1: 前提条件の確認

```bash
# uvxの確認
uvx --version

# Gitの確認
git --version

# Pythonの確認
python3 --version
```

### ステップ2: MCP設定ファイルの更新

`.claude/mcp_settings.json`を上記の内容に更新

### ステップ3: VSCodeの完全再起動

```
1. VSCodeを完全に終了
2. VSCodeを再起動
3. プロジェクトを開く
```

### ステップ4: 動作確認

```
# MCPの接続確認
/mcp

# Serenaのテスト
Serenaを使用して、プロジェクトファイルの一覧を取得してください
```

---

## 🎯 期待される結果

### `/mcp`コマンドの結果

```
✅ context7          - connected
✅ serena-mcp-server - connected
✅ chrome-devtools   - connected (または failed)
```

**重要:** `serena-mcp-server`が`connected`になるはず！

---

## 📊 設定の比較

### 誤った設定（以前）

```json
"serena": {
  "command": "npx",
  "args": ["-y", "@oraios/serena-mcp"]
}
```
**結果:** ❌ Failed（パッケージが存在しない）

### 正しい設定（現在）

```json
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
}
```
**結果:** ✅ Connected（正しくインストールされる）

---

## 🔄 他のプロジェクトでの使用

### プロジェクトパスの変更

他のプロジェクトで使用する場合は、`--project`パスを変更:

```json
"--project",
"/path/to/your/project"
```

### または、環境変数を使用

```json
"--project",
"${workspaceFolder}"
```

---

## 📚 Serena公式リソース

- **GitHubリポジトリ:** https://github.com/oraios/serena
- **ドキュメント:** GitHubのREADME参照
- **Issue報告:** https://github.com/oraios/serena/issues

---

## ✅ まとめ

**正しいSerenaのセットアップ:**
1. ✅ uvxを使用
2. ✅ GitHubから直接インストール
3. ✅ `ide-assistant`コンテキストを使用
4. ✅ プロジェクトパスを明示的に指定

**利点:**
- 22個の強力なツール
- プロジェクト固有の分析
- 循環依存の検出
- 未使用コードの発見
- リファクタリング支援

**次のステップ:**
1. VSCodeを再起動
2. `/mcp`でserena-mcp-serverが`connected`になることを確認
3. Serenaの機能を試す

---

**更新日:** 2025年10月30日
**Serena設定:** uvx + GitHub + ide-assistant
**ステータス:** ✅ 正しい設定完了
