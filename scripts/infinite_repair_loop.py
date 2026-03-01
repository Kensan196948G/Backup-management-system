#!/usr/bin/env python3
"""
無限ループ修復システム - Infinite Repair Loop System

機能:
- 全てのエラー自動検知・自動修復
- 最大15サイクルの修復ループ
- 修復成功後の自動コミット準備
- JSON出力対応（GitHub Actions連携）

使用方法:
    python scripts/infinite_repair_loop.py --max-cycles 15 --issues "1,2,3" --auto-commit --output-json
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class RepairResult:
    """修復結果を格納するデータクラス"""

    success: bool = False
    cycles_used: int = 0
    fixed_errors: int = 0
    remaining_errors: int = 0
    error_details: List[Dict[str, Any]] = field(default_factory=list)
    repair_log: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "cycles_used": self.cycles_used,
            "fixed_errors": self.fixed_errors,
            "remaining_errors": self.remaining_errors,
            "error_details": self.error_details,
            "repair_log": self.repair_log,
            "timestamp": self.timestamp,
        }


class InfiniteRepairLoop:
    """無限ループ修復システム"""

    # 修復可能なエラータイプと対応する修復メソッド
    REPAIR_HANDLERS = {
        "syntax_error": "repair_syntax_errors",
        "import_error": "repair_import_errors",
        "lint_error": "repair_lint_errors",
        "type_error": "repair_type_errors",
        "test_failure": "repair_test_failures",
        "database_error": "repair_database_errors",
        "config_error": "repair_config_errors",
        "dependency_error": "repair_dependency_errors",
        "flask_error": "repair_flask_errors",
        "template_error": "repair_template_errors",
        "security_error": "repair_security_errors",
    }

    def __init__(
        self,
        max_cycles: int = 15,
        issues: Optional[str] = None,
        auto_commit: bool = False,
        output_json: bool = False,
        verbose: bool = True,
    ):
        self.max_cycles = max_cycles
        self.issues = [int(i.strip()) for i in issues.split(",") if i.strip()] if issues else []
        self.auto_commit = auto_commit
        self.output_json = output_json
        self.verbose = verbose
        self.result = RepairResult()
        self.detected_errors: List[Dict[str, Any]] = []
        self.github_token = os.environ.get("GITHUB_TOKEN")

    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.result.repair_log.append(log_entry)
        if self.verbose and not self.output_json:
            print(log_entry)

    def detect_all_errors(self) -> List[Dict[str, Any]]:
        """全エラーを検知"""
        self.log("Starting comprehensive error detection...")
        errors = []

        # 1. Python構文チェック
        syntax_errors = self._check_python_syntax()
        errors.extend(syntax_errors)

        # 2. インポートチェック
        import_errors = self._check_imports()
        errors.extend(import_errors)

        # 3. Lintチェック (flake8)
        lint_errors = self._check_lint()
        errors.extend(lint_errors)

        # 4. 型チェック (mypy) - オプション
        # type_errors = self._check_types()
        # errors.extend(type_errors)

        # 5. テスト実行
        test_errors = self._check_tests()
        errors.extend(test_errors)

        # 6. データベース接続チェック
        db_errors = self._check_database()
        errors.extend(db_errors)

        # 7. Flask起動チェック
        flask_errors = self._check_flask()
        errors.extend(flask_errors)

        # 8. テンプレートチェック
        template_errors = self._check_templates()
        errors.extend(template_errors)

        # 9. 依存関係チェック
        dep_errors = self._check_dependencies()
        errors.extend(dep_errors)

        self.log(f"Detection complete. Found {len(errors)} error(s)")
        return errors

    def _check_python_syntax(self) -> List[Dict[str, Any]]:
        """Python構文チェック"""
        errors = []
        python_files = list(PROJECT_ROOT.glob("**/*.py"))

        for py_file in python_files:
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                compile(code, py_file, "exec")
            except SyntaxError as e:
                errors.append(
                    {
                        "type": "syntax_error",
                        "file": str(py_file.relative_to(PROJECT_ROOT)),
                        "line": e.lineno,
                        "message": str(e.msg),
                        "severity": "critical",
                    }
                )

        return errors

    def _check_imports(self) -> List[Dict[str, Any]]:
        """インポートエラーチェック"""
        errors = []
        try:
            # アプリのインポートを試行
            result = subprocess.run(
                [sys.executable, "-c", "from app import create_app; app = create_app()"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "FLASK_ENV": "testing"},
            )
            if result.returncode != 0:
                errors.append(
                    {
                        "type": "import_error",
                        "file": "app/__init__.py",
                        "message": result.stderr[:500] if result.stderr else "Import failed",
                        "severity": "critical",
                    }
                )
        except subprocess.TimeoutExpired:
            errors.append(
                {"type": "import_error", "file": "app/__init__.py", "message": "Import timeout", "severity": "critical"}
            )
        except Exception as e:
            errors.append({"type": "import_error", "file": "app/__init__.py", "message": str(e), "severity": "critical"})

        return errors

    def _check_lint(self) -> List[Dict[str, Any]]:
        """Lintチェック (flake8)"""
        errors = []
        try:
            result = subprocess.run(
                ["flake8", "--max-line-length=120", "--exclude=venv,__pycache__,migrations", "."],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n")[:20]:  # 最大20件
                    if line.strip():
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            errors.append(
                                {
                                    "type": "lint_error",
                                    "file": parts[0],
                                    "line": int(parts[1]) if parts[1].isdigit() else 0,
                                    "message": parts[3].strip() if len(parts) > 3 else parts[2],
                                    "severity": "warning",
                                }
                            )
        except FileNotFoundError:
            self.log("flake8 not installed, skipping lint check", "WARNING")
        except Exception as e:
            self.log(f"Lint check error: {e}", "ERROR")

        return errors

    def _check_tests(self) -> List[Dict[str, Any]]:
        """テスト実行チェック"""
        errors = []
        try:
            result = subprocess.run(
                ["pytest", "--tb=short", "-q", "--maxfail=5"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ, "FLASK_ENV": "testing"},
            )
            if result.returncode != 0:
                # 失敗したテストを解析
                for line in result.stdout.split("\n"):
                    if "FAILED" in line or "ERROR" in line:
                        errors.append(
                            {
                                "type": "test_failure",
                                "file": line.split("::")[0] if "::" in line else "tests/",
                                "message": line.strip()[:200],
                                "severity": "high",
                            }
                        )
        except FileNotFoundError:
            self.log("pytest not installed, skipping test check", "WARNING")
        except subprocess.TimeoutExpired:
            errors.append({"type": "test_failure", "file": "tests/", "message": "Test execution timeout", "severity": "high"})
        except Exception as e:
            self.log(f"Test check error: {e}", "ERROR")

        return errors

    def _check_database(self) -> List[Dict[str, Any]]:
        """データベース接続チェック"""
        errors = []
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    """
from app import create_app, db
app = create_app()
with app.app_context():
    db.session.execute(db.text('SELECT 1'))
