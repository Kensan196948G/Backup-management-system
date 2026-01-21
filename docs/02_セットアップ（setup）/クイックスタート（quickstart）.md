# クイックスタートガイド
# 3-2-1-1-0 バックアップ管理システム

このガイドでは、開発を始めるための最小限の手順を説明します。

## 🚀 5分でスタート

### ステップ 1: 前提条件の確認

```bash
node --version   # v18.x.x以上が必要
npm --version    # 9.x.x以上が必要
git --version    # 2.30.x以上が必要
```

### ステップ 2: GitHub Personal Access Token の取得

1. https://github.com/settings/tokens にアクセス
2. "Generate new token" → "Generate new token (classic)"
3. 権限を選択:
   - ✅ `repo` (すべて)
   - ✅ `workflow`
4. トークンをコピー（`ghp_`で始まる文字列）

### ステップ 3: MCP設定の更新

```bash
cd /mnt/Linux-ExHDD/backup-management-system

# .envファイルを作成
cp .env.example .env

# エディタで開いてトークンを設定
nano .env
```

以下の行にトークンを貼り付け:
```bash
GITHUB_TOKEN=ghp_あなたのトークンをここに貼り付け
```

保存後、権限を設定:
```bash
chmod 600 .env
```

### ステップ 4: MCP設定ファイルの確認

`.claude/mcp_settings.json` が存在することを確認:

```bash
ls -la .claude/mcp_settings.json
```

### ステップ 5: VSCodeの再起動

1. VSCodeで `Ctrl+Shift+P`
2. "Developer: Reload Window" を実行

または、VSCodeを完全に再起動します。

### ステップ 6: 動作確認

Claude Code で新しいチャットを開き、以下をテスト:

```
MCPサーバーの接続状態を確認してください
```

期待される結果:
- ✅ filesystem: 利用可能
- ✅ github: 利用可能
- ✅ sqlite: 利用可能
- ✅ context7: 利用可能
- ✅ serena: 利用可能
- ✅ chrome-devtools: 利用可能
- ✅ memory: 利用可能
- ✅ sequential-thinking: 利用可能
- ✅ puppeteer: 利用可能

## ✅ セットアップ完了！

これで、以下のことができるようになりました:

### 📝 ファイル操作
```
docs/ディレクトリのファイル一覧を表示してください
```

### 🔍 GitHubリポジトリ操作
```
このリポジトリのブランチ一覧を表示してください
```

### 🔎 技術情報検索（Brave API設定済みの場合）
```
Flask 3.0の新機能について検索してください
```

### 🧠 プロジェクトコンテキスト管理
```
このプロジェクトの要件定義を確認してください
```

## 📚 次のステップ

### 詳細なドキュメント

- [MCP設定ガイド](./MCP_SETUP_GUIDE.md) - 完全なセットアップ手順
- [MCP設定要件](./MCP設定要件.txt) - 技術仕様の詳細

### 開発の開始

プロジェクト構造を作成する準備が整いました:

```
プロジェクトマネージャーAgentを起動して、
プロジェクト構造を作成してください
```

## ❓ トラブルシューティング

### MCPサーバーが見つからない

```bash
# Node.jsバージョン確認
node --version

# VSCodeを完全再起動
pkill -f "Code"
# その後、VSCodeを再起動
```

### GitHub接続エラー

```bash
# トークンの検証
curl -H "Authorization: token ghp_あなたのトークン" \
     https://api.github.com/user
```

成功するとJSON形式でユーザー情報が表示されます。

### 設定ファイルのJSON形式エラー

```bash
# JSON形式の検証
python3 -m json.tool .claude/mcp_settings.json
```

## 🔒 セキュリティ確認

以下のコマンドでファイル権限を確認:

```bash
# .envファイルの権限（600であるべき）
ls -l .env

# MCP設定ファイルの権限
ls -l .claude/mcp_settings.json

# 権限が正しくない場合は修正
chmod 600 .env
chmod 600 .claude/mcp_settings.json
```

## 📧 サポート

問題が解決しない場合:

- **Issues**: https://github.com/Kensan196948G/backup-management-system/issues
- **詳細ガイド**: [MCP_SETUP_GUIDE.md](./MCP_SETUP_GUIDE.md)

---

**最終更新**: 2025年10月30日
