# デプロイメントガイド

3-2-1-1-0 Backup Management System の複数環境へのデプロイメント

## ディレクトリ構成

```
deployment/
├── README.md                    # このファイル
├── linux/                       # Linux（Ubuntu/Debian）デプロイメント
│   ├── setup.sh                # セットアップスクリプト
│   ├── setup_ssl.sh            # SSL証明書取得スクリプト
│   ├── uninstall.sh            # アンインストールスクリプト
│   ├── maintenance.sh          # メンテナンス・運用管理スクリプト
│   ├── README.md               # 詳細ドキュメント
│   ├── QUICKSTART.md           # クイックスタートガイド
│   ├── DEPLOYMENT_CHECKLIST.md # デプロイメントチェックリスト
│   ├── systemd/
│   │   └── backup-management.service  # systemdユニットファイル
│   └── nginx/
│       └── backup-management.conf     # nginxリバースプロキシ設定
├── docker/                      # Docker コンテナ化（将来）
├── kubernetes/                  # Kubernetes デプロイメント（将来）
└── scripts/
    └── deploy.sh               # 統合デプロイスクリプト
```

## 対応プラットフォーム

### 現在対応

- **Linux（Ubuntu/Debian）**: 完全対応
  - Ubuntu 20.04 LTS以上
  - Debian 11以上

### 計画中

- Docker デプロイメント
- Kubernetes デプロイメント
- Windows Server デプロイメント

## クイックスタート

### 最速デプロイメント（5分）

```bash
# 1. リポジトリをクローン
git clone https://github.com/your-org/backup-management-system.git
cd backup-management-system

# 2. セットアップスクリプトを実行
sudo bash deployment/linux/setup.sh

# 3. 環境変数を設定
sudo nano /opt/backup-management-system/.env

# 4. サービスを起動
sudo systemctl start backup-management.service

# 5. アクセス確認
curl http://127.0.0.1:5000
```

### 本番環境デプロイメント（SSL証明書含む）

```bash
# 1-4: 上記と同じ

# 5. SSL証明書を取得
sudo bash deployment/linux/setup_ssl.sh

# 6. HTTPS でアクセス確認
curl https://backup.example.com
```

## 詳細ガイド

### Linux（Ubuntu/Debian）

→ [deployment/linux/README.md](./linux/README.md) を参照

**対象ユーザー**: Linux管理者、DevOps エンジニア

**時間目安**: 30分～1時間

**難易度**: 中程度

## デプロイメント手順の概要

### フェーズ1: 前提条件確認

1. OS互換性の確認
2. ハードウェア要件の確認
3. ネットワーク接続確認
4. ドメイン・DNS設定確認

### フェーズ2: システムセットアップ

1. システムパッケージのインストール
2. Pythonユーザーの作成
3. アプリケーションディレクトリの作成
4. Python仮想環境の構築
5. 依存パッケージのインストール

### フェーズ3: アプリケーションセットアップ

1. ファイルのコピー
2. データベースの初期化
3. 環境変数の設定
4. ログディレクトリの作成

### フェーズ4: Webサーバー設定

1. nginxのインストール
2. リバースプロキシ設定
3. SSL/TLS設定

### フェーズ5: サービス登録

1. systemdユニット登録
2. 自動起動設定
3. サービス起動テスト

### フェーズ6: セキュリティ設定

1. ファイアウォール設定
2. ユーザー権限設定
3. SSL証明書取得
4. セキュリティヘッダー設定

## スクリプト一覧

### setup.sh

**説明**: 本番環境の初期セットアップスクリプト

**実行**: `sudo bash deployment/linux/setup.sh`

**処理**:
- OS互換性チェック
- システムパッケージインストール
- ユーザー・ディレクトリ作成
- Python仮想環境構築
- データベース初期化
- systemd/nginx設定

**所要時間**: 10～15分

### setup_ssl.sh

**説明**: Let's Encrypt SSL証明書取得スクリプト

**実行**: `sudo bash deployment/linux/setup_ssl.sh`

**処理**:
- Certbotインストール確認
- ドメイン入力
- 証明書取得
- nginx設定更新
- 自動更新設定

**所要時間**: 5～10分

### maintenance.sh

**説明**: 日常のメンテナンス・運用管理スクリプト

**実行**: `sudo bash deployment/linux/maintenance.sh`

