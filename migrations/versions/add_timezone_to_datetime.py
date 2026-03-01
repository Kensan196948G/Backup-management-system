"""Add timezone=True to all DateTime columns for PostgreSQL compatibility

Revision ID: add_timezone_to_datetime
Revises: add_api_key_tables
Create Date: 2026-03-01 21:00:00.000000

This migration converts all DATETIME columns to TIMESTAMP WITH TIME ZONE
for PostgreSQL compatibility. SQLite ignores this change (no-op for SQLite).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_timezone_to_datetime"
down_revision = "add_api_key_tables"
branch_labels = None
depends_on = None


def upgrade():
    """
    Convert DateTime columns to DateTime(timezone=True) for PostgreSQL.
    This is a no-op for SQLite, but changes DATETIME -> TIMESTAMPTZ in PostgreSQL.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        # PostgreSQL: ALTER COLUMN to TIMESTAMPTZ
        timezone_columns = {
            "users": ["last_login", "last_failed_login", "account_locked_until", "created_at", "updated_at"],
            "backup_jobs": ["created_at", "updated_at"],
            "backup_copies": ["last_backup_date", "created_at", "updated_at"],
            "offline_media": ["created_at", "updated_at"],
            "media_rotation_schedule": ["created_at", "updated_at"],
            "media_lending": ["borrow_date", "actual_return", "created_at", "updated_at"],
            "verification_tests": ["test_date", "created_at", "updated_at"],
            "verification_schedule": ["created_at", "updated_at"],
            "backup_executions": ["execution_date", "created_at"],
            "compliance_status": ["check_date", "created_at"],
            "alerts": ["acknowledged_at", "created_at"],
            "audit_logs": ["created_at"],
            "reports": ["created_at"],
            "system_settings": ["updated_at"],
            "notification_logs": ["sent_at"],
            "api_keys": ["verified_at", "created_at"],
            "scheduled_reports": ["created_at", "updated_at"],
        }

        for table, columns in timezone_columns.items():
            for column in columns:
                try:
                    op.execute(
                        sa.text(
                            f"ALTER TABLE {table} ALTER COLUMN {column} "
                            f"TYPE TIMESTAMPTZ USING {column} AT TIME ZONE 'UTC'"
                        )
                    )
                except Exception:
                    # Skip if column doesn't exist or already is TIMESTAMPTZ
                    pass
    # SQLite: no-op (SQLite has no native timezone support)


def downgrade():
    """
    Revert TIMESTAMPTZ columns back to TIMESTAMP WITHOUT TIME ZONE in PostgreSQL.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        timezone_columns = {
            "users": ["last_login", "last_failed_login", "account_locked_until", "created_at", "updated_at"],
            "backup_jobs": ["created_at", "updated_at"],
            "backup_copies": ["last_backup_date", "created_at", "updated_at"],
            "offline_media": ["created_at", "updated_at"],
            "media_rotation_schedule": ["created_at", "updated_at"],
            "media_lending": ["borrow_date", "actual_return", "created_at", "updated_at"],
            "verification_tests": ["test_date", "created_at", "updated_at"],
            "verification_schedule": ["created_at", "updated_at"],
            "backup_executions": ["execution_date", "created_at"],
            "compliance_status": ["check_date", "created_at"],
            "alerts": ["acknowledged_at", "created_at"],
            "audit_logs": ["created_at"],
            "reports": ["created_at"],
            "system_settings": ["updated_at"],
            "notification_logs": ["sent_at"],
            "api_keys": ["verified_at", "created_at"],
            "scheduled_reports": ["created_at", "updated_at"],
        }

        for table, columns in timezone_columns.items():
            for column in columns:
                try:
                    op.execute(
                        sa.text(
                            f"ALTER TABLE {table} ALTER COLUMN {column} "
                            f"TYPE TIMESTAMP WITHOUT TIME ZONE"
                        )
                    )
                except Exception:
                    pass
