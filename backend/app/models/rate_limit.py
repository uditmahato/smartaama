# backend/app/models/rate_limit.py
"""
Hit log for the database-backed sliding-window rate limiter (app/core/rate_limit.py).

One row per guarded request (`key` = client IP, `hit_at` = when). Counting rows per key inside
the window gives the current usage; because every worker/process writes to and reads from the
same table, the limit is global across processes sharing the database. Rows older than the
window are pruned opportunistically by the limiter itself, so the table stays small.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# SQLite only auto-increments an INTEGER PRIMARY KEY (BIGINT would not be a rowid alias), so the
# id is BIGINT on PostgreSQL and INTEGER on SQLite; both are large enough for a rolling hit log.
_HIT_ID = BigInteger().with_variant(Integer(), "sqlite")


class AuthRateLimitHit(Base):
    __tablename__ = "auth_rate_limit_hits"

    id: Mapped[int] = mapped_column(_HIT_ID, primary_key=True, autoincrement=True)

    # Rate-limit key: the client IP (first X-Forwarded-For hop or the socket peer).
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    hit_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<AuthRateLimitHit id={self.id} key={self.key!r} hit_at={self.hit_at}>"
