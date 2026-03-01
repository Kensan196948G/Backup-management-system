# API 仕様書

**プロジェクト名:** バックアップ管理システム WebUI
**バージョン:** 1.0.0
**作成日:** 2026-02-25
**ベース URL:** `https://backup-mgmt.example.com/api/v1`

---

## 1. 概要

### 1.1 共通仕様

- **プロトコル:** HTTPS（TLS 1.2 以上）
- **フォーマット:** JSON（`Content-Type: application/json`）
- **文字コード:** UTF-8
- **認証:** JWT Bearer Token

### 1.2 共通リクエストヘッダー

| ヘッダー | 必須 | 説明 |
|---------|------|------|
| `Authorization` | 必須（認証済み） | `Bearer {access_token}` |
| `Content-Type` | POST/PUT/PATCH 時 | `application/json` |
| `Accept-Language` | 任意 | `ja` / `en`（エラーメッセージ言語） |
| `X-Request-ID` | 任意 | リクエスト追跡 ID |

### 1.3 共通レスポンス形式

**成功:**
```json
{
  "data": {...},
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-02-25T09:00:00Z"
  }
}
```

**リスト:**
```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 25,
    "total_pages": 4
  }
}
```

**エラー:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力値が不正です",
    "details": [
      {
        "field": "name",
        "message": "ジョブ名は必須です"
      }
    ]
  }
}
```

### 1.4 HTTP ステータスコード

| コード | 用途 |
|--------|------|
| 200 | 成功（GET / PUT / PATCH） |
| 201 | 作成成功（POST） |
| 204 | 成功（削除・中身なし） |
| 400 | バリデーションエラー |
| 401 | 未認証 |
| 403 | 権限不足 |
| 404 | リソース不存在 |
| 409 | 競合（重複など） |
| 422 | 処理不能エンティティ |
| 429 | レートリミット超過 |
| 500 | サーバー内部エラー |

---

## 2. 認証 API

### POST /auth/login

ログイン・JWT トークン発行。

**リクエスト:**
```json
{
  "email": "admin@example.com",
  "password": "P@ssw0rd",
  "remember_me": false
}
```

**レスポンス 200:**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "email": "admin@example.com",
      "display_name": "管理者",
      "role": "admin"
    }
  }
}
```

**レスポンス 401:**
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "メールアドレスまたはパスワードが正しくありません"
  }
}
```

---

### POST /auth/refresh

アクセストークンをリフレッシュ。

**リクエスト:** Refresh Token は HttpOnly Cookie から自動送信

**レスポンス 200:**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 900
  }
}
```

---

### POST /auth/logout

ログアウト・リフレッシュトークン無効化。

**レスポンス:** `204 No Content`

---

## 3. ジョブ管理 API

### GET /jobs

ジョブ一覧取得。

**クエリパラメータ:**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `page` | integer | ページ番号（デフォルト: 1） |
| `per_page` | integer | 件数（デフォルト: 25、最大: 100） |
| `sort` | string | ソートフィールド（例: `name`, `-last_run`） |
| `status` | string | フィルタ（`success,error,running`） |
| `q` | string | 名前の部分一致検索 |
| `from` | datetime | 最終実行日時フィルタ（開始） |
| `to` | datetime | 最終実行日時フィルタ（終了） |

