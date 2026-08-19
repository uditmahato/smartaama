# backend/alembic/env.py
"""
Alembic environment for SmartAama.

- The database URL comes from app.core.config.settings.DATABASE_URL (env var / backend/.env),
  never from alembic.ini, so the same migrations run against PostgreSQL (production) and SQLite
  (tests / quick local runs).
- `target_metadata` is app.db.base.Base.metadata (importing app.db.base registers every model).
- `render_as_batch` is enabled on SQLite so ALTER TABLE operations are emitted as
  batch ("move and copy") operations; `compare_type=True` so column type drift is detected.
- app.db.init_db runs these migrations programmatically and hands over an already-open
  connection via `config.attributes["connection"]`; the CLI path opens its own engine.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

# Make `app` importable no matter where alembic is invoked from (backend/ is the package root).
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402  (registers all models on Base.metadata)

config = context.config

# Only configure logging when running from the CLI with an ini file (init_db passes none).
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    # `-x url=...` on the CLI or a programmatic sqlalchemy.url override wins; otherwise settings.
    return (
        context.get_x_argument(as_dictionary=True).get("url")
        or config.get_main_option("sqlalchemy.url")
        or settings.DATABASE_URL
    )


def _configure(connection: Connection | None, url: str | None) -> None:
    dialect_name = connection.dialect.name if connection is not None else (url or "").split(":", 1)[0]
    kwargs = dict(
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=False,
        render_as_batch=dialect_name.startswith("sqlite"),
    )
    if connection is not None:
        context.configure(connection=connection, **kwargs)
    else:
        context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"}, **kwargs)


def run_migrations_offline() -> None:
    """
    Offline (`--sql`) mode is NOT supported: revisions such as 0002_facilities run data
    migrations that read from the database, which is impossible when only emitting SQL.
    Run migrations online (`alembic upgrade head` / `python -m app.db.init_db`).
    """
    raise RuntimeError(
        "SmartAama migrations include data steps and cannot run in offline --sql mode; "
        "run `alembic upgrade head` against a live database instead."
    )


def run_migrations_online() -> None:
    """Run migrations against a live connection (CLI or the one handed over by init_db)."""
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure(connection, None)
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            _configure(conn, None)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
