================================================================================
                    設計仕様書
           3-2-1-1-0バックアップ管理システム
================================================================================

文書番号: DD-BACKUP-MGMT-001
版番号: 1.0
作成日: 2025年10月28日
承認者: [承認者名]
作成者: システム開発チーム
関連文書: 要件定義書 (RD-BACKUP-MGMT-001)

================================================================================
目次
================================================================================

1. システムアーキテクチャ
2. 技術スタック
3. ディレクトリ構造
4. データベース設計
5. API設計
6. UI設計
7. セキュリティ設計
8. 認証・認可設計
9. ログ設計
10. 通知設計
11. デプロイメント設計
12. 運用設計
13. テスト設計
14. パフォーマンス設計
15. 監視設計

================================================================================
1. システムアーキテクチャ
================================================================================

1.1 全体アーキテクチャ
----------------------

【3層アーキテクチャ】

+------------------------------------------------------------------+
|                        プレゼンテーション層                       |
|  +---------------------------------------------------------+     |
|  |  Webブラウザ (Chrome/Edge/Firefox)                       |     |
|  |  - HTML5 + Bootstrap 5                                  |     |
|  |  - JavaScript (Chart.js, DataTables)                    |     |
|  |  - AJAX (RESTful API呼び出し)                           |     |
|  +---------------------------------------------------------+     |
+------------------------------------------------------------------+
                            ↕ HTTPS (TLS 1.2+)
