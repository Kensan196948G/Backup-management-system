# MCP クイックスタートガイド
# 3-2-1-1-0 バックアップ管理システム

## 🚀 今すぐ使える機能

### ✅ 接続成功（6個のMCP）

---

## 1. Context7 - ドキュメント取得 📚

**使い方:**
```
Context7を使用して、Flaskのドキュメントを取得してください
Context7でSQLAlchemyのクエリ構文を調べてください
Context7を使用して、Bootstrap 5のコンポーネントを確認してください
```

**用途:**
- Pythonライブラリの公式ドキュメント
- フレームワークのAPIリファレンス
- ベストプラクティスの確認

---

## 2. Serena - コード解析（22ツール）🔍 **NEW!**

### 基本的な使い方

#### プロジェクト構造の確認
```
Serenaを使用して、プロジェクトのディレクトリ構造を確認してください
```

#### クラス・関数の検索
```
Serenaで'BackupJob'クラスを検索してください
Serenaで'process_backup'関数を検索してください
Serenaで'models.py'のシンボル概要を取得してください
```

#### 依存関係の確認
```
Serenaで'BackupJob'を参照しているコードを全て検索してください
Serenaで'app.py'の依存関係を分析してください
```

#### リファクタリング
```
Serenaを使用して、'old_function'を'new_function'にリネームしてください
Serenaで'BackupJob'クラスのメソッドを置換してください
```

#### パターン検索
```
Serenaで"@app.route"パターンを検索してください
Serenaで"db.session"を使用している箇所を全て検索してください
```

### Serenaの22ツール一覧

**プロジェクト管理:**
- list_dir
- find_file
- activate_project

**コード検索:**
- get_symbols_overview
- find_symbol
- find_referencing_symbols
- search_for_pattern

**コード編集:**
- replace_symbol_body
- insert_after_symbol
- insert_before_symbol
- rename_symbol

**メモリ管理:**
- write_memory
- read_memory
- list_memories
- delete_memory

**思考・分析:**
- think_about_collected_information
- think_about_task_adherence
- think_about_whether_you_are_done

**その他:**
- get_current_config
- check_onboarding_performed
- onboarding
- initial_instructions

---

## 3. Chrome DevTools - ブラウザ制御 🌐

**使い方:**
```
Chrome DevToolsを使用して、http://192.168.3.135:5000のページを開いてください
Chrome DevToolsでDOMの構造を確認してください
Chrome DevToolsを使用して、スクリーンショットを取得してください
```

**IPアドレス:**
- **ローカル**: http://localhost:5000
- **ネットワーク**: http://192.168.3.135:5000

**注意**: Chrome実行ファイルが必要（現在未インストール）

**用途:**
- フロントエンドのデバッグ
- UI/UXの検証
- パフォーマンス測定

---

## 4. Brave Search - Web検索 🔍

**使い方:**
```
Brave Searchで、Pythonバックアップのベストプラクティスを検索してください
Brave SearchでFlask 3.0の新機能を検索してください
Brave Searchを使用して、SQLAlchemyのエラー解決方法を検索してください
```

**用途:**
- 最新技術情報の検索
- エラーメッセージの解決方法
- セキュリティ情報の確認

---

## 5. Filesystem - ファイルシステム操作 📁 **NEW!**

**使い方:**
```
Filesystemを使用して、dataディレクトリの内容を確認してください
Filesystemでバックアップファイルを読み込んでください
```

**許可されたディレクトリ:**
```
/mnt/Linux-ExHDD/backup-management-system
```

**用途:**
- ファイル・ディレクトリ操作
- バックアップファイルの管理
- データファイルの確認

---

## 6. Memory - 永続メモリ 💾 **NEW!**

**使い方:**
```
Memoryを使用して、プロジェクトの設定を保存してください
Memoryから前回のセッション情報を読み込んでください
```

**用途:**
- セッション間でのデータ保存
- プロジェクト設定の永続化
- 開発メモの保存

---

## 💡 実践的なワークフロー

### シナリオ1: 新機能の実装

```
1. Serenaでプロジェクト構造確認
   "Serenaを使用して、プロジェクトのディレクトリ構造を確認してください"

2. Serenaで関連コード検索
   "Serenaで'BackupJob'クラスを検索してください"

3. Context7でドキュメント確認
   "Context7を使用して、SQLAlchemyのリレーションシップについて調べてください"

4. 実装
   "models.pyに新しいBackupLogクラスを追加してください"

5. Serenaで参照確認
   "Serenaで新しいBackupLogクラスを使用する場所を確認してください"

6. コミット
   "/commit-and-pr"
```

---

### シナリオ2: バグ修正

