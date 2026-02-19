# 🚀 セットアップ実行ガイド - 残りのステップ

**作成日**: 2026年1月21日
**環境**: Linux (Ubuntu)

---

## ✅ 完了したステップ

### ステップ1: 環境設定の最終調整 ✅ 完了

| 項目 | 設定値 | 状態 |
|-----|--------|------|
| SECRET_KEY | `EgKC1Xmm...BY0` | ✅ |
| 開発環境 BASE_URL | `http://192.168.0.187:5001` | ✅ |
| 本番環境 BASE_URL | `https://192.168.0.187:8443` | ✅ |
| 開発環境 ポート | 5001 (HTTP) | ✅ |
| 本番環境 ポート | 5000 (HTTP), 8443 (HTTPS) | ✅ |

---

## ⏳ 残りのステップ（実行が必要）

### ステップ2: SSL証明書の生成

以下のコマンドを実行してください：

```bash
cd /mnt/LinuxHDD/Backup-Management-System
sudo ./scripts/setup/generate_ssl_cert.sh
```

**対話形式の入力**:
- サーバーのIPアドレス: `192.168.0.187` と入力
- 組織名: そのまま Enter（デフォルト: Backup Management System）

**完了確認**:
```bash
ls -lh /etc/ssl/certs/backup-system-selfsigned.crt
ls -lh /etc/ssl/private/backup-system-selfsigned.key
```

---

### ステップ3: systemdサービスのインストール

```bash
cd /mnt/LinuxHDD/Backup-Management-System
sudo ./scripts/setup/install_systemd_services.sh
```

**環境選択**:
- `2` と入力（本番環境）

**完了確認**:
```bash
systemctl list-unit-files | grep backup-management
```

---

### ステップ4: サービスの起動

```bash
# サービスの起動
sudo systemctl start backup-management-production

# 状態確認
sudo systemctl status backup-management-production

# 自動起動の有効化
sudo systemctl enable backup-management-production
```

**完了確認**:
```bash
# サービスが起動しているか確認
sudo systemctl is-active backup-management-production
# → "active" と表示されればOK

# ログの確認
sudo journalctl -u backup-management-production -n 20
```

---

## 🌐 アクセスURL

セットアップ完了後、以下のURLでアクセスできます：

| 環境 | URL | ブックマーク |
|-----|-----|------------|
| **開発環境** | `http://192.168.0.187:5001` | [開発] Backup System |
| **本番環境 (HTTP)** | `http://192.168.0.187:5000` | [本番HTTP] Backup System |
| **本番環境 (HTTPS)** | `https://192.168.0.187:8443` | [本番HTTPS] Backup System |

---

## 🔍 トラブルシューティング

### SSL証明書生成エラー

```bash
# OpenSSLがインストールされているか確認
openssl version

# インストールされていない場合
sudo apt-get install openssl
```

### サービス起動エラー

```bash
# ログを確認
sudo journalctl -u backup-management-production -n 50

# 設定ファイルを確認
cat .env.production | grep -v '^#'
```

### ポート使用エラー

```bash
# ポート8443が使用中か確認
lsof -i :8443

# もし使用中なら、プロセスを特定して停止
sudo systemctl stop <service-name>
```

---

## 📋 チェックリスト

実行前にチェック：

- [ ] `.env.production` の SECRET_KEY が設定されている
- [ ] `.env.production` の BASE_URL が正しい
- [ ] PostgreSQL が起動している (`sudo systemctl status postgresql`)
- [ ] Redis が起動している (`sudo systemctl status redis-server`)

実行後にチェック：

- [ ] SSL証明書が生成されている
- [ ] systemdサービスがインストールされている
- [ ] backup-management-production サービスが起動している
- [ ] ブラウザで https://192.168.0.187:8443 にアクセスできる

---

## 🎯 次のステップ

セットアップ完了後：

1. ブラウザで `https://192.168.0.187:8443` にアクセス
2. 初回ログイン（デフォルト管理者アカウント）
3. バックアップジョブの作成
4. メディアの登録
5. 通知設定

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
