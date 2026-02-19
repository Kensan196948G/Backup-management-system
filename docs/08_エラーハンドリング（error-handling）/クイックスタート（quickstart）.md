# エラーハンドリング - クイックスタートガイド

## 10分で始める

### 1. ファイルのロード

```powershell
# PowerShellスクリプトの先頭に追加
. .\powershell\error_handling_utils.ps1
. .\powershell\common_functions_enhanced.ps1
```

### 2. 基本的な使用パターン

#### Pattern A: API呼び出し（推奨）

```powershell
try {
    # 設定読み込み
    $config = Get-BackupSystemConfig

    # APIエンドポイント設定
    $apiUrl = $config.api_url.TrimEnd('/') + "/api/backup/update-status"

    # リトライ付きAPI呼び出し
    $response = Invoke-WithRetry `
        -ScriptBlock {
            Invoke-RestMethod -Uri $apiUrl -Method Post `
                -Headers $headers -Body $body -ErrorAction Stop
        } `
        -MaxRetries 3 `
        -OperationName "Send-BackupStatus"

    Write-BackupLog -Level "INFO" -Message "API call succeeded" -JobId $jobId
    return $response
}
catch {
    # エラーコンテキスト作成
    $ctx = New-ErrorContext -Exception $_ `
        -FunctionName "MyFunction" `
        -Context @{ job_id = $jobId }

    # ログ記録
    Write-ErrorContext -ErrorContext $ctx -JobId $jobId

    # 統計記録
    Add-ErrorStatistic -ErrorContext $ctx

    # 再スロー
    throw
}
```

#### Pattern B: ファイル操作

```powershell
try {
    # 検証
    if (-not (Test-ValidString -Value $filePath -ParameterName "FilePath")) {
        throw "Invalid file path"
    }

    # ファイル処理
    $content = Get-Content $filePath -Raw

    Write-BackupLog -Level "INFO" -Message "File read successfully"
}
catch {
    $ctx = New-ErrorContext -Exception $_ `
        -FunctionName "ReadBackupFile" `
        -Context @{ file_path = $filePath }

    Write-ErrorContext -ErrorContext $ctx
    Add-ErrorStatistic -ErrorContext $ctx
    throw
}
```

#### Pattern C: 外部プロセス実行

```powershell
try {
    # パラメータ検証
    if (-not (Test-ValidJobId -JobId $jobId)) {
        throw "Invalid JobId: $jobId"
    }

    # リトライ付き実行
    $result = Invoke-WithRetry `
        -ScriptBlock {
            & $executablePath -JobId $jobId -ErrorAction Stop
        } `
        -MaxRetries 2 `
        -InitialWaitMs 2000 `
        -OperationName "Execute backup job"

    Write-BackupLog -Level "INFO" -Message "Job execution succeeded" -JobId $jobId
}
catch {
    $ctx = New-ErrorContext -Exception $_ `
        -FunctionName "ExecuteBackupJob" `
        -Context @{ job_id = $jobId }

    Write-ErrorContext -ErrorContext $ctx -JobId $jobId
    Add-ErrorStatistic -ErrorContext $ctx
    throw
}
```

### 3. よく使う関数

#### リトライ

```powershell
# 3回リトライ（1秒→2秒→4秒待機）
Invoke-WithRetry -ScriptBlock { ... } -MaxRetries 3

# カスタム設定
Invoke-WithRetry `
    -ScriptBlock { ... } `
    -MaxRetries 5 `
    -InitialWaitMs 2000 `
    -MaxWaitMs 60000
```

#### 検証

```powershell
# ジョブID検証
if (Test-ValidJobId -JobId $jobId) { ... }

# 文字列検証
if (Test-ValidString -Value $jobName -ParameterName "JobName") { ... }

# URI検証
if (Test-ValidUri -Uri $apiUrl) { ... }
```

#### ログ

```powershell
# 情報ログ
Write-BackupLog -Level "INFO" -Message "Processing started" -JobId 1

# 警告ログ
Write-BackupLog -Level "WARNING" -Message "Optional data missing" -JobId 1

# エラーログ
Write-BackupLog -Level "ERROR" -Message "Operation failed: $error" -JobId 1
```

#### エラー情報

```powershell
# エラーコンテキスト作成
$ctx = New-ErrorContext -Exception $_ `
    -FunctionName "MyFunc" `
    -Context @{ job_id = 123; operation = "backup" }

# ログ記録
Write-ErrorContext -ErrorContext $ctx -JobId 123

# 統計記録
Add-ErrorStatistic -ErrorContext $ctx
```

#### 統計

```powershell
# 統計取得
$stats = Get-ErrorStatistics
Write-Host "Total errors: $($stats.total_errors)"

# レポート出力
Write-ErrorStatisticsReport -IncludeDetails
```

### 4. チートシート

| 目的 | 関数 | 用途 |
|-----|-----|------|
| リトライ | `Invoke-WithRetry` | API呼び出し、外部プロセス |
| 検証 | `Test-Valid*` | パラメータ検証 |
| ログ | `Write-BackupLog` | ログ出力 |
| エラー | `New-ErrorContext` | 詳細情報取得 |
| 統計 | `Get-ErrorStatistics` | エラー分析 |
| 変換 | `Convert-*` | 単位変換 |

### 5. エラー分類

```powershell
# 一時的エラー（リトライ推奨）
if (Test-TransientError -Exception $error) {
    # リトライ実行
    $result = Invoke-WithRetry { ... }
}

# 永続的エラー（即座に終了）
else {
    # エラーを記録して終了
    Write-BackupLog -Level "ERROR" -Message "Fatal error"
    throw
}
```

### 6. 実行例

```powershell
# スクリプト開始
.\scripts\powershell\veeam_integration.ps1 -JobId 1 -JobName "Daily Backup"

# テスト実行
.\scripts\test_error_handling.ps1

# レポート確認
cat test_error_handling_report.txt
```

## よくある質問

### Q: リトライは何回まで？
A: デフォルト3回。`-MaxRetries`で調整可能。API呼び出しは3回、ネットワークは5回推奨。

### Q: ログはどこに保存？
A: `scripts/powershell/logs/` ディレクトリに日付別で保存。

### Q: エラーが回復不可能か判定するには？
A: `Test-TransientError -Exception $_` で判定。$trueなら一時的、$falseなら永続的。

### Q: スタックトレースを確認するには？
A: `New-ErrorContext`で自動取得。`$_.ScriptStackTrace`でも確認可能。

### Q: 統計情報をリセットするには？
A: `$script:ErrorStats = @{ ... }`で再初期化。

## 次のステップ

詳細は以下を参照：
- 実装ガイド: `ERROR_HANDLING_IMPLEMENTATION.md`
- 分析レポート: `ERROR_HANDLING_ANALYSIS.md`
- 完了レポート: `ERROR_HANDLING_SUMMARY.md`

## トラブル時

### エラー: "Export-ModuleMember can only be called from inside a module"
**原因**: スクリプトが直接実行されている
**対策**: `. .\error_handling_utils.ps1` でスクリプトを内包すれば問題なし

### エラー: "Cannot bind argument to parameter"
**原因**: パラメータ型が不正
**対策**: `[ValidateScript]`属性を確認。例えば `JobId`は正の整数のみ

### ログが出力されない
**原因**: ディレクトリ権限不足
**対策**: `C:\Users\<user>\AppData\Local\` に書き込み権限があるか確認

---

**版**: 1.0
**最終更新**: 2024-10-31
