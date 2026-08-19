# Testing Guide

Three layers:

1. **Automated backend tests** - `backend/tests/` (pytest, SQLite by default,
   `TEST_DATABASE_URL` for PostgreSQL). Coverage is intentionally focused: the app boots
   and core routes respond, security/authorization (role and facility boundaries, no
   `password_hash` leakage, bootstrap/rate-limit gates, refresh-token rotation and
   revocation), referral state machines and history, migration parity (`alembic check`),
   and pure-function tests for the rule-based advisory engine.
2. **Frontend checks and browser end-to-end tests** - `npm run typecheck`, `npm run build`
   and the Playwright suite `npm run test:e2e` (`frontend/e2e/`, see its README): five
   user journeys (login, signup + approval, patient creation, record update -> advisory,
   referral flow) against a throw-away SQLite backend and the Vite dev server.
3. **Manual QA scenarios** - the walkthroughs below, for anything the automated tests do
   not exercise (edge UI states, multi-user flows).

## 1. Automated tests

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

- Runs against SQLite by default (no PostgreSQL required). Set `TEST_DATABASE_URL` to a
  PostgreSQL URL to run the same suite against Postgres.
- `backend/pytest.ini` sets `pythonpath = .` and `testpaths = tests`.
- `tests/conftest.py` builds the schema with `Base.metadata.create_all`, overrides
  `get_db`, and provides fixtures for users of each role in facilities such as
  "PHC A", "PHC B", "Hospital X" plus a login helper returning bearer headers.
- The pure rule tests (`tests/test_risk_rules.py`) need no database; the service/endpoint
  risk tests use the same SQLite fixtures as the rest of the suite.

Frontend:

```powershell
cd frontend
npm run typecheck      # tsc --noEmit
npm run build          # tsc --noEmit && vite build
```

Both must pass before a change is considered done. There are no frontend unit tests;
browser coverage comes from the Playwright suite:

```
npx playwright install chromium   # once
npm run test:e2e                  # starts backend (SQLite) + frontend itself; see frontend/e2e/README.md
```

## 2. Manual QA setup

- Backend on `http://localhost:8000`, frontend on `http://localhost:5173`.
- Database initialised: `python -m app.db.init_db`.
- `backend/.env` has `ENV=dev`, a `SECRET_KEY` (>= 32 chars), `DATABASE_URL`, and a
  `BOOTSTRAP_TOKEN` (needed once, to create the first admin).
- Users: create at least one admin (via `/auth/bootstrap-admin` with header
  `X-Bootstrap-Token: <BOOTSTRAP_TOKEN>`, or `python -m app.scripts.create_super_admin`
  with `SUPER_ADMIN_USERNAME/EMAIL/PASSWORD` set), then register and approve:
  - `phc_user` - role `clinician`, facility "PHC A"
  - `hospital_user` - role `hospital`, facility "Hospital X"
  - `other_user` - role `clinician`, facility "PHC B"
  - optionally `viewer_user` - role `viewer`, facility "PHC A"
- Passwords must be at least 10 characters. Approve new users under Admin > Pending.

Handy curl (replace `<token>`):

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=phc_user&password=<password>"

