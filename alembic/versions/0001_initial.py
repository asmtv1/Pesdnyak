"""Initial schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_states",
        sa.Column("user_hash", sa.String(64), nullable=False),
        sa.Column("situation_id", sa.String(32), nullable=True),
        sa.Column("level_id", sa.String(16), nullable=True),
        sa.Column("last_indices", sa.String(64), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("user_hash", name="pk_user_states"),
    )
    op.create_table(
        "bag_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_hash", sa.String(64), nullable=False),
        sa.Column("bag_key", sa.String(96), nullable=False),
        sa.Column("remaining", sa.Text(), nullable=False),
        sa.Column("last_index", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_bag_states"),
        sa.UniqueConstraint("user_hash", "bag_key", name="uq_bag_states_user_hash"),
    )
    op.create_index("ix_bag_states_user_hash", "bag_states", ["user_hash"])
    op.create_table(
        "daily_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        sa.Column("situation_id", sa.String(32), nullable=False),
        sa.Column("level_id", sa.String(16), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_daily_metrics"),
        sa.UniqueConstraint(
            "day", "event", "situation_id", "level_id", name="uq_daily_metrics_day"
        ),
    )


def downgrade() -> None:
    op.drop_table("daily_metrics")
    op.drop_index("ix_bag_states_user_hash", table_name="bag_states")
    op.drop_table("bag_states")
    op.drop_table("user_states")
