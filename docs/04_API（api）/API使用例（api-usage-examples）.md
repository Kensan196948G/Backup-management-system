# REST API Usage Examples

バックアップ管理システム REST API の利用例

## Base URL

```
http://localhost:5000/api/v1
```

## 認証

全てのAPIエンドポイントは認証が必要です。以下のいずれかの方法で認証してください：

### 1. セッション認証（Web UIから）
Web UIにログイン後、同じセッションでAPIを呼び出す

### 2. Bearer Token認証（外部アプリケーションから）
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/jobs
```

---

## 1. バックアップジョブ管理 API

### ジョブ一覧取得
```bash
# 基本的な取得
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/jobs

# フィルタリング＆ページネーション
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/jobs?page=1&per_page=20&job_type=database&status=active"

# 検索
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/jobs?search=SQL"
```

### ジョブ詳細取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/jobs/1
```

### ジョブ作成
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "job_name": "Daily SQL Server Backup",
       "job_type": "database",
       "target_server": "SQL-SERVER-01",
       "target_path": "C:\\SQLBackup",
       "backup_tool": "veeam",
       "schedule_type": "daily",
       "retention_days": 30,
       "owner_id": 1,
       "description": "Daily backup of production database"
     }' \
     http://localhost:5000/api/v1/jobs
```

### ジョブ更新
```bash
curl -X PUT \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "retention_days": 60,
       "description": "Updated retention period"
     }' \
     http://localhost:5000/api/v1/jobs/1
```

### ジョブ削除（管理者のみ）
```bash
curl -X DELETE \
     -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/jobs/1
```

### バックアップコピー追加
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "copy_type": "offsite",
       "media_type": "cloud",
       "storage_path": "s3://backup-bucket/sql-backups",
       "is_encrypted": true,
       "is_compressed": true
     }' \
     http://localhost:5000/api/v1/jobs/1/copies
```

---

## 2. バックアップステータス更新 API

### バックアップ実行ステータス更新（PowerShellから）
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "job_id": 1,
       "execution_date": "2025-10-30T03:00:00Z",
       "execution_result": "success",
       "backup_size_bytes": 5368709120,
       "duration_seconds": 300,
       "source_system": "powershell"
     }' \
     http://localhost:5000/api/v1/backup/status
```

### PowerShellスクリプト例
```powershell
$apiUrl = "http://localhost:5000/api/v1/backup/status"
$apiToken = "YOUR_TOKEN"

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

### バックアップコピーステータス更新
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "copy_id": 1,
       "status": "success",
       "last_backup_date": "2025-10-30T03:00:00Z",
       "last_backup_size": 5368709120
     }' \
     http://localhost:5000/api/v1/backup/copy-status
```

### 最終実行情報取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/backup/jobs/1/last-execution
```

---

## 3. アラート管理 API

### アラート一覧取得
```bash
# 未確認アラートのみ
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/alerts?is_acknowledged=false"

# 重大度でフィルタ
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/alerts?severity=critical"

# 特定ジョブのアラート
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/alerts?job_id=1"
```

### アラート詳細取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/alerts/1
```

### アラート確認
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/alerts/1/acknowledge
```

### アラート再オープン
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/alerts/1/unacknowledge
```

### アラートサマリー取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/alerts/summary
```

### 一括確認
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "alert_ids": [1, 2, 3, 4, 5]
     }' \
     http://localhost:5000/api/v1/alerts/bulk-acknowledge
```

---

## 4. レポート生成 API

### レポート一覧取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/reports?report_type=compliance"
```

### レポート詳細取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/reports/1
```

### レポート生成
```bash
# コンプライアンスレポート
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "report_type": "compliance",
       "date_from": "2025-10-01",
       "date_to": "2025-10-30",
       "file_format": "html",
       "options": {
         "include_charts": true,
         "include_details": true
       }
     }' \
     http://localhost:5000/api/v1/reports/generate

# 運用レポート
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "report_type": "operational",
       "date_from": "2025-10-01",
       "date_to": "2025-10-30",
       "file_format": "pdf"
     }' \
     http://localhost:5000/api/v1/reports/generate
```

### レポートダウンロード
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -o report.html \
     http://localhost:5000/api/v1/reports/1/download
```

### レポート種類一覧
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/reports/types
```

---

## 5. ダッシュボード API

### ダッシュボードサマリー取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/dashboard/summary
```

レスポンス例：
```json
{
  "jobs": {
    "total": 50,
    "active": 48,
    "inactive": 2
  },
  "compliance": {
    "compliant": 45,
    "non_compliant": 3,
    "warning": 2
  },
  "executions_24h": {
    "total": 120,
    "success": 115,
    "failed": 3,
    "warning": 2
  },
  "alerts": {
    "critical": 2,
    "error": 5,
    "warning": 10,
    "total_unacknowledged": 17
  }
}
```

