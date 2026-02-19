# Git Worktree並列開発ガイド - 8エージェント構成

## 概要

8体のエージェントが並列で開発するためのGit Worktree環境の使用ガイド。

## セットアップ

```bash
# 環境構築（初回のみ）
./scripts/setup_worktrees.sh

# 状態確認
python scripts/orchestrator.py status
```

## 8エージェントの役割

| ID | エージェント名 | 担当領域 | 優先度 | 依存関係 |
|----|--------------|---------|--------|---------|
| 01 | Core Backup Engine | バックアップロジック、3-2-1-1-0ルール | CRITICAL | なし |
| 02 | Storage Management | ストレージプロバイダ、メディア管理 | CRITICAL | なし |
| 03 | Verification & Validation | 検証、整合性チェック | HIGH | 01, 02 |
| 04 | Scheduler & Job Manager | ジョブスケジューリング、並列実行 | HIGH | 01, 02 |
| 05 | Alert & Notification | 通知、アラート、SLA監視 | MEDIUM | 01, 03 |
| 06 | Web UI & Dashboard | Webインターフェース | MEDIUM | 01, 02, 04, 05 |
| 07 | API & Integration Layer | REST API、外部連携 | MEDIUM | 01-05 |
| 08 | Documentation & Compliance | ドキュメント、ISO準拠 | LOW | 01-07 |

## 日次ワークフロー

### 朝 (9:00)

```bash
# 各エージェントのworktreeで実行
cd /mnt/Linux-ExHDD/worktrees/agent-01-core

# 最新のdevelopを取得
git fetch origin develop
git merge origin/develop

# 進捗ログ更新
echo "$(date): 本日の作業開始" >> logs/agent-01/progress.md
```

### 開発中

```bash
# 15-30分ごとに小さくコミット
git add <files>
git commit -m "[CORE-01] add: 機能説明"

# 1-2時間ごとにプッシュ
git push origin feature/backup-engine
```

### 夕方 (17:30)

```bash
# テスト実行
pytest tests/

# 最終コミット
git add .
git commit -m "[CORE-01] eod: 本日の作業完了"
git push origin feature/backup-engine
```

## 統合手順

```bash
# オーケストレーターで依存関係チェック
python scripts/orchestrator.py deps 03

# 統合実行（dry-run）
python scripts/orchestrator.py integrate 01 --dry-run

# 実際に統合
python scripts/orchestrator.py integrate 01
```

## コミットメッセージ規約

```
[AGENT-XX] type: 説明

type:
- add: 新機能追加
- fix: バグ修正
- refactor: リファクタリング
- test: テスト追加
- docs: ドキュメント更新
- eod: 終業時のまとめコミット
```

## トラブルシューティング

### コンフリクト発生時

```bash
# 競合ファイルを確認
git status

# 手動で解決
git mergetool

# 解決後
git add <resolved-files>
git merge --continue
```

### 全エージェント同期

```bash
# 全エージェントをdevelopと同期
python scripts/orchestrator.py sync
```

---

**詳細な使用方法は各worktreeのAGENT_README.mdを参照してください。**
