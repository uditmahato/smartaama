# Access Control: Roles, Facilities, and the Referral Status Model

This document describes how SmartAama decides who may see and change what. It
supersedes the earlier permission-system implementation notes.

Everything below is **implemented** and covered by `backend/tests/` (see
`test_patients_access.py`, `test_referrals.py`, `test_admin.py`, `test_auth.py`,
`test_events_medical_data.py`, `test_review_fixes.py`). Code locations:
`backend/app/core/permissions.py` (roles), `backend/app/core/authz.py` (facility/object
rules), `backend/app/services/facility_service.py` (facility directory lookups),
`backend/app/services/referral_service.py` (status machines),
`backend/app/api/v1/endpoints/admin.py` (user management). When this document and the
code disagree, the code wins - fix the document.

## 1. Roles (implemented)

`app/models/user.py`:

| Role | Meaning | `require_clinician_or_admin` |
|---|---|---|
| `admin` | Platform administrator; unrestricted across facilities | yes |
| `clinician` | PHC / clinic staff | yes |
| `hospital` | Hospital staff | yes |
| `viewer` | Read-only user | no |

Dependencies in `app/core/permissions.py`:

- `require_any_authenticated` - any valid, active, approved user.
- `require_clinician_or_admin` - `{admin, clinician, hospital}`.
- `require_admin` - `admin` only.

Users must be `is_active`, `is_approved` and not soft-deleted to authenticate
(`get_current_user` in `app/core/security.py` rejects the rest with 401). New
registrations wait for admin approval (`/admin/users/pending`,
`/admin/users/{id}/approve|reject`).

**How roles are assigned.** Self-registration gives `hospital` to users who pick a
hospital facility and `clinician` to PHC users. Admins change roles with
`PATCH /admin/users/{id}/role {"role": "admin|clinician|hospital|viewer"}`; only a
super admin may grant `admin` or change an existing admin's role; nobody can change
their own role; every change is audited (`USER_ROLE_CHANGED`). The first admin is
created by `python -m app.scripts.create_super_admin` (super admin) or the dev-only
bootstrap endpoint.

## 2. Facility identity (implemented)

Facilities are rows of the unified `facilities` table (`id`, `name` unique, `kind`
`phc|hospital`; seeded by `python -m app.db.init_db`, listed by `GET /facilities`).
Facility-bearing rows carry a **foreign key** plus a name snapshot:

| Row | FK (authoritative) | Name snapshot (display / legacy) |
|---|---|---|
| `User` | `facility_id` | `facility_name`, `facility_type` |
| `Patient` | `registered_facility_id` | `registered_facility_name`, `registered_facility_type` |
| `Referral` | `from_facility_id`, `to_facility_id` | `from_facility`, `to_facility` |

Clients keep sending **names** (`from_facility`, `to_facility`, `registered_facility_name`);
the server resolves them (`facility_service.resolve_facility`: case-insensitive, trimmed,
exact — substring / `ILIKE %..%` matching is deliberately not used) and stores the id plus
the directory's canonical spelling. Unknown names are rejected: `400 Unknown facility: X`
on `POST /referrals` and on the admin variants of `POST/PATCH /patients`;
`POST /auth/register` / `bootstrap-admin` require an existing `facility_id` whose `kind`
equals the submitted `facility_type` (404 otherwise).

Matching rule (`authz.facility_ref_matches` / `facility_ref_filter`): **id first** —
`row.<facility_id> == user.facility_id`. The name snapshot is compared
(`authz.facility_matches`, case-insensitive trimmed exact) **only when the row's id is
NULL**: legacy rows written before Alembic revision `0002_facilities` whose name matched no
facility (the migration and every `init_db` run backfill ids for names that do match). A
row that has an id is never matched by name; a user with neither `facility_id` nor
`facility_name` has no facility scope.

## 3. Object-level authorization helpers (implemented in `app/core/authz.py`)

