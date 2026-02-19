# VSCode Workspace 8エージェント並列開発ガイド

## 🎯 1つのVSCodeで8エージェント開発

このガイドでは、1つのVSCodeウィンドウで8体のエージェントを同時に開発する方法を説明します。

---

## 🚀 クイックスタート

### Step 1: Workspaceを開く

**VSCodeで実行:**
```
File → Open Workspace from File...
→ backup-system-8-agents.code-workspace を選択
```

または、コマンドラインから:
```bash
cd /mnt/Linux-ExHDD/backup-management-system
code backup-system-8-agents.code-workspace
```

### Step 2: エクスプローラーの確認

左サイドバー（📁アイコン）に9つのフォルダが表示されます:

```
EXPLORER
  📁 🏠 MAIN REPOSITORY (DEVELOP)      ← 統合管理用
  📁 🔴 AGENT-01: CORE BACKUP ENGINE   ← 実装済み
  📁 🔴 AGENT-02: STORAGE MANAGEMENT   ← これから実装
  📁 🟠 AGENT-03: VERIFICATION & VALIDATION
  📁 🟠 AGENT-04: SCHEDULER & JOB MANAGER
  📁 🟡 AGENT-05: ALERT & NOTIFICATION
  📁 🟡 AGENT-06: WEB UI & DASHBOARD
  📁 🟡 AGENT-07: API & INTEGRATION LAYER
  📁 🟢 AGENT-08: DOCUMENTATION & COMPLIANCE
```

**色の意味:**
- 🔴 CRITICAL - 最優先
- 🟠 HIGH - 高優先
- 🟡 MEDIUM - 中優先
- 🟢 LOW - 低優先

---

## 📝 並列開発の実践

### 方法1: エクスプローラー + 分割エディタ

#### **Agent-01のファイルを開く:**

1. `📁 🔴 AGENT-01: CORE BACKUP ENGINE` の左の▶をクリックして展開
2. `app` → `core` → `backup_engine.py` をダブルクリック
3. エディタに `backup_engine.py` が開きます

#### **Agent-02のファイルを開く（同時に）:**

1. `📁 🔴 AGENT-02: STORAGE MANAGEMENT` を展開
2. `app` → `storage` → `interfaces.py` をダブルクリック
3. エディタに `interfaces.py` が開きます

#### **画面を分割:**

```
backup_engine.py が開いている状態で:
- 右クリック → "Split Right" または
- Ctrl+\ (バックスラッシュ)

結果:
┌───────────────────────┬───────────────────────┐
│ backup_engine.py      │ interfaces.py         │
│ (Agent-01)            │ (Agent-02)            │
│                       │                       │
│ # Agent-01のコード    │ # Agent-02のコード    │
│ class BackupEngine:   │ class IStorageProvider│
│   def execute...      │   def connect...      │
└───────────────────────┴───────────────────────┘
```

両方を見ながら編集できます！

---

### 方法2: ターミナル分割

#### **ターミナルを2分割:**

```
Terminal → Split Terminal (Ctrl+Shift+5)

または、ターミナルパネル右上の「分割」アイコンをクリック

結果:
┌──────────────────────┬──────────────────────┐
│ TERMINAL 1           │ TERMINAL 2           │
│ bash                 │ bash                 │
└──────────────────────┴──────────────────────┘
```

#### **各ターミナルで作業:**

**ターミナル1（Agent-01）:**
```bash
cd /mnt/Linux-ExHDD/worktrees/agent-01-core
pwd  # → agent-01-core
git status
# Agent-01の開発作業
```

**ターミナル2（Agent-02）:**
```bash
cd /mnt/Linux-ExHDD/worktrees/agent-02-storage
pwd  # → agent-02-storage
git status
# Agent-02の開発作業
```

---

### 方法3: Git管理（ソース管理パネル）

#### **左サイドバーのGitアイコン**をクリック

```
SOURCE CONTROL
  📁 Main Repository (develop)     0 changes
  📁 Agent-01: Core Backup Engine  3 changes  ← 展開すると変更ファイルリスト
  📁 Agent-02: Storage Management  1 change
  📁 Agent-03: ...                 0 changes
  ...
```

#### **各エージェントの変更を確認:**

