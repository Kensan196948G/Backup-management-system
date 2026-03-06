"""Add BackupSchedule and StorageProvider models

Revision ID: add_backup_schedule_storage_provider
Revises: add_timezone_to_datetime
Create Date: 2026-03-06 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_backup_schedule_storage_provider"
down_revision = "add_timezone_to_datetime"
branch_labels = None
depends_on = None


def upgrade():
    # Create backup_schedules table
    op.create_table(
        "backup_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False, server_default="0 2 * * *"),
        sa.Column("schedule_description", sa.String(200), nullable=True),
        sa.Column("priority", sa.String(20), nullable=True, server_default="medium"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("next_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["backup_jobs.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create storage_providers table
    op.create_table(
        "storage_providers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=True),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("connection_status", sa.String(20), nullable=True, server_default="unknown"),
        sa.Column("last_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_capacity", sa.BigInteger(), nullable=True),
        sa.Column("used_capacity", sa.BigInteger(), nullable=True),
        sa.Column("backup_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("file_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=True, server_default="100.0"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("backup_schedules")
    op.drop_table("storage_providers")