```python
facility_matches(a, b) -> bool                       # name compare (legacy fallback only)
facility_ref_matches(row_id, row_name, user) -> bool  # id-first, name iff row_id is NULL
facility_ref_filter(id_col, name_col, user)           # same rule as a SQL criterion
user_can_access_patient(db, user, patient) -> bool
get_accessible_patient_or_404(db, user, patient_id) -> Patient   # 404 missing, 403 no access
patient_access_filter(user)                                        # SQLAlchemy criterion for list queries
referral_party_filter(user) / referral_sender_filter(user) / referral_receiver_filter(user)
user_is_referral_party(user, referral) -> bool
require_referral_party(user, referral)        # 403 unless admin or from/to facility
require_referring_facility(user, referral)    # 403 unless admin or from_facility
require_receiving_facility(user, referral)    # 403 unless admin or to_facility
```

Access rule for a patient (non-admin):

- the patient's `registered_facility_id` equals the user's `facility_id` (name fallback only
  when the patient row's id is NULL), **or**
- any referral for the patient has the user's facility as sender or receiver (same
  id-first rule on `from_facility_id` / `to_facility_id`).

Admins pass every check. Users with neither `facility_id` nor `facility_name` can access no
patient-scoped resource unless they are admins.

## 4. Permission matrix

| Actor (non-admin) | View patient | Write clinical data | Create referral | Change `status` | Change `received_facility_status` |
|---|---|---|---|---|---|
| Registering facility, no referral yet | yes | yes (clinician/hospital) | yes | - | - |
| Referring facility (`from_facility`) | yes | yes (clinician/hospital) | yes | yes | no |
| Receiving facility (`to_facility`) | yes | yes (clinician/hospital) * | yes (onward referral) | no | yes |
| Unrelated facility | 403 | 403 | 403 | 403 | 403 |
| `viewer` role (any related facility) | yes | no | no | no | no |

\* The frontend hides the "Update Record" button for a facility that is *only* the
receiving side (`PatientProfile.tsx` `canEdit`), which is a UX convention; the
server-side rule is patient access + role. If a stricter "receiving facility cannot
edit vitals" rule is wanted it must be added on the server - do not rely on the UI.

## 5. Endpoint enforcement (implemented)

| Endpoint | Rule |
|---|---|
| `GET /patients`, `GET /patients/{id}` | scoped by `patient_access_filter` / `get_accessible_patient_or_404` |
| `POST /patients` | `require_clinician_or_admin`; `registered_facility_id` + name/type snapshot set from the actor's facility (400 if the actor has no facility, or its name is not in the directory, and is not an admin supplying `registered_facility_name`; an admin-supplied name must exist → 400 `Unknown facility: X`) |
| `PATCH /patients/{id}` | patient access + `require_clinician_or_admin`; only admins may change `registered_facility_name`, which must name an existing facility (400 otherwise) — the FK and type snapshot follow it |
| `/events*`, `/medical-data/*` | patient access; writes `require_clinician_or_admin` |
| `/ai-analysis/*`, `/ai/risk` | patient access; reads `require_any_authenticated`, generate/regenerate/delete `require_clinician_or_admin` |
| `POST /referrals` | patient access; `from_facility` / `to_facility` must resolve to facilities (400 `Unknown facility: X`); for non-admins `from_facility` must be the caller's own facility, compared by id (400); the row stores both ids and canonical names |
| `GET/PATCH /referrals/{id}` | `require_referral_party` |
| `POST /referrals/{id}/status` | referring facility or admin |
| `POST /referrals/{id}/received-status` | receiving facility or admin; when the new value is also a valid next step for the referring-side `status` (submitted→received, received→closed, draft/submitted→cancelled) it is mirrored into `status` and a `status` history row is written |
| `GET /referrals` | non-admins always constrained to referrals where their facility is `from` **or** `to` (single query; id-first, name only for NULL-id legacy rows); filters `patient_id`, `status`, `received_status`, `direction=incoming|outgoing`, `from_facility`, `to_facility` (exact name, case-insensitive), `limit`, `offset` |
| `GET /referrals/{id}/history` | `require_referral_party` |
| `/admin/*` | `require_admin`; delete is a soft delete; approve / reject / delete / role-change of an **admin-role** user and granting `admin` require `is_super_admin`; self-delete, self-reject and self-role-change are rejected (400) |
| `POST /auth/register`, `POST /auth/bootstrap-admin` | `facility_id` must exist in `facilities` with `kind == facility_type` (404 `Facility not found`); the user row stores the id and the directory's name/kind |
| `GET /facilities?kind=phc\|hospital&q=` | public; items `{id, name, kind}` from the unified table |

