#!/usr/bin/env python3
"""
包括的エラー検知システム - Comprehensive Error Detection System

機能:
- Python構文エラー検知
- インポートエラー検知
- Lintエラー検知 (flake8)
- 型エラー検知 (mypy)
- テスト失敗検知
- データベースエラー検知
- Flask起動エラー検知
- テンプレートエラー検知
- セキュリティ問題検知
- 依存関係エラー検知

使用方法:
    python scripts/detect_all_errors.py --output-json
    python scripts/detect_all_errors.py --verbose
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class DetectionResult:
    """検知結果を格納するデータクラス"""

    error_count: int = 0
    warning_count: int = 0
    error_types: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "error_types": list(set(self.error_types)),
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
        }


class ComprehensiveErrorDetector:
    """包括的エラー検知システム"""

    # 除外パターン
    EXCLUDE_PATTERNS = [
        r"venv/",
        r"\.venv/",
        r"__pycache__/",
        r"\.git/",
        r"node_modules/",
        r"\.pytest_cache/",
        r"\.mypy_cache/",
        r"migrations/",
        r"\.eggs/",
        r"build/",
        r"dist/",
    ]

    def __init__(
        self, output_json: bool = False, verbose: bool = True, check_types: bool = False, check_security: bool = True
    ):
        self.output_json = output_json
        self.verbose = verbose
        self.check_types = check_types
        self.check_security = check_security
        self.result = DetectionResult()
        self.start_time = datetime.now()

    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        if self.verbose and not self.output_json:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")

    def should_exclude(self, path: str) -> bool:
        """除外パターンに一致するかチェック"""
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, path):
                return True
        return False

    def add_error(self, error_type: str, file: str, message: str, line: int = 0, severity: str = "error"):
        """エラーを追加"""
        error = {
            "type": error_type,
            "file": file,
            "line": line,
            "message": message,
            "severity": severity,
            "detected_at": datetime.now().isoformat(),
        }

        if severity in ["critical", "error", "high"]:
            self.result.errors.append(error)
            self.result.error_count += 1
        else:
            self.result.warnings.append(error)
            self.result.warning_count += 1

        if error_type not in self.result.error_types:
            self.result.error_types.append(error_type)

    def detect_syntax_errors(self):
        """Python構文エラーを検知"""
        self.log("Checking Python syntax...")

        python_files = list(PROJECT_ROOT.glob("**/*.py"))
        syntax_errors = 0

        for py_file in python_files:
            rel_path = str(py_file.relative_to(PROJECT_ROOT))

            if self.should_exclude(rel_path):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                compile(code, py_file, "exec")
            except SyntaxError as e:
                self.add_error("syntax_error", rel_path, f"Line {e.lineno}: {e.msg}", e.lineno or 0, "critical")
                syntax_errors += 1
            except Exception as e:
                self.add_error("syntax_error", rel_path, str(e)[:200], 0, "error")
                syntax_errors += 1

        self.log(f"Syntax check complete: {syntax_errors} error(s)")

    def detect_import_errors(self):
        """インポートエラーを検知"""
        self.log("Checking imports...")

        # 主要モジュールのインポートテスト
        test_imports = [
            ("from app import create_app", "app/__init__.py"),
            ("from app import db", "app/__init__.py"),
            ("from app.models import User", "app/models/user.py"),
        ]

        import_errors = 0

        for import_stmt, related_file in test_imports:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", import_stmt],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "FLASK_ENV": "testing"},
                )
                if result.returncode != 0:
                    error_msg = result.stderr[:300] if result.stderr else "Import failed"
                    self.add_error("import_error", related_file, error_msg, 0, "critical")
                    import_errors += 1
            except subprocess.TimeoutExpired:
                self.add_error("import_error", related_file, "Import timeout", 0, "critical")
                import_errors += 1
            except Exception as e:
                self.add_error("import_error", related_file, str(e)[:200], 0, "error")
                import_errors += 1

        self.log(f"Import check complete: {import_errors} error(s)")

    def detect_lint_errors(self):
        """Lintエラーを検知 (flake8)"""
        self.log("Running flake8 lint check...")

        try:
            result = subprocess.run(
                [
                    "flake8",
                    "--max-line-length=120",
                    "--exclude=venv,__pycache__,migrations,.git",
                    "--select=E,F,W",  # エラーと警告のみ
                    "--max-complexity=15",
                    ".",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )

            lint_errors = 0
            if result.stdout:
                for line in result.stdout.strip().split("\n")[:50]:  # 最大50件
                    if not line.strip():
                        continue

                    parts = line.split(":", 3)
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1]) if parts[1].isdigit() else 0
                        code = parts[2].strip()
                        message = parts[3].strip() if len(parts) > 3 else ""

                        # エラーコードで重要度を判定
                        if code.startswith("E9") or code.startswith("F"):
                            severity = "error"
                        else:
                            severity = "warning"

                        self.add_error("lint_error", file_path, f"{code}: {message}", line_num, severity)
                        lint_errors += 1

            self.log(f"Lint check complete: {lint_errors} issue(s)")

        except FileNotFoundError:
            self.log("flake8 not installed, skipping lint check", "WARNING")
        except subprocess.TimeoutExpired:
            self.add_error("lint_error", ".", "Lint check timeout", 0, "warning")
        except Exception as e:
            self.log(f"Lint check error: {e}", "ERROR")

    def detect_type_errors(self):
        """型エラーを検知 (mypy)"""
        if not self.check_types:
            self.log("Type checking disabled, skipping...")
            return

        self.log("Running mypy type check...")

        try:
            result = subprocess.run(
                ["mypy", "--ignore-missing-imports", "--no-error-summary", "--show-column-numbers", "app/"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )

            type_errors = 0
            if result.stdout:
                for line in result.stdout.strip().split("\n")[:30]:  # 最大30件
                    if not line.strip() or "error:" not in line:
                        continue

                    match = re.match(r"(.+):(\d+):(\d+): error: (.+)", line)
                    if match:
                        self.add_error("type_error", match.group(1), match.group(4), int(match.group(2)), "warning")
                        type_errors += 1

            self.log(f"Type check complete: {type_errors} issue(s)")

        except FileNotFoundError:
            self.log("mypy not installed, skipping type check", "WARNING")
        except subprocess.TimeoutExpired:
            self.add_error("type_error", "app/", "Type check timeout", 0, "warning")
        except Exception as e:
            self.log(f"Type check error: {e}", "ERROR")

    def detect_test_failures(self):
        """テスト失敗を検知"""
        self.log("Running pytest...")

        try:
            result = subprocess.run(
                ["pytest", "--tb=line", "-q", "--maxfail=10", "--timeout=60"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ, "FLASK_ENV": "testing"},
            )

            test_failures = 0
            if result.returncode != 0:
                for line in result.stdout.split("\n"):
                    if "FAILED" in line:
                        # FAILED tests/test_file.py::test_name - reason
                        match = re.match(r"FAILED (.+?)(?:\s+-\s+(.+))?$", line.strip())
                        if match:
                            self.add_error(
                                "test_failure", match.group(1).split("::")[0], match.group(2) or "Test failed", 0, "high"
                            )
                            test_failures += 1
                    elif "ERROR" in line and "test" in line.lower():
                        self.add_error("test_failure", "tests/", line.strip()[:200], 0, "error")
                        test_failures += 1

            self.log(f"Test check complete: {test_failures} failure(s)")

        except FileNotFoundError:
            self.log("pytest not installed, skipping test check", "WARNING")
        except subprocess.TimeoutExpired:
            self.add_error("test_failure", "tests/", "Test execution timeout", 0, "high")
        except Exception as e:
            self.log(f"Test check error: {e}", "ERROR")

    def detect_database_errors(self):
        """データベースエラーを検知"""
        self.log("Checking database...")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    """
