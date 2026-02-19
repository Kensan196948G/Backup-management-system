#!/usr/bin/env python
"""
ログイン問題診断スクリプト
400 Bad Request、401 Unauthorized、CSRF Token エラーなどを診断

使用方法:
    python scripts/diagnose_login.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_env_file():
    """Check .env file existence and content"""
    print("=" * 70)
    print("1. 環境変数ファイル (.env) のチェック")
    print("=" * 70)

    # インストールパス: C:\temp\BackupSystem
    env_path = project_root / ".env"

    if not env_path.exists():
        print("❌ .envファイルが存在しません")
        print(f"   パス: {env_path}")
        print("   対処法: .env.exampleをコピーして.envを作成してください")
        print("\nPowerShellコマンド:")
        print("  cd C:\\temp\\BackupSystem")
        print("  Copy-Item .env.example .env")
        return False

    print(f"✅ .envファイルが存在します: {env_path}")

    # Read .env file
    with open(env_path, "r", encoding="utf-8") as f:
        env_content = f.read()

    # Check SECRET_KEY
    print("\n2. SECRET_KEY のチェック")
    print("-" * 70)

    secret_key_found = False
    secret_key_value = None

    for line in env_content.split("\n"):
        if line.strip().startswith("SECRET_KEY="):
            secret_key_found = True
            secret_key_value = line.split("=", 1)[1].strip()
            break

    if not secret_key_found:
        print("❌ SECRET_KEYが.envファイルに設定されていません")
        return False

    if not secret_key_value or secret_key_value == "your-secret-key-here":
        print("❌ SECRET_KEYがデフォルト値のままです")
        print(f"   現在の値: {secret_key_value}")
        print("   対処法: 以下のコマンドで新しいキーを生成してください:")
        print('   python -c "import secrets; print(secrets.token_hex(32))"')
        return False

    if len(secret_key_value) < 32:
        print("⚠️  SECRET_KEYが短すぎます（32文字以上推奨）")
        print(f"   現在の長さ: {len(secret_key_value)}")
        return False

    print(f"✅ SECRET_KEYが設定されています（長さ: {len(secret_key_value)}文字）")

    # Check FLASK_ENV
    print("\n3. FLASK_ENV のチェック")
    print("-" * 70)

    flask_env_found = False
    flask_env_value = None

    for line in env_content.split("\n"):
        if line.strip().startswith("FLASK_ENV="):
            flask_env_found = True
            flask_env_value = line.split("=", 1)[1].strip()
            break

    if not flask_env_found:
        print("⚠️  FLASK_ENVが設定されていません（デフォルト: development）")
    else:
        print(f"✅ FLASK_ENV = {flask_env_value}")

        if flask_env_value == "production":
            print("\n   ⚠️  本番モード (production) の注意点:")
            print("   - SESSION_COOKIE_SECURE=True のため、HTTPSが必要")
            print("   - HTTPで実行する場合は400エラーが発生します")
            print("   - 対処法: HTTP環境ではFLASK_ENV=developmentを使用")

    return True


def check_database():
    """Check database and admin user"""
    print("\n" + "=" * 70)
    print("4. データベースのチェック")
    print("=" * 70)

    try:
        from app import create_app
        from app.models import User, db

        # Create app without starting server
        os.environ["FLASK_ENV"] = "development"  # Force development mode for check
        app = create_app("development")

        with app.app_context():
            # Check if tables exist
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            if not tables:
                print("❌ データベーステーブルが存在しません")
                print("   対処法: python scripts/fix_database.py を実行してください")
                return False

            print(f"✅ データベーステーブルが存在します（{len(tables)}個）")

            # Check admin user
            admin_count = User.query.filter_by(role="admin").count()

            if admin_count == 0:
                print("❌ 管理者ユーザーが存在しません")
                print("   対処法: python scripts/fix_database.py を実行してください")
                return False

            print(f"✅ 管理者ユーザーが存在します（{admin_count}人）")

            # List admin users
            admins = User.query.filter_by(role="admin").all()
            for admin in admins:
                status = "アクティブ" if admin.is_active else "無効"
                print(f"   - {admin.username} ({admin.email}) - {status}")

        return True

    except Exception as e:
        print(f"❌ データベースチェック中にエラーが発生しました: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def check_config():
    """Check Flask configuration"""
    print("\n" + "=" * 70)
    print("5. Flask設定のチェック")
    print("=" * 70)

    try:
        from app.config import get_config

        # Check development config
        print("\n[開発モード (development)]")
        dev_config = get_config("development")
        print(f"  DEBUG: {dev_config.DEBUG}")
        print(f"  WTF_CSRF_ENABLED: {dev_config.WTF_CSRF_ENABLED}")
        print(f"  SESSION_COOKIE_SECURE: {dev_config.SESSION_COOKIE_SECURE}")

        # Check production config
        print("\n[本番モード (production)]")
        prod_config = get_config("production")
        print(f"  DEBUG: {prod_config.DEBUG}")
        print(f"  WTF_CSRF_ENABLED: {prod_config.WTF_CSRF_ENABLED}")
        print(f"  SESSION_COOKIE_SECURE: {prod_config.SESSION_COOKIE_SECURE}")

        print("\n⚠️  重要:")
        print("  本番モードでHTTP接続を使用する場合、SESSION_COOKIE_SECURE=True")
        print("  が原因で400エラーが発生します。")
        print("  → 解決策: 開発モードで起動するか、HTTPSを使用してください")

        return True

    except Exception as e:
        print(f"❌ 設定チェック中にエラーが発生しました: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def provide_recommendations():
    """Provide recommendations based on checks"""
    print("\n" + "=" * 70)
    print("6. 推奨される対処法")
    print("=" * 70)

    print("\n【400 Bad Request エラーの場合】")
    print("原因: 本番モード(production)でHTTP接続を使用しているため")
    print("\n対処法A: 開発モードで起動（推奨）")
    print("  1. .envファイルを開く: notepad C:\\temp\\BackupSystem\\.env")
    print("  2. FLASK_ENV=production を FLASK_ENV=development に変更")
    print("  3. サービス再起動: Restart-Service BackupManagementSystem")
    print("\n対処法B: 本番環境でHTTP許可（一時的）")
    print("  1. cd C:\\temp\\BackupSystem")
    print("  2. .\\venv\\Scripts\\python.exe scripts\\fix_production_http.py")
    print("  3. サービス再起動: Restart-Service BackupManagementSystem")

    print("\n【401 Unauthorized エラーの場合】")
    print("原因: 認証が必要なページに未ログイン状態でアクセス")
    print("\n対処法: ログインページから認証してください")
    print("  URL: http://192.168.3.92:5000/auth/login")

    print("\n【SECRET_KEY エラーの場合】")
    print("原因: SECRET_KEYが未設定または不適切")
    print("\n対処法:")
    print("  1. 新しいキー生成:")
    print('     python -c "import secrets; print(secrets.token_hex(32))"')
    print("  2. .envファイルに設定:")
    print("     SECRET_KEY=（生成されたキー）")
    print("  3. サービス再起動")


def main():
    """Main diagnostic function"""
    print("\n" + "=" * 70)
    print("3-2-1-1-0 バックアップ管理システム - ログイン問題診断")
    print("=" * 70)
    print()

    results = []

    # Run checks
    results.append(("環境変数ファイル", check_env_file()))
    results.append(("データベース", check_database()))
    results.append(("Flask設定", check_config()))

    # Summary
    print("\n" + "=" * 70)
    print("診断結果サマリー")
    print("=" * 70)

    all_passed = True
    for name, passed in results:
        status = "✅ 正常" if passed else "❌ 問題あり"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("✅ すべてのチェックが成功しました！")
        print("\nそれでもログインできない場合:")
        print("  1. ブラウザのキャッシュをクリア")
        print("  2. プライベートブラウジングモードで試す")
        print("  3. サービスログを確認: Get-Content C:\\temp\\BackupSystem\\logs\\service_stderr.log -Tail 50")
    else:
        print("❌ 問題が検出されました。上記の対処法を参考に修正してください。")

    # Provide recommendations
    provide_recommendations()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
