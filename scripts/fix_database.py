#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データベース修復スクリプト

データベーステーブルを作成し、管理者ユーザーを作成します。
"""

import getpass
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import User


def fix_database():
    """データベースを修復"""
    print("=" * 70)
    print("データベース修復スクリプト")
    print("=" * 70)
    print()

    app = create_app("production")

    with app.app_context():
        print("📊 データベース接続確認中...")

        try:
            # データベーステーブルを作成
            print("📝 データベーステーブルを作成中...")
            db.create_all()
            print("✅ データベーステーブル作成完了")
            print()

            # テーブル一覧を表示
            print("📋 作成されたテーブル:")
            for table_name in db.metadata.tables.keys():
                print(f"  ✅ {table_name}")
            print()

            # ユーザー数を確認
            user_count = User.query.count()
            print(f"👤 現在のユーザー数: {user_count}")
            print()

            if user_count == 0:
                print("=" * 70)
                print("管理者ユーザー作成")
                print("=" * 70)
                print()

                # ユーザー名入力
                username = input("管理者ユーザー名 (デフォルト: admin): ").strip()
                if not username:
                    username = "admin"

                # メールアドレス入力
                email = input("管理者メールアドレス (デフォルト: admin@example.com): ").strip()
                if not email:
                    email = "admin@example.com"

                # パスワード入力
                while True:
                    password = getpass.getpass("管理者パスワード (8文字以上): ")

                    if len(password) < 8:
                        print("❌ パスワードは8文字以上である必要があります")
                        continue

                    password_confirm = getpass.getpass("パスワード（確認）: ")

                    if password != password_confirm:
                        print("❌ パスワードが一致しません")
                        continue

                    break

                # 管理者ユーザー作成
                try:
                    admin = User(username=username, email=email, role="admin", is_active=True)
                    admin.set_password(password)
                    db.session.add(admin)
                    db.session.commit()

                    print()
                    print("=" * 70)
                    print("✅ 管理者ユーザー作成成功！")
                    print("=" * 70)
                    print()
                    print(f"ユーザー名: {username}")
                    print(f"メールアドレス: {email}")
                    print(f"役割: admin")
                    print()
                    print("このユーザー名またはメールアドレスと設定したパスワードでログインできます。")
                    print()

                except Exception as e:
                    print()
                    print(f"❌ エラー: 管理者ユーザー作成に失敗しました")
                    print(f"詳細: {e}")
                    db.session.rollback()
                    sys.exit(1)

            else:
                print("✅ ユーザーが既に存在します")
                print()
                print("登録ユーザー:")
                users = User.query.all()
                for user in users:
                    status = "✅ 有効" if user.is_active else "❌ 無効"
                    print(f"  - {user.username} ({user.email}) - {user.role} - {status}")
                print()

            print("=" * 70)
            print("✅ データベース修復完了")
            print("=" * 70)

        except Exception as e:
            print()
            print(f"❌ エラー: データベース修復に失敗しました")
            print(f"詳細: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    fix_database()
