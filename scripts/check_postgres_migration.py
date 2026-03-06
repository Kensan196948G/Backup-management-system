#!/usr/bin/env python3
"""
PostgreSQL移行前チェックスクリプト
移行準備の確認と接続テストを行う
"""
import sys
import os


def check_environment():
    """環境変数の確認"""
    required_vars = ['DATABASE_URL']
    optional_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']

    print("=== 環境変数チェック ===")
    for var in required_vars:
        val = os.environ.get(var)
        if val:
            # パスワードをマスク
            if 'password' in val.lower() or ':' in val:
                print(f"  OK {var}: [設定済み - 値を隠す]")
            else:
                print(f"  OK {var}: {val}")
        else:
            print(f"  WARN {var}: 未設定（SQLiteを使用）")

    for var in optional_vars:
        val = os.environ.get(var)
        status = "OK 設定済み" if val else "INFO 未設定"
        print(f"  {status}: {var}")


def check_psycopg2():
    """psycopg2のインストール確認"""
    print("\n=== PostgreSQLドライバーチェック ===")
    try:
        import psycopg2
        print(f"  OK psycopg2: {psycopg2.__version__}")
        return True
    except ImportError:
        print("  NG psycopg2: 未インストール")
        print("  インストール: pip install psycopg2-binary")
        return False


def check_alembic():
    """alembicの設定確認"""
    print("\n=== Alembicチェック ===")
    try:
        import alembic
        print(f"  OK alembic: {alembic.__version__}")
    except ImportError:
        print("  NG alembic: 未インストール")
        return False

    if os.path.exists('alembic.ini'):
        print("  OK alembic.ini: 存在")
    else:
        print("  NG alembic.ini: 不在")

    migrations_dir = 'migrations/versions'
    if os.path.exists(migrations_dir):
        files = [f for f in os.listdir(migrations_dir) if f.endswith('.py')]
        print(f"  OK マイグレーションファイル: {len(files)}件")
        for f in sorted(files):
            print(f"     - {f}")
    return True


def test_postgres_connection():
    """PostgreSQL接続テスト（環境変数が設定されている場合のみ）"""
    print("\n=== PostgreSQL接続テスト ===")
    db_url = os.environ.get('DATABASE_URL', '')

    if not db_url or 'postgresql' not in db_url:
        print("  INFO DATABASE_URLが未設定またはSQLite設定のためスキップ")
        print("  設定方法: export DATABASE_URL=postgresql://user:pass@host:5432/dbname")
        return False

    try:
        import psycopg2
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            connect_timeout=5
        )
        conn.close()
        print("  OK PostgreSQL接続: 成功")
        return True
    except Exception as e:
        print(f"  NG PostgreSQL接続エラー: {e}")
        return False


if __name__ == '__main__':
    print("PostgreSQL移行準備チェック")
    print("=" * 50)

    check_environment()
    has_driver = check_psycopg2()
    check_alembic()
    test_postgres_connection()

    print("\n=== サマリー ===")
    if has_driver:
        print("OK PostgreSQLドライバー準備完了")
        print("次のステップ: DATABASE_URL環境変数を設定してPostgreSQLに接続")
    else:
        print("要インストール: pip install psycopg2-binary")

    print("\n移行コマンド:")
    print("  DATABASE_URL=postgresql://... alembic upgrade head")
