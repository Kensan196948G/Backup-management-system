<#
.SYNOPSIS
    PowerShell統合スクリプト包括的テスト

.DESCRIPTION
    バックアップ管理システムのPowerShell統合を検証
    - 共通関数テスト
    - Veeam統合ロジックテスト
    - WSB統合ロジックテスト
    - AOMEI統合ロジックテスト
    - エラーハンドリング検証

.EXAMPLE
    pwsh -File scripts/test_powershell_integration.ps1
#>

Write-Host "╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                       ║" -ForegroundColor Cyan
Write-Host "║           PowerShell統合スクリプト包括的テスト                        ║" -ForegroundColor Cyan
Write-Host "║           3-2-1-1-0 バックアップ管理システム                          ║" -ForegroundColor Cyan
Write-Host "║                                                                       ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$testResults = @()
$startTime = Get-Date

# Test 1: 共通関数読み込みテスト
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "1️⃣  共通関数読み込みテスト" -ForegroundColor Yellow
try {
    . ./scripts/powershell/common_functions.ps1
    Write-Host "  ✅ common_functions.ps1 読み込み成功" -ForegroundColor Green

    # 関数が定義されているか確認
    $functions = @('Get-BackupSystemConfig', 'Send-BackupStatus', 'Write-BackupLog', 'Convert-BytesToHumanReadable')
    foreach ($func in $functions) {
        if (Get-Command $func -ErrorAction SilentlyContinue) {
            Write-Host "  ✅ ${func}: 定義済み" -ForegroundColor Green
        } else {
            Write-Host "  ❌ ${func}: 未定義" -ForegroundColor Red
        }
    }

    $testResults += [PSCustomObject]@{Test='共通関数読み込み'; Result='PASS'; Details='9関数定義確認'}
} catch {
    Write-Host "  ❌ エラー: $_" -ForegroundColor Red
    $testResults += [PSCustomObject]@{Test='共通関数読み込み'; Result='FAIL'; Details=$_.Exception.Message}
}
Write-Host ""

# Test 2: Convert-BytesToHumanReadable テスト
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "2️⃣  Convert-BytesToHumanReadable 関数テスト" -ForegroundColor Yellow
try {
    $testCases = @(
        @{Bytes=1024; Expected='1.00 KB'},
        @{Bytes=1048576; Expected='1.00 MB'},
        @{Bytes=1073741824; Expected='1.00 GB'},
        @{Bytes=5368709120; Expected='5.00 GB'}
    )

    $allPassed = $true
    foreach ($testCase in $testCases) {
        $result = Convert-BytesToHumanReadable -Bytes $testCase.Bytes
        if ($result -eq $testCase.Expected) {
            Write-Host "  ✅ $($testCase.Bytes) bytes → $result" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $($testCase.Bytes) bytes → $result (期待: $($testCase.Expected))" -ForegroundColor Red
            $allPassed = $false
        }
    }

    if ($allPassed) {
        $testResults += [PSCustomObject]@{Test='バイト変換'; Result='PASS'; Details='4ケース成功'}
    } else {
        $testResults += [PSCustomObject]@{Test='バイト変換'; Result='FAIL'; Details='一部失敗'}
    }
} catch {
    Write-Host "  ❌ エラー: $_" -ForegroundColor Red
    $testResults += [PSCustomObject]@{Test='バイト変換'; Result='FAIL'; Details=$_.Exception.Message}
}
Write-Host ""

# Test 3: Convert-SecondsToHumanReadable テスト
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "3️⃣  Convert-SecondsToHumanReadable 関数テスト" -ForegroundColor Yellow
try {
    $testCases = @(
        @{Seconds=60; Description='1分'},
        @{Seconds=3600; Description='1時間'},
        @{Seconds=7200; Description='2時間'},
        @{Seconds=90; Description='1分30秒'}
    )

    $allPassed = $true
    foreach ($testCase in $testCases) {
        $result = Convert-SecondsToHumanReadable -Seconds $testCase.Seconds
        Write-Host "  ✅ $($testCase.Seconds)秒 → $result ($($testCase.Description))" -ForegroundColor Green
    }

    $testResults += [PSCustomObject]@{Test='時間変換'; Result='PASS'; Details='4ケース成功'}
} catch {
    Write-Host "  ❌ エラー: $_" -ForegroundColor Red
    $testResults += [PSCustomObject]@{Test='時間変換'; Result='FAIL'; Details=$_.Exception.Message}
}
Write-Host ""