Frontend checks (`canEdit`, hidden buttons, filter chips) are UX only. Every rule above
is enforced server-side and returns 403 (or 404 when the object does not exist).

## 6. Referral status model (implemented)

`app/models/referral.py`, enum `ReferralStatus = draft | submitted | received | closed | cancelled`.

A referral carries **two** independent status columns:

| Column | Owned by | Purpose |
|---|---|---|
| `status` | referring facility (`from_facility`) | lifecycle of the referral itself |
| `received_facility_status` | receiving facility (`to_facility`) | the receiver's acknowledgement / outcome; `NULL` until they act |

### `status` state machine (`referral_service._ALLOWED_TRANSITIONS`)

```
draft ──► submitted ──► received ──► closed
  │           │
  └► cancelled └► cancelled
closed, cancelled: terminal
```

Endpoint: `POST /referrals/{id}/status` `{ "status": "...", "note": "optional" }`.
Timestamps `submitted_at`, `received_at`, `closed_at` are set on the corresponding
transition.

### `received_facility_status` transitions (implemented)

```
NULL ──► received ──► closed
  │          │
  └► cancelled └► cancelled
closed, cancelled: terminal
```

Endpoint: `POST /referrals/{id}/received-status`
`{ "received_facility_status": "received|closed|cancelled", "note": "optional" }`.
The frontend labels these "Admitted Here", "Closed Case", "Referred Elsewhere".

Because the receiving facility is the authority on arrival and case closure, a
received-status change is **mirrored into the referring-side `status`** whenever it is a
valid `status` transition (`submitted → received`, `received → closed`,
`draft|submitted → cancelled`). The sender therefore sees a truthful lifecycle without a
second manual step, and the Dashboard "Closed Case" filter (`status=closed`) matches
cases the receiver closed. The sender can still drive `status` itself via
`POST /referrals/{id}/status` (e.g. cancel while `submitted`, close after `received`).

### Notes and history

- The `referral_status_history` table
  (`id, referral_id, kind ∈ {created,status,received_status,decision}, from_status,
  to_status, note, actor_user_id, actor_name, created_at`) records every change and is
  exposed via `GET /referrals/{id}/history` (parties/admin only). Notes passed with a
  status or received-status change are stored there.
- `clinician_note` is the clinician's own free-text note (set on create or via
  `PATCH /referrals/{id}`); status changes **no longer** append text to it. Rows created
  before this change may still contain older `[date] Status: ...` lines - they are just
  text.
- Every change is also written to `audit_logs`.

### Dashboard filter mapping (implemented)

| Dashboard chip | Query |
|---|---|
| Referred to Here | `direction=incoming` |
| Referred from Here | `direction=outgoing` |
| Admitted Case | `direction=incoming&received_status=received` |
| Closed Case | `status=closed` |

`direction` is relative to the caller's facility.

## 7. Authentication and admin hardening (implemented)

### Tokens
- `POST /auth/login` returns `{access_token, token_type, expires_in, refresh_token}`.
  - **Access token**: stateless HS256 JWT, lifetime `ACCESS_TOKEN_EXPIRE_MINUTES` (default
    **30**). It is *not* individually revocable — it stays usable until it expires — but
    `get_current_user` re-reads the user row on every request, so a rejected / soft-deleted /
    deactivated / unapproved user is refused (401) immediately regardless of the token.
    Authorization always uses the role stored in the DB, never the `role` claim.
  - **Refresh token**: opaque 32-byte urlsafe secret (`secrets.token_urlsafe(32)`), lifetime
    `REFRESH_TOKEN_EXPIRE_DAYS` (default **14**). Only its SHA-256 digest is stored
    (`refresh_tokens.token_hash`, unique) together with `user_id`, `expires_at`, `created_at`,
    `revoked_at`, `replaced_by_id`, `user_agent`, `ip`.
