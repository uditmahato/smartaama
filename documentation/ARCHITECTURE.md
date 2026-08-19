# SmartAama — Architecture Overview

This document describes the system **as implemented** in this repository. Where a
design choice was made deliberately (and could reasonably have gone another way), the
reason is stated so it is not re-litigated by accident. When this document and the
code disagree, the code wins — fix the document.

## 1. Components

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Browser — React 18 + TypeScript + Vite 5 + MUI 5 (frontend/)             │
│  Home · Login · Signup · Dashboard (referral inbox) · Patients (search /   │
│  create / profile / edit / update-record / referral) · Admin (users)      │
│  axios client (services/api.ts) — JWT bearer, 401 → refresh once → /login │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  HTTPS/HTTP JSON, /api/v1/*, CORS allowlist
┌───────────────────────────────┴──────────────────────────────────────────┐
│  FastAPI backend (backend/app)                                            │
│  api/v1/endpoints: auth · admin · patients · clinical_events ·            │
│    medical_data · medical_schema · referrals · ai_risk · ai_analysis ·    │
│    locations · facilities                                                 │
│  core: security (JWT/bcrypt/refresh tokens) · permissions (roles) ·      │
│    authz (facility) · rate_limit (DB-backed) · config                     │
│  services: patient · event · referral · advisory_rules · risk_engine ·    │
│    ai_patient_service · ai_update_service                                 │
│  models (SQLAlchemy 2, portable PG/SQLite types) · schemas (Pydantic 2)   │
│  db: session · base (model registry) · init_db (Alembic runner + seed)    │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  SQLAlchemy (psycopg2) · Alembic (backend/alembic)
┌───────────────────────────────┴──────────────────────────────────────────┐
│  PostgreSQL 14+ (production) — SQLite for tests / quick local runs        │
│  facilities · users · patients · clinical_events · referrals ·            │
│  referral_status_history · ai_patient_analyses · audit_logs ·             │
│  refresh_tokens · auth_rate_limit_hits · alembic_version                  │
└──────────────────────────────────────────────────────────────────────────┘
Private file store: <UPLOADS_DIR>/id_cards/<uuid4>.<ext> (served only via an admin-only endpoint)
```

There is **no** message queue, background worker, LLM/RAG service, vector database or
Docker composition in this repository. Schema evolution is an Alembic migration chain
(`backend/alembic/versions/`, see §3).

## 2. Entry points

| Layer | Entry | Notes |
|---|---|---|
| Backend app | `backend/app/main.py` → `app` | Creates `UPLOADS_DIR/id_cards` on import/startup, mounts `api_router` at `/api/v1`, CORS from `CORS_ORIGINS`. Dev-only: `ENV=dev` + `AUTO_INIT_DB=true` runs `init_db()` at startup. |
| DB init / upgrade | `python -m app.db.init_db` | "Bring any DB to head": stamps a pre-Alembic database at `0001_baseline` if needed, runs `alembic upgrade head`, seeds the facility directory, backfills facility FKs from name snapshots, purges foreign-engine advisory caches. |
| Migrations | `alembic upgrade head` · `alembic check` · `alembic revision --autogenerate -m "…" --rev-id 000N_slug` | Run from `backend/`; `alembic/env.py` reads `DATABASE_URL` from settings (SECRET_KEY must be set too), `render_as_batch` on SQLite, `compare_type=True`. |
| First admin | `python -m app.scripts.create_super_admin` | Requires `SUPER_ADMIN_USERNAME/EMAIL/PASSWORD` env vars (no defaults); optional `SUPER_ADMIN_FACILITY_NAME` (+`_TYPE`) must name an existing facility. Alternative in dev only: `POST /api/v1/auth/bootstrap-admin` with `X-Bootstrap-Token` when `BOOTSTRAP_TOKEN` is set. |
| Frontend | `frontend/src/main.tsx` → `App.tsx` | Vite dev server on **5173**; `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`). |
| Tests | `backend/pytest.ini`, `backend/tests/` | SQLite in-memory by default; `TEST_DATABASE_URL` switches to PostgreSQL. |

## 3. Data model

All primary keys are UUIDs; timestamps are timezone-aware. Types are declared
portably (`sqlalchemy.Uuid`, `JSON().with_variant(JSONB, "postgresql")`) so the same
models run on PostgreSQL (production) and SQLite (tests).

| Table | Purpose | Key columns |
|---|---|---|
| `facilities` | Unified facility directory (PHCs + hospitals) | `name` (unique), `kind` (`phc\|hospital`), `created_at`; seeded by `init_db` |
| `users` | Clinician / hospital / viewer / admin accounts | `username`, `email` (unique), `role` (`admin\|clinician\|hospital\|viewer`), `is_super_admin`, `password_hash` (never serialized), `is_active`, `is_approved`, `approved_by/at`, `rejected_by/at` (rejected registration; cleared by approve), `deleted_at` (soft delete), **`facility_id` (FK → facilities)** + `facility_type/name` snapshots, `nmc_number`, `id_card_image_path` (private) |
| `refresh_tokens` | Server-side refresh tokens (one row per issued token) | `user_id` (FK → users, CASCADE), `token_hash` (sha256 of the opaque secret, unique), `expires_at`, `created_at`, `revoked_at`, `replaced_by_id` (successor on rotation), `user_agent`, `ip` |
| `auth_rate_limit_hits` | Hit log of the DB-backed auth rate limiter (shared by all workers) | `id` (BIGINT / INTEGER on SQLite, autoincrement), `key` (client IP), `hit_at`; pruned opportunistically |
| `patients` | Master record | `patient_id` (`PAT-YYYY-NNNNN`), `facility_mrn`, demographics, Nepal address (province/district/municipality/ward), **`registered_facility_id` (FK → facilities)** + `registered_facility_name/type` snapshots, `created_by_user_id` |
| `clinical_events` | **Append-only** clinical data, one row per field value | `patient_id`, `section`, `factor`, `value` (JSON `{value, unit, type}`), `event_time`, `note`, `created_by_user_id`, optional `referral_id` |
| `referrals` | Inter-facility referral | `patient_id`, **`from_facility_id` / `to_facility_id` (FK → facilities)** + `from_facility` / `to_facility` name snapshots, `status` (referring side), `received_facility_status` (receiving side), `reason`, `reason_codes`, `clinician_decision/note`, `submitted_at/received_at/closed_at` |
| `referral_status_history` | Structured status trail | `referral_id`, `kind` (`created\|status\|received_status\|decision`), `from_status`, `to_status`, `note`, `actor_user_id`, `actor_name`, `created_at` |
| `ai_patient_analyses` | Cached advisory output (1 row per patient) | `summary`, `referral_*`, `risk_factors`, `clinical_indicators`, `model_used`, `last_analyzed_at`, `data_version` |
| `audit_logs` | Append-only audit trail | `actor_user_id`, `action`, `entity_type/id`, `ip_address`, `user_agent`, `details` |
| `alembic_version` | Alembic bookkeeping | `version_num` (current head: `0003_auth_tokens_rate_limit`) |

The **medical schema** (`app/models/medical_schema.py`) is not a table: it is a typed
registry of 22 clinical sections (patient particulars, menstrual/contraceptive/obstetric
history, present pregnancy, three trimester ANC sections, vitals, examinations,
blood/renal/liver/thyroid/urine/serology investigations, ultrasonography). Every
`/medical-data` write is validated against it and stored as `clinical_events` rows.
See `MEDICAL_SCHEMA.md`.

### Facility identity (id-first, legacy name fallback)
Facilities live in ONE table, `facilities` (`kind` = `phc` | `hospital`), and every
facility-bearing row carries a **foreign key** to it: `User.facility_id`,
`Patient.registered_facility_id`, `Referral.from_facility_id` / `to_facility_id`. The name
columns next to those keys (`facility_name`, `registered_facility_name`,
`from_facility` / `to_facility`) are display snapshots (what the frontend sends and shows)
and are re-resolved server-side on every write: `POST /referrals` and the admin variants of
`POST/PATCH /patients` look the name up case-insensitively (trimmed) and reject unknown
names with `400 Unknown facility: X`; registration/bootstrap require an existing
`facility_id` of the requested kind (404 otherwise); the stored snapshot is the directory's
canonical spelling. `app/services/facility_service.py` (`resolve_facility`,
`resolve_user_facility`, `ensure_seed_facilities`, `backfill_facility_ids`) is the single
lookup layer.

Authorization (`app/core/authz.py`) compares **ids first**. The name snapshot is consulted
only when the *row's* facility id is NULL — rows written before revision `0002_facilities`
whose name matched no facility at migration time (the migration and every `init_db` run
backfill ids for names that do match). Such legacy rows stay reachable by name; a row that
has an id is never matched by name (so renaming a facility, or a user typing a look-alike
name, cannot widen access). Users with neither `facility_id` nor `facility_name` have no
facility scope unless they are admins. A legacy user whose `facility_id` is NULL but whose
name resolves is linked (self-healed) the first time they write, so what they write is
readable under the id-first rule.

Upgrade note (revision `0002_facilities`): the two legacy tables are merged into `facilities`
preserving ids; blank names and case-insensitive duplicates are dropped and their users are
re-pointed to the surviving row by name (the user's `facility_type`/`facility_name` are then
refreshed from the directory by `init_db`'s backfill, so a duplicate spanning kinds is made
consistent rather than left half-updated). Uniqueness of `facilities.name` is exact-case at
the database level; the seeding and lookup code compare case-insensitively.

### Schema migrations (Alembic)
Alembic is the schema mechanism. `backend/alembic.ini` (no URL inside) + `alembic/env.py`
(reads `settings.DATABASE_URL`, `target_metadata = Base.metadata`, `compare_type=True`,
`render_as_batch` on SQLite) + `alembic/versions/`:

| Revision | Content |
|---|---|
| `0001_baseline` | the full Phase-1 schema (9 tables incl. the old `phc_facilities` / `hospital_facilities`, enum types `user_role`, `referral_status`) — what `create_all` + the ensure-column helpers used to produce |
| `0002_facilities` | `facilities` table; copies both legacy tables into it (ids preserved); `users.facility_id` FK (dangling values NULLed); new `patients.registered_facility_id`, `referrals.from_facility_id` / `to_facility_id` backfilled by case-insensitive trimmed name; drops the legacy tables. Downgrade recreates them by kind. |
| `0003_auth_tokens_rate_limit` | `refresh_tokens` and `auth_rate_limit_hits` tables; `users.rejected_by` / `rejected_at` (+ index, batch mode). Downgrade drops them (rejected users become plain unapproved users). |

Every migration is written portably (`sa.Uuid()`, `sa.JSON().with_variant(JSONB, "postgresql")`,
`sa.Enum(..., name=...)`, `op.batch_alter_table` for ALTERs) so the same chain runs on
PostgreSQL and SQLite; `tests/test_migrations.py` asserts that `upgrade head` on a fresh
SQLite database yields exactly the ORM metadata (autogenerate diff empty), that the chain
round-trips, and that a pre-Alembic database is stamped and upgraded by `init_db()`.
`python -m app.db.init_db` wraps it all: legacy detection (tables but no `alembic_version`
→ PostgreSQL ensure-column helpers → `stamp 0001_baseline`), `upgrade head`, seed,
backfill, cache purge. New revisions: `alembic revision --autogenerate -m "…" --rev-id 000N_slug`
(keep ids ≤ 32 chars; `alembic_version.version_num` is `VARCHAR(32)`), then hand-check the
generated file for portability. Tests still build their per-test schema with
`Base.metadata.create_all` for speed.

## 4. Authentication

- `POST /api/v1/auth/login` (OAuth2 password form) →
  `{access_token, token_type: "bearer", expires_in, refresh_token}`.
  - **Access token**: HS256 JWT (`sub`, `username`, `role`, `iat`, `exp`), lifetime
    `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30, `expires_in` = seconds). Stateless — it is not
    individually revocable and stays valid until it expires; every request nevertheless
    re-checks the user row (`get_current_user`) and authorization uses the DB role, not the
    claim. Passwords are bcrypt via passlib (`passlib==1.7.4` + `bcrypt==3.2.2`, the
    known-good pair on Python 3.13).
  - **Refresh token**: opaque `secrets.token_urlsafe(32)` secret whose SHA-256 digest is
    stored in `refresh_tokens` (lifetime `REFRESH_TOKEN_EXPIRE_DAYS`, default 14; also
    `user_agent`/`ip` of issuance).
- `POST /auth/refresh {refresh_token}` → a new pair. **Rotation**: the presented row gets
  `revoked_at` + `replaced_by_id` → successor; tokens are single-use. 401 for unknown /
  expired (then retired) / revoked tokens and for users that may no longer sign in.
  **Reuse detection**: a token that was already revoked → every token of that user is revoked
  and `REFRESH_TOKEN_REUSE_DETECTED` is audited. Helpers live in `app/core/security.py`
  (`issue_refresh_token`, `rotate_refresh_token`, `revoke_refresh_token`,
  `revoke_all_refresh_tokens`, `RefreshTokenReuseError`).
- `POST /auth/logout {refresh_token}` → 204 (idempotent; audits `USER_LOGOUT`). Admin
  reject / soft-delete / role change call `revoke_all_refresh_tokens` for the target.
- `get_current_user` (`app/core/security.py`) rejects tokens whose user is missing,
  inactive, unapproved or soft-deleted → 401.
- Self-registration (`POST /auth/register`, multipart) creates an account with
  `is_active=False, is_approved=False` and role `clinician` (PHC facility) or `hospital`
  (hospital facility); an admin approves/rejects it and may change the role later
  (`PATCH /admin/users/{id}/role`, audited). Rejection sets `users.rejected_at/by`
  (`GET /admin/users/rejected` lists them; approve clears the rejection). Password
  minimum length 10 (422 otherwise). Optional ID-card image: jpg/jpeg/png/webp,
  `image/*`, ≤ `MAX_ID_CARD_SIZE_MB`, stored as `<uuid4>.<ext>` (client filename never
  used).
- `/auth/login`, `/auth/register` and `/auth/refresh` are rate-limited per client IP by a
  **database-backed** sliding window (`app/core/rate_limit.py`, table
  `auth_rate_limit_hits`, `RATE_LIMIT_*`): the count is shared by every worker/process
  using the same DB; 429 carries `Retry-After`. `RATE_LIMIT_DISABLED=true` → no-op.
- Frontend flow (`frontend/src/services/api.ts`): tokens in `localStorage`; the axios
  response interceptor answers a 401 (except from `/auth/login|refresh|logout`) with one
  single-flight `/auth/refresh` and a single retry of the failed request, otherwise clears
  the session and redirects to `/login`; `logout()` posts `/auth/logout` best-effort, then
  clears.

## 5. Authorization (server-side; the UI only mirrors it)

Roles (`app/core/permissions.py`):

| Dependency | Roles |
|---|---|
| `require_any_authenticated` | admin, clinician, hospital, viewer |
| `require_clinician_or_admin` | admin, clinician, hospital (all clinical writes) |
| `require_admin` | admin (user management, ID-card retrieval) |

Facility/object rules (`app/core/authz.py`), applied on every patient, event,
medical-data, referral and advisory route:

- **Admin** may access every patient and referral.
- A non-admin may access a **patient** if the patient was registered by their facility
  **or** any referral for that patient lists their facility as sender or receiver — compared
  by facility **id** (`user.facility_id` vs `registered_facility_id` / `from_facility_id` /
  `to_facility_id`); the name snapshot is used only for legacy rows whose id is NULL.
  `GET /patients` (search) applies the same rule as a SQL filter.
- A non-admin may read a **referral** if their facility is sender or receiver (same rule).
  `POST /referrals/{id}/status` — referring facility only; `POST …/received-status` —
  receiving facility only (transitions `None→received|cancelled`,
  `received→closed|cancelled`; terminal states immutable). On create, both facility names
  must resolve to directory rows (400 otherwise) and non-admins' `from_facility` must be
  their own facility (by id).
- **Viewer** can read anything its facility may access but cannot write clinical data,
  create referrals, or (re)generate advisory analyses.
- Admin user management: approve/reject/role-change/soft-delete are audited; acting on
  your own account is rejected; approving, rejecting, deleting or re-roling an
  **admin-role** user and granting `admin` require `is_super_admin` (prevents
  admin-vs-admin lockout).
- ID-card images are **not** static files; `GET /admin/users/{id}/id-card` (admin only)
  streams them from `UPLOADS_DIR`, path-checked to that directory.

Full matrix and rationale: `ACCESS_CONTROL.md`.

## 6. Request flows

**Clinical record update** — `UpdateRecord.tsx` loads `/schema/sections?updates_only=true`
→ user picks a section (deep-linkable via `?section=`) → `POST
/medical-data/patients/{id}/sections/{key}` with `{section_key, data_points, event_time?}`
→ validated against the medical schema → N `clinical_events` rows → the cached advisory
analysis for the patient is deleted (`ai_update_service.mark_ai_analysis_for_update`).
The same invalidation runs on `/events`, `/events/batch`, `/medical-data/bulk-entry` and
referral creation.

**Referral** — referring facility creates (`status=submitted`), the receiving facility
sets `received_facility_status` (admitted/closed/cancelled) with a note; when that value
is also a valid next step of the referring-side machine (submitted→received,
received→closed, draft/submitted→cancelled) it is mirrored into `status`, so the sender's
view stays truthful without a second manual step. Either side's changes append
`referral_status_history` rows; the Referral page renders that table
(`GET /referrals/{id}/history`). The Dashboard inbox uses `GET /referrals` with
`direction=incoming|outgoing`, `status`, `received_status` — one SQL query, correctly
paginated, always constrained to the caller's facility for non-admins.

**Advisory** — `PatientProfile.tsx` fetches `GET /ai-analysis/patients/{id}/analysis?auto_generate=true`
once and passes the result to two presentational cards. If nothing is cached and the
caller may generate (clinician/hospital/admin) the engine runs synchronously and stores
the result; viewers get 404 (empty state) instead of triggering generation.

## 7. Advisory engine (rule-based; no LLM)

`app/services/advisory_rules.py` is the single source of truth: a pure function
`evaluate_latest_values(latest)` over the **latest value per (section, factor)**
(`risk_engine.latest_per_factor`) applies fixed thresholds to maternal vitals
(`vitals.blood_pressure_systolic/diastolic`, `vitals.pulse_rate`, temperature,
respiratory rate, BMI), investigations (`blood_investigations.hemoglobin`,
`blood_glucose`, `platelet_count`; `urine_examination.dipstick_protein`, 24-h protein,
PCR), fetal heart rate (fetal thresholds 110–160, from `per_abdominal_examination` /
`ultrasonography`, never mixed with maternal pulse), ANC symptom booleans, consciousness,
placenta location and a few history fields. Output: `risk_level ∈ unknown|low|medium|high|critical`,
`urgency`, `referral_needed`, weighted findings, advisory actions and a mandatory
disclaimer. Every string passes `app/ai/validators.py::validate_advisory_language`.
Both `POST /ai/risk` (`RiskEngine`) and `/ai-analysis/*` (`AIPatientService`) build on
this function; `model_used`/`model_version` is `"rule-based-advisory-v2"`. Cached rows
produced by any other engine (e.g. LLM-era rows on an upgraded database) are discarded by
`init_db()` and by the service, never served. Every (re)generation is audited
(`ADVISORY_ANALYSIS_GENERATED`). Details, thresholds and limitations:
`AI_FEATURES_README.md`.

## 8. Frontend structure

- `services/api.ts` — axios instance, token store (access + refresh token in
  localStorage) and user store (localStorage + in-memory subscription), `login()` /
  `refreshAccessToken()` / `logout()` session helpers, 401 interceptor (one single-flight
  refresh + retry, else clear + redirect to `/login`), `getErrorMessage`,
  `facilityMatches`, and small typed helpers (admin users incl. `fetchRejectedUsers`,
  ID-card blob, referral history, advisory analysis). `services/types.ts` — shared
  response types.
- `hooks/useUser.tsx` — `{user, loading, isAuthenticated, refresh}` from `/auth/me`.
- `App.tsx` — routes; `RequireAuth` (token present) and `RequireAdmin` (role, with a
  loading state). Route table: `/`, `/login`, `/signup`, `/dashboard`, `/patients`,
  `/patients/new`, `/patients/:id`, `/patients/:id/edit`, `/patients/:id/update`,
  `/patients/:id/referral[/:referralId]`, `/admin/users`, `/admin/pending`.
- TypeScript is strict (`tsconfig.json`); `npm run build` runs `tsc --noEmit` first.

## 9. Testing

`backend/tests` (pytest, 204 tests): startup without an uploads dir, `init_db` on
SQLite, Alembic parity (`upgrade head` == ORM metadata, downgrade round trip, legacy
database stamping + facility-id backfill), facility directory (`GET /facilities`, unknown
facility → 400/404, id-first authorization with legacy name fallback, referral/patient ids),
login/approval/soft-delete, refresh tokens (`test_refresh_tokens.py`: issue, rotation,
reuse detection revoking the family, logout, expiry, refusal for rejected / deleted /
unapproved users, revocation on role change), the DB-backed rate limiter
(`test_rate_limit.py`: 429 + `Retry-After`, sliding window, pruning, two independent
sessions sharing one budget, guarded endpoints, no writes when disabled), rejected
registrations (excluded from pending, listed under `/rejected`, approve clears), no
`password_hash` in any user response, viewer write blocks, facility scoping for
patients/events/medical-data/referrals/advisory, referral party rules and transitions,
history endpoint, direction filters and pagination, ID-card upload validation and
admin-only retrieval, and the advisory rule set (pure-function tests: thresholds,
fetal-vs-maternal, latest-per-factor, advisory-language validation), plus the post-review
fixes (admin-vs-admin guards, role endpoint, registration role, foreign-engine cache purge,
status mirroring, event referral linkage). Frontend: `npm run typecheck`, `npm run build`
and the Playwright suite (`npm run test:e2e`, see `frontend/e2e/README.md`).

## 10. Known limitations / future work

- Legacy rows (created before revision `0002_facilities`) whose facility name matched no
  directory entry keep a NULL facility id and are matched by name only; patients with
  neither id nor name are admin-only until an admin re-homes them via `PATCH /patients/{id}`.
  There is no admin API to create facilities or to change a user's facility (edit the
  `facilities` table / user row and re-run `init_db` to backfill).
- The rate limiter trusts the first `X-Forwarded-For` hop (deploy behind a proxy that sets it).
- Access JWTs are not revocable individually — only bounded by `ACCESS_TOKEN_EXPIRE_MINUTES`
  (refresh tokens are). Tokens live in browser `localStorage`; httpOnly cookies would harden it.
- Advisory engine has no gestational-age awareness or trend analysis and evaluates only
  the fields listed in `AI_FEATURES_README.md`.
- CI (`.github/workflows/ci.yml`) runs the backend suite on SQLite and PostgreSQL (Python 3.11/3.13),
  fresh-database initialisation + `alembic check`, SQLite migration portability, the frontend
  type-check/build and the Playwright E2E suite on every push/PR.
