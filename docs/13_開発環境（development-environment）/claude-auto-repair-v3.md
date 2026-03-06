# 🧠 Claude Code 包括レビュー自動修復ループ v3

## ― 自己収束型レビュー・自動修復アーキテクチャ完全版 ―

---

## 📋 目次

1. [全体アーキテクチャ概要](#1-全体アーキテクチャ概要)
2. [レイヤー別責務分離](#2-レイヤー別責務分離)
3. [自己修復ループ制御設計](#3-自己修復ループ制御設計)
4. [ローカル修復フロー](#4-ローカル修復フロー)
5. [CI修復フロー](#5-ci修復フロー)
6. [強制停止条件](#6-強制停止条件)
7. [人間が介入するポイント](#7-人間が介入するポイント)
8. [無限ループ防止設計](#8-無限ループ防止設計)
9. [最小構成セットアップ手順](#9-最小構成セットアップ手順)
10. [実装ファイル詳細](#10-実装ファイル詳細)
11. [トラブルシューティング](#11-トラブルシューティング)

---

## 1. 全体アーキテクチャ概要

本構成は以下の流れを **安全に自己収束させる設計** です。

```
┌─────────────────────────────────────────────────────────────┐
│                     開発フロー                                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────┐
                    │   設計    │
                    └──────────┘
                           │
                           ▼
                    ┌──────────┐
                    │   実装    │
                    └──────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │        包括レビュー実行                │
        │     (/review-all コマンド)            │
        └──────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
            判定: OK              判定: NG
                │                     │
                ▼                     ▼
        ┌──────────┐         ┌──────────────┐
        │ コミット  │         │  自動修復実行  │
        └──────────┘         │ (/auto-fix)  │
                             └──────────────┘
                                     │
                                     ▼
                             ┌──────────────┐
                             │  再レビュー    │
                             └──────────────┘
                                     │
                        ┌────────────┴────────────┐
                        │                         │
                    判定: OK                  判定: NG
                        │                         │
                        ▼                         ▼
                ┌──────────┐            ┌────────────────┐
                │ コミット  │            │ 収束判定チェック │
                └──────────┘            └────────────────┘
                        │                         │
                        │                ┌────────┴────────┐
                        │                │                 │
                        │            回数<3           回数≥3 or
                        │                │         同一エラー or
                        │                │         差分変化なし
                        │                │                 │
                        │                ▼                 ▼
                        │          ┌─────────┐      ┌──────────┐
                        │          │ 再修復   │      │ 停止通知  │
                        │          └─────────┘      │ (人間介入)│
                        │                │          └──────────┘
                        │                └──┐
                        │                   │
                        ▼                   ▼
                    Push ──────────▶ PR作成
                                       │
                                       ▼
                              ┌──────────────┐
                              │ CI/CD実行     │
                              │ (同様の自動   │
                              │  修復ループ)  │
                              └──────────────┘
                                       │
                                       ▼
                                   マージ
```

### 重要ポイント

* ✅ **最大3回で強制停止** - 無限修復を防止
* ✅ **同じエラーを繰り返さない** - 同一エラー2回連続で停止
* ✅ **差分が変化しないのに続行しない** - ハッシュ比較で検知
* ✅ **人間が最終判断** - 重大な問題は人間が対応
* ❌ **無限修復しない** - 安全設計を徹底

---

## 2. レイヤー別責務分離

システムは4つの明確なレイヤーで構成されています。

### 🏛 レイヤー構成図

```
┌─────────────────────────────────────────────────────────┐
│ 1. ポリシー層 (CLAUDE.md)                                 │
│    - レビュー観点定義                                      │
│    - 自動修復ポリシー                                      │
│    - 停止条件定義                                         │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│ 2. レビュー層 (.claude/commands/)                        │
│    - review-all.md: 包括レビュー実行                      │
│    - auto-fix.md: 自動修復実行                           │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│ 3. ローカル制御層 (Hooks)                                 │
│    - .claude/settings.json: Stop hook設定                │
│    - scripts/local-auto-repair.sh: 修復制御スクリプト      │
│    - state.json: 状態管理                                │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│ 4. CI修復層 (GitHub Actions)                             │
│    - .github/workflows/claude-auto-repair-loop.yml       │
│    - PR/Push時の自動修復                                  │
└─────────────────────────────────────────────────────────┘
```

### レイヤー詳細

#### Layer 1: CLAUDE.md（ポリシー層）

**役割**: すべてのレビュー・修復の基準を定義

**主な内容**:
- バグ、セキュリティ、パフォーマンス、設計、可読性の5つの観点
- 自動修復可能/禁止項目の明確化
- 重大度分類（High/Medium/Low）
- 停止条件の定義

**重要な制約**:
⚠️ **CLAUDE.md単体ではイベント駆動制御はできません**
- Git操作は不可能
- 自動実行は不可能
- あくまでポリシー定義のみ

#### Layer 2: Custom Commands（レビュー実行層）

**役割**: 実際のレビューと修復を実行

**ファイル構成**:
```
.claude/commands/
├── review-all.md    # 包括レビューコマンド
└── auto-fix.md      # 自動修復コマンド
```

**特徴**:
- Claude Codeから `/review-all` や `/auto-fix` で直接実行
- 標準化された出力形式
- CLAUDE.mdのポリシーに準拠

#### Layer 3: Hooks（ローカル制御層）

**役割**: ローカル開発時の自動実行制御

**ファイル構成**:
```
.claude/settings.json             # Stop hook設定
scripts/local-auto-repair.sh      # 修復制御スクリプト
state.json                        # 状態管理ファイル
```

**実行タイミング**:
- Claude Code の "Stop" ボタン押下時
- カスタムコマンド実行後

**制御内容**:
- レビュー → 修復 → 再レビューのループ
- 最大3回までの試行
- 差分ハッシュ比較
- 同一エラー検知

#### Layer 4: GitHub Actions（CI修復層）

**役割**: CI/CDパイプラインでの自動修復

**実行タイミング**:
- PR作成時・更新時
- mainブランチへのpush時
- 手動実行

**機能**:
- ローカルと同様の修復ループ
- 自動コミット・Push
- PRコメントへのレポート投稿

---

## 3. 自己修復ループ制御設計

### 状態管理（state.json）

```json
{
  "repair_count": 0,           // 現在の修復試行回数（0-3）
  "last_hash": "",             // 前回の差分ハッシュ（SHA-256）
  "last_error": "",            // 前回のエラーハッシュ
  "last_review_time": "",      // 最終レビュー時刻（ISO 8601）
  "total_issues_found": 0,     // 累計発見問題数
  "total_issues_fixed": 0,     // 累計修復問題数
  "consecutive_failures": 0,   // 連続失敗回数
  "last_error_message": ""     // 最終エラーメッセージ
}
```

### 修復カウント制御

```bash
# 現在の回数を取得
REPAIR_COUNT=$(jq -r '.repair_count' state.json)

# 上限チェック
if [ "$REPAIR_COUNT" -ge 3 ]; then
    echo "❌ 修復回数上限到達"
    exit 1
fi

# 修復実行後、カウントを増加
jq '.repair_count += 1' state.json > tmp.json && mv tmp.json state.json
```

### 同一エラー検知

```bash
# 現在のエラーをハッシュ化
CURRENT_ERROR=$(grep -A5 "重大度High" review-output.txt | sha256sum | cut -d ' ' -f1)

# 前回のエラーと比較
LAST_ERROR=$(jq -r '.last_error' state.json)

if [ "$CURRENT_ERROR" = "$LAST_ERROR" ] && [ -n "$LAST_ERROR" ]; then
    echo "❌ 同一エラーが2回連続で検出"
    exit 1
fi

# エラーを記録
jq --arg err "$CURRENT_ERROR" '.last_error = $err' state.json > tmp.json
```

### 差分ハッシュ比較

```bash
# 現在の差分ハッシュを計算
CURRENT_HASH=$(git diff | sha256sum | cut -d ' ' -f1)

# 前回のハッシュと比較
LAST_HASH=$(jq -r '.last_hash' state.json)

if [ "$CURRENT_HASH" = "$LAST_HASH" ] && [ -n "$LAST_HASH" ]; then
    echo "❌ 差分が変化していません"
    exit 1
fi

# ハッシュを更新
jq --arg hash "$CURRENT_HASH" '.last_hash = $hash' state.json > tmp.json
```

---

## 4. ローカル修復フロー

### 実行シーケンス

```
┌─────────────────────────────────────────┐
│ 1. Stop hook トリガー                    │
│    (.claude/settings.json)               │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 2. local-auto-repair.sh 起動             │
│    - state.json 初期化/読み込み           │
│    - 修復回数チェック                     │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 3. 包括レビュー実行                       │
│    `claude /review-all`                  │
└─────────────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
     判定: OK          判定: NG
         │                 │
         ▼                 ▼
┌──────────────┐   ┌──────────────────┐
│ 5. 完了      │   │ 4. 差分ハッシュ   │
│    (exit 0)  │   │    計算・比較     │
└──────────────┘   └──────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ 5. 自動修復実行   │
                   │ `claude /auto-fix`│
                   └──────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ 6. 状態更新       │
                   │  - repair_count++ │
                   │  - last_hash更新  │
                   └──────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ 7. 再レビュー実行 │
                   │ `claude /review-all`│
                   └──────────────────┘
                            │
                   ┌────────┴────────┐
                   │                 │
               判定: OK          判定: NG
                   │                 │
                   ▼                 ▼
           ┌──────────┐      ┌────────────┐
           │ 完了     │      │ 次回再試行  │
           │ (exit 0) │      │ または停止  │
           └──────────┘      └────────────┘
```

### 使用方法

#### 自動実行（推奨）

Claude Code の "Stop" ボタンを押すと自動的に実行されます。

```bash
# .claude/settings.json に設定されているため、
# 特別な操作は不要
```

#### 手動実行

```bash
# スクリプトを直接実行
bash scripts/local-auto-repair.sh

# または実行権限を付与して
chmod +x scripts/local-auto-repair.sh
./scripts/local-auto-repair.sh
```

### ログ確認

```bash
# 実行ログを確認
cat logs/auto-repair-local.log

# レビュー結果を確認
cat review-output.txt

# 修復結果を確認
cat fix-output.txt

# 状態を確認
cat state.json
```

---

## 5. CI修復フロー

### GitHub Actions ワークフロー

ファイル: `.github/workflows/claude-auto-repair-loop.yml`

### 実行シーケンス

```
┌─────────────────────────────────────────┐
│ トリガー:                                │
│ - PR作成/更新                            │
│ - mainブランチへのpush                   │
│ - 手動実行                               │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 1. チェックアウト & 環境セットアップ       │
│    - Python 3.11                         │
│    - 依存関係インストール                 │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 2. 状態管理初期化                         │
│    - state.json 作成/読み込み             │
│    - 最大修復回数設定                     │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 3. 差分確認                              │
│    - base branchとの差分取得             │
│    - 差分ハッシュ計算                     │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 4. コードレビュー実行                     │
│    - Flake8: コード品質                  │
│    - Bandit: セキュリティスキャン         │
└─────────────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
     判定: OK          判定: NG
         │                 │
         ▼                 ▼
┌──────────────┐   ┌──────────────────┐
│ 11. 完了     │   │ 5. 修復回数チェック│
└──────────────┘   └──────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ 6. 自動修復実行   │
                   │  - black         │
                   │  - isort         │
                   │  - autoflake     │
                   └──────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ 7. 差分変化確認   │
                   └──────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ 8. コミット&Push  │
                   │  (自動)          │
                   └──────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ 9. 再レビュー実行 │
                   └──────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ 10. PRコメント投稿│
                   │   (結果レポート)  │
                   └──────────────────┘
```

### PRコメントの例

修復成功時:
```markdown
## 🤖 Claude Auto Repair レポート

### 📊 修復統計
- 修復試行回数: 2 / 3
- 初回レビュー: NG
- 自動修復: ✅ 実行済み
- 再レビュー: OK

### ✅ 自動修復成功

すべての自動修復可能な問題が解決されました。
```

修復失敗時:
```markdown
## 🤖 Claude Auto Repair レポート

### 📊 修復統計
- 修復試行回数: 3 / 3
- 初回レビュー: NG
- 自動修復: ❌ 失敗または変更なし

### 🚨 修復回数上限到達

自動修復が規定回数に達しました。手動での対応が必要です。
```

### 手動実行方法

```bash
# GitHub CLIを使用
gh workflow run claude-auto-repair-loop.yml

# 最大修復回数を指定して実行
gh workflow run claude-auto-repair-loop.yml -f max_repairs=5

# または GitHubのUI から
# Actions → Claude Auto Repair Loop → Run workflow
```

---

## 6. 強制停止条件

自動修復は以下のいずれかの条件で**強制的に停止**します。

### 条件1: 修復回数上限到達

```bash
if [ "$REPAIR_COUNT" -ge 3 ]; then
    echo "❌ 修復回数上限到達（3回）"
    exit 1
fi
```

**理由**: 無限ループを防ぐため

**対応**: 人間が問題を調査し、手動で修正

### 条件2: 同一エラー2回連続

```bash
if [ "$CURRENT_ERROR" = "$LAST_ERROR" ]; then
    echo "❌ 同一エラーが2回連続で検出"
    exit 1
fi
```

**理由**: 修復が効果を持たない場合、続行は無意味

**対応**: エラーの根本原因を調査

### 条件3: 差分変化なし

```bash
if [ "$CURRENT_HASH" = "$LAST_HASH" ]; then
    echo "❌ 差分が変化していません"
    exit 1
fi
```

**理由**: 修復が実際には何も変更していない

**対応**: 修復ロジックの見直しまたは手動対応

### 条件4: 重大度High残存

```markdown
## レビュー結果
重大度High: 3件

→ 自動修復不可能
→ 人間による対応必須
```

**理由**: Highレベルの問題は人間の判断が必要

**対応**: 重大な問題を優先的に修正

---

## 7. 人間が介入するポイント

### 必須介入ポイント

#### 1. 修復前の計画確認

**タイミング**: 自動修復実行前

**確認内容**:
- [ ] レビュー結果の妥当性
- [ ] 修復計画の安全性
- [ ] 影響範囲の評価

#### 2. 重大度Highの問題

**対応方法**:
1. レビュー結果を詳細に確認
2. 根本原因を特定
3. 設計レベルから検討
4. 手動で慎重に修正

#### 3. 修復失敗時

**対応方法**:
1. ログを詳細に確認
   ```bash
   cat logs/auto-repair-local.log
   cat review-output.txt
   ```
2. 失敗理由を特定
3. 手動で修正
4. state.jsonをリセット
   ```bash
   cat > state.json <<EOF
   {
     "repair_count": 0,
     "last_hash": "",
     "last_error": ""
   }
   EOF
   ```

#### 4. マージ前の最終確認

**確認内容**:
- [ ] すべてのテストが成功
- [ ] CI/CDが成功
- [ ] レビュー結果がOK
- [ ] 修復内容の妥当性

### 任意介入ポイント

#### 1. 修復内容の確認

```bash
# 修復による変更を確認
git diff

# 修復結果レポートを確認
cat fix-output.txt
```

#### 2. 状態の手動リセット

```bash
# 修復ループをリセットする場合
bash scripts/local-auto-repair.sh --reset
```

---

## 8. 無限ループ防止設計

### 技術的保護メカニズム

#### 1. カウンターベース制御

```
試行1 → 試行2 → 試行3 → 停止
  ✓       ✓       ✓       ✗
```

**実装**:
```bash
MAX_REPAIR=3
REPAIR_COUNT=$(jq -r '.repair_count' state.json)

if [ "$REPAIR_COUNT" -ge "$MAX_REPAIR" ]; then
    exit 1
fi
```

#### 2. ハッシュ比較による変化検知

```
修復前: hash_A
  ↓ 修復実行
修復後: hash_B

if hash_A == hash_B:
    停止（変化なし）
```

**実装**:
```bash
BEFORE=$(git diff | sha256sum)
# ... 修復実行 ...
AFTER=$(git diff | sha256sum)

if [ "$BEFORE" = "$AFTER" ]; then
    exit 1
fi
```

#### 3. エラーパターン追跡

```
エラー1: pattern_X
  ↓ 修復実行
エラー2: pattern_X  ← 同一

→ 停止（修復効果なし）
```

**実装**:
```bash
ERROR_PATTERN=$(extract_error_pattern review-output.txt)
LAST_PATTERN=$(jq -r '.last_error' state.json)

if [ "$ERROR_PATTERN" = "$LAST_PATTERN" ]; then
    exit 1
fi
```

#### 4. タイムアウト設定

```bash
# GitHub Actionsのjobレベルタイムアウト
timeout-minutes: 30

# スクリプトレベルタイムアウト
timeout 600 claude /review-all
```

### 運用的保護メカニズム

#### 1. 段階的エスカレーション

```
試行1: 自動修復
  ↓ 失敗
試行2: 自動修復 + 警告
  ↓ 失敗
試行3: 自動修復 + 詳細ログ
  ↓ 失敗
人間介入
```

#### 2. 通知システム

- 修復失敗時: Slack/Teams通知
- 回数上限時: Issue自動作成
- 重大度High: メール通知

#### 3. ロールバック機能

```bash
# 修復失敗時、自動的に元に戻す
git stash save "auto-repair-backup-$(date +%s)"
# ... 修復実行 ...
if [ $? -ne 0 ]; then
    git stash pop
fi
```

---

## 9. 最小構成セットアップ手順

### 前提条件

- Git 2.x以降
- jq（JSON処理ツール）
- Python 3.11以降（CI用）
- Claude Code（ローカル用）

### ステップ1: jqのインストール確認

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# 確認
jq --version
```

### ステップ2: ファイル配置

以下のファイルをリポジトリに配置します。

```
your-repo/
├── CLAUDE.md                                    # ポリシー定義
├── state.json                                   # 状態管理
├── state.json.schema                            # スキーマ定義
├── .claude/
│   ├── settings.json                            # Hook設定
│   └── commands/
│       ├── review-all.md                        # レビューコマンド
│       └── auto-fix.md                          # 修復コマンド
├── scripts/
│   └── local-auto-repair.sh                     # ローカル修復スクリプト
└── .github/
    └── workflows/
        └── claude-auto-repair-loop.yml          # CI修復ワークフロー
```

### ステップ3: スクリプト実行権限の付与

```bash
chmod +x scripts/local-auto-repair.sh
```

### ステップ4: state.jsonの初期化

```bash
cat > state.json <<EOF
{
  "repair_count": 0,
  "last_hash": "",
  "last_error": "",
  "last_review_time": "",
  "total_issues_found": 0,
  "total_issues_fixed": 0
}
EOF
```

### ステップ5: .gitignoreの設定

```bash
# .gitignoreに追加（任意）
cat >> .gitignore <<EOF

# Auto-repair system
review-output.txt
fix-output.txt
logs/auto-repair-local.log
*.diff
EOF
```

### ステップ6: 動作確認（ローカル）

```bash
# 1. テスト用の変更を作成
echo "# Test" >> README.md

# 2. レビューコマンドを実行（Claude Code内で）
# /review-all

# 3. または直接スクリプトを実行
bash scripts/local-auto-repair.sh

# 4. 結果確認
cat review-output.txt
cat state.json
```

### ステップ7: 動作確認（CI）

```bash
# 1. ブランチ作成
git checkout -b test/auto-repair

# 2. テスト用変更をコミット
git add .
git commit -m "Test: Auto-repair system"

# 3. プッシュ
git push origin test/auto-repair

# 4. PR作成
gh pr create --base main --head test/auto-repair \
  --title "Test: Auto-repair system" \
  --body "Testing auto-repair loop"

# 5. GitHub ActionsでWorkflowの実行を確認
gh pr checks

# 6. PRコメントでレポートを確認
```

### ステップ8: 本番運用開始

```bash
# 1. mainブランチにマージ
gh pr merge --merge

# 2. 開発フローに統合
# - 以降、PRやpush時に自動的に実行されます
# - Claude Code使用時は自動的にローカル修復が実行されます
```

---

## 10. 実装ファイル詳細

### 10.1 CLAUDE.md

**パス**: `/CLAUDE.md`

**役割**: プロジェクト全体のレビュー・修復ポリシー定義

**主要セクション**:
- 包括レビュー基準
- 自動修復ポリシー
- 修復制御ルール
- 重大度分類
- 人間の最終判断

**ポイント**:
- すべての判断基準の根拠
- CLAUDE.md単体ではGit操作やイベント駆動は不可能
- あくまで「ポリシードキュメント」として機能

### 10.2 .claude/commands/review-all.md

**パス**: `/.claude/commands/review-all.md`

**役割**: 包括レビューの実行手順定義

**実行方法**:
```bash
# Claude Code内で
/review-all
```

**出力形式**:
```markdown
## 総合判定
[OK/NG]

## 🔴 重大度High
[問題リスト]

## 🟡 重大度Medium
[問題リスト]

## 🟢 重大度Low
[問題リスト]

## 自動修復可能項目
[修復可能な項目リスト]
```

### 10.3 .claude/commands/auto-fix.md

**パス**: `/.claude/commands/auto-fix.md`

**役割**: 自動修復の実行手順定義

**実行方法**:
```bash
# Claude Code内で
/auto-fix
```

**修復対象**:
- コードフォーマット（インデント、空白）
- 命名規則違反
- 簡単なバグ修正
- ドキュメント追加
- 軽微なリファクタリング

**修復禁止**:
- 設計変更
- 新機能追加
- セキュリティロジック変更

### 10.4 .claude/settings.json

**パス**: `/.claude/settings.json`

**役割**: Claude Codeのhook設定

**設定内容**:
```json
{
  "hooks": {
    "Stop": [
      {
        "command": "bash scripts/local-auto-repair.sh",
        "description": "包括レビューと自動修復の実行"
      }
    ]
  }
}
```

**動作**:
- Claude Codeの "Stop" ボタン押下時に自動実行
- レビュー → 修復 → 再レビューのループを制御

### 10.5 scripts/local-auto-repair.sh

**パス**: `/scripts/local-auto-repair.sh`

**役割**: ローカル自動修復の制御スクリプト

**主な機能**:
1. state.json の初期化・読み込み
2. 包括レビュー実行
3. 修復回数チェック
4. 差分ハッシュ比較
5. 同一エラー検知
6. 自動修復実行
7. 再レビュー実行
8. 状態更新

**使用方法**:
```bash
# 自動実行（Stop hook経由）
# または手動実行
bash scripts/local-auto-repair.sh
```

### 10.6 state.json

**パス**: `/state.json`

**役割**: 修復ループの状態管理

**スキーマ**: `state.json.schema` 参照

**主要フィールド**:
```json
{
  "repair_count": 0,        // 修復試行回数
  "last_hash": "",          // 差分ハッシュ
  "last_error": "",         // エラーハッシュ
  "last_review_time": "",   // 最終レビュー時刻
  "total_issues_found": 0,  // 累計発見問題数
  "total_issues_fixed": 0   // 累計修復問題数
}
```

### 10.7 .github/workflows/claude-auto-repair-loop.yml

**パス**: `/.github/workflows/claude-auto-repair-loop.yml`

**役割**: CI/CDでの自動修復ワークフロー

**トリガー**:
- PR作成・更新時
- mainブランチへのpush時
- 手動実行

**主要ステップ**:
1. 環境セットアップ
2. 状態初期化
3. 差分確認
4. コードレビュー（Flake8, Bandit）
5. 自動修復（Black, isort, autoflake）
6. 差分変化確認
7. 自動コミット・Push
8. 再レビュー
9. PRコメント投稿
10. 状態リセット

---

## 11. トラブルシューティング

### 問題1: jqコマンドが見つからない

**エラー**:
```
bash: jq: command not found
```

**解決方法**:
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# 確認
jq --version
```

### 問題2: Claudeコマンドが見つからない

**エラー**:
```
⚠️ Claude CLI が利用できません
```

**原因**: Claude Codeがインストールされていない、またはCLIが利用できない環境

**解決方法**:
1. Claude Codeをインストール
2. または、スクリプトを修正して直接レビューツールを実行
   ```bash
   # claude /review-all の代わりに
   flake8 app/ > review-output.txt
   ```

### 問題3: 修復が無限ループしている

**症状**: 何度も同じ修復が実行される

**原因**: 停止条件が正しく機能していない

**解決方法**:
```bash
# 1. 状態を確認
cat state.json

# 2. ログを確認
cat logs/auto-repair-local.log

# 3. 手動で状態をリセット
cat > state.json <<EOF
{
  "repair_count": 0,
  "last_hash": "",
  "last_error": ""
}
EOF

# 4. 停止条件のロジックを確認
bash -x scripts/local-auto-repair.sh
```

### 問題4: GitHub Actionsで権限エラー

**エラー**:
```
Permission denied (publickey)
```

**原因**: Git push権限がない

**解決方法**:
```yaml
# .github/workflows/claude-auto-repair-loop.ymlに追加
permissions:
  contents: write
  pull-requests: write
```

### 問題5: レビュー結果が常にOK

**症状**: 問題があるはずなのにOKと判定される

**原因**: レビューツールが正しく実行されていない

**解決方法**:
```bash
# 1. 手動でレビューツールを実行
flake8 app/ --select=E9,F63,F7,F82
bandit -r app/ -ll

# 2. レビュー出力を確認
cat review-output.txt

# 3. レビューコマンドを修正
# .claude/commands/review-all.md を編集
```

### 問題6: 修復後もエラーが残る

**症状**: 修復を実行してもエラーが解消されない

**原因**: 
- 自動修復可能な範囲外の問題
- 修復ロジックの不備

**解決方法**:
1. レビュー結果で重大度Highの項目を確認
2. 人間が手動で修正
3. 修復ロジックを改善
   ```bash
   # auto-fix.md を編集して修復範囲を拡大
   # または制限を追加
   ```

### 問題7: state.jsonが壊れている

**エラー**:
```
parse error: Invalid numeric literal
```

**原因**: state.jsonのJSON形式が不正

**解決方法**:
```bash
# 1. バックアップ
cp state.json state.json.bak

# 2. 再初期化
cat > state.json <<EOF
{
  "repair_count": 0,
  "last_hash": "",
  "last_error": "",
  "last_review_time": "",
  "total_issues_found": 0,
  "total_issues_fixed": 0
}
EOF

# 3. スキーマバリデーション（任意）
jsonschema -i state.json state.json.schema
```

---

## 📚 関連ドキュメント

- [CLAUDE.md](/CLAUDE.md) - ポリシー定義
- [state.json.schema](/state.json.schema) - 状態管理スキーマ
- [GitHub Actions ワークフロー](/.github/workflows/claude-auto-repair-loop.yml)
- [ローカル修復スクリプト](/scripts/local-auto-repair.sh)

---

## 🎯 まとめ

本構成により、以下が実現されます：

### ✅ 達成できること

1. **品質保証の自動化**
   - バグ、セキュリティ、パフォーマンス、設計、可読性の包括的なレビュー
   - 軽微な問題の自動修復

2. **開発効率の向上**
   - レビュー時間の短縮
   - 単純なミスの自動修正
   - 人間は重要な判断に集中

3. **安全性の確保**
   - 最大3回の修復制限
   - 同一エラー・差分変化なしの検知
   - 無限ループの完全防止

4. **透明性の確保**
   - すべての修復内容を記録
   - 状態の可視化
   - 詳細なログ

### 🚀 これは何か？

これは単なる自動修復ではありません。

> **自己収束型CIエージェント**

人間とAIが協調し、安全かつ効率的にコード品質を維持するシステムです。

---

## 🔒 重要な注意事項

1. **CLAUDE.md単体の限界**
   - Git操作は不可能
   - イベント駆動制御は不可能
   - あくまでポリシードキュメント

2. **Git操作の責務**
   - Hooks（ローカル）
   - GitHub Actions（CI）
   - これらが実際のGit操作を実行

3. **安全性の最優先**
   - 修復は最大3回まで
   - 重大な問題は人間が対応
   - 無限ループは絶対に発生しない

4. **実務前提の設計**
   - 現実的な制約を考慮
   - 夢物語ではなく実装可能な構成
   - 実際に動かせるコード

---

**バージョン**: 3.0  
**最終更新**: 2026-02-13  
**ステータス**: 実装完了・運用可能

---

## 📞 サポート

問題が発生した場合は、以下を確認してください：

1. [トラブルシューティング](#11-トラブルシューティング)
2. [GitHub Issues](https://github.com/Kensan196948G/backup-management-system/issues)
3. 実行ログ: `logs/auto-repair-local.log`
4. 状態ファイル: `state.json`

---

**🎉 セットアップ完了おめでとうございます！自己収束型CIエージェントで快適な開発を！**
