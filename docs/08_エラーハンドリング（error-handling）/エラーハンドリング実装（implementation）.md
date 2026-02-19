# PowerShell エラーハンドリング強化 - 実装ガイド

## 概要

このドキュメントは、PowerShell統合スクリプトに実装されたエラーハンドリング機構の詳細な使用方法を説明します。

## 実装済み機能

### 1. リトライロジック（Invoke-WithRetry）

**目的:** ネットワーク一時的エラーに対する自動リトライ機構

**特徴:**
- 指数バックオフ戦略
- 最大リトライ回数制御
- 待機時間の制限

**使用例:**

```powershell
# 基本的な使用
$response = Invoke-WithRetry -ScriptBlock {
    Invoke-RestMethod -Uri $apiUrl -Method Post -Body $jsonBody
} -MaxRetries 3

# カスタム設定
$response = Invoke-WithRetry `
    -ScriptBlock {
        Invoke-RestMethod -Uri $apiUrl -Method Post
    } `
    -MaxRetries 5 `
    -InitialWaitMs 2000 `
    -MaxWaitMs 60000 `
    -BackoffMultiplier 2.0 `
    -OperationName "API Send"
```

**パラメータ:**
- `ScriptBlock`: 実行するコマンド
- `MaxRetries`: 最大リトライ回数（デフォルト: 3）
- `InitialWaitMs`: 初回待機時間（デフォルト: 1000ms）
- `MaxWaitMs`: 最大待機時間（デフォルト: 30000ms）
- `BackoffMultiplier`: バックオフ乗数（デフォルト: 2.0）
- `OperationName`: 操作名（ログ用）

**タイミング例:**
```
試行 1 失敗 → 1秒待機
試行 2 失敗 → 2秒待機
試行 3 失敗 → 4秒待機
試行 4 成功
```

### 2. エラー分類（Test-TransientError）

**目的:** エラーの種類を判定し、適切なハンドリング戦略を選択

**戻り値:**
- `$true`: 一時的エラー（リトライ推奨）
- `$false`: 永続的エラー（即座に終了）

**検出対象（一時的エラー）:**
```
- timeout / Operation timed out
- temporarily unavailable
- service unavailable
- connection refused
- no route to host
- reset by peer
- HTTP 5xx ステータスコード
```

**使用例:**

```powershell
try {
    Invoke-RestMethod -Uri $apiUrl -Method Post
}
catch {
    if (Test-TransientError -Exception $_) {
        # リトライロジックを実行
        # または別の対応を実施
    }
    else {
        # 即座に失敗を報告
        throw
    }
}
```

### 3. エラーコンテキスト（New-ErrorContext）

**目的:** デバッグとトラブルシューティングのための詳細エラー情報収集

**生成されるコンテキスト情報:**

```powershell
@{
    timestamp = "2024-10-31T14:30:45.1234567+09:00"  # ISO 8601
    function_name = "Send-BackupStatus"
    error_message = "Connection timeout"
    error_type = "System.Net.WebException"
    script_stack_trace = "at Send-BackupStatus, ..."
    invocation_info = @{
        script_name = "common_functions.ps1"
        line_number = 245
        line = "Invoke-RestMethod -Uri $apiUrl ..."
    }
    context = @{
        job_id = 123
        operation = "backup_status"
    }
    is_transient = $true
}
```

**使用例:**

```powershell
try {
    Send-BackupStatus -JobId 1 -Status "success"
}
catch {
    # 詳細コンテキストを作成
    $errorContext = New-ErrorContext `
        -Exception $_ `
        -FunctionName "Send-BackupStatus" `
        -Context @{
            job_id = 1
            operation = "status_update"
        }

    # ログに記録
    Write-ErrorContext -ErrorContext $errorContext -JobId 1

    # 統計に追加
    Add-ErrorStatistic -ErrorContext $errorContext
}
```

### 4. パラメータ検証

#### Test-ValidJobId
```powershell
# 有効: 正の整数
Test-ValidJobId -JobId 123      # $true

# 無効: ゼロ以下
Test-ValidJobId -JobId 0        # $false
Test-ValidJobId -JobId -1       # $false
Test-ValidJobId -JobId $null    # $false
```

#### Test-ValidString
```powershell
# 有効: 非空文字列
Test-ValidString -Value "backup_job" -ParameterName "JobName"  # $true

# 無効: 空、null、空白のみ
Test-ValidString -Value ""                                      # $false
Test-ValidString -Value $null                                   # $false
Test-ValidString -Value "   "                                   # $false
```

#### Test-ValidUri
```powershell
# 有効: HTTP/HTTPS
Test-ValidUri -Uri "https://api.example.com/v1"     # $true
Test-ValidUri -Uri "http://localhost:8080"          # $true

