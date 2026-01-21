# 📚 ドキュメント構造マップ（更新版） - Documentation Map (Updated)

**最終更新**: 2025年11月2日
**総ドキュメント数**: 80+ファイル
**整理状況**: ✅ 完全整理済み

---

## 📋 目次

本ドキュメントは、3-2-1-1-0 Backup Management Systemの全ドキュメントの索引です。

---

## 📁 ドキュメント構造

```
docs/
├── 00_ドキュメント構造（documentation-map）.md
├── 00_ドキュメント構造_更新版（documentation-map-updated）.md ★ 本ファイル
├── 00_整理完了レポート（reorganization-report）.md
│
├── 01_要件・設計（requirements-design）/
│   ├── 要件定義書（requirements）.md
│   ├── 設計仕様書（design-spec）.md
│   ├── ISO_27001準拠（iso-27001-compliance）.md
│   └── ISO_19650準拠（iso-19650-compliance）.md
│
├── 02_セットアップ（setup）/
│   ├── クイックスタート（quickstart）.md
│   ├── インストールガイド（installation）.md
│   └── MCP設定ガイド（mcp-setup）.md
│
├── 03_開発（development）/
│   ├── 実装サマリー（implementation）/
│   ├── フェーズレポート（phase-reports）/
│   └── パフォーマンス（performance）/
│
├── 04_API（api）/
│   ├── API使用例（api-usage-examples）.md
│   ├── 認証実装（auth-implementation）.md
│   └── エンドポイント一覧（endpoints-list）.md
│
├── 05_デプロイメント（deployment）/
│   ├── デプロイガイド（deployment-guide）.md
│   ├── 本番運用マニュアル（production-operations）.md
│   └── Veeam統合ガイド（veeam-integration）.md
│
├── 06_パフォーマンス・監視（performance-monitoring）/
│   ├── パフォーマンス監視（performance-monitoring）.md
│   └── メトリクス（metrics）.md
│
├── 07_通知（notifications）/
│   ├── メール通知（email-notifications）.md
│   └── Teams統合（teams-integration）.md
│
├── 08_エラーハンドリング（error-handling）/
│   └── エラーハンドリング設計（error-handling-design）.md
│
├── 09_アーキテクチャ（architecture）/
│   └── アーキテクチャ概要（architecture-overview）.md
│
├── 10_実装完了レポート（implementation-reports）/ ★新規
│   ├── 実装完了レポート_2025（implementation-complete-2025）.md
│   ├── 開発状況（development-status）.md
│   ├── ステータス（status）.md
│   ├── PDF実装サマリー（pdf-implementation-summary）.md
│   ├── 検証機能実装サマリー（verification-implementation-summary）.md
│   └── フェーズ7デプロイ完了（phase7-deployment-complete）.md
│
├── 11_デプロイメントガイド（deployment-guides）/ ★新規
│   ├── 本番デプロイガイド（production-deployment-guide）.md
│   ├── Windowsクリーンインストールガイド（windows-clean-install-guide）.md
│   └── Windows本番環境移行（windows-production-migration）.md
│
├── 12_統合ガイド（integration-guides）/ ★新規
│   ├── AOMEI統合ガイド（aomei-integration）.md
│   ├── AOMEIクイックスタート（aomei-quickstart）.md
│   ├── AOMEI実装サマリー（aomei-implementation-summary）.md
│   ├── PDFレポートガイド（pdf-report-guide）.md
│   ├── PDF生成ガイド（pdf-generation-guide）.md
│   └── 検証サービスガイド（verification-service-guide）.md
│
└── 13_開発環境（development-environment）/ ★新規
    ├── 開発環境ガイド（development-environment-guide）.md
    ├── エージェントシステムセットアップ（agent-system-setup）.md
    ├── エージェント説明（agent-readme）.md
    ├── VSCodeワークスペースガイド（vscode-workspace-guide）.md
    ├── Git並列開発（git-worktree-parallel-dev）.md
    ├── Brave検索セットアップ（brave-search-setup）.md
    ├── GitHubトークンセットアップ（github-token-setup）.md
    ├── 自動修復システム（auto-repair-system）.md
    ├── Serena_MCP修正（serena-mcp-fix）.md
    └── Serena正しいセットアップ（serena-correct-setup）.md
```

---

## 🎯 カテゴリー別ドキュメント一覧

### 01. 要件・設計 (Requirements & Design)

| ファイル名 | 説明 | サイズ |
|-----------|------|--------|
| [要件定義書（requirements）.md](01_要件・設計（requirements-design）/要件定義書（requirements）.md) | システム要件定義 | 15KB |
| [設計仕様書（design-spec）.md](01_要件・設計（requirements-design）/設計仕様書（design-spec）.md) | 詳細設計仕様 | 20KB |
| [ISO_27001準拠（iso-27001-compliance）.md](01_要件・設計（requirements-design）/ISO_27001準拠（iso-27001-compliance）.md) | 情報セキュリティマネジメント | 3KB |
| [ISO_19650準拠（iso-19650-compliance）.md](01_要件・設計（requirements-design）/ISO_19650準拠（iso-19650-compliance）.md) | 情報管理・BIM | 3KB |