Agent-01を展開:
```
📁 Agent-01: Core Backup Engine (3)
  ├─ M app/core/backup_engine.py      ← クリックでdiff表示
  ├─ A app/core/transaction_log.py    ← 新規ファイル
  └─ M tests/core/test_backup_engine.py
```

#### **コミット操作:**

1. 変更ファイルの右の**+ボタン**をクリック → ステージング
2. コミットメッセージ入力欄に入力:
```
[CORE-01] add: トランザクションログ実装
```
3. **✓ Commit**ボタンをクリック
4. **⬆ Sync Changes**でプッシュ

**Agent-02も同様に操作できます！**

---

## 🔧 実践例：Agent-01とAgent-02を同時開発

### 画面レイアウト例

```
┌─────────────────────────────────────────────────────────────────────┐
│ VSCode ウィンドウ                                                    │
├──────────────┬──────────────────────────────────────────────────────┤
│              │  エディタエリア                                       │
│ EXPLORER     ├──────────────────────┬──────────────────────────────┤
│              │ backup_engine.py     │ interfaces.py                │
│ 📁 Main      │ (Agent-01)           │ (Agent-02)                   │
│ 📁 Agent-01  │                      │                              │
│   ├─ app     │ class BackupEngine:  │ class IStorageProvider(ABC):│
│   │  └─ core │   def execute...     │   @abstractmethod           │
│ 📁 Agent-02  │                      │   def connect...            │
│   └─ app     │                      │                              │
│      └─ stor │                      │                              │
├──────────────┴──────────────────────┴──────────────────────────────┤
│ TERMINAL                                                            │
├─────────────────────────────┬───────────────────────────────────────┤
│ Terminal 1 (Agent-01)       │ Terminal 2 (Agent-02)                │
│ $ cd .../agent-01-core      │ $ cd .../agent-02-storage            │
│ $ git status                │ $ git add app/storage/               │
│ $ pytest tests/core/        │ $ git commit -m "[STORAGE-02]..."   │
└─────────────────────────────┴───────────────────────────────────────┘
```

---

## 💻 具体的な操作フロー

### 【シナリオ】Agent-01とAgent-02で並列開発

#### **9:00 - 開発開始**

**ターミナル1（Agent-01）:**
```bash
cd /mnt/Linux-ExHDD/worktrees/agent-01-core
echo "$(date): トランザクションログ実装開始" >> logs/agent-01/progress.md
```

**ターミナル2（Agent-02）:**
```bash
cd /mnt/Linux-ExHDD/worktrees/agent-02-storage
echo "$(date): IStorageProvider実装開始" >> logs/agent-02/progress.md
```

#### **9:30 - コード実装**

**エディタ左側（Agent-01）:**
```python
# app/core/transaction_log.py を新規作成
# エクスプローラーで右クリック → New File
# ファイル名: transaction_log.py
# コードを書く...
```

**エディタ右側（Agent-02）:**
```python
# app/storage/interfaces.py を編集
# IStorageProviderインターフェースを定義...
```

#### **10:00 - 最初のコミット**

**ターミナル1（Agent-01）:**
```bash
git add app/core/transaction_log.py
git commit -m "[CORE-01] add: transaction log implementation"
```

**ターミナル2（Agent-02）:**
```bash
git add app/storage/interfaces.py
git commit -m "[STORAGE-02] add: storage provider interface"
```

#### **12:00 - 午前の成果をプッシュ**

**ターミナル1:**
```bash
git push origin feature/backup-engine
```

**ターミナル2:**
```bash
git push origin feature/storage-management
```

#### **17:30 - 夕方のまとめ**

**統合ターミナルで全体確認:**
```bash
cd /mnt/Linux-ExHDD/backup-management-system
python scripts/orchestrator.py status
```

出力:
```
🟢 Agent-01: UP_TO_DATE (2 commits today)
🟢 Agent-02: UP_TO_DATE (3 commits today)
```

---

## 🎨 便利な機能

### 1. マルチカーソル編集

同じパターンのコードを複数箇所で書く場合:
```
Ctrl+D: 選択中の単語と同じ単語を次々選択
Alt+クリック: 任意の場所にカーソル追加
Ctrl+Shift+L: 選択中の単語の全出現箇所を選択
```

### 2. ファイル間ジャンプ

```
Ctrl+P: ファイルをクイック検索
  → "backup_engine" と入力 → Agent-01のファイルが見つかる
  → "interfaces" と入力 → Agent-02のファイルが見つかる
```