# 無効: その他のスキーム
Test-ValidUri -Uri "ftp://example.com"              # $false
Test-ValidUri -Uri "invalid-uri"                    # $false
```

### 5. エラー統計（Get-ErrorStatistics）

**目的:** エラー発生パターンの可視化と分析

**生成される統計情報:**

```powershell
@{
    total_errors = 42
    transient_errors = 25
    permanent_errors = 17
    by_type = @{
        "System.Net.WebException" = 15
        "System.IO.IOException" = 10
        "System.InvalidOperationException" = 17
    }
    by_function = @{
        "Send-BackupStatus" = 20
        "Get-VeeamJobInfo" = 15
        "Get-WSBJobInfo" = 7
    }
}
```

**使用例:**

```powershell
# 統計情報を取得
$stats = Get-ErrorStatistics

# 統計レポートを出力
Write-ErrorStatisticsReport -IncludeDetails
```

## 実装パターン

### パターン 1: シンプルなAPI呼び出しとリトライ

```powershell
function Send-BackupStatus {
    param(
        [int]$JobId,
        [string]$Status,
        [long]$BackupSize = 0
    )

    try {
        # パラメータ検証
        if (-not (Test-ValidJobId -JobId $JobId)) {
            throw "Invalid JobId: $JobId"
        }

        # リトライ付きAPI呼び出し
        $response = Invoke-WithRetry `
            -ScriptBlock {
                Invoke-RestMethod -Uri $apiUrl -Method Post `
                    -Headers $headers -Body $body
            } `
            -MaxRetries 3 `
            -OperationName "Send-BackupStatus"

        Write-BackupLog -Level "INFO" -Message "Status sent successfully" -JobId $JobId
        return $response
    }
    catch {
        $errorContext = New-ErrorContext -Exception $_ `
            -FunctionName "Send-BackupStatus" `
            -Context @{ job_id = $JobId; status = $Status }

        Write-ErrorContext -ErrorContext $errorContext -JobId $JobId
        Add-ErrorStatistic -ErrorContext $errorContext

        throw
    }
}
```

### パターン 2: エラー分類による条件分岐

```powershell
try {
    $data = Invoke-RestMethod -Uri $apiUrl
}
catch {
    if (Test-TransientError -Exception $_) {
        # リトライ可能なエラー
        Write-BackupLog -Level "WARNING" `
            -Message "Transient error: $($_.Exception.Message). Will retry."

        $result = Invoke-WithRetry -ScriptBlock {
            Invoke-RestMethod -Uri $apiUrl
        } -MaxRetries 5
    }
    else {
        # 回復不可能なエラー
        Write-BackupLog -Level "ERROR" `
            -Message "Permanent error: $($_.Exception.Message). Aborting."

        throw
    }
}
```

### パターン 3: 部分的エラーハンドリング

```powershell
try {
    # メイン処理
    $jobInfo = Get-VeeamJobInfo -JobName $jobName
}
catch {
    # エラー処理（失敗を記録するが継続）
    $errorContext = New-ErrorContext -Exception $_ -FunctionName "Get-VeeamJobInfo"
    Write-ErrorContext -ErrorContext $errorContext
}

# バックアップサイズ取得失敗時はデフォルト値を使用
$backupSize = if ($jobInfo.BackupSize) { $jobInfo.BackupSize } else { 0 }

# 処理を継続
Send-BackupStatus -JobId $jobId -Status $jobInfo.Status -BackupSize $backupSize
```

### パターン 4: リソースのクリーンアップ

```powershell
try {
    $file = [System.IO.File]::OpenRead($filePath)

    # ファイル処理
    $content = $file.ReadToEnd()
}
catch {
    $errorContext = New-ErrorContext -Exception $_ -FunctionName "ReadBackupFile"
    Write-ErrorContext -ErrorContext $errorContext
    throw
}
finally {
    # 必ず実行される
    if ($file) {
        $file.Dispose()
    }
}
```

## 既存コードの移行ガイド

### Before（改善前）

```powershell
try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Post `
        -Headers $headers -Body $jsonBody -ErrorAction Stop
    Write-BackupLog -Level "INFO" -Message "API送信成功" -JobId $JobId
    return $response
}
catch {
    Write-BackupLog -Level "ERROR" -Message "API送信失敗: $_" -JobId $JobId
    throw
}
```

**問題点:**
- リトライ機構がない
- エラーが一時的か永続的か判定できない
- スタックトレース情報が不完全
- エラー統計の収集ができない

### After（改善後）

