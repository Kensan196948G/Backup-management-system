# ========================================
# 開発環境起動スクリプト（Windows PowerShell）
# 3-2-1-1-0 Backup Management System
# ========================================

# エラー時に停止
$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Backup Management System [開発環境] 起動" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# プロジェクトルートディレクトリに移動
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "プロジェクトディレクトリ: $projectRoot" -ForegroundColor Green

# 開発環境の.envファイルを読み込み
if (Test-Path ".env.development") {
    Write-Host "✅ 開発環境設定ファイル (.env.development) を読み込んでいます..." -ForegroundColor Green

    # .envファイルを環境変数として読み込み
    Get-Content ".env.development" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Host "⚠️  警告: .env.development が見つかりません" -ForegroundColor Yellow
    Write-Host "    .env.example.development をコピーして作成してください" -ForegroundColor Yellow
    exit 1
}

# 環境変数の確認
$environment = $env:ENVIRONMENT
$serverPort = $env:SERVER_PORT
$serverHost = $env:SERVER_HOST
$debug = $env:DEBUG

Write-Host ""
Write-Host "環境設定:" -ForegroundColor Cyan
Write-Host "  - 環境: $environment"
Write-Host "  - ポート: $serverPort"
Write-Host "  - ホスト: $serverHost"
Write-Host "  - デバッグ: $debug"
Write-Host ""

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
New-Item -ItemType Directory -Force -Path "reports\dev" | Out-Null
New-Item -ItemType Directory -Force -Path "data" | Out-Null

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
    Write-Host "⚠️  Redis: 停止中" -ForegroundColor Yellow
    Write-Host "Redisを起動してください" -ForegroundColor Yellow
    Write-Host "  - Windows: redis-server を実行" -ForegroundColor Yellow
    Write-Host "  - または WSL: sudo service redis-server start" -ForegroundColor Yellow
}

# PostgreSQLの起動確認
Write-Host ""
Write-Host "PostgreSQLの起動状態を確認しています..." -ForegroundColor Cyan
try {
    $pgTest = pg_isready -h localhost -p 5434 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL: 起動中" -ForegroundColor Green
    } else {
        throw "PostgreSQL not ready"
    }
} catch {
    Write-Host "⚠️  PostgreSQL: 停止中" -ForegroundColor Yellow
    Write-Host "PostgreSQLを起動してください" -ForegroundColor Yellow
}

# Celery Workerの起動（バックグラウンド）
Write-Host ""
Write-Host "Celery Workerを起動しています..." -ForegroundColor Green
Start-Process -FilePath "celery" -ArgumentList "-A", "celery_worker.celery", "worker", "--loglevel=info", "--logfile=logs\celery_worker_dev.log" -WindowStyle Hidden

# Celery Beatの起動（バックグラウンド）
Write-Host "Celery Beatを起動しています..." -ForegroundColor Green
Start-Process -FilePath "celery" -ArgumentList "-A", "celery_worker.celery", "beat", "--loglevel=info", "--logfile=logs\celery_beat_dev.log" -WindowStyle Hidden

# Flowerの起動（オプション - タスク監視UI）
Write-Host "Flower（タスク監視UI）を起動しています..." -ForegroundColor Green
Start-Process -FilePath "celery" -ArgumentList "-A", "celery_worker.celery", "flower", "--port=5555", "--loglevel=info" -WindowStyle Hidden -RedirectStandardOutput "logs\flower_dev.log" -RedirectStandardError "logs\flower_dev_error.log"
Write-Host "✅ Flower UI: http://localhost:5555" -ForegroundColor Green

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✅ バックグラウンドサービスの起動完了" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Flaskアプリケーションの起動
Write-Host "Flaskアプリケーションを起動しています..." -ForegroundColor Green
Write-Host ""
Write-Host "アクセスURL: http://localhost:$serverPort" -ForegroundColor Yellow
Write-Host "ブックマーク: [開発] http://localhost:$serverPort" -ForegroundColor Yellow
Write-Host ""
Write-Host "停止方法: Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# Flaskアプリケーションの起動（フォアグラウンド）
try {
    python run.py
} finally {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "開発環境を停止しています..." -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan

    # Celeryプロセスの停止
    Write-Host "Celery Workerを停止しています..." -ForegroundColor Green
    Get-Process | Where-Object {$_.ProcessName -like "*celery*"} | Stop-Process -Force

    Write-Host "Flowerを停止しています..." -ForegroundColor Green
    Get-Process | Where-Object {$_.CommandLine -like "*flower*"} | Stop-Process -Force

    Write-Host ""
    Write-Host "✅ すべてのプロセスを停止しました" -ForegroundColor Green
    Write-Host ""
}
