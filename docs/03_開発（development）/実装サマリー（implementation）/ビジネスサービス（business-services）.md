# ビジネスロジックサービス実装ガイド

## 概要

バックアップ管理システムのビジネスロジックサービスレイヤーが実装されました。このドキュメントは、実装されたサービスの使用方法と構成を説明します。

## 実装ファイル

### 1. データモデル
- **ファイル**: `/mnt/Linux-ExHDD/backup-management-system/app/models.py`
- **説明**: SQLAlchemy ORM モデル定義
- **主要クラス**:
  - User: ユーザー認証・認可
  - BackupJob: バックアップジョブ設定
  - BackupCopy: バックアップコピー（3-2-1-1-0の実体）
  - ComplianceStatus: 準拠状況キャッシュ
  - Alert: アラート管理
  - BackupExecution: 実行履歴
  - VerificationTest: 検証テスト
  - AuditLog: 監査ログ
  - Report: レポート管理

### 2. ビジネスロジックサービス

#### 2.1 ComplianceChecker
- **ファイル**: `/mnt/Linux-ExHDD/backup-management-system/app/services/compliance_checker.py`
- **目的**: 3-2-1-1-0 バックアップルール準拠チェック
- **主要メソッド**:
  - `check_3_2_1_1_0(job_id)`: 単一ジョブの準拠性チェック
  - `check_all_jobs()`: 全アクティブジョブの一括チェック
  - `get_compliance_history(job_id, days)`: 準拠状況の履歴取得

**3-2-1-1-0 ルール**:
- 3: 最低 3 つのバックアップコピー
- 2: 最低 2 種類の異なるメディアタイプ
- 1: 1 つはオフサイト（geographic distributed）
- 1: 1 つはオフライン（ネットワークから切断）
- 0: オリジナルソースにはコピーなし

**使用例**:
```python
from app.services import ComplianceChecker

checker = ComplianceChecker()

# 単一ジョブの確認
result = checker.check_3_2_1_1_0(job_id=1)
print(f"準拠状況: {result['status']}")
print(f"違反: {result['violations']}")
print(f"警告: {result['warnings']}")

# 全ジョブの確認
summary = checker.check_all_jobs()
print(f"準拠率: {summary['compliance_rate']}%")
```

#### 2.2 AlertManager
- **ファイル**: `/mnt/Linux-ExHDD/backup-management-system/app/services/alert_manager.py`
- **目的**: アラート生成・通知・管理
- **主要メソッド**:
  - `create_alert(alert_type, severity, title, message, job_id, notify)`: アラート作成
  - `send_notifications(alert)`: 通知送信（メール、Teams等）
  - `acknowledge_alert(alert_id, user_id)`: アラート確認
  - `get_unacknowledged_alerts(limit)`: 未確認アラート取得
  - `get_alerts_by_job(job_id, days, limit)`: ジョブのアラート取得

**サポートされる通知チャネル**:
- ダッシュボード（常に有効）
- メール通知（SMTP設定で有効化）
- Microsoft Teams（Webhook URL設定で有効化）

**アラートタイプ**:
- `BACKUP_FAILED`: バックアップ失敗
- `BACKUP_SUCCESS`: バックアップ成功
- `RULE_VIOLATION`: ルール違反
- `COMPLIANCE_WARNING`: 準拠警告
- `OFFLINE_MEDIA_UPDATE_WARNING`: オフラインメディア更新遅延
- `VERIFICATION_REMINDER`: 検証テストリマインダー
- `MEDIA_ROTATION_REMINDER`: メディアローテーションリマインダー
- `MEDIA_OVERDUE_RETURN`: メディア返却遅延
- `SYSTEM_ERROR`: システムエラー

**重要度**:
- `INFO`: 情報
- `WARNING`: 警告
- `ERROR`: エラー
- `CRITICAL`: クリティカル

**使用例**:
```python
from app.services import AlertManager
from app.services.alert_manager import AlertType, AlertSeverity

manager = AlertManager()

# アラート作成と通知
alert = manager.create_alert(
    alert_type=AlertType.BACKUP_FAILED,
    severity=AlertSeverity.ERROR,
    title="Database Backup Failed",
    message="Database backup job 'Daily DB' failed with network timeout",
    job_id=1,
    notify=True  # 通知を送信
)

# 未確認アラートを取得
unack_alerts = manager.get_unacknowledged_alerts(limit=50)

# アラートを確認
manager.acknowledge_alert(alert_id=1, user_id=user_id)
```

