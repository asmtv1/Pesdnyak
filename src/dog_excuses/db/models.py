from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from dog_excuses.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class UserState(Base):
    __tablename__ = "user_states"

    user_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    situation_id: Mapped[str | None] = mapped_column(String(32))
    level_id: Mapped[str | None] = mapped_column(String(16))
    last_indices: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class BagState(Base):
    __tablename__ = "bag_states"
    __table_args__ = (UniqueConstraint("user_hash", "bag_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_hash: Mapped[str] = mapped_column(String(64), index=True)
    bag_key: Mapped[str] = mapped_column(String(96))
    remaining: Mapped[str] = mapped_column(Text)
    last_index: Mapped[int | None] = mapped_column(Integer)


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (UniqueConstraint("day", "event", "situation_id", "level_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date)
    event: Mapped[str] = mapped_column(String(32))
    situation_id: Mapped[str] = mapped_column(String(32), default="")
    level_id: Mapped[str] = mapped_column(String(16), default="")
    count: Mapped[int] = mapped_column(Integer, default=0)