import os
os.environ.setdefault('FLASK_ENV', 'testing')
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
                error_msg = result.stderr[:300] if result.stderr else "Database connection failed"
                self.add_error("database_error", "instance/backup_system.db", error_msg, 0, "critical")
                self.log("Database check: FAILED", "ERROR")
            else:
                self.log("Database check: OK")

        except subprocess.TimeoutExpired:
            self.add_error("database_error", "instance/", "Database check timeout", 0, "critical")
        except Exception as e:
            self.add_error("database_error", "instance/", str(e)[:200], 0, "error")

    def detect_flask_errors(self):
        """Flask起動エラーを検知"""
        self.log("Checking Flask app...")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    """
import os
os.environ.setdefault('FLASK_ENV', 'testing')
from app import create_app
app = create_app()
with app.test_client() as client:
    # ヘルスチェックエンドポイントがなければルートを確認
    try:
        response = client.get('/health')
    except:
        response = client.get('/')
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
                error_msg = result.stderr[:300] if result.stderr else "Flask startup failed"
                self.add_error("flask_error", "app/__init__.py", error_msg, 0, "critical")
                self.log("Flask check: FAILED", "ERROR")
            else:
                self.log("Flask check: OK")

        except subprocess.TimeoutExpired:
            self.add_error("flask_error", "app/", "Flask check timeout", 0, "critical")
        except Exception as e:
            self.add_error("flask_error", "app/", str(e)[:200], 0, "error")

    def detect_template_errors(self):
        """テンプレートエラーを検知"""
        self.log("Checking templates...")

        template_dir = PROJECT_ROOT / "app" / "templates"

        if not template_dir.exists():
            self.add_error("template_error", "app/templates/", "Templates directory not found", 0, "high")
            return

        # 必須テンプレートのチェック
        required_templates = [
            "base.html",
            "auth/login.html",
        ]

        template_errors = 0
        for template in required_templates:
            template_path = template_dir / template
            if not template_path.exists():
                self.add_error("template_error", f"app/templates/{template}", f"Required template missing", 0, "medium")
                template_errors += 1

        # Jinja2構文チェック
        try:
            from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

            env = Environment(loader=FileSystemLoader(str(template_dir)))

            for template_file in template_dir.glob("**/*.html"):
                rel_path = template_file.relative_to(template_dir)
                try:
                    env.get_template(str(rel_path))
                except TemplateSyntaxError as e:
                    self.add_error(
                        "template_error", f"app/templates/{rel_path}", f"Line {e.lineno}: {e.message}", e.lineno or 0, "error"
                    )
                    template_errors += 1
        except ImportError:
            pass
        except Exception as e:
            self.log(f"Template syntax check error: {e}", "WARNING")

        self.log(f"Template check complete: {template_errors} error(s)")

    def detect_security_issues(self):
        """セキュリティ問題を検知"""
        if not self.check_security:
            return

        self.log("Checking security issues...")

        security_issues = 0

        # 機密情報のパターン
        sensitive_patterns = [
            (r"password\s*=\s*['\"](?!(\{|%|\$))([^'\"]+)['\"]", "Hardcoded password"),
            (r"secret\s*=\s*['\"](?!(\{|%|\$))([^'\"]+)['\"]", "Hardcoded secret"),
            (r"api_key\s*=\s*['\"](?!(\{|%|\$))([^'\"]+)['\"]", "Hardcoded API key"),
            (r"token\s*=\s*['\"](?!(\{|%|\$))([a-zA-Z0-9]{20,})['\"]", "Hardcoded token"),
        ]

        python_files = list(PROJECT_ROOT.glob("**/*.py"))

        for py_file in python_files:
            rel_path = str(py_file.relative_to(PROJECT_ROOT))

            if self.should_exclude(rel_path):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                    for pattern, issue_name in sensitive_patterns:
                        for line_num, line in enumerate(lines, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                # テストファイルは除外
                                if "test" not in rel_path.lower():
                                    self.add_error("security_error", rel_path, f"{issue_name} detected", line_num, "high")
                                    security_issues += 1
            except Exception:
                pass

        # .envファイルのチェック
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            try:
                with open(env_file, "r") as f:
                    env_content = f.read()
                    if "SECRET_KEY=" not in env_content:
                        self.add_error("security_error", ".env", "SECRET_KEY not configured", 0, "high")
                        security_issues += 1
            except Exception:
                pass

        self.log(f"Security check complete: {security_issues} issue(s)")

    def detect_dependency_errors(self):
        """依存関係エラーを検知"""
        self.log("Checking dependencies...")

        requirements_file = PROJECT_ROOT / "requirements.txt"

        if not requirements_file.exists():
            self.add_error("dependency_error", "requirements.txt", "requirements.txt not found", 0, "high")
            return

        # 主要パッケージのチェック
        critical_packages = ["flask", "sqlalchemy", "werkzeug", "jinja2"]
        dep_errors = 0

        for package in critical_packages:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import {package}; print({package}.__version__)"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    self.add_error(
                        "dependency_error", "requirements.txt", f"Package not installed or broken: {package}", 0, "critical"
                    )
                    dep_errors += 1
            except Exception:
                pass

        self.log(f"Dependency check complete: {dep_errors} error(s)")

    def run_all_checks(self) -> DetectionResult:
        """全てのチェックを実行"""
        self.log("=" * 60)
        self.log("🔍 Comprehensive Error Detection - Starting")
        self.log("=" * 60)

        self.result.timestamp = datetime.now().isoformat()

        # 各チェックを実行
        checks = [
            self.detect_syntax_errors,
            self.detect_import_errors,
            self.detect_lint_errors,
            self.detect_type_errors,
            self.detect_test_failures,
            self.detect_database_errors,
            self.detect_flask_errors,
            self.detect_template_errors,
            self.detect_security_issues,
            self.detect_dependency_errors,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.log(f"Check failed: {check.__name__} - {e}", "ERROR")

        # 実行時間を計算
        end_time = datetime.now()
        self.result.duration_seconds = (end_time - self.start_time).total_seconds()

        self.log("=" * 60)
        self.log(f"Detection complete in {self.result.duration_seconds:.2f}s")
        self.log(f"Errors: {self.result.error_count}, Warnings: {self.result.warning_count}")
        self.log("=" * 60)

        return self.result

    def output_result(self):
        """結果を出力"""
        if self.output_json:
            print(json.dumps(self.result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print("\n" + "=" * 60)
            print("📊 Detection Result Summary")
            print("=" * 60)
            print(f"Errors: {self.result.error_count}")
            print(f"Warnings: {self.result.warning_count}")
            print(f"Error Types: {', '.join(self.result.error_types) or 'None'}")
            print(f"Duration: {self.result.duration_seconds:.2f}s")

            if self.result.errors:
                print("\n🔴 Errors:")
                for error in self.result.errors[:20]:
                    print(f"  - [{error['type']}] {error['file']}:{error['line']} - {error['message'][:60]}")

            if self.result.warnings:
                print("\n🟡 Warnings:")
                for warning in self.result.warnings[:10]:
                    print(f"  - [{warning['type']}] {warning['file']}:{warning['line']} - {warning['message'][:60]}")

            print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Comprehensive Error Detection System")
    parser.add_argument("--output-json", action="store_true", help="Output result as JSON")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    parser.add_argument("--check-types", action="store_true", help="Enable mypy type checking")
    parser.add_argument("--no-security", action="store_true", help="Disable security checks")

    args = parser.parse_args()

    detector = ComprehensiveErrorDetector(
        output_json=args.output_json, verbose=args.verbose, check_types=args.check_types, check_security=not args.no_security
    )

    result = detector.run_all_checks()
    detector.output_result()

    # エラーがあれば終了コード1
    sys.exit(1 if result.error_count > 0 else 0)


if __name__ == "__main__":
    main()
