# backend/tests/test_admin.py
"""Admin endpoints: user lists (no password_hash), approve/reject/soft-delete, ID-card retrieval."""

from __future__ import annotations

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.settings import ID_CARDS_DIR
from tests.conftest import FACILITY_A, TEST_PASSWORD, bearer

USERS = "/api/v1/admin/users"
PENDING = "/api/v1/admin/users/pending"
REJECTED = "/api/v1/admin/users/rejected"


def _assert_no_secrets(items):
    for u in items:
        assert "password_hash" not in u
        assert "id_card_image_path" not in u
        assert "has_id_card" in u


def test_lists_require_admin(client, clinician_a, viewer_a):
    for user in (clinician_a, viewer_a):
        assert client.get(USERS, headers=bearer(user)).status_code == 403
        assert client.get(PENDING, headers=bearer(user)).status_code == 403
        assert client.get(REJECTED, headers=bearer(user)).status_code == 403
    assert client.get(USERS).status_code == 401
    assert client.get(REJECTED).status_code == 401


def test_admin_lists_have_no_password_hash(client, admin_user, clinician_a, pending_user):
    resp = client.get(USERS, headers=bearer(admin_user))
    assert resp.status_code == 200
    body = resp.json()
    _assert_no_secrets(body)
    assert "clin-a" in {u["username"] for u in body}
    assert "admin" not in {u["username"] for u in body}  # admins excluded from the users list

    resp = client.get(PENDING, headers=bearer(admin_user))
    assert resp.status_code == 200
    body = resp.json()
    _assert_no_secrets(body)
    assert [u["username"] for u in body] == ["pending"]


def test_approve_then_login_and_audit(client, admin_user, pending_user, db):
    resp = client.patch(f"{USERS}/{pending_user.id}/approve", headers=bearer(admin_user))
    assert resp.status_code == 200
    resp = client.post("/api/v1/auth/login", data={"username": "pending", "password": TEST_PASSWORD})
    assert resp.status_code == 200
    actions = db.execute(select(AuditLog.action).where(AuditLog.entity_id == pending_user.id)).scalars().all()
    assert "USER_APPROVED" in actions


def test_reject_writes_audit(client, admin_user, clinician_a, db):
    resp = client.patch(f"{USERS}/{clinician_a.id}/reject", headers=bearer(admin_user))
    assert resp.status_code == 200
    actions = db.execute(select(AuditLog.action).where(AuditLog.entity_id == clinician_a.id)).scalars().all()
    assert "USER_REJECTED" in actions
    # rejected user can no longer use their token
    assert client.get("/api/v1/auth/me", headers=bearer(clinician_a)).status_code == 401


# ------------------------------------------------------------------ rejected registrations
def test_rejected_user_leaves_pending_and_is_listed_under_rejected(client, admin_user, pending_user, make_user, db):
    other_pending = make_user("pending-2", facility_name=FACILITY_A, is_approved=False, is_active=False)
    headers = bearer(admin_user)
    assert {u["username"] for u in client.get(PENDING, headers=headers).json()} == {"pending", other_pending.username}
    assert client.get(REJECTED, headers=headers).json() == []

    resp = client.patch(f"{USERS}/{pending_user.id}/reject", headers=headers)
    assert resp.status_code == 200

    row = db.get(User, pending_user.id)
    db.refresh(row)
    assert row.rejected_at is not None and row.rejected_by == admin_user.id
    assert row.is_approved is False and row.is_active is False

    # excluded from pending, present under /rejected (with rejected_at, no secrets)
    assert [u["username"] for u in client.get(PENDING, headers=headers).json()] == ["pending-2"]
    rejected = client.get(REJECTED, headers=headers).json()
    _assert_no_secrets(rejected)
    assert [u["username"] for u in rejected] == ["pending"]
    assert rejected[0]["rejected_at"] is not None and rejected[0]["is_approved"] is False
    # not in the approved users list either
    assert "pending" not in {u["username"] for u in client.get(USERS, headers=headers).json()}
    # and cannot log in
    assert client.post("/api/v1/auth/login", data={"username": "pending", "password": TEST_PASSWORD}).status_code == 403


def test_approve_clears_rejection(client, admin_user, pending_user, db):
    headers = bearer(admin_user)
    assert client.patch(f"{USERS}/{pending_user.id}/reject", headers=headers).status_code == 200
    assert [u["username"] for u in client.get(REJECTED, headers=headers).json()] == ["pending"]

    resp = client.patch(f"{USERS}/{pending_user.id}/approve", headers=headers)
    assert resp.status_code == 200
    row = db.get(User, pending_user.id)
    db.refresh(row)
    assert row.rejected_at is None and row.rejected_by is None
    assert row.is_approved is True and row.is_active is True
    assert client.get(REJECTED, headers=headers).json() == []
    assert client.get(PENDING, headers=headers).json() == []
    me = client.get("/api/v1/auth/me", headers=bearer(row))
    assert me.status_code == 200 and me.json()["rejected_at"] is None
    assert client.post("/api/v1/auth/login", data={"username": "pending", "password": TEST_PASSWORD}).status_code == 200


def test_soft_deleted_users_are_not_listed_as_rejected(client, admin_user, pending_user):
    headers = bearer(admin_user)
    assert client.patch(f"{USERS}/{pending_user.id}/reject", headers=headers).status_code == 200
    assert client.delete(f"{USERS}/{pending_user.id}", headers=headers).status_code == 200
    assert client.get(REJECTED, headers=headers).json() == []


