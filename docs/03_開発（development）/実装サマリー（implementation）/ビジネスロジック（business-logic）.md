# ビジネスロジックサービス - 実装ガイド

## クイックスタート

### インストール

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# データベースの初期化
flask db upgrade

# レポートディレクトリの作成
mkdir -p reports
```

### 基本的な使用方法

```python
from app import create_app, db
from app.services import ComplianceChecker, AlertManager, ReportGenerator
from app.services.alert_manager import AlertType, AlertSeverity

# アプリケーション初期化
app = create_app()

with app.app_context():
    # 1. 準拠チェック
    checker = ComplianceChecker()
    result = checker.check_3_2_1_1_0(job_id=1)
    print(f"準拠状況: {result['status']}")

    # 2. アラート生成
    if not result['compliant']:
        manager = AlertManager()
        alert = manager.create_alert(
            alert_type=AlertType.RULE_VIOLATION,
            severity=AlertSeverity.WARNING,
            title="3-2-1-1-0 ルール違反",
            message=f"ジョブが準拠していません: {result['violations'][0]}",
            job_id=1,
            notify=True
        )

    # 3. レポート生成
    generator = ReportGenerator()
    report = generator.generate_daily_report(
        generated_by=1,
        format='html'
    )
    print(f"レポート: {report.file_path}")
```

## サービス概要

### ComplianceChecker - 3-2-1-1-0 準拠チェック

**責務**: バックアップジョブが 3-2-1-1-0 ルールに準拠しているか検証

```python
checker = ComplianceChecker()

# 単一ジョブのチェック
result = checker.check_3_2_1_1_0(job_id=1)
# 戻り値:
# {
#     'compliant': True/False,
#     'status': 'compliant' | 'non_compliant' | 'warning',
#     'copies_count': 3,
#     'media_types_count': 2,
#     'has_offsite': True,
#     'has_offline': True,
#     'has_errors': False,
#     'violations': [...],  # 準拠違反メッセージ
#     'warnings': [...]     # 警告メッセージ
# }

# 全ジョブのチェック
summary = checker.check_all_jobs()
# 戻り値:
# {
#     'total_jobs': 10,
#     'compliant_jobs': 8,
#     'warning_jobs': 1,
#     'non_compliant_jobs': 1,
#     'compliance_rate': 80.0,
#     'results': [...]
# }

# 準拠履歴の取得
history = checker.get_compliance_history(job_id=1, days=30)
```

**3-2-1-1-0 ルール仕様**:

| 要件 | 確認項目 | 例 |
|------|---------|-----|
| **3 copies** | 3 つ以上のバックアップコピー | Primary + Secondary + Offsite |
| **2 types** | 2 種類以上のメディア | Disk + Tape または Disk + Cloud |
| **1 offsite** | オフサイトコピー | AWS S3, Azure Blob, Google Cloud |
| **1 offline** | オフラインコピー | テープ, 外部HDD（保管庫保管） |
| **0 source** | ソースにコピーなし | バックアップ後に移動・削除 |

### AlertManager - アラート管理・通知

**責務**: イベントベースのアラート生成・通知・管理

```python
manager = AlertManager()

# アラート作成（通知付き）
alert = manager.create_alert(
    alert_type=AlertType.BACKUP_FAILED,
    severity=AlertSeverity.ERROR,
    title="バックアップ失敗",
    message="Database backup failed - Network timeout",
    job_id=1,
    notify=True  # メール・Teams通知を送信
)

# 未確認アラートの取得
unack_alerts = manager.get_unacknowledged_alerts(limit=50)

# ジョブに関連するアラート取得
job_alerts = manager.get_alerts_by_job(job_id=1, days=30)

# アラートを確認
manager.acknowledge_alert(alert_id=1, user_id=user_id)

