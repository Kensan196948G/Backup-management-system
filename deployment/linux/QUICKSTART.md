# クイックスタートガイド

Ubuntu/Debian環境での迅速なデプロイメント手順

## 5分セットアップ

### 前提条件

- Ubuntu 20.04 LTS / Debian 11以上
- root または sudo アクセス
- インターネット接続

### ステップ1: リポジトリの取得

```bash
# リポジトリをクローン
cd /tmp
git clone https://github.com/your-org/backup-management-system.git
cd backup-management-system
```

### ステップ2: セットアップスクリプトの実行

```bash
# スクリプトに実行権限を付与
chmod +x deployment/linux/setup.sh

# セットアップを実行（root権限が必要）
sudo ./deployment/linux/setup.sh
```

セットアップ中に以下を聞かれます：
- インストール開始の確認：`y` で続行

### ステップ3: 環境変数の設定

```bash
# .envファイルを編集
sudo nano /opt/backup-management-system/.env

# 重要な設定項目:
# - BACKUP_DIR: バックアップストレージのパス
# - RETENTION_DAYS: 保持日数
# - MAIL_SERVER: メール通知設定（オプション）
```

### ステップ4: SSL証明書の取得（本番環境の場合）

```bash
# ドメイン名が設定済みの場合のみ実行
chmod +x deployment/linux/setup_ssl.sh
sudo ./deployment/linux/setup_ssl.sh
```

入力項目：
- ドメイン名: `backup.example.com`
- メール: `admin@example.com`

### ステップ5: サービスの起動

```bash
# アプリケーションサービスを起動
sudo systemctl start backup-management.service

# 自動起動を有効化
sudo systemctl enable backup-management.service

# ステータス確認
sudo systemctl status backup-management.service
```

### ステップ6: アクセス確認

```bash
# ローカルマシン上でテスト
curl http://127.0.0.1:5000

# ブラウザで確認（ドメインが設定済みの場合）
# https://backup.example.com

# または
# http://localhost:80
```

---

## トラブルシューティング

### サービスが起動しない場合

```bash
# ステータス確認
sudo systemctl status backup-management.service

# ログを確認
sudo journalctl -u backup-management.service -f

# 手動実行
sudo /opt/backup-management-system/venv/bin/python /opt/backup-management-system/run.py
```

### ポートが使用中の場合

```bash
# ポート5000の使用状況確認
sudo netstat -tulpn | grep 5000

# 使用中のプロセスを終了
sudo kill -9 <PID>
```

### 環境変数ファイルを見つけられない場合

```bash
# .envファイルの位置を確認
ls -la /opt/backup-management-system/.env

# 存在しない場合は作成
sudo cp /opt/backup-management-system/.env.example /opt/backup-management-system/.env
```

---

## よくある質問

**Q: テスト環境での実行方法は？**

A: テスト環境の場合、SSL証明書設定はスキップできます。HTTP（ポート80）でアクセスしてください。

**Q: ドメイン名はどこで変更する？**

A: `/etc/nginx/sites-available/backup-management.conf` 内の `server_name` を変更してください。

**Q: ポート番号を変更したい場合は？**

A:
```bash
# 1. systemdサービスファイルを編集
sudo systemctl edit backup-management.service

# 2. ExecStartを以下のように変更:
# ExecStart=/opt/backup-management-system/venv/bin/python run.py --port 8080 --production

# 3. nginxコンフィグを編集
sudo nano /etc/nginx/sites-available/backup-management.conf

# 4. upstream backup_app の server を変更:
# server 127.0.0.1:8080;
```

**Q: セットアップを取り消したい場合は？**

A: アンインストールスクリプトを実行してください。
```bash
chmod +x deployment/linux/uninstall.sh
sudo ./deployment/linux/uninstall.sh
```

---

## 次のステップ

- 詳細な設定方法は `README.md` を参照
- 日常の管理・運用は `maintenance.sh` を使用
- 本番環境での推奨設定については `README.md` のセキュリティセクションを確認

---

**セットアップ完了後のアドレス**

- アプリケーション: `http://127.0.0.1:5000` または `https://backup.example.com`
- ログファイル: `/var/log/backup-management-system/app.log`
- 設定ファイル: `/opt/backup-management-system/.env`
- データベース: `/var/lib/backup-management-system/backup_management.db`
