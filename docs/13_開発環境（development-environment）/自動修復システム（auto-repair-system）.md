# GitHub Issue駆動型 自動修復システム

## 概要

このシステムは、バックアップ管理システムのエラーを自動的に検知し、GitHub Issueを通じて自動修復を試みるインテリジェントなシステムです。

### 主な機能

1. **自動エラー検知**: 10分ごとにシステムヘルスチェックを実行
2. **GitHub Issue自動作成**: エラー検出時に詳細なIssueを自動作成
3. **自動修復ループ**: 最大10回まで自動修復を試行
4. **修復ステータス追跡**: Issue上で修復の進捗を可視化
5. **手動介入サポート**: 自動修復失敗時は手動対応にエスカレーション

---

## システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions                               │
│                                                                   │
│  ┌──────────────────┐         ┌─────────────────────┐          │
│  │  Health Check    │         │   Auto-Repair       │          │
│  │  (Every 10min)   │         │   (On Issue Event)  │          │
│  │                  │         │                     │          │
│  │  1. DB Check     │         │  1. Analyze Error   │          │
│  │  2. Flask Check  │         │  2. Execute Repair  │          │
│  │  3. Models Check │───❌───>│  3. Verify Fix      │          │
│  │  4. Routes Check │  Error  │  4. Update Issue    │          │
│  │  5. Templates    │         │  5. Close/Retry     │          │
│  │                  │         │                     │          │
│  │     ↓ Error      │         │        ↓            │          │
│  └─────┬────────────┘         └────────┬────────────┘          │
│        │                               │                        │
│        ↓                               ↓                        │
│  ┌─────────────────────────────────────────────┐               │
│  │         GitHub Issue Created                 │               │
│  │  Labels: auto-repair, bug, automated        │               │
│  │                                              │               │
│  │  Triggers → Auto-Repair Workflow            │               │
│  └─────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

---

## コンポーネント詳細

### 1. ヘルスチェックスクリプト (`scripts/health_check.py`)

**役割**: システムの健全性を監視し、問題を検出する

**チェック項目**:
- ✅ データベース接続
- ✅ Flaskアプリケーション起動
- ✅ モデル整合性
- ✅ ルート定義
- ✅ テンプレートファイル
- ✅ 環境変数

**動作**:
```bash
# 手動実行
python scripts/health_check.py

# 自動実行（GitHub Actions）
# 10分ごとに自動実行される
```

**出力**:
- エラー検出時: GitHub Issueを自動作成
- ログファイル: `logs/health_checks/health_check_YYYYMMDD_HHMMSS.json`

**GitHub Issue作成条件**:
- エラーが1件以上検出された場合
- `GITHUB_TOKEN`環境変数が設定されている場合

---

### 2. 自動修復エージェント (`scripts/auto_repair.py`)

**役割**: GitHub Issueから問題を分析し、自動修復を実行する

**修復機能**:
1. **データベース修復**
   - データベースファイルが存在しない場合、新規作成
   - `init_db.py`スクリプトを実行
   - スキーマ初期化

2. **Flask起動修復**
   - `SECRET_KEY`が未設定の場合、自動生成
   - `.env`ファイルに追加

3. **モデル整合性修復**
   - データベーススキーマを最新に更新
   - `db.create_all()`を実行

4. **ルート・テンプレート検証**
   - 欠落しているファイルを報告

**使用方法**:
```bash
# 手動実行（単一試行）
python scripts/auto_repair.py --issue 10 --max-retries 1 --retry-interval 0

# 手動実行（10回リトライ、10分間隔）
python scripts/auto_repair.py --issue 10 --max-retries 10 --retry-interval 600
```

**パラメータ**:
- `--issue`: 修復対象のIssue番号（必須）
- `--max-retries`: 最大リトライ回数（デフォルト: 10）
- `--retry-interval`: リトライ間隔（秒）（デフォルト: 600秒 = 10分）

---

### 3. GitHub Actions ワークフロー (`.github/workflows/auto-repair.yml`)

**トリガー条件**:
1. **スケジュール実行**: 10分ごとに自動ヘルスチェック
2. **Issue作成時**: `auto-repair`ラベル付きIssueが作成された時
3. **ラベル追加時**: 既存のIssueに`auto-repair`ラベルが追加された時
4. **手動実行**: GitHub Actionsから手動でトリガー

**ジョブ構成**:

#### Job 1: `health-check`
- 定期的にシステムヘルスチェックを実行
- エラー検出時にGitHub Issueを作成
- ログをアーティファクトとして保存（7日間保持）