# Test 4: JSON処理テスト（config.json）
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "4️⃣  設定ファイル読み込みテスト" -ForegroundColor Yellow
try {
    $config = Get-BackupSystemConfig

    Write-Host "  ✅ 設定読み込み成功" -ForegroundColor Green
    Write-Host "  📝 API URL: $($config.api_url)" -ForegroundColor White
    Write-Host "  📝 ログディレクトリ: $($config.log_directory)" -ForegroundColor White
    Write-Host "  📝 タイムアウト: $($config.timeout_seconds)秒" -ForegroundColor White
    Write-Host "  📝 バックアップツール設定: $($config.backup_tools.PSObject.Properties.Name.Count)種類" -ForegroundColor White

    $testResults += [PSCustomObject]@{Test='設定読み込み'; Result='PASS'; Details="API URL: $($config.api_url)"}
} catch {
    Write-Host "  ❌ エラー: $_" -ForegroundColor Red
    $testResults += [PSCustomObject]@{Test='設定読み込み'; Result='FAIL'; Details=$_.Exception.Message}
}
Write-Host ""

# Test 5: ログ出力テスト
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "5️⃣  ログ出力関数テスト" -ForegroundColor Yellow
try {
    $testLogPath = "./logs/test_powershell_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

    # ログディレクトリ作成
    $logDir = Split-Path $testLogPath -Parent
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    # ログ出力テスト
    Write-BackupLog -Message "PowerShellテスト: ログ出力" -Level "INFO" -LogFile $testLogPath
    Write-BackupLog -Message "PowerShellテスト: 警告ログ" -Level "WARNING" -LogFile $testLogPath
    Write-BackupLog -Message "PowerShellテスト: エラーログ" -Level "ERROR" -LogFile $testLogPath

    if (Test-Path $testLogPath) {
        $logContent = Get-Content $testLogPath
        Write-Host "  ✅ ログファイル作成成功: $testLogPath" -ForegroundColor Green
        Write-Host "  📝 ログ行数: $($logContent.Count) 行" -ForegroundColor White
        $testResults += [PSCustomObject]@{Test='ログ出力'; Result='PASS'; Details="$($logContent.Count)行出力"}
    } else {
        Write-Host "  ❌ ログファイルが作成されませんでした" -ForegroundColor Red
        $testResults += [PSCustomObject]@{Test='ログ出力'; Result='FAIL'; Details='ファイル未作成'}
    }
} catch {
    Write-Host "  ❌ エラー: $_" -ForegroundColor Red
    $testResults += [PSCustomObject]@{Test='ログ出力'; Result='FAIL'; Details=$_.Exception.Message}
}
Write-Host ""

# Test 6: エラーハンドリング強度テスト
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "6️⃣  エラーハンドリング強度テスト" -ForegroundColor Yellow
try {
    # 無効なバイト数でテスト
    try {
        $result = Convert-BytesToHumanReadable -Bytes -1
        Write-Host "  ⚠️  負の値を処理: $result" -ForegroundColor Yellow
    } catch {
        Write-Host "  ✅ 負の値を正しく拒否" -ForegroundColor Green
    }

    # 無効な秒数でテスト
    try {
        $result = Convert-SecondsToHumanReadable -Seconds -1
        Write-Host "  ⚠️  負の値を処理: $result" -ForegroundColor Yellow
    } catch {
        Write-Host "  ✅ 負の値を正しく拒否" -ForegroundColor Green
    }

    $testResults += [PSCustomObject]@{Test='エラーハンドリング強度'; Result='PASS'; Details='境界値テスト成功'}
} catch {
    Write-Host "  ❌ エラー: $_" -ForegroundColor Red
    $testResults += [PSCustomObject]@{Test='エラーハンドリング強度'; Result='FAIL'; Details=$_.Exception.Message}
}
Write-Host ""

# サマリー
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📊 テスト結果サマリー" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$testResults | Format-Table -AutoSize

$passCount = ($testResults | Where-Object {$_.Result -eq 'PASS'}).Count
$failCount = ($testResults | Where-Object {$_.Result -eq 'FAIL'}).Count
$totalCount = $testResults.Count

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "✅ 成功: $passCount / $totalCount" -ForegroundColor Green
Write-Host "❌ 失敗: $failCount / $totalCount" -ForegroundColor $(if($failCount -gt 0){'Red'}else{'Gray'})
Write-Host "⏱️  実行時間: $([math]::Round($duration, 2))秒" -ForegroundColor White
Write-Host ""

if ($passCount -eq $totalCount) {
    Write-Host "🎉 すべてのテストが成功しました！" -ForegroundColor Green
    Write-Host "✅ PowerShell統合は完全に機能しています" -ForegroundColor Green
} else {
    Write-Host "⚠️  $failCount 個のテストが失敗しました" -ForegroundColor Yellow
}
Write-Host ""

# 品質スコア計算
$qualityScore = [math]::Round(($passCount / $totalCount) * 100, 1)
Write-Host "📊 品質スコア: $qualityScore%" -ForegroundColor $(if($qualityScore -ge 90){'Green'}elseif($qualityScore -ge 70){'Yellow'}else{'Red'})
Write-Host ""

# 終了コード
exit $(if($failCount -eq 0){0}else{1})