### 3. 定義へジャンプ

```
Agent-01のコード内で:
from app.storage.interfaces import IStorageProvider
                                   ↑
                           Ctrl+クリック → Agent-02のファイルへジャンプ！
```

### 4. エクスプローラーフィルター

```
エクスプローラー上部の検索ボックス:
"agent-01" → Agent-01のファイルのみ表示
"agent-02" → Agent-02のファイルのみ表示
```

---

## 🔄 Git操作（GUIで簡単）

### コミット手順

#### **ソース管理パネル（左サイドバーのGitアイコン）:**

1. **Agent-01の変更を確認:**
```
📁 Agent-01: Core Backup Engine (3)
  ├─ M backup_engine.py        ← クリックでdiff表示
  ├─ A transaction_log.py      ← 新規
  └─ M test_backup_engine.py

右側の + ボタンをクリック → ステージング完了
```

2. **コミットメッセージ入力:**
```
Agent-01の入力欄に:
[CORE-01] add: transaction log implementation
```

3. **✓ Commit ボタンをクリック**

4. **⬆ Sync Changes でプッシュ**

**Agent-02も同じ手順で独立してコミット可能！**

---

## 📊 進捗管理

### STATUS.mdの更新

```
エクスプローラーで:
📁 Main Repository → STATUS.md をダブルクリック

編集:
- [x] Agent-01: Core Backup Engine (30% → 50%)
- [ ] Agent-02: Storage Management (0% → 20%)

保存: Ctrl+S
```

### orchestratorで自動確認

```bash
# 統合ターミナルで（どのディレクトリからでもOK）
cd /mnt/Linux-ExHDD/backup-management-system
python scripts/orchestrator.py status
```

---

## 🎯 開発ワークフロー例

### 朝 (9:00)

```bash
# 統合ターミナルで全エージェント同期
cd /mnt/Linux-ExHDD/backup-management-system
python scripts/orchestrator.py sync

# 全体状況確認
python scripts/orchestrator.py status
```

### 開発中 (9:30-17:00)

**エディタ:**
- Agent-01とAgent-02のファイルを分割表示で編集

**ターミナル:**
- 各エージェントで定期的にコミット・プッシュ

### 夕方 (17:30)

**ターミナル1（Agent-01）:**
```bash
cd /mnt/Linux-ExHDD/worktrees/agent-01-core
pytest tests/core/ -v
git add .
git commit -m "[CORE-01] eod: Day X完了"
git push origin feature/backup-engine
```

**ターミナル2（Agent-02）:**
```bash
cd /mnt/Linux-ExHDD/worktrees/agent-02-storage
pytest tests/storage/ -v
git add .
git commit -m "[STORAGE-02] eod: Day X完了"
git push origin feature/storage-management
```

**統合ターミナル:**
```bash
cd /mnt/Linux-ExHDD/backup-management-system
python scripts/orchestrator.py status > daily_status_$(date +%Y%m%d).txt
```

---

## 🎨 Insight - Workspace並列開発の効率性

`★ Insight ─────────────────────────────────────`

**VSCode Workspaceで実現する3つの並列開発パターン:**

1. **水平分割開発**: エディタを左右に分割し、Agent-01とAgent-02のコードを同時に見ながら開発できます。インターフェース定義を見ながら実装する、といった相互参照が非常にスムーズです。

2. **垂直統合管理**: ターミナルを分割することで、上部でコード編集、下部で各エージェントのGit操作を並行実行できます。Agent-01でテストを実行しながら、Agent-02でコミットする、といった真の並列作業が可能です。

3. **コンテキストスイッチング最小化**: 9つのフォルダが1つのエクスプローラーに集約されているため、VSCodeウィンドウを切り替える必要がありません。Ctrl+Pでファイル検索すれば、全8エージェントのファイルを横断検索できます。

`─────────────────────────────────────────────────`

---

## 🚀 今すぐ実行可能

### Workspaceを開いて開発開始

1. **このVSCodeで Workspace を開く**
2. **Agent-01とAgent-02を展開**
3. **ターミナルを2分割**
4. **並列開発スタート！**

**CLI不要！すべてVSCode GUIで完結します！**

---

**作成日**: 2025-11-01
**対象**: 8エージェント並列開発チーム