#### Job 2: `auto-repair`
- `auto-repair`ラベル付きIssueに対して修復を試行
- `manual-repair`ラベルがある場合はスキップ
- 単一試行のみ実行（ループはスケジュールで管理）
- 成功時: Issue に成功コメント
- 失敗時: Issue に失敗コメントと次回試行通知

#### Job 3: `track-repair-attempts`
- 修復試行回数をカウント
- 10回失敗した場合、`manual-repair`ラベルを自動追加
- 手動対応が必要な旨を通知

---

## ワークフロー詳細

### 標準的な動作フロー

```
1. スケジュールトリガー（10分ごと）
   ↓
2. ヘルスチェック実行
   ↓
3. エラー検出
   ↓
4. GitHub Issue自動作成
   - タイトル: "🔴 Auto-detected System Errors - YYYY-MM-DD HH:MM:SS"
   - ラベル: auto-repair, bug, automated
   ↓
5. Issue作成イベントで自動修復ワークフローをトリガー
   ↓
6. 自動修復試行（試行回数1）
   ↓
7. 検証
   ├─ 成功 → Issue自動クローズ ✅
   └─ 失敗 → 次回のスケジュール実行で再試行 ⏳
          ↓
8. 10分後、再度ヘルスチェック
   ↓
9. まだエラーがある場合、同じIssueで修復試行（試行回数2）
   ↓
   ... 最大10回まで繰り返し ...
   ↓
10. 10回失敗 → manual-repairラベル自動追加 🔴
```

---

## ラベル一覧

| ラベル | 色 | 説明 | 用途 |
|--------|------|------|------|
| `auto-repair` | 緑 (0e8a16) | 自動修復システムが対応 | 自動修復対象として識別 |
| `bug` | 赤 (d73a4a) | バグ報告 | エラー分類 |
| `automated` | 青 (bfd4f2) | 自動作成 | 自動化システムによる作成 |
| `manual-repair` | オレンジ (d93f0b) | 手動対応が必要 | 自動修復を停止し、手動対応へエスカレーション |

---

## 使用例

### 例1: 自動エラー検知とIssue作成

```bash
# GitHub Actionsが10分ごとに自動実行
# エラー検出時にIssue #10が作成される

Issue #10: 🔴 Auto-detected System Errors - 2025-11-01 20:07:03
Labels: auto-repair, bug, automated

内容:
## 🚨 自動検知されたシステムエラー
### ❌ 検出されたエラー
1. ❌ Database connection failed: No module named 'apscheduler'
2. ❌ Flask app startup failed: No module named 'apscheduler'
...
```

### 例2: 自動修復の実行

```bash
# Issue #10作成イベントでワークフローがトリガー
# 自動修復エージェントが起動

試行1: データベース修復を試みる
  ↓
検証: まだエラーが残っている
  ↓
Issue #10にコメント追加:
  "⚠️ 自動修復試行 (1/10)
   次回試行: 10分後"
  ↓
10分後、再試行...
```

### 例3: 修復成功

```bash
試行3: すべての修復が成功
  ↓
検証: ✅ すべてのヘルスチェック合格
  ↓
Issue #10にコメント追加:
  "✅ 自動修復成功
   修復完了時刻: 2025-11-01 20:27:15
   試行回数: 3/10"
  ↓
Issue #10を自動クローズ
```

### 例4: 最大試行回数到達

```bash
試行10: 修復失敗
  ↓
自動的に manual-repair ラベルを追加
  ↓
Issue #10にコメント追加:
  "🔴 最大試行回数（10回）に到達しました
   手動での対応が必要です"
  ↓
自動修復停止、手動対応待ち
```

---

## 手動操作

### 自動修復を停止する場合

```bash
# Issueに manual-repair ラベルを追加
gh issue edit <ISSUE_NUMBER> --add-label "manual-repair"
```

### 自動修復を再開する場合

```bash
# manual-repair ラベルを削除
gh issue edit <ISSUE_NUMBER> --remove-label "manual-repair"
```

### 特定のIssueで即座に修復を試行する場合

```bash
# GitHub Actionsから手動実行
# または、ローカルで実行:
python scripts/auto_repair.py --issue <ISSUE_NUMBER> --max-retries 1
```

---

## トラブルシューティング

### Q1: Issueが作成されない

**確認事項**:
- `GITHUB_TOKEN`環境変数が設定されているか
- GitHub CLIがインストールされているか
- リポジトリに必要なラベルが存在するか

**解決策**:
```bash
# ラベル作成
gh label create "auto-repair" --description "Automated repair system" --color "0e8a16"
gh label create "automated" --description "Created by automation" --color "bfd4f2"
gh label create "manual-repair" --description "Requires manual intervention" --color "d93f0b"
```

