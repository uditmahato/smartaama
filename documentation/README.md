# SmartAama Documentation

Start with the root `README.md` for setup, then use this index. Every file here is
meant to stay truthful to the code in `backend/` and `frontend/`; when the two disagree,
the code wins and the doc should be fixed.

## Index

| Document | What it is for |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture overview: components, data model, request flow, key design decisions (Alembic migrations, rule-based advisory, facility foreign keys with legacy name fallback, refresh tokens, npm). |
| [ACCESS_CONTROL.md](ACCESS_CONTROL.md) | Roles, facility-based authorization (`app/core/authz.py`), the two-column referral status model, endpoint enforcement rules, auth/admin hardening. Marks "implemented" vs "contract". |
| [MEDICAL_SCHEMA.md](MEDICAL_SCHEMA.md) | The clinical data schema (sections, field keys, types, units), the `/schema` and `/medical-data` APIs, and how the frontend consumes them. |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Developer cheat sheet: ports (backend 8000, frontend 5173), env vars, run/test commands, API map, referral status transitions, common code snippets, debugging checklist. |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | How to run the automated tests (`backend/tests`, `npm run typecheck`, `npm run build`), plus manual QA scenarios for facility access, referrals, auth/admin, and the advisory cards. |
| [AI_FEATURES_README.md](AI_FEATURES_README.md) | **Implemented.** The rule-based advisory engine (`backend/app/services/advisory_rules.py`): inputs, thresholds, risk levels, endpoints, response shape, storage/invalidation, frontend cards, limitations. No LLM/RAG. |
| [MATERNAL_RISK_SCORING_FRAMEWORK.md](MATERNAL_RISK_SCORING_FRAMEWORK.md) | **Design reference — not implemented.** A 10-factor clinical scoring proposal kept as domain reference; the backend does not compute it. |
| [RISK_SCORING_QUICK_REFERENCE.md](RISK_SCORING_QUICK_REFERENCE.md) | **Design reference — not implemented.** One-page summary of the same proposal, with pointers to what actually runs. |

## Documentation policy

- **No session logs.** Completion reports, "what I did today" summaries, before/after
  write-ups and celebratory status pages do not belong in this folder. Put that
  narrative in the pull request or commit message. Earlier session logs were removed
  in the 2026 documentation clean-up.
- **Keep docs truthful.** Do not describe features that do not exist (there is no
  LLM/GPT integration, no RAG or vector database, no Celery, no docker-compose). Verify ports, env var names and endpoint paths against the code before
  writing them down. Prefer "as implemented" statements; label planned behaviour as
  such.
- **Design references live in clearly labelled files.** Clinical or scoring references
  (e.g. `MATERNAL_RISK_SCORING_FRAMEWORK.md`) say what the rules are; implementation
  docs say where the code is. Do not mix a design proposal into an implementation doc
  without labelling it.
- **One topic, one file.** Extend an existing document rather than adding a parallel
  one; add a row to the index above when a new document is genuinely needed.
- **Dates:** avoid dates in prose unless they matter; example payload timestamps are
  fine.
