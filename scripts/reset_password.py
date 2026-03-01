#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
パスワードリセットスクリプト

既存ユーザーのパスワードを変更します。
"""

import getpass
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import User


def reset_password():
    """ユーザーのパスワードをリセット"""
    app = create_app("production")

    with app.app_context():
        print("=" * 60)
        print("パスワードリセット")
        print("=" * 60)
        print()

        # ユーザー一覧を表示
        users = User.query.all()

        if not users:
            print("⚠️  ユーザーが登録されていません")
            print()
            print("解決策: 新規管理者ユーザーを作成してください")
            print("  python scripts/create_admin.py")
            return

        print("登録ユーザー一覧:")
        print()
        for i, user in enumerate(users, 1):
            status = "✅ 有効" if user.is_active else "❌ 無効"
            print(f"{i}. {user.username} ({user.email}) - 役割: {user.role} - {status}")

        print()
        print("-" * 60)
        print()

        # ユーザー選択
        while True:
            try:
                choice = input(f"パスワードをリセットするユーザー番号を選択 (1-{len(users)}): ").strip()

                if not choice:
                    print("❌ 番号を入力してください")
                    continue

                choice_num = int(choice)

                if choice_num < 1 or choice_num > len(users):
                    print(f"❌ 1から{len(users)}の間で選択してください")
                    continue

                selected_user = users[choice_num - 1]
                break

            except ValueError:
                print("❌ 数字を入力してください")
            except KeyboardInterrupt:
                print("\n\nキャンセルしました")
                return

        print()
        print(f"選択されたユーザー: {selected_user.username} ({selected_user.email})")
        print()

        # 新しいパスワード入力
        while True:
            try:
                password = getpass.getpass("新しいパスワード: ")

                if len(password) < 8:
                    print("❌ パスワードは8文字以上である必要があります")
                    continue

                password_confirm = getpass.getpass("パスワード（確認）: ")

                if password != password_confirm:
                    print("❌ パスワードが一致しません")
                    continue

                break

            except KeyboardInterrupt:
                print("\n\nキャンセルしました")
                return

        # パスワードを更新
        try:
            selected_user.set_password(password)
            db.session.commit()

            print()
            print("=" * 60)
            print("✅ パスワードリセット成功！")
            print("=" * 60)
            print()
            print(f"ユーザー名: {selected_user.username}")
            print(f"メールアドレス: {selected_user.email}")
            print(f"役割: {selected_user.role}")
            print()
            print("このユーザー名またはメールアドレスと新しいパスワードでログインできます。")
            print()

        except Exception as e:
            print()
            print(f"❌ エラー: パスワードリセットに失敗しました")
            print(f"詳細: {e}")
            db.session.rollback()


if __name__ == "__main__":
    reset_password()