### Q2: 自動修復が動作しない

**確認事項**:
- Issueに`auto-repair`ラベルが付いているか
- `manual-repair`ラベルが付いていないか
- GitHub Actionsワークフローが有効になっているか

**解決策**:
```bash
# ワークフロー状態確認
gh workflow list

# ワークフロー有効化
gh workflow enable "Auto-Repair System"
```

### Q3: 修復が成功しない

**確認事項**:
- エラーログを確認（GitHub Actions Artifacts）
- 修復対象のエラーが対応可能なエラーか
- 必要なパッケージ（`apscheduler`など）がインストールされているか

**解決策**:
```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# 手動で修復スクリプトを実行
python scripts/auto_repair.py --issue <ISSUE_NUMBER> --max-retries 1
```

---

## 設定

### 環境変数

必要な環境変数:
- `GITHUB_TOKEN`: GitHub API認証用トークン
- `GITHUB_REPOSITORY`: リポジトリ名（例: `Kensan196948G/backup-management-system`）
- `SECRET_KEY`: Flask用シークレットキー
- `FLASK_ENV`: Flask環境（`development` または `production`）

### スケジュール変更

`.github/workflows/auto-repair.yml`の`cron`設定を変更:

```yaml
schedule:
  # 現在: 10分ごと
  - cron: '*/10 * * * *'

  # 5分ごとに変更する場合
  - cron: '*/5 * * * *'

  # 1時間ごとに変更する場合
  - cron: '0 * * * *'
```

### 最大試行回数の変更

`scripts/auto_repair.py`のデフォルト値を変更、または起動時に指定:

```bash
# 最大5回まで試行
python scripts/auto_repair.py --issue 10 --max-retries 5

# リトライ間隔を5分（300秒）に変更
python scripts/auto_repair.py --issue 10 --retry-interval 300
```

---

## ファイル構成

```
backup-management-system/
├── .github/
│   └── workflows/
│       ├── auto-repair.yml          # 自動修復ワークフロー
│       └── ci.yml                   # CI/CDワークフロー
├── scripts/
│   ├── health_check.py              # ヘルスチェックスクリプト
│   ├── auto_repair.py               # 自動修復エージェント
│   └── init_db.py                   # データベース初期化
├── logs/
│   └── health_checks/               # ヘルスチェックログ
│       └── health_check_*.json
└── docs/
    └── AUTO_REPAIR_SYSTEM.md        # このドキュメント
```

---

## 監視とログ

### ヘルスチェックログ

場所: `logs/health_checks/health_check_YYYYMMDD_HHMMSS.json`

形式:
```json
{
  "timestamp": "2025-11-01T20:07:04.123456",
  "errors": [
    "❌ Database connection failed: ...",
    "❌ Flask app startup failed: ..."
  ],
  "warnings": [
    "⚠️ Missing environment variables: ..."
  ],
  "checks_passed": [
    "✅ Templates check: OK",
    "✅ Environment variables: OK"
  ],
  "issue_data": {
    "issue_number": "10",
    "issue_url": "https://github.com/.../issues/10"
  }
}
```

### GitHub Actions Artifacts

- ワークフロー実行ごとにログがアーティファクトとして保存される
- 保存期間: 7日間
- ダウンロード: GitHub Actions > ワークフロー実行 > Artifacts

---

## ベストプラクティス

1. **定期的なモニタリング**: GitHub Issuesをウォッチして自動修復の状況を確認
2. **ラベル管理**: 重要度に応じてカスタムラベルを追加
3. **手動介入タイミング**: 3回以上連続で失敗した場合は早めに手動対応を検討
4. **ログレビュー**: 週次でヘルスチェックログをレビュー
5. **依存関係の更新**: `requirements.txt`を最新に保つ

---

## セキュリティ考慮事項

- `GITHUB_TOKEN`は秘匿情報として管理（GitHub Secretsを使用）
- ヘルスチェックログに機密情報が含まれないよう注意
- 自動修復スクリプトは最小権限で実行
- Issue作成時にAPIキーやパスワードを含めない

---

## 今後の拡張案

- [ ] Slack/Teams通知の統合
- [ ] メトリクス収集とダッシュボード化
- [ ] AI/LLM統合による高度なエラー診断
- [ ] カスタム修復スクリプトのプラグイン機構
- [ ] データベースバックアップの自動作成

---

## サポート

問題が発生した場合:
1. GitHub Issueを作成（`manual-repair`ラベル付き）
2. ヘルスチェックログを添付
3. エラーメッセージの詳細を記載

---

**作成日**: 2025-11-01
**バージョン**: 1.0.0
**メンテナンス**: Backup Management System Team