```
1. Serenaでエラー箇所のコード検索
   "Serenaで'process_backup'関数を検索してください"

2. Brave Searchで解決方法検索
   "Brave Searchで'SQLAlchemy IntegrityError'の解決方法を検索してください"

3. Context7で正しい使い方確認
   "Context7でSQLAlchemyのユニーク制約について調べてください"

4. 修正
   "app.pyの50行目を修正してください"

5. Serenaで影響範囲確認
   "Serenaで'process_backup'を使用している他の箇所を確認してください"

6. コミット
   "/commit"
```

---

### シナリオ3: コードリファクタリング

```
1. Serenaでシンボル検索
   "Serenaで'old_function_name'を検索してください"

2. Serenaで参照箇所確認
   "Serenaで'old_function_name'を使用している全ての箇所を検索してください"

3. Serenaでリネーム
   "Serenaを使用して、'old_function_name'を'new_function_name'にリネームしてください"

4. テスト
   "pytestを実行してください"

5. コミット
   "/commit"
```

---

### シナリオ4: フロントエンド開発

```
1. Context7でドキュメント確認
   "Context7を使用して、Bootstrap 5のモーダルについて調べてください"

2. 実装
   "templates/index.htmlにモーダルを追加してください"

3. Chrome DevToolsで確認
   "Chrome DevToolsを使用して、http://192.168.3.135:5000を開いてください"

4. Filesystemでアセット確認
   "Filesystemを使用して、staticディレクトリの内容を確認してください"

5. コミット
   "/commit-and-pr"
```

---

## 🎯 カスタムコマンド

### /commit
```
変更をコミットしてプッシュしてください
```
- git add
- git commit
- git push

### /pr
```
PRを作成してください
```
- PR作成（コミット済みの変更）

### /commit-and-pr
```
変更をコミットしてPRを作成してください
```
- git add + commit + push + PR作成

---

## 📊 MCP接続状況

```bash
# 接続状況の確認
claude mcp list
```

**現在の状況:**
```
✅ context7        - Connected
✅ serena          - Connected (22ツール)
✅ chrome-devtools - Connected
✅ brave-search    - Connected
❌ github          - Failed (代替: カスタムコマンド)
❌ sqlite          - Failed (代替: 標準ツール)
✅ filesystem      - Connected
✅ memory          - Connected
❌ sentry          - Failed (オプション)
❌ puppeteer       - Failed (代替: Chrome DevTools)
```

**接続成功率**: 60%（6/10）

---

## 🔧 トラブルシューティング

### Flaskアプリケーションの起動

```bash
# ローカルホストのみ
python app.py

# ネットワークアクセス許可（推奨）
flask run --host=0.0.0.0 --port=5000
```

**アクセスURL:**
- ローカル: http://localhost:5000
- ネットワーク: http://192.168.3.135:5000

---

### MCP接続エラー

**VSCodeの完全再起動:**
```
1. VSCodeを完全終了（Ctrl+Q）
2. VSCodeを再起動
3. プロジェクトを開く
4. `/mcp`で接続確認
```

**MCP設定の確認:**
```bash
# グローバル設定
claude mcp list

# プロジェクトローカル設定
cat .claude/mcp_settings.json
```

---

## 📚 詳細ドキュメント

- [MCP_FINAL_STATUS_UPDATE.md](MCP_FINAL_STATUS_UPDATE.md) - 最新の接続状況、詳細設定
- [MCP_QUICK_REFERENCE.md](MCP_QUICK_REFERENCE.md) - 全MCP機能リファレンス
- [CUSTOM_COMMANDS.md](CUSTOM_COMMANDS.md) - カスタムコマンドの使い方

---

## ✅ 次のアクション

### 1. Serenaの活用（推奨）🔴
```
Serenaを使用して、プロジェクトのディレクトリ構造を確認してください
Serenaでapp.pyのシンボル概要を取得してください
```

### 2. 開発開始（推奨）🟡
- 6つのMCPで十分な機能をカバー
- Serenaの22ツールで強力なコード解析
- 標準ツールとの組み合わせで完全な開発環境

### 3. 失敗したMCPの修正（オプション）🟢
- SQLite: データベースパス指定の変更
- GitHub: Docker環境変数の修正
- Puppeteer: Chromiumインストール

---

## 🎉 まとめ

**利用可能な機能:**
- ✅ MCP: 6個（Context7、Serena、Chrome DevTools、Brave Search、Filesystem、Memory）
- ✅ 標準ツール: 8個
- ✅ カスタムコマンド: 3個
- **合計: 17の機能**

**特に注目:**
🎉 **Serena MCP（22ツール）が正常接続！**
- コード解析が強化されました
- リファクタリングが容易になりました
- 依存関係の可視化が可能になりました

**IPアドレス:**
- **192.168.3.135** - ネットワークアクセス用

**推奨事項:**
1. VSCodeを再起動して設定を反映
2. Serenaでプロジェクト構造を確認
3. 開発を開始！

---

**作成日**: 2025年10月30日
**ステータス**: ✅ **開発可能な状態**
**MCP接続**: 6/10成功（60%）
