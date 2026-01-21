#!/bin/bash
# ========================================
# SSL権限修正スクリプト
# ========================================

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║     🔧 SSL権限修正とサービス起動                             ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd /mnt/LinuxHDD/Backup-Management-System

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ1: www-dataをssl-certグループに追加"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo usermod -a -G ssl-cert www-data
echo "✅ www-dataをssl-certグループに追加しました"

echo ""
echo "グループメンバーシップ確認:"
getent group ssl-cert
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ2: サービスの再起動"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "backup-management-productionを再起動しています..."
sudo systemctl restart backup-management-production

echo "起動を待機中..."
sleep 5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ3: サービス状態の確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if sudo systemctl is-active --quiet backup-management-production; then
    echo "✅ backup-management-production: 起動成功！"
else
    echo "⚠️  backup-management-production: まだ起動中..."
    echo "追加で5秒待機します..."
    sleep 5
    if sudo systemctl is-active --quiet backup-management-production; then
        echo "✅ backup-management-production: 起動成功！"
    else
        echo "❌ backup-management-production: 起動失敗"
        echo "ログを確認してください: sudo journalctl -u backup-management-production -n 50"
        exit 1
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ4: ポートのリスニング確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if netstat -tuln 2>/dev/null | grep -q ":8443" || ss -tuln 2>/dev/null | grep -q ":8443"; then
    echo "✅ ポート8443: リスニング中"
else
    echo "⚠️  ポート8443: まだリスニングされていません"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ステップ5: HTTPSアクセステスト"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "HTTPSアクセステストを実行しています..."
if curl -k -s -o /dev/null -w "%{http_code}" https://192.168.0.187:8443 | grep -q "200\|30"; then
    echo "✅ HTTPS接続: 成功！"
else
    echo "アクセステスト中..."
    HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" https://192.168.0.187:8443)
    echo "HTTP Status Code: $HTTP_CODE"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║        🎉 セットアップが完全に完了しました！                ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 アクセスURL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "本番環境 (HTTPS):"
echo "  🌐 https://192.168.0.187:8443"
echo "  📋 ブックマーク: [本番] Backup System"
echo ""
echo "開発環境:"
echo "  🌐 http://192.168.0.187:5001"
echo "  📋 ブックマーク: [開発] Backup System"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 全サービス状態"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
sudo systemctl is-active backup-management-production && echo "  ✅ backup-management-production: 起動中" || echo "  ⚠️  backup-management-production: 停止中"
sudo systemctl is-active celery-worker-prod && echo "  ✅ celery-worker-prod: 起動中" || echo "  ⚠️  celery-worker-prod: 停止中"
sudo systemctl is-active celery-beat-prod && echo "  ✅ celery-beat-prod: 起動中" || echo "  ⚠️  celery-beat-prod: 停止中"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
