# backend/tests/test_auth.py
"""Login, token validation, registration validation, bootstrap gating and rate limiting."""

from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.models.user import User, UserRole
from tests.conftest import FACILITY_A, TEST_PASSWORD, bearer

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
REGISTER = "/api/v1/auth/register"
BOOTSTRAP = "/api/v1/auth/bootstrap-admin"


# ------------------------------------------------------------------ login / me
def test_login_success_and_me_has_no_password_hash(client, clinician_a, login):
    headers = login("clin-a")
    resp = client.get(ME, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "clin-a"
    assert body["role"] == "clinician"
    assert body["facility_name"] == FACILITY_A
    assert body["has_id_card"] is False
    assert "password_hash" not in body
    assert "id_card_image_path" not in body


def test_login_wrong_password(client, clinician_a):
    resp = client.post(LOGIN, data={"username": "clin-a", "password": "nope-nope-nope"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(LOGIN, data={"username": "ghost", "password": TEST_PASSWORD})
    assert resp.status_code == 401


def test_unapproved_user_cannot_login(client, make_user):
    make_user("pend", is_approved=False, is_active=True, facility_name=FACILITY_A)
    resp = client.post(LOGIN, data={"username": "pend", "password": TEST_PASSWORD})
    assert resp.status_code == 403
    assert "not approved" in resp.json()["detail"].lower()


def test_get_current_user_rejects_unapproved_token(client, make_user):
    # A valid JWT is not enough: the account must currently be approved + active.
    user = make_user("later-revoked", is_approved=True, facility_name=FACILITY_A)
    headers = bearer(user)
    assert client.get(ME, headers=headers).status_code == 200


def test_get_current_user_rejects_revoked_and_deleted(client, make_user, db):
    user = make_user("revoked", facility_name=FACILITY_A)
    headers = bearer(user)
    assert client.get(ME, headers=headers).status_code == 200

    # un-approve
    u = db.get(User, user.id)
    u.is_approved = False
    db.commit()
    assert client.get(ME, headers=headers).status_code == 401

    # approve again but soft-delete
    u.is_approved = True
    u.deleted_at = datetime.now(timezone.utc)
    db.commit()
    assert client.get(ME, headers=headers).status_code == 401


def test_soft_deleted_user_cannot_login(client, make_user, db):
    user = make_user("gone", facility_name=FACILITY_A)
    u = db.get(User, user.id)
    u.deleted_at = datetime.now(timezone.utc)
    u.is_active = False
    u.is_approved = False
    db.commit()
    resp = client.post(LOGIN, data={"username": "gone", "password": TEST_PASSWORD})
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get(ME).status_code == 401


def test_bad_token_rejected(client):
    assert client.get(ME, headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


# ------------------------------------------------------------------ register
def _register_form(facility_id, **overrides):
    form = {
        "email": "new.doc@example.test",
        "password": "LongEnough123!",
        "full_name": "New Doctor",
        "phone_number": "9800000000",
        "nmc_number": "NMC-1",
        "working_hospital": "PHC A",
        "facility_type": "phc",
        "facility_id": str(facility_id),
    }
    form.update(overrides)
    return form


def test_register_short_password_422(client, seeded_facilities):
    resp = client.post(REGISTER, data=_register_form(seeded_facilities[FACILITY_A], password="short"))
    assert resp.status_code == 422


def test_register_success_pending_and_user_out(client, seeded_facilities, db):
    resp = client.post(REGISTER, data=_register_form(seeded_facilities[FACILITY_A]))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "Awaiting approval" in body["detail"]
    user = body["user"]
    assert user["is_approved"] is False and user["is_active"] is False
    assert user["facility_name"] == FACILITY_A
    assert user["has_id_card"] is False
    assert "password_hash" not in user

    # cannot log in until approved
    resp = client.post(LOGIN, data={"username": "new.doc@example.test", "password": "LongEnough123!"})
    assert resp.status_code == 403


def test_register_duplicate_email_400(client, seeded_facilities):
    form = _register_form(seeded_facilities[FACILITY_A])
    assert client.post(REGISTER, data=form).status_code == 201
    assert client.post(REGISTER, data=form).status_code == 400


def test_register_unknown_facility_404(client, seeded_facilities):
    import uuid

    resp = client.post(REGISTER, data=_register_form(uuid.uuid4()))
    assert resp.status_code == 404


def test_register_bad_id_card_extension_rejected(client, seeded_facilities):
    files = {"id_card_image": ("evil.exe", io.BytesIO(b"MZ..."), "application/octet-stream")}
    resp = client.post(REGISTER, data=_register_form(seeded_facilities[FACILITY_A]), files=files)
    assert resp.status_code in (400, 422)


def test_register_id_card_wrong_content_type_rejected(client, seeded_facilities):
    files = {"id_card_image": ("card.png", io.BytesIO(b"\x89PNG"), "text/plain")}
    resp = client.post(REGISTER, data=_register_form(seeded_facilities[FACILITY_A]), files=files)
    assert resp.status_code == 400


def test_register_id_card_too_large_rejected(client, seeded_facilities):
    # conftest sets MAX_ID_CARD_SIZE_MB=1
    big = io.BytesIO(b"\x00" * (settings.MAX_ID_CARD_SIZE_MB * 1024 * 1024 + 1))
    files = {"id_card_image": ("card.png", big, "image/png")}
    resp = client.post(REGISTER, data=_register_form(seeded_facilities[FACILITY_A]), files=files)
    assert resp.status_code == 413


def test_register_id_card_stored_as_uuid_name(client, seeded_facilities, db):
    from app.settings import ID_CARDS_DIR

    files = {"id_card_image": ("../../etc/passwd.png", io.BytesIO(b"\x89PNGdata"), "image/png")}
    resp = client.post(REGISTER, data=_register_form(seeded_facilities[FACILITY_A]), files=files)
    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["has_id_card"] is True

    user = db.query(User).filter(User.username == "new.doc@example.test").one()
    assert user.id_card_image_path
    assert "/" not in user.id_card_image_path and "\\" not in user.id_card_image_path
    assert user.id_card_image_path.endswith(".png")
    assert "passwd" not in user.id_card_image_path
    assert (ID_CARDS_DIR / user.id_card_image_path).is_file()


# ------------------------------------------------------------------ bootstrap
def test_bootstrap_requires_matching_token(client, seeded_facilities):
    payload = {
        "username": "boot-admin",
        "password": "BootstrapPass1!",
        "full_name": "Boot",
        "facility_kind": "hospital",
        "facility_id": str(seeded_facilities["Hospital X"]),
    }
    # missing header
    assert client.post(BOOTSTRAP, json=payload).status_code == 403
    # wrong header
    assert client.post(BOOTSTRAP, json=payload, headers={"X-Bootstrap-Token": "wrong"}).status_code == 403
    # correct
    resp = client.post(BOOTSTRAP, json=payload, headers={"X-Bootstrap-Token": "test-bootstrap-token"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "admin" and body["is_super_admin"] is True
    assert body["facility_name"] == "Hospital X"
    assert "password_hash" not in body


def test_bootstrap_disabled_when_token_empty(client, seeded_facilities, monkeypatch):
    monkeypatch.setattr(settings, "BOOTSTRAP_TOKEN", "")
    payload = {
        "username": "boot-admin",
        "password": "BootstrapPass1!",
        "facility_kind": "hospital",
        "facility_id": str(seeded_facilities["Hospital X"]),
    }
    resp = client.post(BOOTSTRAP, json=payload, headers={"X-Bootstrap-Token": ""})
    assert resp.status_code == 403


def test_bootstrap_disabled_outside_dev(client, seeded_facilities, monkeypatch):
    monkeypatch.setattr(settings, "ENV", "prod")
    payload = {
        "username": "boot-admin",
        "password": "BootstrapPass1!",
        "facility_kind": "hospital",
        "facility_id": str(seeded_facilities["Hospital X"]),
    }
    resp = client.post(BOOTSTRAP, json=payload, headers={"X-Bootstrap-Token": "test-bootstrap-token"})
    assert resp.status_code == 403


def test_bootstrap_short_password_422(client, seeded_facilities):
    payload = {
        "username": "boot-admin",
        "password": "short",
        "facility_kind": "hospital",
        "facility_id": str(seeded_facilities["Hospital X"]),
    }
    resp = client.post(BOOTSTRAP, json=payload, headers={"X-Bootstrap-Token": "test-bootstrap-token"})
    assert resp.status_code == 422


# ------------------------------------------------------------------ rate limit
def test_login_rate_limited_per_ip(client, clinician_a, monkeypatch):
    from app.core.rate_limit import auth_rate_limiter

    monkeypatch.setattr(settings, "RATE_LIMIT_DISABLED", False)
    monkeypatch.setattr(auth_rate_limiter, "max_requests", 3)
    auth_rate_limiter.reset()

    for _ in range(3):
        assert client.post(LOGIN, data={"username": "clin-a", "password": "bad-bad-bad"}).status_code == 401
    resp = client.post(LOGIN, data={"username": "clin-a", "password": "bad-bad-bad"})
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers

    # A different client IP is not affected
    resp = client.post(
        LOGIN,
        data={"username": "clin-a", "password": TEST_PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    assert resp.status_code == 200
    auth_rate_limiter.reset()


def test_rate_limit_disabled_by_default_in_tests(client, clinician_a):
    for _ in range(15):
        assert client.post(LOGIN, data={"username": "clin-a", "password": "bad-bad-bad"}).status_code == 401