curl http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer <token>"
curl "http://localhost:8000/api/v1/referrals?direction=incoming" -H "Authorization: Bearer <token>"
```

## 3. Scenarios: facility access and referrals

### S1 - PHC registers a patient and refers to hospital

1. Log in as `phc_user`. Create a patient. Confirm the patient appears in the patient
   list and `GET /patients/{id}` returns `registered_facility_name = "PHC A"`.
2. Add clinical data (Update Record) - e.g. vitals and blood investigations.
3. Refer the patient to "Hospital X" with a reason. `from_facility` must be the user's
   own facility (the API rejects other values for non-admins).
4. Dashboard shows the referral under "Referred from Here" (`direction=outgoing`).
5. Patient profile still shows the "Update Record" button.

### S2 - Hospital receives the referral

1. Log in as `hospital_user`. Dashboard shows the referral under "Referred to Here"
   (`direction=incoming`).
2. Open the patient: full profile and clinical data are visible. The read-only banner
   is shown and "Update Record" is hidden (UX convention for a receiving-only facility).
3. Open the referral. Set the receiving status to "Admitted Here" (`received`) with a
   note. Verify:
   - `received_facility_status = received`, `status` unchanged (`submitted`).
   - `GET /referrals/{id}/history` contains a `received_status` entry with the note and
     actor.
   - Dashboard filter "Admitted Case" now lists it.
4. Try to change the *referring* status from this account (`POST /referrals/{id}/status`)
   - expect 403.

### S3 - PHC sees the update and closes

1. Log in as `phc_user`, open the referral. The receiving status, note and history are
   visible.
2. Note that after the hospital marked the case admitted (S2), the PHC's own `status`
   already shows `received` - the receiving facility's acknowledgement is mirrored into
   the referring-side status. From the PHC, use "Your status" to move `received -> closed`
   (or, while still `submitted`, to `cancelled`). Verify timestamps and history entries
   (mirrored rows carry the note "Updated automatically from the receiving facility's
   status"). Attempt an invalid transition via the API (e.g. `closed -> submitted`) -
   expect 400.
3. As `hospital_user`, try `received_facility_status: submitted` - expect 400 (not an
   allowed value); `closed` after `received` succeeds (and mirrors `status=closed`);
   anything after `closed` - 400.

### S4 - Boundaries

1. `other_user` (PHC B): patient list does not include the patient; `GET /patients/{id}`
   returns 403; `GET /referrals` does not include the referral; `GET /referrals/{id}`
   returns 403; `POST /referrals` for that patient returns 403.
2. `viewer_user`: can read the patient and referrals, but `POST /medical-data/...`,
   `POST /events`, `POST /referrals`, advisory generate/delete all return 403.
3. `GET /referrals?from_facility=PHC%20A` as `other_user` still returns nothing (facility
   filters never widen a non-admin's scope).
4. Admin sees everything and may `PATCH /patients/{id}` `registered_facility_name`.

### S5 - Auth and admin

1. Register with a 6-character password - expect 422. Register properly - the account
   is pending; login returns 401/403 until approved.
2. `GET /admin/users` as admin: no `password_hash` in the JSON. Approve/reject/delete
   each create an audit log row; deleted users disappear from lists (soft delete). An
   admin cannot delete themselves; only a super-admin can delete another admin.
3. ID card: `GET /admin/users/{id}/id-card` returns the image for admins, 403 for
   others, 404 when none was uploaded. Upload a `.exe` or a 6 MB image at registration
   - expect 400.
4. With `ENV=prod` or empty `BOOTSTRAP_TOKEN`, `/auth/bootstrap-admin` is refused.
5. Hit `/auth/login` more than `RATE_LIMIT_MAX_REQUESTS` times in the window - expect 429.

## 4. Scenarios: rule-based advisory cards

The "Advisory Summary (rule-based)" and "Referral Advisory (rule-based)" cards are
produced by a deterministic, rule-based advisory engine
(`backend/app/services/advisory_rules.py`, used by `risk_engine.py` and
`ai_patient_service.py`). There is no external model. The exact inputs, thresholds and
outputs are documented in `AI_FEATURES_README.md`; check expected outputs against that
file (the two `*RISK_SCORING*` files are a design reference that is **not** what the
code runs).

Open a patient profile, scroll to the two cards, and verify:

| Case | Expect |
|---|---|
| Patient with **no** clinical events | Summary states plainly that no clinical data has been recorded; referral card says no referral suggested; risk level `unknown` |
| Only a *previous referral*, still no clinical data | Same as above - past referrals alone must not trigger a recommendation |
| Normal vitals/labs recorded | No referral needed or low urgency; findings list the actual recorded values |
| Abnormal values (e.g. BP >= 140/90, Hb < 10, proteinuria) | Referral suggested; the reasons name the specific abnormal values and the rule(s) they map to; urgency and the referral score rise with the number/severity of triggers (BP >= 160/110 with proteinuria -> `critical`) |
| Danger-sign / critical rule triggered | Highest urgency; referral required |
| After adding new clinical data | The stored analysis is invalidated and regenerates on next view (or via the refresh button); `last analyzed` timestamp updates |
| Model label | Card / API `model_used` reads as a rule-based advisory version string (e.g. `rule-based-advisory-v2`), never GPT/OpenAI; `/ai/risk` never reports `rag_used: true` |

API spot checks:

```
GET  /api/v1/ai-analysis/patients/{patient_id}/analysis
POST /api/v1/ai-analysis/generate            {"patient_id": "..."}   (clinician/hospital/admin)
GET  /api/v1/ai-analysis/patients/{patient_id}/status
DELETE /api/v1/ai-analysis/patients/{patient_id}                    (clinician/hospital/admin)
```

A user without access to the patient gets 403 on all of them.

## 5. Sign-off checklist

- [ ] `pytest -q` passes (SQLite) and, if available, against `TEST_DATABASE_URL`.
- [ ] `npm run typecheck` and `npm run build` pass.
- [ ] Backend boots on a fresh clone with only `.env` configured (uploads dir is created
      automatically).
- [ ] S1-S5 pass with the four test users.
- [ ] Advisory table in section 4 holds; no UI text claims GPT/LLM output.
- [ ] No `password_hash` or `id_card_image_path` in any API response.
- [ ] Browser console free of errors on Dashboard, Patient Profile, Referral, Admin.
