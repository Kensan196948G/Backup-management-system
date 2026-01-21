# 3-2-1-1-0 Backup Management System - プロジェクト概要

## プロジェクト基本情報

**プロジェクト名**: 3-2-1-1-0 Backup Management System  
**種別**: 企業向けバックアップ管理・監視システム  
**言語**: Python 3.11+  
**主要フレームワーク**: Flask 3.0+  
**データベース**: SQLite (開発) / PostgreSQL (本番)  
**開発OS**: Linux (Ubuntu 22.04/24.04 LTS)  
**本番OS**: Windows 11 Enterprise  

## アーキテクチャ

### データベースモデル (16モデル)
1. User - ユーザー管理
2. BackupJob - バックアップジョブ
3. BackupCopy - バックアップコピー
4. OfflineMedia - オフラインメディア
5. MediaRotationSchedule - メディアローテーション
6. MediaLending - メディア貸出
7. VerificationTest - 検証テスト
8. VerificationSchedule - 検証スケジュール
9. BackupExecution - バックアップ実行
10. ComplianceStatus - コンプライアンス状態
11. Alert - アラート
12. AuditLog - 監査ログ
13. Report - レポート
14. SystemSetting - システム設定
15. NotificationLog - 通知ログ
16. BackupCopy - バックアップコピー

### アプリケーション構造
- app/api/ - REST API エンドポイント (v1含む)
- app/auth/ - 認証・認可
- app/services/ - ビジネスロジック (5サービス)
- app/scheduler/ - スケジュールタスク
- app/views/ - ビューコントローラー
- app/templates/ - HTMLテンプレート
- app/static/ - 静的ファイル
- app/utils/ - ユーティリティ

### 主要サービス
1. alert_manager.py - アラート管理
2. compliance_checker.py - コンプライアンスチェック
3. notification_service.py - 通知サービス
4. report_generator.py - レポート生成
5. teams_notification_service.py - Teams通知

## 開発手法

### AI支援開発
- Claude Code + MCP（Model Context Protocol）
- 10体のサブエージェントによる並列開発
- 8つのMCPサーバー統合

### エージェント構成
1. Agent-01: Core Backup Engine
2. Agent-02: Storage Management
3. Agent-03: Verification & Validation
4. Agent-04: Scheduler & Job Manager
5. Agent-05: Alert & Notification
6. Agent-06: Web UI & Dashboard
7. Agent-07: API & Integration Layer
8. Agent-08: Documentation & Compliance

## 対応バックアップツール
1. Veeam Backup & Replication - PowerShell統合
2. Windows Server Backup - タスクスケジューラー連携
3. AOMEI Backupper - ログ監視・解析

## コンプライアンス
- ISO 27001準拠
- ISO 19650準拠 (BIM)
- GDPR対応

## ファイル統計
- 総Pythonファイル数: 5,280ファイル
- ドキュメント: 72ファイル（整理済み）
- テンプレート: 複数（dashboard, jobs, media, verification, reports等）
