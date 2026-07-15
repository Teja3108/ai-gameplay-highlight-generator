"""Create the initial persistence schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-15
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the initial Phase 2 tables."""
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_path", sa.String(length=1024), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("resolution", sa.String(length=32), nullable=False),
        sa.Column("fps", sa.Float(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("original_path"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_stage", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("output_directory", sa.String(length=1024), nullable=False),
        sa.Column("temp_directory", sa.String(length=1024), nullable=False),
        sa.Column("preferred_gpu", sa.String(length=128), nullable=True),
        sa.Column("subtitle_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("smart_crop_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "clips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("viral_score", sa.Float(), nullable=False),
        sa.Column("export_path", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the initial Phase 2 tables."""
    op.drop_table("clips")
    op.drop_table("settings")
    op.drop_table("jobs")
    op.drop_table("videos")
