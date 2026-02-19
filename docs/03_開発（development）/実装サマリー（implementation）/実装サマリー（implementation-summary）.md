# ビジネスロジックサービス実装サマリー

## 実装概要

バックアップ管理システムのビジネスロジックサービスレイヤーの実装が完了しました。

## 実装ファイル一覧

| ファイルパス | 行数 | 説明 |
|----------|------|------|
| app/models.py | 406 | SQLAlchemy ORM モデル定義 |
| app/services/__init__.py | 18 | サービスパッケージの初期化 |
| app/services/compliance_checker.py | 359 | 3-2-1-1-0 ルール準拠チェック |
| app/services/alert_manager.py | 546 | アラート管理・通知 |
| app/services/report_generator.py | 961 | レポート生成（HTML/PDF/CSV） |
| tests/test_business_services.py | 550 | ユニットテスト |
| **合計** | **2,840** | - |

## 実装内容

### 1. データモデル（app/models.py）

SQLAlchemy ORM で定義された 13 個のモデル：

#### ユーザー・認証
- **User**: ユーザー情報、認証、ロール管理
  - Flask-Login 統合
  - bcrypt パスワードハッシング
  - ロールベースアクセス制御（admin/operator/viewer/auditor）

#### バックアップ管理
- **BackupJob**: バックアップジョブ設定
  - ジョブ種別（system_image/file/database/vm）
  - スケジュール管理
  - 保持期間設定

- **BackupCopy**: バックアップコピー（3-2-1-1-0 の実体）
  - コピー種別（primary/secondary/offsite/offline）
  - メディア種別（disk/tape/cloud/external_hdd）
  - 暗号化・圧縮設定
  - ステータス追跡

- **BackupExecution**: 実行履歴
  - 実行日時、結果、エラーメッセージ
  - バックアップサイズ、実行時間
  - 実行元追跡

#### オフラインメディア管理
- **OfflineMedia**: オフラインメディア（テープ、外部HDD等）
  - メディア識別子（バーコード）
  - 容量、購入日
  - 保管場所管理
  - QRコード対応

- **MediaRotationSchedule**: メディアローテーション
  - GFS、Tower of Hanoi 等の方式対応
  - ローテーション周期管理

- **MediaLending**: メディア貸出管理
  - 貸出日時、返却予定
  - 貸出目的、返却状態追跡

#### 検証・テスト
- **VerificationTest**: 復元テスト実施記録
  - テスト種別（full_restore/partial/integrity）
  - 復元先、テスト結果
  - 発見された問題の記録

- **VerificationSchedule**: 検証テストスケジュール
  - テスト頻度設定（monthly/quarterly等）
  - 担当者割り当て

#### 準拠・監査
- **ComplianceStatus**: 3-2-1-1-0 準拠状況キャッシュ
  - チェック日時、結果
  - 準拠状態（compliant/non_compliant/warning）

- **Alert**: アラート管理
  - アラート種別・重要度
  - 確認状態追跡
  - 確認者・確認日時記録

- **AuditLog**: 監査ログ
  - ユーザーアクション記録
  - リソース種別・ID
  - 実行結果、詳細情報（JSON）

#### レポート
- **Report**: 生成レポート管理
  - レポート種別（daily/weekly/monthly/compliance/audit）
  - 対象期間、ファイルパス
  - 生成者追跡

- **SystemSetting**: システム設定
  - キー・値形式の設定管理
  - 値タイプ（string/int/bool/json）
  - 暗号化対応

### 2. ComplianceChecker サービス

**ファイル**: `app/services/compliance_checker.py`

#### 機能
- 3-2-1-1-0 バックアップルール自動チェック
- 単一ジョブ・全ジョブの準拠性判定
- 準拠状況の履歴管理