**メニュー**:
1. ステータス確認
2. ログローテーション
3. データベースバックアップ
4. データベース最適化
5. SSL証明書確認
6. システムアップデート
7. ディスク空き容量確認
8. サービス再起動
9. セキュリティチェック
10. ヘルスチェック
11. パフォーマンス分析
12. クリーンアップ
13. レポート生成

### uninstall.sh

**説明**: アプリケーションのアンインストール

**実行**: `sudo bash deployment/linux/uninstall.sh`

**処理**:
- サービス停止
- ファイル削除
- ユーザー削除
- 設定ファイル削除

**所要時間**: 5分

## 環境変数設定

### 主要な環境変数

```env
# Flask設定
FLASK_ENV=production          # 本番環境
SECRET_KEY=<自動生成>         # セッション用シークレット

# データベース
DATABASE_URL=sqlite:///<path> # データベース接続URL

# ログ設定
LOG_LEVEL=INFO               # ログレベル（DEBUG/INFO/WARNING/ERROR）
LOG_FILE=<path>              # ログファイルパス

# バックアップ設定
BACKUP_DIR=/mnt/backups      # バックアップディレクトリ
RETENTION_DAYS=30            # バックアップ保持日数

# セキュリティ
SESSION_COOKIE_SECURE=True   # HTTPS接続時のみCookie送信
SESSION_COOKIE_HTTPONLY=True # JavaScriptからのアクセス禁止
```

詳細は `.env.example` を参照してください。

## トラブルシューティング

### よくある問題

**1. サービスが起動しない**

```bash
# ログを確認
sudo journalctl -u backup-management.service -f

# 手動実行してエラーを確認
sudo -u backupmgmt /opt/backup-management-system/venv/bin/python \
    /opt/backup-management-system/run.py
```

**2. SSL証明書エラー**

```bash
# 証明書を確認
sudo certbot certificates

# 更新テスト
sudo certbot renew --dry-run
```

**3. ディスク容量不足**

```bash
# ディスク使用状況を確認
df -h

# 古いログを削除
sudo find /var/log/backup-management-system -mtime +30 -delete
```

詳細は各プラットフォームのREADMEを参照してください。

## ベストプラクティス

### セキュリティ

- [ ] SSH キーベース認証を使用
- [ ] ファイアウォールで不要なポートを閉じる
- [ ] セキュリティアップデートを定期的に適用
- [ ] バックアップを暗号化して保存
- [ ] ログアクセスを制限

### パフォーマンス

- [ ] ログローテーション設定
- [ ] データベース定期最適化
- [ ] 古いファイルの定期削除
- [ ] メモリ使用量の監視
- [ ] ディスク I/O の監視

### 可用性

- [ ] 定期的なバックアップ
- [ ] ディザスタリカバリー計画
- [ ] 冗長システムの検討
- [ ] ヘルスチェック実装
- [ ] アラート設定

### 運用性

- [ ] 詳細なドキュメント作成
- [ ] 定期的なセキュリティ監査
- [ ] 変更管理プロセス確立
- [ ] 監視システムの導入
- [ ] ロギング戦略の策定

## 更新・アップグレード

### マイナーバージョンアップデート

```bash
# 1. バックアップを作成
sudo bash deployment/linux/maintenance.sh
# → メニュー「3. データベースバックアップ」を選択

# 2. アプリケーションファイルを更新
cd /opt/backup-management-system
git pull origin main

# 3. 依存パッケージを更新
source venv/bin/activate
pip install -r requirements.txt

# 4. サービスを再起動
sudo systemctl restart backup-management.service
```

### メジャーバージョンアップグレード

```bash
# 1. バックアップを作成
sudo bash deployment/linux/maintenance.sh

# 2. データベースマイグレーション
cd /opt/backup-management-system
source venv/bin/activate
flask db upgrade

# 3. 設定ファイルを確認
# 新しいバージョンの .env.example と比較

# 4. サービスを再起動
sudo systemctl restart backup-management.service
```

## サポート

### ドキュメント

- [Linux デプロイメントガイド](./linux/README.md)
- [クイックスタートガイド](./linux/QUICKSTART.md)
- [デプロイメントチェックリスト](./linux/DEPLOYMENT_CHECKLIST.md)

### トラブルシューティング

各プラットフォームのREADMEの「トラブルシューティング」セクションを参照してください。

### GitHub Issues

バグ報告・機能リクエストは GitHub Issues でお願いします。

## ライセンス

このデプロイメントスクリプトはアプリケーションと同じライセンスの下で提供されています。

---

**最終更新**: 2024年1月15日
**バージョン**: 1.0.0
**作成者**: DevOps Team