# 古いアラートを削除
deleted_count = manager.clear_old_alerts(days=90)
```

**通知チャネル**:

| チャネル | 有効化 | 重要度制限 | 形式 |
|---------|--------|-----------|------|
| Dashboard | 常時 | なし | HTML |
| Email | SMTP設定 | WARNING以上 | HTML |
| Teams | Webhook URL | ERROR以上 | Adaptive Card |

**アラートタイプ**:

```python
AlertType.BACKUP_FAILED              # バックアップ失敗
AlertType.BACKUP_SUCCESS             # バックアップ成功
AlertType.RULE_VIOLATION             # ルール違反
AlertType.COMPLIANCE_WARNING         # 準拠警告
AlertType.OFFLINE_MEDIA_UPDATE_WARNING  # オフラインメディア更新遅延
AlertType.VERIFICATION_REMINDER      # 検証テストリマインダー
AlertType.MEDIA_ROTATION_REMINDER    # メディアローテーションリマインダー
AlertType.MEDIA_OVERDUE_RETURN       # メディア返却期限超過
AlertType.SYSTEM_ERROR               # システムエラー
```

**重要度**:

```python
AlertSeverity.INFO      # 情報通知
AlertSeverity.WARNING   # 警告（Email送信）
AlertSeverity.ERROR     # エラー（Email + Teams）
AlertSeverity.CRITICAL  # クリティカル（全チャネル）
```

### ReportGenerator - レポート生成

**責務**: 複数形式・複数種別のレポート生成

```python
generator = ReportGenerator()

# 日次レポート（HTML）
daily = generator.generate_daily_report(
    generated_by=user_id,
    date=datetime.utcnow(),
    format='html'
)

# 週次レポート（CSV）
weekly = generator.generate_weekly_report(
    generated_by=user_id,
    end_date=datetime.utcnow(),
    format='csv'
)

# 月次レポート（HTML）
monthly = generator.generate_monthly_report(
    generated_by=user_id,
    year=2025,
    month=10,
    format='html'
)

# 準拠状況レポート
compliance = generator.generate_compliance_report(
    generated_by=user_id,
    end_date=datetime.utcnow(),
    format='html'
)

# 監査ログレポート
audit = generator.generate_audit_report(
    generated_by=user_id,
    start_date=datetime(2025, 10, 1),
    end_date=datetime(2025, 10, 31),
    format='csv'
)

# 古いレポートを削除
deleted_count = generator.cleanup_old_reports(days=90)
```

**出力形式**:
- `html`: インタラクティブ表示、スタイル付き
- `csv`: データエクスポート、Excel 互換
- `pdf`: スタブ実装（将来：ReportLib/weasyprint）

## スケジューラー統合

APScheduler で定期実行タスクを設定：

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.services import ComplianceChecker, ReportGenerator, AlertManager

scheduler = BackgroundScheduler()

def daily_compliance_check():
    """日次の準拠チェック"""
    checker = ComplianceChecker()
    result = checker.check_all_jobs()
    # 非準拠ジョブにアラート生成
    for job_result in result['results']:
        if not job_result['compliant']:
            manager = AlertManager()
            manager.create_alert(
                alert_type=AlertType.RULE_VIOLATION,
                severity=AlertSeverity.WARNING,
                title=f"非準拠: {job_result['job_name']}",
                message="3-2-1-1-0 ルール違反検出",
                job_id=job_result['job_id'],
                notify=True
            )

def daily_report_generation():
    """日次レポート生成"""
    generator = ReportGenerator()
    generator.generate_daily_report(generated_by=1, format='html')

def cleanup_tasks():
    """クリーンアップ（90日ごと）"""
    checker = ComplianceChecker()
    manager = AlertManager()
    generator = ReportGenerator()

    # 古いアラート削除
    manager.clear_old_alerts(days=90)

    # 古いレポート削除
    generator.cleanup_old_reports(days=90)

# スケジューラー設定
scheduler.add_job(daily_compliance_check, 'cron', hour=6)  # 毎日 6:00
scheduler.add_job(daily_report_generation, 'cron', hour=7)  # 毎日 7:00
scheduler.add_job(cleanup_tasks, 'cron', hour=2, day_of_week=0)  # 毎週日曜 2:00

scheduler.start()
```

## API エンドポイント例

Flask ビューから使用：

```python
from flask import Blueprint, request, jsonify
from app.services import ComplianceChecker, AlertManager

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/compliance/check/<int:job_id>', methods=['GET'])
def check_compliance(job_id):
    """ジョブの準拠性をチェック"""
    checker = ComplianceChecker()
    result = checker.check_3_2_1_1_0(job_id)
    return jsonify(result)

@api_bp.route('/compliance/all', methods=['GET'])
def check_all_compliance():
    """全ジョブの準拠性をチェック"""
    checker = ComplianceChecker()
    result = checker.check_all_jobs()
    return jsonify(result)

@api_bp.route('/alerts/unacknowledged', methods=['GET'])
def get_unacknowledged_alerts():
    """未確認アラートを取得"""
    limit = request.args.get('limit', 50, type=int)
    manager = AlertManager()
    alerts = manager.get_unacknowledged_alerts(limit=limit)
    return jsonify([{
        'id': a.id,
        'alert_type': a.alert_type,
        'severity': a.severity,
        'title': a.title,
        'created_at': a.created_at.isoformat()
    } for a in alerts])

@api_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """アラートを確認"""
    user_id = request.json.get('user_id')
    manager = AlertManager()
    alert = manager.acknowledge_alert(alert_id, user_id)
    return jsonify({'success': True, 'alert_id': alert.id})
```

