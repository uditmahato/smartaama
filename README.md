<h1 align="center">SmartAama</h1>

<p align="center">
  <strong>Maternal-health records and referral system for primary health care facilities in Nepal —<br>
  with a transparent, rule-based, advisory-only risk engine.</strong>
</p>

<p align="center">
  <a href="https://github.com/uditmahato/smartaama/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/uditmahato/smartaama/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-14%2B-4169E1?logo=postgresql&logoColor=white">
  <img alt="React 18" src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black">
  <img alt="TypeScript strict" src="https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
</p>

SmartAama ("smart mother" in Nepali) lets a primary health centre (PHC) register pregnant
patients, record antenatal-care (ANC) visits as an **append-only clinical timeline**, refer
patients to hospitals, and lets the receiving hospital acknowledge, admit and close the case.
A deterministic **rule engine** reads the latest recorded vitals, investigations and ANC
symptoms and produces an *advisory* summary and referral suggestion.

> **Advisory only.** SmartAama does not diagnose, does not use any large language model, and
> is not a substitute for clinical judgement. Clinical decisions rest with the treating
> clinician. See [Advisory engine](#advisory-engine).

This README describes the repository **as it is today**. Anything not implemented is labelled
*Planned*.

---

## Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Quick start](#quick-start)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Setup in detail](#setup-in-detail)
- [Configuration](#configuration)
- [Testing and CI](#testing-and-ci)
- [API overview](#api-overview)
- [Roles and authorization](#roles-and-authorization)
- [Advisory engine](#advisory-engine)
- [Documentation](#documentation)
- [Roadmap and known limitations](#roadmap-and-known-limitations)
- [Contributing and security](#contributing-and-security)
- [Contributors](#contributors)
- [License](#license)

---

## Features

| Area | What it does |
|---|---|
| **Accounts & approval** | Clinicians self-register (with an optional ID-card image); accounts stay pending until an admin approves them. Roles: `admin`, `clinician`, `hospital`, `viewer`. JWT access tokens with rotating refresh tokens; per-IP rate limiting on login/register/refresh. |
| **Patients** | Registration with Nepal's address hierarchy (province → district → municipality → ward), auto-generated IDs (`PAT-YYYY-NNNNN`, facility MRN), search, demographic edits. Every patient belongs to the facility that registered it. |
| **Clinical records** | 22 typed clinical sections (obstetric/menstrual/contraceptive history, present pregnancy, three trimester ANC visits, vitals, examinations, blood/renal/liver/thyroid/urine/serology investigations, ultrasonography). Writes are validated against the schema and stored as immutable clinical events; the profile shows a filterable timeline and latest-value summary. |
| **Referrals** | PHC → hospital referrals with a referring-side status (`draft → submitted → received → closed`, `cancelled`) and a receiving-side status (API values `received` = admitted, `closed`, `cancelled` = referred elsewhere) that is mirrored back into the sender's view; structured status history with notes; an inbox with incoming / outgoing / admitted / closed filters. |
| **Advisory engine** | Rule-based summary and referral suggestion: risk level `unknown / low / medium / high / critical`, weighted findings, advisory actions and a mandatory disclaimer. Cached per patient and invalidated on every clinical write. No LLM. |
| **Access control** | Enforced server-side: role checks plus facility-level scoping (a facility sees only its own patients and referrals it sends or receives). Private ID-card storage; explicit response schemas (no password hashes ever leave the API). |
| **Audit** | Append-only audit log for logins, registrations, approvals/rejections/role changes/deactivations, patient and clinical writes, referral actions and advisory generation. |

## Screenshots

<!-- screenshots:start -->
<table>
  <tr>
    <td width="50%"><img src="documentation/screenshots/dashboard.png" alt="Referral inbox (dashboard) with status/facility filters"><br><sub><b>Referral inbox</b> — incoming/outgoing/admitted/closed filters, scoped to the user's facility.</sub></td>
    <td width="50%"><img src="documentation/screenshots/patient-profile.png" alt="Patient profile header with personal information and actions"><br><sub><b>Patient profile</b> — demographics, notes, referral history, clinical summary and timeline.</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="documentation/screenshots/advisory-summary.png" alt="Advisory Summary (rule-based) card showing a critical risk level and key clinical signs"><br><sub><b>Advisory Summary (rule-based)</b> — latest values vs. thresholds, engine name shown, disclaimer visible.</sub></td>
    <td width="50%"><img src="documentation/screenshots/referral-advisory.png" alt="Referral Advisory (rule-based) card with reasons and weighted risk factors"><br><sub><b>Referral Advisory (rule-based)</b> — suggestion, urgency, reasons and weighted findings (a transparency score, not a probability).</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="documentation/screenshots/referral-history.png" alt="Referral page with receiving-facility status and structured history table"><br><sub><b>Referral</b> — sender/receiver statuses and the structured status history.</sub></td>
    <td width="50%"><img src="documentation/screenshots/admin-pending-users.png" alt="Admin pending users page"><br><sub><b>Admin</b> — approve/reject registrations and view ID cards (roles are changed via the API).</sub></td>
  </tr>
</table>

<sub>Captured from the throw-away end-to-end stack with seeded example data (`E2E_SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts`).</sub>
<!-- screenshots:end -->

## Quick start

Prerequisites: **Python 3.11+**, **Node.js 20+ / npm** (Playwright requires 20+), **PostgreSQL 14+** (tests don't need it), Git.

```bash
git clone https://github.com/uditmahato/smartaama.git && cd smartaama
```

Backend:

```bash
cd backend && python -m venv .venv
```

Activate the venv (Windows PowerShell `.\.venv\Scripts\Activate.ps1`; Linux/macOS `source .venv/bin/activate`), then:

```bash
pip install -r requirements.txt
```

Create `backend/.env` from `backend/.env.example` (set `SECRET_KEY` — 32+ characters — and
`DATABASE_URL`), create the PostgreSQL database, then bring the schema to the current
migration head and seed the facility directory:

```bash
python -m app.db.init_db
```

Create the first admin (values are examples; the script has **no defaults**):

```bash
SUPER_ADMIN_USERNAME=admin SUPER_ADMIN_EMAIL=admin@example.com SUPER_ADMIN_PASSWORD="<at least 10 characters>" SUPER_ADMIN_FACILITY_NAME="Bir Hospital" SUPER_ADMIN_FACILITY_TYPE=hospital python -m app.scripts.create_super_admin
```

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (new terminal):

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173, log in as the admin, approve users under **Admin → Pending users**.
API docs: http://localhost:8000/docs.

## Architecture

```
React 18 + TS + Vite + MUI  ──HTTP/JSON, JWT──▶  FastAPI (/api/v1)  ──SQLAlchemy 2──▶  PostgreSQL 14+
frontend/  (lazy-loaded routes)                  backend/app                              (SQLite for tests)
  Home · Login · Signup · Dashboard (inbox)        endpoints: auth · admin · patients · events ·
  Patient search/create/profile/edit/update        medical-data · schema · referrals · ai-risk ·
  Referral · Admin users                           ai-analysis · locations · facilities
  services/api.ts — axios, bearer + silent          core: security (JWT, refresh tokens) ·
  refresh, 401 → /login                            permissions (roles) · authz (facility scope) ·
                                                   rate_limit (DB-backed)
                                                   services: patient · event · referral ·
                                                   advisory_rules · risk_engine
                                                   Alembic migrations · private uploads dir
```

- **Backend** — FastAPI, SQLAlchemy 2 models with portable types (PostgreSQL in production,
  SQLite in tests), Pydantic 2 schemas, JWT auth, role + facility-level authorization enforced
  server-side, Alembic migrations.
- **Database** — PostgreSQL. `python -m app.db.init_db` upgrades to the Alembic head
  (stamping pre-Alembic databases first), seeds the facility directory and clears stale
  advisory caches.
- **Frontend** — React 18 SPA (strict TypeScript, Vite 5, Material UI 5), route-level code
  splitting, talks only to `/api/v1`.
- **Advisory engine** — `backend/app/services/advisory_rules.py`: pure, deterministic rules over
  the latest value per clinical factor. No OpenAI/LLM, no RAG, no vector DB, no background
  workers.

Full details: [`documentation/ARCHITECTURE.md`](documentation/ARCHITECTURE.md).

## Technology stack

Only what is actually used and installed:

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ (CI: 3.11 and 3.13), FastAPI, Uvicorn, SQLAlchemy 2, Alembic, Pydantic 2 + pydantic-settings, python-jose (JWT HS256), passlib + bcrypt, python-multipart, python-dotenv, psycopg2-binary |
| Database | PostgreSQL 14+ (verified on 16); SQLite for the test suite and E2E runs |
| Frontend | React 18, TypeScript 5 (strict), Vite 5, Material UI 5 (+ `@mui/x-data-grid` 8), React Router 6, axios |
| Tests | pytest + httpx (backend); `tsc --noEmit` + `vite build` (frontend); Playwright (browser E2E) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |

*Not used:* OpenAI/GPT, LangChain, RAG/vector databases, sentence-transformers, Celery, Redis, Docker.

## Repository structure

```
smartaama/
├── README.md · LICENSE (MIT) · CONTRIBUTING.md · .gitignore
├── .github/workflows/ci.yml       # backend (SQLite + PostgreSQL), frontend, E2E
├── backend/
│   ├── requirements.txt · .env.example · pytest.ini · alembic.ini
│   ├── alembic/                   # migrations (versions/0001_baseline, 0002_facilities, …)
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, uploads dir, /api/v1 router
│   │   ├── core/                  # config, security (JWT/bcrypt/refresh tokens), permissions,
│   │   │                          # authz (facility/object rules), rate_limit (DB-backed)
│   │   ├── db/                    # session, base (model registry), init_db (Alembic wrapper)
│   │   ├── models/                # SQLAlchemy models + medical_schema registry
│   │   ├── schemas/               # Pydantic request/response models
│   │   ├── services/              # patient, event, referral, facility, advisory_rules,
│   │   │                          # risk_engine, ai_patient_service, ai_update_service
│   │   ├── api/v1/                # api_router + endpoints/*
│   │   ├── ai/validators.py       # advisory-language validator
│   │   ├── scripts/create_super_admin.py
│   │   └── utils/nepal_locations.py (+ nepal_admin_structure_province_names.json)
│   └── tests/                     # pytest suite (SQLite by default; TEST_DATABASE_URL for PG)
├── frontend/
│   ├── package.json · package-lock.json (npm) · tsconfig.json · vite.config.ts · playwright.config.ts
│   ├── .env.example               # VITE_API_BASE_URL
│   ├── e2e/                       # Playwright specs + helpers (see e2e/README.md)
│   └── src/
│       ├── App.tsx (lazy routes) · main.tsx
│       ├── pages/                 # Home, Login, Signup, Dashboard, PatientSearch, PatientCreate,
│       │                          # PatientProfile, PatientEdit, UpdateRecord, Referral, admin/*
│       ├── components/            # Navbar, RequiredAdmin, IdCardDialog, advisory cards
│       ├── hooks/useUser.tsx
│       └── services/              # api.ts (axios + token refresh + helpers), types.ts
└── documentation/                 # ARCHITECTURE, ACCESS_CONTROL, MEDICAL_SCHEMA,
                                   # AI_FEATURES_README, TESTING_GUIDE, QUICK_REFERENCE, …
```

## Setup in detail

### Backend

1. `cd backend && python -m venv .venv` and activate it.
2. `pip install -r requirements.txt` (runtime + test dependencies).
3. Copy `.env.example` → `.env`; set `SECRET_KEY` (32+ chars, e.g.
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`) and `DATABASE_URL`
   (e.g. `postgresql+psycopg2://user:password@localhost:5432/smartaama`).
4. Create the database (`CREATE DATABASE smartaama;`).
5. `python -m app.db.init_db` — runs `alembic upgrade head` (stamps a pre-Alembic database
   at the baseline first), seeds ~20 PHC/hospital facilities, and purges stale advisory
   caches. Safe to re-run; run it again after pulling changes that add migrations.
   Developers can also use `alembic upgrade head`, `alembic current`, `alembic check`, and
   `alembic revision --autogenerate -m "…" --rev-id 000N_short_slug` from `backend/`.
6. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (or `start_backend.ps1` /
   `start_backend.bat`). The private uploads directory is created automatically.

### First admin

Accounts created through the signup page are unapproved until an admin approves them, so the
first (super) admin is created from the command line with `python -m app.scripts.create_super_admin`
and the `SUPER_ADMIN_*` environment variables shown in [Quick start](#quick-start). The facility
name must be one of the seeded facilities (`GET /api/v1/facilities?kind=hospital|phc`).
Alternative in development only: with `ENV=dev` and a non-empty `BOOTSTRAP_TOKEN`,
`POST /api/v1/auth/bootstrap-admin` with header `X-Bootstrap-Token` (see Swagger UI).

### Frontend

`cd frontend && npm install && npm run dev` — served at **http://localhost:5173**. It calls the
backend at `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`) directly, so the
backend's `CORS_ORIGINS` must include the frontend origin (the default does).

## Configuration

Backend (`backend/.env`, every variable listed with comments in `.env.example`):

| Variable | Required | Meaning |
|---|---|---|
| `SECRET_KEY` | yes | JWT signing secret, ≥ 32 characters |
| `DATABASE_URL` | yes | SQLAlchemy URL (PostgreSQL in production; SQLite works for quick local runs) |
| `ENV` | no (`dev`) | `dev` / `staging` / `prod`; dev-only features (bootstrap endpoint, `AUTO_INIT_DB`) require `dev` |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `JWT_ALGORITHM` | no | token lifetimes / algorithm |
| `CORS_ORIGINS` | no | comma-separated allowed browser origins |
| `AUTO_INIT_DB` | no | dev only: run `init_db()` at startup |
| `BOOTSTRAP_TOKEN` | no | dev only: enables `POST /auth/bootstrap-admin`; empty = disabled |
| `UPLOADS_DIR`, `MAX_ID_CARD_SIZE_MB` | no | private upload root (default `backend/uploads`), max ID-card size |
| `RATE_LIMIT_DISABLED`, `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` | no | auth rate limiter (10 requests / 60 s per IP by default; DB-backed, works across workers) |

Frontend (`frontend/.env`): `VITE_API_BASE_URL` only. Never commit `.env` files (gitignored).

## Testing and CI

Everything below runs in CI (`.github/workflows/ci.yml`) on every push and pull request.

Backend — no database server needed (SQLite), optionally PostgreSQL:

```bash
cd backend && python -m pytest -q
```

```bash
cd backend && TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/smartaama_test python -m pytest -q
```

Frontend — type-check and production build (`build` runs `tsc --noEmit` first):

```bash
cd frontend && npm run typecheck && npm run build
```

Browser end-to-end (Playwright, Chromium; starts a throw-away SQLite backend and the Vite dev
server itself — see [`frontend/e2e/README.md`](frontend/e2e/README.md)):

```bash
cd frontend && npx playwright install chromium && npm run test:e2e
```

Test coverage is focused rather than exhaustive: authentication/authorization, user
serialization, facility scoping, referral rules, migration parity (`alembic check`), the
advisory rule set, and five end-to-end user journeys (login, signup + approval, patient
creation, record update → advisory, referral flow).

## API overview

Base path `/api/v1`, interactive docs at `/docs`. Authenticate with
`Authorization: Bearer <access token>` from `POST /auth/login`.

| Group | Endpoints | Access |
|---|---|---|
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/register`, `GET /auth/me`, `POST /auth/bootstrap-admin` (dev) | public / public / public / public / any user / token-gated |
| Admin | `GET /admin/users`, `GET /admin/users/pending`, `GET /admin/users/rejected`, `PATCH /admin/users/{id}/approve`, `PATCH …/reject`, `PATCH …/role`, `DELETE /admin/users/{id}` (soft delete), `GET /admin/users/{id}/id-card` | admin (admin-role targets and granting `admin` require a super admin) |
| Patients | `POST /patients`, `GET /patients` (scoped search), `GET /patients/{id}`, `PATCH /patients/{id}` | clinician/hospital/admin write; facility-scoped read |
| Clinical events | `POST /events`, `POST /events/batch`, `GET /events?patient_id=` | facility-scoped; writes clinician/hospital/admin |
| Medical schema / data | `GET /schema/sections[?updates_only]`, `GET /schema/sections/{key}[/fields]`; `POST /medical-data/patients/{id}/sections/{key}`, `POST …/bulk-entry`, `GET …/latest`, `GET …/history` | authenticated; writes clinician/hospital/admin |
| Referrals | `POST /referrals`, `GET /referrals` (`direction`, `status`, `received_status`, `patient_id`, …), `GET /referrals/{id}`, `PATCH /referrals/{id}`, `POST /referrals/{id}/status`, `POST /referrals/{id}/received-status`, `GET /referrals/{id}/history` | referral parties only; `status` = referring facility, `received-status` = receiving facility |
| Advisory | `GET /ai-analysis/patients/{id}/analysis`, `GET …/status`, `POST /ai-analysis/generate`, `DELETE /ai-analysis/patients/{id}`, `POST /ai/risk` | read: any user with patient access; generate/delete: clinician/hospital/admin |
| Reference data | `GET /locations/provinces|districts|municipalities|wards`, `GET /facilities?kind=phc|hospital` | public (needed for signup) |

## Roles and authorization

Roles: `admin`, `clinician`, `hospital`, `viewer`. Enforcement is **server-side**
(`backend/app/core/permissions.py`, `backend/app/core/authz.py`); the UI only mirrors it.

- **Admin** — everything, including user management. Acting on admin-role users and granting
  `admin` require a super admin (the account created by `create_super_admin`).
- **Clinician / hospital** — clinical writes and referrals for patients their facility may
  access. Self-registration assigns `clinician` (PHC) or `hospital` (hospital facility);
  admins can change roles.
- **Viewer** — read-only within the same facility scope.
- **Facility scope** — facilities are rows of a directory table and referenced by foreign key
  from users, patients and referrals; a user may access a patient registered by their facility
  or any patient with a referral from/to their facility. Referrals are visible only to the
  sending and receiving facilities.
- Rejected registrations, soft-deletion and role changes revoke the user's refresh tokens.

Details and the permission matrix: [`documentation/ACCESS_CONTROL.md`](documentation/ACCESS_CONTROL.md).

## Advisory engine

`backend/app/services/advisory_rules.py` evaluates the **latest recorded value per factor**
against fixed thresholds — maternal BP, pulse, temperature, respiratory rate, BMI;
haemoglobin, glucose, platelets; urine protein; fetal heart rate (fetal thresholds, kept
separate from maternal pulse); ANC symptom flags; consciousness; placenta location; selected
history fields — and returns a risk level, a referral suggestion with urgency and weighted
reasons, advisory actions and a disclaimer. Every sentence passes an advisory-language
validator (no "must", "administer", "diagnose", …). `model_used` is always
`rule-based-advisory-v2`.

It is **advisory only** — not a diagnosis, not a substitute for clinical judgement, and not
cleared for regulated clinical use. Thresholds, inputs and limitations:
[`documentation/AI_FEATURES_README.md`](documentation/AI_FEATURES_README.md).

## Documentation

[`documentation/README.md`](documentation/README.md) is the index: architecture, access
control, the medical schema, the advisory engine, the testing guide, a developer quick
reference, and two clearly labelled *design reference (not implemented)* files on a broader
risk-scoring proposal.

## Roadmap and known limitations

- Multi-tab sessions share one refresh token; two tabs refreshing in the very same instant can
  trip the reuse detection and log both out (mitigated with a cross-tab lock where the browser
  supports the Web Locks API).
- **Planned:** admin UI for facility management (facilities are seeded; there is no API to add
  one yet), Nepali-language UI, offline support, notifications on referral changes, Docker
  packaging, LLM-assisted summaries with guideline retrieval (explicitly *not* present today).
- Access tokens are short-lived but not individually revocable before expiry (refresh tokens
  are). Tokens are kept in browser `localStorage`; moving to httpOnly cookies is a hardening
  step for production.
- Patients/referrals created before facility foreign keys existed keep working through a
  name-based fallback and are back-filled by `init_db`; rows whose legacy name matches no
  facility are admin-only until re-homed.
- Automated tests are focused (backend security/rules/migrations, frontend type-check/build,
  five browser journeys), not exhaustive.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, expectations and the verification commands.
Please report suspected vulnerabilities privately to the maintainers below rather than in a
public issue.

## Contributors

Derived from the Git history (`git shortlog -sne --all`); no names were added from outside the
repository:

- **Udit Kumar Mahato** — GitHub [`@uditmahato`](https://github.com/uditmahato); commits authored as `uditmahato <uditmahato29271@gmail.com>` and `Udit Kumar Mahato <…@users.noreply.github.com>` (same GitHub account).
- **subin989** — commits authored as `subin989 <subin@konnectcraft.com>`.
- **Subin Satyal** — GitHub [`@subin131`](https://github.com/subin131); one commit (PR #6, `6243a5b`) whose squash message carries a `Co-authored-by: subin989` trailer — likely the same person as `subin989`, but the history does not state it conclusively, so both are listed as recorded.

## License

Released under the [MIT License](LICENSE) — Copyright (c) 2026 Udit Kumar Mahato and the
SmartAama contributors. The advisory engine's outputs are provided as-is and are not medical
advice (see the disclaimer below).

---

*SmartAama is a clinical decision-support and record-keeping tool. Its advisory output is not
a diagnosis; healthcare providers retain full responsibility for clinical decisions.*
