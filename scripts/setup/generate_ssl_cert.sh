#!/bin/bash
# ========================================
# 自己署名SSL証明書生成スクリプト
# 3-2-1-1-0 Backup Management System
# ========================================

set -e

echo "========================================="
echo "自己署名SSL証明書生成"
echo "========================================="

# 証明書の保存先
CERT_DIR="/etc/ssl/certs"
KEY_DIR="/etc/ssl/private"
CERT_FILE="${CERT_DIR}/backup-system-selfsigned.crt"
KEY_FILE="${KEY_DIR}/backup-system-selfsigned.key"

# IPアドレスの入力（デフォルト値を提供）
read -p "サーバーのIPアドレスを入力してください（例: 192.168.1.100）: " SERVER_IP
SERVER_IP=${SERVER_IP:-"192.168.1.100"}

read -p "組織名を入力してください（例: My Company）: " ORG_NAME
ORG_NAME=${ORG_NAME:-"Backup Management System"}

# root権限チェック
if [ "$EUID" -ne 0 ]; then
    echo "エラー: このスクリプトはroot権限で実行する必要があります"
    echo "sudo $0 を実行してください"
    exit 1
fi

echo ""
echo "設定内容:"
echo "  - サーバーIP: ${SERVER_IP}"
echo "  - 組織名: ${ORG_NAME}"
echo "  - 証明書ファイル: ${CERT_FILE}"
echo "  - 秘密鍵ファイル: ${KEY_FILE}"
echo "  - 有効期限: 365日"
echo ""

# ディレクトリが存在しない場合は作成
mkdir -p "${CERT_DIR}"
mkdir -p "${KEY_DIR}"

# 既存の証明書があればバックアップ
if [ -f "${CERT_FILE}" ]; then
    echo "既存の証明書をバックアップしています..."
    mv "${CERT_FILE}" "${CERT_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
fi

if [ -f "${KEY_FILE}" ]; then
    echo "既存の秘密鍵をバックアップしています..."
    mv "${KEY_FILE}" "${KEY_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# OpenSSL設定ファイルの作成（SANs対応）
cat > /tmp/openssl-san.cnf << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=JP
ST=Tokyo
L=Tokyo
O=${ORG_NAME}
OU=IT Department
CN=${SERVER_IP}

[v3_req]
subjectAltName = @alt_names

[alt_names]
IP.1 = ${SERVER_IP}
IP.2 = 127.0.0.1
DNS.1 = localhost
DNS.2 = backup-system.local
EOF

echo "SSL証明書を生成しています..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${KEY_FILE}" \
    -out "${CERT_FILE}" \
    -config /tmp/openssl-san.cnf \
    -extensions v3_req

# 秘密鍵のパーミッション設定
chmod 600 "${KEY_FILE}"
chmod 644 "${CERT_FILE}"

# 一時ファイルの削除
rm -f /tmp/openssl-san.cnf

echo ""
echo "========================================="
echo "✅ SSL証明書の生成が完了しました"
echo "========================================="
echo ""
echo "証明書情報:"
openssl x509 -in "${CERT_FILE}" -noout -text | grep -A 2 "Subject:"
echo ""
openssl x509 -in "${CERT_FILE}" -noout -text | grep -A 5 "Subject Alternative Name"
echo ""
echo "有効期限:"
openssl x509 -in "${CERT_FILE}" -noout -dates
echo ""

echo "次のステップ:"
echo "1. ブラウザで https://${SERVER_IP} にアクセス"
echo "2. セキュリティ警告が表示されます（自己署名証明書のため）"
echo "3. 「詳細設定」→「サイトに進む」をクリック"
echo "4. または、証明書をブラウザの信頼されたルート証明機関にインポート"
echo ""
echo "証明書のインポート方法（Chrome/Edge）:"
echo "1. ${CERT_FILE} をダウンロード"
echo "2. ブラウザの設定 → プライバシーとセキュリティ → セキュリティ"
echo "3. 証明書の管理 → 信頼されたルート証明機関 → インポート"
echo ""

echo "nginx設定に以下を追加してください:"
echo "---"
echo "ssl_certificate ${CERT_FILE};"
echo "ssl_certificate_key ${KEY_FILE};"
echo "---"
echo ""
