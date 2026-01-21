#!/usr/bin/env python3
"""
ダッシュボード手動テストスクリプト
開発環境でダッシュボードが正常に動作するか確認
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app import create_app
from app.models import User, db


def test_dashboard():
    """Test dashboard loading without errors"""
    print("=" * 70)
    print("ダッシュボード動作確認テスト")
    print("=" * 70)
    print()

    # Create app
    app = create_app("development")

    with app.test_client() as client:
        # Login
        print("1. ログイン中...")
        response = client.post("/auth/login", data={"username": "admin", "password": "Admin123!"}, follow_redirects=False)

        if response.status_code not in [200, 302]:
            print(f"❌ ログイン失敗: {response.status_code}")
            print(f"   レスポンス: {response.data.decode('utf-8')[:200]}")
            return False

        print("✅ ログイン成功")

        # Access dashboard
        print("\n2. ダッシュボードアクセス中...")
        response = client.get("/dashboard", follow_redirects=True)

        if response.status_code != 200:
            print(f"❌ ダッシュボードアクセス失敗: {response.status_code}")
            print(f"   レスポンス: {response.data.decode('utf-8')[:500]}")
            return False

        # Check for errors in response (skip JavaScript error handling code)
        response_text = response.data.decode("utf-8")

        # Check for actual server errors (not JavaScript strings)
        if "<h1>Error</h1>" in response_text or "<h1>エラー</h1>" in response_text:
            print("❌ ダッシュボードにサーバーエラーが含まれています:")
            # Extract error message
            import re

            error_match = re.search(r"<h1>Error</h1><p>(.*?)</p>", response_text, re.DOTALL)
            if error_match:
                print(f"   {error_match.group(1)}")
            return False

        if "Entity namespace" in response_text:
            print("❌ モデルプロパティエラーが含まれています:")
            # Extract entity namespace error
            import re

            error_match = re.search(r'Entity namespace.*?"', response_text, re.DOTALL)
            if error_match:
                print(f"   {error_match.group(0)}")
            return False

        print("✅ ダッシュボード正常表示")

        # Check key elements are present
        print("\n3. ダッシュボード要素確認中...")
        required_elements = ["ダッシュボード", "バックアップジョブ", "準拠率"]

        missing_elements = []
        for element in required_elements:
            if element not in response_text:
                missing_elements.append(element)

        if missing_elements:
            print(f"⚠️  一部の要素が見つかりません: {missing_elements}")
        else:
            print("✅ 全ての主要要素が存在します")

        # Check API endpoints
        print("\n4. API エンドポイント確認中...")
        api_endpoints = [
            "/api/dashboard/stats",
            "/api/dashboard/compliance-chart",
            "/api/dashboard/success-rate-chart",
            "/api/dashboard/storage-chart",
        ]

        for endpoint in api_endpoints:
            response = client.get(endpoint)
            if response.status_code != 200:
                print(f"❌ API エラー {endpoint}: {response.status_code}")
                print(f"   レスポンス: {response.data.decode('utf-8')[:200]}")
                return False

        print("✅ 全てのAPI エンドポイントが正常")

        return True


if __name__ == "__main__":
    success = test_dashboard()

    print("\n" + "=" * 70)
    if success:
        print("✅ 全てのテストが成功しました!")
        print("\nダッシュボードは正常に動作しています。")
        print("Windows本番環境への適用準備が整いました。")
        sys.exit(0)
    else:
        print("❌ テストが失敗しました")
        print("\n修正が必要です。")
        sys.exit(1)