#### 2.3 ReportGenerator
- **ファイル**: `/mnt/Linux-ExHDD/backup-management-system/app/services/report_generator.py`
- **目的**: レポート生成（HTML/PDF/CSV）
- **主要メソッド**:
  - `generate_daily_report(generated_by, date, format)`: 日次レポート
  - `generate_weekly_report(generated_by, end_date, format)`: 週次レポート
  - `generate_monthly_report(generated_by, year, month, format)`: 月次レポート
  - `generate_compliance_report(generated_by, end_date, format)`: 準拠状況レポート
  - `generate_audit_report(generated_by, start_date, end_date, format)`: 監査ログレポート
  - `cleanup_old_reports(days)`: 古いレポート削除

**出力形式**:
- **HTML**: インタラクティブで視認性が高い
- **PDF**: 印刷・配布用（スタブ実装）
- **CSV**: データエクスポート・Excel互換

**レポート種別**:
- `daily`: 日次バックアップ状況
- `weekly`: 週次サマリー
- `monthly`: 月次パフォーマンス・準拠状況
- `compliance`: 3-2-1-1-0 準拠分析
- `audit`: 監査ログ

**使用例**:
```python
from app.services import ReportGenerator
from datetime import datetime

generator = ReportGenerator()

# 日次レポート生成（HTML形式）
daily_report = generator.generate_daily_report(
    generated_by=user_id,
    date=datetime.utcnow(),
    format='html'
)
print(f"生成されたレポート: {daily_report.file_path}")

# 準拠状況レポート生成（CSV形式）
compliance_report = generator.generate_compliance_report(
    generated_by=user_id,
    format='csv'
)

# 古いレポートをクリーンアップ（90日以上前）
deleted_count = generator.cleanup_old_reports(days=90)
```

## サービスの初期化

Flask アプリケーションで使用するには：

```python
from flask import Flask
from app.models import db
from app.config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# サービスの使用
with app.app_context():
    from app.services import ComplianceChecker, AlertManager, ReportGenerator

    checker = ComplianceChecker()
    manager = AlertManager()
    generator = ReportGenerator()
```

## データベーススキーマ

### 主要テーブル

**backup_jobs**
- id (PK)
- job_name: ジョブ名
- job_type: 種別（system_image/file/database/vm）
- target_server: 対象サーバー
- backup_tool: バックアップツール（veeam/wsb/aomei）
- schedule_type: スケジュール（daily/weekly/monthly）
- retention_days: 保持期間
- owner_id (FK users): 担当者
- is_active: 有効フラグ

**backup_copies**
- id (PK)
- job_id (FK backup_jobs): ジョブID
- copy_type: コピー種別（primary/secondary/offsite/offline）
- media_type: メディア種別（disk/tape/cloud/external_hdd）
- storage_path: 保存先
- status: 状態（success/failed/warning/unknown）
- last_backup_date: 最終バックアップ日時
- offline_media_id (FK offline_media): オフラインメディアID

**compliance_status**
- id (PK)
- job_id (FK backup_jobs): ジョブID
- check_date: チェック日時
- copies_count: コピー数
- media_types_count: メディア種別数
- has_offsite: オフサイト有無
- has_offline: オフライン有無
- has_errors: エラー有無
- overall_status: 総合状態（compliant/non_compliant/warning）

**alerts**
- id (PK)
- alert_type: アラート種別
- severity: 重要度（info/warning/error/critical）
- job_id (FK backup_jobs): 関連ジョブID
- title: タイトル
- message: メッセージ
- is_acknowledged: 確認済みフラグ
- acknowledged_by (FK users): 確認者ID
- acknowledged_at: 確認日時

**reports**
- id (PK)
- report_type: レポート種別（daily/weekly/monthly/compliance/audit）
- report_title: タイトル
- date_from: 対象期間開始
- date_to: 対象期間終了
- file_path: ファイルパス
- file_format: 形式（html/pdf/csv）
- generated_by (FK users): 生成者ID

## 設定（app/config.py）

