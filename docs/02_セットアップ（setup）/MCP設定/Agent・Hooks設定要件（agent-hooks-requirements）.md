================================================================================
              Agent機能・Hooks並列開発 設定要件書
           3-2-1-1-0バックアップ管理システム
================================================================================

文書番号: AGENT-CONFIG-001
版番号: 1.0
作成日: 2025年10月30日
プロジェクト: backup-management-system
GitHubリポジトリ: https://github.com/Kensan196948G/backup-management-system

================================================================================
目次
================================================================================

1. Agent機能の概要
2. システムアーキテクチャ
3. 10体のサブエージェント詳細仕様
4. Hooks並列開発機能
5. Agent間連携プロトコル
6. タスク管理・ワークフロー
7. Git戦略とブランチ管理
8. セットアップ手順
9. 開発フロー実例
10. モニタリング・デバッグ
11. トラブルシューティング
12. ベストプラクティス

================================================================================
1. Agent機能の概要
================================================================================

1.1 目的
--------

【Agent機能の目的】
- 複雑な開発タスクを並列化して開発速度を向上
- 各分野のエキスパートAgentによる高品質なコード生成
- 人間の開発者は全体調整と重要な意思決定に集中
- 継続的なコード品質とテストカバレッジの維持

【適用プロジェクト】
3-2-1-1-0バックアップ管理システム
- Flask Webアプリケーション
- SQLiteデータベース
- REST API
- PowerShell統合
- クロスプラットフォーム対応（Linux開発、Windows本番）

1.2 Agent機能の利点
-------------------

【開発速度】
- 単一開発者による逐次開発と比較して3-5倍高速化
- 複数機能を同時並行で開発
- 待機時間の削減

【品質向上】
- 各分野の専門家による実装
- 自動テスト生成
- コードレビューの組み込み

【一貫性】
- 統一されたコーディング規約
- ドキュメントの自動更新
- 設計パターンの統一

【スケーラビリティ】
- 必要に応じてAgent数を調整可能
- 新機能追加が容易
- 保守性の向上

1.3 システム要件
----------------

【ハードウェア要件】
- CPU: 8コア以上推奨（並列処理のため）
- RAM: 16GB以上推奨
- ストレージ: SSD推奨（高速I/O）

【ソフトウェア要件】
- Linux: Ubuntu 22.04/24.04 LTS
- Python: 3.11以上
- Node.js: 18以上
- Git: 2.30以上
- Claude Desktop: 最新版
- Docker: 24以上（オプション）

【ネットワーク要件】
- GitHub接続: 常時
- Claude API接続: 常時
- 帯域幅: 10Mbps以上推奨

================================================================================
2. システムアーキテクチャ
================================================================================

2.1 全体構成
------------

┌──────────────────────────────────────────────────────────────┐
│                   人間開発者（統括・意思決定）                │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────────┐
│  Agent 1: プロジェクトマネージャー（PM Agent）               │
│  - タスク分解・優先順位付け                                  │
│  - 他Agentへの指示・調整                                     │
│  - 進捗管理・報告                                            │
└────────────────────────┬─────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ↓                ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Agent 2      │  │ Agent 3      │  │ Agent 4      │
│ データベース │  │ バックエンド │  │ フロント     │
│ アーキテクト │  │ API開発      │  │ エンド開発   │
└──────────────┘  └──────────────┘  └──────────────┘
        ↓                ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Agent 5      │  │ Agent 6      │  │ Agent 7      │
│ 認証・       │  │ ビジネス     │  │ スケジュー   │
│ セキュリティ │  │ ロジック開発 │  │ ラー・通知   │
└──────────────┘  └──────────────┘  └──────────────┘
        ↓                ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Agent 8      │  │ Agent 9      │  │ Agent 10     │
│ PowerShell   │  │ テスト       │  │ DevOps/      │
│ 統合         │  │ エンジニア   │  │ デプロイ     │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┴────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│              Hooks並列実行エンジン                           │
│  - Git Hooks (pre-commit, pre-push, post-merge)             │
│  - GitHub Actions (CI/CD)                                    │
│  - 並列タスク管理                                            │
└────────────────────────┬─────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                   統合・テスト・デプロイ                     │
│  - コード統合（develop ブランチ）                            │
│  - 自動テスト実行                                            │
│  - コードレビュー                                            │
│  - 本番デプロイ（main ブランチ）                             │
└──────────────────────────────────────────────────────────────┘

2.2 通信プロトコル
------------------

【Agent間通信】

方法1: GitHub Issues/Pull Requests
  - 各Agentがタスクとして作成
  - コメントで進捗報告
  - ラベルで状態管理

方法2: Context7（長期記憶）
  - プロジェクト全体の状態共有
  - 決定事項の記録
  - ナレッジベース

方法3: 共有ドキュメント
  - docs/agent-communication/
  - JSON形式の状態ファイル
  - マークダウン形式の報告書

【データフォーマット】

Agent間メッセージ構造:
```json
{
  "from": "Agent-2-Database",
  "to": "Agent-3-Backend-API",
  "timestamp": "2025-10-30T10:00:00Z",
  "type": "task_completion",
  "subject": "Database models completed",
  "body": {
    "task_id": "DB-001",
    "status": "completed",
    "deliverables": [
      "app/models.py",
      "migrations/versions/001_initial.py"
    ],
    "dependencies_resolved": [
      "SQLAlchemy models ready for API integration"
    ],
    "next_actions": [
      "Agent-3 can now implement API endpoints"
    ]
  },
  "attachments": [
    {
      "type": "code",
      "path": "app/models.py",
      "commit": "abc123def456"
    }
  ]
}
```

2.3 状態管理
------------

【グローバル状態】

プロジェクト状態ファイル:
docs/agent-communication/project-state.json

```json
{
  "project": {
    "name": "backup-management-system",
    "phase": "development",
    "sprint": 1,
    "version": "0.1.0-dev"
  },
  "agents": {
    "agent-1-pm": {
      "status": "active",
      "current_task": "Sprint planning",
      "last_update": "2025-10-30T10:00:00Z"
    },
    "agent-2-database": {
      "status": "working",
      "current_task": "DB-001: Implement models",
      "progress": 75,
      "estimated_completion": "2025-10-30T12:00:00Z"
    }
  },
  "tasks": {
    "total": 50,
    "completed": 12,
    "in_progress": 8,
    "blocked": 2,
    "pending": 28
  },
  "builds": {
    "last_success": "2025-10-30T09:00:00Z",
    "last_failure": null,
    "test_coverage": 82.5
  }
}
```

================================================================================
3. 10体のサブエージェント詳細仕様
================================================================================

3.1 Agent 1: プロジェクトマネージャー（PM Agent）
------------------------------------------------

【役割】
プロジェクト全体の統括、タスク管理、進捗管理

【責任範囲】
- 要件定義書・設計仕様書の理解と分解
- 各Agentへのタスク割り当て
- 優先順位の決定
- 依存関係の管理
- 進捗監視とレポーティング
- ボトルネックの特定と解消
- リスク管理
- ドキュメント統括

【担当ファイル】
- README.md
- docs/開発進捗.md
- docs/タスク一覧.md
- docs/agent-communication/project-state.json
- docs/スプリント計画.md
- CHANGELOG.md

【必要なスキル】
- プロジェクト管理
- タスク分解
- 優先順位付け
- コミュニケーション
- リスク管理

【ワークフロー】

1. 要件分析
   └─ 設計仕様書を読み込み
   └─ 機能を識別
   └─ タスクに分解

2. タスク作成
   └─ GitHub Issuesに登録
   └─ 担当Agent割り当て
   └─ 優先順位設定
   └─ 依存関係定義

3. 進捗監視
   └─ 各Agentの状態確認
   └─ ボトルネック特定
   └─ リソース再配分

4. 統合管理
   └─ Pull Requestレビュー調整
   └─ マージ承認
   └─ コンフリクト解決支援

5. 報告
   └─ 日次進捗レポート
   └─ 週次サマリー
   └─ マイルストーン達成報告

【コマンド例】

タスク分解:
```bash
claude agent pm "要件定義書と設計仕様書を分析し、
開発タスクを50個のGitHub Issuesに分解してください。
各タスクには:
- 説明
- 担当Agent
- 優先度（High/Medium/Low）
- 見積時間
- 依存関係
を含めてください"
```

進捗確認:
```bash
claude agent pm "全Agentの進捗状況を確認し、
project-state.jsonを更新してください"
```

3.2 Agent 2: データベースアーキテクト
-------------------------------------

【役割】
データベース設計、モデル実装、マイグレーション管理

【責任範囲】
- SQLAlchemyモデル実装
- データベーススキーマ設計
- マイグレーションスクリプト作成
- インデックス最適化
- リレーションシップ定義
- 制約・バリデーション実装
- データベース初期化スクリプト

