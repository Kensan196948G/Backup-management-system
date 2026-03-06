"""
Unit tests for Alembic migration file structure and integrity.

These tests verify that:
- The migrations directory and key files exist
- Each migration version file has correct structure (revision, down_revision, upgrade, downgrade)
- Migration chain is consistent (no broken references)
- Migration files have required attributes set to valid values
- Upgrade/downgrade functions are callable (syntactically valid)
"""

import importlib.util
import os
import re
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"
VERSIONS_DIR = MIGRATIONS_DIR / "versions"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _load_migration_module(filepath: Path):
    """
    Dynamically load a migration file as a Python module without executing
    Alembic context-level code (i.e., without running upgrade/downgrade).
    Returns the module object.
    """
    spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
    module = importlib.util.module_from_spec(spec)
    # We do NOT exec the module top-level because env.py calls context.run_migrations.
    # For version files this is safe; for env.py we skip execution.
    spec.loader.exec_module(module)
    return module


def _get_version_files():
    """Return sorted list of .py migration version files (excluding __init__.py)."""
    if not VERSIONS_DIR.exists():
        return []
    return sorted(
        p for p in VERSIONS_DIR.glob("*.py")
        if p.name not in ("__init__.py",) and not p.name.startswith("__")
    )


# ---------------------------------------------------------------------------
# Directory / file existence tests
# ---------------------------------------------------------------------------

class TestMigrationDirectoryStructure:
    """Verify the expected file layout exists."""

    def test_migrations_directory_exists(self):
        assert MIGRATIONS_DIR.exists(), f"Expected migrations dir at {MIGRATIONS_DIR}"
        assert MIGRATIONS_DIR.is_dir()

    def test_versions_directory_exists(self):
        assert VERSIONS_DIR.exists(), f"Expected versions dir at {VERSIONS_DIR}"
        assert VERSIONS_DIR.is_dir()

    def test_env_py_exists(self):
        env_file = MIGRATIONS_DIR / "env.py"
        assert env_file.exists(), f"Missing env.py in {MIGRATIONS_DIR}"

    def test_script_mako_exists(self):
        mako_file = MIGRATIONS_DIR / "script.py.mako"
        assert mako_file.exists(), f"Missing script.py.mako in {MIGRATIONS_DIR}"

    def test_at_least_one_version_file(self):
        version_files = _get_version_files()
        assert len(version_files) > 0, "No migration version files found"

    def test_known_version_files_present(self):
        """Check that the two known migration files exist."""
        expected = ["add_api_key_tables.py", "add_timezone_to_datetime.py"]
        existing = {p.name for p in _get_version_files()}
        for name in expected:
            assert name in existing, f"Expected migration file not found: {name}"


# ---------------------------------------------------------------------------
# Per-file structural tests
# ---------------------------------------------------------------------------

class TestMigrationFileContents:
    """Verify each migration version file has the required structure."""

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_file_is_non_empty(self, migration_file):
        content = migration_file.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, f"{migration_file.name} is empty"

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_has_revision_identifier(self, migration_file):
        content = migration_file.read_text(encoding="utf-8")
        assert re.search(r'revision\s*=\s*["\']', content), (
            f"{migration_file.name} missing 'revision' identifier"
        )

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_has_down_revision(self, migration_file):
        content = migration_file.read_text(encoding="utf-8")
        assert re.search(r'down_revision\s*=', content), (
            f"{migration_file.name} missing 'down_revision'"
        )

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_has_upgrade_function(self, migration_file):
        content = migration_file.read_text(encoding="utf-8")
        assert re.search(r'def\s+upgrade\s*\(', content), (
            f"{migration_file.name} missing 'upgrade()' function"
        )

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_has_downgrade_function(self, migration_file):
        content = migration_file.read_text(encoding="utf-8")
        assert re.search(r'def\s+downgrade\s*\(', content), (
            f"{migration_file.name} missing 'downgrade()' function"
        )

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_imports_alembic_op(self, migration_file):
        content = migration_file.read_text(encoding="utf-8")
        assert "from alembic import op" in content or "import alembic" in content, (
            f"{migration_file.name} does not import alembic op"
        )

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_imports_sqlalchemy(self, migration_file):
        content = migration_file.read_text(encoding="utf-8")
        assert "sqlalchemy" in content.lower(), (
            f"{migration_file.name} does not import sqlalchemy"
        )

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_revision_is_non_empty_string(self, migration_file):
        content = migration_file.read_text(encoding="utf-8")
        match = re.search(r'revision\s*=\s*["\']([^"\']+)["\']', content)
        assert match is not None, f"{migration_file.name}: could not parse revision value"
        revision_value = match.group(1).strip()
        assert len(revision_value) > 0, f"{migration_file.name}: revision is empty string"

    @pytest.mark.parametrize("migration_file", _get_version_files(), ids=lambda p: p.name)
    def test_no_syntax_errors(self, migration_file):
        """Ensure the file can be compiled without syntax errors."""
        source = migration_file.read_text(encoding="utf-8")
        try:
            compile(source, str(migration_file), "exec")
        except SyntaxError as exc:
            pytest.fail(f"Syntax error in {migration_file.name}: {exc}")


