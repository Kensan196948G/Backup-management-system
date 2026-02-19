<#
.SYNOPSIS
    ログイン問題包括的診断スクリプト

.DESCRIPTION
    Windows本番環境でのログイン問題を診断し、解決策を提示

.EXAMPLE
    pwsh -File scripts/diagnose_login_issue.ps1
#>

param(
    [string]$InstallPath = "C:\BackupSystem"
)

Write-Host "╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                       ║" -ForegroundColor Cyan
Write-Host "║           🔍 ログイン問題包括的診断                                   ║" -ForegroundColor Cyan
Write-Host "║           3-2-1-1-0 バックアップ管理システム                          ║" -ForegroundColor Cyan
Write-Host "║                                                                       ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$issues = @()
$fixes = @()

# チェック1: .envファイル確認
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "1️⃣  .envファイル確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$envPath = Join-Path $InstallPath ".env"

if (Test-Path $envPath) {
    Write-Host "  ✅ .envファイル存在: $envPath" -ForegroundColor Green

    $envContent = Get-Content $envPath -Raw

    # SECRET_KEYチェック
    if ($envContent -match 'SECRET_KEY\s*=\s*(.+)') {
        $secretKey = $Matches[1].Trim()

        if ($secretKey.Length -lt 32) {
            Write-Host "  ❌ SECRET_KEYが短すぎます: $($secretKey.Length)文字" -ForegroundColor Red
            $issues += "SECRET_KEYが短すぎる（$($secretKey.Length)文字 < 32文字）"
            $fixes += "SECRET_KEY を32文字以上に設定"
        } elseif ($secretKey -eq 'your-secret-key-here' -or $secretKey -eq 'dev-secret-key') {
            Write-Host "  ❌ SECRET_KEYがデフォルト値です" -ForegroundColor Red
            $issues += "SECRET_KEYがデフォルト値"
            $fixes += "ランダムなSECRET_KEYを生成・設定"
        } else {
            Write-Host "  ✅ SECRET_KEY設定済み: $($secretKey.Length)文字" -ForegroundColor Green
        }
    } else {
        Write-Host "  ❌ SECRET_KEYが設定されていません" -ForegroundColor Red
        $issues += "SECRET_KEY未設定"
        $fixes += "SECRET_KEYを生成・設定"
    }

    # FLASK_ENVチェック
    if ($envContent -match 'FLASK_ENV\s*=\s*(.+)') {
        $flaskEnv = $Matches[1].Trim()
        Write-Host "  ✅ FLASK_ENV: $flaskEnv" -ForegroundColor Green
    }

} else {
    Write-Host "  ❌ .envファイルが見つかりません" -ForegroundColor Red
    $issues += ".envファイルが存在しない"
    $fixes += ".env.exampleをコピーして.envを作成"
}

Write-Host ""

# チェック2: データベース確認
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "2️⃣  データベース確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$dbPath = Join-Path $InstallPath "data\backup_mgmt.db"

if (Test-Path $dbPath) {
    $dbInfo = Get-Item $dbPath
    Write-Host "  ✅ データベース存在: $dbPath" -ForegroundColor Green
    Write-Host "  📊 サイズ: $($dbInfo.Length) bytes" -ForegroundColor White
    Write-Host "  📅 最終更新: $($dbInfo.LastWriteTime)" -ForegroundColor White

    # Pythonでテーブル確認
    $pythonPath = Join-Path $InstallPath "venv\Scripts\python.exe"

    if (Test-Path $pythonPath) {
        try {
            $checkScript = @"
import sqlite3
conn = sqlite3.connect(r'$dbPath')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f'テーブル数: {len(tables)}')
if 'users' in tables:
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    print(f'ユーザー数: {user_count}')
    if user_count > 0:
        cursor.execute('SELECT username, email, is_active FROM users')
        for row in cursor.fetchall():
            print(f'ユーザー: {row[0]} ({row[1]}) - 有効: {row[2]}')
else:
    print('エラー: usersテーブルが存在しません')
conn.close()
"@

            $result = & $pythonPath -c $checkScript 2>&1
            Write-Host "  $result" -ForegroundColor White

            if ($result -match 'エラー: usersテーブルが存在しません') {
                $issues += "usersテーブルが存在しない"
                $fixes += "fix_database.py を実行してテーブルを作成"
            }

        } catch {
            Write-Host "  ⚠️  データベース確認エラー: $_" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ❌ データベースが見つかりません" -ForegroundColor Red
    $issues += "データベースファイルが存在しない"
    $fixes += "fix_database.py を実行してデータベースを作成"
}

Write-Host ""

# チェック3: Windowsサービス確認
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "3️⃣  Windowsサービス確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $service = Get-Service -Name BackupManagementSystem -ErrorAction Stop

    if ($service.Status -eq 'Running') {
        Write-Host "  ✅ サービス稼働中" -ForegroundColor Green
    } else {
        Write-Host "  ❌ サービス停止中: $($service.Status)" -ForegroundColor Red
        $issues += "Windowsサービスが停止中"
        $fixes += "Start-Service -Name BackupManagementSystem"
    }
} catch {
    Write-Host "  ❌ サービスが見つかりません" -ForegroundColor Red
    $issues += "Windowsサービス未登録"
    $fixes += "install_service.ps1 を実行"
}

Write-Host ""

# チェック4: ログファイル確認
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "4️⃣  ログファイル確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$stderrPath = Join-Path $InstallPath "logs\service_stderr.log"

if (Test-Path $stderrPath) {
    $logContent = Get-Content $stderrPath -Tail 20
    Write-Host "  📝 最新20行のログ:" -ForegroundColor White

    foreach ($line in $logContent) {
        if ($line -match 'ERROR') {
            Write-Host "  ❌ $line" -ForegroundColor Red
        } elseif ($line -match 'WARNING') {
            Write-Host "  ⚠️  $line" -ForegroundColor Yellow
        } else {
            Write-Host "  ℹ️  $line" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  ⚠️  ログファイルが見つかりません" -ForegroundColor Yellow
}

Write-Host ""

# チェック5: ネットワーク確認
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "5️⃣  ネットワーク確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/auth/login" -Method GET -UseBasicParsing -TimeoutSec 5
    Write-Host "  ✅ /auth/login にアクセス可能" -ForegroundColor Green
    Write-Host "  📊 ステータスコード: $($response.StatusCode)" -ForegroundColor White
} catch {
    if ($_.Exception.Response.StatusCode.Value__ -eq 401) {
        Write-Host "  ✅ エンドポイント応答（401 = 認証必要 = 正常）" -ForegroundColor Green
    } else {
        Write-Host "  ❌ エンドポイントエラー: $_" -ForegroundColor Red
    }
}

Write-Host ""

# サマリー
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📊 診断結果サマリー" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

if ($issues.Count -eq 0) {
    Write-Host "✅ 問題は検出されませんでした" -ForegroundColor Green
    Write-Host ""
    Write-Host "ログイン情報を再確認してください:" -ForegroundColor Yellow
    Write-Host "  ユーザー名: admin" -ForegroundColor White
    Write-Host "  メールアドレス: admin@example.com" -ForegroundColor White
    Write-Host "  パスワード: （設定したパスワード）" -ForegroundColor White
} else {
    Write-Host "❌ 検出された問題:" -ForegroundColor Red
    foreach ($issue in $issues) {
        Write-Host "  • $issue" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "✅ 推奨される解決策:" -ForegroundColor Green
    foreach ($fix in $fixes) {
        Write-Host "  • $fix" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
