# ========================================
# 本番環境起動スクリプト（Windows PowerShell）
# 3-2-1-1-0 Backup Management System
# ========================================

# 管理者権限チェック
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  警告: このスクリプトは管理者権限で実行することを推奨します" -ForegroundColor Yellow
    Write-Host "PowerShellを管理者として実行してください" -ForegroundColor Yellow
}

# エラー時に停止
$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Backup Management System [本番環境] 起動" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# プロジェクトルートディレクトリに移動
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "プロジェクトディレクトリ: $projectRoot" -ForegroundColor Green

# 本番環境の.envファイルを読み込み
if (Test-Path ".env.production") {
    Write-Host "✅ 本番環境設定ファイル (.env.production) を読み込んでいます..." -ForegroundColor Green

    # .envファイルを環境変数として読み込み
    Get-Content ".env.production" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Host "❌ エラー: .env.production が見つかりません" -ForegroundColor Red
    Write-Host "    .env.example.production をコピーして作成してください" -ForegroundColor Red
    exit 1
}

# 重要な設定の検証
$secretKey = $env:SECRET_KEY
if ($secretKey -eq "CHANGE_THIS_TO_STRONG_RANDOM_SECRET_KEY_MIN_50_CHARS") {
    Write-Host "❌ エラー: SECRET_KEYが変更されていません" -ForegroundColor Red
    Write-Host "    .env.production を編集して強力なSECRET_KEYを設定してください" -ForegroundColor Red
    Write-Host "    生成方法: python -c `"import secrets; print(secrets.token_urlsafe(50))`"" -ForegroundColor Yellow
    exit 1
}

# 環境変数の確認
$environment = $env:ENVIRONMENT
$serverPort = $env:SERVER_PORT
$httpsPort = $env:HTTPS_PORT
$useHttps = $env:USE_HTTPS
$serverHost = $env:SERVER_HOST
$debug = $env:DEBUG

Write-Host ""
Write-Host "環境設定:" -ForegroundColor Cyan
Write-Host "  - 環境: $environment"
Write-Host "  - ポート（HTTP）: $serverPort"
Write-Host "  - ポート（HTTPS）: $httpsPort"
Write-Host "  - HTTPS: $useHttps"
Write-Host "  - ホスト: $serverHost"
Write-Host "  - デバッグ: $debug"
Write-Host ""

# SSL証明書の確認（HTTPS使用時）
if ($useHttps -eq "true") {
    Write-Host "SSL証明書を確認しています..." -ForegroundColor Cyan
    $sslCertPath = $env:SSL_CERT_PATH
    $sslKeyPath = $env:SSL_KEY_PATH

    if (-not (Test-Path $sslCertPath)) {
        Write-Host "❌ エラー: SSL証明書が見つかりません: $sslCertPath" -ForegroundColor Red
        Write-Host "    SSL証明書を生成してください" -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path $sslKeyPath)) {
        Write-Host "❌ エラー: SSL秘密鍵が見つかりません: $sslKeyPath" -ForegroundColor Red
        Write-Host "    SSL証明書を生成してください" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ SSL証明書: 確認完了" -ForegroundColor Green
}

# Python仮想環境のアクティベート
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Python仮想環境をアクティベートしています..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1"
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Python仮想環境をアクティベートしています..." -ForegroundColor Green
    & ".venv\Scripts\Activate.ps1"
} else {
    Write-Host "⚠️  警告: Python仮想環境が見つかりません" -ForegroundColor Yellow
}

# 必要なディレクトリの作成
Write-Host "必要なディレクトリを作成しています..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
New-Item -ItemType Directory -Force -Path "reports\prod" | Out-Null
New-Item -ItemType Directory -Force -Path "data" | Out-Null
New-Item -ItemType Directory -Force -Path "C:\BackupSystem\database" | Out-Null

# Redisの起動確認
Write-Host ""
Write-Host "Redisの起動状態を確認しています..." -ForegroundColor Cyan
try {
    $redisTest = redis-cli ping 2>&1
    if ($redisTest -eq "PONG") {
        Write-Host "✅ Redis: 起動中" -ForegroundColor Green
    } else {
        throw "Redis not responding"
    }
} catch {
    Write-Host "❌ エラー: Redisが起動していません" -ForegroundColor Red
    Write-Host "Redisを起動してください" -ForegroundColor Red
    exit 1
}

# PostgreSQLの起動確認
Write-Host ""
Write-Host "PostgreSQLの起動状態を確認しています..." -ForegroundColor Cyan
try {
    $pgTest = pg_isready -h localhost -p 5432 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL: 起動中" -ForegroundColor Green
    } else {
        throw "PostgreSQL not ready"
    }
} catch {
    Write-Host "❌ エラー: PostgreSQLが起動していません" -ForegroundColor Red
    Write-Host "PostgreSQLを起動してください" -ForegroundColor Red
    exit 1
}

# データベースマイグレーションの実行
Write-Host ""
Write-Host "データベースマイグレーションを実行しています..." -ForegroundColor Green
flask db upgrade

# 本番環境ではWindowsサービスとして起動することを推奨
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "⚠️  本番環境では Windows サービスとして起動することを推奨します" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Windows サービスとして起動する方法:" -ForegroundColor Yellow
Write-Host "  1. NSSM (Non-Sucking Service Manager) をインストール" -ForegroundColor Yellow
Write-Host "  2. nssm install BackupManagementSystem" -ForegroundColor Yellow
Write-Host ""
Write-Host "このスクリプトで起動する場合:" -ForegroundColor Yellow
Write-Host "  - 開発・テスト目的のみ" -ForegroundColor Yellow
Write-Host "  - プロセスがフォアグラウンドで実行されます" -ForegroundColor Yellow
Write-Host "  - Ctrl+C で停止できます" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "このまま起動しますか? (Y/N)"
if ($confirmation -ne 'Y' -and $confirmation -ne 'y') {
    Write-Host "起動をキャンセルしました" -ForegroundColor Yellow
    exit 0
}

# Celery Workerの起動（バックグラウンド）
Write-Host ""
Write-Host "Celery Workerを起動しています..." -ForegroundColor Green
Start-Process -FilePath "celery" -ArgumentList "-A", "celery_worker.celery", "worker", "--loglevel=info", "--logfile=logs\celery_worker_prod.log" -WindowStyle Hidden

# Celery Beatの起動（バックグラウンド）
Write-Host "Celery Beatを起動しています..." -ForegroundColor Green
Start-Process -FilePath "celery" -ArgumentList "-A", "celery_worker.celery", "beat", "--loglevel=info", "--logfile=logs\celery_beat_prod.log" -WindowStyle Hidden

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✅ バックグラウンドサービスの起動完了" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Flaskアプリケーションの起動
Write-Host "Flaskアプリケーションを起動しています..." -ForegroundColor Green
Write-Host ""
if ($useHttps -eq "true") {
    Write-Host "アクセスURL: https://localhost:$httpsPort" -ForegroundColor Yellow
    Write-Host "ブックマーク: [本番] https://YOUR_IP_ADDRESS" -ForegroundColor Yellow
} else {
    Write-Host "アクセスURL: http://localhost:$serverPort" -ForegroundColor Yellow
    Write-Host "ブックマーク: [本番] http://YOUR_IP_ADDRESS:$serverPort" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "停止方法: Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# Waitressを使用した本番環境での起動（推奨）
try {
    $waitressCheck = python -c "import waitress" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Waitressで起動しています..." -ForegroundColor Green
        if ($useHttps -eq "true") {
            python -c "from waitress import serve; from app import create_app; serve(create_app(), host='0.0.0.0', port=$httpsPort, url_scheme='https')"
        } else {
            python -c "from waitress import serve; from app import create_app; serve(create_app(), host='0.0.0.0', port=$serverPort)"
        }
    } else {
        throw "Waitress not installed"
    }
} catch {
    Write-Host "⚠️  警告: Waitressがインストールされていません" -ForegroundColor Yellow
    Write-Host "    本番環境ではWaitressの使用を推奨します" -ForegroundColor Yellow
    Write-Host "    インストール: pip install waitress" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Flaskの開発サーバーで起動しています..." -ForegroundColor Yellow
    python run.py
} finally {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "本番環境を停止しています..." -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan

    # Celeryプロセスの停止
    Write-Host "Celery Workerを停止しています..." -ForegroundColor Green
    Get-Process | Where-Object {$_.ProcessName -like "*celery*"} | Stop-Process -Force

    Write-Host ""
    Write-Host "✅ すべてのプロセスを停止しました" -ForegroundColor Green
    Write-Host ""
}