#### 主要メソッド

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `check_3_2_1_1_0(job_id)` | 単一ジョブの準拠チェック | dict（準拠状態、違反、警告） |
| `check_all_jobs()` | 全アクティブジョブのチェック | dict（サマリー、個別結果） |
| `get_compliance_history(job_id, days)` | 準拠状況の履歴取得 | list（履歴レコード） |

#### 3-2-1-1-0 ルール検証
```
✓ 3 copies: 最低 3 つのバックアップコピー確認
✓ 2 types: 最低 2 種類のメディアタイプ確認
✓ 1 offsite: オフサイトコピー（クラウド等）存在確認
✓ 1 offline: オフラインコピー（テープ等）存在確認
✓ 0 source: オリジナルにコピーなし確認
+ Stale check: オフラインメディアの鮮度確認
+ Error check: コピーの失敗状態確認
```

#### 返却データ構造
```python
{
    'compliant': bool,
    'status': 'compliant' | 'non_compliant' | 'warning',
    'copies_count': int,
    'media_types': [str, ...],
    'media_types_count': int,
    'has_offsite': bool,
    'has_offline': bool,
    'has_errors': bool,
    'violations': [str, ...],  # 違反メッセージ
    'warnings': [str, ...],    # 警告メッセージ
    'details': {                # 詳細情報
        'job_id': int,
        'job_name': str,
        'checked_at': str,
        'copies': [...]
    }
}
```

### 3. AlertManager サービス

**ファイル**: `app/services/alert_manager.py`

#### 機能
- イベントベースのアラート生成
- マルチチャネル通知（Dashboard/Email/Teams）
- アラート確認・状態管理
- アラート履歴クエリ

#### サポート通知チャネル

| チャネル | 設定 | 説明 |
|---------|------|------|
| Dashboard | 常に有効 | データベースに記録、UI表示 |
| Email | SMTP設定で有効化 | 管理者・ジョブ担当者宛通知 |
| Teams | Webhook URL で有効化 | Microsoft Teams Adaptive Card |

#### アラートタイプ（9種類）
- `BACKUP_FAILED`: バックアップ失敗
- `BACKUP_SUCCESS`: バックアップ成功
- `RULE_VIOLATION`: ルール違反（3-2-1-1-0等）
- `COMPLIANCE_WARNING`: 準拠警告
- `OFFLINE_MEDIA_UPDATE_WARNING`: オフラインメディア更新遅延
- `VERIFICATION_REMINDER`: 検証テスト実施リマインダー
- `MEDIA_ROTATION_REMINDER`: メディアローテーションリマインダー
- `MEDIA_OVERDUE_RETURN`: メディア返却期限超過
- `SYSTEM_ERROR`: システムエラー

#### 重要度レベル
- `INFO`: 情報通知
- `WARNING`: 警告（Email送信）
- `ERROR`: エラー（Email + Teams送信）
- `CRITICAL`: クリティカル（全チャネル）

#### 主要メソッド

| メソッド | 説明 |
|---------|------|
| `create_alert()` | アラート作成・通知送信 |
| `send_notifications()` | 通知配信（各チャネル） |
| `acknowledge_alert()` | アラート確認マーク |
| `get_unacknowledged_alerts()` | 未確認アラート取得 |
| `get_alerts_by_job()` | ジョブ別アラート取得 |
| `get_alerts_by_type()` | タイプ別アラート取得 |
| `clear_old_alerts()` | 古いアラート削除 |

#### Email 通知テンプレート
- HTML形式で視認性向上
- 重要度別の色分け
- ジョブ情報を含める

#### Microsoft Teams Adaptive Card
- テキストブロック（タイトル・メッセージ）
- ファクトセット（詳細情報）
- アクション付き

### 4. ReportGenerator サービス

**ファイル**: `app/services/report_generator.py`

#### 機能
- 複数形式でのレポート生成
- 時間ベースのレポート作成
- レポートファイル管理

#### レポート種別（5種類）