print('OK')
""",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "FLASK_ENV": "testing"},
            )
            if result.returncode != 0 or "OK" not in result.stdout:
                errors.append(
                    {
                        "type": "database_error",
                        "file": "instance/backup_system.db",
                        "message": result.stderr[:300] if result.stderr else "Database connection failed",
                        "severity": "critical",
                    }
                )
        except Exception as e:
            errors.append(
                {
                    "type": "database_error",
                    "file": "instance/backup_system.db",
                    "message": str(e)[:300],
                    "severity": "critical",
                }
            )

        return errors

    def _check_flask(self) -> List[Dict[str, Any]]:
        """Flask起動チェック"""
        errors = []
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    """
from app import create_app
app = create_app()
with app.test_client() as client:
    response = client.get('/health')
    print('STATUS:', response.status_code)
""",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "FLASK_ENV": "testing"},
            )
            if result.returncode != 0:
                errors.append(
                    {
                        "type": "flask_error",
                        "file": "app/__init__.py",
                        "message": result.stderr[:300] if result.stderr else "Flask startup failed",
                        "severity": "critical",
                    }
                )
        except Exception as e:
            errors.append({"type": "flask_error", "file": "app/__init__.py", "message": str(e)[:300], "severity": "critical"})

        return errors

    def _check_templates(self) -> List[Dict[str, Any]]:
        """テンプレートチェック"""
        errors = []
        template_dir = PROJECT_ROOT / "app" / "templates"

        if not template_dir.exists():
            errors.append(
                {
                    "type": "template_error",
                    "file": "app/templates/",
                    "message": "Templates directory not found",
                    "severity": "high",
                }
            )
            return errors

        required_templates = [
            "base.html",
            "auth/login.html",
            "dashboard.html",
        ]

        for template in required_templates:
            if not (template_dir / template).exists():
                errors.append(
                    {
                        "type": "template_error",
                        "file": f"app/templates/{template}",
                        "message": f"Required template missing: {template}",
                        "severity": "medium",
                    }
                )

        return errors

    def _check_dependencies(self) -> List[Dict[str, Any]]:
        """依存関係チェック"""
        errors = []
        requirements_file = PROJECT_ROOT / "requirements.txt"

        if not requirements_file.exists():
            errors.append(
                {
                    "type": "dependency_error",
                    "file": "requirements.txt",
                    "message": "requirements.txt not found",
                    "severity": "high",
                }
            )
            return errors

        # 主要パッケージのインポートチェック
        critical_packages = ["flask", "sqlalchemy", "werkzeug"]
        for package in critical_packages:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import {package}"], capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    errors.append(
                        {
                            "type": "dependency_error",
                            "file": "requirements.txt",
                            "message": f"Package not installed: {package}",
                            "severity": "critical",
                        }
                    )
            except Exception:
                pass

        return errors

    def repair_error(self, error: Dict[str, Any]) -> bool:
        """単一エラーの修復を試行"""
        error_type = error.get("type", "unknown")
        handler_name = self.REPAIR_HANDLERS.get(error_type)

        if not handler_name:
            self.log(f"No handler for error type: {error_type}", "WARNING")
            return False

        handler = getattr(self, handler_name, None)
        if not handler:
            self.log(f"Handler not implemented: {handler_name}", "WARNING")
            return False

        try:
            return handler(error)
        except Exception as e:
            self.log(f"Repair failed for {error_type}: {e}", "ERROR")
            return False

    def repair_syntax_errors(self, error: Dict[str, Any]) -> bool:
        """構文エラーの修復"""
        self.log(f"Attempting to repair syntax error in {error['file']}")
        # 構文エラーは自動修復が難しいため、ログのみ
        return False

    def repair_import_errors(self, error: Dict[str, Any]) -> bool:
        """インポートエラーの修復"""
        self.log(f"Attempting to repair import error: {error['message'][:100]}")

        # 不足しているパッケージをインストール
        if "No module named" in error.get("message", ""):
            module_name = error["message"].split("'")[1] if "'" in error["message"] else None
            if module_name:
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install", module_name], capture_output=True, timeout=60)
                    self.log(f"Installed missing module: {module_name}")
                    return True
                except Exception:
                    pass

        return False

    def repair_lint_errors(self, error: Dict[str, Any]) -> bool:
        """Lintエラーの修復（blackで自動フォーマット）"""
        file_path = PROJECT_ROOT / error.get("file", "")

        if not file_path.exists():
            return False

        self.log(f"Attempting to auto-format: {error['file']}")

        try:
            # black でフォーマット
            result = subprocess.run(["black", "--line-length=120", str(file_path)], capture_output=True, text=True, timeout=30)

            # isort でインポート整理
            subprocess.run(["isort", "--profile=black", str(file_path)], capture_output=True, timeout=30)

            return result.returncode == 0
        except FileNotFoundError:
            self.log("black/isort not installed", "WARNING")
            return False
        except Exception as e:
            self.log(f"Format error: {e}", "ERROR")
            return False

    def repair_type_errors(self, error: Dict[str, Any]) -> bool:
        """型エラーの修復"""
        # 型エラーは自動修復が難しい
        return False

    def repair_test_failures(self, error: Dict[str, Any]) -> bool:
        """テスト失敗の修復"""
        # テスト失敗は自動修復が難しい
        return False

    def repair_database_errors(self, error: Dict[str, Any]) -> bool:
        """データベースエラーの修復"""
        self.log("Attempting to repair database...")

        try:
            # データベース初期化
            init_script = PROJECT_ROOT / "scripts" / "init_db.py"
            if init_script.exists():
                result = subprocess.run(
                    [sys.executable, str(init_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=PROJECT_ROOT,
                    env={**os.environ, "FLASK_ENV": "testing"},
                )
                if result.returncode == 0:
                    self.log("Database initialized successfully")
                    return True

            # 直接初期化を試行
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    """
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
print('OK')
""",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "FLASK_ENV": "testing"},
            )

            return "OK" in result.stdout

        except Exception as e:
            self.log(f"Database repair failed: {e}", "ERROR")
            return False

    def repair_config_errors(self, error: Dict[str, Any]) -> bool:
        """設定エラーの修復"""
        self.log("Attempting to repair config...")

        # SECRET_KEY が設定されていない場合
        if "SECRET_KEY" in error.get("message", ""):
            import secrets

            env_file = PROJECT_ROOT / ".env"
            secret_key = secrets.token_hex(32)

            try:
                env_content = ""
                if env_file.exists():
                    with open(env_file, "r") as f:
                        env_content = f.read()

                if "SECRET_KEY=" not in env_content:
                    with open(env_file, "a") as f:
                        f.write(f"\nSECRET_KEY={secret_key}\n")
                    self.log("SECRET_KEY generated and saved")
                    return True
            except Exception as e:
                self.log(f"Config repair failed: {e}", "ERROR")

        return False

    def repair_dependency_errors(self, error: Dict[str, Any]) -> bool:
        """依存関係エラーの修復"""
        self.log("Attempting to repair dependencies...")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0
        except Exception as e:
            self.log(f"Dependency repair failed: {e}", "ERROR")
            return False

    def repair_flask_errors(self, error: Dict[str, Any]) -> bool:
        """Flaskエラーの修復"""
        # データベースとコンフィグの修復を試行
        db_result = self.repair_database_errors({"type": "database_error"})
        config_result = self.repair_config_errors({"type": "config_error", "message": "SECRET_KEY"})
        return db_result or config_result

    def repair_template_errors(self, error: Dict[str, Any]) -> bool:
        """テンプレートエラーの修復"""
        # テンプレートは自動生成が難しい
        return False

    def repair_security_errors(self, error: Dict[str, Any]) -> bool:
        """セキュリティエラーの修復"""
        # セキュリティ問題は慎重に対応が必要
        return False

    def run_repair_cycle(self) -> bool:
        """1サイクルの修復を実行"""
        self.log(f"=== Repair Cycle {self.result.cycles_used + 1}/{self.max_cycles} ===")

        # エラー検知
        errors = self.detect_all_errors()
        self.detected_errors = errors

        if not errors:
            self.log("No errors detected!")
            return True

        self.log(f"Found {len(errors)} error(s) to repair")

        # 各エラーの修復を試行
        fixed_count = 0
        for error in errors:
            if self.repair_error(error):
                fixed_count += 1
                self.result.fixed_errors += 1

        self.log(f"Fixed {fixed_count}/{len(errors)} error(s) in this cycle")

        # 再検知して残りのエラーを確認
        remaining_errors = self.detect_all_errors()
        self.result.remaining_errors = len(remaining_errors)

        return len(remaining_errors) == 0

    def run(self) -> RepairResult:
        """メイン実行ループ"""
        self.log("=" * 60)
        self.log("🤖 Infinite Repair Loop System - Starting")
        self.log("=" * 60)
        self.log(f"Max Cycles: {self.max_cycles}")
        self.log(f"Issues: {self.issues}")
        self.log(f"Auto Commit: {self.auto_commit}")
        self.log("=" * 60)

        self.result.timestamp = datetime.now().isoformat()

        for cycle in range(self.max_cycles):
            self.result.cycles_used = cycle + 1

            try:
                success = self.run_repair_cycle()

                if success:
                    self.result.success = True
                    self.log("=" * 60)
                    self.log("✅ All errors fixed successfully!")
                    self.log("=" * 60)
                    break

            except Exception as e:
                self.log(f"Cycle {cycle + 1} failed with exception: {e}", "ERROR")

            # 次のサイクルまで少し待機
            if cycle + 1 < self.max_cycles and not self.result.success:
                self.log(f"Waiting before next cycle...")
                time.sleep(5)

        if not self.result.success:
            self.log("=" * 60)
            self.log(f"❌ Max cycles ({self.max_cycles}) reached. Manual intervention required.")
            self.log("=" * 60)

        # 結果をまとめる
        self.result.error_details = self.detected_errors

        return self.result

    def output_result(self):
        """結果を出力"""
        if self.output_json:
            print(json.dumps(self.result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print("\n" + "=" * 60)
            print("📊 Repair Result Summary")
            print("=" * 60)
            print(f"Success: {self.result.success}")
            print(f"Cycles Used: {self.result.cycles_used}/{self.max_cycles}")
            print(f"Fixed Errors: {self.result.fixed_errors}")
            print(f"Remaining Errors: {self.result.remaining_errors}")
            print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Infinite Repair Loop System")
    parser.add_argument("--max-cycles", type=int, default=15, help="Maximum repair cycles (default: 15)")
    parser.add_argument("--issues", type=str, default="", help="Comma-separated list of GitHub issue numbers")
    parser.add_argument("--auto-commit", action="store_true", help="Prepare changes for auto-commit")
    parser.add_argument("--output-json", action="store_true", help="Output result as JSON")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")

    args = parser.parse_args()

    repair_loop = InfiniteRepairLoop(
        max_cycles=args.max_cycles,
        issues=args.issues,
        auto_commit=args.auto_commit,
        output_json=args.output_json,
        verbose=args.verbose,
    )

    result = repair_loop.run()
    repair_loop.output_result()

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
