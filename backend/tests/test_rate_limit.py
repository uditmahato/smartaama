# backend/tests/test_rate_limit.py
"""
Database-backed sliding-window rate limiter (app/core/rate_limit.py).

- 429 + Retry-After once a key exceeds RATE_LIMIT_MAX_REQUESTS inside the window
- state is in the DB: two independent Sessions (stand-ins for two worker processes) share it
- hits age out of the window; expired rows are pruned
- RATE_LIMIT_DISABLED=true (the default for the suite) never touches the table
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.rate_limit import DBSlidingWindowRateLimiter, auth_rate_limiter
from app.models.rate_limit import AuthRateLimitHit
from tests.conftest import TEST_PASSWORD, TestingSessionLocal, WRONG_PASSWORD

LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"


def _hits(db, key=None) -> int:
    stmt = select(func.count()).select_from(AuthRateLimitHit)
    if key is not None:
        stmt = stmt.where(AuthRateLimitHit.key == key)
    return int(db.execute(stmt).scalar_one())


@pytest.fixture()
def limiter_enabled(monkeypatch):
    """Turn the limiter on for one test (suite default is RATE_LIMIT_DISABLED=true) and clean up."""
    monkeypatch.setattr(settings, "RATE_LIMIT_DISABLED", False)
    auth_rate_limiter.reset()
    yield auth_rate_limiter
    auth_rate_limiter.reset()


# ------------------------------------------------------------------ unit: limiter object
def test_check_allows_up_to_max_then_blocks_with_retry_after(db):
    lim = DBSlidingWindowRateLimiter(max_requests=3, window_seconds=60, prune_every=1000)
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(3):
        allowed, retry = lim.check(db, "1.2.3.4", now=t0 + timedelta(seconds=i))
        assert allowed and retry == 0
    allowed, retry = lim.check(db, "1.2.3.4", now=t0 + timedelta(seconds=3))
    assert not allowed
    # 4 hits in the window (t0..t0+3, the refused one counts too); the next request may only be
    # preceded by 2 in-window hits, so the two oldest (t0, t0+1) must age out: (t0+1+60) - (t0+3) = 58 s
    assert retry == 58
    # other keys are independent
    assert lim.check(db, "5.6.7.8", now=t0 + timedelta(seconds=3)) == (True, 0)


def test_hits_slide_out_of_the_window(db):
    lim = DBSlidingWindowRateLimiter(max_requests=2, window_seconds=10, prune_every=1000)
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert lim.check(db, "k", now=t0)[0]
    assert lim.check(db, "k", now=t0 + timedelta(seconds=1))[0]
    assert not lim.check(db, "k", now=t0 + timedelta(seconds=2))[0]
    # 11 s later the first two hits are outside the window (the refused hit at +2 s still counts)
    assert lim.check(db, "k", now=t0 + timedelta(seconds=11))[0]


def test_expired_hits_are_pruned_opportunistically(db):
    lim = DBSlidingWindowRateLimiter(max_requests=100, window_seconds=10, prune_every=3)
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    lim.check(db, "old", now=t0)
    lim.check(db, "old", now=t0)
    assert _hits(db) == 2
    # third call is a prune call: rows older than the window (as of `now`) go away
    lim.check(db, "new", now=t0 + timedelta(seconds=30))
    assert _hits(db, "old") == 0 and _hits(db, "new") == 1
    # a key over its limit also triggers pruning
    lim2 = DBSlidingWindowRateLimiter(max_requests=1, window_seconds=10, prune_every=10_000)
    lim2.check(db, "stale", now=t0)
    lim2.check(db, "hammer", now=t0 + timedelta(seconds=60))
    lim2.check(db, "hammer", now=t0 + timedelta(seconds=60))  # over limit -> prune
    assert _hits(db, "stale") == 0


def test_two_independent_sessions_share_the_budget():
    """Two Sessions stand in for two worker processes: the count is global, not per process."""
    lim_a = DBSlidingWindowRateLimiter(max_requests=4, window_seconds=60, prune_every=1000)
    lim_b = DBSlidingWindowRateLimiter(max_requests=4, window_seconds=60, prune_every=1000)
    s1, s2 = TestingSessionLocal(), TestingSessionLocal()
    try:
        assert lim_a.check(s1, "shared")[0]
        assert lim_b.check(s2, "shared")[0]
        assert lim_a.check(s1, "shared")[0]
        assert lim_b.check(s2, "shared")[0]
        # 5th hit, whichever "process" sees it, is refused
        allowed, retry = lim_b.check(s2, "shared")
        assert not allowed and 1 <= retry <= 60
        assert not lim_a.check(s1, "shared")[0]
        assert _hits(s1, "shared") == 6 and _hits(s2, "shared") == 6
    finally:
        s1.close()
        s2.close()


# ------------------------------------------------------------------ dependency / endpoints
def test_login_429_after_budget_and_retry_after_header(client, clinician_a, limiter_enabled, monkeypatch, db):
    monkeypatch.setattr(limiter_enabled, "max_requests", 3)
    for _ in range(3):
        assert client.post(LOGIN, data={"username": "clin-a", "password": WRONG_PASSWORD}).status_code == 401
    resp = client.post(LOGIN, data={"username": "clin-a", "password": WRONG_PASSWORD})
    assert resp.status_code == 429
    assert 1 <= int(resp.headers["Retry-After"]) <= settings.RATE_LIMIT_WINDOW_SECONDS
    # even correct credentials are refused while blocked
    assert client.post(LOGIN, data={"username": "clin-a", "password": TEST_PASSWORD}).status_code == 429
    # another IP (first X-Forwarded-For hop) has its own budget
    ok = client.post(LOGIN, data={"username": "clin-a", "password": TEST_PASSWORD}, headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"})
    assert ok.status_code == 200
    assert _hits(db, "203.0.113.9") == 1


def test_register_and_refresh_are_guarded(client, seeded_facilities, limiter_enabled, monkeypatch):
    monkeypatch.setattr(limiter_enabled, "max_requests", 1)
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": "x" * 43}).status_code == 401
    # budget shared per IP across the guarded endpoints
    assert client.post(REGISTER, data={"email": "x"}).status_code == 429
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": "x" * 43}).status_code == 429


def test_disabled_limiter_writes_nothing(client, clinician_a, db):
    assert settings.RATE_LIMIT_DISABLED is True
    for _ in range(12):
        assert client.post(LOGIN, data={"username": "clin-a", "password": WRONG_PASSWORD}).status_code == 401
    assert _hits(db) == 0
