# Windows本番環境 - クイックスタートガイド

**最終更新**: 2025-11-01
**所要時間**: 約30分 | **難易度**: ★☆☆☆☆

---

## 🚀 最速30分でインストール完了

### 前提条件

✅ Python 3.13.7 インストール済み
✅ Git for Windows インストール済み
✅ PowerShell（管理者権限）で実行

---

## 📝 クイックインストール

### PowerShell（管理者）で以下をコピー＆ペースト

```powershell
# === ステップ1-3: クリーンアップ＆最新コード取得 ===
Stop-Service -Name BackupManagementSystem -ErrorAction SilentlyContinue
if (Test-Path "C:\temp\BackupSystem\nssm\nssm.exe") { C:\temp\BackupSystem\nssm\nssm.exe remove BackupManagementSystem confirm }
Remove-Item -Recurse -Force C:\temp\BackupSystem -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force C:\temp\BackupSystem -ErrorAction SilentlyContinue

cd C:\temp
git clone https://github.com/Kensan196948G/backup-management-system.git BackupSystem
cd BackupSystem
git checkout develop

# インストール先は既にC:\temp\BackupSystemです
cd C:\temp\BackupSystem

# === ステップ4: 環境変数設定 ===
Copy-Item .env.example .env
$secretKey = python -c "import secrets; print(secrets.token_hex(32))"
Write-Host "`n=== SECRET_KEY ===" -ForegroundColor Yellow
Write-Host $secretKey -ForegroundColor Cyan
Write-Host "この値をメモして、.envに設定してください`n" -ForegroundColor Yellow

notepad .env
# SECRET_KEY=（上記の値を貼り付け）
# FLASK_ENV=production
# DATABASE_URL=sqlite:///C:/BackupSystem/data/backup_mgmt.db
# 保存して閉じる（Ctrl+S → Alt+F4）

# === ステップ5: 仮想環境とパッケージ ===
python -m venv venv
.\venv\Scripts\pip.exe install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt

# === ステップ6: データベース初期化 ===
mkdir data, logs, reports -Force
.\venv\Scripts\python.exe scripts\fix_database.py
# 対話形式:
#   ユーザー名: admin
#   メール: kensan1969@gmail.com
#   パスワード: Admin123!
#   確認: Admin123!

# === ステップ7-9: サービス化とファイアウォール ===
cd deployment\windows
.\install_service.ps1
.\configure_firewall.ps1
.\verify_installation.ps1

# === ステップ10: ログイン ===
Start-Process "http://192.168.3.92:5000"
# ユーザー名: admin
# パスワード: Admin123!
```

---

## ✅ 成功の確認

### 1. 検証結果

```powershell
.\deployment\windows\verify_installation.ps1
```

**期待される出力**:
```
✅ 検証完了: 27/27 項目成功
✅ すべてのチェックが成功しました！
```

### 2. サービス状態

```powershell
Get-Service -Name BackupManagementSystem
# Status: Running
```

### 3. ブラウザアクセス

- URL: http://192.168.3.92:5000
- ✅ ログイン画面が表示される
- ✅ admin / Admin123! でログイン成功
- ✅ ダッシュボードが表示される

---

## 🔧 トラブルシューティング

### 問題: 400 Bad Request

**原因**: SECRET_KEYが未設定

**対処法**:
```powershell
$secretKey = C:\temp\BackupSystem\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
notepad C:\temp\BackupSystem\.env  # SECRET_KEY=（上記の値を設定）
Restart-Service -Name BackupManagementSystem
```

### 問題: サービスが起動しない

**対処法**:
```powershell
Get-Content C:\temp\BackupSystem\logs\service_stderr.log -Tail 50
C:\temp\BackupSystem\venv\Scripts\python.exe C:\temp\BackupSystem\run.py --production
```

### 問題: ポート5000が使用中

**対処法**:
```powershell
Get-NetTCPConnection -LocalPort 5000 | Select-Object OwningProcess
Stop-Process -Id <PID> -Force
```

---

## 📚 詳細ドキュメント

- **完全版**: [docs/WINDOWS_PRODUCTION_MIGRATION.md](../../docs/WINDOWS_PRODUCTION_MIGRATION.md)
- **README**: [README.md](./README.md)
- **Veeam統合**: [docs/Veeam統合ガイド](../../docs/05_デプロイメント（deployment）/Veeam統合ガイド（veeam-integration）.md)

---

## 🎯 次のステップ

### 1. Veeam統合
```powershell
cd C:\temp\BackupSystem\scripts\powershell
.\veeam_integration.ps1 -Register
```

### 2. メール通知設定
```powershell
notepad C:\temp\BackupSystem\.env
# MAIL_SERVER=smtp.gmail.com
# MAIL_USERNAME=your-email@gmail.com
# MAIL_PASSWORD=your-app-password
Restart-Service -Name BackupManagementSystem
```

### 3. Teams通知設定
```powershell
notepad C:\temp\BackupSystem\.env
# TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxxx
Restart-Service -Name BackupManagementSystem
```

---

### 便利なコマンド

```powershell
# サービス再起動
Restart-Service BackupManagementSystem

# ログ確認
Get-Content C:\temp\BackupSystem\logs\app.log -Tail 50 -Wait

# サービス状態確認
Get-Service BackupManagementSystem

# エラーログ確認
Get-Content C:\temp\BackupSystem\logs\service_stderr.log -Tail 50
```

---

🚀 **30分でインストール完了！**
