#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Phase 12: Database & Infrastructure Enhancement

This script migrates data from SQLite to PostgreSQL while preserving
all relationships and data integrity.

Usage:
    python migrate_sqlite_to_postgres.py --sqlite-path data/backup_management.db \
        --postgres-url postgresql://user:pass@localhost/backup_management

Requirements:
    pip install psycopg2-binary sqlalchemy
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration from SQLite to PostgreSQL."""

    def __init__(self, sqlite_path: str, postgres_url: str):
        """
        Initialize migrator.

        Args:
            sqlite_path: Path to SQLite database file
            postgres_url: PostgreSQL connection URL
        """
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url

        # Create engines
        self.sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
        self.postgres_engine = create_engine(postgres_url)

        # Create sessions
        self.SQLiteSession = sessionmaker(bind=self.sqlite_engine)
        self.PostgresSession = sessionmaker(bind=self.postgres_engine)

        # Migration statistics
        self.stats = {
            "tables_migrated": 0,
            "rows_migrated": 0,
            "errors": [],
            "start_time": None,
            "end_time": None,
        }

    def validate_connections(self) -> bool:
        """Validate database connections."""
        logger.info("Validating database connections...")

        # Check SQLite
        if not Path(self.sqlite_path).exists():
            logger.error(f"SQLite database not found: {self.sqlite_path}")
            return False

        try:
            with self.sqlite_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ SQLite connection OK")
        except Exception as e:
            logger.error(f"SQLite connection failed: {e}")
            return False

        # Check PostgreSQL
        try:
            with self.postgres_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ PostgreSQL connection OK")
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return False

        return True

    def get_table_order(self) -> List[str]:
        """
        Get tables in dependency order for migration.

        Returns ordered list of table names, with parent tables first.
        """
        inspector = inspect(self.sqlite_engine)
        tables = inspector.get_table_names()

        # Build dependency graph
        dependencies: Dict[str, List[str]] = {table: [] for table in tables}

        for table in tables:
            fks = inspector.get_foreign_keys(table)
            for fk in fks:
                if fk["referred_table"] in tables:
                    dependencies[table].append(fk["referred_table"])

        # Topological sort
        ordered = []
        visited = set()

        def visit(table):
            if table in visited:
                return
            visited.add(table)
            for dep in dependencies[table]:
                visit(dep)
            ordered.append(table)

        for table in tables:
            visit(table)

        return ordered

    def create_postgres_schema(self):
        """Create PostgreSQL schema from SQLite structure."""
        logger.info("Creating PostgreSQL schema...")

        # Import models to get SQLAlchemy metadata
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        try:
            from app.models import db

            # Create all tables
            db.metadata.create_all(self.postgres_engine)
            logger.info("✅ PostgreSQL schema created")
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            raise

    def migrate_table(self, table_name: str, batch_size: int = 1000) -> int:
        """
        Migrate a single table from SQLite to PostgreSQL.

        Args:
            table_name: Name of table to migrate
            batch_size: Number of rows per batch

        Returns:
            Number of rows migrated
        """
        logger.info(f"Migrating table: {table_name}")

        inspector = inspect(self.sqlite_engine)
        columns = [col["name"] for col in inspector.get_columns(table_name)]

        # Count rows
        with self.sqlite_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            total_rows = result.scalar()

        if total_rows == 0:
            logger.info(f"  Table {table_name} is empty, skipping")
            return 0

        logger.info(f"  Found {total_rows} rows to migrate")

        # Migrate in batches
        migrated = 0
        offset = 0

        while offset < total_rows:
            # Read batch from SQLite
            with self.sqlite_engine.connect() as conn:
                query = text(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
                result = conn.execute(query)
                rows = result.fetchall()

            if not rows:
                break

            # Insert batch into PostgreSQL
            with self.postgres_engine.connect() as conn:
                transaction = conn.begin()
                for row in rows:
                    try:
                        # Build insert dict
                        data = dict(zip(columns, row))

                        # Handle NULL values and type conversions
                        data = self._convert_row_types(data, table_name)

                        # Build parameterized insert
                        cols = ", ".join(data.keys())
                        placeholders = ", ".join([f":{k}" for k in data.keys()])
                        insert_sql = text(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})")

                        conn.execute(insert_sql, data)
                    except Exception as e:
                        logger.warning(f"  Row insert failed: {e}")
                        self.stats["errors"].append({"table": table_name, "error": str(e), "data": str(data)[:200]})
                        # Rollback this transaction and start a new one
                        transaction.rollback()
                        transaction = conn.begin()

                transaction.commit()

            migrated += len(rows)
            offset += batch_size

            if migrated % 5000 == 0:
                logger.info(f"  Progress: {migrated}/{total_rows} rows")

        logger.info(f"  ✅ Migrated {migrated} rows from {table_name}")
        return migrated

    def _convert_row_types(self, data: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """
        Convert SQLite types to PostgreSQL compatible types.

        Args:
            data: Row data dict
            table_name: Name of table for context

        Returns:
            Converted data dict
        """
        converted = {}

        # Boolean field names that need conversion
        boolean_fields = {
            "is_active",
            "is_acknowledged",
            "is_read",
            "is_locked",
            "is_verified",
            "is_encrypted",
            "is_compressed",
            "is_offline",
            "is_readonly",
            "auto_rotation_enabled",
            "notify_on_completion",
            "notify_on_failure",
            "enforce_verification",
            "require_secondary_storage",
            "is_default",
            "is_secure",
        }

        for key, value in data.items():
            if value is None:
                converted[key] = None
            elif key in boolean_fields:
                # Convert integer/string to boolean
                if isinstance(value, int):
                    converted[key] = bool(value)
                elif isinstance(value, str):
                    converted[key] = value.lower() in ("true", "1", "yes")
                else:
                    converted[key] = bool(value)
            elif isinstance(value, bytes):
                # Convert bytes to string or handle as binary
                try:
                    converted[key] = value.decode("utf-8")
                except UnicodeDecodeError:
                    converted[key] = value.hex()
            elif isinstance(value, str):
                # Handle boolean strings from SQLite
                if value.lower() in ("true", "false"):
                    converted[key] = value.lower() == "true"
                else:
                    converted[key] = value
            else:
                converted[key] = value

        return converted

    def reset_sequences(self):
        """Reset PostgreSQL sequences to continue from max ID."""
        logger.info("Resetting PostgreSQL sequences...")

        inspector = inspect(self.postgres_engine)
        tables = inspector.get_table_names()

        with self.postgres_engine.connect() as conn:
            for table in tables:
                # Check if table has id column
                columns = [col["name"] for col in inspector.get_columns(table)]
                if "id" not in columns:
                    continue

                # Get max ID
                result = conn.execute(text(f"SELECT MAX(id) FROM {table}"))
                max_id = result.scalar() or 0

                # Reset sequence
                seq_name = f"{table}_id_seq"
                try:
                    conn.execute(text(f"SELECT setval('{seq_name}', {max_id + 1}, false)"))
                    logger.info(f"  Reset {seq_name} to {max_id + 1}")
                except Exception as e:
                    logger.warning(f"  Could not reset sequence {seq_name}: {e}")

            conn.commit()

    def verify_migration(self) -> bool:
        """
        Verify migration by comparing row counts.

        Returns:
            True if verification passes
        """
        logger.info("Verifying migration...")

        inspector_sqlite = inspect(self.sqlite_engine)
        sqlite_tables = set(inspector_sqlite.get_table_names())

        inspector_postgres = inspect(self.postgres_engine)
        postgres_tables = set(inspector_postgres.get_table_names())

        # Only verify tables that exist in both databases
        common_tables = sqlite_tables & postgres_tables

        all_ok = True

        for table in common_tables:
            with self.sqlite_engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                sqlite_count = result.scalar()

            with self.postgres_engine.connect() as conn:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    postgres_count = result.scalar()
                except Exception as e:
                    logger.warning(f"  ⚠️ {table}: Could not verify - {e}")
                    continue

            if sqlite_count == postgres_count:
                logger.info(f"  ✅ {table}: {sqlite_count} rows")
            else:
                logger.error(f"  ❌ {table}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")
                all_ok = False

        # Report tables only in SQLite
        only_sqlite = sqlite_tables - postgres_tables
        if only_sqlite:
            logger.warning(f"  ⚠️ Tables only in SQLite (skipped): {only_sqlite}")

        return all_ok

    def run_migration(self, skip_schema: bool = False) -> bool:
        """
        Run full migration process.

        Args:
            skip_schema: Skip schema creation if already exists

        Returns:
            True if migration successful
        """
        self.stats["start_time"] = datetime.now()

        logger.info("=" * 60)
        logger.info("SQLite to PostgreSQL Migration")
        logger.info("=" * 60)
        logger.info(f"Source: {self.sqlite_path}")
        logger.info(f"Target: {self.postgres_url.split('@')[1] if '@' in self.postgres_url else self.postgres_url}")
        logger.info("=" * 60)

        # Validate connections
        if not self.validate_connections():
            return False

        # Create schema
        if not skip_schema:
            try:
                self.create_postgres_schema()
            except Exception as e:
                logger.error(f"Schema creation failed: {e}")
                return False

        # Get migration order
        tables = self.get_table_order()
        logger.info(f"Tables to migrate: {tables}")

        # Migrate tables
        for table in tables:
            try:
                rows = self.migrate_table(table)
                self.stats["rows_migrated"] += rows
                self.stats["tables_migrated"] += 1
            except Exception as e:
                logger.error(f"Failed to migrate {table}: {e}")
                self.stats["errors"].append({"table": table, "error": str(e)})

        # Reset sequences
        self.reset_sequences()

        # Verify
        verification_ok = self.verify_migration()

        self.stats["end_time"] = datetime.now()

        # Print summary
        duration = self.stats["end_time"] - self.stats["start_time"]

        logger.info("=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info(f"Tables migrated: {self.stats['tables_migrated']}")
        logger.info(f"Rows migrated: {self.stats['rows_migrated']}")
        logger.info(f"Errors: {len(self.stats['errors'])}")
        logger.info(f"Duration: {duration}")
        logger.info(f"Verification: {'✅ PASSED' if verification_ok else '❌ FAILED'}")
        logger.info("=" * 60)

        if self.stats["errors"]:
            logger.warning("Errors encountered:")
            for err in self.stats["errors"][:10]:
                logger.warning(f"  - {err['table']}: {err['error']}")

        return verification_ok and len(self.stats["errors"]) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate SQLite database to PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic migration
    python migrate_sqlite_to_postgres.py \\
        --sqlite-path data/backup_management.db \\
        --postgres-url postgresql://user:pass@localhost/backup_management

    # Skip schema creation (tables already exist)
    python migrate_sqlite_to_postgres.py \\
        --sqlite-path data/backup_management.db \\
        --postgres-url postgresql://user:pass@localhost/backup_management \\
        --skip-schema
        """,
    )

    parser.add_argument(
        "--sqlite-path",
        required=True,
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--postgres-url",
        required=True,
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip schema creation (use if tables already exist)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Rows per batch (default: 1000)",
    )

    args = parser.parse_args()

    migrator = DatabaseMigrator(args.sqlite_path, args.postgres_url)
    success = migrator.run_migration(skip_schema=args.skip_schema)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
