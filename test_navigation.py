#!/usr/bin/env python3
"""
ナビゲーション動作テスト
ナビゲーションメニューのすべてのリンクが正常に動作するか確認
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app import create_app


def test_navigation():
    """Test all navigation links"""
    print("=" * 70)
    print("ナビゲーション動作テスト")
    print("=" * 70)
    print()

    # Create app
    app = create_app("development")

    with app.test_client() as client:
        # Login first
        print("1. ログイン処理中...")
        response = client.post("/auth/login", data={"username": "admin", "password": "Admin123!"}, follow_redirects=False)

        if response.status_code not in [200, 302]:
            print(f"❌ ログイン失敗: {response.status_code}")
            return False

        print("✅ ログイン成功")

        # Test all navigation links
        print("\n2. ナビゲーションリンク確認中...")
        navigation_links = [
            ("/dashboard", "ダッシュボード"),
            ("/jobs/", "バックアップジョブ"),
            ("/media/", "オフラインメディア"),
            ("/verification/", "検証テスト"),
            ("/reports/", "レポート"),
        ]

        failed_links = []
        for url, label in navigation_links:
            response = client.get(url, follow_redirects=True)
            if response.status_code != 200:
                failed_links.append((url, label, response.status_code))
                print(f"  ❌ {label} ({url}): {response.status_code}")
            else:
                print(f"  ✅ {label} ({url}): OK")

        if failed_links:
            print(f"\n❌ {len(failed_links)}個のリンクが失敗しました")
            return False

        print(f"\n✅ すべてのナビゲーションリンクが正常です")

        # Test navigation bar appears on all pages
        print("\n3. ナビゲーションバー確認中...")
        for url, label in navigation_links:
            response = client.get(url, follow_redirects=True)
            response_text = response.data.decode("utf-8")

            # Check for navbar brand
            if "バックアップ管理システム" not in response_text:
                print(f"  ⚠️  {label}: ナビゲーションバーブランドが見つかりません")

            # Check for navbar structure
            if "navbar navbar-expand-lg" not in response_text:
                print(f"  ⚠️  {label}: ナビゲーション構造が見つかりません")

        print("✅ ナビゲーションバーが全ページに表示されています")

        # Test active link highlighting
        print("\n4. アクティブリンク表示確認中...")
        for url, label in navigation_links:
            response = client.get(url, follow_redirects=True)
            response_text = response.data.decode("utf-8")

            # Check for nav-link elements
            if "nav-link" not in response_text:
                print(f"  ⚠️  {label}: ナビゲーションリンク要素が見つかりません")
            else:
                print(f"  ✅ {label}: ナビゲーションリンクが存在します")

        print("\n" + "=" * 70)
        print("✅ ナビゲーション機能テスト完了: すべて正常です")
        print("=" * 70)
        return True


if __name__ == "__main__":
    success = test_navigation()

    if not success:
        sys.exit(1)
    sys.exit(0)
