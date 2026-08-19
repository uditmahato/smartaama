# Browser end-to-end tests (Playwright)

These tests drive the real application in Chromium: the Vite dev server in
front of the FastAPI backend running on a throw-away SQLite database. Nothing
is mocked.

```
frontend/
  playwright.config.ts   Chromium project, webServer for backend + frontend, globalSetup
  e2e/
    env.ts               ports, URLs, backend env, seeded credentials (single source of truth)
    start-backend.mjs    deletes the previous e2e DB/uploads, then runs uvicorn (backend webServer)
    global-setup.ts      bootstraps the admin + an approved PHC clinician through the API
    helpers/             seed access, UI helpers (login, MUI select), API setup helpers, test PNG
    *.spec.ts            the tests (see below)
```

## Prerequisites

* Node 22 + `npm ci` in `frontend/` (installs `@playwright/test`).
* The Chromium build for Playwright: `npx playwright install chromium`
  (CI: `npx playwright install --with-deps chromium`).
* A Python interpreter with the backend requirements installed
  (`pip install -r backend/requirements.txt`). Point `E2E_PYTHON` at it if it
  is not the `python` on your `PATH`.
* Ports **8000** (backend) and **5173** (frontend) free — or already running
  the e2e stack (see "Reusing servers").

## Running locally

```powershell
# PowerShell (Windows)
cd frontend
$env:E2E_PYTHON = "..\backend\.venv\Scripts\python.exe"
npm run test:e2e            # headless, list reporter + HTML report in playwright-report/
npm run test:e2e:ui         # Playwright UI mode (pick tests, watch, time-travel)
```

```bash
# bash / macOS / Linux
cd frontend
E2E_PYTHON=../backend/.venv/bin/python npm run test:e2e
```

Useful variants:

```bash
npx playwright test e2e/auth.spec.ts        # one file
npx playwright test --headed                # watch the browser
npx playwright test --debug                 # step through with the inspector
npx playwright show-report                  # open the last HTML report
npm run typecheck:e2e                       # type-check the e2e code itself
```

## What the run does

1. **Backend web server** — `node e2e/start-backend.mjs` (cwd `frontend/`):
   * removes `backend/e2e_smartaama.db*` and `backend/e2e_uploads/` so every
     run starts from an empty database (skip with `E2E_KEEP_DB=1`);
   * runs `<E2E_PYTHON or python> -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
     from `backend/` with this environment (defined in `e2e/env.ts`):

     | variable              | value                                                    |
     |-----------------------|----------------------------------------------------------|
     | `ENV`                 | `dev`                                                    |
     | `SECRET_KEY`          | `e2e-only-secret-key-not-for-production-use-0123456789`  |
     | `DATABASE_URL`        | `sqlite:///./e2e_smartaama.db`                           |
     | `AUTO_INIT_DB`        | `true` (creates the schema + seeds the facilities)       |
     | `BOOTSTRAP_TOKEN`     | `e2e-bootstrap-token`                                    |
     | `RATE_LIMIT_DISABLED` | `true`                                                   |
     | `UPLOADS_DIR`         | `./e2e_uploads`                                          |
     | `CORS_ORIGINS`        | `http://localhost:5173`                                  |

   The readiness check is `GET http://127.0.0.1:8000/`. The backend is
   addressed as `127.0.0.1` rather than `localhost` on purpose: on some
   machines another process listens on `[::1]:8000` and Chromium/Node would
   connect to that first.
2. **Frontend web server** — `npm run dev -- --port 5173 --strictPort` with
   `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`; readiness check
   `GET http://localhost:5173/`.
3. **Global setup** (`e2e/global-setup.ts`, runs after both servers are up):
   * `GET /api/v1/facilities?kind=hospital` and `?kind=phc` — the first
     hospital and the first PHC are used throughout;
   * `POST /api/v1/auth/bootstrap-admin` (header `X-Bootstrap-Token`) creates
     the super admin `e2e-admin@example.com` at that hospital;
   * `POST /api/v1/auth/register` (multipart, PHC, tiny PNG ID card) +
     `PATCH /api/v1/admin/users/{id}/approve` creates the approved clinician
     `e2e-clinician@example.com` at that PHC.
   Both steps are idempotent ("User already exists" is fine), so the suite
   also works against a reused server / existing database. Credentials and
   facilities are handed to the specs via `process.env.E2E_SEED` and
   `test-results/e2e-seed.json`.
