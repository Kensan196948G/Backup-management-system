# MCP セットアップガイド
# 3-2-1-1-0 バックアップ管理システム

## 📋 目次

1. [前提条件の確認](#前提条件の確認)
2. [MCPサーバーのセットアップ](#mcpサーバーのセットアップ)
3. [GitHub トークンの設定](#github-トークンの設定)
4. [Brave Search API の設定（オプション）](#brave-search-api-の設定オプション)
5. [動作確認](#動作確認)
6. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件の確認

### 必要なソフトウェア

以下のコマンドで各ソフトウェアのバージョンを確認してください：

```bash
node --version   # v18.x.x以上が必要
npm --version    # 9.x.x以上が必要
git --version    # 2.30.x以上が必要
```

バージョンが古い場合は、以下のコマンドで更新してください：

```bash
# Node.js と npm の更新（Ubuntu/Debian）
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Git の更新
sudo apt-get update
sudo apt-get install -y git
```

---

## MCPサーバーのセットアップ

### ステップ 1: プロジェクトディレクトリの確認

```bash
cd /mnt/Linux-ExHDD/backup-management-system
ls -la .claude/
```

以下のファイルが存在することを確認：
- `.claude/mcp_settings.json` - 実際の設定ファイル（Git管理外）
- `.claude/mcp_settings.json.example` - テンプレートファイル

### ステップ 2: MCP設定ファイルの編集

エディタで設定ファイルを開きます：

```bash
nano .claude/mcp_settings.json
# または
code .claude/mcp_settings.json
```

### ステップ 3: 設定されているMCPサーバーの確認

現在、以下の10個のMCPサーバーが設定されています：

#### 1. Filesystem MCP ✅ （必須）
- **役割**: ファイルシステムへのアクセス
- **パッケージ**: `@modelcontextprotocol/server-filesystem`
- **対象パス**: `/mnt/Linux-ExHDD/backup-management-system`
- **設定**: 自動で有効（トークン不要）

#### 2. GitHub MCP 🔴 （必須 - 要設定）
- **役割**: GitHubリポジトリ操作
- **パッケージ**: `@modelcontextprotocol/server-github`
- **必要情報**: GitHub Personal Access Token
- **状態**: ⚠️ トークンの設定が必要

#### 3. Brave Search MCP 🟡 （推奨 - 要設定）
- **役割**: Web検索、技術情報収集
- **パッケージ**: `@modelcontextprotocol/server-brave-search`
- **必要情報**: Brave API Key
- **状態**: ⚠️ APIキーの設定が必要

#### 4. SQLite MCP 🟢 （推奨）
- **役割**: データベース操作
- **パッケージ**: `@modelcontextprotocol/server-sqlite`
- **対象DB**: `/mnt/Linux-ExHDD/backup-management-system/data/backup_mgmt.db`
- **状態**: 設定済み（DB作成後に使用可能）

#### 5. Context7 MCP 🟢 （推奨）
- **役割**: プロジェクトコンテキスト管理、長期記憶
- **パッケージ**: `@context7/mcp`
- **状態**: 設定済み（トークン不要）

#### 6. Serena MCP 🟡 （オプション）
- **役割**: Webスクレイピング、ドキュメント収集
- **パッケージ**: `@oraios/serena-mcp`
- **用途**: 技術ドキュメント収集、競合調査
- **状態**: 設定済み（トークン不要）

#### 7. Chrome DevTools MCP 🟢 （開発支援）
- **役割**: Chrome DevTools操作、ブラウザ自動化
- **パッケージ**: `@executeautomation/chrome-devtools-mcp`
- **用途**: フロントエンド開発、デバッグ、E2Eテスト
- **状態**: 設定済み（トークン不要）

#### 8. Memory MCP 🟢 （推奨）
- **役割**: 永続的メモリ管理、セッション間データ保持
- **パッケージ**: `@modelcontextprotocol/server-memory`
- **用途**: 開発コンテキストの長期保存、学習内容の記憶
- **状態**: 設定済み（トークン不要）

#### 9. Sequential Thinking MCP 🟢 （推奨）
- **役割**: 複雑な問題の段階的思考支援
- **パッケージ**: `@modelcontextprotocol/server-sequential-thinking`
- **用途**: アーキテクチャ設計、複雑なロジックの分析
- **状態**: 設定済み（トークン不要）

#### 10. Puppeteer MCP 🟢 （自動化）
- **役割**: ヘッドレスブラウザ制御、Webスクレイピング
- **パッケージ**: `@modelcontextprotocol/server-puppeteer`
- **用途**: UI自動化テスト、スクリーンショット取得、PDF生成
- **状態**: 設定済み（トークン不要）

---

## GitHub トークンの設定

### ステップ 1: GitHub Personal Access Token の取得

1. GitHubにログイン
2. https://github.com/settings/tokens にアクセス
3. **"Generate new token"** → **"Generate new token (classic)"** をクリック
4. トークンの設定：
   - **Note**: `backup-management-system MCP`
   - **Expiration**: `90 days` （推奨）
   - **Select scopes**:
     - ✅ `repo` （すべてのサブ項目）
     - ✅ `workflow`

5. **"Generate token"** をクリック
6. 生成されたトークン（`ghp_`で始まる文字列）をコピー
   - ⚠️ この画面を閉じると二度と表示されません！

### ステップ 2: トークンの設定

#### 方法 1: 環境変数を使用（推奨）

`.env` ファイルを作成（`.env.example`をコピー）：

```bash
cp .env.example .env
nano .env
```

以下の行にトークンを貼り付け：

```bash
GITHUB_TOKEN=ghp_あなたのトークンをここに貼り付け
```

ファイルを保存後、権限を設定：

```bash
chmod 600 .env
```

#### 方法 2: 直接設定ファイルに記載（非推奨）

`.claude/mcp_settings.json` を編集：

```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_あなたのトークンをここに貼り付け"
  }
}
```

⚠️ **セキュリティ警告**: この方法は推奨されません。必ず方法1を使用してください。

### ステップ 3: トークンの検証

以下のコマンドでトークンが有効か確認：

```bash
curl -H "Authorization: token ghp_あなたのトークン" \
     https://api.github.com/user
```

成功すると、GitHubユーザー情報がJSON形式で表示されます。

---

## Brave Search API の設定（オプション）

### ステップ 1: Brave Search API Key の取得

1. https://brave.com/search/api/ にアクセス
2. **"Get Started"** をクリック
3. アカウント作成（無料プランで可）
4. ダッシュボードから API Key を取得

**無料プランの制限**:
- 2,000 リクエスト/月
- レート制限あり

### ステップ 2: API Key の設定

`.env` ファイルに追加：

```bash
BRAVE_API_KEY=あなたのAPIキーをここに貼り付け
```

または `.claude/mcp_settings.json` に直接記載（非推奨）。

---

## 動作確認

### ステップ 1: Claude Code の再起動

VSCodeウィンドウを再読み込み：

1. `Ctrl+Shift+P` を押す
2. `Developer: Reload Window` を実行

または、VSCodeを完全に再起動します。

### ステップ 2: MCP接続の確認

Claude Code で新しいチャットを開き、以下のプロンプトを実行：

```
MCPサーバーの接続状態を確認してください。
以下のサーバーが利用可能か教えてください:
- filesystem
- github
- sqlite
- context7
- brave-search
- serena
- chrome-devtools
- memory
- sequential-thinking
- puppeteer
```

**期待される結果**:
- ✅ `filesystem`: 利用可能
- ✅ `github`: 利用可能（トークン設定済みの場合）
- ✅ `sqlite`: 利用可能（DB作成後）
- ✅ `context7`: 利用可能
- ✅ `brave-search`: 利用可能（APIキー設定済みの場合）
- ✅ `serena`: 利用可能
- ✅ `chrome-devtools`: 利用可能
- ✅ `memory`: 利用可能
- ✅ `sequential-thinking`: 利用可能
- ✅ `puppeteer`: 利用可能

### ステップ 3: 各MCPの機能テスト

#### Filesystem MCP のテスト

```
/mnt/Linux-ExHDD/backup-management-system/docs/ の
ファイル一覧を表示してください
```

**期待される結果**: `docs/` ディレクトリ内のファイルが表示される

#### GitHub MCP のテスト

```
GitHubリポジトリ Kensan196948G/backup-management-system の
ブランチ一覧を表示してください
```

**期待される結果**: `main`, `develop` などのブランチが表示される

#### SQLite MCP のテスト（DB作成後）

```
/mnt/Linux-ExHDD/backup-management-system/data/backup_mgmt.db
のテーブル一覧を表示してください
```

**期待される結果**: データベーステーブルが表示される

#### Context7 MCP のテスト

```
このプロジェクトのコンテキストを確認してください
```

**期待される結果**: プロジェクト情報が表示される

#### Brave Search MCP のテスト（APIキー設定済みの場合）

```
Flask 3.0の新機能について検索してください
```

**期待される結果**: Flask 3.0に関する情報が表示される

#### Chrome DevTools MCP のテスト

```
Chrome DevToolsを使用して、localhost:5000の
ページ構造を確認してください
```

**期待される結果**: ページのDOM構造やコンソール情報が表示される

#### Memory MCP のテスト

```
このプロジェクトの主要な技術スタックを記憶してください
```

**期待される結果**: 情報が永続的メモリに保存される

#### Sequential Thinking MCP のテスト

```
バックアップ管理システムのアーキテクチャ設計を
段階的に分析してください
```

**期待される結果**: 複雑な設計が段階的に分析される

#### Puppeteer MCP のテスト

```
Puppeteerを使用して、プロジェクトのREADME.mdを
PDFとして出力してください
```

**期待される結果**: PDFファイルが生成される

---

## トラブルシューティング

### 問題 1: MCPサーバーが見つからない

**症状**: 「MCPサーバーが利用できません」というエラー

**対処方法**:

```bash
# Node.jsバージョン確認
node --version

# npm確認
npm --version

# npxコマンド確認
which npx

# VSCodeの再起動
```

### 問題 2: GitHub MCP接続エラー

**症状**: 「GitHub APIに接続できません」

**対処方法**:

1. トークンの有効性確認:
```bash
curl -H "Authorization: token ghp_あなたのトークン" \
     https://api.github.com/rate_limit
```

2. トークンの権限確認:
   - https://github.com/settings/tokens でトークンの権限を確認
   - `repo` と `workflow` 権限が必要

3. レート制限確認:
   - 上記のcurlコマンドで残りリクエスト数を確認
   - 制限に達している場合は1時間待つ

### 問題 3: SQLite MCP接続エラー

**症状**: 「データベースに接続できません」

**対処方法**:

```bash
# データディレクトリの確認
ls -la /mnt/Linux-ExHDD/backup-management-system/data/

# ディレクトリが存在しない場合は作成
mkdir -p /mnt/Linux-ExHDD/backup-management-system/data

# パーミッション確認
chmod 755 /mnt/Linux-ExHDD/backup-management-system/data
```

### 問題 4: 設定ファイルのJSON形式エラー

**症状**: 設定ファイルの読み込みに失敗

**対処方法**:

```bash
# JSON形式の検証
python3 -m json.tool .claude/mcp_settings.json
```

エラーが表示された場合、以下を確認：
- カンマの過不足
- 括弧の閉じ忘れ
- ダブルクォートの欠落

### 問題 5: Brave Search API エラー

**症状**: 「API Keyが無効です」

**対処方法**:

1. API Keyの確認:
   - https://brave.com/search/api/dashboard でキーを確認

2. クォータ確認:
   - 無料プランは 2,000 リクエスト/月
   - 上限に達していないか確認

3. APIキー再生成:
   - ダッシュボードで新しいキーを生成
   - 設定ファイルを更新

---

## セキュリティのベストプラクティス

### ✅ 推奨される方法

1. **環境変数でトークン管理**
   - `.env` ファイルにトークンを記載
   - `.env` は `.gitignore` に含まれている

2. **ファイル権限の設定**
   ```bash
   chmod 600 .env
   chmod 600 .claude/mcp_settings.json
   ```

3. **定期的なトークンローテーション**
   - 90日ごとにトークンを再生成
   - 古いトークンを無効化

4. **2段階認証の有効化**
   - GitHubアカウントで2FAを有効化
   - https://github.com/settings/security

### ❌ 避けるべき行為

1. トークンをGitにコミットしない
2. トークンを他人と共有しない
3. 不要な権限を付与しない
4. 公開リポジトリにトークンを含めない

---

## チェックリスト

セットアップが完了したら、以下の項目を確認してください：

- [ ] Node.js 18以上がインストールされている
- [ ] npm 9以上がインストールされている
- [ ] `.claude/mcp_settings.json` が作成されている
- [ ] GitHub Personal Access Token を取得した
- [ ] トークンに `repo` と `workflow` 権限がある
- [ ] `.env` ファイルにトークンを設定した
- [ ] `.env` のファイル権限を 600 に設定した
- [ ] VSCodeを再起動した
- [ ] Filesystem MCP が動作する
- [ ] GitHub MCP が動作する
- [ ] Context7 MCP が動作する
- [ ] （オプション）Brave Search API を設定した
- [ ] （オプション）Serena MCP が動作する

---

## サポート情報

### 公式ドキュメント

- **Claude Code**: https://docs.claude.com/en/docs/claude-code
- **MCP仕様**: https://modelcontextprotocol.io/
- **GitHub API**: https://docs.github.com/en/rest

### プロジェクト固有

- **Issues**: https://github.com/Kensan196948G/backup-management-system/issues
- **Discussions**: https://github.com/Kensan196948G/backup-management-system/discussions

---

## 次のステップ

MCPのセットアップが完了したら、以下の開発作業に進むことができます：

1. **プロジェクト構造の作成**
   - Agentを使用したディレクトリ構造の生成

2. **データベース設計**
   - SQLite MCPを使用したスキーマ設計

3. **GitHub統合**
   - 自動コミット・プッシュの設定
   - Issueベースのタスク管理

4. **並列開発の開始**
   - 10体のAgentによる同時開発
   - feature ブランチでの作業

詳細は [docs/MCP設定要件.txt](./MCP設定要件.txt) を参照してください。

---

**作成日**: 2025年10月30日
**バージョン**: 1.0
**プロジェクト**: 3-2-1-1-0 バックアップ管理システム
