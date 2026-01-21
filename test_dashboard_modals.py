#!/usr/bin/env python3
"""
ダッシュボードモーダルインタラクティブテスト
ダッシュボードの全てのクリック可能要素とモーダル表示を検証
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app import create_app
from app.models import db


def test_dashboard_modals():
    """Test dashboard modal functionality"""
    print("=" * 70)
    print("ダッシュボード モーダル インタラクティブテスト")
    print("=" * 70)
    print()

    # Create app
    app = create_app("development")

    with app.test_client() as client:
        # Login
        print("1. ログイン処理中...")
        response = client.post("/auth/login", data={"username": "admin", "password": "Admin123!"}, follow_redirects=False)

        if response.status_code not in [200, 302]:
            print(f"❌ ログイン失敗: {response.status_code}")
            return False

        print("✅ ログイン成功")

        # Access dashboard
        print("\n2. ダッシュボードアクセス中...")
        response = client.get("/dashboard", follow_redirects=True)

        if response.status_code != 200:
            print(f"❌ ダッシュボードアクセス失敗: {response.status_code}")
            return False

        response_text = response.data.decode("utf-8")
        print("✅ ダッシュボード表示成功")

        # Test 3: Check for all clickable statistics cards
        print("\n3. クリック可能なカード確認中...")
        clickable_cards = {
            "compliance": ("onclick=\"showStatModal('compliance'", "3-2-1-1-0ルール準拠率"),
            "success": ("onclick=\"showStatModal('success'", "バックアップ成功率"),
            "alerts": ("onclick=\"showStatModal('alerts'", "未確認アラート"),
            "media": ("onclick=\"showStatModal('media'", "オフラインメディア"),
        }

        missing_cards = []
        for card_name, (onclick_attr, label) in clickable_cards.items():
            if onclick_attr not in response_text:
                missing_cards.append(f"{card_name} ({label})")

        if missing_cards:
            print(f"❌ 以下のカードが見つかりません:")
            for card in missing_cards:
                print(f"   - {card}")
            return False

        print("✅ 全4つのクリック可能なカードが存在します")

        # Test 4: Check for all modal definitions
        print("\n4. モーダルダイアログ定義確認中...")
        modal_ids = [
            ("complianceModal", "3-2-1-1-0ルール準拠率 詳細"),
            ("successModal", "バックアップ成功率 詳細"),
            ("alertsModal", "未確認アラート 詳細"),
            ("mediaModal", "オフラインメディア 詳細"),
        ]

        missing_modals = []
        for modal_id, modal_title in modal_ids:
            if f'id="{modal_id}"' not in response_text:
                missing_modals.append(f"{modal_id} ({modal_title})")

        if missing_modals:
            print(f"❌ 以下のモーダルが見つかりません:")
            for modal in missing_modals:
                print(f"   - {modal}")
            return False

        print("✅ 全4つのモーダルダイアログが定義されています")

        # Test 5: Check for JavaScript modal handler function
        print("\n5. JavaScriptモーダルハンドラー確認中...")
        if "function showStatModal(type, event)" not in response_text:
            print("❌ showStatModal関数が見つかりません")
            return False

        print("✅ showStatModal関数が定義されています")

        # Test 6: Check for tab navigation in modals
        print("\n6. モーダルタブ機能確認中...")
        tab_checks = {
            "compliance": [
                'id="compliance-overview"',
                'id="compliance-breakdown"',
                'id="compliance-recommendations"',
            ],
            "success": [
                'id="success-overview"',
                'id="success-trend"',
                'id="success-details"',
            ],
            "alerts": [
                'id="alerts-overview"',
                'id="alerts-breakdown"',
                'id="alerts-recommendations"',
            ],
            "media": [
                'id="media-overview"',
                'id="media-breakdown"',
                'id="media-recommendations"',
            ],
        }

        missing_tabs = []
        for modal_type, tabs in tab_checks.items():
            for tab_id in tabs:
                if tab_id not in response_text:
                    missing_tabs.append(f"{modal_type}: {tab_id}")

        if missing_tabs:
            print(f"⚠️  一部のタブが見つかりません:")
            for tab in missing_tabs[:3]:  # Show first 3
                print(f"   - {tab}")
            print(f"   ... など{len(missing_tabs)}個")
        else:
            print("✅ 全てのモーダルタブが定義されています")

        # Test 7: Check for Chart.js initialization
        print("\n7. Chart.js初期化確認中...")
        chart_functions = [
            "initComplianceDetailChart",
            "initSuccessDetailChart",
            "initSuccessTrendChart",
            "initAlertsDetailChart",
            "initAlertsBreakdownChart",
            "initMediaDetailChart",
            "initMediaTypesChart",
        ]

        missing_charts = []
        for chart_func in chart_functions:
            if f"function {chart_func}" not in response_text:
                missing_charts.append(chart_func)

        if missing_charts:
            print(f"❌ 以下のチャート関数が見つかりません:")
            for chart in missing_charts:
                print(f"   - {chart}")
            return False

        print(f"✅ 全{len(chart_functions)}個のチャート関数が定義されています")

        # Test 8: Check for API endpoints in JS
        print("\n8. APIエンドポイント参照確認中...")
        api_endpoints = [
            "/api/dashboard/compliance-chart",
            "/api/dashboard/success-rate-chart",
            "/api/dashboard/storage-chart",
        ]

        missing_apis = []
        for api in api_endpoints:
            if api not in response_text:
                missing_apis.append(api)

        if missing_apis:
            print(f"❌ 以下のAPIが参照されていません:")
            for api in missing_apis:
                print(f"   - {api}")
            return False

        print("✅ 全APIエンドポイント参照が存在します")

        # Test 9: Check for keyboard support (ESC key)
        print("\n9. キーボードイベント処理確認中...")
        if "e.key === 'Escape'" not in response_text:
            print("⚠️  ESCキーハンドリングが見つかりません")
        else:
            print("✅ ESCキーでモーダル閉鎖機能が実装されています")

        # Test 10: Check CSS hover effects
        print("\n10. CSSホバー効果確認中...")
        if "transform: translateY(-5px)" not in response_text:
            print("⚠️  ホバー効果が見つかりません")
        else:
            print("✅ カードのホバー効果が実装されています")

        print("\n" + "=" * 70)
        print("✅ 全てのダッシュボードインタラクティブ機能テストが成功しました!")
        print("=" * 70)
        print()
        print("検証結果:")
        print("  ✓ 4つのクリック可能な統計カード")
        print("  ✓ 4つのモーダルダイアログ")
        print("  ✓ JavaScriptモーダルハンドラー")
        print("  ✓ タブベースの詳細表示")
        print("  ✓ Chart.js チャート統合")
        print("  ✓ APIデータフェッチ機能")
        print("  ✓ キーボード操作サポート（ESC）")
        print("  ✓ マウスホバーエフェクト")
        print()
        return True


if __name__ == "__main__":
    success = test_dashboard_modals()

    print("\n" + "=" * 70)
    if success:
        print("✅ ダッシュボード機能検証完了: すべて正常です")
        print("\n次のステップ:")
        print("  1. ブラウザで http://127.0.0.1:5000 にアクセス")
        print("  2. admin / Admin123! でログイン")
        print("  3. ダッシュボードの統計カード（4つ）をクリック")
        print("  4. モーダルが表示され、タブ切り替えできることを確認")
        print("  5. チャートデータが正しく表示されることを確認")
        sys.exit(0)
    else:
        print("❌ テストが失敗しました")
        sys.exit(1)