**レスポンス 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "日次フルバックアップ",
      "type": "full",
      "status": "success",
      "enabled": true,
      "last_run_at": "2026-02-25T23:00:00Z",
      "last_run_duration_seconds": 1800,
      "last_run_size_bytes": 10737418240,
      "next_run_at": "2026-02-26T23:00:00Z",
      "compliance_32110": {
        "is_compliant": true,
        "copies_count": 3,
        "media_types_count": 2,
        "offsite_ok": true,
        "immutable_ok": true,
        "last_verification_status": "success",
        "last_verification_at": "2026-02-25T23:40:00Z"
      },
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "pagination": {...}
}
```

---

### POST /jobs

ジョブ新規作成。

**リクエスト:**
```json
{
  "name": "週次増分バックアップ",
  "type": "incremental",
  "description": "毎週日曜の増分バックアップ",
  "source": {
    "type": "directory",
    "paths": ["D:\\Data"],
    "excludes": ["*.tmp", "*.log"]
  },
  "destination": {
    "storage_pool_id": "uuid",
    "retention_days": 30,
    "retention_count": 10,
    "encryption": true
  },
  "schedule": {
    "type": "cron",
    "expression": "0 2 * * 0",
    "timezone": "Asia/Tokyo"
  },
  "notifications": {
    "on_success": false,
    "on_failure": true,
    "channels": ["email"],
    "recipients": ["admin@example.com"]
  },
  "compliance_32110_policy": {
    "required_copies": 3,
    "required_media_types": 2,
    "require_offsite": true,
    "require_immutable": true,
    "require_zero_verification_errors": true,
    "verification_window_hours": 24
  }
}
```

**レスポンス 201:**
```json
{
  "data": {
    "id": "uuid",
    "name": "週次増分バックアップ",
    ...
  }
}
```

---

### GET /jobs/{job_id}

ジョブ詳細取得。

**パスパラメータ:** `job_id` (UUID)

**レスポンス 200:** ジョブオブジェクト（詳細版）

---

### PUT /jobs/{job_id}

ジョブ更新（全フィールド置換）。

---

### PATCH /jobs/{job_id}

ジョブ部分更新。

**リクエスト例（有効化/無効化）:**
```json
{
  "enabled": false
}
```

---

### DELETE /jobs/{job_id}

ジョブ削除。

**レスポンス:** `204 No Content`

---

### POST /jobs/{job_id}/run

ジョブの即時実行。

**レスポンス 202:**
```json
{
  "data": {
    "execution_id": "uuid",
    "job_id": "uuid",
    "status": "running",
    "started_at": "2026-02-25T09:00:00Z"
  }
}
```

---

## 4. ジョブ実行履歴 API

### GET /jobs/{job_id}/executions

ジョブの実行履歴一覧。

**クエリパラメータ:** `page`, `per_page`, `status`, `from`, `to`

---

### GET /jobs/{job_id}/executions/{execution_id}/logs

実行ログの取得。

**クエリパラメータ:**
- `tail`: integer（末尾 N 行、デフォルト: 100）
- `stream`: boolean（WebSocket ストリーミング）

---

## 5. ダッシュボード API

### GET /dashboard/summary

ダッシュボードサマリー取得。

**クエリパラメータ:** `period` (`24h` / `7d` / `30d`)

**レスポンス 200:**
```json
{
  "data": {
    "success_count": 24,
    "error_count": 2,
    "running_count": 1,
    "storage_used_bytes": 107374182400,
    "storage_total_bytes": 214748364800,
    "success_rate_percent": 92.3,
    "period": "24h",
    "compliance_32110": {
      "total_jobs": 6,
      "compliant_jobs": 3,
      "non_compliant_jobs": 3,
      "overall_status": "warning",
      "checks": {
        "copies_3": { "passed": 4, "total": 6 },
        "media_2": { "passed": 4, "total": 6 },
        "offsite_1": { "passed": 4, "total": 6 },
        "immutable_1": { "passed": 3, "total": 6 },
        "verify_0": { "passed": 3, "total": 6 }
      }
    }
  }
}
```

---

### GET /compliance/32110/summary

3-2-1-1-0 準拠状況サマリーを取得。

**クエリパラメータ:**
- `scope`: `all` / `enabled_jobs`（デフォルト: `enabled_jobs`）
- `period`: `24h` / `7d` / `30d`

**レスポンス 200:**
```json
{
  "data": {
    "overall_status": "warning",
    "evaluated_at": "2026-02-25T09:30:00Z",
    "summary": {
      "jobs_total": 6,
      "jobs_compliant": 3,
      "jobs_non_compliant": 3
    },
    "checks": {
      "copies_3": { "passed": 4, "total": 6, "required": 3 },
      "media_2": { "passed": 4, "total": 6, "required": 2 },
      "offsite_1": { "passed": 4, "total": 6, "required": true },
      "immutable_1": { "passed": 3, "total": 6, "required": true },
      "verify_0": { "passed": 3, "total": 6, "required": "success" }
    }
  }
}
```

---

### GET /jobs/{job_id}/compliance/32110

ジョブ単位の 3-2-1-1-0 判定と証跡を取得。

**レスポンス 200:**
```json
{
  "data": {
    "job_id": "uuid",
    "is_compliant": false,
    "checks": {
      "copies_3": false,
      "media_2": false,
      "offsite_1": false,
      "immutable_1": false,
      "verify_0": false
    },
    "evidence": [
      {
        "type": "verification",
        "status": "error",
        "captured_at": "2026-02-25T08:20:00Z",
        "details": {
          "execution_id": "uuid",
          "message": "復元検証に失敗"
        }
      }
    ]
  }
}
```

---

### GET /reports/compliance/32110

3-2-1-1-0 準拠レポート一覧を取得。

**クエリパラメータ:** `page`, `per_page`, `from`, `to`, `format`

---

## 6. レート制限

| エンドポイント | 制限 | ウィンドウ |
|--------------|------|----------|
| POST /auth/login | 10 回 | 15 分 |
| 全 GET | 300 回 | 1 分 |
| 全 POST/PUT/DELETE | 60 回 | 1 分 |

**レスポンスヘッダー:**
- `X-RateLimit-Limit`: 制限値
- `X-RateLimit-Remaining`: 残り回数
- `X-RateLimit-Reset`: リセット時刻（Unix timestamp）

---

## 更新履歴

| 日付 | バージョン | 更新者 | 内容 |
|------|-----------|--------|------|
| 2026-02-25 | 1.0.0 | システム管理者 | 初版作成 |
