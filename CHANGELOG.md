# Changelog

All notable changes to SmartAama are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). The current version lives in `VERSION`.

## [Unreleased]

## [0.1.0] - 2026-08-19

First tagged release: the repository after the full audit, remediation and hardening pass.

### Added
- Alembic migration chain (`0001_baseline`, `0002_facilities`, `0003_auth_tokens_rate_limit`);
  `python -m app.db.init_db` stamps pre-Alembic databases and upgrades to head.
- Unified `facilities` directory with foreign keys from users, patients and referrals;
  id-first facility authorization with a legacy name fallback.
- Refresh-token rotation with reuse detection (`POST /auth/refresh`, `POST /auth/logout`);
  tokens revoked on reject / deactivate / role change.
- DB-backed, cross-worker rate limiter for login, register and refresh.
- Rejected registrations (`users.rejected_at`), `GET /admin/users/rejected`, re-approval.
- Role management (`PATCH /admin/users/{id}/role`); `hospital` role assigned at signup for
  hospital facilities; super-admin guards for admin-role targets.
- Structured referral status history (`referral_status_history`, `GET /referrals/{id}/history`);
  receiving-facility status mirrored into the referring status; direction / received-status
  filters on the referral inbox.
- Private ID-card storage with validated uploads and an admin-only retrieval endpoint.
- Rule-based advisory engine (`advisory_rules.py`) with honest metadata
  (`rule-based-advisory-v2`), advisory-language validation and cache invalidation on every
  clinical write.
- Frontend: strict TypeScript, silent token refresh with cross-tab lock, route-level code
  splitting, Playwright end-to-end suite, README screenshots capture.
- GitHub Actions CI (backend on SQLite + PostgreSQL, frontend build, E2E), release
  packaging workflow, `CONTRIBUTING.md`, MIT licence, truthful documentation set.

### Changed
- Every user-returning endpoint serialises an explicit `UserOut` schema (no password hashes).
- `/schema/*` requires authentication; `POST /auth/register`, bootstrap and `/medical-data`
  writes return `201`; login response includes `expires_in` and `refresh_token`; access-token
  default lifetime is 30 minutes.
- Facility names sent to `POST /referrals` / `POST|PATCH /patients` must exist in the directory.
- `/ai-analysis/patient/{id}/...` singular paths renamed to `/ai-analysis/patients/{id}/...`.

### Removed
- Mocked OpenAI/RAG scaffolding, unused heavyweight dependencies, dead modules, stale scripts,
  32 session-log documents and the duplicate pnpm lockfile.

### Security
- Server-side facility scoping on all patient, event, medical-data, referral and advisory
  routes; viewer role is read-only; admin actions audited; no default credentials; bounded,
  validated client-IP handling for audit and rate limiting.

[Unreleased]: https://github.com/uditmahato/smartaama/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/uditmahato/smartaama/releases/tag/v0.1.0
