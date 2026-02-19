#!/usr/bin/env python
"""
本番環境HTTP対応スクリプト

本番モード(production)でHTTP接続を使用する場合の設定を修正します。
セキュリティ上の理由から、最終的にはHTTPS環境への移行を推奨します。

使用方法:
    python scripts/fix_production_http.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def backup_file(file_path):
    """Create backup of file"""
    backup_path = Path(str(file_path) + ".backup")
    import shutil

    shutil.copy2(file_path, backup_path)
    print(f"✅ バックアップ作成: {backup_path}")
    return backup_path


def create_http_config():
    """Create HTTP-compatible production configuration"""
    print("=" * 70)
    print("本番環境HTTP対応設定の作成")
    print("=" * 70)
    print()

    config_file = project_root / "app" / "config.py"

    if not config_file.exists():
        print(f"❌ 設定ファイルが見つかりません: {config_file}")
        return False

    # Backup original file
    backup_file(config_file)

    # Read current config
    with open(config_file, "r", encoding="utf-8") as f:
        config_content = f.read()

    # Check if already patched
    if "ProductionHTTPConfig" in config_content:
        print("✅ HTTP対応設定は既に適用されています")
        return True

    # Add new configuration class before the config dictionary
    http_config_class = '''

class ProductionHTTPConfig(ProductionConfig):
    """
    本番環境HTTP接続用設定

    警告: HTTP接続はセキュリティリスクがあります。
    本番環境では必ずHTTPS（nginx + SSL証明書）への移行を検討してください。
    """

    # HTTP環境でもセッションCookieを許可
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = "http"

    def __init__(self):
        """Validate configuration and show warning"""
        super().__init__()
        import warnings
        warnings.warn(
            "⚠️  HTTP接続モードで実行中です。本番環境ではHTTPSの使用を強く推奨します。",
            RuntimeWarning
        )

'''

    # Find the position to insert (before "# Configuration dictionary")
    insert_position = config_content.find("# Configuration dictionary")

    if insert_position == -1:
        print("❌ 設定ファイルの構造が想定と異なります")
        return False

    # Insert the new class
    new_config_content = config_content[:insert_position] + http_config_class + config_content[insert_position:]

    # Update config dictionary to include new config
    new_config_content = new_config_content.replace(
        'config = {\n    "development": DevelopmentConfig,\n    "production": ProductionConfig,',
        'config = {\n    "development": DevelopmentConfig,\n    "production": ProductionConfig,\n    "production_http": ProductionHTTPConfig,',
    )

    # Write updated config
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(new_config_content)

    print("✅ HTTP対応設定クラス (ProductionHTTPConfig) を追加しました")
    return True


def update_env_file():
    """Update .env file to use production_http mode"""
    print("\n" + "=" * 70)
    print(".envファイルの更新")
    print("=" * 70)
    print()

    env_file = project_root / ".env"

    if not env_file.exists():
        print(f"❌ .envファイルが見つかりません: {env_file}")
        print("   対処法: .env.exampleをコピーして.envを作成してください")
        return False

    # Backup .env file
    backup_file(env_file)

    # Read .env file
    with open(env_file, "r", encoding="utf-8") as f:
        env_lines = f.readlines()

    # Update FLASK_ENV
    flask_env_found = False
    updated_lines = []

    for line in env_lines:
        if line.strip().startswith("FLASK_ENV="):
            flask_env_found = True
            updated_lines.append("FLASK_ENV=production_http\n")
            print("✅ FLASK_ENV を production_http に変更しました")
        else:
            updated_lines.append(line)

    if not flask_env_found:
        updated_lines.append("\n# Flask環境設定\n")
        updated_lines.append("FLASK_ENV=production_http\n")
        print("✅ FLASK_ENV=production_http を追加しました")

    # Write updated .env
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

    return True


def verify_secret_key():
    """Verify SECRET_KEY is properly set"""
    print("\n" + "=" * 70)
    print("SECRET_KEYの確認")
    print("=" * 70)
    print()

    env_file = project_root / ".env"

    with open(env_file, "r", encoding="utf-8") as f:
        env_content = f.read()

    secret_key_value = None
    for line in env_content.split("\n"):
        if line.strip().startswith("SECRET_KEY="):
            secret_key_value = line.split("=", 1)[1].strip()
            break

    if not secret_key_value or secret_key_value == "your-secret-key-here":
        print("⚠️  SECRET_KEYが設定されていません")
        print("\n新しいSECRET_KEYを生成しますか? (y/n): ", end="")

        try:
            response = input().strip().lower()
        except:
            response = "y"

        if response == "y":
            import secrets

            new_key = secrets.token_hex(32)

            # Update .env file
            with open(env_file, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

            updated_lines = []
            secret_key_updated = False

            for line in env_lines:
                if line.strip().startswith("SECRET_KEY="):
                    updated_lines.append(f"SECRET_KEY={new_key}\n")
                    secret_key_updated = True
                else:
                    updated_lines.append(line)

            if not secret_key_updated:
                updated_lines.append(f"\nSECRET_KEY={new_key}\n")

            with open(env_file, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)

            print(f"✅ 新しいSECRET_KEYを生成・設定しました")
            print(f"   キー: {new_key}")
        else:
            print("⚠️  手動でSECRET_KEYを設定してください")
            return False
    else:
        print(f"✅ SECRET_KEYが設定されています（長さ: {len(secret_key_value)}文字）")

    return True


def show_restart_instructions():
    """Show instructions for restarting the service"""
    print("\n" + "=" * 70)
    print("サービスの再起動が必要です")
    print("=" * 70)
    print()
    print("以下のコマンドでサービスを再起動してください:")
    print()
    print("PowerShell (管理者権限):")
    print("  Restart-Service BackupManagementSystem")
    print()
    print("または:")
    print("  Stop-Service BackupManagementSystem")
    print("  Start-Service BackupManagementSystem")
    print()
    print("サービス状態確認:")
    print("  Get-Service BackupManagementSystem")
    print()


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("3-2-1-1-0 バックアップ管理システム")
    print("本番環境HTTP対応スクリプト")
    print("=" * 70)
    print()
    print("このスクリプトは以下の処理を実行します:")
    print("  1. HTTP接続対応の設定クラスを追加")
    print("  2. .envファイルをproduction_httpモードに変更")
    print("  3. SECRET_KEYの確認・生成")
    print()
    print("⚠️  警告: HTTP接続はセキュリティリスクがあります")
    print("   本番環境では必ずHTTPS（nginx + SSL証明書）の使用を推奨します")
    print()
    print("続行しますか? (y/n): ", end="")

    try:
        response = input().strip().lower()
    except:
        response = "y"

    if response != "y":
        print("処理を中止しました")
        return 1

    print()

    # Execute fixes
    success = True
    success &= create_http_config()
    success &= update_env_file()
    success &= verify_secret_key()

    print("\n" + "=" * 70)
    if success:
        print("✅ すべての処理が完了しました！")
        show_restart_instructions()

        print("\n次のステップ:")
        print("  1. サービスを再起動")
        print("  2. ブラウザで http://192.168.3.92:5000 にアクセス")
        print("  3. 自動的に /auth/login にリダイレクトされることを確認")
        print("  4. ログイン（admin / パスワード）")
        print()
        print("⚠️  将来的な対応:")
        print("  - nginx + Let's Encrypt でHTTPS化を推奨")
        print("  - ドキュメント: deployment/windows/README.md のHTTPS設定を参照")
        return 0
    else:
        print("❌ 一部の処理が失敗しました")
        print("   ログを確認して、手動で修正してください")
        return 1


if __name__ == "__main__":
    sys.exit(main())
