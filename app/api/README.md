# REST API Implementation

バックアップ管理システム REST API モジュール

## 概要

このモジュールは、バックアップ管理システムのRESTful APIを提供します。
外部システム（PowerShellスクリプト等）からバックアップステータスを更新したり、
Web UIからダッシュボード情報を取得するために使用されます。

## ディレクトリ構成

```
app/api/
├── __init__.py           # Blueprint定義
├── errors.py             # エラーハンドリング
├── validators.py         # 入力値検証
├── helpers.py            # ヘルパー関数
├── backup.py             # バックアップステータス更新API
├── jobs.py               # ジョブ管理API
├── alerts.py             # アラート管理API
├── reports.py            # レポート生成API
├── dashboard.py          # ダッシュボードAPI
├── media.py              # オフラインメディア管理API
├── verification.py       # 検証テスト管理API
└── README.md             # このファイル
```

## エンドポイント一覧

### Base URL
```
http://localhost:5000/api/v1
```

### 認証
全てのエンドポイントは認証が必要です：
- Bearer Token認証: `Authorization: Bearer {token}`
- セッション認証: Web UIからのログイン

### エンドポイント

#### 1. バックアップステータス更新
- `POST /backup/status` - バックアップ実行結果記録
- `POST /backup/copy-status` - コピーステータス更新
- `GET /backup/jobs/{job_id}/last-execution` - 最終実行情報

#### 2. ジョブ管理
- `GET /jobs` - ジョブ一覧
- `GET /jobs/{job_id}` - ジョブ詳細
- `POST /jobs` - ジョブ作成
- `PUT /jobs/{job_id}` - ジョブ更新
- `DELETE /jobs/{job_id}` - ジョブ削除
- `POST /jobs/{job_id}/copies` - コピー追加

#### 3. アラート管理
- `GET /alerts` - アラート一覧
- `GET /alerts/{alert_id}` - アラート詳細
- `POST /alerts/{alert_id}/acknowledge` - アラート確認
- `POST /alerts/{alert_id}/unacknowledge` - 再オープン
- `GET /alerts/summary` - アラートサマリー
- `POST /alerts/bulk-acknowledge` - 一括確認

#### 4. レポート生成
- `GET /reports` - レポート一覧
- `GET /reports/{report_id}` - レポート詳細
- `GET /reports/{report_id}/download` - ダウンロード
- `POST /reports/generate` - レポート生成
- `DELETE /reports/{report_id}` - レポート削除
- `GET /reports/types` - レポート種類一覧

#### 5. ダッシュボード
- `GET /dashboard/summary` - 全体サマリー
- `GET /dashboard/recent-executions` - 最近の実行
- `GET /dashboard/recent-alerts` - 最近のアラート
- `GET /dashboard/compliance-trend` - コンプライアンス推移
- `GET /dashboard/execution-statistics` - 実行統計
- `GET /dashboard/storage-usage` - ストレージ使用状況

#### 6. オフラインメディア管理
- `GET /media` - メディア一覧
- `GET /media/{media_id}` - メディア詳細
- `POST /media` - メディア登録
- `PUT /media/{media_id}` - メディア更新
- `DELETE /media/{media_id}` - メディア削除
- `POST /media/{media_id}/borrow` - メディア貸出
- `POST /media/{media_id}/return` - メディア返却

#### 7. 検証テスト管理
- `GET /verification/tests` - テスト一覧
- `GET /verification/tests/{test_id}` - テスト詳細
- `POST /verification/tests` - テスト記録
- `PUT /verification/tests/{test_id}` - テスト更新
- `GET /verification/schedules` - スケジュール一覧
- `POST /verification/schedules` - スケジュール作成
- `PUT /verification/schedules/{schedule_id}` - スケジュール更新
- `DELETE /verification/schedules/{schedule_id}` - スケジュール削除

## 使用例

### PowerShellからバックアップステータス更新

```powershell
$apiUrl = "http://localhost:5000/api/v1/backup/status"
$apiToken = "YOUR_API_TOKEN"

$backupResult = @{
    job_id = 1
    execution_date = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    execution_result = "success"
    backup_size_bytes = 5368709120
    duration_seconds = 300
    source_system = "powershell"
} | ConvertTo-Json

Invoke-RestMethod -Uri $apiUrl -Method Post `
    -Headers @{Authorization="Bearer $apiToken"} `
    -ContentType "application/json" `
    -Body $backupResult
```

### curlでジョブ一覧取得

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/jobs?page=1&per_page=20"
```

## レスポンス形式

### 成功レスポンス
```json
{
  "message": "Success message",
  "data": {...}
}
```

### エラーレスポンス
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {...}
  }
}
```

### ページネーション
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

## エラーコード

- `AUTHENTICATION_REQUIRED` - 認証が必要
- `AUTHORIZATION_FAILED` - 権限不足
- `VALIDATION_ERROR` - 入力値エラー
- `RESOURCE_NOT_FOUND` - リソースが見つからない
- `RESOURCE_CONFLICT` - リソースの競合
- `INTERNAL_ERROR` - サーバーエラー

## 開発

### モジュールのインポート

```python
from app.api import api_bp

# Flaskアプリケーションに登録
app.register_blueprint(api_bp)
```

### 新しいエンドポイントの追加

1. 適切なモジュールファイルを編集（例: `jobs.py`）
2. デコレーターを使用してエンドポイントを定義
3. 入力値検証を実装
4. エラーハンドリングを実装
5. ドキュメントを更新

例：
```python
@api_bp.route('/resource', methods=['GET'])
@api_token_required
def list_resource():
    """Resource list endpoint"""
    try:
        # Implementation
        return jsonify({'items': []}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return error_response(500, 'Failed', 'ERROR_CODE')
```

## テスト

```bash
# 単体テスト実行
pytest tests/test_api.py

# カバレッジ確認
pytest --cov=app/api tests/
```

## ドキュメント

詳細なドキュメントは以下を参照：
- [API Usage Examples](../../docs/API_USAGE_EXAMPLES.md)
- [API Implementation Summary](../../docs/API_IMPLEMENTATION_SUMMARY.md)
- [REST API Checklist](../../docs/REST_API_CHECKLIST.md)

## ライセンス

社内システム - 非公開

## 作成者

API Development Team (devapi)

## 更新履歴

- 2025-10-30: 初版作成（v1.0.0）