## 設定（app/config.py）

```python
# 3-2-1-1-0 ルール
MIN_COPIES = 3  # 最少コピー数
MIN_MEDIA_TYPES = 2  # 最少メディア種別数
OFFLINE_MEDIA_UPDATE_WARNING_DAYS = 7  # オフラインメディア警告期間

# SMTP 通知
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

# Microsoft Teams
TEAMS_WEBHOOK_URL = os.environ.get('TEAMS_WEBHOOK_URL')

# レポート
REPORT_OUTPUT_DIR = BASE_DIR / 'reports'
REPORT_RETENTION_DAYS = 90
```

## ロギング

サービスは構造化ログを出力します：

```
INFO - Compliance check for job 1 (Daily DB Backup): compliant
WARNING - Backup job 5 is not compliant with 3-2-1-1-0 rule
ERROR - Failed to send email notification: SMTP connection error
DEBUG - Cached compliance status for job 1
```

ログレベル設定：

```python
import logging

# アプリケーション全体
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 特定のロガー
logging.getLogger('app.services.compliance_checker').setLevel(logging.DEBUG)
```

## データベースクエリ例

```python
from app.models import BackupJob, ComplianceStatus, Alert

# 過去30日間で非準拠だったジョブ
non_compliant = ComplianceStatus.query.filter(
    ComplianceStatus.overall_status == 'non_compliant',
    ComplianceStatus.check_date >= datetime.utcnow() - timedelta(days=30)
).all()

# 未確認のエラーアラート
error_alerts = Alert.query.filter(
    Alert.severity == 'error',
    Alert.is_acknowledged == False
).order_by(Alert.created_at.desc()).all()

# ジョブのコピー一覧
job = BackupJob.query.get(1)
for copy in job.copies:
    print(f"{copy.copy_type}: {copy.media_type}")
```

## トラブルシューティング

### 準拠チェックが失敗する

```python
# ログを確認
import logging
logging.getLogger('app.services').setLevel(logging.DEBUG)

# ジョブが存在することを確認
job = BackupJob.query.get(job_id)
assert job is not None
assert job.is_active == True

# コピーが作成されていることを確認
copies = BackupCopy.query.filter_by(job_id=job_id).all()
assert len(copies) > 0
```

### メール通知が送信されない

```python
# SMTP 設定を確認
from app.config import Config
print(f"MAIL_SERVER: {Config.MAIL_SERVER}")
print(f"MAIL_PORT: {Config.MAIL_PORT}")
print(f"MAIL_USERNAME: {Config.MAIL_USERNAME}")

# ユーザーのメールアドレスを確認
user = User.query.get(user_id)
assert user.email is not None

# テスト送信
from app.utils.email import EmailService
email_service = EmailService()
email_service.send(
    to='test@example.com',
    subject='Test',
    html='<p>Test email</p>'
)
```

### レポートが生成されない

```python
# レポートディレクトリを確認
from app.config import Config
import os
report_dir = Config.REPORT_OUTPUT_DIR
os.makedirs(report_dir, exist_ok=True)
print(f"Report directory: {report_dir}")
print(f"Writable: {os.access(report_dir, os.W_OK)}")

# データベースを確認
from app.models import BackupExecution
executions = BackupExecution.query.all()
print(f"Total executions: {len(executions)}")
```

## 参考資料

- **実装ガイド**: `BUSINESS_SERVICES_IMPLEMENTATION.md`
- **実装サマリー**: `IMPLEMENTATION_SUMMARY.md`
- **設計仕様書**: `docs/設計仕様書_3-2-1-1-0バックアップ管理システム.txt`
- **テスト**: `tests/test_business_services.py`

## ライセンス・サポート

このコンポーネントはバックアップ管理システムの一部です。

質問や問題については、プロジェクトの Issue Tracker を使用してください。
