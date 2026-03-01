# 🚀 クイックスタートガイド - 本番環境セットアップ

**最終更新**: 2026年1月21日

---

## 📋 事前準備チェックリスト

- [ ] Linux環境（Ubuntu 20.04+推奨）またはWindows 10/11
- [ ] Python 3.11+インストール済み
- [ ] PostgreSQL 15+インストール済み
- [ ] Redis 7.x インストール済み
- [ ] Git インストール済み
- [ ] 管理者権限（sudo/Administrator）

---

## 🎯 5ステップセットアップ（Linux）

### Step 1: プロジェクトのクローン

```bash
cd /mnt/LinuxHDD
git clone <your-repo-url> Backup-Management-System
cd Backup-Management-System
```

### Step 2: Python仮想環境の作成

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: 環境設定ファイルの編集

```bash
# 本番環境設定ファイルをコピー
cp .env.production.example .env.production

# 設定ファイルを編集
nano .env.production

# 以下の項目を必ず変更:
# 1. SECRET_KEY（強力なランダム文字列）
# 2. DATABASE_URL（PostgreSQL接続文字列）
# 3. BASE_URL（実際のIPアドレス）
# 4. メール設定（SMTP情報）
```

**SECRET_KEY生成方法**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### Step 4: SSL証明書の生成

```bash
sudo ./scripts/setup/generate_ssl_cert.sh
# サーバーのIPアドレスを入力: 192.168.1.100
# 組織名を入力: My Company
```

### Step 5: systemdサービスのインストールと起動

```bash
# サービスのインストール
sudo ./scripts/setup/install_systemd_services.sh
# → 選択: 2) 本番環境

# サービスの起動
sudo systemctl start backup-management-production

# 自動起動の有効化
sudo systemctl enable backup-management-production

# 状態確認
sudo systemctl status backup-management-production
```

---

## 🎯 5ステップセットアップ（Windows）

### Step 1: プロジェクトのクローン

```powershell
cd C:\
git clone <your-repo-url> BackupSystem
cd BackupSystem
```

### Step 2: Python仮想環境の作成

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 3: 環境設定ファイルの編集

```powershell
# 本番環境設定ファイルをコピー
copy .env.production.example .env.production

# メモ帳で編集
notepad .env.production

# 以下の項目を必ず変更:
# 1. SECRET_KEY（強力なランダム文字列）
# 2. DATABASE_URL（PostgreSQL接続文字列）
# 3. BASE_URL（実際のIPアドレス）
```

### Step 4: SSL証明書の生成（OpenSSLが必要）

```powershell
# OpenSSLがインストールされている場合
# または、Let's Encryptなどの証明書を使用
```

### Step 5: アプリケーションの起動

```powershell
# 管理者としてPowerShellを実行
.\scripts\Start-Production.ps1

# またはWindowsサービス化（NSSM使用）
# 1. NSSMをインストール: https://nssm.cc/download
# 2. サービス登録:
nssm install BackupManagementSystem C:\BackupSystem\venv\Scripts\python.exe C:\BackupSystem\run.py
nssm start BackupManagementSystem
```

---

## ✅ 動作確認

### 1. Webブラウザでアクセス

```
# HTTPS（推奨）
https://192.168.x.x

# HTTP
http://192.168.x.x:5000
```

### 2. 初回ログイン

デフォルト管理者アカウント:
- **ユーザー名**: `admin`
- **パスワード**: （初回セットアップ時に設定）

### 3. サービス状態の確認（Linux）

```bash
# Webアプリケーション
sudo systemctl status backup-management-production

# Celery Worker
sudo systemctl status celery-worker-prod

# Celery Beat
sudo systemctl status celery-beat-prod

# PostgreSQL
sudo systemctl status postgresql

# Redis
sudo systemctl status redis-server
```

### 4. ログの確認

```bash
# アプリケーションログ
tail -f logs/app_prod.log

# Celeryログ
tail -f logs/celery_worker_prod.log

# systemdログ
sudo journalctl -u backup-management-production -f
```

---

## 🔧 基本操作

### サービスの起動・停止（Linux）

```bash
# 起動
sudo systemctl start backup-management-production

# 停止
sudo systemctl stop backup-management-production

# 再起動
sudo systemctl restart backup-management-production

# 自動起動の有効化
sudo systemctl enable backup-management-production

# 自動起動の無効化
sudo systemctl disable backup-management-production
```

### サービスの起動・停止（Windows）

```powershell
# スクリプト起動（開発・テスト用）
.\scripts\Start-Production.ps1

# Windowsサービス
net start BackupManagementSystem
net stop BackupManagementSystem
```

---

## 📊 監視ダッシュボード

| サービス | URL | 用途 |
|---------|-----|------|
| メインアプリ | https://192.168.x.x | バックアップ管理 |
| Flower | http://localhost:5555 | タスク監視 |
| Grafana | http://localhost:3000 | システム監視 |
| Prometheus | http://localhost:9090 | メトリクス |

---

## 🚨 トラブルシューティング

### アプリケーションが起動しない

```bash
# ログを確認
sudo journalctl -u backup-management-production -n 50

# 設定ファイルを確認
cat .env.production | grep -v '^#'

# データベース接続テスト
psql -h localhost -p 5432 -U backupmgmt -d backup_management_prod
```

### ポート443が使えない

```bash
# ポート使用状況確認
sudo netstat -tlnp | grep :443

# 他のプロセスが使用している場合は停止
sudo systemctl stop nginx  # nginxなど
```

### Celeryタスクが実行されない

```bash
# Redis接続確認
redis-cli ping
# 出力: PONG

# Celery Worker状態確認
sudo systemctl status celery-worker-prod

# Celery Beatログ確認
tail -f logs/celery_beat_prod.log
```

---

## 🔐 セキュリティ設定

### ファイアウォール設定

```bash
# ポート5000を開放（HTTP）
sudo ufw allow 5000/tcp

# ポート443を開放（HTTPS）
sudo ufw allow 443/tcp

# ファイアウォールの有効化
sudo ufw enable
```

### パスワードポリシー

`.env.production`で設定:
```
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
```

---

## 📦 バックアップ

### データベースバックアップ

```bash
# 手動バックアップ
./scripts/backup/postgres_daily_backup.sh

# 自動バックアップ設定（cron）
sudo crontab -e
# 以下を追加:
0 2 * * * /mnt/LinuxHDD/Backup-Management-System/scripts/backup/postgres_daily_backup.sh
```

### アプリケーションファイルのバックアップ

```bash
# プロジェクト全体をバックアップ
tar -czf backup-management-$(date +%Y%m%d).tar.gz /mnt/LinuxHDD/Backup-Management-System
```

---

## 📞 サポート

- **ドキュメント**: `docs/システム開発完全ガイド_Phase14更新版.md`
- **Issues**: GitHub Issuesで報告
- **ログ**: `logs/`ディレクトリ内のログファイルを確認

---

## 🎓 次のステップ

1. ✅ **ユーザー管理**: 管理者以外のユーザーを追加
2. ✅ **バックアップジョブ作成**: 最初のバックアップジョブを設定
3. ✅ **メディア登録**: オフラインメディアを登録
4. ✅ **通知設定**: Email/Teams通知を設定
5. ✅ **レポート確認**: 日次レポートを生成

---

**おめでとうございます! 🎉**

Backup Management Systemの本番環境セットアップが完了しました。

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
