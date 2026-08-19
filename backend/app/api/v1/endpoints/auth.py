# backend/app/api/v1/endpoints/auth.py

from __future__ import annotations

import hmac
import uuid
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import auth_rate_limit, client_ip
from app.core.security import (
    RefreshTokenReuseError,
    access_token_expires_in,
    create_access_token,
    get_current_user,
    hash_password,
    issue_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    user_is_login_eligible,
    verify_password,
)
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.auth import LogoutRequest, RefreshRequest, TokenResponse
from app.schemas.user import RegisterResponse, UserOut
from app.services.facility_service import resolve_facility
from app.settings import ID_CARDS_DIR

router = APIRouter()

PASSWORD_MIN_LENGTH = 10

# ID-card upload policy
ALLOWED_ID_CARD_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
_READ_CHUNK = 64 * 1024


class BootstrapAdminPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)
    full_name: Optional[str] = None
    facility_kind: Literal["phc", "hospital"]
    facility_id: UUID


def _token_response(db: Session, *, user: User, request: Request) -> TokenResponse:
    """Mint an access JWT + a fresh refresh token for `user` (caller commits)."""
    refresh_secret, _ = issue_refresh_token(
        db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip=client_ip(request),
    )
    return TokenResponse(
        access_token=create_access_token(subject_user=user),
        expires_in=access_token_expires_in(),
        refresh_token=refresh_secret,
    )


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2-compatible login endpoint (form fields `username`, `password`).
    Returns `{access_token, token_type, expires_in, refresh_token}`: the access token is a
    short-lived JWT, the refresh token an opaque single-use secret for POST /auth/refresh.
    """
    stmt = select(User).where(User.username == form_data.username)
    user = db.execute(stmt).scalar_one_or_none()

    # Same generic error for unknown user / wrong password / soft-deleted.
    if not user or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Only a correctly-authenticated user learns that the account is pending/inactive.
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not approved yet. Please contact the administrator.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Please contact the administrator.",
        )

    if not user_is_login_eligible(user):  # defensive; covered by the checks above
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    tokens = _token_response(db, user=user, request=request)

    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="USER_LOGIN",
            entity_type="user",
            entity_id=user.id,
            ip_address=client_ip(request),
            user_agent=request.headers.get("user-agent"),
            details={"username": user.username},
        )
    )
    db.commit()

    return tokens


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
def refresh(
    request: Request,
    payload: RefreshRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Exchange a refresh token for a new access + refresh pair (rotation: the presented token is
    revoked and linked to its successor). 401 when the token is unknown, expired, revoked, or its
    user may no longer sign in (rejected, soft-deleted, inactive, unapproved). Presenting a token
    that was already rotated/revoked is treated as reuse: EVERY refresh token of that user is
    revoked (the legitimate session must sign in again) and the event is audited.
    """
    try:
        user, new_secret, new_row = rotate_refresh_token(
            db,
            secret=payload.refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip=client_ip(request),
        )
    except RefreshTokenReuseError as exc:
        # rotate_refresh_token already revoked + committed; record the incident separately.
        db.add(
            AuditLog(
                actor_user_id=exc.user_id,
                action="REFRESH_TOKEN_REUSE_DETECTED",
                entity_type="user",
                entity_id=exc.user_id,
                ip_address=client_ip(request),
                user_agent=request.headers.get("user-agent"),
                details={"effect": "all refresh tokens revoked"},
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    db.commit()
    return TokenResponse(
        access_token=create_access_token(subject_user=user),
        expires_in=access_token_expires_in(),
        refresh_token=new_secret,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(
    request: Request,
    payload: LogoutRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Revoke the presented refresh token (204, idempotent: unknown / already-revoked tokens are a
    no-op). The current access JWT is stateless and stays valid until it expires — clients must
    drop it locally. No Bearer token is required: possession of the refresh token is the credential.
    """
    revoked = revoke_refresh_token(db, payload.refresh_token)
    if revoked is not None:
        db.add(
            AuditLog(
                actor_user_id=revoked.user_id,
                action="USER_LOGOUT",
                entity_type="user",
                entity_id=revoked.user_id,
                ip_address=client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bootstrap-admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(
    payload: BootstrapAdminPayload = Body(...),
    x_bootstrap_token: Optional[str] = Header(default=None, alias="X-Bootstrap-Token"),
    db: Session = Depends(get_db),
):
    """
    DEV-ONLY endpoint to create the first (super) admin user.
    Refused unless ENV=dev AND BOOTSTRAP_TOKEN is configured (non-empty) AND the
    X-Bootstrap-Token header matches it (constant-time comparison).
    """
    if settings.ENV != "dev" or not settings.BOOTSTRAP_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bootstrap disabled")

    provided = (x_bootstrap_token or "").strip()
    if not provided or not hmac.compare_digest(provided.encode("utf-8"), settings.BOOTSTRAP_TOKEN.encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bootstrap token")

    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username and password required")

    exists = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="User already exists")

    # The facility must exist in the unified directory with the requested kind.
    facility = resolve_facility(db, facility_id=payload.facility_id, kind=payload.facility_kind)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    user = User(
        username=username,
        email=username,
        full_name=payload.full_name.strip() if isinstance(payload.full_name, str) and payload.full_name.strip() else None,
        role=UserRole.ADMIN,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_approved=True,
        facility_type=facility.kind,
        facility_id=facility.id,
        facility_name=facility.name,
        is_super_admin=True,
    )
    db.add(user)
    db.flush()

    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="BOOTSTRAP_ADMIN_CREATED",
            entity_type="user",
            entity_id=user.id,
            details={
                "username": user.username,
                "role": user.role.value,
                "facility_type": user.facility_type,
                "facility_id": str(user.facility_id) if user.facility_id else None,
                "facility_name": user.facility_name,
            },
        )
    )

    db.commit()
    db.refresh(user)
    return user


def _validate_and_store_id_card(upload: UploadFile) -> str:
    """
    Validate an uploaded ID-card image and store it as <uuid4>.<ext> under ID_CARDS_DIR.
    Returns the stored filename (relative to ID_CARDS_DIR). Never uses the client filename.
    """
    original = upload.filename or ""
    ext = Path(original).suffix.lower().lstrip(".")
    if ext not in ALLOWED_ID_CARD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ID card must be an image file ({', '.join(sorted(ALLOWED_ID_CARD_EXTENSIONS))})",
        )
    content_type = (upload.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID card must be an image (content-type image/*)")

    max_bytes = settings.MAX_ID_CARD_SIZE_MB * 1024 * 1024
    ID_CARDS_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}.{ext}"
    dest = ID_CARDS_DIR / stored_name

    written = 0
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = upload.file.read(_READ_CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,  # Content Too Large
                        detail=f"ID card image exceeds {settings.MAX_ID_CARD_SIZE_MB} MB",
                    )
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not store ID card image")
    finally:
        try:
            upload.file.close()
        except Exception:
            pass

    if written == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID card image is empty")

    return stored_name


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
def register(
    email: str = Form(..., min_length=3, max_length=255),
    password: str = Form(..., min_length=PASSWORD_MIN_LENGTH, max_length=128),
    full_name: str = Form(..., min_length=1, max_length=200),
    phone_number: str = Form(..., min_length=1, max_length=20),
    nmc_number: str = Form(..., min_length=1, max_length=64),
    working_hospital: str = Form(..., min_length=1, max_length=255),
    facility_type: Literal["phc", "hospital"] = Form(...),
    facility_id: UUID = Form(...),
    id_card_image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    """
    Self-registration (multipart form). The account is created inactive/unapproved and must be
    approved by an admin. Optional `id_card_image` (jpg/jpeg/png/webp, image/*, <= MAX_ID_CARD_SIZE_MB).
    """
    email_norm = email.strip()
    if not email_norm:
        raise HTTPException(status_code=422, detail="email is required")

    exists = db.execute(
        select(User).where((User.email == email_norm) | (User.username == email_norm))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="User already exists")

    # `facility_id` must exist in the unified directory with kind == facility_type (404 otherwise).
    facility = resolve_facility(db, facility_id=facility_id, kind=facility_type)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Validate/store the upload BEFORE touching the DB so a bad file never leaves a half-created user.
    stored_id_card: Optional[str] = None
    if id_card_image is not None and (id_card_image.filename or "").strip():
        stored_id_card = _validate_and_store_id_card(id_card_image)

    user = User(
        username=email_norm,
        email=email_norm,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        phone_number=phone_number.strip(),
        nmc_number=nmc_number.strip(),
        working_hospital=working_hospital.strip(),
        facility_type=facility.kind,
        facility_id=facility.id,
        facility_name=facility.name,
        # Role follows the facility type: hospital staff get the `hospital` role, PHC staff `clinician`.
        # Both may write clinical data; admins can re-assign roles via PATCH /admin/users/{id}/role.
        role=UserRole.HOSPITAL if facility_type == "hospital" else UserRole.CLINICIAN,
        is_active=False,
        is_approved=False,
        id_card_image_path=stored_id_card,
    )

    db.add(user)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="USER_REGISTERED",
            entity_type="user",
            entity_id=user.id,
            details={"username": user.username, "facility_name": user.facility_name, "has_id_card": bool(stored_id_card)},
        )
    )
    db.commit()
    db.refresh(user)

    return RegisterResponse(detail="Registration successful. Awaiting approval", user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """
    Return current authenticated user profile.
    """
    return current_user
