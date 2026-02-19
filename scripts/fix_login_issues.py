#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ログイン問題自動修復スクリプト

Windows本番環境でのログイン問題を自動診断・修復します。
"""

import getpass
import os
import secrets
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import User


def check_and_fix_env():
    """環境変数をチェック・修正"""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    print("=" * 70)
    print("環境変数チェック")
    print("=" * 70)
    print()

    if not os.path.exists(env_path):
        print("❌ .envファイルが見つかりません")
        print(f"   パス: {env_path}")
        return False

    with open(env_path, "r", encoding="utf-8") as f:
        env_content = f.read()

    # SECRET_KEYチェック
    if "SECRET_KEY=" not in env_content or "SECRET_KEY=\n" in env_content:
        print("❌ SECRET_KEYが設定されていません")

        # 自動生成
        new_secret_key = secrets.token_hex(32)
        print(f"✅ 新しいSECRET_KEYを生成しました")
        print(f"   SECRET_KEY={new_secret_key}")
        print()

        # .envファイルに追加または更新
        lines = env_content.split("\n")
        found = False

        for i, line in enumerate(lines):
            if line.startswith("SECRET_KEY="):
                lines[i] = f"SECRET_KEY={new_secret_key}"
                found = True
                break

        if not found:
            lines.append(f"SECRET_KEY={new_secret_key}")

        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print("✅ .envファイルを更新しました")
        print()
        print("⚠️  重要: Windowsサービスを再起動してください")
        print("   PS> Restart-Service -Name BackupManagementSystem")
        print()

        return True
    else:
        print("✅ SECRET_KEYは設定されています")

        # 長さチェック
        import re

        match = re.search(r"SECRET_KEY\s*=\s*(.+)", env_content)
        if match:
            secret_key = match.group(1).strip()
            print(f"   長さ: {len(secret_key)}文字")

            if len(secret_key) < 32:
                print("⚠️  SECRET_KEYが短すぎます（32文字以上推奨）")
                return False

    print()
    return True


def check_and_fix_database():
    """データベースをチェック・修復"""
    print("=" * 70)
    print("データベースチェック")
    print("=" * 70)
    print()

    app = create_app("production")

    with app.app_context():
        try:
            # テーブル作成
            db.create_all()
            print("✅ データベーステーブル確認/作成完了")

            # テーブル一覧
            table_count = len(db.metadata.tables)
            print(f"   テーブル数: {table_count}")

            # ユーザー確認
            user_count = User.query.count()
            print(f"   ユーザー数: {user_count}")
            print()

            if user_count == 0:
                print("⚠️  管理者ユーザーが存在しません")
                print()
                print("管理者ユーザーを作成しますか？ (Y/n): ", end="")

                choice = input().strip().lower()

                if choice != "n":
                    create_admin_user()
            else:
                print("✅ ユーザーが存在します")
                print()
                print("登録ユーザー:")
                users = User.query.all()
                for user in users:
                    status = "✅ 有効" if user.is_active else "❌ 無効"
                    print(f"  - {user.username} ({user.email}) - {user.role} - {status}")
                print()

                # パスワードリセット提案
                print("パスワードをリセットしますか？ (y/N): ", end="")
                choice = input().strip().lower()

                if choice == "y":
                    reset_user_password(users)

            return True

        except Exception as e:
            print(f"❌ データベースエラー: {e}")
            import traceback

            traceback.print_exc()
            return False


def create_admin_user():
    """管理者ユーザー作成"""
    print()
    print("=" * 70)
    print("管理者ユーザー作成")
    print("=" * 70)
    print()

    username = input("ユーザー名 (デフォルト: admin): ").strip() or "admin"
    email = input("メールアドレス (デフォルト: admin@example.com): ").strip() or "admin@example.com"

    while True:
        password = getpass.getpass("パスワード (8文字以上): ")

        if len(password) < 8:
            print("❌ パスワードは8文字以上である必要があります")
            continue

        password_confirm = getpass.getpass("パスワード（確認）: ")

        if password != password_confirm:
            print("❌ パスワードが一致しません")
            continue

        break

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
        print(f"パスワード: （設定済み）")
        print()

    except Exception as e:
        print(f"❌ エラー: {e}")
        db.session.rollback()


def reset_user_password(users):
    """ユーザーパスワードリセット"""
    print()
    print("パスワードをリセットするユーザーを選択:")
    for i, user in enumerate(users, 1):
        print(f"  {i}. {user.username} ({user.email})")

    try:
        choice = int(input("\n番号を入力: ")) - 1
        selected_user = users[choice]

        print(f"\n選択: {selected_user.username}")

        while True:
            password = getpass.getpass("新しいパスワード (8文字以上): ")

            if len(password) < 8:
                print("❌ パスワードは8文字以上である必要があります")
                continue

            password_confirm = getpass.getpass("パスワード（確認）: ")

            if password != password_confirm:
                print("❌ パスワードが一致しません")
                continue

            break

        selected_user.set_password(password)
        db.session.commit()

        print()
        print("✅ パスワードリセット成功！")
        print(f"   ユーザー名: {selected_user.username}")
        print(f"   メールアドレス: {selected_user.email}")
        print()

    except Exception as e:
        print(f"❌ エラー: {e}")
        db.session.rollback()


def main():
    """メイン処理"""
    print()
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                       ║")
    print("║           🔧 ログイン問題自動修復                                     ║")
    print("║           3-2-1-1-0 バックアップ管理システム                          ║")
    print("║                                                                       ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()

    # 環境変数チェック
    env_ok = check_and_fix_env()

    # データベースチェック
    db_ok = check_and_fix_database()

    print()
    print("=" * 70)
    print("修復完了")
    print("=" * 70)
    print()

    if env_ok and db_ok:
        print("✅ すべての問題が修復されました")
        print()
        print("次のステップ:")
        print("  1. Windowsサービスを再起動:")
        print("     PS> Restart-Service -Name BackupManagementSystem")
        print()
        print("  2. ブラウザでログイン:")
        print("     http://192.168.3.92:5000")
        print()
    else:
        print("⚠️  一部の問題が残っています")
        print("   上記のエラーメッセージを確認してください")

    print()


if __name__ == "__main__":
    main()
