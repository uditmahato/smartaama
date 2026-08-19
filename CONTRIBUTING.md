# Contributing to SmartAama

Thanks for your interest. SmartAama handles maternal-health records, so correctness,
security and honesty in documentation matter more than speed. This page tells you how
to set up, what we expect in a change, and how it is verified.

## Development setup

Follow the root [README](README.md): backend (Python 3.11+, virtualenv,
`pip install -r requirements.txt`, `.env` from `.env.example`, `python -m app.db.init_db`),
frontend (Node 20+, `npm install`, `npm run dev`). PostgreSQL is needed to run the app;
the automated tests run on SQLite without any database server.

## Before opening a pull request

Run all of these — CI runs the same commands (`.github/workflows/ci.yml`):

```bash
cd backend && python -m pytest -q
```

```bash
cd frontend && npm run typecheck && npm run build
```

```bash
cd frontend && npm run test:e2e        # browser tests; see frontend/e2e/README.md
```

If you change the database schema:

1. Edit the SQLAlchemy models.
2. `cd backend && alembic revision --autogenerate -m "short description" --rev-id 000N_short_slug` and review the
   generated file — keep it portable (SQLite and PostgreSQL both run the migrations; use
   `op.batch_alter_table` for ALTERs and portable column types).
3. `alembic upgrade head` locally, and make sure `python -m app.db.init_db` still works
   on an empty database.

## What we look for

- **Security first.** Every route that touches patient or referral data must go through
  the helpers in `backend/app/core/authz.py`; roles come from `core/permissions.py`.
  Never return ORM objects directly — use explicit Pydantic response models. Never log or
  return password hashes, tokens or ID-card paths.
- **Advisory, not diagnostic.** Anything the advisory engine emits must pass
  `app/ai/validators.py` (no "must", "administer", "diagnose", …) and stay clearly labelled
  as advisory. Do not describe the engine as AI/LLM-based; it is rule-based.
- **Truthful docs.** If you change behaviour, update `README.md` and the relevant file in
  `documentation/` in the same PR. Do not add session logs or "completion reports".
- **Tests for security-relevant changes.** Authorization, authentication, and data-integrity
  changes need a test in `backend/tests/`.
- **Small, reviewable PRs** with a clear description of what changed and why.

## Commit / PR hygiene

- Branch from `main`; open a PR against `main`.
- Commits are authored by humans under their own identity.
- Do not commit `.env`, uploads, databases, or build output (see `.gitignore`).

## Licence

By contributing you agree that your contributions are licensed under the repository's
[MIT License](LICENSE).

## Reporting security issues

Please do **not** open a public issue for a vulnerability. Contact the maintainers listed
in the README's *Contributors* section directly, describe the issue and how to reproduce
it, and allow reasonable time for a fix before disclosure.