---

### 02. セットアップ (Setup)

| ファイル名 | 説明 | サイズ |
|-----------|------|--------|
| [クイックスタート（quickstart）.md](02_セットアップ（setup）/クイックスタート（quickstart）.md) | 5分で起動 | 8KB |
| [インストールガイド（installation）.md](02_セットアップ（setup）/インストールガイド（installation）.md) | 詳細インストール | 12KB |
| [MCP設定ガイド（mcp-setup）.md](02_セットアップ（setup）/MCP設定ガイド（mcp-setup）.md) | MCP統合設定 | 10KB |

---

### 10. 実装完了レポート (Implementation Reports) ★新規

| ファイル名 | 説明 | サイズ |
|-----------|------|--------|
| [実装完了レポート_2025（implementation-complete-2025）.md](10_実装完了レポート（implementation-reports）/実装完了レポート_2025（implementation-complete-2025）.md) | **最新実装完了レポート** | 8KB |
| [開発状況（development-status）.md](10_実装完了レポート（implementation-reports）/開発状況（development-status）.md) | 開発進捗状況 | 12KB |
| [ステータス（status）.md](10_実装完了レポート（implementation-reports）/ステータス（status）.md) | プロジェクトステータス | 4KB |
| [PDF実装サマリー（pdf-implementation-summary）.md](10_実装完了レポート（implementation-reports）/PDF実装サマリー（pdf-implementation-summary）.md) | PDF生成機能実装 | 6KB |
| [検証機能実装サマリー（verification-implementation-summary）.md](10_実装完了レポート（implementation-reports）/検証機能実装サマリー（verification-implementation-summary）.md) | 検証機能実装 | 5KB |
| [フェーズ7デプロイ完了（phase7-deployment-complete）.md](10_実装完了レポート（implementation-reports）/フェーズ7デプロイ完了（phase7-deployment-complete）.md) | フェーズ7レポート | 18KB |

---

### 11. デプロイメントガイド (Deployment Guides) ★新規

| ファイル名 | 説明 | サイズ |
|-----------|------|--------|
| [本番デプロイガイド（production-deployment-guide）.md](11_デプロイメントガイド（deployment-guides）/本番デプロイガイド（production-deployment-guide）.md) | **完全デプロイ手順** | 25KB |
| [Windowsクリーンインストールガイド（windows-clean-install-guide）.md](11_デプロイメントガイド（deployment-guides）/Windowsクリーンインストールガイド（windows-clean-install-guide）.md) | Windows新規インストール | 12KB |
| [Windows本番環境移行（windows-production-migration）.md](11_デプロイメントガイド（deployment-guides）/Windows本番環境移行（windows-production-migration）.md) | 本番環境移行 | 14KB |

---

### 12. 統合ガイド (Integration Guides) ★新規

| ファイル名 | 説明 | サイズ |
|-----------|------|--------|
| [AOMEI統合ガイド（aomei-integration）.md](12_統合ガイド（integration-guides）/AOMEI統合ガイド（aomei-integration）.md) | **AOMEI完全統合** | 11KB |
| [AOMEIクイックスタート（aomei-quickstart）.md](12_統合ガイド（integration-guides）/AOMEIクイックスタート（aomei-quickstart）.md) | AOMEI即座使用 | 8KB |
| [AOMEI実装サマリー（aomei-implementation-summary）.md](12_統合ガイド（integration-guides）/AOMEI実装サマリー（aomei-implementation-summary）.md) | AOMEI実装詳細 | 8KB |
| [PDFレポートガイド（pdf-report-guide）.md](12_統合ガイド（integration-guides）/PDFレポートガイド（pdf-report-guide）.md) | PDF機能使用法 | 7KB |
| [PDF生成ガイド（pdf-generation-guide）.md](12_統合ガイド（integration-guides）/PDF生成ガイド（pdf-generation-guide）.md) | PDF生成詳細 | 12KB |
| [検証サービスガイド（verification-service-guide）.md](12_統合ガイド（integration-guides）/検証サービスガイド（verification-service-guide）.md) | 検証機能ガイド | 80KB |

---

### 13. 開発環境 (Development Environment) ★新規

