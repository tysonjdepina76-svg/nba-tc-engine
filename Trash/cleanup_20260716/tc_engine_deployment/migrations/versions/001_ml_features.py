"""Add ML features column and actual_value to picks table

Revision ID: 001_ml_features
Revises: None
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "001_ml_features"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "graded_picks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("sport", sa.String(20), nullable=False),
        sa.Column("player", sa.String(100)),
        sa.Column("stat", sa.String(30)),
        sa.Column("direction", sa.String(10)),
        sa.Column("line", sa.Float()),
        sa.Column("projection", sa.Float()),
        sa.Column("edge", sa.Float()),
        sa.Column("actual_value", sa.Float()),
        sa.Column("hit", sa.Boolean()),
        sa.Column("signal", sa.String(20)),
        sa.Column("features", JSON),
        sa.Column("model_version", sa.String(30)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_index("idx_graded_picks_date_sport", "graded_picks", ["date", "sport"])
    op.create_index("idx_graded_picks_hit", "graded_picks", ["hit"])


def downgrade():
    op.drop_index("idx_graded_picks_hit")
    op.drop_index("idx_graded_picks_date_sport")
    op.drop_table("graded_picks")