+------------------------------------------------------------------+
|                        アプリケーション層                         |
|  +---------------------------------------------------------+     |
|  |  Flask Webアプリケーション (Python 3.10+)                |     |
|  |  +-----------------------+  +-------------------------+  |     |
|  |  | ビュー (Views)        |  | REST API                |  |     |
|  |  | - ダッシュボード      |  | - /api/v1/backup/*      |  |     |
|  |  | - ジョブ管理         |  | - /api/v1/jobs/*        |  |     |
|  |  | - レポート           |  | - /api/v1/reports/*     |  |     |
|  |  +-----------------------+  +-------------------------+  |     |
|  |                                                         |     |
|  |  +-----------------------+  +-------------------------+  |     |
|  |  | ビジネスロジック      |  | スケジューラー          |  |     |
|  |  | - 3-2-1-1-0チェック   |  | (APScheduler)           |  |     |
|  |  | - アラート生成       |  | - 定期レポート生成      |  |     |
|  |  | - レポート生成       |  | - 検証リマインダー      |  |     |
|  |  +-----------------------+  +-------------------------+  |     |
|  +---------------------------------------------------------+     |
+------------------------------------------------------------------+
                            ↕ ORM (SQLAlchemy)
+------------------------------------------------------------------+
|                        データ層                                  |
|  +---------------------------------------------------------+     |
|  |  SQLite (開発) / PostgreSQL (本番移行時)                |     |
|  |  - backup_jobs                                          |     |
|  |  - backup_copies                                        |     |
|  |  - offline_media                                        |     |
|  |  - verification_tests                                   |     |
|  |  - users                                                |     |
|  |  - audit_logs                                           |     |
|  +---------------------------------------------------------+     |
+------------------------------------------------------------------+

【外部連携】

+------------------+              +---------------------------+
| Windows Server   |              | 外部サービス              |
| +-------------+  |  REST API    | +---------------------+   |
| | PowerShell  |--+------------->| | SMTPサーバー        |   |
| | スクリプト  |  |              | | (メール通知)        |   |
| +-------------+  |              | +---------------------+   |
|                  |              |                           |
| +-------------+  |              | +---------------------+   |
| | Veeam       |  |              | | Microsoft Teams     |   |
| | WSB         |  |              | | (Webhook通知)       |   |
| | AOMEI       |  |              | +---------------------+   |
| +-------------+  |              +---------------------------+
+------------------+

1.2 コンポーネント設計
----------------------

【Flaskアプリケーション構成】

app/
├── __init__.py          # アプリケーション初期化
├── models.py            # データモデル (SQLAlchemy)
├── views/               # ビューモジュール
│   ├── __init__.py
│   ├── dashboard.py     # ダッシュボード
│   ├── jobs.py          # バックアップジョブ管理
│   ├── media.py         # オフラインメディア管理
│   ├── verification.py  # 検証テスト管理
│   └── reports.py       # レポート
├── api/                 # REST APIモジュール
│   ├── __init__.py
│   ├── backup.py        # バックアップAPI
│   ├── jobs.py          # ジョブAPI
│   └── reports.py       # レポートAPI
├── services/            # ビジネスロジック
│   ├── __init__.py
│   ├── compliance_checker.py  # 3-2-1-1-0準拠チェック
│   ├── alert_manager.py       # アラート管理
│   └── report_generator.py    # レポート生成
├── auth/                # 認証・認可
│   ├── __init__.py
│   └── decorators.py    # 権限チェックデコレーター
├── utils/               # ユーティリティ
│   ├── __init__.py
│   ├── email.py         # メール送信
│   └── logger.py        # ロガー
└── scheduler/           # スケジューラー
    ├── __init__.py
    └── tasks.py         # 定期実行タスク

1.3 開発環境と本番環境の差異対応
--------------------------------

【クロスプラットフォーム対応設計】

config.py:
  - 環境変数による設定切り替え
  - os.name判定による環境判別
  - pathlibによるパス処理統一

開発環境 (Linux):
  - Flask開発サーバー (flask run)
  - SQLite
  - 簡易ログ出力

本番環境 (Windows 11):
  - Waitress WSGIサーバー
  - SQLite (初期) / PostgreSQL (移行時)
  - systemd相当 (NSSM)
  - Windows Event Log統合

1.4 スケーラビリティ設計
------------------------

【水平スケーリング (将来対応)】
- データベースをPostgreSQLに移行
- Redis導入 (セッション管理、キャッシュ)
- ロードバランサー配置
- 複数インスタンス起動

【垂直スケーリング】
- CPU/メモリ増強
- データベースクエリ最適化
- インデックス追加

================================================================================
2. 技術スタック
================================================================================

2.1 バックエンド
----------------

言語:
  - Python 3.10以上

Webフレームワーク:
  - Flask 3.0.x

ORM:
  - SQLAlchemy 2.0.x

データベース:
  - SQLite 3.x (開発・小規模運用)
  - PostgreSQL 14+ (大規模運用時)

スケジューラー:
  - APScheduler 3.10.x

WSGIサーバー (本番):
  - Waitress 2.1.x (Windows推奨)
  - Gunicorn (Linux代替)

認証:
  - Flask-Login 0.6.x
  - bcrypt (パスワードハッシュ化)

パッケージ管理:
  - pip
  - requirements.txt

2.2 フロントエンド
------------------

HTML/CSS:
  - HTML5
  - Bootstrap 5.3.x (レスポンシブUI)

JavaScript:
  - Vanilla JavaScript (ES6+)
  - Chart.js 4.x (グラフ表示)
  - DataTables 1.13.x (テーブル表示)
  - Axios (AJAX通信)

2.3 開発ツール
--------------

バージョン管理:
  - Git

エディタ:
  - VS Code (推奨)
  - Vim/Nano (Linux)

デバッグ:
  - Flask Debug Toolbar (開発時)
  - Python debugger (pdb)

2.4 外部サービス
----------------

メール送信:
  - SMTPLib (Python標準)
  - 外部SMTPサーバー

通知:
  - Microsoft Teams Incoming Webhook

2.5 Windows環境固有
--------------------

サービス化:
  - NSSM (Non-Sucking Service Manager)

ファイアウォール:
  - Windows Defender Firewall

リバースプロキシ (オプション):
  - IIS + wfastcgi
  - IIS + URL Rewrite

================================================================================
3. ディレクトリ構造
================================================================================

backup-management-system/
│
├── app/                          # アプリケーション本体
│   ├── __init__.py               # Flask app初期化
│   ├── models.py                 # データモデル
│   ├── config.py                 # 設定
│   │
│   ├── views/                    # Webビュー
│   │   ├── __init__.py
│   │   ├── dashboard.py
│   │   ├── jobs.py
│   │   ├── media.py
│   │   ├── verification.py
│   │   └── reports.py
│   │
│   ├── api/                      # REST API
│   │   ├── __init__.py
│   │   ├── backup.py
│   │   ├── jobs.py
│   │   └── reports.py
│   │
│   ├── services/                 # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── compliance_checker.py
│   │   ├── alert_manager.py
│   │   └── report_generator.py
│   │
│   ├── auth/                     # 認証・認可
│   │   ├── __init__.py
│   │   └── decorators.py
│   │
│   ├── utils/                    # ユーティリティ
│   │   ├── __init__.py
│   │   ├── email.py
│   │   └── logger.py
│   │
│   ├── scheduler/                # スケジューラー
│   │   ├── __init__.py
│   │   └── tasks.py
│   │
│   ├── templates/                # Jinja2テンプレート
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── jobs/
│   │   │   ├── list.html
│   │   │   ├── detail.html
│   │   │   └── edit.html
│   │   ├── media/
│   │   │   ├── list.html
│   │   │   └── detail.html
│   │   ├── verification/
│   │   │   ├── list.html
│   │   │   └── test.html
│   │   └── reports/
│   │       ├── compliance.html
│   │       └── operational.html
│   │
│   └── static/                   # 静的ファイル
│       ├── css/
│       │   └── custom.css
│       ├── js/
│       │   ├── dashboard.js
│       │   └── common.js
│       └── img/
│           └── logo.png
│
├── migrations/                   # DBマイグレーション (Flask-Migrate)
│   └── versions/
│
├── tests/                        # テストコード
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_api.py
│   └── test_services.py
│
├── scripts/                      # 運用スクリプト
│   ├── init_db.py                # DB初期化
│   ├── create_admin.py           # 管理者作成
│   └── backup_db.py              # DBバックアップ
│
├── docs/                         # ドキュメント
│   ├── user_manual.md
│   ├── admin_manual.md
│   └── api_specification.md
│
├── logs/                         # ログ出力先
│   ├── app.log
│   └── error.log
│
├── data/                         # データ格納
│   └── backup_mgmt.db            # SQLiteファイル
│
├── deployment/                   # デプロイ関連
│   ├── windows/
│   │   ├── install.ps1           # Windowsインストールスクリプト
│   │   ├── nssm-config.txt       # NSSMサービス設定
│   │   └── firewall-rule.ps1    # ファイアウォール設定
│   └── linux/
│       ├── install.sh            # Linuxインストールスクリプト
│       └── systemd/
│           └── backup-mgmt.service
│
├── requirements.txt              # Python依存パッケージ
├── requirements-dev.txt          # 開発用パッケージ
├── .env.example                  # 環境変数テンプレート
├── .gitignore
├── README.md
└── run.py                        # アプリケーション起動スクリプト

================================================================================
4. データベース設計
================================================================================

4.1 ER図 (概念図)
-----------------

[users] 1 ----< ∞ [backup_jobs]
                    |
                    | 1
                    |
                    ∞
              [backup_copies]
                    |
                    | ∞
                    |
                    1
              [offline_media]

[backup_jobs] 1 ----< ∞ [verification_tests]

[backup_jobs] 1 ----< ∞ [backup_executions]

[users] 1 ----< ∞ [audit_logs]

4.2 テーブル定義
----------------

【users テーブル】
ユーザー情報を管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  ユーザーID
username           VARCHAR(50)   NO     UNIQUE              ユーザー名
email              VARCHAR(100)  NO     UNIQUE              メールアドレス
password_hash      VARCHAR(255)  NO                         パスワードハッシュ
full_name          VARCHAR(100)  YES                        氏名
department         VARCHAR(100)  YES                        所属部署
role               VARCHAR(20)   NO                         役割 (admin/operator/viewer/auditor)
is_active          BOOLEAN       NO     DEFAULT TRUE        有効フラグ
last_login         DATETIME      YES                        最終ログイン日時
created_at         DATETIME      NO     DEFAULT NOW()       作成日時
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_username ON username
  - idx_email ON email
  - idx_role ON role


【backup_jobs テーブル】
バックアップジョブ情報を管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  ジョブID
job_name           VARCHAR(100)  NO                         ジョブ名
job_type           VARCHAR(50)   NO                         種別 (system_image/file/database/vm)
target_server      VARCHAR(100)  YES                        対象サーバー
target_path        VARCHAR(500)  YES                        対象パス
backup_tool        VARCHAR(50)   NO                         ツール (veeam/wsb/aomei/custom)
schedule_type      VARCHAR(20)   NO                         スケジュール (daily/weekly/monthly/manual)
retention_days     INTEGER       NO                         保持期間 (日)
owner_id           INTEGER       NO     FK -> users.id      担当者ID
description        TEXT          YES                        説明
is_active          BOOLEAN       NO     DEFAULT TRUE        有効フラグ
created_at         DATETIME      NO     DEFAULT NOW()       作成日時
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_job_name ON job_name
  - idx_job_type ON job_type
  - idx_owner_id ON owner_id
  - idx_is_active ON is_active


【backup_copies テーブル】
バックアップコピー情報を管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  コピーID
job_id             INTEGER       NO     FK -> backup_jobs.id  ジョブID
copy_type          VARCHAR(20)   NO                         種別 (primary/secondary/offsite/offline)
media_type         VARCHAR(20)   NO                         メディア (disk/tape/cloud/external_hdd)
storage_path       VARCHAR(500)  YES                        保存先パス/URL
is_encrypted       BOOLEAN       NO     DEFAULT FALSE       暗号化有無
is_compressed      BOOLEAN       NO     DEFAULT FALSE       圧縮有無
last_backup_date   DATETIME      YES                        最終バックアップ日時
last_backup_size   BIGINT        YES                        最終サイズ (bytes)
status             VARCHAR(20)   NO     DEFAULT 'unknown'   状態 (success/failed/warning/unknown)
offline_media_id   INTEGER       YES    FK -> offline_media.id  オフラインメディアID
created_at         DATETIME      NO     DEFAULT NOW()       作成日時
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_job_id ON job_id
  - idx_copy_type ON copy_type
  - idx_media_type ON media_type
  - idx_offline_media_id ON offline_media_id


【offline_media テーブル】
オフラインメディア情報を管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  メディアID
media_id           VARCHAR(50)   NO     UNIQUE              メディア識別子 (バーコード等)
media_type         VARCHAR(20)   NO                         種別 (external_hdd/tape/usb)
capacity_gb        INTEGER       YES                        容量 (GB)
purchase_date      DATE          YES                        購入日
storage_location   VARCHAR(200)  YES                        保管場所
current_status     VARCHAR(20)   NO     DEFAULT 'available' 状態 (in_use/stored/retired)
owner_id           INTEGER       YES    FK -> users.id      担当者ID
qr_code            TEXT          YES                        QRコード (Base64)
notes              TEXT          YES                        備考
created_at         DATETIME      NO     DEFAULT NOW()       作成日時
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_media_id ON media_id
  - idx_media_type ON media_type
  - idx_current_status ON current_status


【media_rotation_schedule テーブル】
メディアローテーションスケジュール管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  スケジュールID
offline_media_id   INTEGER       NO     FK -> offline_media.id  メディアID
rotation_type      VARCHAR(20)   NO                         方式 (gfs/tower_of_hanoi/custom)
rotation_cycle     VARCHAR(20)   NO                         周期 (weekly/monthly)
next_rotation_date DATE          NO                         次回入れ替え日
last_rotation_date DATE          YES                        前回入れ替え日
is_active          BOOLEAN       NO     DEFAULT TRUE        有効フラグ
created_at         DATETIME      NO     DEFAULT NOW()       作成日時
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_offline_media_id ON offline_media_id
  - idx_next_rotation_date ON next_rotation_date


【media_lending テーブル】
メディア貸出履歴管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  貸出ID
offline_media_id   INTEGER       NO     FK -> offline_media.id  メディアID
borrower_id        INTEGER       NO     FK -> users.id      貸出先ユーザーID
borrow_purpose     VARCHAR(200)  YES                        貸出目的
borrow_date        DATETIME      NO                         貸出日時
expected_return    DATE          NO                         返却予定日
actual_return      DATETIME      YES                        実際の返却日時
return_condition   VARCHAR(20)   YES                        返却時状態 (normal/abnormal)
notes              TEXT          YES                        備考
created_at         DATETIME      NO     DEFAULT NOW()       作成日時
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_offline_media_id ON offline_media_id
  - idx_borrower_id ON borrower_id
  - idx_actual_return ON actual_return (NULL検索用)


【verification_tests テーブル】
検証テスト実施記録

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  テストID
job_id             INTEGER       NO     FK -> backup_jobs.id  ジョブID
test_type          VARCHAR(50)   NO                         種別 (full_restore/partial/integrity)
test_date          DATETIME      NO                         実施日時
tester_id          INTEGER       NO     FK -> users.id      実施者ID
restore_target     VARCHAR(200)  YES                        復元先
test_result        VARCHAR(20)   NO                         結果 (success/failed)
duration_seconds   INTEGER       YES                        所要時間 (秒)
issues_found       TEXT          YES                        発見された問題
notes              TEXT          YES                        備考
created_at         DATETIME      NO     DEFAULT NOW()       作成日時
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_job_id ON job_id
  - idx_test_date ON test_date
  - idx_test_result ON test_result


【verification_schedule テーブル】
検証テストスケジュール管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  スケジュールID
job_id             INTEGER       NO     FK -> backup_jobs.id  ジョブID
test_frequency     VARCHAR(20)   NO                         頻度 (monthly/quarterly/semi-annual/annual)
next_test_date     DATE          NO                         次回テスト日
last_test_date     DATE          YES                        前回テスト日
assigned_to        INTEGER       YES    FK -> users.id      担当者ID
is_active          BOOLEAN       NO     DEFAULT TRUE        有効フラグ
created_at         DATETIME      NO     DEFAULT NOW()       作成日時
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_job_id ON job_id
  - idx_next_test_date ON next_test_date


【backup_executions テーブル】
バックアップ実行履歴

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  実行ID
job_id             INTEGER       NO     FK -> backup_jobs.id  ジョブID
execution_date     DATETIME      NO                         実行日時
execution_result   VARCHAR(20)   NO                         結果 (success/failed/warning)
error_message      TEXT          YES                        エラーメッセージ
backup_size_bytes  BIGINT        YES                        サイズ (bytes)
duration_seconds   INTEGER       YES                        所要時間 (秒)
source_system      VARCHAR(100)  YES                        実行元 (powershell/manual/scheduled)
created_at         DATETIME      NO     DEFAULT NOW()       作成日時

INDEX:
  - idx_job_id ON job_id
  - idx_execution_date ON execution_date
  - idx_execution_result ON execution_result


【compliance_status テーブル】
3-2-1-1-0ルール準拠状況キャッシュ

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  ID
job_id             INTEGER       NO     FK -> backup_jobs.id  ジョブID
check_date         DATETIME      NO                         チェック日時
copies_count       INTEGER       NO                         コピー数
media_types_count  INTEGER       NO                         メディア種類数
has_offsite        BOOLEAN       NO                         オフサイト有無
has_offline        BOOLEAN       NO                         オフライン有無
has_errors         BOOLEAN       NO                         エラー有無
overall_status     VARCHAR(20)   NO                         総合状態 (compliant/non_compliant/warning)
created_at         DATETIME      NO     DEFAULT NOW()       作成日時

INDEX:
  - idx_job_id ON job_id
  - idx_check_date ON check_date
  - idx_overall_status ON overall_status


【alerts テーブル】
アラート管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  アラートID
alert_type         VARCHAR(50)   NO                         種別 (backup_failed/rule_violation等)
severity           VARCHAR(20)   NO                         深刻度 (info/warning/error/critical)
job_id             INTEGER       YES    FK -> backup_jobs.id  関連ジョブID
title              VARCHAR(200)  NO                         タイトル
message            TEXT          NO                         メッセージ
is_acknowledged    BOOLEAN       NO     DEFAULT FALSE       確認済みフラグ
acknowledged_by    INTEGER       YES    FK -> users.id      確認者ID
acknowledged_at    DATETIME      YES                        確認日時
created_at         DATETIME      NO     DEFAULT NOW()       作成日時

INDEX:
  - idx_alert_type ON alert_type
  - idx_severity ON severity
  - idx_is_acknowledged ON is_acknowledged
  - idx_created_at ON created_at


【audit_logs テーブル】
監査ログ

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  ログID
user_id            INTEGER       YES    FK -> users.id      ユーザーID
action_type        VARCHAR(50)   NO                         操作種別
resource_type      VARCHAR(50)   YES                        対象リソース種別
resource_id        INTEGER       YES                        対象リソースID
ip_address         VARCHAR(45)   YES                        IPアドレス
action_result      VARCHAR(20)   NO                         結果 (success/failed)
details            TEXT          YES                        詳細 (JSON)
created_at         DATETIME      NO     DEFAULT NOW()       作成日時

INDEX:
  - idx_user_id ON user_id
  - idx_action_type ON action_type
  - idx_created_at ON created_at


【reports テーブル】
生成されたレポート管理

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  レポートID
report_type        VARCHAR(50)   NO                         種別 (daily/weekly/monthly/compliance/audit)
report_title       VARCHAR(200)  NO                         タイトル
date_from          DATE          NO                         対象期間開始
date_to            DATE          NO                         対象期間終了
file_path          VARCHAR(500)  YES                        ファイルパス
file_format        VARCHAR(10)   NO                         形式 (html/pdf/csv)
generated_by       INTEGER       NO     FK -> users.id      生成者ID
created_at         DATETIME      NO     DEFAULT NOW()       生成日時

INDEX:
  - idx_report_type ON report_type
  - idx_created_at ON created_at


【system_settings テーブル】
システム設定

カラム名           型            NULL   制約                説明
------------------ ------------- ------ ------------------- ---------------------
id                 INTEGER       NO     PK, AUTO_INCREMENT  設定ID
setting_key        VARCHAR(100)  NO     UNIQUE              設定キー
setting_value      TEXT          YES                        設定値
value_type         VARCHAR(20)   NO                         値タイプ (string/int/bool/json)
description        TEXT          YES                        説明
is_encrypted       BOOLEAN       NO     DEFAULT FALSE       暗号化フラグ
updated_by         INTEGER       YES    FK -> users.id      更新者ID
updated_at         DATETIME      NO     DEFAULT NOW()       更新日時

INDEX:
  - idx_setting_key ON setting_key


4.3 SQLAlchemyモデル定義例
---------------------------

【models.py 抜粋】

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, BigInteger, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    department = Column(String(100))
    role = Column(String(20), nullable=False)  # admin, operator, viewer, auditor
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    backup_jobs = relationship('BackupJob', back_populates='owner')
    audit_logs = relationship('AuditLog', back_populates='user')

class BackupJob(db.Model):
    __tablename__ = 'backup_jobs'
    
    id = Column(Integer, primary_key=True)
    job_name = Column(String(100), nullable=False)
    job_type = Column(String(50), nullable=False)
    target_server = Column(String(100))
    target_path = Column(String(500))
    backup_tool = Column(String(50), nullable=False)
    schedule_type = Column(String(20), nullable=False)
    retention_days = Column(Integer, nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship('User', back_populates='backup_jobs')
    copies = relationship('BackupCopy', back_populates='job', cascade='all, delete-orphan')
    executions = relationship('BackupExecution', back_populates='job', cascade='all, delete-orphan')
    verification_tests = relationship('VerificationTest', back_populates='job')

class BackupCopy(db.Model):
    __tablename__ = 'backup_copies'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('backup_jobs.id'), nullable=False)
    copy_type = Column(String(20), nullable=False)
    media_type = Column(String(20), nullable=False)
    storage_path = Column(String(500))
    is_encrypted = Column(Boolean, default=False, nullable=False)
    is_compressed = Column(Boolean, default=False, nullable=False)
    last_backup_date = Column(DateTime)
    last_backup_size = Column(BigInteger)
    status = Column(String(20), default='unknown', nullable=False)
    offline_media_id = Column(Integer, ForeignKey('offline_media.id'))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    job = relationship('BackupJob', back_populates='copies')
    offline_media = relationship('OfflineMedia', back_populates='backup_copies')

# 以下、他のモデルも同様に定義...

4.4 マイグレーション戦略
------------------------

【Flask-Migrate使用】

初期化:
  $ flask db init

マイグレーション作成:
  $ flask db migrate -m "Initial tables"

マイグレーション適用:
  $ flask db upgrade

ロールバック:
  $ flask db downgrade

================================================================================
5. API設計
================================================================================

5.1 REST API設計原則
--------------------

- RESTful設計
- HTTPメソッド: GET, POST, PUT, DELETE
- ステータスコード: 200, 201, 400, 401, 403, 404, 500
- JSON形式
- 認証: Bearer Token
- バージョニング: /api/v1/

5.2 認証
--------

【認証フロー】

1. POST /api/v1/auth/login
   - リクエスト: {"username": "user", "password": "pass"}
   - レスポンス: {"token": "xxx", "expires_in": 3600}

2. 以降のリクエスト
   - Header: Authorization: Bearer {token}

5.3 APIエンドポイント一覧
--------------------------

【バックアップジョブ管理】

GET /api/v1/jobs
  説明: ジョブ一覧取得
  パラメータ: page, per_page, search, job_type, status
  認証: 必要
  権限: operator以上
  レスポンス例:
    {
      "jobs": [
        {
          "id": 1,
          "job_name": "Daily DB Backup",
          "job_type": "database",
          "status": "compliant",
          "last_execution": "2025-10-27T03:00:00Z"
        }
      ],
      "total": 100,
      "page": 1,
      "per_page": 20
    }

GET /api/v1/jobs/{job_id}
  説明: ジョブ詳細取得
  認証: 必要
  権限: operator以上
  レスポンス例:
    {
      "id": 1,
      "job_name": "Daily DB Backup",
      "job_type": "database",
      "target_server": "DB-SERVER-01",
      "backup_tool": "veeam",
      "copies": [
        {
          "id": 1,
          "copy_type": "primary",
          "media_type": "disk",
          "storage_path": "\\\\NAS01\\Backups"
        }
      ],
      "compliance_status": {
        "copies_count": 3,
        "media_types_count": 2,
        "has_offsite": true,
        "has_offline": true,
        "has_errors": false,
        "overall_status": "compliant"
      }
    }

POST /api/v1/jobs
  説明: ジョブ新規登録
  認証: 必要
  権限: operator以上
  リクエスト例:
    {
      "job_name": "New Backup Job",
      "job_type": "file",
      "target_server": "FILE-SERVER-01",
      "target_path": "D:\\Data",
      "backup_tool": "wsb",
      "schedule_type": "daily",
      "retention_days": 30,
      "description": "File server daily backup"
    }
  レスポンス: 201 Created
    {
      "id": 10,
      "message": "Job created successfully"
    }

PUT /api/v1/jobs/{job_id}
  説明: ジョブ更新
  認証: 必要
  権限: operator以上
  リクエスト例:
    {
      "job_name": "Updated Job Name",
      "retention_days": 60
    }
  レスポンス: 200 OK

DELETE /api/v1/jobs/{job_id}
  説明: ジョブ削除
  認証: 必要
  権限: admin
  レスポンス: 204 No Content


【バックアップステータス更新 (PowerShell連携)】

POST /api/v1/backup/status
  説明: バックアップ実行結果の更新
  認証: 必要 (API Token)
  権限: system
  リクエスト例:
    {
      "job_id": 1,
      "execution_date": "2025-10-28T03:00:00Z",
      "execution_result": "success",
      "backup_size_bytes": 10737418240,
      "duration_seconds": 1800,
      "source_system": "powershell"
    }
  レスポンス: 200 OK
    {
      "message": "Status updated successfully",
      "compliance_check": {
        "status": "compliant"
      }
    }


【アラート管理】

GET /api/v1/alerts
  説明: アラート一覧取得
  パラメータ: status (all/unacknowledged), severity, date_from, date_to
  認証: 必要
  権限: operator以上
  レスポンス例:
    {
      "alerts": [
        {
          "id": 1,
          "alert_type": "backup_failed",
          "severity": "error",
          "title": "Backup Failed: Daily DB Backup",
          "message": "Backup job failed due to network error",
          "job_id": 1,
          "is_acknowledged": false,
          "created_at": "2025-10-28T03:30:00Z"
        }
      ],
      "total": 5
    }

PUT /api/v1/alerts/{alert_id}/acknowledge
  説明: アラートを確認済みにする
  認証: 必要
  権限: operator以上
  レスポンス: 200 OK


【レポート生成】

POST /api/v1/reports/generate
  説明: レポート生成
  認証: 必要
  権限: operator以上
  リクエスト例:
    {
      "report_type": "compliance",
      "date_from": "2025-10-01",
      "date_to": "2025-10-31",
      "format": "pdf"
    }
  レスポンス: 202 Accepted
    {
      "report_id": 123,
      "status": "generating",
      "estimated_time": 30
    }

GET /api/v1/reports/{report_id}
  説明: レポートダウンロード
  認証: 必要
  権限: operator以上
  レスポンス: 200 OK (file download) or 404 Not Found


【ダッシュボードデータ】

GET /api/v1/dashboard/summary
  説明: ダッシュボードサマリー取得
  認証: 必要
  権限: viewer以上
  レスポンス例:
    {
      "total_jobs": 100,
      "compliant_jobs": 95,
      "non_compliant_jobs": 3,
      "warning_jobs": 2,
      "success_rate_7days": 99.2,
      "storage_usage": {
        "total_gb": 5000,
        "used_gb": 3500,
        "usage_percent": 70
      },
      "recent_alerts": [...]
    }


【オフラインメディア管理】

GET /api/v1/media
  説明: オフラインメディア一覧
  パラメータ: status, media_type
  認証: 必要
  権限: operator以上

POST /api/v1/media
  説明: オフラインメディア登録
  認証: 必要
  権限: operator以上

GET /api/v1/media/{media_id}
  説明: オフラインメディア詳細
  認証: 必要
  権限: operator以上

PUT /api/v1/media/{media_id}
  説明: オフラインメディア更新
  認証: 必要
  権限: operator以上


【検証テスト管理】

POST /api/v1/verification/tests
  説明: 検証テスト結果登録
  認証: 必要
  権限: operator以上

GET /api/v1/verification/schedule
  説明: 検証スケジュール取得
  認証: 必要
  権限: operator以上


5.4 エラーレスポンス形式
------------------------

【統一エラー形式】

{
  "error": {
    "code": "BACKUP_NOT_FOUND",
    "message": "Backup job with ID 999 not found",
    "details": {
      "job_id": 999
    }
  }
}

【エラーコード一覧】
- AUTHENTICATION_FAILED: 認証失敗
- AUTHORIZATION_FAILED: 認可失敗
- INVALID_REQUEST: 不正なリクエスト
- RESOURCE_NOT_FOUND: リソース未発見
- INTERNAL_SERVER_ERROR: サーバー内部エラー
- BACKUP_NOT_FOUND: バックアップジョブ未発見
- MEDIA_NOT_FOUND: メディア未発見
- VALIDATION_ERROR: バリデーションエラー

5.5 レート制限
--------------

- 認証済みユーザー: 1000リクエスト/時間
- 未認証: 100リクエスト/時間
- レート超過時: 429 Too Many Requests
- Header: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

================================================================================
6. UI設計
================================================================================

6.1 画面一覧
------------

1. ログイン画面
2. ダッシュボード
3. バックアップジョブ一覧
4. バックアップジョブ詳細
5. バックアップジョブ編集
6. オフラインメディア一覧
7. オフラインメディア詳細
8. 検証テスト一覧
9. 検証テスト実施
10. レポート一覧
11. レポート生成
12. アラート一覧
13. ユーザー管理
14. システム設定

6.2 共通レイアウト
------------------

【ヘッダー】
- ロゴ
- ナビゲーションメニュー
  - ダッシュボード
  - バックアップジョブ
  - オフラインメディア
  - 検証テスト
  - レポート
  - アラート
- ユーザーメニュー (ドロップダウン)
  - プロフィール
  - 設定
  - ログアウト
- アラート通知アイコン

【サイドバー (オプション)】
- クイックリンク
- 統計サマリー

【フッター】
- バージョン情報
- サポートリンク
- プライバシーポリシー

6.3 ダッシュボード設計
----------------------

【レイアウト】

+------------------------------------------------------------------+
|  [ヘッダー]                                                       |
+------------------------------------------------------------------+
|                                                                  |
|  [3-2-1-1-0ルール準拠率]                                         |
|  +---------------+  +---------------+  +---------------+         |
|  | 準拠: 95%     |  | 非準拠: 3%    |  | 警告: 2%      |         |
|  | (円グラフ)    |  |               |  |               |         |
|  +---------------+  +---------------+  +---------------+         |
|                                                                  |
|  [バックアップ成功率 (直近7日間)]                                 |
|  +-------------------------------------------------------------+ |
|  |                    (折れ線グラフ)                           | |
|  +-------------------------------------------------------------+ |
|                                                                  |
|  [ストレージ使用状況]           [アラート一覧]                   |
|  +---------------------------+  +---------------------------+   |
|  | (棒グラフ)                |  | • バックアップ失敗         |   |
|  | - オンサイト: 70%        |  | • オフライン更新遅延       |   |
|  | - オフサイト: 60%        |  | • 検証テスト未実施         |   |
|  | - オフライン: 50%        |  +---------------------------+   |
|  +---------------------------+                                  |
|                                                                  |
|  [次回実行予定ジョブ]                                             |
|  +-------------------------------------------------------------+ |
|  | ジョブ名              | 予定時刻         | 種別            | |
|  +-------------------------------------------------------------+ |
|  | Daily DB Backup       | 2025-10-29 03:00 | database        | |
|  | File Server Backup    | 2025-10-29 01:00 | file            | |
|  +-------------------------------------------------------------+ |
|                                                                  |
+------------------------------------------------------------------+
|  [フッター]                                                       |
+------------------------------------------------------------------+

6.4 バックアップジョブ一覧画面
------------------------------

【機能】
- 検索・フィルタリング (ジョブ名、種別、担当者、ステータス)
- ソート (各カラム)
- ページネーション
- 一括操作 (削除、有効/無効化)
- 新規登録ボタン
- エクスポート (CSV)

【テーブルカラム】
- チェックボックス
- ジョブID
- ジョブ名
- 種別
- 担当者
- 最終実行日時
- 実行結果
- 準拠状況 (○/×/△)
- アクション (詳細/編集/削除)

6.5 バックアップジョブ詳細画面
------------------------------

【セクション】

1. 基本情報
   - ジョブ名、種別、対象サーバー、ツール等

2. 3-2-1-1-0ルール準拠状況
   - 各要件の充足状況を可視化
   - コピー一覧

3. 実行履歴
   - 直近10件の実行結果
   - グラフ表示 (成功/失敗推移)

4. 検証テスト履歴
   - 直近のテスト結果

5. アラート履歴
   - このジョブに関連するアラート

6.6 カラースキーム
------------------

【ステータスカラー】
- 成功 (Success): #28a745 (緑)
- 警告 (Warning): #ffc107 (黄)
- エラー (Error): #dc3545 (赤)
- 情報 (Info): #17a2b8 (青)

【準拠状況カラー】
- 準拠 (Compliant): #28a745 (緑)
- 非準拠 (Non-compliant): #dc3545 (赤)
- 警告 (Warning): #ffc107 (黄)

6.7 レスポンシブデザイン
------------------------

【ブレークポイント】
- XS: < 576px (スマートフォン)
- SM: ≥ 576px (タブレット縦)
- MD: ≥ 768px (タブレット横)
- LG: ≥ 992px (デスクトップ)
- XL: ≥ 1200px (大型デスクトップ)

【対応方針】
- Bootstrap 5のグリッドシステム使用
- モバイルファーストアプローチ
- ハンバーガーメニュー (SM以下)
- テーブルのスクロール対応

================================================================================
7. セキュリティ設計
================================================================================

7.1 認証設計
------------

【パスワードポリシー】
- 最低8文字
- 英大文字、英小文字、数字、記号の3種類以上
- パスワード有効期限: 90日
- 過去3世代のパスワード再利用禁止
- ハッシュ化: bcrypt (work factor: 12)

【セッション管理】
- セッションタイムアウト: 30分
- セキュアクッキー (HttpOnly, Secure, SameSite=Strict)
- CSRF対策: Flask-WTF CSRFトークン
- セッションIDの再生成 (ログイン時)

【ログイン保護】
- ログイン試行回数制限: 5回/10分
- アカウントロックアウト: 10分間
- ログイン失敗時の遅延: 1秒
- ログイン失敗ログの記録

7.2 認可設計
------------

【役割定義】

システム管理者 (admin):
  - 全機能へのアクセス
  - ユーザー管理
  - システム設定変更
  - ジョブの登録・編集・削除

バックアップ管理者 (operator):
  - バックアップ運用
  - ジョブの登録・編集
  - 検証テスト実施
  - レポート閲覧・生成

閲覧者 (viewer):
  - ダッシュボード閲覧
  - ジョブ一覧・詳細閲覧
  - レポート閲覧のみ

監査担当者 (auditor):
  - 監査ログ閲覧
  - コンプライアンスレポート閲覧
  - システム設定閲覧 (変更不可)

【権限マトリックス】

機能                     admin  operator  viewer  auditor
----------------------  -----  --------  ------  -------
ダッシュボード閲覧        ○      ○        ○       ○
ジョブ閲覧                ○      ○        ○       ○
ジョブ登録・編集          ○      ○        ×       ×
ジョブ削除                ○      ×        ×       ×
オフラインメディア管理    ○      ○        ×       ×
検証テスト実施            ○      ○        ×       ×
レポート閲覧              ○      ○        ○       ○
レポート生成              ○      ○        ×       ○
監査ログ閲覧              ○      ×        ×       ○
ユーザー管理              ○      ×        ×       ×
システム設定              ○      ×        ×       ×

7.3 データ保護
--------------

【暗号化】

転送中:
  - HTTPS (TLS 1.2以上) 必須
  - 証明書: Let's Encrypt (推奨) または商用証明書
  - 自己署名証明書は開発環境のみ

保存時:
  - パスワード: bcrypt (work factor 12)
  - APIトークン: 暗号化保存
  - 機密設定値: 暗号化保存

【データマスキング】
- ログ出力時のパスワードマスキング
- 監査ログからの機密情報除外
- API応答からのパスワードハッシュ除外

7.4 入力検証
------------

【検証項目】
- データ型チェック
- 長さチェック
- 形式チェック (メールアドレス、URL等)
- 範囲チェック (数値)
- SQLインジェクション対策 (ORM使用)
- XSS対策 (テンプレートエスケープ)
- ファイルアップロード検証 (拡張子、MIMEタイプ、サイズ)

【Flask-WTF使用】
- フォームバリデーション
- CSRFトークン自動付与

7.5 セキュリティヘッダー
------------------------

【推奨ヘッダー】
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000; includeSubDomains
- Content-Security-Policy: default-src 'self'

【Flask-Talisman使用】
自動的にセキュリティヘッダーを付与

7.6 脆弱性対策
--------------

【依存パッケージ管理】
- 定期的な更新 (月次)
- pip-audit実行 (脆弱性スキャン)
- requirements.txt固定バージョン指定

【セキュリティスキャン】
- Banditによる静的解析
- OWASP ZAPによる動的解析 (四半期)

7.7 ログセキュリティ
--------------------

【監査ログ要件】
- 改ざん防止 (append-only)
- アクセス制限 (admin, auditor のみ)
- 長期保存 (3年間)
- 定期的なバックアップ

【ログ記録項目】
- 日時
- ユーザーID
- IPアドレス
- 操作種別
- 対象リソース
- 結果 (成功/失敗)
- 詳細情報

================================================================================
8. 認証・認可設計
================================================================================

8.1 Flask-Login統合
-------------------

【設定】

from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

【Userモデル拡張】

class User(UserMixin, db.Model):
    # ... (既存のカラム定義)
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def has_role(self, role):
        return self.role == role
    
    def has_any_role(self, *roles):
        return self.role in roles

8.2 権限チェックデコレーター
----------------------------

【decorators.py】

from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    """指定された役割を持つユーザーのみアクセス可能"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_any_role(*roles):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """管理者のみアクセス可能"""
    return role_required('admin')(f)

def operator_required(f):
    """オペレーター以上のアクセス可能"""
    return role_required('admin', 'operator')(f)

【使用例】

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/jobs/create')
@operator_required
def create_job():
    return render_template('jobs/create.html')

8.3 API認証
-----------

【トークンベース認証】

トークン生成:
  - ログイン成功時にJWT生成
  - 有効期限: 1時間
  - リフレッシュトークン (7日間)

トークン検証:
  - Authorizationヘッダーから取得
  - 署名検証
  - 有効期限チェック

【実装例】

import jwt
from datetime import datetime, timedelta

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

8.4 Active Directory統合 (将来対応)
------------------------------------

【LDAP認証】

from ldap3 import Server, Connection, ALL

def authenticate_ldap(username, password):
    server = Server(app.config['LDAP_SERVER'], get_info=ALL)
    conn = Connection(server, user=f'{username}@{app.config["LDAP_DOMAIN"]}', 
                      password=password, auto_bind=True)
    
    if conn.bind():
        # ユーザー情報取得
        conn.search(app.config['LDAP_BASE_DN'], 
                    f'(sAMAccountName={username})', 
                    attributes=['mail', 'displayName'])
        return conn.entries[0]
    return None

================================================================================
9. ログ設計
================================================================================

9.1 ログレベル
--------------

DEBUG: 開発時のデバッグ情報
INFO: 通常の動作ログ
WARNING: 警告 (処理は継続)
ERROR: エラー (処理失敗)
CRITICAL: 致命的エラー (システム停止)

9.2 ログ出力先
--------------

【開発環境】
- コンソール出力
- ファイル: logs/app.log

【本番環境】
- ファイル: logs/app.log (日次ローテーション)
- エラーログ: logs/error.log
- Windows Event Log (オプション)

9.3 ログ設定
------------

【logging.conf】

[loggers]
keys=root,app

[handlers]
keys=consoleHandler,fileHandler,errorHandler

[formatters]
keys=detailed

[logger_root]
level=INFO
handlers=consoleHandler

[logger_app]
level=INFO
handlers=fileHandler,errorHandler
qualname=app
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=DEBUG
formatter=detailed
args=(sys.stdout,)

[handler_fileHandler]
class=handlers.TimedRotatingFileHandler
level=INFO
formatter=detailed
args=('logs/app.log', 'midnight', 1, 90)

[handler_errorHandler]
class=handlers.TimedRotatingFileHandler
level=ERROR
formatter=detailed
args=('logs/error.log', 'midnight', 1, 90)

[formatter_detailed]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S

9.4 ログ出力例
--------------

【アプリケーションログ】

2025-10-28 10:30:15 - app - INFO - User 'admin' logged in from 192.168.1.100
2025-10-28 10:31:22 - app - INFO - Backup job 'Daily DB Backup' created by user 'admin'
2025-10-28 10:35:18 - app - WARNING - Backup job 5 is not compliant with 3-2-1-1-0 rule
2025-10-28 10:40:05 - app - ERROR - Failed to send email notification: SMTP connection error

【監査ログ】

データベースに記録 (audit_logs テーブル)

9.5 ログローテーション
----------------------

- 日次ローテーション (午前0時)
- 保存期間: 90日
- 圧縮: gzip
- 古いログの自動削除

================================================================================
10. 通知設計
================================================================================

10.1 メール通知
---------------

【SMTP設定】

SMTP_SERVER: mail.example.com
SMTP_PORT: 587 (STARTTLS) or 465 (SSL)
SMTP_USERNAME: backup-system@example.com
SMTP_PASSWORD: (環境変数)
SMTP_FROM: Backup Management System <backup-system@example.com>

【メールテンプレート】

templates/email/
├── backup_failed.html
├── rule_violation.html
├── media_rotation_reminder.html
├── verification_reminder.html
└── daily_report.html

【送信タイミング】
- バックアップ失敗時: 即時
- ルール非準拠検知: 即時
- オフラインメディア更新遅延: 日次チェック
- 検証テストリマインダー: 7日前
- 日次レポート: 毎朝8:00

10.2 Microsoft Teams通知
-------------------------

【Incoming Webhook】

Webhook URL: (チャネル設定から取得)
通知形式: Adaptive Card

【Adaptive Card例】

{
  "type": "message",
  "attachments": [
    {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
          {
            "type": "TextBlock",
            "text": "バックアップ失敗",
            "weight": "Bolder",
            "size": "Large",
            "color": "Attention"
          },
          {
            "type": "FactSet",
            "facts": [
              {"title": "ジョブ名", "value": "Daily DB Backup"},
              {"title": "サーバー", "value": "DB-SERVER-01"},
              {"title": "日時", "value": "2025-10-28 03:00"},
              {"title": "エラー", "value": "ネットワークタイムアウト"}
            ]
          }
        ],
        "actions": [
          {
            "type": "Action.OpenUrl",
            "title": "詳細を見る",
            "url": "https://backup-mgmt.example.com/jobs/1"
          }
        ]
      }
    }
  ]
}

10.3 ダッシュボード通知
-----------------------

【通知バナー】
- 画面上部に表示
- 種別に応じた色分け (成功/警告/エラー)
- 閉じるボタン
- 詳細リンク

【ベルアイコン】
- ヘッダーに配置
- 未読件数バッジ
- クリックでドロップダウン表示
- 最新10件の通知

10.4 通知設定
-------------

【ユーザー別通知設定】
- メール通知の有効/無効
- Teams通知の有効/無効
- 通知レベルの選択 (すべて/エラーのみ/重要のみ)
- 通知時間帯の設定 (営業時間のみ等)

================================================================================
11. デプロイメント設計
================================================================================

11.1 Linux開発環境セットアップ
-------------------------------

【Ubuntu 22.04/24.04 LTS】

# システム更新
sudo apt update && sudo apt upgrade -y

# Python関連
sudo apt install python3 python3-pip python3-venv -y

# プロジェクトクローン
cd ~
git clone https://github.com/your-repo/backup-management-system.git
cd backup-management-system

# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# パッケージインストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
nano .env

# データベース初期化
flask db upgrade
python scripts/init_db.py

# 管理者作成
python scripts/create_admin.py

# 開発サーバー起動
flask run --host=0.0.0.0 --port=5000

11.2 Windows 11本番環境セットアップ
------------------------------------

【前提条件】
- Windows 11 Enterprise
- Python 3.10以上インストール済み
- Git for Windowsインストール済み

【インストール手順】

# 1. プロジェクトクローン
cd C:\Apps
git clone https://github.com/your-repo/backup-management-system.git
cd backup-management-system

# 2. 仮想環境作成
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. パッケージインストール
pip install -r requirements.txt

# 4. 環境変数設定
copy .env.example .env
notepad .env
# SECRET_KEY, DATABASE_URL等を設定

# 5. データベース初期化
$env:FLASK_APP="run.py"
flask db upgrade
python scripts\init_db.py

# 6. 管理者作成
python scripts\create_admin.py

# 7. 動作確認
python run.py
# ブラウザで http://localhost:5000 にアクセス

【サービス化 (NSSM使用)】

# NSSMダウンロード
# https://nssm.cc/download

# サービスインストール
nssm install BackupManagementSystem "C:\Apps\backup-management-system\venv\Scripts\python.exe" "C:\Apps\backup-management-system\run.py"

# サービス設定
nssm set BackupManagementSystem AppDirectory "C:\Apps\backup-management-system"
nssm set BackupManagementSystem AppStdout "C:\Apps\backup-management-system\logs\service.log"
nssm set BackupManagementSystem AppStderr "C:\Apps\backup-management-system\logs\service-error.log"

# 環境変数設定
nssm set BackupManagementSystem AppEnvironmentExtra FLASK_ENV=production

# サービス開始
nssm start BackupManagementSystem

# サービス状態確認
nssm status BackupManagementSystem

【ファイアウォール設定】

New-NetFirewallRule -DisplayName "Backup Management System" `
                    -Direction Inbound `
                    -LocalPort 5000 `
                    -Protocol TCP `
                    -Action Allow

11.3 IIS統合 (オプション)
--------------------------

【wfastcgi使用】

# wfastcgiインストール
pip install wfastcgi
wfastcgi-enable

# IISサイト作成
# - アプリケーションプール作成 (.NET CLR version: No Managed Code)
# - 物理パス: C:\Apps\backup-management-system
# - web.config作成

【web.config例】

<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="Python FastCGI" 
           path="*" 
           verb="*" 
           modules="FastCgiModule" 
           scriptProcessor="C:\Apps\backup-management-system\venv\Scripts\python.exe|C:\Apps\backup-management-system\venv\Lib\site-packages\wfastcgi.py" 
           resourceType="Unspecified" 
           requireAccess="Script" />
    </handlers>
  </system.webServer>
  <appSettings>
    <add key="PYTHONPATH" value="C:\Apps\backup-management-system" />
    <add key="WSGI_HANDLER" value="run.app" />
    <add key="WSGI_LOG" value="C:\Apps\backup-management-system\logs\wfastcgi.log" />
  </appSettings>
</configuration>

11.4 デプロイチェックリスト
----------------------------

□ Python 3.10以上インストール済み
□ Gitインストール済み
□ プロジェクトクローン完了
□ 仮想環境作成完了
□ 依存パッケージインストール完了
□ .env設定完了
□ SECRET_KEY生成・設定
□ データベース初期化完了
□ 管理者ユーザー作成完了
□ ファイアウォール設定完了
□ サービス化完了 (NSSM or IIS)
□ サービス自動起動設定
□ ログディレクトリ作成・権限設定
□ バックアップスクリプト配置
□ 動作確認完了

11.5 アップデート手順
----------------------

【Linux】

cd ~/backup-management-system
source venv/bin/activate
git pull origin main
pip install -r requirements.txt --upgrade
flask db upgrade
sudo systemctl restart backup-mgmt

【Windows】

cd C:\Apps\backup-management-system
.\venv\Scripts\Activate.ps1
git pull origin main
pip install -r requirements.txt --upgrade
flask db upgrade
nssm restart BackupManagementSystem

11.6 ロールバック手順
----------------------

# 前のコミットに戻す
git checkout <previous-commit-hash>

# データベースロールバック
flask db downgrade

# サービス再起動
nssm restart BackupManagementSystem

================================================================================
12. 運用設計
================================================================================

12.1 バックアップ
-----------------

【システムデータベースのバックアップ】

スケジュール: 日次 (午前3:00)
保存先: D:\Backups\BackupMgmtDB
保持期間: 7世代

【バックアップスクリプト (Windows PowerShell)】

# backup_db.ps1
$BackupDir = "D:\Backups\BackupMgmtDB"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = "$BackupDir\backup_mgmt_$Timestamp.db"

# データベースファイルをコピー
Copy-Item "C:\Apps\backup-management-system\data\backup_mgmt.db" $BackupFile

# 古いバックアップを削除 (7世代保持)
Get-ChildItem $BackupDir -Filter "backup_mgmt_*.db" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -Skip 7 | 
    Remove-Item

# タスクスケジューラーで定期実行
$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\Apps\backup-management-system\scripts\backup_db.ps1"
$Trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
Register-ScheduledTask -Action $Action -Trigger $Trigger -TaskName "BackupManagementDB-Backup" -Description "Daily backup of Backup Management System database"

12.2 監視
---------

【監視項目】

プロセス監視:
  - サービス稼働状態 (NSSM経由)
  - CPU使用率
  - メモリ使用率

ディスク監視:
  - ディスク使用率
  - ログディレクトリ容量
  - データベースファイルサイズ

アプリケーション監視:
  - エラーログ監視 (error.log)
  - アラート未確認件数
  - バックアップ失敗率

【Windows Performance Monitor】

カウンター追加:
  - Process(python)\% Processor Time
  - Process(python)\Working Set
  - LogicalDisk(C:)\% Free Space

【監視スクリプト例】

# monitor.ps1
$ServiceName = "BackupManagementSystem"
$Service = Get-Service $ServiceName

if ($Service.Status -ne 'Running') {
    # サービス停止時の処理
    Start-Service $ServiceName
    Send-MailMessage -To "admin@example.com" `
                     -From "monitor@example.com" `
                     -Subject "[Alert] Backup Management System stopped" `
                     -Body "Service was stopped and restarted automatically."
}

12.3 ログ管理
-------------

【ログローテーション】
- 日次ローテーション
- 保存期間: 90日
- 圧縮: gzip (Linux) / zip (Windows)

【ログ確認コマンド】

# 最新のエラーログ確認
tail -f logs/error.log  # Linux
Get-Content logs\error.log -Tail 50 -Wait  # Windows

# ログ検索
grep "ERROR" logs/app.log  # Linux
Select-String -Path logs\app.log -Pattern "ERROR"  # Windows

12.4 定期メンテナンス
---------------------

【日次】
- システムログ確認
- アラート確認
- バックアップ実行確認

【週次】
- ディスク容量確認
- パフォーマンス確認
- 未解決アラート確認

【月次】
- セキュリティパッチ適用
- 依存パッケージ更新
- データベース最適化
- コンプライアンスレポート確認

【四半期】
- 脆弱性スキャン
- 復旧テスト
- ドキュメント更新

【年次】
- システム監査
- バックアップ戦略見直し
- 容量計画見直し

12.5 トラブルシューティング
---------------------------

【サービス起動失敗】

原因:
  - ポート競合
  - 設定ファイルエラー
  - データベース接続エラー

対応:
  1. ログ確認 (logs/error.log)
  2. ポート使用状況確認 (netstat -ano | findstr :5000)
  3. 設定ファイル確認 (.env)
  4. データベースファイル存在確認

【パフォーマンス低下】

原因:
  - データベース肥大化
  - ログファイル肥大化
  - メモリ不足

対応:
  1. データベース最適化 (VACUUM)
  2. 古いログ削除
  3. リソース使用状況確認
  4. インデックス再構築

【データベース破損】

対応:
  1. サービス停止
  2. 最新バックアップからリストア
  3. トランザクションログ適用 (PostgreSQL使用時)
  4. 整合性チェック
  5. サービス再開

================================================================================
13. テスト設計
================================================================================

13.1 テスト戦略
---------------

【テストレベル】
1. 単体テスト (Unit Test)
2. 統合テスト (Integration Test)
3. システムテスト (System Test)
4. ユーザー受入テスト (UAT)

【テストフレームワーク】
- pytest
- Flask-Testing
- coverage (カバレッジ測定)

13.2 単体テスト
---------------

【対象】
- モデルメソッド
- ビジネスロジック
- ユーティリティ関数

【テストケース例】

# tests/test_models.py

import pytest
from app.models import BackupJob, BackupCopy

def test_backup_job_creation():
    job = BackupJob(
        job_name="Test Job",
        job_type="file",
        backup_tool="wsb",
        schedule_type="daily",
        retention_days=30,
        owner_id=1
    )
    assert job.job_name == "Test Job"
    assert job.is_active == True

def test_compliance_check_compliant():
    job = BackupJob(id=1, job_name="Test")
    
    # 3コピー
    copy1 = BackupCopy(job_id=1, copy_type='primary', media_type='disk')
    copy2 = BackupCopy(job_id=1, copy_type='secondary', media_type='tape')
    copy3 = BackupCopy(job_id=1, copy_type='offline', media_type='external_hdd')
    
    job.copies = [copy1, copy2, copy3]
    
    status = job.check_compliance()
    assert status['copies_count'] >= 3
    assert status['media_types_count'] >= 2
    assert status['overall_status'] == 'compliant'

# tests/test_services.py

from app.services.compliance_checker import ComplianceChecker

def test_compliance_checker():
    checker = ComplianceChecker()
    
    job_data = {
        'copies': [
            {'copy_type': 'primary', 'media_type': 'disk'},
            {'copy_type': 'offsite', 'media_type': 'cloud'},
            {'copy_type': 'offline', 'media_type': 'tape'}
        ],
        'has_errors': False
    }
    
    result = checker.check_3_2_1_1_0(job_data)
    assert result['compliant'] == True

13.3 統合テスト
---------------

【対象】
- APIエンドポイント
- データベース連携
- 外部サービス連携

【テストケース例】

# tests/test_api.py

import pytest
from app import create_app, db

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_login(client):
    response = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': 'password'
    })
    assert response.status_code == 200
    assert 'token' in response.json

def test_get_jobs_unauthorized(client):
    response = client.get('/api/v1/jobs')
    assert response.status_code == 401

def test_get_jobs_authorized(client):
    # ログイン
    login_response = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': 'password'
    })
    token = login_response.json['token']
    
    # ジョブ一覧取得
    response = client.get('/api/v1/jobs', headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 200
    assert 'jobs' in response.json

def test_create_job(client):
    # ログイン
    login_response = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': 'password'
    })
    token = login_response.json['token']
    
    # ジョブ作成
    response = client.post('/api/v1/jobs', 
        headers={'Authorization': f'Bearer {token}'},
        json={
            'job_name': 'Test Job',
            'job_type': 'file',
            'backup_tool': 'wsb',
            'schedule_type': 'daily',
            'retention_days': 30
        }
    )
    assert response.status_code == 201
    assert response.json['id'] > 0

13.4 システムテスト
-------------------

【対象】
- エンドツーエンド機能
- パフォーマンス
- セキュリティ

【テストシナリオ例】

シナリオ1: バックアップジョブ登録から検証まで
1. ログイン
2. バックアップジョブ登録
3. コピー追加 (3種類)
4. 3-2-1-1-0準拠状況確認
5. PowerShellからステータス更新
6. 検証テスト実施
7. レポート生成

シナリオ2: アラート通知フロー
1. バックアップ失敗をシミュレート
2. アラート生成確認
3. メール送信確認
4. ダッシュボード表示確認
5. アラート確認処理

13.5 パフォーマンステスト
-------------------------

【負荷テスト】

ツール: Locust

locustfile.py:

from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # ログイン
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test",
            "password": "password"
        })
        self.token = response.json()["token"]
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/dashboard", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(2)
    def view_jobs(self):
        self.client.get("/api/v1/jobs", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(1)
    def view_job_detail(self):
        self.client.get("/api/v1/jobs/1", headers={
            "Authorization": f"Bearer {self.token}"
        })

実行:
locust -f locustfile.py --host=http://localhost:5000

目標:
- 同時ユーザー: 50
- レスポンスタイム: 95パーセンタイルで3秒以内
- エラー率: 0.1%以下

13.6 セキュリティテスト
-----------------------

【脆弱性スキャン】

ツール: OWASP ZAP, Bandit

実行:
# 静的解析
bandit -r app/

# 動的スキャン
zap-cli quick-scan --self-contained http://localhost:5000

【ペネトレーションテスト項目】
- SQLインジェクション
- XSS
- CSRF
- 認証バイパス
- セッションハイジャック
- ディレクトリトラバーサル

13.7 テスト自動化
-----------------

【CI/CD統合】

GitHub Actionsワークフロー例:

.github/workflows/test.yml:

name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=app tests/
    
    - name: Security scan
      run: |
        bandit -r app/

================================================================================
14. パフォーマンス設計
================================================================================

14.1 データベース最適化
-----------------------

【インデックス戦略】
- 頻繁に検索されるカラムにインデックス
- 外部キーに自動インデックス
- 複合インデックス (検索条件の組み合わせ)

【クエリ最適化】
- N+1問題の回避 (SQLAlchemy joinedload使用)
- ページネーション実装
- SELECT句の最小化 (必要なカラムのみ)

【コネクションプーリング】

SQLAlchemyエンジン設定:

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

14.2 キャッシング
-----------------

【Flask-Caching (将来対応)】

from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'simple',  # または 'redis'
    'CACHE_DEFAULT_TIMEOUT': 300
})

@cache.cached(timeout=60, key_prefix='dashboard_summary')
def get_dashboard_summary():
    # 重い処理
    return summary

14.3 非同期処理 (将来対応)
---------------------------

【Celery統合】

長時間実行タスク:
- レポート生成
- 大量データエクスポート
- メール一括送信

celery_tasks.py:

from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def generate_report(report_type, date_from, date_to):
    # レポート生成処理
    pass

================================================================================
15. 監視設計
================================================================================

15.1 ヘルスチェックエンドポイント
---------------------------------

GET /health
  説明: システムヘルスチェック
  認証: 不要
  レスポンス例:
    {
      "status": "healthy",
      "database": "connected",
      "disk_usage": 65,
      "memory_usage": 45,
      "uptime": 86400
    }

15.2 メトリクス収集 (将来対応)
-------------------------------

【Prometheus統合】

from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)

メトリクス:
- リクエスト数
- レスポンスタイム
- エラー率
- データベース接続数

15.3 アラート設定
-----------------

【監視アラート】
- サービス停止: 即時
- ディスク使用率 > 80%: 警告
- メモリ使用率 > 90%: 警告
- エラー率 > 5%: 警告
- レスポンスタイム > 5秒: 警告

================================================================================
承認
================================================================================

本設計仕様書は、以下の承認を得た上で有効となる。

システムアーキテクト: _______________________ 日付: __________

ITシステム運用管理者: _______________________ 日付: __________

情報セキュリティ管理者: _____________________ 日付: __________

プロジェクトマネージャー: ___________________ 日付: __________


================================================================================
改訂履歴
================================================================================

版番号  日付         改訂内容                           承認者
------  -----------  ---------------------------------  --------------------
1.0     2025/10/28   初版作成                           [承認者名]


================================================================================
以上
================================================================================