```python
# 3-2-1-1-0 ルール設定
MIN_COPIES = 3  # 最少コピー数
MIN_MEDIA_TYPES = 2  # 最少メディア種別数
OFFLINE_MEDIA_UPDATE_WARNING_DAYS = 7  # オフラインメディア更新警告期限

# メール通知設定
MAIL_SERVER = 'mail.example.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'backup-system@example.com'
MAIL_PASSWORD = 'password'

# Microsoft Teams 通知
TEAMS_WEBHOOK_URL = 'https://outlook.webhook.office.com/webhookb2/...'

# レポート出力
REPORT_OUTPUT_DIR = BASE_DIR / 'reports'
REPORT_RETENTION_DAYS = 90
```

## ログ出力

サービスはログレベルに応じて詳細な情報を出力します：

```python
import logging

# ログレベル設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 出力例
# INFO - Compliance check for job 1 (Daily DB Backup): compliant
# WARNING - Backup job 5 is not compliant with 3-2-1-1-0 rule
# ERROR - Failed to send email notification: SMTP connection error
```

## エラーハンドリング

各サービスメソッドは例外を適切に処理し、ロギングします：

```python
try:
    result = checker.check_3_2_1_1_0(job_id)
except Exception as e:
    logger.error(f"Compliance check failed: {str(e)}")
    # フォールバック処理
```

## テスト

ユニットテストファイル: `/mnt/Linux-ExHDD/backup-management-system/tests/test_business_services.py`

テスト実行：
```bash
pytest tests/test_business_services.py -v
```

**テストカバレッジ**:
- ComplianceChecker: 準拠チェック、単一・複数ジョブ、履歴取得
- AlertManager: アラート作成、確認、通知、取得
- ReportGenerator: 日次/週次/月次/準拠/監査レポート生成

## パフォーマンス最適化

### 準拠状況キャッシング
`check_3_2_1_1_0()` 実行後、結果は `ComplianceStatus` テーブルにキャッシュされます。これにより、同じジョブの重複チェックを回避できます。

```python
# キャッシュから取得（履歴確認）
history = checker.get_compliance_history(job_id, days=30)
```

### インデックス最適化
主要なクエリは以下のインデックスで最適化されています：
- `backup_jobs`: job_name, job_type, owner_id, is_active
- `backup_copies`: job_id, copy_type, media_type
- `compliance_status`: job_id, check_date, overall_status
- `alerts`: alert_type, severity, is_acknowledged, created_at
- `audit_logs`: user_id, action_type, created_at

### バッチ処理
`check_all_jobs()` は全ジョブを効率的に処理します。定期実行タスク（スケジューラー）で使用してください。

## セキュリティ考慮事項

1. **パスワード保護**: User モデルで bcrypt ハッシング
2. **監査ログ**: すべての操作を AuditLog に記録
3. **アクセス制御**: ロールベースのアクセス制御（admin/operator/viewer/auditor）
4. **メール認証**: SMTP 認証情報は環境変数で管理
5. **Teams Webhook**: 環境変数で安全に管理

## 将来の拡張機能

### 実装予定
- PDF レポート生成（ReportLib等の統合）
- グラフ生成（matplotlib等の統合）
- S3/Azure Blob Storage への直接保存
- キャッシング戦略の最適化（Redis 統合）
- API レート制限
- Slack 通知対応

### 拡張性
各サービスは独立設計により、新機能追加が容易：
```python
# カスタムアラートハンドラー追加
class CustomAlertHandler:
    def handle_alert(self, alert):
        # カスタム処理
        pass

# レポート形式追加
class ReportGenerator:
    def generate_report_format_x(self, data, format='xlsx'):
        # XLSX形式レポート生成
        pass
```

## トラブルシューティング

### 準拠チェックが実行されない
- ジョブが `is_active=True` であることを確認
- バックアップコピーが作成されていることを確認
- ログを確認: `logger.info()` 出力

### アラート通知が送信されない
- SMTP 設定を確認: `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`
- ユーザーのメールアドレスが設定されていることを確認
- ログで通知失敗をチェック

### レポートが生成されない
- レポート出力ディレクトリの書き込み権限を確認
- ディスク容量の確認
- データベース接続を確認

## まとめ

このビジネスロジックサービスレイヤーは、バックアップ管理システムの中核機能を提供します。設計原則：

- **単一責任**: 各サービスは明確な責務を持つ
- **疎結合**: サービス間の依存性を最小化
- **再利用性**: 複数のエンドポイント・タスクから利用可能
- **テスト可能**: ユニットテスト対応
- **拡張性**: 新機能追加が容易

詳細については、各サービスのコメントと設計仕様書を参照してください。
