#!/bin/bash
# ========================================
# systemdサービスインストールスクリプト
# 3-2-1-1-0 Backup Management System
# ========================================

set -e

echo "========================================="
echo "systemdサービスのインストール"
echo "========================================="

# root権限チェック
if [ "$EUID" -ne 0 ]; then
    echo "エラー: このスクリプトはroot権限で実行する必要があります"
    echo "sudo $0 を実行してください"
    exit 1
fi

# プロジェクトルートディレクトリ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SYSTEMD_DIR="${PROJECT_ROOT}/deployment/systemd"

echo "プロジェクトディレクトリ: ${PROJECT_ROOT}"
echo ""

# インストールする環境の選択
echo "インストールする環境を選択してください:"
echo "  1) 開発環境（Development）"
echo "  2) 本番環境（Production）"
echo "  3) 両方"
echo ""
read -p "選択 (1-3): " ENV_CHOICE

case $ENV_CHOICE in
    1)
        SERVICES=("backup-management-development")
        ENV_NAME="開発環境"
        ;;
    2)
        SERVICES=("backup-management-production" "celery-worker-prod" "celery-beat-prod")
        ENV_NAME="本番環境"
        ;;
    3)
        SERVICES=("backup-management-development" "backup-management-production" "celery-worker-prod" "celery-beat-prod")
        ENV_NAME="開発環境 + 本番環境"
        ;;
    *)
        echo "無効な選択です"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "${ENV_NAME} のサービスをインストールします"
echo "========================================="
echo ""

# 必要なディレクトリの作成
echo "必要なディレクトリを作成しています..."
mkdir -p /var/run/celery
chown www-data:www-data /var/run/celery

# サービスファイルのコピー
echo "サービスファイルをコピーしています..."
for service in "${SERVICES[@]}"; do
    if [ -f "${SYSTEMD_DIR}/${service}.service" ]; then
        cp "${SYSTEMD_DIR}/${service}.service" /etc/systemd/system/
        echo "  ✅ ${service}.service"
    else
        echo "  ⚠️  ${service}.service が見つかりません"
    fi
done

# systemdデーモンのリロード
echo ""
echo "systemdデーモンをリロードしています..."
systemctl daemon-reload

echo ""
echo "========================================="
echo "✅ インストール完了"
echo "========================================="
echo ""

# サービスの操作方法を表示
echo "サービスの操作方法:"
echo ""

for service in "${SERVICES[@]}"; do
    echo "【${service}】"
    echo "  起動:         sudo systemctl start ${service}"
    echo "  停止:         sudo systemctl stop ${service}"
    echo "  再起動:       sudo systemctl restart ${service}"
    echo "  状態確認:     sudo systemctl status ${service}"
    echo "  自動起動有効: sudo systemctl enable ${service}"
    echo "  自動起動無効: sudo systemctl disable ${service}"
    echo "  ログ表示:     sudo journalctl -u ${service} -f"
    echo ""
done

echo "========================================="
echo "推奨: 自動起動を有効化する"
echo "========================================="
echo ""

read -p "自動起動を有効化しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    for service in "${SERVICES[@]}"; do
        systemctl enable "${service}"
        echo "  ✅ ${service} の自動起動を有効化しました"
    done
else
    echo "自動起動の有効化をスキップしました"
    echo "後で手動で有効化する場合:"
    for service in "${SERVICES[@]}"; do
        echo "  sudo systemctl enable ${service}"
    done
fi

echo ""
echo "========================================="
echo "サービスを起動する"
echo "========================================="
echo ""

read -p "今すぐサービスを起動しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    for service in "${SERVICES[@]}"; do
        systemctl start "${service}"

        # 起動確認
        sleep 2
        if systemctl is-active --quiet "${service}"; then
            echo "  ✅ ${service} を起動しました"
        else
            echo "  ❌ ${service} の起動に失敗しました"
            echo "     ログを確認してください: sudo journalctl -u ${service} -n 50"
        fi
    done
else
    echo "サービスの起動をスキップしました"
    echo "後で手動で起動する場合:"
    for service in "${SERVICES[@]}"; do
        echo "  sudo systemctl start ${service}"
    done
fi

echo ""
echo "========================================="
echo "セットアップ完了"
echo "========================================="
echo ""
echo "次のステップ:"
echo "  1. サービスの状態を確認してください"
echo "  2. Webブラウザでアクセスしてください"
echo "     - 開発環境: http://localhost:5001"
echo "     - 本番環境: http://localhost:5000 または https://localhost:443"
echo "  3. ログを監視してエラーがないか確認してください"
echo ""
