#!/usr/bin/env python3
"""
完全なシステム統合テスト
ログイン、ダッシュボード、ナビゲーション、全ページアクセスを確認
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app import create_app


def test_complete_system():
    """Comprehensive system integration test"""
    print("\n" + "=" * 70)
    print("3-2-1-1-0 バックアップ管理システム - 完全統合テスト")
    print("=" * 70)

    app = create_app("development")

    with app.test_client() as client:
        # Test 1: Login
        print("\n[1/5] ログイン認証テスト...")
        response = client.post("/auth/login", data={"username": "admin", "password": "Admin123!"}, follow_redirects=False)
        if response.status_code not in [200, 302]:
            print(f"  ❌ FAILED: {response.status_code}")
            return False
        print("  ✅ PASSED")

        # Test 2: Dashboard
        print("\n[2/5] ダッシュボード表示テスト...")
        response = client.get("/dashboard", follow_redirects=True)
        if response.status_code != 200:
            print(f"  ❌ FAILED: {response.status_code}")
            return False
        html = response.data.decode("utf-8")
        required_elements = ["showStatModal", "complianceModal", "successModal", "alertsModal", "mediaModal"]
        missing = [el for el in required_elements if el not in html]
        if missing:
            print(f"  ❌ FAILED: Missing {missing}")
            return False
        print("  ✅ PASSED - モーダル機能確認")

        # Test 3: Navigation links
        print("\n[3/5] ナビゲーションリンク機能テスト...")
        navigation_routes = [
            ("/jobs/", "Jobs"),
            ("/media/", "Media"),
            ("/verification/", "Verification"),
            ("/reports/", "Reports"),
        ]

        failed = []
        for route, name in navigation_routes:
            response = client.get(route, follow_redirects=True)
            if response.status_code != 200:
                failed.append(f"{name}({route}): {response.status_code}")

        if failed:
            print(f"  ❌ FAILED:\n    {chr(10).join('    ' + f for f in failed)}")
            return False
        print("  ✅ PASSED - 全リンク機能確認")

        # Test 4: API endpoints
        print("\n[4/5] APIエンドポイント機能テスト...")
        api_endpoints = [
            "/api/dashboard/stats",
            "/api/dashboard/compliance-chart",
            "/api/dashboard/success-rate-chart",
            "/api/dashboard/storage-chart",
        ]

        failed = []
        for endpoint in api_endpoints:
            response = client.get(endpoint)
            if response.status_code != 200:
                failed.append(f"{endpoint}: {response.status_code}")

        if failed:
            print(f"  ❌ FAILED:\n    {chr(10).join('    ' + f for f in failed)}")
            return False
        print("  ✅ PASSED - 全APIエンドポイント機能確認")

        # Test 5: Navbar presence on all pages
        print("\n[5/5] 全ページナビゲーションバー確認テスト...")
        test_pages = ["/dashboard", "/jobs/", "/media/", "/verification/", "/reports/"]

        failed = []
        for page in test_pages:
            response = client.get(page, follow_redirects=True)
            html = response.data.decode("utf-8")
            if "navbar navbar-expand-lg" not in html:
                failed.append(f"{page}: navbar missing")
            if "バックアップ管理システム" not in html:
                failed.append(f"{page}: brand missing")

        if failed:
            print(f"  ❌ FAILED:\n    {chr(10).join('    ' + f for f in failed)}")
            return False
        print("  ✅ PASSED - 全ページナビゲーション確認")

        return True


if __name__ == "__main__":
    try:
        success = test_complete_system()

        print("\n" + "=" * 70)
        if success:
            print("✅ 完全統合テスト成功!")
            print("=" * 70)
            print("\n✨ システムの準備完了")
            print("\n開発環境での動作確認コマンド:")
            print("  source venv/bin/activate")
            print("  python run.py --config development")
            print("\nブラウザでのアクセス:")
            print("  URL: http://127.0.0.1:5000")
            print("  ユーザー: admin")
            print("  パスワード: Admin123!")
            print("\n確認ポイント:")
            print("  1. ログイン画面が表示される")
            print("  2. ダッシュボードの統計カード（4つ）がクリック可能")
            print("  3. モーダルダイアログが表示される")
            print("  4. ナビゲーションメニューから全ページにアクセス可能")
            print("  5. 各ページでナビゲーションバーが表示される")
            sys.exit(0)
        else:
            print("❌ テストが失敗しました")
            print("=" * 70)
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