| 種別 | 対象期間 | 内容 |
|------|---------|------|
| **Daily** | 1日 | バックアップ実行状況、成功/失敗数 |
| **Weekly** | 7日 | 日別推移、成功率 |
| **Monthly** | 30日 | パフォーマンス指標、検証テスト結果 |
| **Compliance** | 30日 | 3-2-1-1-0 準拠率、準拠/非準拠ジョブ数 |
| **Audit** | カスタム | 監査ログ詳細、アクション履歴 |

#### 出力形式（3種類）

| 形式 | 用途 | ステータス |
|------|------|----------|
| **HTML** | Web表示、可視化 | 完全実装 |
| **PDF** | 印刷、配布 | スタブ実装 |
| **CSV** | データエクスポート、Excel | 完全実装 |

#### 主要メソッド

| メソッド | 戻り値 |
|---------|--------|
| `generate_daily_report()` | Report オブジェクト |
| `generate_weekly_report()` | Report オブジェクト |
| `generate_monthly_report()` | Report オブジェクト |
| `generate_compliance_report()` | Report オブジェクト |
| `generate_audit_report()` | Report オブジェクト |
| `cleanup_old_reports()` | 削除件数（int） |

#### HTML レポート構成
- ヘッダー（タイトル、期間）
- サマリーセクション（統計情報）
- 詳細テーブル（実行履歴等）
- スタイル（CSS インライン）

#### CSV レポート構成
- ヘッダーセクション（タイトル、期間）
- サマリーセクション（統計）
- 詳細セクション（テーブルデータ）
- Excel互換形式

#### 出力ディレクトリ
`{BASE_DIR}/reports/`

ファイル命名規則：
- 日次: `daily_report_{YYYY-MM-DD}.{format}`
- 週次: `weekly_report_{start}_to_{end}.{format}`
- 月次: `monthly_report_{YYYY-MM}.{format}`
- 準拠: `compliance_report_{start}_to_{end}.{format}`
- 監査: `audit_report_{start}_to_{end}.{format}`

### 5. ユニットテスト

**ファイル**: `tests/test_business_services.py`

#### テストスイート

| テストクラス | テスト数 | 対象 |
|-------------|--------|------|
| TestComplianceChecker | 5 | ComplianceChecker |
| TestAlertManager | 6 | AlertManager |
| TestReportGenerator | 5 | ReportGenerator |
| TestServiceIntegration | 1 | 複合シナリオ |

#### テストカバレッジ

**ComplianceChecker**
- ✓ 準拠ジョブのチェック
- ✓ 非準拠ジョブのチェック
- ✓ 警告ジョブのチェック
- ✓ 全ジョブの一括チェック
- ✓ 準拠履歴の取得

**AlertManager**
- ✓ アラート作成
- ✓ アラート確認
- ✓ 未確認アラートの取得
- ✓ ジョブ別アラートの取得
- ✓ Adaptive Card 生成
- ✓ Email テンプレート

**ReportGenerator**
- ✓ 日次 HTML レポート生成
- ✓ 日次 CSV レポート生成
- ✓ 準拠状況レポート生成
- ✓ 監査ログレポート生成
- ✓ 古いレポートのクリーンアップ

## 設計パターン

### 1. Service Pattern
各サービスが独立した責務を持つ単一責任原則を遵守

### 2. Repository Pattern
データアクセスは SQLAlchemy ORM を通じて一元化

### 3. DTO Pattern
サービス間、API間のデータ受け渡しに dict を使用

### 4. Enum Pattern
アラートタイプ、重要度等を型安全な Enum で定義

## パフォーマンス特性

### データベースクエリ最適化
- **インデックス**: 頻繁にクエリされるカラムに設定
  - backup_jobs: job_name, job_type, owner_id, is_active
  - backup_copies: job_id, copy_type, media_type
  - compliance_status: job_id, check_date, overall_status
  - alerts: alert_type, severity, is_acknowledged, created_at
  - audit_logs: user_id, action_type, created_at

