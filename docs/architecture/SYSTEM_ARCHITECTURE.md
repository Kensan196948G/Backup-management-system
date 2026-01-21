# システムアーキテクチャ - 3-2-1-1-0バックアップ管理システム

## 8エージェント構成

```
┌─────────────────────────────────────────────────────────────┐
│                    3-2-1-1-0 Backup System                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Agent-01: Core Backup Engine                               │
│  ├─ BackupEngine (実行エンジン)                             │
│  ├─ Rule321110Validator (ルール検証)                        │
│  └─ TransactionLog (トランザクションログ)                   │
│           ↓                                                  │
│  Agent-02: Storage Management                               │
│  ├─ IStorageProvider (抽象インターフェース)                 │
│  ├─ LocalStorage / NAS / S3 / Tape (実装)                   │
│  └─ StorageRegistry (レジストリ)                            │
│           ↓                                                  │
│  Agent-03: Verification & Validation                        │
│  ├─ ChecksumService (チェックサム計算)                      │
│  ├─ FileValidator (整合性検証)                              │
│  └─ RestoreTest (リストアテスト)                            │
│           ↓                                                  │
│  Agent-04: Scheduler & Job Manager                          │
│  ├─ CronScheduler (スケジューラー)                          │
│  ├─ JobQueue (優先度キュー)                                 │
│  └─ JobExecutor (並列実行制御)                              │
│           ↓                                                  │
│  Agent-05: Alert & Notification                             │
│  ├─ AlertEngine (アラートエンジン)                          │
│  ├─ Email/Slack/Teams (通知チャネル)                        │
│  └─ SLAMonitor (SLA監視)                                    │
│           ↓                                                  │
│  Agent-06: Web UI & Dashboard                               │
│  ├─ Dashboard (ダッシュボード)                              │
│  ├─ Schedule UI (スケジュール設定)                          │
│  └─ Storage Config (ストレージ設定)                         │
│           ↓                                                  │
│  Agent-07: API & Integration Layer                          │
│  ├─ REST API (バックアップ/ストレージ/検証)                 │
│  ├─ JWT認証 (セキュリティ)                                  │
│  └─ Webhooks (外部連携)                                     │
│           ↓                                                  │
│  Agent-08: Documentation & Compliance                       │
│  ├─ ユーザーマニュアル                                       │
│  ├─ API リファレンス                                        │
│  └─ ISO準拠レポート                                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 技術スタック

- **バックエンド**: Python 3.11+, Flask 2.3+
- **データベース**: SQLAlchemy 2.0+, SQLite/PostgreSQL
- **フロントエンド**: Bootstrap 5.3, Chart.js 4.4, DataTables
- **API**: RESTful, JWT認証, Pydantic検証
- **スケジューリング**: APScheduler, Cron式
- **通知**: SMTP, Slack/Teams Webhook
- **検証**: SHA-256/512, BLAKE2
- **並列開発**: Git Worktree, 8エージェント構成

## ISO準拠

- **ISO 27001**: A.12.3, A.12.4, A.9
- **ISO 19650**: BIM情報管理、CDE構造
