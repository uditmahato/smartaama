# backend/tests/test_refresh_tokens.py
"""
Refresh tokens: login issues one, /auth/refresh rotates it (old one dies), reuse of a rotated
token revokes the whole family, /auth/logout revokes, and refresh is refused for users that may
no longer sign in (rejected / soft-deleted / unapproved) or for expired tokens.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_refresh_token, revoke_all_refresh_tokens
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.user import User
from tests.conftest import TEST_PASSWORD, bearer

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
ADMIN_USERS = "/api/v1/admin/users"


def _login(client, username, password=TEST_PASSWORD):
    resp = client.post(LOGIN, data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _refresh(client, token):
    return client.post(REFRESH, json={"refresh_token": token})


def _me(client, access_token):
    return client.get(ME, headers={"Authorization": f"Bearer {access_token}"})


def _row(db, secret) -> RefreshToken | None:
    return db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(secret))).scalar_one_or_none()


# ------------------------------------------------------------------ login
def test_login_returns_refresh_token_and_stores_only_hash(client, clinician_a, db):
    body = _login(client, "clin-a")
    assert set(body) >= {"access_token", "token_type", "expires_in", "refresh_token"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    secret = body["refresh_token"]
    assert len(secret) >= 32

    row = _row(db, secret)
    assert row is not None and row.user_id == clinician_a.id and row.revoked_at is None
    # the secret itself is stored nowhere
    all_hashes = db.execute(select(RefreshToken.token_hash)).scalars().all()
    assert secret not in all_hashes
    assert _me(client, body["access_token"]).status_code == 200


def test_each_login_issues_a_distinct_token(client, clinician_a, db):
    a = _login(client, "clin-a")["refresh_token"]
    b = _login(client, "clin-a")["refresh_token"]
    assert a != b
    rows = db.execute(select(RefreshToken).where(RefreshToken.user_id == clinician_a.id)).scalars().all()
    assert len(rows) == 2


# ------------------------------------------------------------------ rotation
def test_refresh_rotates_and_old_token_stops_working(client, clinician_a, db):
    first = _login(client, "clin-a")
    resp = _refresh(client, first["refresh_token"])
    assert resp.status_code == 200, resp.text
    second = resp.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert second["access_token"]
    assert _me(client, second["access_token"]).status_code == 200

    old = _row(db, first["refresh_token"])
    new = _row(db, second["refresh_token"])
    assert old.revoked_at is not None and old.replaced_by_id == new.id
    assert new.revoked_at is None

    # the old token cannot be used again (and this counts as reuse, see below)
    assert _refresh(client, first["refresh_token"]).status_code == 401


def test_reuse_of_rotated_token_revokes_all_tokens_of_user(client, clinician_a, hospital_x, db):
    first = _login(client, "clin-a")
    other_session = _login(client, "clin-a")  # a second device
    unrelated = _login(client, "hosp-x")

    second = _refresh(client, first["refresh_token"]).json()
    # attacker replays the rotated token
    resp = _refresh(client, first["refresh_token"])
    assert resp.status_code == 401

    # every token of clin-a is dead now: the successor AND the other device
    assert _refresh(client, second["refresh_token"]).status_code == 401
    assert _refresh(client, other_session["refresh_token"]).status_code == 401
    live = db.execute(
        select(RefreshToken).where(RefreshToken.user_id == clinician_a.id, RefreshToken.revoked_at.is_(None))
    ).scalars().all()
    assert live == []
    # ... but the incident is audited and other users are untouched
    actions = db.execute(select(AuditLog.action).where(AuditLog.entity_id == clinician_a.id)).scalars().all()
    assert "REFRESH_TOKEN_REUSE_DETECTED" in actions
    assert _refresh(client, unrelated["refresh_token"]).status_code == 200


def test_unknown_or_malformed_refresh_token_401_or_422(client, clinician_a):
    assert _refresh(client, "x" * 43).status_code == 401
    assert client.post(REFRESH, json={"refresh_token": "short"}).status_code == 422
    assert client.post(REFRESH, json={}).status_code == 422


def test_expired_refresh_token_401(client, clinician_a, db):
    body = _login(client, "clin-a")
    row = _row(db, body["refresh_token"])
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert _refresh(client, body["refresh_token"]).status_code == 401
    db.refresh(row)
    assert row.revoked_at is not None  # expired tokens are retired, not left live


# ------------------------------------------------------------------ logout
def test_logout_revokes_and_is_idempotent(client, clinician_a, db):
    body = _login(client, "clin-a")
    resp = client.post(LOGOUT, json={"refresh_token": body["refresh_token"]})
    assert resp.status_code == 204
    assert _row(db, body["refresh_token"]).revoked_at is not None
    assert _refresh(client, body["refresh_token"]).status_code == 401
    # again: still 204 (no-op), and an unknown token is also a 204
    assert client.post(LOGOUT, json={"refresh_token": body["refresh_token"]}).status_code == 204
    assert client.post(LOGOUT, json={"refresh_token": "definitely-not-a-token"}).status_code == 204
    actions = db.execute(select(AuditLog.action).where(AuditLog.entity_id == clinician_a.id)).scalars().all()
    assert actions.count("USER_LOGOUT") == 1
    # the (stateless) access token keeps working until it expires — documented behaviour
    assert _me(client, body["access_token"]).status_code == 200


def test_logout_does_not_touch_other_tokens(client, clinician_a, db):
    a = _login(client, "clin-a")
    b = _login(client, "clin-a")
    assert client.post(LOGOUT, json={"refresh_token": a["refresh_token"]}).status_code == 204
    assert _refresh(client, b["refresh_token"]).status_code == 200


# ------------------------------------------------------------------ eligibility
def test_refresh_refused_for_rejected_user_and_tokens_revoked(client, admin_user, clinician_a, db):
    body = _login(client, "clin-a")
    resp = client.patch(f"{ADMIN_USERS}/{clinician_a.id}/reject", headers=bearer(admin_user))
    assert resp.status_code == 200
    assert _row(db, body["refresh_token"]).revoked_at is not None
    assert _refresh(client, body["refresh_token"]).status_code == 401
    # a token that somehow survived would still be refused because the user is not eligible
    from app.core.security import issue_refresh_token

    secret, _ = issue_refresh_token(db, user=db.get(User, clinician_a.id))
    db.commit()
    assert _refresh(client, secret).status_code == 401


def test_refresh_refused_for_soft_deleted_user(client, admin_user, clinician_a, db):
    body = _login(client, "clin-a")
    assert client.delete(f"{ADMIN_USERS}/{clinician_a.id}", headers=bearer(admin_user)).status_code == 200
    assert _refresh(client, body["refresh_token"]).status_code == 401
    assert _row(db, body["refresh_token"]).revoked_at is not None


def test_refresh_refused_for_unapproved_or_inactive_user(client, clinician_a, db):
    body = _login(client, "clin-a")
    u = db.get(User, clinician_a.id)
    u.is_approved = False
    db.commit()
    assert _refresh(client, body["refresh_token"]).status_code == 401
    u.is_approved = True
    u.is_active = False
    db.commit()
    assert _refresh(client, body["refresh_token"]).status_code == 401


def test_role_change_revokes_refresh_tokens(client, admin_user, clinician_a, db):
    body = _login(client, "clin-a")
    resp = client.patch(f"{ADMIN_USERS}/{clinician_a.id}/role", json={"role": "viewer"}, headers=bearer(admin_user))
    assert resp.status_code == 200, resp.text
    assert _refresh(client, body["refresh_token"]).status_code == 401
    # same-role no-op does not revoke
    again = _login(client, "clin-a")
    resp = client.patch(f"{ADMIN_USERS}/{clinician_a.id}/role", json={"role": "viewer"}, headers=bearer(admin_user))
    assert resp.status_code == 200
    assert _refresh(client, again["refresh_token"]).status_code == 200


def test_revoke_all_helper_counts_only_live_tokens(client, clinician_a, db):
    _login(client, "clin-a")
    _login(client, "clin-a")
    assert revoke_all_refresh_tokens(db, clinician_a.id) == 2
    db.commit()
    assert revoke_all_refresh_tokens(db, clinician_a.id) == 0


def test_refresh_is_rate_limited(client, clinician_a, monkeypatch):
    from app.core.config import settings
    from app.core.rate_limit import auth_rate_limiter

    monkeypatch.setattr(settings, "RATE_LIMIT_DISABLED", False)
    monkeypatch.setattr(auth_rate_limiter, "max_requests", 2)
    auth_rate_limiter.reset()
    try:
        for _ in range(2):
            assert _refresh(client, "x" * 43).status_code == 401
        resp = _refresh(client, "x" * 43)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
    finally:
        auth_rate_limiter.reset()