def test_soft_delete_user(client, admin_user, clinician_a, db):
    headers = bearer(admin_user)
    resp = client.delete(f"{USERS}/{clinician_a.id}", headers=headers)
    assert resp.status_code == 200

    # row still exists but is marked deleted / inactive / unapproved
    row = db.get(User, clinician_a.id)
    db.refresh(row)
    assert row.deleted_at is not None
    assert row.is_active is False and row.is_approved is False

    # excluded from lists
    usernames = {u["username"] for u in client.get(USERS, headers=headers).json()}
    assert "clin-a" not in usernames
    usernames = {u["username"] for u in client.get(PENDING, headers=headers).json()}
    assert "clin-a" not in usernames

    # cannot log in, token rejected
    assert client.post("/api/v1/auth/login", data={"username": "clin-a", "password": TEST_PASSWORD}).status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer(clinician_a)).status_code == 401

    # deleting again -> 404 (behaves as non-existent)
    assert client.delete(f"{USERS}/{clinician_a.id}", headers=headers).status_code == 404

    actions = db.execute(select(AuditLog.action).where(AuditLog.entity_id == clinician_a.id)).scalars().all()
    assert "USER_SOFT_DELETED" in actions


def test_cannot_delete_self(client, admin_user):
    resp = client.delete(f"{USERS}/{admin_user.id}", headers=bearer(admin_user))
    assert resp.status_code == 400


def test_only_super_admin_can_delete_admins(client, admin_user, admin_user_plain, make_user):
    other_admin = make_user("admin3", role=UserRole.ADMIN, facility_name=FACILITY_A)
    # plain admin -> 403
    resp = client.delete(f"{USERS}/{other_admin.id}", headers=bearer(admin_user_plain))
    assert resp.status_code == 403
    # super admin -> 200
    resp = client.delete(f"{USERS}/{other_admin.id}", headers=bearer(admin_user))
    assert resp.status_code == 200
    # plain admin can still delete a clinician
    clin = make_user("clin-z", facility_name=FACILITY_A)
    assert client.delete(f"{USERS}/{clin.id}", headers=bearer(admin_user_plain)).status_code == 200


def test_delete_requires_admin(client, clinician_a, clinician_b):
    assert client.delete(f"{USERS}/{clinician_b.id}", headers=bearer(clinician_a)).status_code == 403


# ------------------------------------------------------------------ id card
def test_id_card_endpoint_admin_only(client, admin_user, clinician_a, make_user):
    ID_CARDS_DIR.mkdir(parents=True, exist_ok=True)
    fname = "11111111-2222-3333-4444-555555555555.png"
    (ID_CARDS_DIR / fname).write_bytes(b"\x89PNG\r\n\x1a\nfake")
    owner = make_user("with-card", facility_name=FACILITY_A, id_card_image_path=fname)

    url = f"{USERS}/{owner.id}/id-card"
    # unauthenticated
    assert client.get(url).status_code == 401
    # non-admin
    assert client.get(url, headers=bearer(clinician_a)).status_code == 403
    # admin
    resp = client.get(url, headers=bearer(admin_user))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.content.startswith(b"\x89PNG")
    assert "no-store" in resp.headers.get("cache-control", "")

    # user list exposes only the boolean
    listed = [u for u in client.get(USERS, headers=bearer(admin_user)).json() if u["username"] == "with-card"]
    assert listed and listed[0]["has_id_card"] is True


def test_id_card_404_when_missing(client, admin_user, make_user):
    no_card = make_user("no-card", facility_name=FACILITY_A)
    assert client.get(f"{USERS}/{no_card.id}/id-card", headers=bearer(admin_user)).status_code == 404

    dangling = make_user("dangling", facility_name=FACILITY_A, id_card_image_path="does-not-exist.png")
    assert client.get(f"{USERS}/{dangling.id}/id-card", headers=bearer(admin_user)).status_code == 404


def test_id_card_path_traversal_rejected(client, admin_user, make_user, tmp_path):
    # A file outside ID_CARDS_DIR must never be served, whatever the DB says.
    outside = ID_CARDS_DIR.parent / "secret.png"
    outside.write_bytes(b"top-secret")
    try:
        evil = make_user("evil", facility_name=FACILITY_A, id_card_image_path="../secret.png")
        resp = client.get(f"{USERS}/{evil.id}/id-card", headers=bearer(admin_user))
        assert resp.status_code == 404
        evil2 = make_user("evil2", facility_name=FACILITY_A, id_card_image_path=str(outside))
        resp = client.get(f"{USERS}/{evil2.id}/id-card", headers=bearer(admin_user))
        assert resp.status_code == 404
    finally:
        outside.unlink(missing_ok=True)


def test_id_card_legacy_relative_path_still_works(client, admin_user, make_user):
    # Older rows stored "id_cards/<name>"; the final component is used.
    ID_CARDS_DIR.mkdir(parents=True, exist_ok=True)
    fname = "legacy-card.jpg"
    (ID_CARDS_DIR / fname).write_bytes(b"\xff\xd8\xff")
    legacy = make_user("legacy", facility_name=FACILITY_A, id_card_image_path=f"id_cards/{fname}")
    resp = client.get(f"{USERS}/{legacy.id}/id-card", headers=bearer(admin_user))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/jpeg")
