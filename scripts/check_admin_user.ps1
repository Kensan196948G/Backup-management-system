<#
.SYNOPSIS
    管理者ユーザー確認スクリプト

.DESCRIPTION
    データベース内の管理者ユーザー情報を確認

.EXAMPLE
    pwsh -File scripts/check_admin_user.ps1
#>

param(
    [string]$InstallPath = "C:\BackupSystem"
)

Write-Host "╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                       ║" -ForegroundColor Cyan
Write-Host "║           🔍 管理者ユーザー確認                                       ║" -ForegroundColor Cyan
Write-Host "║           3-2-1-1-0 バックアップ管理システム                          ║" -ForegroundColor Cyan
Write-Host "║                                                                       ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$dbPath = Join-Path $InstallPath "data\backup_mgmt.db"

if (-not (Test-Path $dbPath)) {
    Write-Host "❌ データベースファイルが見つかりません: $dbPath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ データベースファイル: $dbPath" -ForegroundColor Green
Write-Host ""

# SQLiteでユーザー情報を確認
try {
    # Pythonでデータベースを確認
    $pythonPath = Join-Path $InstallPath "venv\Scripts\python.exe"

    if (-not (Test-Path $pythonPath)) {
        Write-Host "❌ Python実行ファイルが見つかりません: $pythonPath" -ForegroundColor Red
        exit 1
    }

    Write-Host "📊 ユーザー情報を取得中..." -ForegroundColor Yellow
    Write-Host ""

    $pythonScript = @"
import sys
import sqlite3

db_path = r'$dbPath'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ユーザー数を取得
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    print(f'総ユーザー数: {user_count}')
    print('')

    # 全ユーザー情報を取得
    cursor.execute('SELECT id, username, email, role, is_active FROM users')
    users = cursor.fetchall()

    if user_count == 0:
        print('⚠️  ユーザーが登録されていません')
        print('')
        print('解決策: 新規管理者ユーザーを作成してください')
        print('  PS> cd C:\BackupSystem')
        print('  PS> .\venv\Scripts\python.exe scripts\create_admin.py')
    else:
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print('登録ユーザー一覧:')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print('')
        print(f'{"ID":<5} {"ユーザー名":<20} {"メールアドレス":<30} {"役割":<10} {"状態":<10}')
        print('-' * 80)

        for user in users:
            user_id, username, email, role, is_active = user
            status = '✅ 有効' if is_active else '❌ 無効'
            print(f'{user_id:<5} {username:<20} {email:<30} {role:<10} {status:<10}')

        print('')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print('')
        print('ログイン方法:')
        print('  ユーザー名: 上記の「ユーザー名」を使用')
        print('  または')
        print('  メールアドレス: 上記の「メールアドレス」を使用')
        print('  パスワード: setup.ps1実行時に設定したパスワード')
        print('')
        print('パスワードを忘れた場合:')
        print('  PS> .\venv\Scripts\python.exe scripts\reset_password.py')

    conn.close()

except Exception as e:
    print(f'❌ エラー: {e}')
    sys.exit(1)
"@

    & $pythonPath -c $pythonScript

} catch {
    Write-Host "❌ エラー: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "💡 トラブルシューティング" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. ユーザーが存在しない場合:" -ForegroundColor White
Write-Host "   PS> cd C:\BackupSystem" -ForegroundColor Gray
Write-Host "   PS> .\venv\Scripts\python.exe scripts\create_admin.py" -ForegroundColor Gray
Write-Host ""
Write-Host "2. パスワードを忘れた場合:" -ForegroundColor White
Write-Host "   PS> cd C:\BackupSystem" -ForegroundColor Gray
Write-Host "   PS> .\venv\Scripts\python.exe scripts\reset_password.py" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 新規管理者を作成する場合:" -ForegroundColor White
Write-Host "   PS> cd C:\BackupSystem" -ForegroundColor Gray
Write-Host "   PS> .\venv\Scripts\python.exe scripts\create_admin.py" -ForegroundColor Gray
Write-Host ""
