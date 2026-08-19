# backend/tests/conftest.py
"""
Shared pytest fixtures.

- Environment is set BEFORE `app` is imported (SECRET_KEY, DATABASE_URL, ENV=dev, ...).
- Default DB: in-memory SQLite (StaticPool, see app.db.session). Set TEST_DATABASE_URL to run
  the same suite against PostgreSQL.
- Every test starts from an empty schema (drop_all + create_all — faster than running the Alembic
  chain per test; migration parity has its own tests in test_migrations.py) so tests are independent.
- The three test facilities (PHC A, PHC B, Hospital X) are seeded into the unified `facilities`
  table for every test; `make_user(facility_name=...)` links users to them by FK.
- Uploads go to a throw-away temp directory (UPLOADS_DIR).
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

import pytest

# --------------------------------------------------------------------------- env (before app import)
_UPLOADS_TMP = tempfile.mkdtemp(prefix="smartaama-test-uploads-")

os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-definitely-longer-than-32-chars")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or "sqlite://"
os.environ["ENV"] = "dev"
os.environ["AUTO_INIT_DB"] = "false"
os.environ["BOOTSTRAP_TOKEN"] = "test-bootstrap-token"
os.environ["RATE_LIMIT_DISABLED"] = "true"
os.environ["UPLOADS_DIR"] = _UPLOADS_TMP
os.environ["MAX_ID_CARD_SIZE_MB"] = "1"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.db.base import Base  # noqa: E402  (registers all models)
from app.db.session import engine, get_db  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.models.facility import Facility  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services.facility_service import normalize_name  # noqa: E402
from app.main import app  # noqa: E402

TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

# Test-only credentials (NOT secrets): every account below is created inside the throw-away
# test database of a single pytest run and never exists anywhere else. Kept in one place so
# secret scanners see named constants rather than literal username/password pairs.
TEST_PASSWORD = "Str0ngPassw0rd!"
WRONG_PASSWORD = "definitely-not-the-password"
REGISTER_PASSWORD = "Register-Test-Passw0rd"
BOOTSTRAP_PASSWORD = "Bootstrap-Test-Passw0rd"
TOO_SHORT_PASSWORD = "short"
# bcrypt is slow; hash the shared test password once.
_TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)

FACILITY_A = "PHC A"
FACILITY_B = "PHC B"
HOSPITAL_X = "Hospital X"


# --------------------------------------------------------------------------- schema per test
@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.core.rate_limit import auth_rate_limiter

    auth_rate_limiter.reset()
    yield
    Base.metadata.drop_all(bind=engine)


# --------------------------------------------------------------------------- facilities
def facility_kind_for(name: str, facility_type: Optional[str] = None) -> str:
    """Test convention: names starting with 'PHC' are PHCs, everything else is a hospital."""
    return facility_type or ("phc" if name.strip().upper().startswith("PHC") else "hospital")


def ensure_facility(db: Session, name: str, kind: Optional[str] = None) -> Facility:
    """Get-or-create a row of the unified facility directory (case-insensitive name match)."""
    key = normalize_name(name)
    existing = db.execute(select(Facility).where(func.lower(func.trim(Facility.name)) == key)).scalars().first()
    if existing is not None:
        return existing
    facility = Facility(name=name.strip(), kind=facility_kind_for(name, kind))
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility


@pytest.fixture(autouse=True)
def seeded_facilities(_fresh_schema) -> Dict[str, uuid.UUID]:
    """The three test facilities, present in every test. Maps name -> facility id."""
    with TestingSessionLocal() as session:
        ids = {
            name: ensure_facility(session, name, kind).id
            for name, kind in ((FACILITY_A, "phc"), (FACILITY_B, "phc"), (HOSPITAL_X, "hospital"))
        }
    return ids


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db() -> Session:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# --------------------------------------------------------------------------- users
@pytest.fixture()
def make_user(db: Session) -> Callable[..., User]:
    def _make(
        username: Optional[str] = None,
        *,
        role: UserRole = UserRole.CLINICIAN,
        facility_name: Optional[str] = None,
        facility_type: Optional[str] = None,
        is_approved: bool = True,
        is_active: bool = True,
        is_super_admin: bool = False,
        password: str = TEST_PASSWORD,
        id_card_image_path: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> User:
        username = username or f"user-{uuid.uuid4().hex[:8]}"
        # A facility name always resolves to a directory row (created on demand) and the user
        # is linked to it by FK; the name is stored exactly as given (display snapshot).
        facility = ensure_facility(db, facility_name, facility_type) if facility_name and facility_name.strip() else None
        user = User(
            username=username,
            email=f"{username}@example.test",
            full_name=full_name or username,
            role=role,
            facility_id=facility.id if facility else None,
            facility_name=facility_name,
            facility_type=(facility.kind if facility else None),
            password_hash=_TEST_PASSWORD_HASH if password == TEST_PASSWORD else hash_password(password),
            is_active=is_active,
            is_approved=is_approved,
            is_super_admin=is_super_admin,
            approved_at=datetime.now(timezone.utc) if is_approved else None,
            id_card_image_path=id_card_image_path,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture()
def admin_user(make_user) -> User:
    """Super admin without a facility (unrestricted)."""
    return make_user("admin", role=UserRole.ADMIN, is_super_admin=True)


@pytest.fixture()
def admin_user_plain(make_user) -> User:
    """Admin that is NOT a super admin, at Hospital X."""
    return make_user("admin2", role=UserRole.ADMIN, facility_name=HOSPITAL_X, facility_type="hospital")


@pytest.fixture()
def clinician_a(make_user) -> User:
    return make_user("clin-a", role=UserRole.CLINICIAN, facility_name=FACILITY_A, facility_type="phc")


@pytest.fixture()
def clinician_b(make_user) -> User:
    return make_user("clin-b", role=UserRole.CLINICIAN, facility_name=FACILITY_B, facility_type="phc")


@pytest.fixture()
def hospital_x(make_user) -> User:
    return make_user("hosp-x", role=UserRole.HOSPITAL, facility_name=HOSPITAL_X, facility_type="hospital")


@pytest.fixture()
def viewer_a(make_user) -> User:
    return make_user("viewer-a", role=UserRole.VIEWER, facility_name=FACILITY_A, facility_type="phc")


@pytest.fixture()
def pending_user(make_user) -> User:
    return make_user("pending", role=UserRole.CLINICIAN, facility_name=FACILITY_A, is_approved=False, is_active=False)


# --------------------------------------------------------------------------- auth helpers
def bearer(user: User) -> Dict[str, str]:
    """Authorization header with a freshly minted JWT for `user` (bypasses /auth/login)."""
    return {"Authorization": f"Bearer {create_access_token(subject_user=user)}"}


@pytest.fixture()
def auth() -> Callable[[User], Dict[str, str]]:
    return bearer


@pytest.fixture()
def login(client: TestClient) -> Callable[[str, str], Dict[str, str]]:
    def _login(username: str, password: str = TEST_PASSWORD) -> Dict[str, str]:
        resp = client.post("/api/v1/auth/login", data={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login


# --------------------------------------------------------------------------- patients
def create_patient(client: TestClient, headers: Dict[str, str], **overrides) -> dict:
    payload = {
        "first_name": "Sita",
        "last_name": "Sharma",
        "age_in_years": 27,
        "sex": "female",
        "province": "Bagmati",
        "district": "Kathmandu",
        "municipality": "Kathmandu",
    }
    payload.update(overrides)
    resp = client.post("/api/v1/patients", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def patient_a(client, clinician_a) -> dict:
    """Patient registered by facility A."""
    return create_patient(client, bearer(clinician_a))
