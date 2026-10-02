import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from core.db import Base
from core.management.migrations import load_models, split_by_app, table_owners

"""
Module: migrations/env.py

Description: Alembic environment used by `manage.py makemigrations/migrate`.
Every apps/<app>/models.py is imported automatically, like Django's model discovery,
and autogenerate only looks at the tables of the app being migrated.
"""

load_models()
target_metadata = Base.metadata
selected_apps = context.config.attributes.get("apps")
# makemigrations points new apps at a blank database, so they get a full 0001_initial
database_url = context.config.attributes.get("url", settings.DATABASE_URL)
owners = table_owners()


def _table_name(obj, type_, name):
    if type_ == "table":
        return name
    table = getattr(obj, "table", None)
    return table.name if table is not None else None


def _include_object(obj, name, type_, reflected, compare_to):
    if not selected_apps:
        return True
    table = _table_name(obj, type_, name)
    # tables of other apps, and unknown tables in the DB, are left alone
    return table is None or owners.get(table) in selected_apps


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=settings.DATABASE_URL.startswith("sqlite"),
        include_object=_include_object,
        process_revision_directives=split_by_app(context.script, context.config),
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(url=database_url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
