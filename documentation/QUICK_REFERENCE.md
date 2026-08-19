# Developer Quick Reference

One-page cheat sheet for working on SmartAama. For the "why", see `ARCHITECTURE.md`;
for authorization rules see `ACCESS_CONTROL.md`.

## Ports and URLs

| What | Value |
|---|---|
| Backend (uvicorn) | `http://localhost:8000` |
| API prefix | `/api/v1` (`app/main.py`) |
| OpenAPI docs | `http://localhost:8000/docs` |
| Frontend (Vite dev server) | `http://localhost:5173` (`frontend/vite.config.ts`) |

## Run locally

```powershell
# Backend (Windows; venv at backend\.venv)
cd backend
copy .env.example .env            # then edit: SECRET_KEY (>=32 chars), DATABASE_URL, BOOTSTRAP_TOKEN
.venv\Scripts\python.exe -m app.db.init_db          # alembic upgrade head (+ stamp legacy DBs) + seed facilities
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
# or: .\start_backend.ps1 / start_backend.bat

# Frontend (npm, Node 22)
cd frontend
npm install
npm run dev                       # http://localhost:5173
npm run typecheck                 # tsc --noEmit
npm run build                     # tsc --noEmit && vite build
```

Database schema management is **Alembic** (`backend/alembic.ini`, `backend/alembic/`);
`python -m app.db.init_db` wraps it (stamps a pre-Alembic database at `0001_baseline`,
runs `upgrade head`, seeds the facility directory, backfills facility ids). Direct commands
(run from `backend/`, `DATABASE_URL` + `SECRET_KEY` set / in `.env`):

```powershell
.venv\Scripts\python.exe -m alembic upgrade head            # apply pending migrations
.venv\Scripts\python.exe -m alembic current                 # show the DB's revision (head: 0003_auth_tokens_rate_limit)
.venv\Scripts\python.exe -m alembic check                   # fail if models and DB schema differ
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "add x" --rev-id 0004_add_x   # then hand-check portability
.venv\Scripts\python.exe -m alembic downgrade 0001_baseline
```

Migrations must run on PostgreSQL **and** SQLite: use `sa.Uuid()`,
`sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")`,
`sa.Enum(..., name=...)` and `op.batch_alter_table(...)` for ALTERs; keep revision ids
≤ 32 characters.

## Environment variables

Backend (`backend/.env`, all declared in `app/core/config.py`):

| Var | Notes |
|---|---|
| `ENV` | `dev` \| `staging` \| `prod` |
| `SECRET_KEY` | JWT signing secret, **>= 32 chars** (not `JWT_SECRET_KEY`) |
| `JWT_ALGORITHM` | default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | access-token lifetime, default 30 (the frontend refreshes silently) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | refresh-token lifetime, default 14 (rotated on every refresh) |
| `DATABASE_URL` | e.g. `postgresql+psycopg2://user:pass@localhost:5432/smartaama` (PostgreSQL in prod; tests use SQLite) |
| `BOOTSTRAP_TOKEN` | required for `/auth/bootstrap-admin`; endpoint is disabled unless `ENV=dev` and this is set |
| `AUTO_INIT_DB` | dev only: run `init_db()` on startup |
| `CORS_ORIGINS` | comma-separated; default includes `http://localhost:5173` |
| `MAX_ID_CARD_SIZE_MB` | default 5 |
| `RATE_LIMIT_DISABLED` / `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | auth rate limiting for login/register/refresh — DB-backed sliding window per client IP, shared across workers |

Frontend (`frontend/.env`):

| Var | Notes |
|---|---|
| `VITE_API_BASE_URL` | e.g. `http://localhost:8000/api/v1` (default in `src/services/api.ts`) |

Never commit real secrets. Use obvious placeholders (`change-me`) in examples.

## Roles

`admin`, `clinician`, `hospital`, `viewer` (`app/models/user.py`).
`require_clinician_or_admin` = `{admin, clinician, hospital}`; `viewer` is read-only.
Users must be approved by an admin before they can log in.

## API map (prefix `/api/v1`)

| Area | Routes |
|---|---|
| Auth | `POST /auth/login` (form: `username`, `password` → access + refresh token) · `POST /auth/refresh` (`{refresh_token}`, rotates) · `POST /auth/logout` (`{refresh_token}`, 204) · `POST /auth/register` (multipart, optional ID card) · `GET /auth/me` · `POST /auth/bootstrap-admin` (dev only) |
| Admin | `GET /admin/users` · `GET /admin/users/pending` · `GET /admin/users/rejected` · `PATCH /admin/users/{id}/approve|reject` · `PATCH /admin/users/{id}/role` · `DELETE /admin/users/{id}` (soft) · `GET /admin/users/{id}/id-card` |
| Patients | `POST /patients` · `GET /patients` · `GET /patients/{id}` · `PATCH /patients/{id}` |
| Clinical events | `POST /events` · `POST /events/batch` · `GET /events?patient_id=` |
| Medical schema | `GET /schema/sections[?category=&updates_only=]` · `GET /schema/sections/{key}` · `GET /schema/sections/{key}/fields` |
| Medical data | `POST /medical-data/patients/{id}/sections/{key}` · `.../latest` · `.../history?limit=` · `POST /medical-data/patients/{id}/bulk-entry` |
| Referrals | `POST /referrals` · `GET /referrals` · `GET/PATCH /referrals/{id}` · `POST /referrals/{id}/status` · `POST /referrals/{id}/received-status` · `GET /referrals/{id}/history` |
| Advisory (rule-based) | `GET /ai-analysis/patients/{id}/analysis` · `POST /ai-analysis/generate` · `GET /ai-analysis/patients/{id}/status` · `DELETE /ai-analysis/patients/{id}` · `POST /ai/risk` |
| Reference data | `GET /locations/provinces|districts|municipalities|wards` · `GET /facilities?kind=phc|hospital&q=` (`{id, name, kind}`) |

