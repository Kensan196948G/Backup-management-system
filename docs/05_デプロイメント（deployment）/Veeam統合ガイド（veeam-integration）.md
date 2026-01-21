# Veeam統合ガイド

バックアップ管理システムとVeeam Backup & Replicationの統合方法を詳しく説明します。

## 目次

1. [前提条件](#前提条件)
2. [APIトークン取得](#apiトークン取得)
3. [バックアップ管理システムの設定](#バックアップ管理システムの設定)
4. [Veeamコンソールでのジョブ設定](#veeamコンソールでのジョブ設定)
5. [ポストジョブスクリプト設定](#ポストジョブスクリプト設定)
6. [テスト実行](#テスト実行)
7. [トラブルシューティング](#トラブルシューティング)
8. [APIリファレンス](#apiリファレンス)

---

## 前提条件

### 必須要件

- [ ] Veeam Backup & Replication 12.0以上がインストール済み
- [ ] バックアップ管理システムがインストール済み
- [ ] Veeamコンソールへのアクセス権（管理者）
- [ ] Veeamサーバーのホスト名またはIPアドレス
- [ ] Veeamサーバーのポート番号（デフォルト: 9398）
- [ ] ネットワーク接続確認（Veeam ← → バックアップ管理システム）

### ネットワーク要件

```bash
# Veeamサーバーへの接続テスト
nc -zv veeam-server 9398

# または
curl -I http://veeam-server:9398/api/about
```

---

## APIトークン取得

### ステップ1: Veeamコンソールにログイン

1. **Veeam Backup & Replication コンソールを起動**
   - Windowsスタートメニュー → "Veeam Backup & Replication"

2. **コンソール画面例**
   
   ```
   スクリーンショット: Veeam Backup & Replicationコンソール
   (実装: Veeamコンソール接続画面のプレースホルダー)
   ```

### ステップ2: API認証の有効化

#### 方法A: Veeamコンソールから（推奨）

1. **メニュー → 設定 → 全般設定を開く**

   ```
   Veeamコンソール → ハンバーガーメニュー(三本線)
   ↓
   設定
   ↓
   全般設定
   ```

2. **"REST API"セクションを見つける**

   ```
   画面: Veeam 設定パネル
   [全般設定]
   ├─ REST API
   │  └─ REST APIの有効化: ☑ 有効
   │
   └─ ポート設定
      └─ APIポート: 9398 (デフォルト)
   ```

3. **"REST APIの有効化"にチェック**
   - ポートを確認（デフォルト: 9398）
   - 必要に応じて変更

4. **"適用"をクリック**

#### 方法B: PowerShellから

```powershell
# Veeam Backup PowerShell Snapin をロード
Add-PSSnapin VeeamPSSnapin

# REST API有効化
Get-VBRRESTAPIOptions | Set-VBRRESTAPIOptions -Enabled:$true

# 状態確認
Get-VBRRESTAPIOptions | Select-Object -Property Enabled, Port
```

### ステップ3: アクセストークンの生成

#### REST API を使用したトークン取得

```bash
#!/bin/bash

# 変数設定
VEEAM_SERVER="192.168.1.100"
VEEAM_PORT="9398"
VEEAM_USERNAME="administrator@veeam.local"
VEEAM_PASSWORD="YourPassword123"

# Base64でエンコード
CREDENTIALS=$(echo -n "$VEEAM_USERNAME:$VEEAM_PASSWORD" | base64)

# トークン取得
curl -X POST \
  -H "Authorization: Basic $CREDENTIALS" \
  -H "Content-Type: application/json" \
  "http://$VEEAM_SERVER:$VEEAM_PORT/api/sessionMgr/?v=1.4" \
  -d '{
    "User":"'"$VEEAM_USERNAME"'",
    "Password":"'"$VEEAM_PASSWORD"'"
  }' \
  -c cookies.txt \
  -v

# 応答例
# HTTP/1.1 200 OK
# Set-Cookie: X-RestSvcSessionId=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**トークンの保存**

```bash
# クッキーから X-RestSvcSessionId を抽出
SESSION_ID=$(grep X-RestSvcSessionId cookies.txt | awk '{print $NF}')
echo $SESSION_ID

# または、レスポンスヘッダーから直接取得
# Set-Cookie: X-RestSvcSessionId=...
```

#### 永続的なAPIトークンの生成（推奨）

1. **Veeamコンソール → 設定 → ユーザー管理を開く**

2. **新しいAPI用のユーザーを作成**
   - ユーザー名: `api-backup-mgmt`
   - ロール: `Backup Operator` または `Restore Operator`
   - パスワード: 強力なパスワード（最小12文字）

3. **該当するロールの権限を確認**

   ```
   画面: ユーザーロール管理
   ┌────────────────────────────────┐
   │ Backup Operator ロール          │
   ├────────────────────────────────┤
   │ ☑ バックアップジョブの実行     │
   │ ☑ ジョブの構成                │
   │ ☑ レポート表示                │
   │ ☐ ユーザー管理                │
   │ ☐ 管理者設定                  │
   └────────────────────────────────┘
   ```

---

## バックアップ管理システムの設定

### ステップ1: 環境変数の設定

**ファイル: `.env`**

```ini
# Veeam連携設定
VEEAM_ENABLED=true

# Veeamサーバー情報
VEEAM_API_URL=http://192.168.1.100:9398
VEEAM_USERNAME=api-backup-mgmt
VEEAM_PASSWORD=YourPassword123

# Veeamセッション設定
VEEAM_SESSION_TIMEOUT=3600
VEEAM_RETRY_COUNT=3
VEEAM_RETRY_DELAY=5

# APIバージョン（Veeamバージョンに合わせて調整）
VEEAM_API_VERSION=1.4

# ポーリング設定（バックアップ進行状況確認）
VEEAM_POLLING_INTERVAL=30
VEEAM_POLLING_TIMEOUT=3600

# SSL/TLS設定（自己署名証明書の場合）
VEEAM_VERIFY_SSL=false
# 本番環境では true に設定
```

### ステップ2: VeeamService の設定

**ファイル: `app/services/veeam_service.py`**

```python
import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

class VeeamService:
    def __init__(self):
        self.base_url = os.getenv('VEEAM_API_URL')
        self.username = os.getenv('VEEAM_USERNAME')
        self.password = os.getenv('VEEAM_PASSWORD')
        self.api_version = os.getenv('VEEAM_API_VERSION', '1.4')
        self.session_id = None
        self.session_expiry = None
        self.verify_ssl = os.getenv('VEEAM_VERIFY_SSL', 'false').lower() == 'true'
    
    def authenticate(self):
        """Veeamサーバーに認証してセッションIDを取得"""
        url = f"{self.base_url}/api/sessionMgr/?v={self.api_version}"
        
        try:
            response = requests.post(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                verify=self.verify_ssl,
                timeout=10
            )
            response.raise_for_status()
            
            # レスポンスヘッダーからセッションIDを抽出
            cookies = response.cookies.get_dict()
            self.session_id = cookies.get('X-RestSvcSessionId')
            
            # セッション有効期限を設定（1時間）
            self.session_expiry = datetime.now() + timedelta(hours=1)
            
            return True
        except requests.exceptions.RequestException as e:
            print(f"Veeam認証失敗: {e}")
            return False
    
    def get_headers(self):
        """APIリクエスト用のヘッダーを生成"""
        return {
            'X-RestSvcSessionId': self.session_id,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_jobs(self):
        """バックアップジョブの一覧を取得"""
        if not self._is_session_valid():
            self.authenticate()
        
        url = f"{self.base_url}/api/jobs?v={self.api_version}"
        
        try:
            response = requests.get(
                url,
                headers=self.get_headers(),
                verify=self.verify_ssl,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"ジョブ取得失敗: {e}")
            return None
    
    def _is_session_valid(self):
        """セッションが有効か確認"""
        if not self.session_id or not self.session_expiry:
            return False
        return datetime.now() < self.session_expiry
```

### ステップ3: テスト接続

```bash
# 仮想環境を有効化
source /opt/backup-management-system/venv/bin/activate

# Python シェルで接続テスト
python3 << EOF
import os
from app import create_app
from app.services.veeam_service import VeeamService

app = create_app()
with app.app_context():
    veeam = VeeamService()
    
    # 認証テスト
    if veeam.authenticate():
        print("✓ Veeam認証成功")
        
        # ジョブ取得テスト
        jobs = veeam.get_jobs()
        if jobs:
            print(f"✓ ジョブ取得成功: {len(jobs['Jobs'])}個のジョブを取得")
        else:
            print("✗ ジョブ取得失敗")
    else:
        print("✗ Veeam認証失敗")
EOF
```

---

## Veeamコンソールでのジョブ設定

### ステップ1: バックアップジョブの確認

1. **Veeamコンソール → バックアップジョブを開く**

   ```
   画面: Veeamコンソール - バックアップジョブ一覧
   [ホーム] > [バックアップジョブ]
   
   ┌─────────────────────────────────┐
   │ バックアップジョブ              │
   ├─────────────────────────────────┤
   │ □ VM Backup Job 1               │
   │ □ VM Backup Job 2               │
   │ □ Physical Server Backup        │
   │ □ File Server Backup            │
   └─────────────────────────────────┘
   ```

2. **統合対象のジョブを選択**
   - ジョブを右クリック → "プロパティ"

3. **詳細な設定確認**

   ```
   画面: バックアップジョブプロパティ
   ┌──────────────────────────────────┐
   │ [全般] [バックアップ] [詳細設定] │
   ├──────────────────────────────────┤
   │ ジョブ名: VM Backup Job 1        │
   │ ID: 12345678-1234-1234-1234...   │
   │ 説明: 月次 VM バックアップ       │
   │                                  │
   │ ジョブの有効化: ☑ 有効           │
   │ スケジュール: 毎日 22:00         │
   └──────────────────────────────────┘
   ```

### ステップ2: ジョブIDの確認

**Veeam REST APIでジョブ情報を取得**

```bash
# セッションIDを取得（前述のステップで取得）
SESSION_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
VEEAM_SERVER="192.168.1.100"

# ジョブ情報を取得
curl -H "X-RestSvcSessionId: $SESSION_ID" \
  "http://$VEEAM_SERVER:9398/api/jobs?v=1.4" | jq .

# 応答例（JSON形式）
{
  "Jobs": [
    {
      "UID": "12345678-1234-1234-1234-123456789012",
      "Name": "VM Backup Job 1",
      "Type": "Backup",
      "JobType": "Backup",
      "IsScheduleEnabled": true,
      "ScheduleOptions": {
        "OptionPeriod": "Daily",
        "OptionTime": "22:00"
      }
    }
  ]
}
```

ジョブIDを記録しておきます:
```
ジョブ名: VM Backup Job 1
Job UID: 12345678-1234-1234-1234-123456789012
```

---

## ポストジョブスクリプト設定

### ステップ1: スクリプトの作成

#### Windows 環境用スクリプト

**ファイル: `C:\scripts\backup-notification.ps1`**

```powershell
# Veeam バックアップジョブ完了後通知スクリプト
# Veeam Backup コンソール → ジョブプロパティ → 詳細設定 → ポストジョブスクリプト

param(
    [string]$jobName = $env:JOB_NAME,
    [string]$jobId = $env:JOB_ID,
    [string]$status = $env:JOB_STATUS,
    [string]$backupSize = $env:BACKUP_SIZE,
    [string]$duration = $env:JOB_DURATION
)

# 設定
$backupMgmtUrl = "http://backup-mgmt-system:5000"
$apiEndpoint = "$backupMgmtUrl/api/veeam/job-complete"
$logFile = "C:\logs\veeam-notifications.log"

# ログ関数
function Write-Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp - $message"
    Add-Content -Path $logFile -Value $logMessage
    Write-Host $logMessage
}

# メイン処理
try {
    Write-Log "ジョブ完了通知を開始: $jobName"
    
    # リクエストボディを作成
    $payload = @{
        jobName = $jobName
        jobId = $jobId
        status = $status
        backupSize = $backupSize
        duration = $duration
        timestamp = (Get-Date -AsUTC).ToString('o')
    } | ConvertTo-Json
    
    Write-Log "ペイロード: $payload"
    
    # バックアップ管理システムに通知
    $response = Invoke-WebRequest `
        -Uri $apiEndpoint `
        -Method POST `
        -ContentType "application/json" `
        -Body $payload `
        -UseBasicParsing `
        -TimeoutSec 30
    
    Write-Log "通知完了: HTTP $($response.StatusCode)"
    
} catch {
    Write-Log "エラー: $_"
    exit 1
}

exit 0
```

#### Linux 環境用スクリプト

**ファイル: `/usr/local/bin/backup-notification.sh`**

```bash
#!/bin/bash

# Veeam バックアップジョブ完了後通知スクリプト

# 設定
BACKUP_MGMT_URL="http://backup-mgmt-system:5000"
API_ENDPOINT="$BACKUP_MGMT_URL/api/veeam/job-complete"
LOG_FILE="/var/log/veeam-notifications.log"

# ジョブ情報（Veeamから環境変数として渡される）
JOB_NAME="${1:-$JOB_NAME}"
JOB_ID="${2:-$JOB_ID}"
JOB_STATUS="${3:-$JOB_STATUS}"
BACKUP_SIZE="${4:-$BACKUP_SIZE}"
JOB_DURATION="${5:-$JOB_DURATION}"

# ログ関数
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "ジョブ完了通知を開始: $JOB_NAME"

# ペイロードを作成
PAYLOAD=$(cat <<EOF
{
    "jobName": "$JOB_NAME",
    "jobId": "$JOB_ID",
    "status": "$JOB_STATUS",
    "backupSize": "$BACKUP_SIZE",
    "duration": "$JOB_DURATION",
    "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
}
EOF
)

log_message "ペイロード: $PAYLOAD"

# バックアップ管理システムに通知
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "$API_ENDPOINT" \
    --connect-timeout 10 \
    --max-time 30)

if [ "$HTTP_CODE" -eq 200 ]; then
    log_message "通知完了: HTTP $HTTP_CODE"
    exit 0
else
    log_message "エラー: HTTP $HTTP_CODE"
    exit 1
fi
```

**実行権限の設定:**

```bash
chmod +x /usr/local/bin/backup-notification.sh
```

### ステップ2: Veeamコンソールでスクリプトを登録

#### Windows環境

1. **Veeamコンソール → バックアップジョブを右クリック → プロパティ**

2. **詳細設定タブを開く**

   ```
   画面: バックアップジョブプロパティ - 詳細設定
   ┌─────────────────────────────────────────┐
   │ 詳細設定                                │
   ├─────────────────────────────────────────┤
   │                                         │
   │ [プリスクリプト]  [ポストスクリプト]    │
   │                                         │
   │ ☐ ポストジョブスクリプトを実行         │
   │                                         │
   │ スクリプトファイルパス:                │
   │ C:\scripts\backup-notification.ps1     │
   │                                         │
   │ スクリプト引数:                        │
   │ -jobName $([VBR.Job]::Name) \          │
   │ -status $([VBR.Job]::Status) \         │
   │ -jobId $([VBR.Job]::JobID)             │
   │                                         │
   │ [テスト実行]                           │
   │                                         │
   └─────────────────────────────────────────┘
   ```

3. **設定内容**
   - ☑ "ポストジョブスクリプトを実行"
   - パス: `C:\scripts\backup-notification.ps1`
   - 実行ユーザー: Veeamサービスユーザー（通常 NT AUTHORITY\SYSTEM）

4. **[テスト実行]をクリックして動作確認**

#### Linux環境（Veeam Backup Agent for Linux）

1. **Veeamコンソール → バックアップジョブプロパティ**

2. **スクリプトパス設定**
   - ポストスクリプト: `/usr/local/bin/backup-notification.sh`
   - 引数: `"$jobname" "$jobid" "$jobstatus" "$backupsize" "$jobduration"`

3. **Veeamエージェントが実行権限を持つか確認**

   ```bash
   # Veeamエージェント用ユーザー確認
   getent passwd | grep veeam
   
   # スクリプト権限確認
   ls -la /usr/local/bin/backup-notification.sh
   
   # 実行権限がなければ付与
   sudo chmod +x /usr/local/bin/backup-notification.sh
   ```

### ステップ3: API エンドポイントの実装

**ファイル: `app/routes/veeam_routes.py`**

```python
from flask import Blueprint, request, jsonify
from app import db
from app.models import BackupHistory
from app.services.notification_service import NotificationService
from datetime import datetime
import logging

veeam_bp = Blueprint('veeam', __name__, url_prefix='/api/veeam')
logger = logging.getLogger(__name__)

@veeam_bp.route('/job-complete', methods=['POST'])
def job_complete():
    """
    Veeamからのジョブ完了通知を受け取るエンドポイント
    
    リクエストボディ:
    {
        "jobName": "VM Backup Job 1",
        "jobId": "12345678-1234-1234-1234-123456789012",
        "status": "Success",
        "backupSize": "1024000",
        "duration": "3600",
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """
    try:
        data = request.get_json()
        
        # リクエストデータの検証
        required_fields = ['jobName', 'jobId', 'status']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # 履歴レコードを作成
        history = BackupHistory(
            job_name=data['jobName'],
            veeam_job_id=data['jobId'],
            status=data['status'],
            backup_size=data.get('backupSize'),
            duration=data.get('duration'),
            completed_at=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        )
        
        db.session.add(history)
        db.session.commit()
        
        logger.info(f"ジョブ完了通知を記録: {data['jobName']} - {data['status']}")
        
        # 通知を送信（エラー時）
        if data['status'] != 'Success':
            notification_service = NotificationService()
            notification_service.send_job_failure_notification(
                job_name=data['jobName'],
                status=data['status'],
                error_details=data.get('errorMessage', '')
            )
        
        return jsonify({
            'success': True,
            'message': 'Job completion notification received'
        }), 200
        
    except Exception as e:
        logger.error(f"エラー: {e}")
        return jsonify({'error': str(e)}), 500
```

---

## テスト実行

### ステップ1: 接続テスト

```bash
# Veeamサーバーへの接続確認
curl -v http://veeam-server:9398/api/about

# 期待される応答
# HTTP/1.1 200 OK
# {
#   "ProductVersion": "12.0.0.1234",
#   "RestVersion": "1.4"
# }
```

### ステップ2: APIテスト（実際のジョブなしで実行）

```bash
# テスト用のPOSTリクエスト
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "jobName": "Test Backup Job",
    "jobId": "test-job-id",
    "status": "Success",
    "backupSize": "1024000",
    "duration": "1800",
    "timestamp": "2024-01-15T10:30:00Z"
  }' \
  http://localhost:5000/api/veeam/job-complete

# 期待される応答
# HTTP/1.1 200 OK
# {
#   "success": true,
#   "message": "Job completion notification received"
# }
```

### ステップ3: 実際のジョブでテスト

1. **Veeamコンソールで任意のバックアップジョブを選択**

2. **"今すぐ実行"をクリック**

   ```
   画面: ジョブ実行画面
   [VM Backup Job 1] > [今すぐ実行]
   
   バックアップが開始されます。
   進捗表示:
   ████████░░ 80% - 実行中
   ```

3. **ジョブ完了後、バックアップ管理システムで履歴を確認**

   ```
   ブラウザ: http://localhost/backup-history
   
   ┌─────────────────────────────────────┐
   │ バックアップ実行履歴                │
   ├─────────────────────────────────────┤
   │ ジョブ名         │ 状態  │ 時刻    │
   ├─────────────────────────────────────┤
   │ Test Backup Job │ 成功 │ 10:30   │
   │ VM Backup Job 1 │ 成功 │ 10:15   │
   └─────────────────────────────────────┘
   ```

---

## トラブルシューティング

### 問題1: Veeamへの接続ができない

**症状**: "接続タイムアウト" または "接続拒否"

**対応**:

```bash
# 1. ホスト名解決確認
nslookup veeam-server
ping veeam-server

# 2. ポート接続確認
nc -zv veeam-server 9398

# 3. Veeamサーバーのファイアウォール設定確認
# Windows: Windows Defender ファイアウォール
# Linux: firewalld/ufw

# 4. Veeamサーバーのサービス状態確認
# Windows: Veeam Backup Service が実行されているか確認
# Linux: systemctl status veeam-backup
```

### 問題2: 認証失敗

**症状**: "401 Unauthorized"

**対応**:

```bash
# 1. ユーザー名とパスワードを確認
echo "VEEAM_USERNAME=$VEEAM_USERNAME"
# 期待: api-backup-mgmt

# 2. 環境変数の.env ファイルを確認
grep "VEEAM_" .env

# 3. Veeamでユーザーが有効か確認
# Veeamコンソール → 設定 → ユーザー管理 → api-backup-mgmt が存在

# 4. パスワードをリセット（必要に応じて）
# Veeamコンソール → ユーザー編集 → パスワード変更
```

### 問題3: ポストジョブスクリプトが実行されない

**症状**: ジョブは完了するが、バックアップ管理システムに通知が来ない

**対応**:

```bash
# 1. Veeamコンソールで設定を確認
# ジョブプロパティ → 詳細設定 → "ポストジョブスクリプトを実行" にチェック

# 2. スクリプトが実行可能か確認（Linux）
ls -la /usr/local/bin/backup-notification.sh
# 出力例: -rwxr-xr-x

# 3. スクリプトの手動実行テスト
/usr/local/bin/backup-notification.sh "Test Job" "test-id" "Success" "1024000" "3600"

# 4. ログファイルを確認
tail -50 /var/log/veeam-notifications.log

# 5. Veeamのイベントログを確認（Windows）
eventvwr.msc → Windows ログ → アプリケーション
```

### 問題4: スクリプト実行後にエラーが返される

**症状**: ジョブは完了するが、スクリプトでエラーになる

**対応**:

```bash
# 1. curl/Invoke-WebRequest のテスト
# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:5000/api/veeam/job-complete" `
  -Method POST -Body '{"test":"data"}' -ContentType "application/json"

# Linux bash
curl -X POST http://localhost:5000/api/veeam/job-complete \
  -H "Content-Type: application/json" \
  -d '{"test":"data"}'

# 2. バックアップ管理システムのログを確認
journalctl -u backup-management.service -n 50

# 3. Nginxのログを確認
tail -50 /var/log/nginx/error.log

# 4. ファイアウォール設定を確認
# Veeamサーバーからバックアップ管理システムへの通信が許可されているか
```

### 問題5: "Job ID not found"エラー

**症状**: Veeam APIで"404 Not Found"が返される

**対応**:

```bash
# 1. ジョブIDが正しいか確認
# Veeam APIで全ジョブを取得
curl -H "X-RestSvcSessionId: $SESSION_ID" \
  "http://veeam-server:9398/api/jobs?v=1.4" | jq .

# 2. ジョブIDの形式確認
# 正しい形式: UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)

# 3. ジョブが削除されていないか確認
# Veeamコンソールで該当ジョブが存在するか確認
```

---

## APIリファレンス

### REST API エンドポイント一覧

| メソッド | エンドポイント | 説明 |
|---------|----------------|------|
| POST | /api/sessionMgr | セッション作成（認証） |
| GET | /api/jobs | バックアップジョブ一覧 |
| GET | /api/jobs/{jobId} | 特定のジョブ詳細 |
| GET | /api/backupServers | バックアップサーバー一覧 |
| POST | /api/jobs/{jobId}/start | ジョブ実行 |
| GET | /api/jobs/{jobId}/lastSession | 最終実行情報 |
| GET | /api/repositories | バックアップリポジトリ一覧 |

### セッション管理

```bash
# セッション作成
curl -X POST \
  -H "Authorization: Basic $(echo -n 'user:pass' | base64)" \
  "http://veeam:9398/api/sessionMgr/?v=1.4"

# レスポンス
# Set-Cookie: X-RestSvcSessionId=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# セッション削除
curl -X DELETE \
  -H "X-RestSvcSessionId: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" \
  "http://veeam:9398/api/sessionMgr/?v=1.4"
```

### ジョブ実行API

```bash
# ジョブを実行
curl -X POST \
  -H "X-RestSvcSessionId: $SESSION_ID" \
  "http://veeam:9398/api/jobs/12345678-1234-1234-1234-123456789012/start"

# レスポンス例
{
  "UID": "87654321-4321-4321-4321-210987654321",
  "JobUid": "12345678-1234-1234-1234-123456789012",
  "State": "Running",
  "Progress": {
    "TaskNumber": 1,
    "TotalTasks": 1,
    "CompletedSize": 0,
    "TotalSize": 1099511627776
  }
}
```

### セッション情報取得

```bash
# セッション情報を確認
curl -H "X-RestSvcSessionId: $SESSION_ID" \
  "http://veeam:9398/api/sessionMgr/"

# レスポンス例
{
  "User": "api-backup-mgmt",
  "LogonTime": "2024-01-15T10:00:00.000Z",
  "SessionTimeout": 3600,
  "IsSessionIdValid": true
}
```

---

## セキュリティベストプラクティス

### 1. APIトークン管理

```bash
# 環境変数で管理（ファイルには記録しない）
export VEEAM_PASSWORD="$(cat /run/secrets/veeam_password)"

# または、systemd環境ファイル
cat > /etc/default/backup-mgmt << EOF
VEEAM_USERNAME=api-backup-mgmt
VEEAM_PASSWORD=secure-password-here
EOF
```

### 2. ネットワークセキュリティ

```nginx
# Veeamサーバーからのアクセスのみを許可
location /api/veeam/ {
    allow 192.168.1.100;  # Veeamサーバー IP
    deny all;
}
```

### 3. SSL/TLS設定

```bash
# Veeamが自己署名証明書を使用している場合
VEEAM_VERIFY_SSL=false  # 開発環境のみ

# 本番環境では
VEEAM_VERIFY_SSL=true
VEEAM_CA_BUNDLE=/path/to/ca-bundle.crt
```

### 4. ログの監視

```bash
# ポストジョブスクリプトのログを監視
tail -f /var/log/veeam-notifications.log | grep -i error

# 定期的にログをチェック
logwatch --detail high --service veeam
```

---

## まとめ

正常に設定できた場合、以下の流れで自動運用が実現されます:

1. **Veeamでバックアップジョブが完了**
2. **ポストジョブスクリプトが自動実行**
3. **バックアップ管理システムに通知**
4. **実行履歴が自動記録**
5. **必要に応じてメール/Teams通知**

トラブルが発生した場合は、前述のトラブルシューティング セクションを参照してください。

---

**最終更新**: 2024年1月
**バージョン**: 1.0
**対応Veeamバージョン**: 11.0, 12.0 以上
