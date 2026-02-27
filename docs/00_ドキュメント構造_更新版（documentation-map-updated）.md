# ドキュメント構造マップ（最終更新版）

**最終更新日:** 2026-02-25
**バージョン:** 3.0.0
**総ドキュメント数:** 100+ ファイル
**整理状況:** 完全整理済み

---

## ドキュメント全体構成

```
docs/
├── 00_ドキュメント構造_更新版（documentation-map-updated）.md  ← 本ファイル
├── 00_ドキュメント構造（documentation-map）.md
├── 00_整理完了レポート（reorganization-report）.md
│
├── 01_要件・設計（requirements-design）/
│   ├── 要件定義書（requirements）.md
│   ├── 設計仕様書（design-spec）.md
│   ├── ISO_19650準拠（iso-19650-compliance）.md
│   └── ISO_27001準拠（iso-27001-compliance）.md
│
├── 02_セットアップ（setup）/
│   ├── クイックスタート（quickstart）.md
│   ├── インストールガイド（installation）.md
│   ├── 環境変数ガイド（environment-variables）.md
│   ├── カスタムコマンド（custom-commands）.md
│   ├── QUICKSTART_UI_ENHANCEMENTS.md              ← 2026-02-25 移動
│   └── MCP設定/
│       └── (...MCP関連ファイル群...)
│
├── 03_開発（development）/
│   ├── 実装サマリー（implementation）/
│   │   ├── 実装サマリー（implementation-summary）.md
│   │   ├── 実装完了（implementation-complete）.md
│   │   ├── WebUI（web-ui）.md
│   │   ├── Webビュー（web-views）.md
│   │   ├── アプリケーション構造（application-structure）.md
│   │   ├── アプリ初期化（app-initialization）.md
│   │   ├── ビジネスサービス（business-services）.md
│   │   ├── ビジネスロジック（business-logic）.md
│   │   ├── テスト実装（test-implementation）.md
│   │   └── ui-components-guide.md                 ← 2026-02-25 移動
│   ├── テストレポート（test-reports）/
│   │   └── (...テストレポート群...)
│   └── フェーズレポート（phase-reports）/
│       └── (...フェーズレポート群...)
│
├── 04_API（api）/
│   ├── API使用例（api-usage-examples）.md
│   ├── API実装サマリー（api-implementation）.md
│   ├── RESTAPIチェックリスト（rest-api-checklist）.md
│   └── 認証実装（auth-implementation）.md
│
├── 05_デプロイメント（deployment）/
│   ├── デプロイガイド（deployment-guide）.md
│   ├── デプロイアーキテクチャ（deployment-architecture）.md
│   ├── デプロイ実装レポート（deployment-implementation）.md
│   ├── デプロイ構造（deployment-structure）.md
│   ├── 本番運用マニュアル（production-operations）.md
│   └── Veeam統合ガイド（veeam-integration）.md
│
├── 06_パフォーマンス・監視（performance-monitoring）/
│   ├── パフォーマンスチューニング（performance-tuning）.md
│   ├── パフォーマンステストレポート（performance-test-report）.md
│   └── フェーズ10サマリー（phase10-summary）.md
│
├── 07_通知（notifications）/
│   ├── フェーズ8.1 Email通知（phase8-1-email）.md
│   ├── フェーズ8.1実装サマリー（phase8-1-implementation）.md
│   └── フェーズ8.2 Teams通知完了（phase8-2-teams）.md
│
├── 08_エラーハンドリング（error-handling）/
│   ├── エラーハンドリング実装（implementation）.md
│   ├── エラーハンドリング分析（analysis）.md
│   ├── エラーハンドリングサマリー（summary）.md
│   ├── QAレポート（qa-report）.md
│   ├── テストレポート（test-report）.md
│   ├── テスト結果（test-results）.md
│   ├── クイックスタート（quickstart）.md
│   └── ファイル一覧（files-manifest）.md
│
├── 09_アーキテクチャ（architecture）/
│   ├── アーキテクチャ概要（architecture-overview）.md
│   └── SYSTEM_ARCHITECTURE.md                     ← 2026-02-25 移動
│
├── 10_実装完了レポート（implementation-reports）/
│   ├── 実装完了レポート_2025（implementation-complete-2025）.md
│   ├── 実装完了レポート_v1（implementation-complete-v1）.md
│   ├── PDF実装サマリー（pdf-implementation-summary）.md
│   ├── 検証機能実装サマリー（verification-implementation-summary）.md
│   ├── フェーズ7デプロイ完了（phase7-deployment-complete）.md
│   ├── ステータス（status）.md
│   └── 開発状況（development-status）.md
│
├── 11_デプロイメントガイド（deployment-guides）/
│   ├── 本番デプロイガイド（production-deployment-guide）.md
│   ├── Windowsクリーンインストールガイド（windows-clean-install-guide）.md
│   └── Windows本番環境移行（windows-production-migration）.md
│
├── 12_統合ガイド（integration-guides）/
│   ├── AOMEI統合ガイド（aomei-integration）.md
│   ├── AOMEIクイックスタート（aomei-quickstart）.md
│   ├── AOMEI実装サマリー（aomei-implementation-summary）.md
│   ├── PDFレポートガイド（pdf-report-guide）.md
│   ├── PDF生成ガイド（pdf-generation-guide）.md
│   └── 検証サービスガイド（verification-service-guide）.md
│
├── 13_開発環境（development-environment）/
│   ├── 開発環境ガイド（development-environment-guide）.md
│   ├── VSCodeワークスペースガイド（vscode-workspace-guide）.md
│   ├── Git並列開発（git-worktree-parallel-dev）.md
│   ├── GitHubトークンセットアップ（github-token-setup）.md
│   ├── Brave検索セットアップ（brave-search-setup）.md
│   ├── Serena_MCP修正（serena-mcp-fix）.md
│   ├── Serena正しいセットアップ（serena-correct-setup）.md
│   ├── エージェントシステムセットアップ（agent-system-setup）.md
│   ├── エージェント説明（agent-readme）.md
│   ├── 自動修復システム（auto-repair-system）.md
│   └── AUTO_REPAIR_SYSTEM.md                      ← 2026-02-25 移動
│
├── 14_開発ロードマップ（development-roadmap）/
│   ├── 開発ロードマップ_Phase11-14（roadmap-phase11-14）.md
│   ├── Phase11_非同期処理実装（phase11-async-implementation）.md
│   ├── Phase12_データベース強化準備（phase12-database-preparation）.md
│   ├── Phase12_完了レポート.md                     ← 2026-02-25 統合
│   ├── Phase13_PostgreSQL最適化・監視.md            ← 2026-02-25 統合
│   └── システム開発完全ガイド_Phase14更新版.md       ← 2026-02-25 移動
│
├── agent-communication/                            ← エージェント間通信ファイル
│   ├── dependency_resolver.py
│   └── project-state.json
│
└── webui-sample-docs/                              ★ 2026-02-25 新規作成
    ├── 00_INDEX.md                                   インデックス
    ├── 01_要件定義書.md                               機能・非機能要件
    ├── 02_機能仕様書.md                               各機能詳細仕様
    ├── 03_UI_UX設計書.md                              デザイン・配色・タイポグラフィ
    ├── 04_画面設計書.md                               画面レイアウト・遷移図
    ├── 05_コンポーネント仕様書.md                      UIコンポーネント仕様
    ├── 06_アーキテクチャ設計書.md                      システム構成・技術スタック
    ├── 07_API仕様書.md                               REST APIエンドポイント
    ├── 08_データベース設計書.md                        DBスキーマ・テーブル定義
    ├── 09_認証・認可設計書.md                          JWT認証・RBACフロー
    ├── 10_セキュリティ仕様書.md                        OWASP対策・セキュリティ設計
    ├── 11_テスト仕様書.md                             テスト計画・ケース
    ├── 12_パフォーマンス要件書.md                      性能要件・最適化方針
    ├── 13_アクセシビリティ仕様書.md                    WCAG 2.1 AA対応
    ├── 14_エラーハンドリング仕様書.md                  エラーコード・ハンドリング設計
    ├── 15_国際化・ローカライズ仕様書.md                i18n / L10n 対応
    ├── 16_デプロイメント仕様書.md                      環境構成・CI/CD
    ├── 17_運用・保守マニュアル.md                      日常運用・障害対応
    ├── 18_変更管理仕様書.md                           変更管理プロセス
    └── 19_用語集.md                                  用語・略語一覧
```