- `POST /auth/refresh {refresh_token}` → new `{access_token, …, refresh_token}`. **Rotation**:
  the presented token is revoked and linked to its successor (`replaced_by_id`); every token is
  single-use. 401 when the token is unknown, expired (it is then also retired), revoked, or its
  user is no longer login-eligible (rejected, soft-deleted, inactive, unapproved).
  **Reuse detection**: presenting a token that was *already* revoked/rotated is treated as
  theft — every refresh token of that user is revoked (the legitimate session must sign in again)
  and `REFRESH_TOKEN_REUSE_DETECTED` is written to `audit_logs`.
- `POST /auth/logout {refresh_token}` → 204, idempotent (unknown / already-revoked → still 204).
  Revokes that refresh token and audits `USER_LOGOUT`; the client drops both tokens locally.
  No Bearer token is needed — possession of the refresh token is the credential.
- Admin actions that revoke **all** refresh tokens of the target
  (`revoke_all_refresh_tokens(db, user_id)` in `app/core/security.py`): reject, soft-delete,
  and any role change (`PATCH /admin/users/{id}/role`). The audit `details` carry
  `refresh_tokens_revoked`.
- Frontend (`frontend/src/services/api.ts`): both tokens in `localStorage` (XSS trade-off
  documented in the file; httpOnly cookies are the hardening path). On a 401 from any endpoint
  other than `/auth/login|refresh|logout` the axios interceptor performs **one** single-flight
  refresh (concurrent 401s share it — a second parallel refresh would look like a replay), retries
  the original request once, otherwise clears both tokens + cached user and redirects to
  `/login`. Logout posts `/auth/logout` (best effort) and clears.

### Rate limiting (database-backed, cross-process)
- `/auth/login`, `/auth/register` and `/auth/refresh` share a per-client-IP sliding-window budget
  (`RATE_LIMIT_MAX_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS`, defaults 10 / 60 s). Client IP =
  first `X-Forwarded-For` hop, else the socket peer.
- The hit log is the table `auth_rate_limit_hits(key, hit_at)`: every guarded request inserts a
  row, then counts the key's rows inside the window; over budget → `429` with `Retry-After`
  (seconds until enough hits age out; refused requests count too). Because the state is in the
  application database the limit is **shared by every uvicorn worker / process / instance**
  (it is a brute-force brake, not an exact counter: truly concurrent requests at the boundary may
  all be admitted once, the next one is refused). Old rows are pruned
  opportunistically (every 50th check per process and whenever a key is over budget).
- `RATE_LIMIT_DISABLED=true` makes the dependency a no-op with no DB access (tests, e2e).

### Registrations
- Registration password minimum length 10 (422 on failure).
- Rejecting a registration (`PATCH /admin/users/{id}/reject`) sets `users.rejected_at/rejected_by`,
  makes the account unapproved + inactive and revokes its refresh tokens. Rejected users are
  excluded from `GET /admin/users/pending` and listed by **`GET /admin/users/rejected`**
  (admin only, `List[UserOut]`, newest rejection first); `UserOut` carries `rejected_at`.
  Approving (`PATCH …/approve`) clears the rejection and re-admits the account (audited with
  `was_rejected`). Soft-deleted users appear in neither list.
- `/auth/bootstrap-admin` only when `ENV=dev` **and** `BOOTSTRAP_TOKEN` is non-empty
  and matches the `X-Bootstrap-Token` header (constant-time compare).
- User-returning endpoints serialise `UserOut`; `password_hash` and
  `id_card_image_path` are never returned. ID cards are served only to admins via
  `GET /admin/users/{id}/id-card`.
- `python -m app.scripts.create_super_admin` requires
  `SUPER_ADMIN_USERNAME / SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD` (no defaults).

## 8. Known limitations / future work

- The facility directory is seed data: there is no admin API to add facilities or to move a
  user to another facility (edit the `facilities` table / user row; `init_db` backfills ids
  from names). Legacy rows whose name matched no facility keep a NULL id and are matched by
  name only.
- No facility hierarchy (district / province roll-up).
- Access JWTs are not revocable individually (bounded by `ACCESS_TOKEN_EXPIRE_MINUTES`); the
  refresh token is the revocable credential. Tokens are kept in `localStorage` on the client
  (httpOnly cookies would harden this).
- The rate limiter trusts the first `X-Forwarded-For` hop; put a proxy that sets it in front.
- No notifications on referral changes.