# ---------------------------------------------------------------------------
# Migration chain consistency
# ---------------------------------------------------------------------------

class TestMigrationChain:
    """Verify the migration chain references are consistent."""

    def _parse_revisions(self):
        """
        Parse revision and down_revision from all version files.
        Returns dict: {revision_id: down_revision_id_or_None}
        """
        chain = {}
        for filepath in _get_version_files():
            content = filepath.read_text(encoding="utf-8")
            rev_match = re.search(r'^revision\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            down_match = re.search(r'^down_revision\s*=\s*(?:["\']([^"\']*)["\']|None)', content, re.MULTILINE)
            if rev_match:
                rev = rev_match.group(1)
                down_rev = down_match.group(1) if (down_match and down_match.group(1)) else None
                chain[rev] = down_rev
        return chain

    def test_chain_has_entries(self):
        chain = self._parse_revisions()
        assert len(chain) > 0, "No revisions found in migration files"

    def test_exactly_one_root_migration(self):
        """Exactly one migration should have down_revision=None (the root)."""
        chain = self._parse_revisions()
        roots = [rev for rev, down in chain.items() if down is None]
        assert len(roots) == 1, (
            f"Expected exactly 1 root migration (down_revision=None), found {len(roots)}: {roots}"
        )

    def test_all_down_revisions_point_to_existing_revisions(self):
        """Every non-null down_revision must reference a revision that exists."""
        chain = self._parse_revisions()
        all_revisions = set(chain.keys())
        for rev, down_rev in chain.items():
            if down_rev is not None:
                assert down_rev in all_revisions, (
                    f"Migration '{rev}' has down_revision='{down_rev}' "
                    f"which does not exist in version files"
                )

    def test_no_duplicate_revision_ids(self):
        """Each revision ID must be unique."""
        rev_ids = []
        for filepath in _get_version_files():
            content = filepath.read_text(encoding="utf-8")
            match = re.search(r'^revision\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                rev_ids.append(match.group(1))
        assert len(rev_ids) == len(set(rev_ids)), (
            f"Duplicate revision IDs found: {[r for r in rev_ids if rev_ids.count(r) > 1]}"
        )

    def test_chain_forms_linear_sequence(self):
        """
        The migration chain should form a linear sequence (each revision
        is referenced as down_revision by at most one other revision).
        """
        chain = self._parse_revisions()
        # Count how many times each revision is referenced as down_revision
        reference_counts: dict = {}
        for down_rev in chain.values():
            if down_rev is not None:
                reference_counts[down_rev] = reference_counts.get(down_rev, 0) + 1
        duplicates = {rev: cnt for rev, cnt in reference_counts.items() if cnt > 1}
        assert not duplicates, (
            f"Branching migration chain detected. These revisions are referenced "
            f"as down_revision more than once: {duplicates}"
        )

    def test_known_revision_ids(self):
        """Check the known revision IDs from the codebase."""
        chain = self._parse_revisions()
        assert "add_api_key_tables" in chain, (
            "Expected revision 'add_api_key_tables' not found"
        )
        assert "add_timezone_to_datetime" in chain, (
            "Expected revision 'add_timezone_to_datetime' not found"
        )

    def test_timezone_migration_follows_api_key_migration(self):
        """add_timezone_to_datetime should come after add_api_key_tables."""
        chain = self._parse_revisions()
        if "add_timezone_to_datetime" in chain:
            assert chain["add_timezone_to_datetime"] == "add_api_key_tables", (
                "Expected 'add_timezone_to_datetime' to have "
                "down_revision='add_api_key_tables'"
            )


# ---------------------------------------------------------------------------
# Specific migration content validation
# ---------------------------------------------------------------------------

class TestApiKeyMigrationContent:
    """Content-level checks for add_api_key_tables.py."""

    @pytest.fixture
    def migration_content(self):
        filepath = VERSIONS_DIR / "add_api_key_tables.py"
        return filepath.read_text(encoding="utf-8")

    def test_creates_api_keys_table(self, migration_content):
        assert "api_keys" in migration_content

    def test_creates_refresh_tokens_table(self, migration_content):
        assert "refresh_tokens" in migration_content

    def test_upgrade_creates_tables(self, migration_content):
        assert "create_table" in migration_content

    def test_downgrade_drops_tables(self, migration_content):
        assert "drop_table" in migration_content

    def test_api_keys_has_required_columns(self, migration_content):
        required_columns = ["key_hash", "key_prefix", "name", "user_id", "is_active"]
        for col in required_columns:
            assert col in migration_content, f"Column '{col}' not found in api_key_tables migration"

    def test_foreign_key_to_users(self, migration_content):
        assert "users.id" in migration_content or '"users"' in migration_content

    def test_primary_key_constraint(self, migration_content):
        assert "PrimaryKeyConstraint" in migration_content

    def test_unique_constraint_on_key_hash(self, migration_content):
        assert "UniqueConstraint" in migration_content


class TestTimezoneMigrationContent:
    """Content-level checks for add_timezone_to_datetime.py."""

    @pytest.fixture
    def migration_content(self):
        filepath = VERSIONS_DIR / "add_timezone_to_datetime.py"
        return filepath.read_text(encoding="utf-8")

    def test_references_postgresql_dialect(self, migration_content):
        assert "postgresql" in migration_content

    def test_uses_timestamptz(self, migration_content):
        assert "TIMESTAMPTZ" in migration_content or "timezone" in migration_content.lower()

    def test_handles_sqlite_as_noop(self, migration_content):
        """SQLite should be handled as no-op (no ALTER TABLE for SQLite)."""
        # The migration should check dialect before applying changes
        assert "dialect" in migration_content

    def test_covers_users_table(self, migration_content):
        assert '"users"' in migration_content or "'users'" in migration_content

    def test_covers_backup_jobs_table(self, migration_content):
        assert "backup_jobs" in migration_content

    def test_covers_multiple_tables(self, migration_content):
        tables = ["users", "backup_jobs", "backup_copies", "alerts", "audit_logs"]
        found = sum(1 for t in tables if t in migration_content)
        assert found >= 3, f"Expected at least 3 tables in timezone migration, found {found}"

    def test_downgrade_reverts_changes(self, migration_content):
        # downgrade function exists and is non-trivial
        assert "def downgrade" in migration_content
        # downgrade should also reference postgresql
        downgrade_section = migration_content[migration_content.find("def downgrade"):]
        assert "postgresql" in downgrade_section or "TIMESTAMP" in downgrade_section

    def test_exception_handling_in_upgrade(self, migration_content):
        """Migration should gracefully handle columns that don't exist."""
        assert "except" in migration_content or "try" in migration_content


# ---------------------------------------------------------------------------
# env.py structure tests
# ---------------------------------------------------------------------------

class TestEnvPyStructure:
    """Verify env.py has expected structure without executing it."""

    @pytest.fixture
    def env_content(self):
        return (MIGRATIONS_DIR / "env.py").read_text(encoding="utf-8")

    def test_imports_alembic_context(self, env_content):
        assert "from alembic import context" in env_content

    def test_has_run_migrations_offline(self, env_content):
        assert "def run_migrations_offline" in env_content

    def test_has_run_migrations_online(self, env_content):
        assert "def run_migrations_online" in env_content

    def test_has_get_metadata(self, env_content):
        assert "def get_metadata" in env_content or "target_metadata" in env_content

    def test_handles_flask_sqlalchemy_versions(self, env_content):
        """Should handle both old and new Flask-SQLAlchemy API."""
        assert "migrate" in env_content

    def test_no_hardcoded_database_url(self, env_content):
        """env.py should not have a hardcoded DB URL."""
        # Should use dynamic URL retrieval
        assert "get_engine_url" in env_content or "current_app" in env_content
        # Must not contain a hardcoded connection string
        assert "postgresql://user:password@" not in env_content
        assert "mysql://user:password@" not in env_content
