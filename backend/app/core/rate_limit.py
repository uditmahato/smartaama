# backend/app/core/rate_limit.py
"""
Database-backed sliding-window rate limiter for the unauthenticated auth endpoints
(/auth/login, /auth/register, /auth/refresh).

How it works
- Every guarded request inserts one row into `auth_rate_limit_hits` (key = client IP, hit_at = now)
  and then counts the rows for that key whose hit_at lies inside the last RATE_LIMIT_WINDOW_SECONDS.
  If the count exceeds RATE_LIMIT_MAX_REQUESTS the request is refused with 429 + `Retry-After`
  (seconds until enough old hits have aged out of the window). Refused requests are counted too,
  so a client that keeps hammering stays blocked until it backs off for a full window.
- Because the state lives in the application database, the limit is shared by every uvicorn
  worker / process / instance that uses the same database (unlike the previous in-memory
  version, which counted per process). It is a brute-force brake, not an exact counter: with
  READ COMMITTED isolation, requests that arrive truly concurrently at the boundary do not see
  each other's uncommitted hit and may all be admitted (over-admission bounded by the number of
  concurrent requests); the very next request is refused. Use a per-key lock if exactness matters.
- Rows older than the window are useless; they are pruned opportunistically (every
  PRUNE_EVERY-th check in this process, and whenever a key is over the limit), so the table stays
  a few rows per active client.
- Keyed by client IP (first hop of X-Forwarded-For if present, else the socket peer). Behind a
  reverse proxy the peer is always the proxy, so XFF is honoured; when exposed directly a client
  could rotate XFF values, which is why this is a brake against brute force, not a security
  boundary.

Configuration (app.core.config.Settings):
- RATE_LIMIT_DISABLED=true            -> limiter is a no-op: no DB reads or writes (test-suite, e2e)
- RATE_LIMIT_MAX_REQUESTS (default 10) per RATE_LIMIT_WINDOW_SECONDS (default 60), sliding window.

Public surface (kept stable): the FastAPI dependency `auth_rate_limit`, the module-level
`auth_rate_limiter` (attributes `max_requests`, `window_seconds`, `check()`, `reset()`) and
`client_ip()`.
"""

from __future__ import annotations

import ipaddress

import math
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.rate_limit import AuthRateLimitHit

# Prune expired rows on every N-th check made by this process (plus whenever a key is over limit).
PRUNE_EVERY = 50


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes for DateTime(timezone=True); treat them as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class DBSlidingWindowRateLimiter:
    """
    Sliding-window limiter whose hit log is the `auth_rate_limit_hits` table.

    Works across processes/workers that share the database: `check()` takes the caller's Session,
    records the hit and counts hits within the window in the same transaction, then commits.
    """

    def __init__(self, max_requests: int, window_seconds: int, prune_every: int = PRUNE_EVERY) -> None:
        self.max_requests = int(max_requests)
        self.window_seconds = int(window_seconds)
        self.prune_every = max(1, int(prune_every))
        self._calls = 0
        self._lock = threading.Lock()

    # -- internals ---------------------------------------------------------------------------
    def _should_prune(self) -> bool:
        with self._lock:
            self._calls += 1
            return self._calls % self.prune_every == 0

    def _prune(self, db: Session, cutoff: datetime) -> int:
        result = db.execute(delete(AuthRateLimitHit).where(AuthRateLimitHit.hit_at <= cutoff))
        return int(result.rowcount or 0)

    def _retry_after(self, db: Session, key: str, cutoff: datetime, now: datetime, count: int) -> int:
        """
        Seconds until the key is allowed again: the next request succeeds once at most
        max_requests-1 hits remain in the window, i.e. when the (count - max_requests + 1)-th
        oldest in-window hit has aged out.
        """
        skip = max(0, count - self.max_requests)
        boundary = db.execute(
            select(AuthRateLimitHit.hit_at)
            .where(AuthRateLimitHit.key == key, AuthRateLimitHit.hit_at > cutoff)
            .order_by(AuthRateLimitHit.hit_at.asc())
            .offset(skip)
            .limit(1)
        ).scalar_one_or_none()
        if boundary is None:
            return self.window_seconds
        seconds = (_as_utc(boundary) + timedelta(seconds=self.window_seconds) - now).total_seconds()
        return int(min(self.window_seconds, max(1, math.ceil(seconds))))

    # -- API ---------------------------------------------------------------------------------
    def check(self, db: Session, key: str, now: Optional[datetime] = None) -> Tuple[bool, int]:
        """
        Record a hit for `key` and return `(allowed, retry_after_seconds)`.
        `allowed` is False when the hits for `key` inside the window (including this one) exceed
        `max_requests`; `retry_after_seconds` is 0 when allowed. Commits the caller's session.
        """
        now = now or _utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)

        db.add(AuthRateLimitHit(key=key, hit_at=now))
        db.flush()
        count = int(
            db.execute(
                select(func.count())
                .select_from(AuthRateLimitHit)
                .where(AuthRateLimitHit.key == key, AuthRateLimitHit.hit_at > cutoff)
            ).scalar_one()
        )
        allowed = count <= self.max_requests
        retry_after = 0 if allowed else self._retry_after(db, key, cutoff, now, count)

        if not allowed or self._should_prune():
            self._prune(db, cutoff)
        db.commit()
        return allowed, retry_after

    def reset(self) -> None:
        """Forget every hit (tests). Uses its own connection; a missing table is ignored."""
        from sqlalchemy.exc import SQLAlchemyError

        from app.db.session import engine

        with self._lock:
            self._calls = 0
        try:
            with engine.begin() as conn:
                conn.execute(delete(AuthRateLimitHit))
        except SQLAlchemyError:
            # Table not created yet (e.g. reset() before the schema exists): nothing to forget.
            pass


auth_rate_limiter = DBSlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


# Longest textual IPv6 (incl. IPv4-mapped) is 45 chars; audit_logs.ip_address is String(64).
MAX_IP_LEN = 45


def normalize_client_ip(x_forwarded_for: Optional[str], peer_host: Optional[str] = None) -> Optional[str]:
    """
    Best-effort client address for rate limiting and audit rows: the first hop of
    X-Forwarded-For if it parses as an IP address, else the peer host. Never returns a
    string longer than MAX_IP_LEN, so a hostile/huge header can never break a DB write.
    """
    if x_forwarded_for:
        first = x_forwarded_for.split(",")[0].strip()[: MAX_IP_LEN + 1]
        if first:
            try:
                return str(ipaddress.ip_address(first))
            except ValueError:
                pass  # not an IP literal (garbage / hostname) -> fall back to the peer
    if peer_host:
        peer = peer_host.strip()[:MAX_IP_LEN]
        return peer or None
    return None


def client_ip(request: Request) -> str:
    return (
        normalize_client_ip(request.headers.get("x-forwarded-for"), request.client.host if request.client else None)
        or "unknown"
    )


def auth_rate_limit(request: Request, db: Session = Depends(get_db)) -> None:
    """
    FastAPI dependency: 429 when the caller IP exceeds the auth request budget.
    With RATE_LIMIT_DISABLED=true it returns immediately (no database access at all).
    """
    if settings.RATE_LIMIT_DISABLED:
        return
    allowed, retry_after = auth_rate_limiter.check(db, client_ip(request))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