### 最近の実行履歴
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/dashboard/recent-executions
```

### 最近のアラート
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/dashboard/recent-alerts
```

### コンプライアンス傾向
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/dashboard/compliance-trend
```

### 実行統計（7日間）
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/dashboard/execution-statistics
```

### ストレージ使用状況
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/dashboard/storage-usage
```

---

## 6. オフラインメディア管理 API

### メディア一覧取得
```bash
# 全メディア
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/media

# タイプでフィルタ
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/media?media_type=tape"

# ステータスでフィルタ
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/media?current_status=stored"
```

### メディア詳細取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/media/1
```

### メディア登録
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "media_id": "TAPE-001",
       "media_type": "tape",
       "capacity_gb": 1000,
       "purchase_date": "2025-10-01",
       "storage_location": "Fireproof Safe A",
       "current_status": "stored",
       "notes": "LTO-7 tape"
     }' \
     http://localhost:5000/api/v1/media
```

### メディア更新
```bash
curl -X PUT \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "storage_location": "Offsite Vault B",
       "current_status": "stored"
     }' \
     http://localhost:5000/api/v1/media/1
```

### メディア貸出
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "borrower_id": 2,
       "borrow_purpose": "Restore test",
       "expected_return": "2025-11-10"
     }' \
     http://localhost:5000/api/v1/media/1/borrow
```

### メディア返却
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "return_condition": "normal",
       "notes": "Returned in good condition"
     }' \
     http://localhost:5000/api/v1/media/1/return
```

---

## 7. 検証テスト管理 API

### 検証テスト一覧取得
```bash
# 全テスト
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/verification/tests

# 特定ジョブのテスト
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/verification/tests?job_id=1"

# 結果でフィルタ
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/verification/tests?test_result=failed"
```

### 検証テスト詳細取得
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/verification/tests/1
```

### 検証テスト記録
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "job_id": 1,
       "test_type": "full_restore",
       "test_result": "success",
       "restore_target": "TEST-SERVER-01",
       "duration_seconds": 1800,
       "notes": "Successful restore test"
     }' \
     http://localhost:5000/api/v1/verification/tests
```

### 検証スケジュール一覧取得
```bash
# 全スケジュール
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/v1/verification/schedules

# 期限切れのみ
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/v1/verification/schedules?overdue=true"
```

### 検証スケジュール作成
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "job_id": 1,
       "test_frequency": "quarterly",
       "next_test_date": "2025-12-01",
       "assigned_to": 2
     }' \
     http://localhost:5000/api/v1/verification/schedules
```

### 検証スケジュール更新
```bash
curl -X PUT \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "next_test_date": "2025-12-15",
       "assigned_to": 3
     }' \
     http://localhost:5000/api/v1/verification/schedules/1
```

---

## エラーレスポンス

全てのエラーは統一されたフォーマットで返されます：

### 400 Bad Request（不正なリクエスト）
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "fields": {
        "job_name": "job_name is required",
        "retention_days": "Must be at least 1 day"
      }
    }
  }
}
```

### 401 Unauthorized（認証エラー）
```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication required"
  }
}
```

### 403 Forbidden（権限エラー）
```json
{
  "error": {
    "code": "AUTHORIZATION_FAILED",
    "message": "Insufficient permissions"
  }
}
```

### 404 Not Found（リソースが見つからない）
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource not found"
  }
}
```

### 409 Conflict（リソースの競合）
```json
{
  "error": {
    "code": "MEDIA_ALREADY_BORROWED",
    "message": "Media is already borrowed"
  }
}
```

### 500 Internal Server Error（サーバーエラー）
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Internal server error"
  }
}
```

---

## レート制限

現在、レート制限は実装されていませんが、将来的に以下を実装予定：

- 1時間あたり1000リクエスト（認証済みユーザー）
- 1時間あたり100リクエスト（未認証）

レート制限に達した場合は HTTP 429 Too Many Requests が返されます。

---

## ページネーション

リスト取得APIは全てページネーションをサポートしています：

### パラメータ
- `page`: ページ番号（デフォルト: 1）
- `per_page`: 1ページあたりのアイテム数（デフォルト: 20、最大: 100）

### レスポンス例
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## 推奨事項

1. **エラーハンドリング**: 全てのAPIコールでエラーハンドリングを実装してください
2. **リトライ**: 500エラーの場合は指数バックオフでリトライしてください
3. **タイムアウト**: 長時間実行される可能性のある操作（レポート生成など）には適切なタイムアウトを設定してください
4. **ロギング**: APIコールとレスポンスをログに記録してください
5. **セキュリティ**: トークンは安全に保管し、HTTPSを使用してください

---

## サポート

API に関する質問や問題がある場合は、システム管理者にお問い合わせください。