## Referral status cheat sheet

Two columns, two owners (`ACCESS_CONTROL.md` §6):

```
status                     (referring facility)   draft -> submitted -> received -> closed ; cancelled from draft/submitted
received_facility_status   (receiving facility)   NULL -> received -> closed ; cancelled from NULL/received
```

`GET /referrals` filters: `patient_id`, `status`, `received_status`,
`direction=incoming|outgoing`, `from_facility`, `to_facility`, `limit`, `offset`.
Non-admins only ever see referrals where their facility is sender or receiver.

Dashboard chips: "Referred to Here" = `direction=incoming`; "Referred from Here" =
`direction=outgoing`; "Admitted Case" = `direction=incoming&received_status=received`;
"Closed Case" = `status=closed`.

## Common backend tasks

Guard an endpoint by patient access:

```python
from app.core.authz import get_accessible_patient_or_404
from app.core.permissions import require_clinician_or_admin

@router.post("/patients/{patient_id}/something")
def do_it(patient_id: UUID, db: Session = Depends(get_db),
          user: User = Depends(require_clinician_or_admin)):
    patient = get_accessible_patient_or_404(db, user, patient_id)   # 404 / 403
    ...
```

Scope a list query:

```python
from app.core.authz import patient_access_filter
stmt = select(Patient).where(patient_access_filter(user))
```

Guard a referral action:

```python
from app.core.authz import require_referral_party, require_referring_facility, require_receiving_facility
require_referral_party(user, referral)        # read / PATCH
require_referring_facility(user, referral)    # POST /status
require_receiving_facility(user, referral)    # POST /received-status
```

Resolve a facility name a client sent (ids are authoritative, names are display snapshots):

```python
from app.services.facility_service import resolve_facility, resolve_user_facility
facility = resolve_facility(db, name=payload.to_facility)          # None -> 400 "Unknown facility: X"
mine = resolve_user_facility(db, current_user)                     # the caller's own facility row
row.to_facility_id, row.to_facility = facility.id, facility.name
```

Add a schema change: edit the model, then `alembic revision --autogenerate -m "..." --rev-id 000N_slug`,
hand-check the file (portable types, `batch_alter_table`), `alembic upgrade head`, and run
`pytest tests/test_migrations.py` (asserts `upgrade head` == models on SQLite).

Add a clinical field: edit `app/models/medical_schema.py` (see `MEDICAL_SCHEMA.md`).

Invalidate the advisory analysis after a clinical write:
`from app.services.ai_update_service import mark_ai_analysis_for_update; mark_ai_analysis_for_update(db, patient_id)`.

## Common frontend tasks

- Use the shared axios instance `src/services/api.ts` (adds the bearer token; a 401
  clears the token and redirects to `/login`).
- Handle 403 with a friendly "no access" state - patient/referral/advisory routes can
  now return it.
- Show ID cards by fetching `/admin/users/{id}/id-card` with `responseType: "blob"` and
  an object URL; there is no static uploads URL.
- Advisory cards (`AIPatientSummary.tsx`, `AIReferralRecommendation.tsx`) present a
  rule-based advisory; do not label them as GPT/LLM output.

## Tests

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q          # SQLite by default; set TEST_DATABASE_URL for PostgreSQL
cd ..\frontend
npm run typecheck ; npm run build
```

See `TESTING_GUIDE.md` for manual QA scenarios.

## Debugging checklist

- 401 everywhere: token missing/expired, or user not yet approved.
- 403 on a patient: caller's `facility_id` equals neither `registered_facility_id` nor any
  referral `from_facility_id`/`to_facility_id` for that patient (names are only compared
  for legacy rows whose id is NULL).
- Dashboard empty for a hospital user: check the user's `facility_id` equals the
  referral's `to_facility_id` (`GET /auth/me` vs `GET /referrals/{id}`); legacy rows with
  a NULL id match on `to_facility` name (whitespace / spelling).
- 400 `Unknown facility: X` on referral/patient writes: the name is not in `GET /facilities`
  (case-insensitive, trimmed); seed it via `python -m app.db.init_db` or fix the spelling.
- `alembic check` reports drift / tests in `test_migrations.py` fail: a model changed
  without a migration — generate one (`alembic revision --autogenerate ...`).
- Backend refuses to start: `SECRET_KEY` shorter than 32 chars or `DATABASE_URL` unset.
- CORS error in browser: `CORS_ORIGINS` must include `http://localhost:5173`.