---

## 2026-02-25 変更サマリー

### 追加
- `webui-sample-docs/` フォルダを新規作成（サンプルWebUI仕様書 19 ファイル）

### 整理（docs直下のファイルをサブフォルダへ移動）

| 移動前（docs直下） | 移動先 |
|-----------------|--------|
| `AUTO_REPAIR_SYSTEM.md` | `13_開発環境（development-environment）/` |
| `QUICKSTART_UI_ENHANCEMENTS.md` | `02_セットアップ（setup）/` |
| `ui-components-guide.md` | `03_開発（development）/実装サマリー（implementation）/` |
| `システム開発完全ガイド_Phase14更新版.md` | `14_開発ロードマップ（development-roadmap）/` |
| `architecture/SYSTEM_ARCHITECTURE.md` | `09_アーキテクチャ（architecture）/` |

### 統合・削除
- `14_開発ロードマップ/`（重複）の内容を `14_開発ロードマップ（development-roadmap）/` に統合後、空フォルダを削除
- 空フォルダ `architecture/` を削除

---

## 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-02-25 | 3.0.0 | webui-sample-docs追加・docs直下ファイル整理・重複フォルダ統合 |
| 2025-11-02 | 2.0.0 | フォルダ構造の再編・80+ファイルの整理 |
| 2025-xx-xx | 1.0.0 | 初版作成 |
