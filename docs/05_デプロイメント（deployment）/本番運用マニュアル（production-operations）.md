# 本番運用マニュアル

バックアップ管理システムの本番環境における日常的な運用手順書です。

## 目次

1. [サービス管理](#サービス管理)
2. [ログ確認と分析](#ログ確認と分析)
3. [アプリケーションバックアップ](#アプリケーションバックアップ)
4. [障害対応フロー](#障害対応フロー)
5. [定期メンテナンス](#定期メンテナンス)
6. [セキュリティアップデート](#セキュリティアップデート)
7. [パフォーマンス監視](#パフォーマンス監視)
8. [ユーザーサポート](#ユーザーサポート)

---

## サービス管理

### Linuxでのサービス操作

#### サービスの起動

```bash
# 通常起動
sudo systemctl start backup-management.service
sudo systemctl start nginx

# サービスの自動起動有効化
sudo systemctl enable backup-management.service
sudo systemctl enable nginx
```

#### サービスの停止

```bash
# グレースフルシャットダウン（接続完了を待つ）
sudo systemctl stop backup-management.service
sudo systemctl stop nginx

# 強制停止（危険）
sudo systemctl kill -9 backup-management.service
```

#### サービスの再起動

```bash
# 通常再起動
sudo systemctl restart backup-management.service

# リロード（設定ファイル変更時）
sudo systemctl reload backup-management.service

# ステータス確認
sudo systemctl status backup-management.service
```

#### サービス起動状態の確認

```bash
# 詳細ステータス
systemctl status backup-management.service

# 起動に要した時間
systemctl status backup-management.service | grep "Active:"

# 自動起動設定の確認
systemctl is-enabled backup-management.service
```

### Windowsでのサービス操作

#### 管理者権限でコマンドプロンプトを開く

```
右クリック → 管理者として実行
```

#### サービスの起動

```cmd
net start BackupManagementSystem
net start Nginx

REM ステータス確認
sc query BackupManagementSystem
```

#### サービスの停止

```cmd
net stop BackupManagementSystem
net stop Nginx
```

#### サービスの再起動

```cmd
net stop BackupManagementSystem
timeout /t 3
net start BackupManagementSystem
```

#### サービス管理UI

```cmd
REM Windows サービス管理画面を開く
services.msc

REM またはタスクマネージャから操作
taskmgr
```

---

## ログ確認と分析

### Linuxでのログ確認

#### アプリケーションログ（systemd）

```bash
# 最新50行の表示
sudo journalctl -u backup-management.service -n 50

# リアルタイム監視（tail -f 相当）
sudo journalctl -u backup-management.service -f

# 特定の日時以降のログ
sudo journalctl -u backup-management.service --since "2024-01-15 09:00:00"

# エラーレベルのみ抽出
sudo journalctl -u backup-management.service -p err

# JSONフォーマットで出力
sudo journalctl -u backup-management.service -o json | jq .
```

#### Nginxログ

```bash
# アクセスログ（最新行）
sudo tail -50 /var/log/nginx/access.log

# エラーログ
sudo tail -50 /var/log/nginx/error.log

# リアルタイム監視
sudo tail -f /var/log/nginx/access.log

# 特定のステータスコードを抽出
sudo grep " 500 " /var/log/nginx/access.log
sudo grep " 404 " /var/log/nginx/access.log

# IPアドレスごとのアクセス数
sudo awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# レスポンスタイム分析
sudo awk '{print $NF}' /var/log/nginx/access.log | sort -n | tail -10
```

#### アプリケーション固有ログ

```bash
# ログディレクトリの確認
ls -lh /var/log/backup-mgmt/

# ログファイルのサイズ確認
du -sh /var/log/backup-mgmt/*

# 特定キーワードの検索
grep "Error" /var/log/backup-mgmt/app.log
grep "WARNING" /var/log/backup-mgmt/app.log

# ログのフォローと検索を同時に実行
tail -f /var/log/backup-mgmt/app.log | grep --line-buffered "ERROR"
```

### Windowsでのログ確認

#### アプリケーションログ

```cmd
REM ログファイルの確認
type "C:\ProgramData\BackupManagementSystem\logs\app.log"

REM 最新行を表示（最後の20行）
powershell -Command "Get-Content 'C:\ProgramData\BackupManagementSystem\logs\app.log' -Tail 20"

REM リアルタイム監視
powershell -Command "Get-Content 'C:\ProgramData\BackupManagementSystem\logs\app.log' -Tail 0 -Wait"

REM エラーを含む行を抽出
findstr /C:"Error" "C:\ProgramData\BackupManagementSystem\logs\app.log"
```

#### イベントビューアー

```cmd
REM イベントビューアーを開く
eventvwr.msc

REM コマンドラインで確認
wevtutil qe System /c:20 /rd:true /f:text
```

### ログ分析の例

#### レスポンスタイムの分析

**Linux:**
```bash
# レスポンスタイムの統計
awk '{print $NF}' /var/log/nginx/access.log | \
    awk '{sum+=$1; sumsq+=$1*$1; count++} \
    END {print "平均:", sum/count, "標準偏差:", sqrt(sumsq/count - (sum/count)^2)}'
```

#### エラー率の計算

```bash
# 総アクセス数
TOTAL=$(wc -l /var/log/nginx/access.log | awk '{print $1}')

# エラー数（5xx）
ERRORS=$(grep " 5[0-9][0-9] " /var/log/nginx/access.log | wc -l)

# エラー率
ERROR_RATE=$((ERRORS * 100 / TOTAL))
echo "エラー率: $ERROR_RATE%"
```

#### 時間別のアクセストレンド

```bash
# 1時間ごとのアクセス数
awk '{print substr($4, 2, 11)}' /var/log/nginx/access.log | sort | uniq -c
```

---

## アプリケーションバックアップ

### バックアップ対象

1. **アプリケーション本体**
   - `/opt/backup-management-system` (Linux)
   - `C:\Program Files\BackupManagementSystem` (Windows)

2. **データベース**
   - `/var/lib/backup-mgmt/backup_mgmt.db` (Linux)
   - `C:\ProgramData\BackupManagementSystem\data\backup_mgmt.db` (Windows)

3. **設定ファイル**
   - `.env` ファイル
   - `/etc/nginx/sites-available/backup-management` (Linux)

4. **ログとデータ**
   - `/var/log/backup-mgmt/*` (Linux)
   - `C:\ProgramData\BackupManagementSystem\logs\*` (Windows)

### 手動バックアップ

#### Linuxでの手動バックアップ

```bash
# バックアップディレクトリの作成
mkdir -p /backup/application-backups
cd /backup/application-backups

# 日時付きバックアップの作成
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)

# アプリケーション全体のバックアップ
sudo tar -czf backup-mgmt-app-$BACKUP_DATE.tar.gz \
    /opt/backup-management-system \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude=.pytest_cache

# データベースのバックアップ
sudo cp /var/lib/backup-mgmt/backup_mgmt.db \
    backup_mgmt-$BACKUP_DATE.db

# 設定ファイルのバックアップ
sudo tar -czf backup-mgmt-config-$BACKUP_DATE.tar.gz \
    /opt/backup-management-system/.env \
    /etc/nginx/sites-available/backup-management \
    /etc/systemd/system/backup-management.service

# バックアップファイルの所有権変更
sudo chown $USER:$USER backup-mgmt-*

# バックアップリストの表示
ls -lh backup-mgmt-*
```

#### Windowsでの手動バックアップ

```cmd
REM バックアップディレクトリの作成
mkdir C:\Backups\BackupMgmt

REM 日時の取得
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)

REM アプリケーションディレクトリのコピー
xcopy "C:\Program Files\BackupManagementSystem" "C:\Backups\BackupMgmt\app-%mydate%_%mytime%" /E /I

REM データベースのコピー
copy "C:\ProgramData\BackupManagementSystem\data\backup_mgmt.db" "C:\Backups\BackupMgmt\backup_mgmt-%mydate%_%mytime%.db"

REM 設定ファイルのコピー
copy "C:\Program Files\BackupManagementSystem\.env" "C:\Backups\BackupMgmt\.env-%mydate%_%mytime%"
```

### 自動バックアップスクリプト

#### Linux（cronジョブ）

**ファイル: `/etc/cron.d/backup-mgmt-backup`**

```bash
# 毎日午前2時にバックアップ実行
0 2 * * * root /usr/local/bin/backup-mgmt-backup.sh

# 毎週日曜日に完全バックアップ
0 3 * * 0 root /usr/local/bin/backup-mgmt-full-backup.sh
```

**バックアップスクリプト: `/usr/local/bin/backup-mgmt-backup.sh`**

```bash
#!/bin/bash

set -e

BACKUP_DIR="/backup/application-backups"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# ディレクトリの作成
mkdir -p "$BACKUP_DIR"

# バックアップの実行
sudo tar -czf "$BACKUP_DIR/backup-mgmt-app-$BACKUP_DATE.tar.gz" \
    /opt/backup-management-system \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude=.pytest_cache 2>/dev/null || true

sudo cp /var/lib/backup-mgmt/backup_mgmt.db \
    "$BACKUP_DIR/backup_mgmt-$BACKUP_DATE.db"

# 古いバックアップの削除
find "$BACKUP_DIR" -name "backup-mgmt-app-*.tar.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "backup_mgmt-*.db" -mtime +$RETENTION_DAYS -delete

# ログ出力
echo "Backup completed: $BACKUP_DATE" >> /var/log/backup-mgmt/backup.log

# メール通知（オプション）
# echo "Backup completed successfully" | mail -s "Backup Notification" admin@example.com
```

**実行権限の設定:**

```bash
sudo chmod 755 /usr/local/bin/backup-mgmt-backup.sh
sudo chmod 755 /usr/local/bin/backup-mgmt-full-backup.sh
```

#### Windows（タスクスケジューラ）

1. タスクスケジューラを開く: `taskschd.msc`
2. 「タスクの作成」をクリック
3. 以下を設定:
   - **トリガー**: 毎日午前2時
   - **アクション**: バッチファイルを実行
   - **ファイル**: `C:\Scripts\backup-mgmt.bat`

**バックアップスクリプト: `C:\Scripts\backup-mgmt.bat`**

```batch
@echo off

REM 日時の取得
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)

REM バックアップディレクトリ
set BACKUP_DIR=C:\Backups\BackupMgmt
mkdir "%BACKUP_DIR%" 2>nul

REM バックアップ実行
7z a -r -y "%BACKUP_DIR%\backup-mgmt-%mydate%_%mytime%.7z" ^
    "C:\Program Files\BackupManagementSystem" ^
    -xr!venv -xr!__pycache__ -xr!.pytest_cache

copy "C:\ProgramData\BackupManagementSystem\data\backup_mgmt.db" ^
    "%BACKUP_DIR%\backup_mgmt-%mydate%_%mytime%.db"

REM ログ出力
echo %date% %time% Backup completed >> C:\Backups\backup.log
```

### バックアップ検証

```bash
# バックアップファイルの整合性確認
tar -tzf /backup/application-backups/backup-mgmt-app-*.tar.gz > /dev/null && echo "OK" || echo "FAILED"

# 圧縮ファイルのサイズ確認
du -sh /backup/application-backups/*

# バックアップディレクトリ容量の確認
df -h /backup/
```

---

## 障害対応フロー

### 障害検知

#### 障害の検知方法

1. **自動監視**
   - systemd による自動再起動
   - Nginxのヘルスチェック
   - ログ監視ツール

2. **手動確認**
   ```bash
   curl http://localhost/health
   systemctl status backup-management.service
   ```

3. **アラート**
   - ログアグリゲーション（ELK Stackなど）
   - メール通知
   - Slack 通知

### 障害対応フローチャート

```
┌─────────────────────────────────────┐
│        障害の報告・検知             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   ステップ1: サービス確認           │
│   systemctl status ...              │
│   curl http://localhost/health      │
└────────────┬────────────────────────┘
             │
             ├─────────────┬─────────────┐
             │             │             │
        サービス起動    サービス停止   メモリ不足
             │             │             │
             ▼             ▼             ▼
        通常運用      障害対応      資源確保
                    ステップ2       メモリ解放
                                        │
                                        ▼
                                  サービス再起動
                                        │
                                        ▼
                                    動作確認
                                        │
                         ┌──────────────┴──────────────┐
                         │                             │
                       成功                           失敗
                         │                             │
                         ▼                             ▼
                      完了                          ロールバック
                                                        │
                                                        ▼
                                                   前バージョン復元
```

### 対応手順

#### ステップ1: 現状把握（5分以内）

```bash
# サービスステータス確認
sudo systemctl status backup-management.service
sudo systemctl status nginx

# ログの確認
sudo journalctl -u backup-management.service -n 50

# リソース使用状況
free -h
df -h
ps aux --sort=-%mem | head -n 5
```

#### ステップ2: 初期対応（5-15分）

```bash
# サービスの再起動
sudo systemctl restart backup-management.service

# Nginxの再起動
sudo systemctl restart nginx

# 接続テスト
curl -I http://localhost/
```

#### ステップ3: 詳細分析（15-30分）

```bash
# Nginxエラーログの確認
sudo tail -100 /var/log/nginx/error.log

# アプリケーションログの詳細確認
sudo journalctl -u backup-management.service --since "30 min ago"

# データベース接続テスト
python3 << EOF
import sqlite3
db = sqlite3.connect('/var/lib/backup-mgmt/backup_mgmt.db')
cursor = db.cursor()
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
print("テーブル数:", cursor.fetchone()[0])
db.close()
EOF
```

#### ステップ4: 必要に応じた対応

**メモリ不足の場合:**
```bash
# キャッシュのクリア
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# 不要なプロセスの停止
sudo systemctl stop <service-name>
```

**ディスク容量不足の場合:**
```bash
# 古いログファイルの削除
sudo find /var/log/backup-mgmt -type f -mtime +7 -delete

# 一時ファイルの削除
sudo rm -rf /tmp/*
```

**ポート競合の場合:**
```bash
# 使用中のプロセスを確認
sudo lsof -i :5000

# プロセスを終了（必要に応じて）
sudo kill -9 <PID>

# サービス再起動
sudo systemctl restart backup-management.service
```

#### ステップ5: 復旧確認

```bash
# 複数回の動作テスト
for i in {1..3}; do
    curl -s http://localhost/ > /dev/null && echo "OK: $i" || echo "FAILED: $i"
    sleep 5
done

# ログエラーの監視
sudo journalctl -u backup-management.service -f &

# 15分間の監視
sleep 900
```

### ロールバック判定基準

以下の場合は即座にロールバックを実行:

1. 再起動後も 5分以内に再び障害
2. データベースの破損が疑われる
3. セキュリティ侵害の可能性
4. 本番環境での重大なデータ損失

---

## 定期メンテナンス

### 日次チェック（毎日実施）

#### 朝礼チェック（開業時）

```bash
#!/bin/bash
echo "=== 日次メンテナンスチェック ===" 
echo "実行時刻: $(date)"
echo ""

# 1. サービス確認
echo "1. サービスステータス"
systemctl status backup-management.service --no-pager | grep -E "Active|loaded"

# 2. ディスク容量
echo ""
echo "2. ディスク容量"
df -h / | tail -1

# 3. メモリ使用率
echo ""
echo "3. メモリ使用率"
free -h | grep Mem

# 4. ログエラー
echo ""
echo "4. エラーログ（過去1時間）"
journalctl -u backup-management.service --since "1 hour ago" -p err

# 5. 接続テスト
echo ""
echo "5. 接続テスト"
curl -s http://localhost/health > /dev/null && echo "Web Service: OK" || echo "Web Service: FAILED"
```

### 週次メンテナンス（毎週月曜日）

```bash
#!/bin/bash
echo "=== 週次メンテナンス ===" 
echo "実行時刻: $(date)"

# 1. ログローテーション確認
echo "1. ログファイルサイズ"
du -sh /var/log/backup-mgmt/*

# 2. バックアップ実行状況
echo ""
echo "2. バックアップ実行状況"
ls -lh /backup/application-backups/ | tail -5

# 3. データベース最適化
echo ""
echo "3. データベース最適化"
sqlite3 /var/lib/backup-mgmt/backup_mgmt.db "VACUUM;"
sqlite3 /var/lib/backup-mgmt/backup_mgmt.db "ANALYZE;"

# 4. ログ統計
echo ""
echo "4. アクセスログ統計"
echo "総リクエスト数: $(wc -l < /var/log/nginx/access.log)"
echo "エラー数(5xx): $(grep -c " 5[0-9][0-9] " /var/log/nginx/access.log)"
echo "エラー数(4xx): $(grep -c " 4[0-9][0-9] " /var/log/nginx/access.log)"

# 5. ディスク使用量トレンド
echo ""
echo "5. データベースサイズ"
ls -lh /var/lib/backup-mgmt/backup_mgmt.db
```

### 月次メンテナンス（毎月最初の平日）

#### セキュリティアップデートの確認

**Linux:**
```bash
# セキュリティアップデート確認
apt list --upgradable 2>/dev/null | grep "upgradable"

# またはセキュリティに特化したツール
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### 依存ライブラリの更新確認

```bash
# 現在のバージョン確認
pip list --outdated

# 更新可能なライブラリの確認
pip index versions flask

# 安全な更新（テスト環境で先に実施）
pip install --upgrade <package-name>
```

#### パフォーマンス分析

```bash
# Nginxのリクエスト分析
awk '{print $NF}' /var/log/nginx/access.log | \
    awk '{sum+=$1; sumsq+=$1*$1; count++} \
    END {printf "平均レスポンスタイム: %.2f秒\n", sum/count}'

# CPU/メモリのピーク確認
ps aux --sort=-%cpu | head -5
ps aux --sort=-%mem | head -5
```

#### ユーザーアクティビティレポート

```bash
# アクセス数の多いエンドポイント
awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# クライアント IP 統計
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# エラーの多いエンドポイント
grep " [45][0-9][0-9] " /var/log/nginx/access.log | awk '{print $7}' | sort | uniq -c | sort -rn
```

---

## セキュリティアップデート

### アップデート前チェック

```bash
# 1. バックアップ実施
sudo tar -czf /backup/pre-update-backup-$(date +%Y%m%d).tar.gz \
    /opt/backup-management-system \
    /var/lib/backup-mgmt/

# 2. 現在の状態を記録
systemctl status backup-management.service > /tmp/status-before.log

# 3. ディスク空き容量確認
df -h / | grep -v "Filesystem"
```

### アップデート手順

#### Pythonパッケージのアップデート

```bash
# 1. サービス停止
sudo systemctl stop backup-management.service

# 2. 仮想環境の更新
source /opt/backup-management-system/venv/bin/activate
pip install --upgrade pip setuptools wheel

# 3. 依存ライブラリのアップデート
pip install -r /opt/backup-management-system/requirements.txt --upgrade

# 4. 変更内容の確認
pip list | grep -E "flask|sqlalchemy|werkzeug"

# 5. サービス再起動
sudo systemctl start backup-management.service
```

#### OSパッケージのアップデート

```bash
# セキュリティアップデートのみ実施
sudo apt-get update
sudo apt-get install -y --only-upgrade <package-name>

# または、自動セキュリティアップデート設定
sudo apt install -y unattended-upgrades
sudo systemctl restart unattended-upgrades.service
```

### アップデート後確認

```bash
# 1. サービス確認
systemctl status backup-management.service

# 2. ログエラー確認
journalctl -u backup-management.service --since "10 min ago" -p err

# 3. 動作テスト
curl -s http://localhost/ > /dev/null && echo "OK" || echo "FAILED"

# 4. パフォーマンス確認
curl -w "@curl-format.txt" -o /dev/null http://localhost/

# 5. ロールバック計画の確認
ls -lh /backup/pre-update-backup-*
```

---

## パフォーマンス監視

### リアルタイムモニタリング

#### システムリソース監視

```bash
# top: CPU/メモリの監視
top -u backup-mgmt

# htop: より詳細な表示
htop -u backup-mgmt

# iostat: ディスク I/O の監視
iostat -x 1 5

# sar: 過去のパフォーマンス データ確認
sar -u | tail -10
```

#### アプリケーション監視

```bash
# Flask アプリケーションプロセスの確認
ps aux | grep "[p]ython.*app"

# メモリリークの確認（メモリ使用量の増加傾向）
while true; do
    date
    ps aux | grep "[p]ython.*app" | awk '{print $6 " KB"}'
    sleep 60
done
```

### メトリクス収集

#### Prometheus 統合（オプション）

Flask アプリケーションに Prometheus メトリクスを追加:

```python
# app/__init__.py に追加
from prometheus_client import Counter, Histogram, generate_latest
import time

# メトリクス定義
REQUEST_COUNT = Counter('app_request_total', 'Total requests')
REQUEST_DURATION = Histogram('app_request_duration_seconds', 'Request duration')
ERROR_COUNT = Counter('app_errors_total', 'Total errors')

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time
    REQUEST_COUNT.inc()
    REQUEST_DURATION.observe(duration)
    return response

@app.route('/metrics')
def metrics():
    return generate_latest()
```

### ログベースの監視

#### ログの自動分析

```bash
#!/bin/bash
# スクリプト: analyze_logs.sh

LOG_FILE="/var/log/nginx/access.log"
HOUR_AGO=$(date -d "1 hour ago" +"%d/%b/%Y:%H:%M" | cut -d: -f1,2)

echo "=== 過去1時間のログ分析 ==="

# 1. リクエスト数
echo "総リクエスト数: $(grep "$HOUR_AGO" $LOG_FILE | wc -l)"

# 2. エラー率
ERRORS=$(grep "$HOUR_AGO" $LOG_FILE | grep " [45][0-9][0-9] " | wc -l)
TOTAL=$(grep "$HOUR_AGO" $LOG_FILE | wc -l)
echo "エラー率: $((ERRORS * 100 / TOTAL))%"

# 3. 平均レスポンスタイム
grep "$HOUR_AGO" $LOG_FILE | awk '{print $NF}' | \
    awk '{sum+=$1; count++} END {printf "平均: %.2f秒\n", sum/count}'

# 4. 最大レスポンスタイム
grep "$HOUR_AGO" $LOG_FILE | awk '{print $NF}' | sort -n | tail -1 | \
    awk '{printf "最大: %.2f秒\n", $1}'
```

実行:
```bash
chmod +x /usr/local/bin/analyze_logs.sh
/usr/local/bin/analyze_logs.sh
```

---

## ユーザーサポート

### よくある質問（FAQ）

#### Q1: ログインできない

**A:**
```bash
# 1. ユーザーアカウント確認
sqlite3 /var/lib/backup-mgmt/backup_mgmt.db "SELECT username, email FROM user LIMIT 5;"

# 2. パスワードリセット（管理者用）
python3 << EOF
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='admin').first()
    if user:
        user.set_password('new_password')
        db.session.commit()
        print("パスワードをリセットしました")
EOF
```

#### Q2: ジョブが完了しない

**A:**
```bash
# 1. バックエンドサービスの確認
systemctl status backup-management.service

# 2. ログでエラーを確認
journalctl -u backup-management.service | grep "ERROR"

# 3. ディスク空き容量の確認
df -h /

# 4. データベース接続テスト
sqlite3 /var/lib/backup-mgmt/backup_mgmt.db "PRAGMA integrity_check;"
```

#### Q3: 古いデータを削除したい

**A:**
```bash
# 1. バックアップ実施（重要）
sudo tar -czf /backup/before-delete-$(date +%Y%m%d).tar.gz \
    /var/lib/backup-mgmt/backup_mgmt.db

# 2. 古いレコード削除
sqlite3 /var/lib/backup-mgmt/backup_mgmt.db << EOF
-- 30日以上前の履歴を削除
DELETE FROM backup_history WHERE created_at < datetime('now', '-30 days');

-- 対応を確認
SELECT COUNT(*) FROM backup_history;
EOF
```

### ユーザー管理

#### ユーザーの追加

```python
python3 << EOF
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # 新規ユーザー作成
    user = User(
        username='newuser',
        email='user@example.com'
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    print(f"ユーザーを作成しました: {user.username}")
EOF
```

#### ユーザーの削除

```python
python3 << EOF
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='olduser').first()
    if user:
        db.session.delete(user)
        db.session.commit()
        print("ユーザーを削除しました")
EOF
```

#### ユーザーのロール変更

```python
python3 << EOF
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='targetuser').first()
    if user:
        user.role = 'admin'  # または 'user'
        db.session.commit()
        print(f"ユーザーロールを変更しました: {user.role}")
EOF
```

### トラブルシューティングウィザード

**問題**: アプリケーションが応答しない
**対応**:
1. サービスステータス確認: `systemctl status backup-management.service`
2. ログ確認: `journalctl -u backup-management.service -n 50`
3. サービス再起動: `systemctl restart backup-management.service`
4. メモリ確認: `free -h`
5. ディスク確認: `df -h`

---

## 連絡先と支援

- **技術サポート**: support@example.com
- **緊急時**: +81-XX-XXXX-XXXX
- **ドキュメント**: 本リポジトリの docs/ ディレクトリ

---

**最終更新**: 2024年1月
**バージョン**: 1.0