### キャッシング戦略
- **ComplianceStatus テーブル**: チェック結果をキャッシュ
- **Report テーブル**: 生成済みレポートの記録
- 将来: Redis キャッシュ統合予定

### バッチ処理
- `check_all_jobs()`: 全ジョブを効率的に処理
- `cleanup_old_reports()`: バッチ削除

## セキュリティ機能

1. **認証・認可**
   - Flask-Login 統合
   - bcrypt パスワードハッシング
   - ロールベースアクセス制御

2. **監査**
   - すべてのアクション記録（AuditLog）
   - 実行者・タイムスタンプ・結果追跡
   - リソース変更の詳細記録（JSON）

3. **秘密管理**
   - SMTP 認証情報は環境変数
   - Teams Webhook URL は環境変数
   - 設定値の暗号化対応（is_encrypted フラグ）

4. **データ保護**
   - メール送信時のSSL/TLS
   - HTTPS 強制（本番環境）
   - CSRF 保護（Flask-WTF）

## 拡張性設計

### 新しい通知チャネル追加
```python
def _send_slack_notification(self, alert: Alert) -> bool:
    # Slack API 統計情報追加
    pass

def _should_send_slack(self, alert: Alert) -> bool:
    return Config.SLACK_WEBHOOK_URL is not None
```

### 新しいレポート形式追加
```python
def _generate_report_xlsx(self, data: Dict, date) -> Tuple[Path, bytes]:
    # XLSX 形式生成
    pass

def generate_xlsx_report(self, generated_by: int, date: datetime):
    # XLSX レポート生成メソッド
    pass
```

### カスタム準拠ルール追加
```python
def check_custom_rule(self, job_id: int, rule_definition: Dict) -> bool:
    # カスタムルールの検証ロジック
    pass
```

## デプロイメント考慮事項

### 開発環境
- SQLite データベース
- Flask 開発サーバー
- メール: テスト (console backend)
- Teams: スキップ

### 本番環境
- PostgreSQL データベース
- Waitress WSGI サーバー (Windows)
- メール: SMTP (TLS/SSL)
- Teams: Webhook 有効化

### 初期化スクリプト
```bash
# データベースマイグレーション
flask db upgrade

# テスト実行
pytest tests/test_business_services.py

# レポートディレクトリ作成
mkdir -p reports
```

## メンテナンス指針

### 定期実行タスク（APScheduler）
- 日次: `check_all_jobs()` + 準拠アラート生成
- 日次: `generate_daily_report()`
- 週次: `generate_weekly_report()`
- 月次: `generate_monthly_report()`
- 定期: `cleanup_old_reports()` + `clear_old_alerts()`

### モニタリング
- ログレベル: INFO (本番), DEBUG (開発)
- ログローテーション: 90日
- アラート未確認数: ダッシュボード表示

### バックアップ
- SQLite: 定期的にバックアップ
- PostgreSQL: レプリケーション・バックアップ設定

## 既知制限と今後の改善

| 項目 | 現状 | 改善予定 |
|------|------|---------|
| PDF生成 | スタブ | ReportLab/weasyprint 統合 |
| グラフ | なし | matplotlib/plotly 統合 |
| キャッシング | 単純 | Redis 統合 |
| テスト | 基本 | カバレッジ向上（>90%） |
| API | なし | FastAPI/GraphQL 追加 |
| 国際化 | 日本語のみ | i18n 対応 |

## ドキュメント

- **実装ガイド**: `BUSINESS_SERVICES_IMPLEMENTATION.md`
- **このファイル**: `IMPLEMENTATION_SUMMARY.md`
- **設計仕様書**: `docs/設計仕様書_3-2-1-1-0バックアップ管理システム.txt`

## サポート情報

バグ報告やサポートについては、プロジェクトの Issue Tracker を使用してください。

---

**実装完了日**: 2025-10-30
**実装者**: Claude API
**総実装行数**: 2,840 行
**テストカバレッジ**: 17 テスト