【担当ファイル】
- app/models.py
- migrations/versions/*.py
- scripts/init_db.py
- scripts/seed_data.py
- docs/database-schema.md

【テーブル担当】
1. users（ユーザー）
2. backup_jobs（バックアップジョブ）
3. backup_copies（バックアップコピー）
4. offline_media（オフラインメディア）
5. verification_tests（検証テスト）
6. audit_logs（監査ログ）
7. alerts（アラート）
8. reports（レポート）
9. settings（システム設定）
10. schedules（スケジュール）
11. notifications（通知履歴）
12. compliance_checks（コンプライアンスチェック）
13. media_inventory（メディア在庫）
14. backup_chains（バックアップチェーン）

【必要なスキル】
- SQLAlchemy ORM
- データベース設計
- 正規化理論
- パフォーマンスチューニング
- Flask-Migrate

【モデル実装例】

app/models.py:
```python
from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    """ユーザーモデル"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    backup_jobs = db.relationship('BackupJob', backref='creator', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """パスワードハッシュを設定"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """パスワード検証"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class BackupJob(db.Model):
    """バックアップジョブモデル"""
    __tablename__ = 'backup_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    backup_type = db.Column(db.String(50), nullable=False)  # full/incremental/differential
    source_path = db.Column(db.String(500), nullable=False)
    target_tool = db.Column(db.String(50), nullable=False)  # Veeam/WSB/AOMEI
    schedule_type = db.Column(db.String(50))  # daily/weekly/monthly
    retention_days = db.Column(db.Integer, default=30)
    is_active = db.Column(db.Boolean, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    backup_copies = db.relationship('BackupCopy', backref='job', lazy='dynamic', 
                                   cascade='all, delete-orphan')
    verification_tests = db.relationship('VerificationTest', backref='job', 
                                        lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<BackupJob {self.name}>'

class BackupCopy(db.Model):
    """バックアップコピーモデル（3-2-1-1-0の各コピー）"""
    __tablename__ = 'backup_copies'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('backup_jobs.id'), nullable=False)
    copy_number = db.Column(db.Integer, nullable=False)  # 1-3 for 3 copies
    storage_type = db.Column(db.String(50), nullable=False)  # local/nas/cloud/tape
    storage_location = db.Column(db.String(500), nullable=False)
    media_type = db.Column(db.String(50), nullable=False)  # disk/tape/cloud
    is_offsite = db.Column(db.Boolean, default=False)
    is_offline = db.Column(db.Boolean, default=False)
    last_backup_date = db.Column(db.DateTime)
    backup_size_gb = db.Column(db.Float)
    status = db.Column(db.String(20), default='active')  # active/inactive/error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # インデックス
    __table_args__ = (
        db.Index('idx_job_copy', 'job_id', 'copy_number'),
    )
    
    def __repr__(self):
        return f'<BackupCopy Job:{self.job_id} Copy:{self.copy_number}>'
```

【コマンド例】

モデル実装:
```bash
claude agent database "app/models.pyに14個のSQLAlchemyモデルを実装してください。
設計仕様書のデータベース設計セクションに従ってください。
各モデルには:
- 適切なカラム定義
- リレーションシップ
- インデックス
- バリデーション
- to_dict()メソッド
を含めてください"
```

マイグレーション作成:
```bash
claude agent database "初期マイグレーションスクリプトを作成してください。
flask db migrate -m 'Initial database schema'
を実行し、生成されたファイルをレビューしてください"
```

3.3 Agent 3: バックエンドAPI開発者
----------------------------------

【役割】
REST API実装、エンドポイント設計、ビジネスロジック統合

【責任範囲】
- REST APIエンドポイント実装
- リクエスト/レスポンス処理
- JSONシリアライゼーション
- エラーハンドリング
- APIドキュメント生成
- レート制限実装
- CORS設定

【担当ファイル】
- app/api/__init__.py
- app/api/backup.py
- app/api/jobs.py
- app/api/reports.py
- app/api/auth.py
- app/api/alerts.py
- docs/api-documentation.md

【実装エンドポイント】

1. 認証関連
   - POST /api/v1/auth/login
   - POST /api/v1/auth/logout
   - POST /api/v1/auth/refresh
   - GET /api/v1/auth/me

2. ジョブ管理
   - GET /api/v1/jobs
   - GET /api/v1/jobs/{id}
   - POST /api/v1/jobs
   - PUT /api/v1/jobs/{id}
   - DELETE /api/v1/jobs/{id}

3. バックアップコピー
   - GET /api/v1/jobs/{id}/copies
   - POST /api/v1/jobs/{id}/copies
   - PUT /api/v1/copies/{id}
   - DELETE /api/v1/copies/{id}

4. 検証テスト
   - GET /api/v1/jobs/{id}/verifications
   - POST /api/v1/jobs/{id}/verifications
   - GET /api/v1/verifications/{id}

5. コンプライアンス
   - GET /api/v1/compliance/check
   - GET /api/v1/compliance/summary
   - GET /api/v1/compliance/jobs/{id}

6. レポート
   - GET /api/v1/reports
   - GET /api/v1/reports/{id}
   - POST /api/v1/reports/generate
   - GET /api/v1/reports/{id}/download

7. アラート
   - GET /api/v1/alerts
   - GET /api/v1/alerts/{id}
   - PUT /api/v1/alerts/{id}/acknowledge
   - DELETE /api/v1/alerts/{id}

8. 統計
   - GET /api/v1/stats/dashboard
   - GET /api/v1/stats/compliance-trends
   - GET /api/v1/stats/storage-usage

【必要なスキル】
- Flask Blueprint
- RESTful API設計
- JSONスキーマバリデーション
- HTTPステータスコード
- API認証（JWT）

【実装例】

app/api/jobs.py:
```python
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import BackupJob, BackupCopy
from app.auth.decorators import admin_required
from datetime import datetime

bp = Blueprint('jobs', __name__, url_prefix='/api/v1/jobs')

@bp.route('', methods=['GET'])
@login_required
def get_jobs():
    """バックアップジョブ一覧取得"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', None)
        
        query = BackupJob.query
        
        # フィルタリング
        if status:
            query = query.filter_by(is_active=(status == 'active'))
        
        # ページネーション
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': {
                'jobs': [job.to_dict() for job in pagination.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    """バックアップジョブ詳細取得"""
    try:
        job = BackupJob.query.get_or_404(job_id)
        
        # コピー情報も含める
        copies = [copy.to_dict() for copy in job.backup_copies]
        
        job_data = job.to_dict()
        job_data['copies'] = copies
        
        return jsonify({
            'success': True,
            'data': job_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404

@bp.route('', methods=['POST'])
@login_required
@admin_required
def create_job():
    """バックアップジョブ作成"""
    try:
        data = request.get_json()
        
        # バリデーション
        required_fields = ['name', 'backup_type', 'source_path', 'target_tool']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # ジョブ作成
        job = BackupJob(
            name=data['name'],
            description=data.get('description', ''),
            backup_type=data['backup_type'],
            source_path=data['source_path'],
            target_tool=data['target_tool'],
            schedule_type=data.get('schedule_type'),
            retention_days=data.get('retention_days', 30),
            created_by_id=current_user.id
        )
        
        db.session.add(job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': job.to_dict(),
            'message': 'Backup job created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:job_id>', methods=['PUT'])
@login_required
@admin_required
def update_job(job_id):
    """バックアップジョブ更新"""
    try:
        job = BackupJob.query.get_or_404(job_id)
        data = request.get_json()
        
        # 更新可能なフィールド
        updatable_fields = [
            'name', 'description', 'schedule_type', 
            'retention_days', 'is_active'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(job, field, data[field])
        
        job.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': job.to_dict(),
            'message': 'Backup job updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:job_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_job(job_id):
    """バックアップジョブ削除"""
    try:
        job = BackupJob.query.get_or_404(job_id)
        
        # ソフトデリート（is_activeをFalseに）
        job.is_active = False
        job.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Backup job deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

【コマンド例】

API実装:
```bash
claude agent api "app/api/jobs.pyにバックアップジョブ管理の
REST APIエンドポイントを実装してください。
CRUD操作、ページネーション、エラーハンドリングを含めてください"
```

3.4 Agent 4: フロントエンド開発者
---------------------------------

【役割】
Webページ、テンプレート、CSS、JavaScriptの実装

【責任範囲】
- Jinja2テンプレート実装
- レスポンシブデザイン
- ダッシュボードUI
- グラフ・チャート表示
- フォームバリデーション
- ユーザーインタラクション

【担当ファイル】
- app/templates/base.html
- app/templates/dashboard.html
- app/templates/jobs/*.html
- app/templates/reports/*.html
- app/static/css/main.css
- app/static/js/dashboard.js
- app/static/js/charts.js

【ページ一覧】

1. 認証
   - login.html（ログイン）
   - register.html（ユーザー登録）※管理者のみ

2. ダッシュボード
   - dashboard.html（メインダッシュボード）
     * 3-2-1-1-0コンプライアンス状況
     * 最近のアラート
     * ストレージ使用状況
     * 検証テスト状況

3. ジョブ管理
   - jobs/list.html（ジョブ一覧）
   - jobs/detail.html（ジョブ詳細）
   - jobs/create.html（ジョブ作成）
   - jobs/edit.html（ジョブ編集）

4. コピー管理
   - copies/list.html（コピー一覧）
   - copies/detail.html（コピー詳細）

5. 検証テスト
   - verifications/list.html（テスト一覧）
   - verifications/detail.html（テスト詳細）
   - verifications/schedule.html（スケジュール設定）

6. レポート
   - reports/list.html（レポート一覧）
   - reports/view.html（レポート表示）
   - reports/generate.html（レポート生成）

7. アラート
   - alerts/list.html（アラート一覧）
   - alerts/detail.html（アラート詳細）

8. 設定
   - settings/general.html（一般設定）
   - settings/users.html（ユーザー管理）
   - settings/notifications.html（通知設定）

【必要なスキル】
- HTML5/CSS3
- JavaScript (ES6+)
- Jinja2テンプレートエンジン
- Bootstrap 5 / Tailwind CSS
- Chart.js / D3.js

【実装例】

app/templates/base.html:
```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}3-2-1-1-0 バックアップ管理システム{% endblock %}</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
    
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- ナビゲーションバー -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('main.dashboard') }}">
                <i class="fas fa-database"></i> バックアップ管理
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('main.dashboard') }}">
                            <i class="fas fa-tachometer-alt"></i> ダッシュボード
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('jobs.list') }}">
                            <i class="fas fa-tasks"></i> ジョブ
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('reports.list') }}">
                            <i class="fas fa-chart-bar"></i> レポート
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('alerts.list') }}">
                            <i class="fas fa-bell"></i> アラート
                            {% if unread_alerts_count > 0 %}
                            <span class="badge bg-danger">{{ unread_alerts_count }}</span>
                            {% endif %}
                        </a>
                    </li>
                </ul>
                <ul class="navbar-nav">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" 
                           data-bs-toggle="dropdown">
                            <i class="fas fa-user"></i> {{ current_user.username }}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="{{ url_for('auth.profile') }}">プロフィール</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('settings.general') }}">設定</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('auth.logout') }}">ログアウト</a></li>
                        </ul>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <!-- フラッシュメッセージ -->
    <div class="container mt-3">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
    </div>

    <!-- メインコンテンツ -->
    <main class="container my-4">
        {% block content %}{% endblock %}
    </main>

    <!-- フッター -->
    <footer class="bg-light text-center text-lg-start mt-5">
        <div class="text-center p-3">
            © 2025 3-2-1-1-0 バックアップ管理システム v{{ app_version }}
        </div>
    </footer>

    <!-- Bootstrap JS Bundle -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- jQuery (オプション) -->
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    
    <!-- Custom JS -->
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

app/templates/dashboard.html:
```html
{% extends "base.html" %}

{% block title %}ダッシュボード - 3-2-1-1-0 バックアップ管理{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h1 class="mb-4"><i class="fas fa-tachometer-alt"></i> ダッシュボード</h1>
    </div>
</div>

<!-- 3-2-1-1-0 コンプライアンスカード -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card border-primary">
            <div class="card-body text-center">
                <h5 class="card-title">3つのコピー</h5>
                <p class="display-4 text-primary">
                    {{ compliance_data.copies_count }}/3
                </p>
                <p class="card-text">
                    {% if compliance_data.copies_ok %}
                    <span class="badge bg-success">OK</span>
                    {% else %}
                    <span class="badge bg-danger">NG</span>
                    {% endif %}
                </p>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card border-info">
            <div class="card-body text-center">
                <h5 class="card-title">2つの異なるメディア</h5>
                <p class="display-4 text-info">
                    {{ compliance_data.media_types_count }}/2
                </p>
                <p class="card-text">
                    {% if compliance_data.media_ok %}
                    <span class="badge bg-success">OK</span>
                    {% else %}
                    <span class="badge bg-danger">NG</span>
                    {% endif %}
                </p>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card border-warning">
            <div class="card-body text-center">
                <h5 class="card-title">1つがオフサイト</h5>
                <p class="display-4 text-warning">
                    {{ compliance_data.offsite_count }}/1
                </p>
                <p class="card-text">
                    {% if compliance_data.offsite_ok %}
                    <span class="badge bg-success">OK</span>
                    {% else %}
                    <span class="badge bg-danger">NG</span>
                    {% endif %}
                </p>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card border-success">
            <div class="card-body text-center">
                <h5 class="card-title">1つがオフライン</h5>
                <p class="display-4 text-success">
                    {{ compliance_data.offline_count }}/1
                </p>
                <p class="card-text">
                    {% if compliance_data.offline_ok %}
                    <span class="badge bg-success">OK</span>
                    {% else %}
                    <span class="badge bg-danger">NG</span>
                    {% endif %}
                </p>
            </div>
        </div>
    </div>
</div>

<!-- 検証エラー0 -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card border-{{ 'success' if compliance_data.verification_errors == 0 else 'danger' }}">
            <div class="card-body text-center">
                <h5 class="card-title">検証エラー（0エラー目標）</h5>
                <p class="display-3 text-{{ 'success' if compliance_data.verification_errors == 0 else 'danger' }}">
                    {{ compliance_data.verification_errors }}
                </p>
                <p class="card-text">
                    {% if compliance_data.verification_errors == 0 %}
                    <span class="badge bg-success"><i class="fas fa-check-circle"></i> 検証OK</span>
                    {% else %}
                    <span class="badge bg-danger"><i class="fas fa-exclamation-triangle"></i> 要対応</span>
                    {% endif %}
                </p>
            </div>
        </div>
    </div>
</div>

<!-- グラフエリア -->
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-chart-line"></i> コンプライアンス推移</h5>
            </div>
            <div class="card-body">
                <canvas id="complianceChart"></canvas>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-hdd"></i> ストレージ使用状況</h5>
            </div>
            <div class="card-body">
                <canvas id="storageChart"></canvas>
            </div>
        </div>
    </div>
</div>

<!-- 最近のアラート -->
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-bell"></i> 最近のアラート</h5>
            </div>
            <div class="card-body">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>レベル</th>
                            <th>メッセージ</th>
                            <th>ジョブ</th>
                            <th>日時</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for alert in recent_alerts %}
                        <tr>
                            <td>
                                <span class="badge bg-{{ alert.level_class }}">
                                    {{ alert.level }}
                                </span>
                            </td>
                            <td>{{ alert.message }}</td>
                            <td>{{ alert.job_name }}</td>
                            <td>{{ alert.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                            <td>
                                <a href="{{ url_for('alerts.detail', id=alert.id) }}" 
                                   class="btn btn-sm btn-outline-primary">
                                    詳細
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
<script>
    // コンプライアンス推移チャート
    const complianceData = {{ compliance_trend_data | tojson }};
    initComplianceChart(complianceData);
    
    // ストレージ使用状況チャート
    const storageData = {{ storage_data | tojson }};
    initStorageChart(storageData);
</script>
{% endblock %}
```

【コマンド例】

テンプレート実装:
```bash
claude agent frontend "app/templates/dashboard.htmlを実装してください。
3-2-1-1-0コンプライアンス状況、グラフ、最近のアラートを表示する
レスポンシブなダッシュボードを作成してください"
```

3.5 Agent 5: 認証・セキュリティエンジニア
-----------------------------------------

【役割】
認証、認可、セキュリティ機能の実装

【責任範囲】
- Flask-Login統合
- ユーザー認証
- ロールベースアクセス制御（RBAC）
- パスワードハッシュ化
- セッション管理
- CSRF保護
- セキュリティヘッダー設定

【担当ファイル】
- app/auth/__init__.py
- app/auth/decorators.py
- app/auth/forms.py
- app/auth/views.py
- app/models.py（Userモデル）

【ロール定義】

1. admin（管理者）
   - すべての機能にアクセス可能
   - ユーザー管理
   - システム設定変更

2. operator（オペレーター）
   - ジョブの作成・編集・削除
   - レポート生成
   - アラート確認・対応

3. viewer（閲覧者）
   - ダッシュボード閲覧
   - レポート閲覧
   - ジョブ情報閲覧（編集不可）

【必要なスキル】
- Flask-Login
- bcrypt / Werkzeug Security
- JWT（オプション）
- OWASP Top 10理解
- セキュリティベストプラクティス

【実装例】

app/auth/decorators.py:
```python
from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    """管理者権限が必要なビューのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def operator_required(f):
    """オペレーター以上の権限が必要なビューのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role not in ['admin', 'operator']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """指定されたロールのいずれかが必要なビューのデコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

【コマンド例】

認証実装:
```bash
claude agent security "app/auth/にFlask-Loginを使った
認証システムを実装してください。
ロールベースアクセス制御（admin/operator/viewer）を含めてください"
```

3.6 Agent 6: ビジネスロジック開発者
-----------------------------------

【役割】
3-2-1-1-0チェックロジック、アラート生成、コンプライアンスチェック

【責任範囲】
- 3-2-1-1-0ルールチェックロジック
- コンプライアンススコア計算
- アラート生成ロジック
- レポート生成ロジック
- ビジネスルール実装

【担当ファイル】
- app/services/compliance_checker.py
- app/services/alert_manager.py
- app/services/report_generator.py
- app/services/backup_analyzer.py

【必要なスキル】
- Pythonビジネスロジック実装
- アルゴリズム設計
- データ分析
- レポート生成

【実装例】

app/services/compliance_checker.py:
```python
from datetime import datetime, timedelta
from app import db
from app.models import BackupJob, BackupCopy, VerificationTest
from typing import Dict, List, Tuple

class ComplianceChecker:
    """3-2-1-1-0コンプライアンスチェッカー"""
    
    def __init__(self):
        pass
    
    def check_job_compliance(self, job_id: int) -> Dict:
        """
        特定のジョブの3-2-1-1-0コンプライアンスをチェック
        
        Returns:
            Dict: {
                'compliant': bool,
                'score': int (0-100),
                'details': {...},
                'issues': [...]
            }
        """
        job = BackupJob.query.get_or_404(job_id)
        copies = BackupCopy.query.filter_by(job_id=job_id, status='active').all()
        
        result = {
            'job_id': job_id,
            'job_name': job.name,
            'compliant': True,
            'score': 100,
            'details': {},
            'issues': []
        }
        
        # 1. 3つのコピーチェック
        copies_check = self._check_three_copies(copies)
        result['details']['copies'] = copies_check
        if not copies_check['ok']:
            result['compliant'] = False
            result['score'] -= 20
            result['issues'].append(copies_check['message'])
        
        # 2. 2つの異なるメディアタイプチェック
        media_check = self._check_two_media_types(copies)
        result['details']['media'] = media_check
        if not media_check['ok']:
            result['compliant'] = False
            result['score'] -= 20
            result['issues'].append(media_check['message'])
        
        # 3. 1つがオフサイトチェック
        offsite_check = self._check_one_offsite(copies)
        result['details']['offsite'] = offsite_check
        if not offsite_check['ok']:
            result['compliant'] = False
            result['score'] -= 20
            result['issues'].append(offsite_check['message'])
        
        # 4. 1つがオフライン（エアギャップ）チェック
        offline_check = self._check_one_offline(copies)
        result['details']['offline'] = offline_check
        if not offline_check['ok']:
            result['compliant'] = False
            result['score'] -= 20
            result['issues'].append(offline_check['message'])
        
        # 5. 検証エラー0チェック
        verification_check = self._check_zero_verification_errors(job_id)
        result['details']['verification'] = verification_check
        if not verification_check['ok']:
            result['compliant'] = False
            result['score'] -= 20
            result['issues'].append(verification_check['message'])
        
        return result
    
    def _check_three_copies(self, copies: List[BackupCopy]) -> Dict:
        """3つのコピーが存在するかチェック"""
        count = len(copies)
        return {
            'ok': count >= 3,
            'count': count,
            'required': 3,
            'message': f'{count}/3 コピー' if count < 3 else '3つのコピーOK'
        }
    
    def _check_two_media_types(self, copies: List[BackupCopy]) -> Dict:
        """2つ以上の異なるメディアタイプが使用されているかチェック"""
        media_types = set(copy.media_type for copy in copies)
        count = len(media_types)
        return {
            'ok': count >= 2,
            'count': count,
            'required': 2,
            'types': list(media_types),
            'message': f'{count}/2 メディアタイプ' if count < 2 else '2つのメディアタイプOK'
        }
    
    def _check_one_offsite(self, copies: List[BackupCopy]) -> Dict:
        """少なくとも1つがオフサイトかチェック"""
        offsite_copies = [c for c in copies if c.is_offsite]
        count = len(offsite_copies)
        return {
            'ok': count >= 1,
            'count': count,
            'required': 1,
            'message': 'オフサイトコピーなし' if count < 1 else 'オフサイトコピーOK'
        }
    
    def _check_one_offline(self, copies: List[BackupCopy]) -> Dict:
        """少なくとも1つがオフライン（エアギャップ）かチェック"""
        offline_copies = [c for c in copies if c.is_offline]
        count = len(offline_copies)
        return {
            'ok': count >= 1,
            'count': count,
            'required': 1,
            'message': 'オフラインコピーなし' if count < 1 else 'オフラインコピーOK'
        }
    
    def _check_zero_verification_errors(self, job_id: int) -> Dict:
        """最近の検証テストでエラーがないかチェック"""
        # 過去30日間の検証テストを取得
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        tests = VerificationTest.query.filter(
            VerificationTest.job_id == job_id,
            VerificationTest.test_date >= thirty_days_ago
        ).all()
        
        if not tests:
            return {
                'ok': False,
                'error_count': 0,
                'test_count': 0,
                'message': '検証テストが実施されていません'
            }
        
        error_count = sum(1 for test in tests if test.status == 'failed')
        
        return {
            'ok': error_count == 0,
            'error_count': error_count,
            'test_count': len(tests),
            'message': f'{error_count}件の検証エラー' if error_count > 0 else '検証エラー0'
        }
    
    def check_all_jobs_compliance(self) -> Dict:
        """全ジョブのコンプライアンス状況を集計"""
        jobs = BackupJob.query.filter_by(is_active=True).all()
        
        results = {
            'total_jobs': len(jobs),
            'compliant_jobs': 0,
            'non_compliant_jobs': 0,
            'average_score': 0,
            'jobs': []
        }
        
        total_score = 0
        for job in jobs:
            job_result = self.check_job_compliance(job.id)
            results['jobs'].append(job_result)
            
            if job_result['compliant']:
                results['compliant_jobs'] += 1
            else:
                results['non_compliant_jobs'] += 1
            
            total_score += job_result['score']
        
        if len(jobs) > 0:
            results['average_score'] = total_score / len(jobs)
        
        return results
```

【コマンド例】

ビジネスロジック実装:
```bash
claude agent logic "app/services/compliance_checker.pyに
3-2-1-1-0ルールのチェックロジックを実装してください。
各条件の判定、スコア計算、課題抽出を含めてください"
```

3.7 Agent 7: スケジューラー・通知開発者
---------------------------------------

【役割】
定期実行タスク、メール通知、Teams通知の実装

【責任範囲】
- APScheduler設定
- 定期バックアップチェック
- コンプライアンスチェック実行
- メール送信機能
- Microsoft Teams通知
- アラート通知

【担当ファイル】
- app/scheduler/tasks.py
- app/scheduler/__init__.py
- app/utils/email.py
- app/utils/notifications.py
- app/utils/teams_webhook.py

【スケジュールタスク】

1. 日次タスク（毎日深夜2時）
   - 全ジョブのコンプライアンスチェック
   - アラート生成
   - 日次レポート作成

2. 週次タスク（毎週月曜日9時）
   - 週次サマリーレポート
   - 管理者への通知

3. 月次タスク（毎月1日9時）
   - 月次コンプライアンスレポート
   - ストレージ使用状況分析

4. 即時タスク
   - バックアップ失敗検知時
   - 検証エラー検知時
   - 閾値超過検知時

【必要なスキル】
- APScheduler
- SMTPプロトコル
- Webhooks
- 非同期処理

【実装例】

app/scheduler/tasks.py:
```python
from datetime import datetime
from app import db, scheduler
from app.models import BackupJob, Alert
from app.services.compliance_checker import ComplianceChecker
from app.services.report_generator import ReportGenerator
from app.utils.email import send_email
from app.utils.notifications import send_teams_notification
import logging

logger = logging.getLogger(__name__)

def daily_compliance_check():
    """日次コンプライアンスチェック（毎日深夜2時実行）"""
    logger.info("Starting daily compliance check...")
    
    try:
        checker = ComplianceChecker()
        results = checker.check_all_jobs_compliance()
        
        # 非コンプライアントなジョブにアラート生成
        for job_result in results['jobs']:
            if not job_result['compliant']:
                create_compliance_alert(job_result)
        
        # 管理者に通知
        if results['non_compliant_jobs'] > 0:
            notify_admins_compliance_issues(results)
        
        logger.info(f"Daily compliance check completed. "
                   f"Compliant: {results['compliant_jobs']}, "
                   f"Non-compliant: {results['non_compliant_jobs']}")
        
    except Exception as e:
        logger.error(f"Error in daily compliance check: {str(e)}")

def create_compliance_alert(job_result):
    """コンプライアンス違反のアラートを作成"""
    job_id = job_result['job_id']
    issues = ', '.join(job_result['issues'])
    
    alert = Alert(
        job_id=job_id,
        level='warning',
        title='3-2-1-1-0 コンプライアンス違反',
        message=f"ジョブ '{job_result['job_name']}' がコンプライアンス要件を満たしていません: {issues}",
        status='unread'
    )
    
    db.session.add(alert)
    db.session.commit()
    
    # Teams通知
    send_teams_notification(
        title='コンプライアンス違反',
        text=alert.message,
        color='warning'
    )

def notify_admins_compliance_issues(results):
    """管理者にコンプライアンス問題を通知"""
    from app.models import User
    
    admins = User.query.filter_by(role='admin', is_active=True).all()
    
    for admin in admins:
        subject = f"【要対応】{results['non_compliant_jobs']}件のコンプライアンス違反"
        body = f"""
        {admin.username} 様

        日次コンプライアンスチェックの結果、以下の問題が検出されました:

        - 総ジョブ数: {results['total_jobs']}
        - コンプライアント: {results['compliant_jobs']}
        - 非コンプライアント: {results['non_compliant_jobs']}
        - 平均スコア: {results['average_score']:.1f}

        詳細はダッシュボードでご確認ください。

        ---
        3-2-1-1-0 バックアップ管理システム
        """
        
        send_email(
            to=admin.email,
            subject=subject,
            body=body
        )

def weekly_summary_report():
    """週次サマリーレポート（毎週月曜日9時実行）"""
    logger.info("Generating weekly summary report...")
    
    try:
        generator = ReportGenerator()
        report = generator.generate_weekly_summary()
        
        # 管理者とオペレーターに送信
        from app.models import User
        recipients = User.query.filter(
            User.role.in_(['admin', 'operator']),
            User.is_active == True
        ).all()
        
        for user in recipients:
            send_email(
                to=user.email,
                subject='週次バックアップサマリーレポート',
                body=report['text'],
                html=report['html']
            )
        
        logger.info("Weekly summary report sent successfully")
        
    except Exception as e:
        logger.error(f"Error generating weekly summary: {str(e)}")

def monthly_compliance_report():
    """月次コンプライアンスレポート（毎月1日9時実行）"""
    logger.info("Generating monthly compliance report...")
    
    try:
        generator = ReportGenerator()
        report = generator.generate_monthly_compliance_report()
        
        # レポートをDB保存
        from app.models import Report
        db_report = Report(
            title=f"月次コンプライアンスレポート {datetime.utcnow().strftime('%Y年%m月')}",
            report_type='monthly_compliance',
            content=report['content'],
            format='pdf'
        )
        db.session.add(db_report)
        db.session.commit()
        
        logger.info(f"Monthly compliance report saved with ID {db_report.id}")
        
    except Exception as e:
        logger.error(f"Error generating monthly report: {str(e)}")

# スケジューラーにタスク登録
def init_scheduler(app):
    """スケジューラー初期化"""
    with app.app_context():
        # 日次タスク（毎日深夜2時）
        scheduler.add_job(
            id='daily_compliance_check',
            func=daily_compliance_check,
            trigger='cron',
            hour=2,
            minute=0
        )
        
        # 週次タスク（毎週月曜日9時）
        scheduler.add_job(
            id='weekly_summary_report',
            func=weekly_summary_report,
            trigger='cron',
            day_of_week='mon',
            hour=9,
            minute=0
        )
        
        # 月次タスク（毎月1日9時）
        scheduler.add_job(
            id='monthly_compliance_report',
            func=monthly_compliance_report,
            trigger='cron',
            day=1,
            hour=9,
            minute=0
        )
        
        logger.info("Scheduler initialized successfully")
```

【コマンド例】

スケジューラー実装:
```bash
claude agent scheduler "app/scheduler/にAPSchedulerを使った
定期実行タスクを実装してください。
日次コンプライアンスチェック、週次レポート、月次レポートを含めてください"
```

3.8 Agent 8: PowerShell統合エンジニア
-------------------------------------

【役割】
Windows環境でのPowerShell統合、デプロイスクリプト

【責任範囲】
- PowerShellスクリプト作成
- Windows API呼び出し
- NSSM サービス化スクリプト
- バックアップツール連携（Veeam/WSB/AOMEI）

【担当ファイル】
- deployment/windows/*.ps1
- scripts/windows/*.ps1
- docs/PowerShell統合ガイド.md

【スクリプト一覧】

1. deploy.ps1（デプロイメント）
2. install-service.ps1（サービス化）
3. backup-api-client.ps1（API呼び出し）
4. veeam-integration.ps1（Veeam統合）
5. wsb-integration.ps1（Windows Server Backup統合）
6. check-compliance.ps1（コンプライアンスチェック）

【必要なスキル】
- PowerShell 5.1/7.x
- Windows API
- REST API呼び出し
- エラーハンドリング

【実装例】

deployment/windows/backup-api-client.ps1:
```powershell
<#
.SYNOPSIS
    3-2-1-1-0 バックアップ管理システム API クライアント

.DESCRIPTION
    PowerShellからFlask APIにアクセスしてバックアップジョブを管理

.PARAMETER ApiUrl
    APIのベースURL

.PARAMETER ApiKey
    API認証キー

.EXAMPLE
    .\backup-api-client.ps1 -ApiUrl "http://localhost:5000" -Action GetJobs
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ApiUrl,
    
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,
    
    [Parameter(Mandatory=$true)]
    [ValidateSet('GetJobs', 'GetJob', 'CreateJob', 'UpdateJobStatus', 'CheckCompliance')]
    [string]$Action,
    
    [Parameter(Mandatory=$false)]
    [int]$JobId,
    
    [Parameter(Mandatory=$false)]
    [hashtable]$JobData
)

# エラーアクション設定
$ErrorActionPreference = "Stop"

# ログ設定
$LogFile = "C:\Logs\backup-api-client.log"
function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Timestamp - $Message" | Out-File -FilePath $LogFile -Append
    Write-Verbose $Message
}

# API呼び出し共通関数
function Invoke-BackupAPI {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [object]$Body = $null
    )
    
    try {
        $Headers = @{
            "Authorization" = "Bearer $ApiKey"
            "Content-Type" = "application/json"
        }
        
        $Params = @{
            Uri = "$ApiUrl/api/v1/$Endpoint"
            Method = $Method
            Headers = $Headers
        }
        
        if ($Body) {
            $Params.Body = ($Body | ConvertTo-Json -Depth 10)
        }
        
        Write-Log "API Call: $Method $($Params.Uri)"
        
        $Response = Invoke-RestMethod @Params
        
        Write-Log "API Response: Success"
        return $Response
        
    } catch {
        Write-Log "API Error: $($_.Exception.Message)"
        throw
    }
}

# バックアップジョブ一覧取得
function Get-BackupJobs {
    Write-Log "Getting backup jobs list..."
    $Response = Invoke-BackupAPI -Endpoint "jobs" -Method "GET"
    return $Response.data.jobs
}

# バックアップジョブ詳細取得
function Get-BackupJob {
    param([int]$Id)
    Write-Log "Getting backup job details: ID=$Id"
    $Response = Invoke-BackupAPI -Endpoint "jobs/$Id" -Method "GET"
    return $Response.data
}

# バックアップジョブ作成
function New-BackupJob {
    param([hashtable]$Data)
    Write-Log "Creating new backup job: $($Data.name)"
    $Response = Invoke-BackupAPI -Endpoint "jobs" -Method "POST" -Body $Data
    return $Response.data
}

# バックアップジョブステータス更新
function Update-BackupJobStatus {
    param(
        [int]$Id,
        [string]$Status
    )
    Write-Log "Updating backup job status: ID=$Id, Status=$Status"
    $Body = @{ status = $Status }
    $Response = Invoke-BackupAPI -Endpoint "jobs/$Id/status" -Method "PUT" -Body $Body
    return $Response.data
}

# コンプライアンスチェック
function Test-Compliance {
    param([int]$JobId)
    Write-Log "Checking compliance for job: ID=$JobId"
    $Endpoint = if ($JobId) { "compliance/jobs/$JobId" } else { "compliance/summary" }
    $Response = Invoke-BackupAPI -Endpoint $Endpoint -Method "GET"
    return $Response.data
}

# メイン処理
try {
    Write-Log "Starting backup API client: Action=$Action"
    
    switch ($Action) {
        "GetJobs" {
            $Jobs = Get-BackupJobs
            Write-Output $Jobs
        }
        
        "GetJob" {
            if (-not $JobId) {
                throw "JobId is required for GetJob action"
            }
            $Job = Get-BackupJob -Id $JobId
            Write-Output $Job
        }
        
        "CreateJob" {
            if (-not $JobData) {
                throw "JobData is required for CreateJob action"
            }
            $NewJob = New-BackupJob -Data $JobData
            Write-Output $NewJob
        }
        
        "UpdateJobStatus" {
            if (-not $JobId) {
                throw "JobId is required for UpdateJobStatus action"
            }
            if (-not $JobData.status) {
                throw "Status is required in JobData"
            }
            $Updated = Update-BackupJobStatus -Id $JobId -Status $JobData.status
            Write-Output $Updated
        }
        
        "CheckCompliance" {
            $Compliance = Test-Compliance -JobId $JobId
            Write-Output $Compliance
        }
    }
    
    Write-Log "Backup API client completed successfully"
    exit 0
    
} catch {
    Write-Log "Error: $($_.Exception.Message)"
    Write-Error $_.Exception.Message
    exit 1
}
```

【コマンド例】

PowerShell統合:
```bash
claude agent powershell "deployment/windows/backup-api-client.ps1を作成してください。
PowerShellからFlask APIを呼び出す機能を実装してください"
```

3.9 Agent 9: テストエンジニア
-----------------------------

【役割】
単体テスト、統合テスト、テストカバレッジ管理

【責任範囲】
- Pytestによる単体テスト作成
- APIテスト作成
- テストカバレッジ測定
- テスト自動化
- CIパイプライン設定

【担当ファイル】
- tests/test_models.py
- tests/test_api.py
- tests/test_services.py
- tests/test_auth.py
- tests/conftest.py
- .github/workflows/test.yml

【テストカバレッジ目標】
- 全体: 80%以上
- クリティカル機能: 90%以上
- ビジネスロジック: 95%以上

【必要なスキル】
- Pytest
- unittest.mock
- Test fixtures
- CI/CD（GitHub Actions）

【実装例】

tests/test_models.py:
```python
import pytest
from datetime import datetime, timedelta
from app import db
from app.models import User, BackupJob, BackupCopy, VerificationTest

class TestUserModel:
    """Userモデルのテスト"""
    
    def test_create_user(self, app):
        """ユーザー作成テスト"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                role='operator'
            )
            user.set_password('password123')
            
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.role == 'operator'
            assert user.check_password('password123')
            assert not user.check_password('wrongpassword')
    
    def test_user_password_hashing(self, app):
        """パスワードハッシュ化テスト"""
        with app.app_context():
            user = User(username='hashtest', email='hash@example.com')
            user.set_password('secure_password')
            
            # パスワードハッシュは元のパスワードと異なる
            assert user.password_hash != 'secure_password'
            
            # check_passwordで検証できる
            assert user.check_password('secure_password')
            assert not user.check_password('wrong_password')
    
    def test_user_to_dict(self, app, sample_user):
        """to_dict()メソッドテスト"""
        with app.app_context():
            user_dict = sample_user.to_dict()
            
            assert 'id' in user_dict
            assert 'username' in user_dict
            assert 'email' in user_dict
            assert 'role' in user_dict
            assert 'password_hash' not in user_dict  # パスワードハッシュは含まれない

class TestBackupJobModel:
    """BackupJobモデルのテスト"""
    
    def test_create_backup_job(self, app, sample_user):
        """バックアップジョブ作成テスト"""
        with app.app_context():
            job = BackupJob(
                name='Test Backup',
                description='Test Description',
                backup_type='full',
                source_path='C:\\Data',
                target_tool='Veeam',
                schedule_type='daily',
                retention_days=30,
                created_by_id=sample_user.id
            )
            
            db.session.add(job)
            db.session.commit()
            
            assert job.id is not None
            assert job.name == 'Test Backup'
            assert job.is_active == True
            assert job.creator.username == sample_user.username
    
    def test_backup_job_copies_relationship(self, app, sample_backup_job):
        """バックアップコピーとのリレーションシップテスト"""
        with app.app_context():
            # 3つのコピーを追加
            for i in range(1, 4):
                copy = BackupCopy(
                    job_id=sample_backup_job.id,
                    copy_number=i,
                    storage_type='local' if i == 1 else 'nas',
                    storage_location=f'\\\\storage{i}\\backup',
                    media_type='disk' if i < 3 else 'tape',
                    is_offsite=(i == 2),
                    is_offline=(i == 3)
                )
                db.session.add(copy)
            
            db.session.commit()
            
            # リレーションシップ確認
            assert sample_backup_job.backup_copies.count() == 3
            
            # カスケード削除テスト
            db.session.delete(sample_backup_job)
            db.session.commit()
            
            remaining_copies = BackupCopy.query.filter_by(job_id=sample_backup_job.id).count()
            assert remaining_copies == 0  # カスケード削除される

class TestBackupCopyModel:
    """BackupCopyモデルのテスト"""
    
    def test_create_backup_copy(self, app, sample_backup_job):
        """バックアップコピー作成テスト"""
        with app.app_context():
            copy = BackupCopy(
                job_id=sample_backup_job.id,
                copy_number=1,
                storage_type='local',
                storage_location='C:\\Backups',
                media_type='disk',
                is_offsite=False,
                is_offline=False,
                last_backup_date=datetime.utcnow(),
                backup_size_gb=150.5
            )
            
            db.session.add(copy)
            db.session.commit()
            
            assert copy.id is not None
            assert copy.job_id == sample_backup_job.id
            assert copy.copy_number == 1
            assert copy.status == 'active'
    
    def test_index_on_job_and_copy_number(self, app, sample_backup_job):
        """job_id + copy_numberインデックステスト"""
        with app.app_context():
            # 同じcopy_numberで複数のコピーを作成（異なるジョブ）
            copy1 = BackupCopy(
                job_id=sample_backup_job.id,
                copy_number=1,
                storage_type='local',
                storage_location='C:\\Backup1',
                media_type='disk'
            )
            db.session.add(copy1)
            db.session.commit()
            
            # インデックスを使った検索が高速に実行されることを確認
            result = BackupCopy.query.filter_by(
                job_id=sample_backup_job.id,
                copy_number=1
            ).first()
            
            assert result is not None
            assert result.id == copy1.id
```

tests/conftest.py:
```python
import pytest
from app import create_app, db
from app.models import User, BackupJob
from config import TestConfig

@pytest.fixture
def app():
    """Flaskアプリケーションフィクスチャ"""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Flaskテストクライアントフィクスチャ"""
    return app.test_client()

@pytest.fixture
def sample_user(app):
    """サンプルユーザーフィクスチャ"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # セッションから切り離して返す
        db.session.refresh(user)
        return user

@pytest.fixture
def sample_backup_job(app, sample_user):
    """サンプルバックアップジョブフィクスチャ"""
    with app.app_context():
        job = BackupJob(
            name='Test Job',
            description='Test Description',
            backup_type='full',
            source_path='C:\\Data',
            target_tool='Veeam',
            created_by_id=sample_user.id
        )
        db.session.add(job)
        db.session.commit()
        
        db.session.refresh(job)
        return job

@pytest.fixture
def auth_headers(client, sample_user):
    """認証ヘッダーフィクスチャ"""
    response = client.post('/api/v1/auth/login', json={
        'username': 'testuser',
        'password': 'password123'
    })
    
    token = response.json['data']['access_token']
    return {'Authorization': f'Bearer {token}'}
```

【コマンド例】

テスト実装:
```bash
claude agent test "tests/test_models.pyにモデルの単体テストを実装してください。
User, BackupJob, BackupCopyモデルのCRUD操作とリレーションシップをテストしてください"
```

3.10 Agent 10: DevOps/デプロイエンジニア
----------------------------------------

【役割】
CI/CD、デプロイ自動化、環境構築

【責任範囲】
- GitHub Actions設定
- デプロイスクリプト作成
- Docker対応（オプション）
- 環境構築自動化
- 監視設定

【担当ファイル】
- .github/workflows/ci.yml
- .github/workflows/deploy.yml
- deployment/linux/deploy.sh
- deployment/windows/deploy.ps1
- Dockerfile（オプション）
- docker-compose.yml（オプション）

【CI/CDパイプライン】

1. プッシュ時
   - リントチェック（flake8, pylint）
   - 単体テスト実行
   - カバレッジ測定

2. Pull Request時
   - すべてのテスト実行
   - セキュリティスキャン
   - コード品質チェック

3. developマージ時
   - 統合テスト
   - ステージング環境デプロイ

4. mainマージ時
   - 本番環境デプロイ
   - タグ作成
   - リリースノート生成

【必要なスキル】
- GitHub Actions
- Shell Script / PowerShell
- Docker（オプション）
- Linux/Windows サーバー管理

【実装例】

.github/workflows/ci.yml:
```yaml
name: CI Pipeline

on:
  push:
    branches: [ develop, main ]
  pull_request:
    branches: [ develop, main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 pylint
          pip install -r requirements.txt
      
      - name: Lint with flake8
        run: |
          flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
      
      - name: Lint with pylint
        run: |
          pylint app/ --exit-zero

  test:
    runs-on: ubuntu-latest
    needs: lint
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests with coverage
        run: |
          pytest tests/ --cov=app --cov-report=xml --cov-report=term
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  security:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Bandit security scan
        run: |
          pip install bandit
          bandit -r app/ -f json -o bandit-report.json
      
      - name: Upload security report
        uses: actions/upload-artifact@v3
        with:
          name: bandit-report
          path: bandit-report.json

  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.event_name == 'push'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build application
        run: |
          echo "Build completed successfully"
      
      - name: Create deployment artifact
        run: |
          tar -czf backup-mgmt-system-${{ github.sha }}.tar.gz \
            app/ \
            migrations/ \
            scripts/ \
            deployment/ \
            requirements.txt \
            run.py
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: deployment-package
          path: backup-mgmt-system-${{ github.sha }}.tar.gz
```

deployment/linux/deploy.sh:
```bash
#!/bin/bash
#
# デプロイスクリプト（Linux）
# 3-2-1-1-0 バックアップ管理システム
#

set -e  # エラー時に停止

# 設定
APP_NAME="backup-mgmt-system"
APP_DIR="/opt/${APP_NAME}"
VENV_DIR="${APP_DIR}/venv"
LOG_DIR="/var/log/${APP_NAME}"
USER="backup-admin"
GROUP="backup-admin"

# 色付きログ
RED='\033[0:31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# root権限チェック
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

log_info "Starting deployment of ${APP_NAME}..."

# ディレクトリ作成
log_info "Creating directories..."
mkdir -p "${APP_DIR}"
mkdir -p "${LOG_DIR}"
mkdir -p "${APP_DIR}/data"

# ユーザー・グループ作成（存在しない場合）
if ! id -u "${USER}" > /dev/null 2>&1; then
    log_info "Creating user ${USER}..."
    useradd -r -s /bin/false "${USER}"
fi

# ソースコードデプロイ
log_info "Deploying source code..."
rsync -av --exclude='venv' --exclude='*.pyc' --exclude='__pycache__' \
    ./ "${APP_DIR}/"

# 仮想環境作成
log_info "Creating virtual environment..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi

# パッケージインストール
log_info "Installing Python packages..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"

# データベースマイグレーション
log_info "Running database migrations..."
cd "${APP_DIR}"
"${VENV_DIR}/bin/flask" db upgrade

# 権限設定
log_info "Setting permissions..."
chown -R "${USER}:${GROUP}" "${APP_DIR}"
chown -R "${USER}:${GROUP}" "${LOG_DIR}"
chmod 755 "${APP_DIR}"
chmod 750 "${APP_DIR}/data"

# systemdサービス設定
log_info "Configuring systemd service..."
cat > /etc/systemd/system/${APP_NAME}.service << EOF
[Unit]
Description=3-2-1-1-0 Backup Management System
After=network.target

[Service]
Type=simple
User=${USER}
Group=${GROUP}
WorkingDirectory=${APP_DIR}
Environment="PATH=${VENV_DIR}/bin"
ExecStart=${VENV_DIR}/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# サービス有効化・起動
log_info "Enabling and starting service..."
systemctl daemon-reload
systemctl enable ${APP_NAME}
systemctl restart ${APP_NAME}

# 状態確認
sleep 3
if systemctl is-active --quiet ${APP_NAME}; then
    log_info "Deployment completed successfully!"
    log_info "Service status:"
    systemctl status ${APP_NAME} --no-pager
else
    log_error "Service failed to start!"
    journalctl -u ${APP_NAME} -n 50 --no-pager
    exit 1
fi
```

【コマンド例】

CI/CD設定:
```bash
claude agent devops ".github/workflows/ci.ymlを作成してください。
リントチェック、テスト実行、カバレッジ測定、
セキュリティスキャンを含むCIパイプラインを設定してください"
```

================================================================================
4. Hooks並列開発機能
================================================================================

4.1 Git Hooksとは
-----------------

Gitリポジトリで特定のイベント発生時に自動実行されるスクリプト。

【利用可能なHooks】

クライアント側:
- pre-commit: コミット前
- prepare-commit-msg: コミットメッセージ準備時
- commit-msg: コミットメッセージ検証
- post-commit: コミット後
- pre-push: プッシュ前
- post-checkout: チェックアウト後
- post-merge: マージ後

サーバー側:
- pre-receive: プッシュ受信前
- post-receive: プッシュ受信後
- update: ブランチ更新時

4.2 並列開発のためのHooks設定
------------------------------

【.git/hooks/pre-commit】

コミット前にコード品質チェック:

```bash
#!/bin/bash
# pre-commit: コミット前チェック

set -e

echo "Running pre-commit checks..."

# Python構文チェック
python -m py_compile $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$') 2>/dev/null || {
    echo "Python syntax errors found!"
    exit 1
}

# flake8チェック
if command -v flake8 &> /dev/null; then
    flake8 $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$') 2>/dev/null || {
        echo "flake8 errors found!"
        exit 1
    }
fi

# black自動フォーマット
if command -v black &> /dev/null; then
    black $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$') 2>/dev/null
    git add $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')
fi

echo "Pre-commit checks passed!"
```

【.git/hooks/pre-push】

プッシュ前にテスト実行:

```bash
#!/bin/bash
# pre-push: プッシュ前テスト

set -e

echo "Running tests before push..."

# 単体テスト実行
python -m pytest tests/ -v || {
    echo "Tests failed! Push aborted."
    exit 1
}

echo "All tests passed!"
```

【.git/hooks/post-merge】

マージ後に依存関係更新:

```bash
#!/bin/bash
# post-merge: マージ後処理

echo "Checking for dependency updates..."

# requirements.txtが更新されたか確認
if git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD | grep --quiet requirements.txt; then
    echo "requirements.txt changed, updating dependencies..."
    pip install -r requirements.txt
fi

# マイグレーションファイルが更新されたか確認
if git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD | grep --quiet "migrations/versions/"; then
    echo "Database migrations changed, running migrations..."
    flask db upgrade
fi
```

4.3 GitHub Actionsによる並列実行
---------------------------------

複数のジョブを並列実行してCI/CD時間を短縮:

```yaml
name: Parallel CI

on: [push, pull_request]

jobs:
  # 並列ジョブ1: Lint
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run linters
        run: |
          pip install flake8 pylint
          flake8 app/
          pylint app/

  # 並列ジョブ2: Unit Tests
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: |
          pip install pytest
          pytest tests/unit/

  # 並列ジョブ3: Integration Tests
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: |
          pip install pytest
          pytest tests/integration/

  # 並列ジョブ4: Security Scan
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run security scan
        run: |
          pip install bandit
          bandit -r app/

  # 統合ジョブ（すべての並列ジョブ完了後）
  build:
    needs: [lint, unit-tests, integration-tests, security]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build application
        run: echo "All checks passed, building..."
```

4.4 Agent並列開発の実装
-----------------------

複数のAgentが同時に異なるブランチで開発:

```bash
# Agent 2: データベース開発
git checkout develop
git checkout -b feature/database-models
# ... 開発作業 ...
git push origin feature/database-models

# Agent 3: API開発（並列）
git checkout develop
git checkout -b feature/api-endpoints
# ... 開発作業 ...
git push origin feature/api-endpoints

# Agent 4: フロントエンド開発（並列）
git checkout develop
git checkout -b feature/dashboard-ui
# ... 開発作業 ...
git push origin feature/dashboard-ui
```

各Agentの作業が完了したら、Pull Requestを作成し、
CI/CDパイプラインで自動テスト後、developにマージ。

================================================================================
5. Agent間連携プロトコル詳細
================================================================================

5.1 通信チャネル
----------------

【1. GitHub Issues/Pull Requests】

最も基本的な通信手段。各Agentがタスクを作成・更新。

Issue構造:
```
タイトル: [Agent-2] Implement database models
担当者: @agent-2-database
ラベル: database, in-progress
マイルストーン: Sprint 1

本文:
## タスク概要
14個のSQLAlchemyモデルを実装

## 依存関係
- なし（最初のタスク）

## 成果物
- [ ] app/models.py
- [ ] migrations/versions/001_initial.py
- [ ] tests/test_models.py

## 進捗
- [x] Userモデル実装
- [x] BackupJobモデル実装
- [ ] BackupCopyモデル実装
- [ ] その他のモデル実装

## 通知
実装完了後、@agent-3-api に通知してください
```

【2. JSON状態ファイル】

docs/agent-communication/project-state.json

リアルタイムで各Agentの状態を共有:

```json
{
  "updated_at": "2025-10-30T15:30:00Z",
  "project": {
    "name": "backup-management-system",
    "phase": "development",
    "sprint": 1,
    "version": "0.1.0-dev",
    "start_date": "2025-10-28",
    "target_release": "2025-12-01"
  },
  "agents": {
    "agent-1-pm": {
      "status": "active",
      "current_task": "Sprint planning and task assignment",
      "last_update": "2025-10-30T15:30:00Z",
      "health": "green"
    },
    "agent-2-database": {
      "status": "working",
      "current_task": "DB-001: Implement SQLAlchemy models",
      "progress": 85,
      "estimated_completion": "2025-10-30T18:00:00Z",
      "blockers": [],
      "health": "green"
    },
    "agent-3-api": {
      "status": "waiting",
      "current_task": "API-001: Implement REST endpoints",
      "progress": 0,
      "waiting_for": ["agent-2-database"],
      "health": "yellow"
    },
    "agent-4-frontend": {
      "status": "working",
      "current_task": "UI-001: Create base templates",
      "progress": 45,
      "estimated_completion": "2025-10-30T17:00:00Z",
      "blockers": [],
      "health": "green"
    },
    "agent-5-security": {
      "status": "idle",
      "current_task": null,
      "progress": 0,
      "waiting_for": ["agent-2-database", "agent-3-api"],
      "health": "green"
    },
    "agent-6-logic": {
      "status": "idle",
      "current_task": null,
      "health": "green"
    },
    "agent-7-scheduler": {
      "status": "idle",
      "current_task": null,
      "health": "green"
    },
    "agent-8-powershell": {
      "status": "idle",
      "current_task": null,
      "health": "green"
    },
    "agent-9-test": {
      "status": "working",
      "current_task": "TEST-001: Unit tests for models",
      "progress": 30,
      "health": "green"
    },
    "agent-10-devops": {
      "status": "completed",
      "current_task": "DEVOPS-001: CI/CD pipeline setup",
      "progress": 100,
      "health": "green"
    }
  },
  "tasks": {
    "total": 50,
    "completed": 8,
    "in_progress": 6,
    "blocked": 2,
    "pending": 34
  },
  "metrics": {
    "code_coverage": 72.5,
    "test_pass_rate": 100,
    "build_status": "passing",
    "open_issues": 12,
    "open_prs": 4
  },
  "dependencies": {
    "agent-3-api": ["agent-2-database"],
    "agent-5-security": ["agent-2-database", "agent-3-api"],
    "agent-6-logic": ["agent-2-database"],
    "agent-7-scheduler": ["agent-6-logic"],
    "agent-9-test": ["agent-2-database", "agent-3-api", "agent-4-frontend"]
  }
}
```

【3. Context7統合】

長期記憶として重要な決定事項や設計変更を保存。

Context7エントリ例:
```
Date: 2025-10-30
Category: Design Decision
Agents: agent-1-pm, agent-2-database

決定事項:
バックアップコピーの管理方法について、当初は単一テーブルで
管理する予定でしたが、以下の理由により別テーブルに分離:

1. 3-2-1-1-0ルールの各コピーを明確に管理
2. 異なる属性（オフサイト、オフライン）を持つ
3. 将来的な拡張性

実装:
- backup_copies テーブルを作成
- job_id + copy_number でインデックス
- is_offsite, is_offline フラグで管理

影響を受けるAgent:
- agent-3-api: APIエンドポイント設計
- agent-6-logic: コンプライアンスチェックロジック
```

5.2 メッセージングパターン
--------------------------

【パターン1: 同期通信（要求-応答）】

Agent Aが Agent Bに情報を要求:

```
Agent-3-API → Agent-2-Database:
"Userモデルのスキーマ定義を教えてください"

Agent-2-Database → Agent-3-API:
"Userモデル:
- id: Integer, Primary Key
- username: String(64), Unique
- email: String(120), Unique
- password_hash: String(256)
- role: String(20)
..."
```

実装方法: GitHub Issue コメント

【パターン2: 非同期通知（発行-購読）】

Agent Aが作業完了を通知:

```
Agent-2-Database → All:
"データベースモデルの実装が完了しました。
app/models.py をコミットしました (commit: abc123)

次のAgentが作業を開始できます:
- Agent-3-API: REST API実装
- Agent-5-Security: 認証機能実装
- Agent-6-Logic: ビジネスロジック実装"
```

実装方法: 
- GitHub Issue更新 + ラベル変更
- project-state.json更新
- @メンションで通知

【パターン3: ブロードキャスト】

Agent PMが全Agentに通知:

```
Agent-1-PM → All Agents:
"Sprint 1の中間レビューを実施します。

日時: 2025-10-31 10:00
場所: GitHub Discussions

各Agentは以下を報告してください:
1. 完了したタスク
2. 進行中のタスク
3. ブロッカー
4. 次のタスク"
```

5.3 依存関係管理
----------------

【依存関係グラフ】

```
Agent-1 (PM)
    ↓ (タスク割り当て)
    ├→ Agent-2 (Database)
    │      ↓ (モデル完成)
    │      ├→ Agent-3 (API)
    │      │      ↓ (API完成)
    │      │      ├→ Agent-4 (Frontend)
    │      │      └→ Agent-5 (Security)
    │      ├→ Agent-6 (Logic)
    │      │      ↓ (ロジック完成)
    │      │      └→ Agent-7 (Scheduler)
    │      └→ Agent-9 (Test)
    │
    ├→ Agent-4 (Frontend - 並列)
    │      ↓ (テンプレート完成)
    │      └→ Agent-3 (統合)
    │
    ├→ Agent-8 (PowerShell - 独立)
    │
    └→ Agent-10 (DevOps - 最初に実行)
           ↓ (CI/CD完成)
           └→ All Agents (継続的統合)
```

【依存関係解決アルゴリズム】

```python
# docs/agent-communication/dependency_resolver.py

class DependencyResolver:
    """Agent間の依存関係を管理"""
    
    def __init__(self, dependencies):
        self.dependencies = dependencies  # {agent: [required_agents]}
        self.completed = set()
    
    def can_start(self, agent):
        """Agentが作業を開始できるか判定"""
        required = self.dependencies.get(agent, [])
        return all(req in self.completed for req in required)
    
    def mark_completed(self, agent):
        """Agentの作業完了をマーク"""
        self.completed.add(agent)
    
    def get_ready_agents(self):
        """作業開始可能なAgentをリストアップ"""
        all_agents = set(self.dependencies.keys())
        not_completed = all_agents - self.completed
        return [agent for agent in not_completed if self.can_start(agent)]
    
    def get_blocked_agents(self):
        """ブロックされているAgentとその理由"""
        blocked = {}
        all_agents = set(self.dependencies.keys())
        not_completed = all_agents - self.completed
        
        for agent in not_completed:
            if not self.can_start(agent):
                required = self.dependencies.get(agent, [])
                waiting_for = [req for req in required if req not in self.completed]
                blocked[agent] = waiting_for
        
        return blocked

# 使用例
dependencies = {
    'agent-3-api': ['agent-2-database'],
    'agent-5-security': ['agent-2-database', 'agent-3-api'],
    'agent-6-logic': ['agent-2-database'],
    'agent-7-scheduler': ['agent-6-logic'],
    'agent-9-test': ['agent-2-database', 'agent-3-api']
}

resolver = DependencyResolver(dependencies)

# Agent-2が完了
resolver.mark_completed('agent-2-database')

# 作業開始可能なAgent
ready = resolver.get_ready_agents()
# ['agent-3-api', 'agent-6-logic', 'agent-9-test']

# ブロックされているAgent
blocked = resolver.get_blocked_agents()
# {'agent-5-security': ['agent-3-api'], 'agent-7-scheduler': ['agent-6-logic']}
```

5.4 コンフリクト解決
--------------------

【コンフリクトの種類】

1. ファイルコンフリクト
   - 複数のAgentが同じファイルを編集
   
2. API設計コンフリクト
   - 異なるAgentが異なるAPI設計を提案
   
3. データモデルコンフリクト
   - スキーマ設計の不一致

4. スケジュールコンフリクト
   - タスクの優先順位が競合

【解決プロトコル】

ステップ1: コンフリクト検出
```
Agent-3-API:
"app/models.py で Agent-2-Database の変更と競合しています"
```

ステップ2: Agent PM に報告
```
GitHub Issue作成:
タイトル: [CONFLICT] app/models.py の変更競合
担当: @agent-1-pm
ラベル: conflict, high-priority
```

ステップ3: PM による調停
```
Agent-1-PM の判断:
1. 両方のAgentから変更理由をヒアリング
2. 設計仕様書と照らし合わせ
3. 最適な解決策を決定
4. 決定事項をContext7に記録
```

ステップ4: 実装
```
決定された方針に従ってマージ
コンフリクト解決の記録を残す
```

5.5 エラーハンドリング
----------------------

【エラー種別】

1. Agent障害
   - Agentが応答しない
   - 実装に致命的なバグ

2. ビルド失敗
   - CI/CDパイプラインでエラー

3. テスト失敗
   - Agent-9が検出

4. デプロイ失敗
   - Agent-10のデプロイスクリプトエラー

【対応フロー】

```
エラー検出
    ↓
GitHub Actionsが失敗を検知
    ↓
Agent-1-PM に自動通知
    ↓
PM が原因Agentを特定
    ↓
該当Agentに修正指示
    ↓
修正完了後、再テスト
    ↓
成功 → 次のステップへ
失敗 → エスカレーション（人間開発者）
```

================================================================================
6. タスク管理・ワークフロー
================================================================================

6.1 スプリント計画
------------------

【スプリント期間】
- 1スプリント = 2週間
- 計画: 1日（月曜日）
- 開発: 9日（火曜日〜翌週金曜日）
- レビュー: 1日（翌週月曜日）

【スプリント1の例】

期間: 2025-10-28 〜 2025-11-08

目標:
- MVPの基本機能実装
- データベース設計完了
- 基本的なAPI実装
- シンプルなダッシュボード

タスク割り当て:

Agent-10 (DevOps):
- CI/CDパイプライン構築
- 見積: 1日

Agent-2 (Database):
- SQLAlchemyモデル実装（14テーブル）
- マイグレーション作成
- 見積: 3日

Agent-3 (API):
- REST APIエンドポイント実装
  * 認証 API
  * ジョブ管理 API
  * コピー管理 API
- 見積: 4日

Agent-4 (Frontend):
- ベーステンプレート作成
- ダッシュボード画面
- ジョブ一覧画面
- 見積: 4日

Agent-5 (Security):
- Flask-Login統合
- 認証機能実装
- RBAC実装
- 見積: 3日

Agent-6 (Logic):
- コンプライアンスチェックロジック
- 見積: 3日

Agent-9 (Test):
- 単体テスト作成
- 見積: 継続的

6.2 タスクボード
----------------

【GitHub Projects】

カンバン方式:

```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ Backlog  │  To Do   │In Progress│ Review  │  Done    │
├──────────┼──────────┼──────────┼──────────┼──────────┤
│ 34 items │ 8 items  │ 6 items  │ 2 items  │ 12 items │
│          │          │          │          │          │
│ UI-005   │ DB-002   │ DB-001   │ API-003  │ DEVOPS-1 │
│ API-010  │ API-004  │ API-001  │ UI-001   │ DB-000   │
│ LOGIC-05 │ UI-002   │ UI-003   │          │ API-000  │
│ ...      │ ...      │ ...      │          │ ...      │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

【タスクカード構造】

```
[DB-001] Implement SQLAlchemy models

Agent: agent-2-database
Priority: High
Estimate: 3 days
Dependencies: None

Description:
14個のデータベースモデルをapp/models.pyに実装

Acceptance Criteria:
- [ ] 全14モデルが定義されている
- [ ] リレーションシップが正しく設定されている
- [ ] インデックスが適切に設定されている
- [ ] to_dict()メソッドが実装されている
- [ ] 単体テストが通過する

Subtasks:
- [x] Userモデル
- [x] BackupJobモデル
- [ ] BackupCopyモデル
- [ ] OfflineMediaモデル
- [ ] VerificationTestモデル
- [ ] ...

Comments: 3
Linked PRs: #12
```

6.3 進捗トラッキング
--------------------

【日次スタンドアップ】

毎日10:00（自動）、各Agentが報告:

Agent-2-Database:
```
昨日:
- Userモデル実装完了
- BackupJobモデル実装完了

今日:
- BackupCopyモデル実装
- OfflineMediaモデル実装

ブロッカー:
- なし
```

Agent-3-API:
```
昨日:
- なし（Agent-2待ち）

今日:
- なし（Agent-2待ち）

ブロッカー:
- Agent-2のモデル実装待ち
```

【バーンダウンチャート】

スプリントの進捗を可視化:

```
残タスク数
 50 │●
    │  ●
 40 │    ●
    │      ●●
 30 │        ●
    │         ●●
 20 │           ●●
    │             ●
 10 │              ●●
    │                ●
  0 │_________________●
    0  2  4  6  8  10 12 14日
    
理想線: 直線的に減少
実績線: ●でプロット
```

6.4 コードレビュープロセス
--------------------------

【Pull Requestフロー】

1. Agent が実装完了
   ↓
2. 自己チェック
   - コードスタイル確認
   - テスト実行
   - ドキュメント更新
   ↓
3. PR作成
   ```
   Title: [Agent-2] Implement database models
   
   ## Changes
   - 14個のSQLAlchemyモデルを実装
   - マイグレーションスクリプト作成
   - 単体テスト追加
   
   ## Testing
   - ✅ All unit tests pass
   - ✅ Migration successful
   - ✅ Coverage: 95%
   
   ## Related Issues
   Closes #10
   
   ## Agent Communication
   @agent-3-api @agent-5-security @agent-6-logic
   データベースモデルが利用可能になりました
   ```
   ↓
4. 自動チェック（GitHub Actions）
   - Lint
   - Tests
   - Coverage
   - Security scan
   ↓
5. Agent-9 (Test) レビュー
   - テストカバレッジ確認
   - テストケース品質確認
   ↓
6. Agent-1 (PM) レビュー
   - 要件との整合性確認
   - 設計仕様との一致確認
   ↓
7. 承認 & マージ
   ↓
8. developブランチに統合
   ↓
9. 依存するAgentに通知

【レビュー基準】

必須項目:
- [ ] すべてのテストが通過
- [ ] カバレッジ80%以上
- [ ] Lintエラーなし
- [ ] ドキュメント更新済み
- [ ] コミットメッセージが明確
- [ ] コンフリクトなし

推奨項目:
- [ ] コードコメント適切
- [ ] パフォーマンス考慮
- [ ] エラーハンドリング適切
- [ ] セキュリティ考慮

6.5 リリース管理
----------------

【バージョニング】

セマンティックバージョニング: MAJOR.MINOR.PATCH

- MAJOR: 互換性のない変更
- MINOR: 後方互換性のある機能追加
- PATCH: 後方互換性のあるバグ修正

例:
- 0.1.0: 初期開発版
- 0.2.0: 基本機能追加
- 0.3.0: API拡張
- 1.0.0: 正式リリース

【リリースプロセス】

1. developブランチで開発
   ↓
2. 機能完成
   ↓
3. リリースブランチ作成
   ```bash
   git checkout develop
   git checkout -b release/v0.1.0
   ```
   ↓
4. バージョン番号更新
   - __init__.py
   - setup.py
   - CHANGELOG.md
   ↓
5. 最終テスト
   ↓
6. mainにマージ
   ```bash
   git checkout main
   git merge release/v0.1.0
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin main --tags
   ```
   ↓
7. developにもマージ
   ```bash
   git checkout develop
   git merge release/v0.1.0
   git push origin develop
   ```
   ↓
8. リリースノート作成
   ↓
9. デプロイ

【CHANGELOG.md】

```markdown
# Changelog

## [0.1.0] - 2025-11-08

### Added
- データベースモデル実装（14テーブル）
- REST API基本エンドポイント
- ダッシュボード画面
- 3-2-1-1-0コンプライアンスチェック機能
- 認証・認可機能

### Changed
- なし

### Fixed
- なし

## [0.0.1] - 2025-10-28

### Added
- プロジェクト初期化
- CI/CDパイプライン構築
```

================================================================================
7. Git戦略とブランチ管理
================================================================================

7.1 ブランチ戦略
----------------

【Git Flow 変形版】

```
main (本番)
    │
    ├─── v1.0.0 (tag)
    ├─── v0.2.0 (tag)
    └─── v0.1.0 (tag)
    ↑
develop (開発統合)
    │
    ├─── feature/database-models (Agent-2)
    │
    ├─── feature/api-endpoints (Agent-3)
    │
    ├─── feature/dashboard-ui (Agent-4)
    │
    ├─── feature/authentication (Agent-5)
    │
    ├─── feature/compliance-logic (Agent-6)
    │
    ├─── feature/scheduler (Agent-7)
    │
    ├─── feature/powershell-integration (Agent-8)
    │
    └─── feature/tests (Agent-9)
```

【ブランチルール】

main:
- 常に本番デプロイ可能な状態
- 直接プッシュ禁止
- マージはPRのみ
- タグ付けで versioning

develop:
- 開発統合ブランチ
- 各featureブランチの統合先
- 直接プッシュ禁止
- マージはPRのみ

feature/*:
- 各Agentの作業ブランチ
- developから分岐
- developにマージ
- 命名規則: feature/{agent-name}-{feature-name}

hotfix/*:
- 緊急バグ修正
- mainから分岐
- main と develop にマージ
- 命名規則: hotfix/{issue-number}-{brief-description}

release/*:
- リリース準備
- developから分岐
- main と develop にマージ
- 命名規則: release/v{version}

7.2 ブランチ命名規則
--------------------

【形式】

```
{type}/{agent-name}-{description}

type:
- feature: 新機能
- bugfix: バグ修正
- hotfix: 緊急修正
- release: リリース準備
- docs: ドキュメントのみ
- refactor: リファクタリング

agent-name:
- database
- api
- frontend
- security
- logic
- scheduler
- powershell
- test
- devops
```

【例】

```
feature/database-models
feature/api-endpoints
feature/frontend-dashboard
feature/security-rbac
feature/logic-compliance-checker
bugfix/api-authentication-error
hotfix/critical-data-loss
release/v0.1.0
docs/api-documentation
refactor/database-query-optimization
```

7.3 コミットメッセージ規約
--------------------------

【Conventional Commits】

形式:
```
<type>(<scope>): <subject>

<body>

<footer>
```

type:
- feat: 新機能
- fix: バグ修正
- docs: ドキュメント
- style: フォーマット
- refactor: リファクタリング
- test: テスト追加・修正
- chore: その他の変更

scope (オプション):
- database
- api
- frontend
- auth
- etc.

【例】

```
feat(database): implement User and BackupJob models

- Add User model with authentication fields
- Add BackupJob model with relationships
- Add migration script

Closes #10
```

```
fix(api): resolve authentication token expiration issue

Token was expiring after 1 hour instead of 24 hours
due to incorrect timedelta calculation.

Fixes #45
```

```
test(database): add unit tests for models

- Test User model creation and password hashing
- Test BackupJob model relationships
- Test cascade delete behavior

Coverage increased from 75% to 92%
```

7.4 マージ戦略
--------------

【Squash and Merge（推奨）】

featureブランチの複数コミットを1つにまとめてマージ:

```bash
# PRマージ時に自動的に実行される
# Before:
feature/database-models
  ├─ commit 1: WIP: User model
  ├─ commit 2: WIP: BackupJob model
  ├─ commit 3: Fix typo
  └─ commit 4: Add tests

# After (develop):
develop
  └─ feat(database): implement database models
```

利点:
- 履歴がクリーン
- 各featureが1コミットに
- レビューしやすい

【Merge Commit】

重要な統合ポイントで使用:

```bash
# release → main
git checkout main
git merge --no-ff release/v0.1.0
git tag -a v0.1.0 -m "Release 0.1.0"
```

利点:
- 完全な履歴保存
- マージポイントが明確

【Rebase（使用しない）】

公開ブランチではrebase禁止:
- 履歴が書き換わる
- 他のAgentと競合

7.5 保護ルール
--------------

【mainブランチ】

GitHub設定:
```
Settings → Branches → Branch protection rules

ブランチ名パターン: main

✅ Require pull request reviews before merging
   - Required approvals: 1
   - Dismiss stale reviews when new commits are pushed

✅ Require status checks to pass before merging
   - lint
   - test
   - security-scan

✅ Require branches to be up to date before merging

✅ Include administrators

❌ Allow force pushes

❌ Allow deletions
```

【developブランチ】

```
ブランチ名パターン: develop

✅ Require pull request reviews before merging
   - Required approvals: 1

✅ Require status checks to pass before merging
   - lint
   - test

✅ Require branches to be up to date before merging

✅ Include administrators
```

7.6 コンフリクト解決手順
------------------------

【シナリオ】
Agent-2 と Agent-3 が同じファイルを編集してコンフリクト

【解決手順】

1. コンフリクト検出
```bash
git checkout develop
git pull origin develop
git checkout feature/api-endpoints
git merge develop

# CONFLICT in app/models.py
```

2. コンフリクトを確認
```bash
git status
# both modified: app/models.py
```

3. ファイルを開く
```python
# app/models.py

class BackupJob(db.Model):
<<<<<<< HEAD
    # Agent-3 の変更
    status = db.Column(db.String(20), default='pending')
=======
    # Agent-2 の変更
    status = db.Column(db.String(20), default='active')
>>>>>>> develop
```

4. Agent-1 (PM) に相談
```
GitHub Issue作成:
[CONFLICT] app/models.py status field default value

Agent-2: 'active'
Agent-3: 'pending'

設計仕様書を確認してください
```

5. PMの判断
```
設計仕様書によると、初期状態は'pending'が正しい。
Agent-3 の変更を採用。
```

6. 解決
```python
class BackupJob(db.Model):
    status = db.Column(db.String(20), default='pending')
```

7. コミット
```bash
git add app/models.py
git commit -m "fix: resolve conflict in BackupJob.status default value"
git push origin feature/api-endpoints
```

================================================================================
8. セットアップ手順（完全版）
================================================================================

8.1 開発環境セットアップ
------------------------

【前提条件】

ハードウェア:
- CPU: 8コア以上
- RAM: 16GB以上
- ストレージ: SSD 100GB以上

ソフトウェア:
- OS: Ubuntu 22.04/24.04 LTS
- Python: 3.11以上
- Node.js: 18以上
- Git: 2.30以上

【ステップ1: システム更新】

```bash
sudo apt update
sudo apt upgrade -y
```

【ステップ2: Python環境】

```bash
# Python 3.11インストール
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# pipインストール
sudo apt install python3-pip -y

# venv作成
cd /mnt/Linux-ExHDD/backup-management-system
python3.11 -m venv venv

# 有効化
source venv/bin/activate

# pip更新
pip install --upgrade pip
```

【ステップ3: Node.js環境】

```bash
# Node.jsインストール
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# バージョン確認
node --version  # v18.x.x
npm --version   # 9.x.x
```

【ステップ4: Git設定】

```bash
# Git設定
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Git エディタ設定
git config --global core.editor "nano"

# デフォルトブランチ名
git config --global init.defaultBranch main
```

【ステップ5: プロジェクトクローン】

```bash
# リポジトリクローン
cd /mnt/Linux-ExHDD
git clone https://github.com/Kensan196948G/backup-management-system.git
cd backup-management-system

# developブランチに切り替え
git checkout develop
```

【ステップ6: 依存パッケージインストール】

```bash
# 仮想環境有効化
source venv/bin/activate

# パッケージインストール
pip install -r requirements.txt

# 開発用パッケージ
pip install pytest pytest-cov flake8 pylint black
```

【ステップ7: 環境変数設定】

```bash
# .envファイル作成
cp .env.example .env

# 編集
nano .env
```

.env内容:
```bash
# Flask設定
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-change-this

# データベース
DATABASE_URL=sqlite:///data/backup_mgmt.db

# セキュリティ
BCRYPT_LOG_ROUNDS=12

# メール設定
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Teams Webhook
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...

# ログ
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

【ステップ8: データベース初期化】

```bash
# dataディレクトリ作成
mkdir -p data

# マイグレーション初期化
flask db init

# マイグレーション作成
flask db migrate -m "Initial migration"

# マイグレーション適用
flask db upgrade
```

【ステップ9: 開発サーバー起動】

```bash
# 起動
python run.py

# または
flask run --host=0.0.0.0 --port=5000
```

ブラウザで確認:
http://localhost:5000

8.2 MCP設定（再掲）
-------------------

【Claude Desktop設定】

```bash
# 設定ファイル編集
nano ~/.config/Claude/claude_desktop_config.json
```

内容:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/mnt/Linux-ExHDD/backup-management-system"
      ]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    },
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "--db-path",
        "/mnt/Linux-ExHDD/backup-management-system/data/backup_mgmt.db"
      ]
    }
  }
}
```

【Claude Desktop再起動】

```bash
pkill -f "Claude"
# GUI から再起動
```

8.3 Agent機能初期化
--------------------

【ステップ1: プロジェクト状態ファイル作成】

```bash
mkdir -p docs/agent-communication

# 初期状態ファイル
cat > docs/agent-communication/project-state.json << 'EOF'
{
  "updated_at": "2025-10-30T00:00:00Z",
  "project": {
    "name": "backup-management-system",
    "phase": "initialization",
    "sprint": 0,
    "version": "0.0.1-dev"
  },
  "agents": {
    "agent-1-pm": {"status": "active"},
    "agent-2-database": {"status": "idle"},
    "agent-3-api": {"status": "idle"},
    "agent-4-frontend": {"status": "idle"},
    "agent-5-security": {"status": "idle"},
    "agent-6-logic": {"status": "idle"},
    "agent-7-scheduler": {"status": "idle"},
    "agent-8-powershell": {"status": "idle"},
    "agent-9-test": {"status": "idle"},
    "agent-10-devops": {"status": "idle"}
  }
}
EOF
```

【ステップ2: Agent用ブランチ作成】

```bash
# 各Agentのfeatureブランチ
git checkout develop

git checkout -b feature/database-models
git push -u origin feature/database-models

git checkout develop
git checkout -b feature/api-endpoints
git push -u origin feature/api-endpoints

# ... 各Agentのブランチを作成
```

【ステップ3: GitHub Projects セットアップ】

GitHub Webインターフェース:
1. リポジトリ → Projects → New project
2. Board view選択
3. カラム作成:
   - Backlog
   - To Do
   - In Progress
   - Review
   - Done

【ステップ4: Issue Templates 作成】

.github/ISSUE_TEMPLATE/agent-task.md:
```markdown
---
name: Agent Task
about: Task template for Agent-based development
title: '[AGENT-X] '
labels: ''
assignees: ''
---

## Agent
Agent-X-Name

## Task Description


## Dependencies
- [ ] Agent-Y: Task-Z

## Acceptance Criteria
- [ ] 
- [ ] 

## Estimated Time


## Related PRs

```

8.4 Git Hooks セットアップ
---------------------------

【インストール】

```bash
# Hooksディレクトリ
cd /mnt/Linux-ExHDD/backup-management-system/.git/hooks

# pre-commit
cat > pre-commit << 'EOF'
#!/bin/bash
set -e
echo "Running pre-commit checks..."

# Python syntax check
python -m py_compile $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$') 2>/dev/null || {
    echo "Python syntax errors!"
    exit 1
}

# flake8
if command -v flake8 &> /dev/null; then
    flake8 $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$') 2>/dev/null || true
fi

# black
if command -v black &> /dev/null; then
    black $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$') 2>/dev/null
    git add $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')
fi

echo "Pre-commit checks passed!"
EOF

chmod +x pre-commit

# pre-push
cat > pre-push << 'EOF'
#!/bin/bash
set -e
echo "Running pre-push tests..."

# 単体テスト
pytest tests/ -v || {
    echo "Tests failed! Push aborted."
    exit 1
}

echo "All tests passed!"
EOF

chmod +x pre-push
```

8.5 CI/CD パイプライン確認
---------------------------

【GitHub Actions 動作確認】

```bash
# テストコミット
git checkout develop
echo "# Test" >> README.md
git add README.md
git commit -m "test: verify CI/CD pipeline"
git push origin develop
```

GitHub Web:
- Actions タブを確認
- Workflow実行を確認
- すべてのチェックが通過することを確認

================================================================================
9. 開発フロー実例
================================================================================

9.1 シナリオ: Sprint 1 開始
----------------------------

【Day 1: スプリント計画】

10:00 - Agent-1 (PM) がスプリント開始

```bash
# PMとして実行
claude agent pm "Sprint 1を開始します。

要件定義書と設計仕様書を分析し、
以下のタスクをGitHub Issuesとして作成してください:

1. データベースモデル実装
2. REST API基本エンドポイント
3. 認証機能
4. ダッシュボードUI
5. 3-2-1-1-0コンプライアンスチェック

各タスクには:
- 担当Agent
- 見積時間
- 優先度
- 依存関係
を設定してください"
```

PMが50個のIssueを自動生成:
- #10: [Agent-2] Implement database models (High, 3 days)
- #11: [Agent-3] Implement REST API endpoints (High, 4 days, depends on #10)
- #12: [Agent-4] Create dashboard UI (Medium, 4 days)
- #13: [Agent-5] Implement authentication (High, 3 days, depends on #10)
- ...

【Day 1-2: Agent-10 - CI/CD構築】

```bash
# DevOps Agentとして実行
git checkout develop
git checkout -b feature/devops-cicd

claude agent devops "CI/CDパイプラインを構築してください。

要件:
- GitHub Actionsを使用
- Lint, Test, Security scanを含む
- developとmainブランチで実行
- テストカバレッジレポート

.github/workflows/ci.yml を作成してください"
```

Agent-10が実装完了:
```bash
git add .github/workflows/ci.yml
git commit -m "feat(devops): implement CI/CD pipeline"
git push origin feature/devops-cicd
```

Pull Request作成:
```
Title: [Agent-10] Implement CI/CD pipeline

## Changes
- GitHub Actions workflow for CI/CD
- Lint, test, security scan steps
- Coverage reporting

## Testing
- ✅ Workflow syntax validated
- ✅ Test run successful

Closes #50
```

Agent-1 (PM) がレビュー・承認 → develop にマージ

【Day 2-4: Agent-2 - データベース実装】

```bash
# Database Agentとして実行
git checkout develop
git pull origin develop
git checkout -b feature/database-models

claude agent database "app/models.pyに14個のデータベースモデルを実装してください。

参照: docs/設計仕様書_3-2-1-1-0バックアップ管理システム.txt

要件:
- User, BackupJob, BackupCopy等 14テーブル
- リレーションシップ定義
- インデックス設定
- to_dict()メソッド実装"
```

Agent-2 が段階的に実装:

Day 2:
```bash
# Userモデル実装
git add app/models.py
git commit -m "feat(database): implement User model"

# BackupJobモデル実装
git add app/models.py
git commit -m "feat(database): implement BackupJob model"
```

Day 3:
```bash
# BackupCopyモデル実装
git add app/models.py
git commit -m "feat(database): implement BackupCopy model"

# その他のモデル実装
# ...
```

Day 4:
```bash
# マイグレーション作成
flask db migrate -m "Initial database schema"
git add migrations/
git commit -m "feat(database): add initial migration"

# テスト作成
git add tests/test_models.py
git commit -m "test(database): add model unit tests"

# プッシュ
git push origin feature/database-models
```

Pull Request作成:
```
Title: [Agent-2] Implement database models

## Changes
- 14個のSQLAlchemyモデル実装
- 初期マイグレーションスクリプト
- モデル単体テスト

## Testing
- ✅ All tests pass (92% coverage)
- ✅ Migration successful
- ✅ No lint errors

## Next Steps
@agent-3-api @agent-5-security @agent-6-logic
データベースモデルが利用可能になりました

Closes #10
```

Agent-1とAgent-9がレビュー → develop にマージ

【Day 5-8: Agent-3 - API実装（並列）】

Agent-2のPRマージ後、Agent-3が作業開始:

```bash
git checkout develop
git pull origin develop  # Agent-2の変更を取り込み
git checkout -b feature/api-endpoints

claude agent api "REST APIエンドポイントを実装してください。

app/api/に以下を作成:
- auth.py (認証API)
- jobs.py (ジョブ管理API)
- copies.py (コピー管理API)
- compliance.py (コンプライアンスAPI)

各エンドポイント:
- CRUD操作
- エラーハンドリング
- JSONレスポンス"
```

Day 5-6: 認証API
```bash
git add app/api/auth.py
git commit -m "feat(api): implement authentication endpoints"
```

Day 7: ジョブ管理API
```bash
git add app/api/jobs.py
git commit -m "feat(api): implement job management endpoints"
```

Day 8: その他API + テスト
```bash
git add app/api/
git add tests/test_api.py
git commit -m "feat(api): implement remaining endpoints and tests"
git push origin feature/api-endpoints
```

【Day 5-8: Agent-4 - UI実装（並列）】

Agent-2のPRマージ後、Agent-4も並列で作業:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/frontend-dashboard

claude agent frontend "ダッシュボードUIを実装してください。

app/templates/と app/static/に以下を作成:
- base.html (ベーステンプレート)
- dashboard.html (ダッシュボード)
- jobs/list.html (ジョブ一覧)

Bootstrap 5とChart.jsを使用"
```

実装・コミット・プッシュ

【Day 9-10: Agent-5 - 認証実装】

Agent-2とAgent-3のPRマージ後:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/security-authentication

claude agent security "Flask-Loginを使った認証機能を実装してください。

app/auth/に:
- __init__.py
- views.py (ログイン、ログアウト)
- decorators.py (admin_required等)
- forms.py (ログインフォーム)

ロールベースアクセス制御（admin/operator/viewer）"
```

実装・テスト・PR作成

【Day 11: 統合テスト】

すべてのAgentのPRがdevelopにマージされた後:

```bash
git checkout develop
git pull origin develop

# 統合テスト
pytest tests/ -v

# 手動テスト
python run.py
# ブラウザでhttp://localhost:5000を確認
```

【Day 12: レビュー & 次スプリント計画】

Agent-1 (PM) がスプリントレビュー:
- 完了タスク: 42/50
- 未完了: 8タスク → Sprint 2へ
- 次スプリント計画

9.2 コンフリクト解決の実例
--------------------------

【シナリオ】
Agent-2 と Agent-6 が app/models.py の BackupCopy モデルを
同時に編集してコンフリクト

Agent-2:
```python
# is_verified フィールドを追加
class BackupCopy(db.Model):
    # ...
    is_verified = db.Column(db.Boolean, default=False)
```

Agent-6:
```python
# verification_status フィールドを追加
class BackupCopy(db.Model):
    # ...
    verification_status = db.Column(db.String(20), default='pending')
```

【解決プロセス】

1. Agent-6 が develop にマージしようとしてコンフリクト検出
```bash
git checkout feature/logic-compliance
git merge develop
# CONFLICT in app/models.py
```

2. Issue作成
```
Title: [CONFLICT] BackupCopy model verification field

Agent-2: is_verified (Boolean)
Agent-6: verification_status (String)

どちらを採用すべきか決定が必要です。

@agent-1-pm @agent-2-database @agent-6-logic
```

3. Agent-1 (PM) が設計仕様書を確認
```
設計仕様書:
「検証状態は複数の状態を持つ（pending/in_progress/completed/failed）」

→ Agent-6 の verification_status (String) を採用
```

4. Agent-6 が解決
```bash
# Agent-2の変更を破棄、Agent-6の変更を採用
git checkout --theirs app/models.py
git add app/models.py
git commit -m "fix: resolve conflict - use verification_status"
git push origin feature/logic-compliance
```

5. Agent-2 に通知
```
@agent-2-database
コンフリクト解決のため、verification_statusを採用しました。
is_verifiedではなく、verification_statusを使用してください。
```

9.3 ホットフィックスの実例
--------------------------

【シナリオ】
本番環境でクリティカルなバグ発見

バグ内容:
認証トークンが1時間で期限切れ（設計では24時間）

【対応フロー】

1. バグ報告 (Issue作成)
```
Title: [BUG] Authentication token expires after 1 hour

Priority: Critical
Labels: bug, hotfix

Description:
認証トークンが1時間で期限切れになり、
ユーザーが頻繁にログアウトされる問題

Expected: 24時間有効
Actual: 1時間で失効
```

2. hotfixブランチ作成
```bash
git checkout main
git pull origin main
git checkout -b hotfix/auth-token-expiration
```

3. Agent-5 (Security) が修正
```python
# app/auth/views.py

# Before:
token_expires = timedelta(hours=1)

# After:
token_expires = timedelta(hours=24)
```

```bash
git add app/auth/views.py
git commit -m "fix(auth): set token expiration to 24 hours"
```

4. テスト
```bash
pytest tests/test_auth.py -v
# すべて通過確認
```

5. main にマージ
```bash
git checkout main
git merge hotfix/auth-token-expiration
git tag -a v0.1.1 -m "Hotfix: auth token expiration"
git push origin main --tags
```

6. develop にもマージ
```bash
git checkout develop
git merge hotfix/auth-token-expiration
git push origin develop
```

7. デプロイ
```bash
# 本番環境に即座にデプロイ
./deployment/windows/deploy.ps1
```

8. Issue クローズ
```
Fixed in v0.1.1

Changes:
- Token expiration: 1h → 24h

Deployed to production: 2025-10-30 16:00
```

================================================================================
10. モニタリング・デバッグ
================================================================================

10.1 Agent状態監視
-------------------

【監視ダッシュボード】

docs/agent-communication/monitor.py:

```python
#!/usr/bin/env python3
"""
Agent状態監視スクリプト
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

def load_project_state():
    """プロジェクト状態ファイル読み込み"""
    state_file = Path("docs/agent-communication/project-state.json")
    with open(state_file, 'r') as f:
        return json.load(f)

def check_agent_health():
    """Agent健康状態チェック"""
    state = load_project_state()
    
    print("=" * 60)
    print("Agent Status Monitor")
    print("=" * 60)
    print(f"Updated: {state['updated_at']}")
    print(f"Sprint: {state['project']['sprint']}")
    print()
    
    for agent_id, agent_data in state['agents'].items():
        status = agent_data.get('status', 'unknown')
        health = agent_data.get('health', 'unknown')
        
        # 色付け
        if health == 'green':
            health_icon = '✅'
        elif health == 'yellow':
            health_icon = '⚠️'
        elif health == 'red':
            health_icon = '🔴'
        else:
            health_icon = '❓'
        
        print(f"{health_icon} {agent_id}: {status}")
        
        if agent_data.get('current_task'):
            print(f"   Task: {agent_data['current_task']}")
        
        if agent_data.get('progress'):
            print(f"   Progress: {agent_data['progress']}%")
        
        if agent_data.get('blockers'):
            print(f"   ⚠️  Blockers: {agent_data['blockers']}")
        
        if agent_data.get('waiting_for'):
            print(f"   ⏳ Waiting: {agent_data['waiting_for']}")
        
        print()
    
    print("=" * 60)
    print("Tasks Summary")
    print("=" * 60)
    tasks = state['tasks']
    total = tasks['total']
    completed = tasks['completed']
    progress = (completed / total * 100) if total > 0 else 0
    
    print(f"Total: {total}")
    print(f"Completed: {completed} ({progress:.1f}%)")
    print(f"In Progress: {tasks['in_progress']}")
    print(f"Blocked: {tasks['blocked']}")
    print(f"Pending: {tasks['pending']}")
    
    if state.get('metrics'):
        print()
        print("=" * 60)
        print("Metrics")
        print("=" * 60)
        metrics = state['metrics']
        print(f"Code Coverage: {metrics.get('code_coverage', 0)}%")
        print(f"Test Pass Rate: {metrics.get('test_pass_rate', 0)}%")
        print(f"Build Status: {metrics.get('build_status', 'unknown')}")

if __name__ == "__main__":
    check_agent_health()
```

使用:
```bash
python docs/agent-communication/monitor.py
```

出力例:
```
============================================================
Agent Status Monitor
============================================================
Updated: 2025-10-30T15:30:00Z
Sprint: 1

✅ agent-1-pm: active
   Task: Sprint planning and task assignment

✅ agent-2-database: working
   Task: DB-001: Implement SQLAlchemy models
   Progress: 85%

⚠️  agent-3-api: waiting
   Task: API-001: Implement REST endpoints
   Progress: 0%
   ⏳ Waiting: ['agent-2-database']

✅ agent-4-frontend: working
   Task: UI-001: Create base templates
   Progress: 45%

...

============================================================
Tasks Summary
============================================================
Total: 50
Completed: 8 (16.0%)
In Progress: 6
Blocked: 2
Pending: 34

============================================================
Metrics
============================================================
Code Coverage: 72.5%
Test Pass Rate: 100%
Build Status: passing
```

10.2 ログ管理
-------------

【アプリケーションログ】

app/__init__.py:
```python
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    """ログ設定"""
    if not app.debug:
        # ログディレクトリ作成
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # ファイルハンドラ
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
```

【Agent活動ログ】

各Agentの作業を記録:

docs/agent-communication/agent-logs/{agent-id}.log

例: docs/agent-communication/agent-logs/agent-2-database.log
```
2025-10-30 10:00:00 - INFO - Agent-2-Database started
2025-10-30 10:05:00 - INFO - Task DB-001 assigned
2025-10-30 10:10:00 - INFO - Started implementing User model
2025-10-30 11:30:00 - INFO - User model completed
2025-10-30 11:35:00 - INFO - Started implementing BackupJob model
2025-10-30 13:00:00 - INFO - BackupJob model completed
2025-10-30 14:00:00 - INFO - Committed changes (abc123)
2025-10-30 14:05:00 - INFO - Created Pull Request #12
2025-10-30 15:00:00 - INFO - PR #12 approved and merged
2025-10-30 15:05:00 - INFO - Task DB-001 completed
```

10.3 パフォーマンスモニタリング
------------------------------

【CI/CD実行時間】

.github/workflows/ci.yml に計測を追加:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Start time
        run: echo "START_TIME=$(date +%s)" >> $GITHUB_ENV
      
      - uses: actions/checkout@v4
      
      - name: Run tests
        run: pytest tests/
      
      - name: Calculate duration
        run: |
          END_TIME=$(date +%s)
          DURATION=$((END_TIME - START_TIME))
          echo "Test duration: ${DURATION}s"
          echo "DURATION=${DURATION}" >> $GITHUB_ENV
      
      - name: Update metrics
        run: |
          echo "Test execution time: ${{ env.DURATION }}s" >> metrics.txt
```

【データベースクエリ分析】

app/utils/query_profiler.py:
```python
from flask_sqlalchemy import get_debug_queries
import time

def profile_queries(f):
    """クエリプロファイリングデコレータ"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        
        queries = get_debug_queries()
        
        print(f"Function: {f.__name__}")
        print(f"Duration: {duration:.3f}s")
        print(f"Queries: {len(queries)}")
        
        for query in queries:
            print(f"  SQL: {query.statement}")
            print(f"  Duration: {query.duration:.3f}s")
        
        return result
    return wrapper
```

使用:
```python
@profile_queries
def get_compliance_summary():
    """コンプライアンスサマリー取得"""
    jobs = BackupJob.query.all()
    # ...
```

10.4 デバッグツール
-------------------

【Flask Debug Toolbar】

requirements-dev.txt:
```
flask-debugtoolbar==0.14.1
```

app/__init__.py:
```python
from flask_debugtoolbar import DebugToolbarExtension

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    if app.debug:
        toolbar = DebugToolbarExtension(app)
    
    # ...
    return app
```

【VSCode デバッグ設定】

.vscode/launch.json:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "run.py",
                "FLASK_ENV": "development"
            },
            "args": [
                "run",
                "--no-debugger",
                "--no-reload"
            ],
            "jinja": true,
            "justMyCode": true
        },
        {
            "name": "Python: Pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/",
                "-v"
            ],
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

【Agent デバッグモード】

環境変数:
```bash
export AGENT_DEBUG=1
export AGENT_VERBOSE=1
```

詳細ログを出力:
```
[DEBUG] Agent-2-Database: Parsing requirements from docs/設計仕様書...
[DEBUG] Agent-2-Database: Found 14 table definitions
[DEBUG] Agent-2-Database: Generating User model...
[VERBOSE] Agent-2-Database: Added field: id (Integer, PrimaryKey)
[VERBOSE] Agent-2-Database: Added field: username (String(64), Unique)
...
```

================================================================================
11. トラブルシューティング
================================================================================

11.1 一般的な問題と解決
-----------------------

【問題1: Agent が応答しない】

症状:
```
Agent-3-API が24時間以上応答なし
project-state.jsonが更新されない
```

診断:
```bash
# 1. project-state.json確認
cat docs/agent-communication/project-state.json | jq '.agents."agent-3-api"'

# 2. ログ確認
tail -f docs/agent-communication/agent-logs/agent-3-api.log

# 3. GitHubアクティビティ確認
# feature/api-endpoints ブランチの最終コミット確認
```

解決策:
```
1. Agent-1 (PM) が状況確認
2. ブロッカーがあれば解消
3. タスクを他のAgentに再割り当て
4. 必要に応じて人間開発者がエスカレーション
```

【問題2: CI/CDパイプライン失敗】

症状:
```
GitHub Actions でテストが失敗
"Test suite failed with 5 errors"
```

診断:
```bash
# 1. GitHub Actionsログ確認
# WebインターフェースでFailedジョブのログ表示

# 2. ローカルで再現
git checkout feature/api-endpoints
pytest tests/ -v

# 3. 失敗したテストを特定
pytest tests/test_api.py::test_authentication -v
```

解決策:
```bash
# 1. テスト修正
nano tests/test_api.py

# 2. 再実行
pytest tests/test_api.py -v

# 3. コミット
git add tests/test_api.py
git commit -m "fix(test): resolve authentication test failure"
git push origin feature/api-endpoints
```

【問題3: データベースマイグレーションエラー】

症状:
```
flask db upgrade
Error: Can't locate revision abc123
```

診断:
```bash
# 1. マイグレーション履歴確認
flask db history

# 2. 現在のリビジョン確認
flask db current

# 3. データベース状態確認
sqlite3 data/backup_mgmt.db
sqlite> .schema alembic_version
```

解決策:
```bash
# オプション1: リセット
rm data/backup_mgmt.db
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# オプション2: 手動修正
flask db stamp head
flask db upgrade
```

【問題4: マージコンフリクト】

症状:
```
git merge develop
CONFLICT (content): Merge conflict in app/models.py
```

診断:
```bash
# コンフリクトファイル確認
git status
# both modified: app/models.py

# コンフリクト内容確認
git diff app/models.py
```

解決策:
```bash
# 1. ファイルを開いて手動解決
nano app/models.py

# 2. コンフリクトマーカー削除
# <<<<<<< HEAD
# =======
# >>>>>>> develop

# 3. テスト実行
pytest tests/test_models.py

# 4. マーク解決済み
git add app/models.py
git commit -m "fix: resolve merge conflict in models.py"
```

【問題5: メモリ不足】

症状:
```
MemoryError during test execution
pytest killed by OOM
```

診断:
```bash
# メモリ使用状況
free -h

# プロセス確認
top -o %MEM
```

解決策:
```bash
# 1. テストを分割実行
pytest tests/test_models.py
pytest tests/test_api.py
# 全体を一度に実行しない

# 2. pytest設定調整
# pytest.ini
[pytest]
addopts = -n auto --maxprocesses=4

# 3. システムリソース増強
# RAMを追加
```

11.2 Agent固有の問題
---------------------

【Agent-2 (Database): モデル定義エラー】

問題:
```python
# リレーションシップの循環参照
class BackupJob(db.Model):
    copies = db.relationship('BackupCopy', backref='job')

class BackupCopy(db.Model):
    job = db.relationship('BackupJob', backref='copies')
# エラー: Circular reference detected
```

解決:
```python
# 正しい定義
class BackupJob(db.Model):
    copies = db.relationship('BackupCopy', backref='job', lazy='dynamic')

class BackupCopy(db.Model):
    job_id = db.Column(db.Integer, db.ForeignKey('backup_jobs.id'))
    # backref で自動的にjobプロパティが作成される
```

【Agent-3 (API): 認証エラー】

問題:
```
401 Unauthorized
Token verification failed
```

解決:
```python
# app/api/auth.py

# 問題のあるコード
token = jwt.encode(payload, 'wrong-secret-key')

# 修正
token = jwt.encode(payload, app.config['SECRET_KEY'])
```

【Agent-4 (Frontend): テンプレートエラー】

問題:
```
jinja2.exceptions.UndefinedError: 'compliance_data' is undefined
```

解決:
```python
# app/views/dashboard.py

@bp.route('/dashboard')
@login_required
def dashboard():
    # 問題: compliance_dataを渡していない
    return render_template('dashboard.html')

# 修正
@bp.route('/dashboard')
@login_required
def dashboard():
    compliance_data = get_compliance_summary()
    return render_template('dashboard.html', 
                         compliance_data=compliance_data)
```

【Agent-9 (Test): テスト失敗】

問題:
```
AssertionError: Expected 3, got 2
```

解決:
```python
# tests/test_services.py

# 問題のあるテスト
def test_compliance_check():
    job = create_test_job()
    # コピーを2つしか作成していない
    create_backup_copy(job, 1)
    create_backup_copy(job, 2)
    
    result = check_compliance(job)
    assert result['copies_count'] == 3  # 失敗

# 修正
def test_compliance_check():
    job = create_test_job()
    # 3つのコピーを作成
    create_backup_copy(job, 1)
    create_backup_copy(job, 2)
    create_backup_copy(job, 3)
    
    result = check_compliance(job)
    assert result['copies_count'] == 3  # 成功
```

11.3 パフォーマンス問題
-----------------------

【問題: 大量データでクエリが遅い】

症状:
```
Dashboard loading time: 15 seconds
Database query time: 12 seconds
```

診断:
```python
# クエリプロファイリング
from flask_sqlalchemy import get_debug_queries

@app.after_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= 1.0:  # 1秒以上
            app.logger.warning(
                f"SLOW QUERY: {query.statement}\n"
                f"Duration: {query.duration}s"
            )
    return response
```

解決:
```python
# 問題のあるコード
jobs = BackupJob.query.all()
for job in jobs:
    copies = job.backup_copies.all()  # N+1クエリ!

# 修正: Eager Loading
jobs = BackupJob.query.options(
    db.joinedload(BackupJob.backup_copies)
).all()

# または: Select IN Loading
jobs = BackupJob.query.options(
    db.selectinload(BackupJob.backup_copies)
).all()
```

【問題: メモリ使用量が多い】

症状:
```
Memory usage: 2GB
Process killed by OOM
```

解決:
```python
# 問題: 全データをメモリに読み込み
jobs = BackupJob.query.all()

# 修正1: ページネーション
jobs = BackupJob.query.paginate(page=1, per_page=50)

# 修正2: yield_per でストリーミング
for job in BackupJob.query.yield_per(100):
    process(job)

# 修正3: 必要なカラムのみ取得
jobs = db.session.query(
    BackupJob.id, 
    BackupJob.name
).all()
```

11.4 デプロイ問題
-----------------

【問題: Windowsデプロイでパスエラー】

症状:
```powershell
FileNotFoundError: C:\Backups\data/backup_mgmt.db
```

解決:
```python
# 問題: Linuxパス
DATABASE_PATH = 'data/backup_mgmt.db'

# 修正: pathlib使用
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / 'data' / 'backup_mgmt.db'
```

【問題: NSSM サービスが起動しない】

症状:
```
Service failed to start
Exit code: 1
```

診断:
```powershell
# ログ確認
Get-Content C:\Logs\backup-mgmt-system-stderr.log

# 手動起動テスト
cd C:\backup-management-system
.\venv\Scripts\python.exe run.py
```

解決:
```powershell
# パーミッション確認
icacls C:\backup-management-system

# サービス再設定
nssm remove BackupMgmtSystem confirm
nssm install BackupMgmtSystem "C:\backup-management-system\venv\Scripts\python.exe" "C:\backup-management-system\run.py"
nssm set BackupMgmtSystem AppDirectory "C:\backup-management-system"
nssm start BackupMgmtSystem
```

================================================================================
12. ベストプラクティス
================================================================================

12.1 コーディング規約
---------------------

【Python Style Guide】

PEP 8準拠 + プロジェクト固有ルール:

```python
# ✅ Good

from datetime import datetime
from typing import Dict, List, Optional

class BackupJob(db.Model):
    """
    バックアップジョブモデル
    
    Attributes:
        id: プライマリキー
        name: ジョブ名
        backup_type: バックアップタイプ（full/incremental/differential）
    """
    __tablename__ = 'backup_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    backup_type = db.Column(db.String(50), nullable=False)
    
    def to_dict(self) -> Dict[str, any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'name': self.name,
            'backup_type': self.backup_type
        }
    
    def __repr__(self) -> str:
        return f'<BackupJob {self.name}>'


# ❌ Bad

class backupjob(db.Model):  # クラス名はPascalCase
    id=db.Column(db.Integer,primary_key=True)  # スペース不足
    Name=db.Column(db.String(100))  # カラム名はsnake_case
    
    def toDict(self):  # メソッド名はsnake_case
        return {'id':self.id,'name':self.Name}  # スペース不足
```

【命名規則】

```python
# クラス: PascalCase
class BackupJob:
class ComplianceChecker:

# 関数・メソッド: snake_case
def get_compliance_summary():
def check_backup_copies():

# 変数: snake_case
backup_count = 3
is_compliant = True

# 定数: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_RETENTION_DAYS = 30

# プライベート: 先頭に_
class MyClass:
    def __init__(self):
        self._private_var = 0
    
    def _private_method(self):
        pass
```

【ドキュメンテーション】

```python
def check_job_compliance(job_id: int) -> Dict[str, any]:
    """
    指定されたジョブの3-2-1-1-0コンプライアンスをチェック
    
    Args:
        job_id: チェック対象のジョブID
    
    Returns:
        コンプライアンスチェック結果の辞書:
        {
            'compliant': bool,
            'score': int,
            'details': dict,
            'issues': list
        }
    
    Raises:
        ValueError: job_idが無効な場合
        DatabaseError: データベースアクセスエラー
    
    Examples:
        >>> result = check_job_compliance(123)
        >>> print(result['compliant'])
        True
    """
    # 実装
    pass
```

12.2 テストのベストプラクティス
-------------------------------

【テストカバレッジ目標】

- 全体: 80%以上
- ビジネスロジック: 95%以上
- クリティカル機能: 100%

【テスト構造】

```python
# tests/test_services.py

import pytest
from app.services.compliance_checker import ComplianceChecker
from tests.factories import JobFactory, CopyFactory

class TestComplianceChecker:
    """ComplianceCheckerクラスのテスト"""
    
    @pytest.fixture
    def checker(self):
        """テスト用のComplianceCheckerインスタンス"""
        return ComplianceChecker()
    
    @pytest.fixture
    def compliant_job(self, app):
        """コンプライアント状態のジョブ"""
        with app.app_context():
            job = JobFactory()
            # 3つのコピーを作成
            CopyFactory(job=job, copy_number=1, is_offsite=False, is_offline=False)
            CopyFactory(job=job, copy_number=2, is_offsite=True, is_offline=False)
            CopyFactory(job=job, copy_number=3, is_offsite=False, is_offline=True)
            return job
    
    def test_check_three_copies_pass(self, checker, compliant_job):
        """3つのコピーチェック - 成功ケース"""
        result = checker.check_job_compliance(compliant_job.id)
        assert result['details']['copies']['ok'] is True
        assert result['details']['copies']['count'] == 3
    
    def test_check_three_copies_fail(self, checker, app):
        """3つのコピーチェック - 失敗ケース"""
        with app.app_context():
            job = JobFactory()
            CopyFactory(job=job, copy_number=1)
            CopyFactory(job=job, copy_number=2)
            # 2つのみ
            
            result = checker.check_job_compliance(job.id)
            assert result['details']['copies']['ok'] is False
            assert result['compliant'] is False
    
    @pytest.mark.parametrize("media_types,expected", [
        (['disk', 'tape'], True),
        (['disk', 'cloud'], True),
        (['disk', 'disk'], False),
    ])
    def test_check_media_types(self, checker, app, media_types, expected):
        """異なるメディアタイプチェック - パラメータ化"""
        with app.app_context():
            job = JobFactory()
            for i, media_type in enumerate(media_types, 1):
                CopyFactory(job=job, copy_number=i, media_type=media_type)
            
            result = checker.check_job_compliance(job.id)
            assert result['details']['media']['ok'] is expected
```

【Mockの使用】

```python
from unittest.mock import patch, MagicMock

def test_send_email_notification(app):
    """メール送信のモックテスト"""
    with patch('app.utils.email.send_email') as mock_send:
        mock_send.return_value = True
        
        # テスト対象の関数を実行
        result = notify_compliance_issue(job_id=123)
        
        # send_emailが呼ばれたことを確認
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert 'admin@example.com' in args
        assert 'Compliance Issue' in args
```

12.3 セキュリティベストプラクティス
-----------------------------------

【パスワード管理】

```python
# ✅ Good
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ❌ Bad
class User(db.Model):
    password = db.Column(db.String(100))  # 平文保存は絶対NG!
```

【SQLインジェクション対策】

```python
# ✅ Good: SQLAlchemy ORM使用
jobs = BackupJob.query.filter_by(name=user_input).all()

# ✅ Good: パラメータバインディング
jobs = db.session.execute(
    "SELECT * FROM backup_jobs WHERE name = :name",
    {'name': user_input}
).fetchall()

# ❌ Bad: 文字列連結
query = f"SELECT * FROM backup_jobs WHERE name = '{user_input}'"
jobs = db.session.execute(query).fetchall()  # SQLインジェクション脆弱性!
```

【XSS対策】

```html
<!-- ✅ Good: Jinja2自動エスケープ -->
<div>{{ user.username }}</div>
<div>{{ job.description }}</div>

<!-- ❌ Bad: 手動でエスケープを無効化 -->
<div>{{ user.username | safe }}</div>  <!-- XSS脆弱性! -->
```

【CSRF対策】

```python
# app/__init__.py
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    csrf.init_app(app)
    return app
```

```html
<!-- フォームにCSRFトークン -->
<form method="POST">
    {{ form.csrf_token }}
    <!-- フィールド -->
</form>
```

12.4 パフォーマンス最適化
-------------------------

【データベースクエリ最適化】

```python
# ❌ Bad: N+1クエリ
jobs = BackupJob.query.all()
for job in jobs:
    for copy in job.backup_copies:  # 各ジョブごとにクエリ!
        print(copy.storage_location)

# ✅ Good: Eager Loading
jobs = BackupJob.query.options(
    db.joinedload(BackupJob.backup_copies)
).all()
for job in jobs:
    for copy in job.backup_copies:
        print(copy.storage_location)
```

【キャッシング】

```python
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'simple'})

@app.route('/dashboard')
@cache.cached(timeout=300)  # 5分キャッシュ
def dashboard():
    # 重い処理
    data = get_compliance_summary()
    return render_template('dashboard.html', data=data)
```

【インデックス活用】

```python
class BackupCopy(db.Model):
    __tablename__ = 'backup_copies'
    
    job_id = db.Column(db.Integer, db.ForeignKey('backup_jobs.id'))
    copy_number = db.Column(db.Integer)
    
    # 複合インデックス
    __table_args__ = (
        db.Index('idx_job_copy', 'job_id', 'copy_number'),
    )
```

12.5 Agent協調のベストプラクティス
-----------------------------------

【1. 明確なコミュニケーション】

```markdown
# Good Issue コメント

@agent-3-api

Agent-2 (Database) です。

BackupJobモデルの実装が完了しました。

変更内容:
- app/models.py に BackupJob クラス追加
- 14フィールド定義
- backup_copies リレーションシップ設定

影響:
API実装で以下のフィールドが利用可能です:
- id, name, description, backup_type, source_path...

次のステップ:
REST API エンドポイント実装を開始できます。

PR: #12
Commit: abc123def456
```

【2. 小さく頻繁なコミット】

```bash
# ✅ Good
git commit -m "feat(database): add User model"
git commit -m "feat(database): add BackupJob model"
git commit -m "feat(database): add relationships"
git commit -m "test(database): add model tests"

# ❌ Bad
git commit -m "implement everything"  # 1つの巨大なコミット
```

【3. 早期のフィードバック】

```markdown
# Draft Pull Request を活用

Title: [WIP] [Agent-2] Implement database models

## Status
🚧 Work in Progress - 60% complete

## Completed
- [x] User model
- [x] BackupJob model
- [x] BackupCopy model

## In Progress
- [ ] VerificationTest model
- [ ] Alert model

## Questions
@agent-1-pm
OfflineMediaテーブルの media_id フィールドは
String型でよいでしょうか？それともInteger型？
```

【4. 定期的な同期】

```bash
# 毎日developから変更を取り込む
git checkout feature/my-branch
git fetch origin
git merge origin/develop
git push origin feature/my-branch
```

【5. ドキュメント更新】

```python
# コード変更と同時にドキュメント更新
# app/models.py を変更したら
# docs/database-schema.md も更新

# 例:
# git add app/models.py docs/database-schema.md
# git commit -m "feat(database): add new model and update docs"
```

================================================================================
改訂履歴
================================================================================

版番号  日付         改訂内容                           承認者
------  -----------  ---------------------------------  --------------------
1.0     2025/10/30   初版作成                           [承認者名]


================================================================================
以上
================================================================================