| ファイル名 | 説明 | サイズ |
|-----------|------|--------|
| [開発環境ガイド（development-environment-guide）.md](13_開発環境（development-environment）/開発環境ガイド（development-environment-guide）.md) | 開発環境セットアップ | 9KB |
| [エージェントシステムセットアップ（agent-system-setup）.md](13_開発環境（development-environment）/エージェントシステムセットアップ（agent-system-setup）.md) | Agent統合 | 7KB |
| [エージェント説明（agent-readme）.md](13_開発環境（development-environment）/エージェント説明（agent-readme）.md) | Agentの説明 | 12KB |
| [VSCodeワークスペースガイド（vscode-workspace-guide）.md](13_開発環境（development-environment）/VSCodeワークスペースガイド（vscode-workspace-guide）.md) | VSCode設定 | 14KB |
| [Git並列開発（git-worktree-parallel-dev）.md](13_開発環境（development-environment）/Git並列開発（git-worktree-parallel-dev）.md) | Git並列開発 | 3KB |
| [Brave検索セットアップ（brave-search-setup）.md](13_開発環境（development-environment）/Brave検索セットアップ（brave-search-setup）.md) | Brave MCP | 10KB |
| [GitHubトークンセットアップ（github-token-setup）.md](13_開発環境（development-environment）/GitHubトークンセットアップ（github-token-setup）.md) | GitHub設定 | 7KB |
| [自動修復システム（auto-repair-system）.md](13_開発環境（development-environment）/自動修復システム（auto-repair-system）.md) | 自動修復 | 15KB |
| [Serena_MCP修正（serena-mcp-fix）.md](13_開発環境（development-environment）/Serena_MCP修正（serena-mcp-fix）.md) | Serena修正 | 6KB |
| [Serena正しいセットアップ（serena-correct-setup）.md](13_開発環境（development-environment）/Serena正しいセットアップ（serena-correct-setup）.md) | Serena設定 | 9KB |

---

## 🚀 クイックナビゲーション

### 🎯 初めての方
1. [README.md](../README.md) - プロジェクト概要
2. [クイックスタート（quickstart）.md](02_セットアップ（setup）/クイックスタート（quickstart）.md) - 5分で起動
3. [インストールガイド（installation）.md](02_セットアップ（setup）/インストールガイド（installation）.md) - 詳細手順

### 💻 開発者向け
1. [開発環境ガイド（development-environment-guide）.md](13_開発環境（development-environment）/開発環境ガイド（development-environment-guide）.md)
2. [VSCodeワークスペースガイド（vscode-workspace-guide）.md](13_開発環境（development-environment）/VSCodeワークスペースガイド（vscode-workspace-guide）.md)
3. [エージェント説明（agent-readme）.md](13_開発環境（development-environment）/エージェント説明（agent-readme）.md)

### 🚀 デプロイ担当者
1. [本番デプロイガイド（production-deployment-guide）.md](11_デプロイメントガイド（deployment-guides）/本番デプロイガイド（production-deployment-guide）.md) - **最重要**
2. [Windows本番環境移行（windows-production-migration）.md](11_デプロイメントガイド（deployment-guides）/Windows本番環境移行（windows-production-migration）.md)
3. [本番運用マニュアル（production-operations）.md](05_デプロイメント（deployment）/本番運用マニュアル（production-operations）.md)

### 🔌 統合担当者
1. [AOMEI統合ガイド（aomei-integration）.md](12_統合ガイド（integration-guides）/AOMEI統合ガイド（aomei-integration）.md) - **AOMEI完全統合**
2. [AOMEIクイックスタート（aomei-quickstart）.md](12_統合ガイド（integration-guides）/AOMEIクイックスタート（aomei-quickstart）.md)
3. [検証サービスガイド（verification-service-guide）.md](12_統合ガイド（integration-guides）/検証サービスガイド（verification-service-guide）.md)

### 📊 レポート確認
1. [実装完了レポート_2025（implementation-complete-2025）.md](10_実装完了レポート（implementation-reports）/実装完了レポート_2025（implementation-complete-2025）.md) - **最新**
2. [開発状況（development-status）.md](10_実装完了レポート（implementation-reports）/開発状況（development-status）.md)

---

## 📝 ドキュメント命名規則

### 基本ルール
- **フォーマット**: `日本語名（英語名）.md`
- **例**: `本番デプロイガイド（production-deployment-guide）.md`

### フォルダ命名規則
- **フォーマット**: `番号_日本語名（英語名）/`
- **例**: `11_デプロイメントガイド（deployment-guides）/`

---

## 🔄 最近の変更 (2025-11-02)

### 新規追加
- ✅ `10_実装完了レポート（implementation-reports）/` フォルダ作成
- ✅ `11_デプロイメントガイド（deployment-guides）/` フォルダ作成
- ✅ `12_統合ガイド（integration-guides）/` フォルダ作成
- ✅ `13_開発環境（development-environment）/` フォルダ作成

### 移動・整理
- ✅ ルート直下のドキュメントを適切なフォルダに移動
- ✅ ファイル名を「日本語名（英語名）」形式に統一
- ✅ カテゴリー別に整理

---

## 📊 統計情報

- **総ドキュメント数**: 80+ファイル
- **カテゴリー数**: 13カテゴリー
- **総文字数**: 約500,000文字
- **言語**: 日本語・英語

---

## 🙏 貢献者

- **開発**: Kensan196948G
- **AI支援**: Claude AI (Anthropic)
- **ドキュメント整理**: 2025年11月2日完了

---

**最終更新**: 2025年11月2日
**バージョン**: 2.0
