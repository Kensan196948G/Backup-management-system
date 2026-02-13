# 🤖 Claude Code 自動修復ループシステム

**バージョン**: 3.0  
**ステータス**: ✅ 実装完了・運用可能

---

## 🚀 これは何？

Claude Code による **自己収束型レビュー・自動修復システム** です。

### 特徴

- ✅ **自動レビュー**: バグ、セキュリティ、パフォーマンス、設計、可読性を自動チェック
- ✅ **自動修復**: 軽微な問題を自動的に修正
- ✅ **安全設計**: 最大3回で停止、無限ループなし
- ✅ **ローカル & CI**: ローカル開発とCI/CD両対応
- ✅ **人間優先**: 重大な問題は人間が判断

---

## 📦 クイックスタート

### 1. 前提条件

```bash
jq --version        # JSON処理ツール
git --version       # Git
python3 --version   # Python 3.11以降
```

### 2. テスト実行

```bash
python3 test_auto_repair_system.py
```

### 3. 使用開始

- **ローカル**: Claude Codeの "Stop" ボタンを押す
- **CI/CD**: PRを作成すると自動実行

---

## 📚 ドキュメント

- [クイックスタートガイド](docs/13_開発環境（development-environment）/claude-auto-repair-quickstart.md) - 5分で始める
- [完全版技術ガイド](docs/13_開発環境（development-environment）/claude-auto-repair-v3.md) - 詳細情報
- [実装完了レポート](docs/10_実装完了レポート（implementation-reports）/claude-auto-repair-implementation.md) - 実装内容

---

## 📂 ファイル構成

```
├── CLAUDE.md                          # ポリシー定義
├── state.json                         # 状態管理
├── .claude/
│   ├── settings.json                  # Hook設定
│   └── commands/
│       ├── review-all.md              # レビューコマンド
│       └── auto-fix.md                # 修復コマンド
├── scripts/
│   └── local-auto-repair.sh           # ローカル制御
└── .github/workflows/
    └── claude-auto-repair-loop.yml    # CI制御
```

---

## 💡 主な機能

- **包括レビュー**: 5つの観点で自動チェック
- **自動修復**: 軽微な問題を自動修正
- **安全性保証**: 無限ループ防止

詳細は[完全版ガイド](docs/13_開発環境（development-environment）/claude-auto-repair-v3.md)を参照。

---

**Happy Coding with Claude! 🚀**
