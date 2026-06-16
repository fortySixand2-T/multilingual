from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.users.models import Base

# Import models so their tables register on Base.metadata for autogenerate.
import app.assessment.tables  # noqa: E402,F401
import app.comprehension.tables  # noqa: E402,F401
import app.content.tables  # noqa: E402,F401
import app.progress.models  # noqa: E402,F401
import app.srs.models  # noqa: E402,F401
import app.usage.models  # noqa: E402,F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_url() -> str:
    # Alembic uses sync drivers; map the app's async URL to a sync one.
    url = os.getenv("DATABASE_URL", "sqlite:///./data/tef.db")
    return url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg")


def run_migrations_offline() -> None:
    context.configure(url=_sync_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _sync_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
