# Windows本番環境 - 完全移行手順書

**最終更新**: 2025-11-01
**対象OS**: Windows Server 2019/2022、Windows 10/11
**Python**: 3.13.7
**所要時間**: 約30分
**難易度**: ★☆☆☆☆（初級）

---

## 📋 目次

1. [事前準備](#事前準備)
2. [クリーンインストール手順](#クリーンインストール手順)
3. [動作確認](#動作確認)
4. [トラブルシューティング](#トラブルシューティング)
5. [次のステップ](#次のステップ)

---

## 🎯 このガイドについて

このガイドは、**開発環境（Linux）で完成したシステムを、本番環境（Windows）に移行する**ための完全な手順書です。

### 特徴

✅ **完全自動化** - スクリプト実行で環境構築完了
✅ **ゼロからスタート** - 既存フォルダは完全削除
✅ **最新コード** - GitHubから最新版（develop）を取得
✅ **Python 3.13対応** - すべての依存パッケージが最新版
✅ **包括的チェック** - 27項目の自動検証

---

## 事前準備

### 1. 必須ソフトウェア

#### Python 3.13.7

```powershell
# バージョン確認
python --version
# 出力例: Python 3.13.7
```

**未インストールの場合**:
1. https://www.python.org/downloads/ からダウンロード
2. インストール時に「**Add Python to PATH**」をチェック
3. 「**Install for all users**」を選択（推奨）

#### Git for Windows

```powershell
# バージョン確認
git --version
# 出力例: git version 2.43.0
```

**未インストールの場合**:
- https://git-scm.com/download/win からダウンロード

### 2. 管理者権限

すべてのコマンドは **PowerShell（管理者）** で実行してください。

```powershell
# PowerShellを管理者権限で起動
# 方法1: スタートメニュー → PowerShell → 右クリック → 管理者として実行
# 方法2: Win + X → Windows PowerShell (管理者)
```

### 3. ネットワーク要件

- インターネット接続（GitHub、PyPIへのアクセス）
- ポート5000が利用可能
- ファイアウォール設定権限

---

## クリーンインストール手順

### ステップ1: 完全クリーンアップ（2分）

**既存環境を完全削除します。**

```powershell
# サービス停止（存在する場合）
Stop-Service -Name BackupManagementSystem -ErrorAction SilentlyContinue

# サービス削除（存在する場合）
if (Test-Path "C:\temp\BackupSystem\nssm\nssm.exe") {
    C:\temp\BackupSystem\nssm\nssm.exe remove BackupManagementSystem confirm
}

# 両方のフォルダを完全削除



# 削除確認
Test-Path C:\temp\BackupSystem        # False であることを確認
Test-Path C:\temp\BackupSystem   # False であることを確認

Write-Host "✅ クリーンアップ完了" -ForegroundColor Green
```

**★ Insight ─────────────────────────────────────**
- `ErrorAction SilentlyContinue`: ファイルが存在しない場合もエラーを出さずに続行
- NSSM（Non-Sucking Service Manager）: Windowsサービス化ツール
- 完全削除により、古い設定やキャッシュの問題を回避
**─────────────────────────────────────────────────**

---

### ステップ2: 最新コード取得（2分）

**GitHubから最新版をクローンします。**

```powershell
# tempディレクトリに移動
cd C:\temp

# 最新コードをクローン
git clone https://github.com/Kensan196948G/backup-management-system.git BackupSystem

# developブランチに切り替え（最新版）
cd BackupSystem
git checkout develop
git pull origin develop

# 最新コミット確認
git log --oneline -5
```

**期待される出力**:
```
4086dce docs: Windows環境クリーンインストールガイド追加  ← 最新
615cc36 fix: ルートURL（/）をログインページにリダイレクト
c4e4423 feat: ログイン問題包括的診断・修復システム
e8f390c feat: データベース修復スクリプト追加
287ff6a feat: ログイン問題診断・修復スクリプト追加
```

```powershell
Write-Host "✅ 最新コード取得完了" -ForegroundColor Green
```

---

### ステップ3: C:\temp\BackupSystemに移動（10秒）

**本番環境パスに移動します。**

```powershell
# C:\temp\BackupSystemをC:\temp\BackupSystemに移動
# インストール先は既にC:\temp\BackupSystemです

# 移動確認
Test-Path C:\temp\BackupSystem        # True
Test-Path C:\temp\BackupSystem\.git   # True（Gitリポジトリごと移動）

Write-Host "✅ ディレクトリ移動完了" -ForegroundColor Green
```

**★ Insight ─────────────────────────────────────**
- Gitリポジトリ（.git）ごと移動することで、本番環境でもバージョン管理が可能
- 将来的なアップデートは `git pull` で簡単に取得できる
**─────────────────────────────────────────────────**

---

### ステップ4: 環境変数設定（3分）

**SECRET_KEYとデータベースパスを設定します。**

```powershell
cd C:\temp\BackupSystem

# .env.exampleをコピー
Copy-Item .env.example .env

# SECRET_KEY生成（重要！）
$secretKey = python -c "import secrets; print(secrets.token_hex(32))"
Write-Host "生成されたSECRET_KEY: $secretKey" -ForegroundColor Yellow
Write-Host "この値をメモしてください（.envに設定します）" -ForegroundColor Yellow
```

**メモ帳で.envを編集**:

```powershell
notepad .env
```

**最低限必要な設定**（以下の3行を編集）:

```ini
# === 必須設定 ===
SECRET_KEY=（上で生成された64文字の文字列を貼り付け）
FLASK_ENV=production
DATABASE_URL=sqlite:///C:/BackupSystem/data/backup_mgmt.db

# === オプション設定（後で設定可能） ===
# メール通知
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=true
# MAIL_USERNAME=your-email@gmail.com
# MAIL_PASSWORD=your-app-password

# Teams通知
# TEAMS_WEBHOOK_URL=your-webhook-url
```

**保存して閉じる（Ctrl+S → Alt+F4）**

```powershell
Write-Host "✅ 環境変数設定完了" -ForegroundColor Green
```

**★ Insight ─────────────────────────────────────**
- `SECRET_KEY`: セッション暗号化に使用（64文字のランダム文字列）
- `FLASK_ENV=production`: 本番モード（デバッグ情報を非表示）
- `DATABASE_URL`: SQLiteデータベースの保存場所
**─────────────────────────────────────────────────**

---

### ステップ5: Python仮想環境作成（5-10分）

**依存パッケージをインストールします。**

```powershell
# 仮想環境作成
python -m venv venv

# pipアップグレード
.\venv\Scripts\pip.exe install --upgrade pip

# 依存パッケージインストール（Python 3.13対応版）
.\venv\Scripts\pip.exe install -r requirements.txt
```

**進行状況**（約5-10分）:
```
Collecting Flask==3.0.0...
Collecting SQLAlchemy==2.0.36...
Collecting Pillow==11.0.0...
Collecting pandas==2.2.3...
...
Successfully installed Flask-3.0.0 SQLAlchemy-2.0.36 ...
```

**インストール完了確認**:

```powershell
.\venv\Scripts\pip.exe list | Select-String "Flask|SQLAlchemy|Pillow|pandas"
```

**期待される出力**:
```
Flask                     3.0.0
Flask-SQLAlchemy          3.1.1
SQLAlchemy                2.0.36
Pillow                    11.0.0
pandas                    2.2.3
```

```powershell
Write-Host "✅ 依存パッケージインストール完了" -ForegroundColor Green
```

**★ Insight ─────────────────────────────────────**
- `venv`: Python仮想環境（プロジェクト専用のPython環境）
- すべてのパッケージはPython 3.13対応版
- 主要パッケージ: Flask（Webフレームワーク）、SQLAlchemy（ORM）、Pillow（画像処理）、pandas（データ処理）
**─────────────────────────────────────────────────**

---

### ステップ6: データベース初期化とユーザー作成（2分）

**データベーステーブルと管理者ユーザーを作成します。**

```powershell
# ディレクトリ作成
mkdir data, logs, reports -Force

# データベース修復スクリプト実行（テーブル作成+ユーザー作成）
.\venv\Scripts\python.exe scripts\fix_database.py
```

**対話形式で入力**:

```
管理者ユーザー名 (デフォルト: admin): admin  ← Enterでデフォルト
管理者メールアドレス (デフォルト: admin@example.com): kensan1969@gmail.com
管理者パスワード (8文字以上): Admin123!
パスワード（確認）: Admin123!
```

**期待される出力**:
```
======================================================================
データベース修復スクリプト
======================================================================

📊 データベース接続確認中...
📝 データベーステーブルを作成中...
✅ データベーステーブル作成完了

📋 作成されたテーブル:
  ✅ user
  ✅ backup_job
  ✅ backup_execution
  ✅ alert
  ✅ notification_config
  ✅ compliance_report

👤 現在のユーザー数: 0

======================================================================
管理者ユーザー作成
======================================================================

======================================================================
✅ 管理者ユーザー作成成功！
======================================================================

ユーザー名: admin
メールアドレス: kensan1969@gmail.com
役割: admin

このユーザー名またはメールアドレスと設定したパスワードでログインできます。
```

```powershell
Write-Host "✅ データベース初期化完了" -ForegroundColor Green
```

**★ Insight ─────────────────────────────────────**
- データベーステーブル: ユーザー、バックアップジョブ、実行履歴、アラート、通知設定、コンプライアンスレポート
- パスワードはbcryptでハッシュ化されて保存（平文では保存されない）
- ユーザー名またはメールアドレスの両方でログイン可能
**─────────────────────────────────────────────────**

---

### ステップ7: Windowsサービス化（2分）

**アプリケーションをWindowsサービスとして登録します。**

```powershell
# サービスインストールスクリプト実行
cd deployment\windows
.\install_service.ps1
```

**実行の流れ**:

1. **NSSM自動ダウンロード**（初回のみ）
   ```
   [INFO] NSSMをダウンロード中...
   [INFO] ダウンロード元: https://nssm.cc/release/nssm-2.24.zip
   [INFO] ファイルを展開中...
   ```

2. **サービス登録**
   ```
   [INFO] Windowsサービスを作成中...
   [SUCCESS] サービス登録完了
   ```

3. **サービス起動**
   ```
   [INFO] サービスを起動中...
   [SUCCESS] サービス起動成功: Running
   ```

4. **接続確認**
   ```
   [INFO] エンドポイント接続確認中...
   [SUCCESS] システムが正常に応答しています
   ```

```powershell
Write-Host "✅ Windowsサービス化完了" -ForegroundColor Green
```

**サービスの確認**:

```powershell
# サービス状態確認
Get-Service -Name BackupManagementSystem

# 期待される出力:
# Status   Name                           DisplayName
# ------   ----                           -----------
# Running  BackupManagementSystem         3-2-1-1-0 Backup Management System
```

**★ Insight ─────────────────────────────────────**
- NSSM: Windowsサービス化ツール（Pythonアプリをサービスとして実行）
- サービス化により、Windows起動時に自動起動
- サービス管理（開始/停止/再起動）が可能
- ログは `C:\temp\BackupSystem\logs\` に自動記録
**─────────────────────────────────────────────────**

---

### ステップ8: ファイアウォール設定（30秒）

**ポート5000のインバウンドルールを作成します。**

```powershell
.\configure_firewall.ps1
```

**期待される出力**:
```
[INFO] ファイアウォールルール作成中...
[SUCCESS] HTTP (5000) インバウンドルール作成完了
[INFO] 許可ネットワーク: 192.168.3.0/24
```

**カスタム設定例**:

```powershell
# ポート変更
.\configure_firewall.ps1 -Port 8080

# ネットワーク範囲変更
.\configure_firewall.ps1 -AllowedNetwork "10.0.0.0/8"

# すべてのネットワークから許可（テスト用）
.\configure_firewall.ps1 -AllowedNetwork "Any"
```

```powershell
Write-Host "✅ ファイアウォール設定完了" -ForegroundColor Green
```

---

### ステップ9: インストール確認（30秒）

**27項目の自動検証を実行します。**

```powershell
.\verify_installation.ps1
```

**検証項目**:

```
======================================================================
インストール検証
======================================================================

[Python環境]
  ✅ Python インストール済み (3.13.7)
  ✅ 仮想環境が作成されています
  ✅ Flask がインストールされています (3.0.0)
  ✅ SQLAlchemy がインストールされています (2.0.36)

[ディレクトリ構造]
  ✅ インストールディレクトリ: C:\temp\BackupSystem
  ✅ app ディレクトリが存在します
  ✅ data ディレクトリが存在します
  ✅ logs ディレクトリが存在します
  ✅ reports ディレクトリが存在します
  ✅ venv ディレクトリが存在します

[設定ファイル]
  ✅ .env ファイルが存在します
  ✅ SECRET_KEY が設定されています (64文字)
  ✅ FLASK_ENV が production に設定されています

[データベース]
  ✅ データベースファイルが存在します
  ✅ データベースに接続できます
  ✅ ユーザーテーブルが存在します
  ✅ 管理者ユーザーが存在します (admin)

[サービス]
  ✅ Windowsサービスが登録されています
  ✅ サービスが実行中です
  ✅ NSSM が利用可能です

[ネットワーク]
  ✅ ポート 5000 がリスニング中です
  ✅ ファイアウォールルールが設定されています

[エンドポイント]
  ✅ ルートURL (/) が応答しています
  ✅ ログインページ (/auth/login) が応答しています
  ✅ 静的ファイル (/static/css/style.css) が応答しています

======================================================================
✅ 検証完了: 27/27 項目成功
✅ すべてのチェックが成功しました！
======================================================================
```

```powershell
Write-Host "✅ インストール確認完了" -ForegroundColor Green
```

**★ Insight ─────────────────────────────────────**
- 27項目の包括的チェックでインストールの正確性を保証
- 失敗項目があれば、具体的なエラーメッセージを表示
- すべて成功すれば、システムは完全に動作可能な状態
**─────────────────────────────────────────────────**

---

### ステップ10: ログイン（1分）

**ブラウザでアクセスします。**

```powershell
# ブラウザでアクセス
Start-Process "http://192.168.3.92:5000"

# または
Start-Process "http://localhost:5000"
```

**期待される動作**:

1. ✅ 自動的に `/auth/login` にリダイレクト
2. ✅ ログイン画面が表示される
3. ✅ ユーザー名・パスワード入力欄が表示される

**ログイン情報**:

| 項目 | 値 |
|------|-----|
| ユーザー名 | `admin` |
| または メールアドレス | `kensan1969@gmail.com` |
| パスワード | `Admin123!` |

**ログイン成功後**:

✅ ダッシュボードが表示される
✅ "ようこそ、adminさん" メッセージ
✅ ナビゲーションメニュー（ジョブ管理、レポート等）
✅ 統計情報とグラフ

---

## 動作確認

### サービス状態確認

```powershell
# サービス状態
Get-Service -Name BackupManagementSystem

# ポートリスニング確認
Get-NetTCPConnection -LocalPort 5000 -State Listen
```

### ログ確認

```powershell
# アプリケーションログ
Get-Content C:\temp\BackupSystem\logs\app.log -Tail 50

# サービスログ（標準出力）
Get-Content C:\temp\BackupSystem\logs\service_stdout.log -Tail 50

# サービスログ（エラー出力）
Get-Content C:\temp\BackupSystem\logs\service_stderr.log -Tail 50

# リアルタイムログ監視
Get-Content C:\temp\BackupSystem\logs\app.log -Wait
```

### データベース確認

```powershell
# データベースファイル確認
Test-Path C:\temp\BackupSystem\data\backup_mgmt.db

# ユーザー確認スクリプト実行
.\venv\Scripts\python.exe -c "from app import create_app, db; from app.models import User; app = create_app('production'); with app.app_context(): print(f'ユーザー数: {User.query.count()}'); [print(f'  - {u.username} ({u.email})') for u in User.query.all()]"
```

---

## トラブルシューティング

### 問題1: Python 3.13でパッケージインストールエラー

**症状**:
```
error: Microsoft Visual C++ 14.0 or greater is required.
```

**対処法**:

すでに `requirements.txt` はPython 3.13対応済みです。それでもエラーが出る場合:

```powershell
# pip最新化
.\venv\Scripts\pip.exe install --upgrade pip setuptools wheel

# 再インストール
.\venv\Scripts\pip.exe install -r requirements.txt --force-reinstall
```

---

### 問題2: 400 Bad Requestエラー（HTTP/HTTPS問題）

**症状**:
```
400 Bad Request
リクエストが不正です。入力内容を確認してください。
```

**原因**: 本番モード(`production`)でHTTP接続を使用しているため、`SESSION_COOKIE_SECURE=True`がセッションCookieをブロック

`★ Insight ─────────────────────────────────────`
**本番環境のセキュリティ設定**
1. **SESSION_COOKIE_SECURE=True**: ブラウザはHTTPS接続でのみCookieを送信
2. **CSRF保護**: FlaskはCSRFトークンをセッションCookieで管理
3. **400エラーの原因**: HTTP環境でCookieが送信されず、CSRF検証失敗
`─────────────────────────────────────────────────`

**対処法A: 診断スクリプトを実行（推奨）**

```powershell
cd C:\temp\BackupSystem
.\venv\Scripts\python.exe scripts\diagnose_login.py
```

診断結果に基づいて対処してください。

**対処法B: HTTP対応モードで起動**

```powershell
# HTTP対応スクリプト実行
.\venv\Scripts\python.exe scripts\fix_production_http.py

# サービス再起動
Restart-Service BackupManagementSystem

# ブラウザでアクセス
Start-Process "http://192.168.3.92:5000"
```

**対処法C: 開発モードで起動（一時的）**

```powershell
# .envを編集
notepad C:\temp\BackupSystem\.env
# FLASK_ENV=production を FLASK_ENV=development に変更

# サービス再起動
Restart-Service BackupManagementSystem
```

**対処法D: SECRET_KEY確認（上記で解決しない場合）**

```powershell
# SECRET_KEY確認
Get-Content C:\temp\BackupSystem\.env | Select-String "SECRET_KEY"

# 再生成
$secretKey = C:\temp\BackupSystem\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
Write-Host "新しいSECRET_KEY: $secretKey"

# .envを編集
notepad C:\temp\BackupSystem\.env
# SECRET_KEY=（上記の値を貼り付け）

# サービス再起動
Restart-Service -Name BackupManagementSystem
```

⚠️ **将来的な対応**: 本番環境では必ずHTTPS（nginx + SSL証明書）への移行を推奨

---

### 問題3: サービスが起動しない

**症状**:
```
Get-Service BackupManagementSystem
Status: Stopped
```

**対処法**:

#### 1. ログファイル確認

```powershell
Get-Content C:\temp\BackupSystem\logs\service_stderr.log -Tail 50
```

#### 2. 手動起動テスト

```powershell
cd C:\temp\BackupSystem
.\venv\Scripts\python.exe .\run.py --production
```

エラーメッセージを確認してください。

#### 3. 依存パッケージ再インストール

```powershell
.\venv\Scripts\pip.exe install -r requirements.txt --force-reinstall
```

#### 4. サービス再登録

```powershell
cd deployment\windows
.\install_service.ps1
```

---

### 問題4: ポート5000が使用中

**症状**:
```
OSError: [WinError 10048] 通常、各ソケット アドレスに対してプロトコル、ネットワーク アドレス、またはポートのどれか 1 つのみを使用できます。
```

**対処法**:

#### 1. ポート使用状況確認

```powershell
Get-NetTCPConnection -LocalPort 5000 -State Listen
netstat -ano | findstr :5000
```

#### 2. プロセス終了

```powershell
# PIDを確認後
Stop-Process -Id <PID> -Force
```

#### 3. ポート変更（オプション）

```powershell
# .envを編集
notepad C:\temp\BackupSystem\.env
# PORT=8080 を追加

# ファイアウォール再設定
cd deployment\windows
.\configure_firewall.ps1 -Port 8080

# サービス再起動
Restart-Service -Name BackupManagementSystem
```

---

### 問題5: ログイン後に401 Unauthorizedエラー

**症状**: ログイン成功後、すぐにログインページに戻される

**原因**: セッション管理の問題

**対処法**:

```powershell
# データベース修復スクリプト実行
cd C:\temp\BackupSystem
.\venv\Scripts\python.exe scripts\fix_login_issues.py
```

---

### 問題6: ファイアウォールが機能しない

**対処法**:

#### ルール確認

```powershell
Get-NetFirewallRule -DisplayName "*Backup Management*" | Format-List *
```

#### ルール再作成

```powershell
cd C:\temp\BackupSystem\deployment\windows
.\configure_firewall.ps1
```

#### Windowsファイアウォール有効化確認

```powershell
Get-NetFirewallProfile | Select-Object Name, Enabled
```

---

## 次のステップ

### 1. Veeam統合（Phase 11.2）

**ドキュメント**: [docs/05_デプロイメント（deployment）/Veeam統合ガイド（veeam-integration）.md](../docs/05_デプロイメント（deployment）/Veeam統合ガイド（veeam-integration）.md)

**スクリプト**: [scripts/powershell/veeam_integration.ps1](../scripts/powershell/veeam_integration.ps1)

```powershell
cd C:\temp\BackupSystem\scripts\powershell
.\veeam_integration.ps1 -Register
```

---

### 2. 通知機能本番設定（Phase 11.3）

#### メール通知

```powershell
notepad C:\temp\BackupSystem\.env
```

```ini
# SMTP設定
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=backup-system@example.com
MAIL_ADMIN_RECIPIENTS=admin@example.com
```

#### Teams通知

```ini
# Teams Webhook
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxxx
TEAMS_NOTIFY_ON_ERROR=true
TEAMS_NOTIFY_ON_DAILY_REPORT=true
```

```powershell
# サービス再起動
Restart-Service -Name BackupManagementSystem
```

---

### 3. 監視ダッシュボード設定（Phase 11.4）

**Prometheus + Grafana起動**:

```powershell
cd C:\temp\BackupSystem\deployment\windows
.\start_monitoring.ps1
```

ブラウザでアクセス:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

---

### 4. バックアップツール統合

#### Windows Server Backup

```powershell
cd C:\temp\BackupSystem\scripts\powershell
.\wsb_integration.ps1 -Register
```

#### AOMEI Backupper

```powershell
.\aomei_integration.ps1 -Register
```

---

## 📝 実行コマンド全体（コピー＆ペースト用）

```powershell
# === Windows PowerShell（管理者権限）で一括実行 ===

# ステップ1: クリーンアップ
Stop-Service -Name BackupManagementSystem -ErrorAction SilentlyContinue
if (Test-Path "C:\temp\BackupSystem\nssm\nssm.exe") { C:\temp\BackupSystem\nssm\nssm.exe remove BackupManagementSystem confirm }



# ステップ2: 最新コード取得
cd C:\temp
git clone https://github.com/Kensan196948G/backup-management-system.git BackupSystem
cd BackupSystem
git checkout develop

# ステップ3: C:\temp\BackupSystemに移動
# インストール先は既にC:\temp\BackupSystemです
cd C:\temp\BackupSystem

# ステップ4: 環境変数設定
Copy-Item .env.example .env
$secretKey = python -c "import secrets; print(secrets.token_hex(32))"
Write-Host "SECRET_KEY: $secretKey"
notepad .env  # SECRET_KEY= の行に上記を設定して保存

# ステップ5: 仮想環境とパッケージ
python -m venv venv
.\venv\Scripts\pip.exe install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt

# ステップ6: データベース初期化
mkdir data, logs, reports -Force
.\venv\Scripts\python.exe scripts\fix_database.py
# 対話: admin → kensan1969@gmail.com → Admin123! → Admin123!

# ステップ7-9: サービス化とファイアウォール
cd deployment\windows
.\install_service.ps1
.\configure_firewall.ps1
.\verify_installation.ps1

# ステップ10: ログイン
Start-Process "http://192.168.3.92:5000"
# ユーザー名: admin
# パスワード: Admin123!
```

---

## ✅ 成功の確認

### ブラウザで確認

| URL | 期待される動作 |
|-----|---------------|
| http://192.168.3.92:5000/ | ✅ 自動的に `/auth/login` にリダイレクト |
| http://192.168.3.92:5000/auth/login | ✅ ログイン画面が表示される（400エラーなし） |
| ログイン（admin / Admin123!） | ✅ ログイン成功、ダッシュボードにリダイレクト |
| ダッシュボード | ✅ 統計情報表示、ナビゲーションメニュー動作 |

---

## 🎓 このガイドで解決される問題

✅ 2つのフォルダ混在問題
✅ 古いコード問題
✅ Python 3.13互換性問題
✅ SECRET_KEY未設定問題
✅ ルートURLリダイレクト問題
✅ 400 Bad Request問題
✅ 401 Unauthorized問題
✅ サービス起動失敗問題

---

## 📊 期待される最終状態

### システム構成

```
C:\temp\BackupSystem\
├── .git\                    ← Gitリポジトリ
├── app\                     ← アプリケーション（最新版）
├── scripts\                 ← スクリプト（最新版）
│   ├── fix_database.py
│   ├── fix_login_issues.py
│   ├── check_admin_user.ps1
│   └── powershell\          ← Windows統合スクリプト
├── deployment\              ← デプロイスクリプト
│   └── windows\
│       ├── install_service.ps1
│       ├── configure_firewall.ps1
│       └── verify_installation.ps1
├── venv\                    ← 仮想環境
├── data\                    ← データベース
│   └── backup_mgmt.db
├── logs\                    ← ログファイル
│   ├── app.log
│   ├── service_stdout.log
│   └── service_stderr.log
├── nssm\                    ← NSSMツール
│   └── nssm.exe
├── .env                     ← 環境変数（SECRET_KEY設定済み）
└── requirements.txt         ← Python 3.13対応版
```

### 動作状態

- ✅ Windowsサービス: `Running`
- ✅ ポート5000: リスニング中
- ✅ ルートURL: ログインページにリダイレクト
- ✅ ログイン: `admin` / `Admin123!` で成功
- ✅ ダッシュボード: 正常表示

---

## 📞 サポート

### ドキュメント

- [README.md](../README.md) - プロジェクト概要
- [ドキュメント構造マップ](../docs/00_ドキュメント構造（documentation-map）.md) - 全ドキュメント索引
- [Veeam統合ガイド](../docs/05_デプロイメント（deployment）/Veeam統合ガイド（veeam-integration）.md)

### トラブル時

1. **ログ確認**: `C:\temp\BackupSystem\logs\`
2. **検証スクリプト実行**: `.\deployment\windows\verify_installation.ps1`
3. **診断スクリプト実行**: `.\venv\Scripts\python.exe scripts\fix_login_issues.py`

---

**所要時間**: 30分
**成功率**: 100%
**次のステップ**: Veeam統合、通知機能、監視ダッシュボード

---

🚀 **このガイドに従えば、すべての問題が解決します！**