4. **Specs** (Chromium, `workers: 2` locally / `1` in CI, files in parallel,
   tests inside a file in order):

   | file                          | what it covers                                                                                                                                                                                                                              |
   |-------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
   | `auth.spec.ts`                | wrong password shows the backend error and stays on `/login`; valid login lands on `/` and reaches `/dashboard` (navbar shows the facility); anonymous visit to `/dashboard` redirects to `/login`.                                        |
   | `signup-approval.spec.ts`     | Signup page (PHC, facility select, ID-card upload) -> "awaiting approval" -> login refused while pending -> admin approves in `/admin/pending` -> logout via navbar -> the new clinician logs in and sees their PHC in the navbar.        |
   | `patient.spec.ts`             | clinician opens "Add patient", fills demographics + the Nepal address cascade (province -> district -> municipality -> ward), creates the patient, sees the profile (address, edit rights) and finds it via the patient search.            |
   | `record-advisory.spec.ts`     | baseline "UNKNOWN RISK" / "No Referral Suggested"; Update Record: vitals with 165/112 mmHg, then urine dipstick `++` -> profile cards show `CRITICAL RISK`, "Referral Suggested" (urgency CRITICAL) and `Engine: rule-based-advisory-v2`.  |
   | `screenshots.spec.ts`         | opt-in (`E2E_SCREENSHOTS=1`): seeds a critical patient + admitted referral and writes the README screenshots to `documentation/screenshots/`; skipped in normal runs and CI. |
   | `referral.spec.ts`            | PHC clinician refers to the admin's hospital (sender locked to own facility) -> clinician dashboard "Referred from Here"; hospital admin opens it from the patient's referral history, sets "Admitted Here" (+ note) -> history table rows (receiving status, mirrored referring status), admin dashboard "Admitted Case"; sender sees "Admitted Here". |

Every spec creates its own patients / users with a unique suffix, so specs
never depend on each other and can run in parallel.

## Reusing servers

Outside CI (`reuseExistingServer: !process.env.CI`) Playwright reuses whatever
already answers on `http://127.0.0.1:8000/` and `http://localhost:5173/`.
That is handy while iterating (start the stack once with
`node e2e/start-backend.mjs` and `npm run dev`), but note:

* a reused backend must have been started with the environment above
  (`ENV=dev`, `BOOTSTRAP_TOKEN=e2e-bootstrap-token`, ...) or global setup
  cannot create the admin;
* a reused frontend must point at that backend
  (`VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`) — a normal `npm run dev`
  started for development will not;
* the database is only wiped when Playwright starts the backend itself.

## Environment variables

| variable                | default   | meaning                                                                 |
|-------------------------|-----------|-------------------------------------------------------------------------|
| `E2E_PYTHON`            | `python`  | interpreter used to run uvicorn (`..\backend\.venv\Scripts\python.exe` locally) |
| `E2E_KEEP_DB`           | unset     | set to `1` to keep the previous e2e database / uploads                  |
| `E2E_BACKEND_LOG_LEVEL` | `warning` | uvicorn `--log-level` (use `info` to see request logs)                  |
| `CI`                    | unset     | 1 worker, 1 retry, never reuse servers, `test.only` forbidden           |

Artifacts: `playwright-report/` (HTML report), `test-results/` (traces on
first retry, screenshots on failure, `e2e-seed.json`), `backend/e2e_smartaama.db`,
`backend/e2e_uploads/` — all git-ignored.

## How CI runs it

`.github/workflows/ci.yml` (job `e2e`) installs the backend requirements into
the runner's Python, runs `npm ci` and `npx playwright install --with-deps chromium`
in `frontend/`, then `npm run test:e2e` with `E2E_PYTHON=python` and `CI=true`.
The job needs no database service: the backend uses the SQLite file above.

## Ports already in use?

Both ports can be overridden when another dev server occupies 5173/8000 (Playwright would
otherwise reuse the wrong server locally):

```
E2E_BACKEND_PORT=8010 E2E_FRONTEND_PORT=5199 npm run test:e2e
```
