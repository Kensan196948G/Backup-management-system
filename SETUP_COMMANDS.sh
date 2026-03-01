#!/bin/bash
# ========================================
# セットアップコマンド実行スクリプト
# すべてのステップを順番に実行
# ========================================

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║   Backup Management System - セットアップ実行スクリプト       ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# プロジェクトルートに移動
cd /mnt/LinuxHDD/Backup-Management-System

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ1: 環境設定の確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "開発環境 BASE_URL:"
grep "^BASE_URL=" .env.development
echo ""
echo "本番環境 BASE_URL:"
grep "^BASE_URL=" .env.production
echo ""
echo "本番環境 SECRET_KEY (先頭20文字):"
grep "^SECRET_KEY=" .env.production | cut -c1-30
echo "...（省略）"
echo ""
read -p "環境設定は正しいですか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "設定を確認してから再実行してください"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ2: SSL証明書の生成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "SSL証明書を生成します..."
echo "  - サーバーIP: 192.168.0.187"
echo "  - 組織名: Backup Management System"
echo ""
read -p "SSL証明書を生成しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo ./scripts/setup/generate_ssl_cert.sh
else
    echo "SSL証明書の生成をスキップしました"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ3: systemdサービスのインストール"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "systemdサービスをインストールします"
echo ""
echo "インストールする環境を選択してください:"
echo "  1) 開発環境（Development）"
echo "  2) 本番環境（Production）"
echo "  3) 両方"
echo ""
read -p "選択 (1-3): " ENV_CHOICE

case $ENV_CHOICE in
    1|2|3)
        echo "$ENV_CHOICE" | sudo ./scripts/setup/install_systemd_services.sh
        ;;
    *)
        echo "無効な選択です。スキップします。"
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ4: サービスの起動確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "インストールされたサービス:"
systemctl list-unit-files | grep backup-management || echo "サービスが見つかりません"
echo ""

read -p "本番環境サービスを起動しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "本番環境サービスを起動しています..."
    sudo systemctl start backup-management-production

    echo ""
    echo "サービス状態:"
    sudo systemctl status backup-management-production --no-pager

    echo ""
    echo "自動起動を有効化しますか？"
    read -p "(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl enable backup-management-production
        echo "✅ 自動起動を有効化しました"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║              ✅ セットアップが完了しました！                  ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "アクセスURL:"
echo "  - 開発環境: http://192.168.0.187:5001"
echo "  - 本番環境: https://192.168.0.187"
echo ""
echo "次のステップ:"
echo "  1. ブラウザでアクセス"
echo "  2. 初回ログイン"
echo "  3. バックアップジョブの作成"
echo ""