```powershell
try {
    # パラメータ検証
    if (-not (Test-ValidJobId -JobId $JobId)) {
        throw "Invalid JobId: $JobId"
    }

    # リトライ付きAPI呼び出し
    $response = Invoke-WithRetry `
        -ScriptBlock {
            Invoke-RestMethod -Uri $apiUrl -Method Post `
                -Headers $headers -Body $jsonBody `
                -ErrorAction Stop
        } `
        -MaxRetries 3 `
        -OperationName "API send for job $JobId"

    Write-BackupLog -Level "INFO" -Message "API send successful" -JobId $JobId
    return $response
}
catch {
    # 詳細なエラーコンテキスト作成
    $errorContext = New-ErrorContext `
        -Exception $_ `
        -FunctionName "Send-BackupStatus" `
        -Context @{
            job_id = $JobId
            api_url = $apiUrl
            backup_size = $BackupSize
        }

    # ログに詳細情報を記録
    Write-ErrorContext -ErrorContext $errorContext -JobId $JobId

    # 統計に追加
    Add-ErrorStatistic -ErrorContext $errorContext

    # 再スロー
    throw
}
```

**改善点:**
- リトライ機構実装済み
- エラーコンテキストに詳細情報を含む
- 統計情報を自動収集
- スタックトレースとタイムスタンプを記録

## テスト実行

### 基本的なテスト実行

```powershell
# スクリプトディレクトリで実行
cd scripts

# テスト実行
.\test_error_handling.ps1

# 詳細ログ付き実行
.\test_error_handling.ps1 -Verbose

# インテグレーションテスト含む
.\test_error_handling.ps1 -IncludeIntegrationTests

# レポート出力先指定
.\test_error_handling.ps1 -ReportPath "C:\logs\test_report.txt"
```

### テスト結果確認

```
================================================================================
ERROR HANDLING TEST REPORT
================================================================================
Execution Time: 2024-10-31 14:35:22

SUMMARY
-------
Total Tests:  27
Passed:       27
Failed:       0
Skipped:      0
Pass Rate:    100.00%
```

## トラブルシューティング

### リトライが機能していないように見える

**症状:** エラー発生時に即座に失敗する

**確認項目:**
1. `Invoke-WithRetry`を使用しているか
2. `MaxRetries`が0でないか
3. エラーが実際に一時的か（`Test-TransientError`で確認）

```powershell
# デバッグ方法
$context = @{...}
$isTransient = Test-TransientError -Exception $myException
Write-Host "Error is transient: $isTransient"
```

### ログが記録されていない

**症状:** `Write-BackupLog`が機能していない

**確認項目:**
1. ログディレクトリが書き込み可能か
2. パスが正しいか

```powershell
# ログパスの確認
Write-Host "Log path: $script:LogPath"
Write-Host "Exists: $(Test-Path $script:LogPath)"
Write-Host "Writable: $(Test-Path -Path $script:LogPath -IsValid)"
```

### エラーコンテキストが不完全

**症状:** スタックトレース情報が不完全

**確認:** `New-ErrorContext`に`Exception`オブジェクト全体を渡しているか

```powershell
# 正しい方法
catch {
    $context = New-ErrorContext -Exception $_  # $_全体を渡す
}

# 誤り
catch {
    $context = New-ErrorContext -Exception $_.Exception.Message  # 文字列だけ
}
```

## ベストプラクティス

1. **常にパラメータを検証する**
   ```powershell
   if (-not (Test-ValidJobId -JobId $JobId)) {
       throw "Invalid JobId"
   }
   ```

2. **APIコールには必ずリトライを使用する**
   ```powershell
   Invoke-WithRetry -ScriptBlock { ... } -MaxRetries 3
   ```

3. **エラーコンテキストは常に作成する**
   ```powershell
   $context = New-ErrorContext -Exception $_ -FunctionName $FunctionName
   ```

4. **エラー統計を活用する**
   ```powershell
   Write-ErrorStatisticsReport -IncludeDetails
   ```

5. **適切なログレベルを使用する**
   - `INFO`: 正常な進行状況
   - `WARNING`: 回復可能なエラー、デフォルト値の使用
   - `ERROR`: 回復不可能なエラー

## パフォーマンス考慮事項

### リトライ設定ガイドライン

| 操作 | Max Retries | Initial Wait | Max Wait | Multiplier |
|-----|------------|-------------|----------|-----------|
| API送信 | 3 | 1000ms | 30000ms | 2.0 |
| ファイル読み込み | 2 | 500ms | 5000ms | 2.0 |
| ネットワーク接続 | 5 | 2000ms | 60000ms | 1.5 |

### メモリ使用量

エラー統計情報はメモリに保持されるため、長時間実行する場合は定期的にリセットすることを推奨：

```powershell
$script:ErrorStats = @{
    total_errors = 0
    transient_errors = 0
    permanent_errors = 0
    by_type = @{}
    by_function = @{}
}
```

## 関連ファイル

- `/scripts/powershell/error_handling_utils.ps1` - エラーハンドリングユーティリティ
- `/scripts/powershell/common_functions_enhanced.ps1` - 拡張共通関数
- `/scripts/test_error_handling.ps1` - テストスイート
- `/ERROR_HANDLING_ANALYSIS.md` - 分析レポート
- `/ERROR_HANDLING_IMPLEMENTATION.md` - このガイド
