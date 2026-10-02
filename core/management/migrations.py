import argparse
import asyncio
import importlib
import os
import pkgutil
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Tuple

from alembic.config import Config
from alembic.operations.ops import MigrationScript, UpgradeOps
from alembic.runtime.migration import MigrationContext
from alembic.script import Script, ScriptDirectory
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import create_async_engine

import apps
from config import settings
from core.db import Base

"""
Module: management/migrations.py

Description: Shared Alembic setup for the makemigrations/migrate/showmigrations
commands. Each app is its own Alembic branch (label = app name) whose files live
in migrations/<app>/ and are numbered 0001, 0002, ... like Django.
"""

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATIONS_DIR = os.path.join(PROJECT_ROOT, "migrations")


def load_models() -> List[str]:
    """Import every apps/<app>/models.py and return the app names that have one."""
    found = []
    for _, app_name, is_pkg in pkgutil.iter_modules(apps.__path__):
        if is_pkg and importlib.util.find_spec(f"apps.{app_name}.models"):
            importlib.import_module(f"apps.{app_name}.models")
            found.append(app_name)
    return found


def table_owners() -> Dict[str, str]:
    """{table name: app name}, from which apps.<app>.models module defines it."""
    owners = {}
    for mapper in Base.registry.mappers:
        parts = mapper.class_.__module__.split(".")
        if len(parts) >= 2 and parts[0] == "apps" and mapper.local_table is not None:
            owners[mapper.local_table.name] = parts[1]
    return owners


def app_dependencies(app: str) -> Set[str]:
    """Other apps whose tables this app's tables point at via foreign keys."""
    owners = table_owners()
    deps = set()
    for table_name, owner in owners.items():
        if owner != app:
            continue
        for fk in Base.metadata.tables[table_name].foreign_keys:
            target = owners.get(fk.column.table.name)
            if target and target != app:
                deps.add(target)
    return deps


def ordered_apps(names: List[str]) -> List[str]:
    """Apps sorted so that an app comes after the apps it depends on."""
    ordered, seen = [], set()

    def visit(app: str) -> None:
        if app in seen:
            return
        seen.add(app)
        for dep in sorted(app_dependencies(app)):
            if dep in names:
                visit(dep)
        ordered.append(app)

    for name in sorted(names):
        visit(name)
    return ordered


def app_migrations_dir(app: str) -> str:
    return os.path.join(MIGRATIONS_DIR, app)


def migration_apps() -> List[str]:
    """Apps that already have a migrations/<app>/ folder."""
    if not os.path.isdir(MIGRATIONS_DIR):
        return []
    return sorted(
        name for name in os.listdir(MIGRATIONS_DIR)
        if os.path.isdir(app_migrations_dir(name)) and not name.startswith(("_", "."))
    )


def get_alembic_config() -> Config:
    cfg = Config(cmd_opts=argparse.Namespace(quiet=True))  # commands print their own output
    cfg.set_main_option("script_location", MIGRATIONS_DIR)
    cfg.set_main_option("path_separator", "os")
    cfg.set_main_option("revision_environment", "true")  # run env.py for --empty too
    cfg.set_main_option("version_locations", os.pathsep.join(app_migrations_dir(a) for a in migration_apps()))
    return cfg


def get_script(cfg: Config) -> ScriptDirectory:
    return ScriptDirectory.from_config(cfg)


def app_revisions(script: ScriptDirectory, app: str) -> List[Script]:
    """An app's migrations, oldest first."""
    folder = app_migrations_dir(app)
    revs = [rev for rev in script.walk_revisions() if os.path.dirname(rev.path) == folder]
    return sorted(revs, key=lambda rev: rev.revision)


def app_head(script: ScriptDirectory, app: str) -> Optional[str]:
    revs = app_revisions(script, app)
    return revs[-1].revision if revs else None


def next_number(script: ScriptDirectory, app: str) -> int:
    return len(app_revisions(script, app)) + 1


def revision_id(app: str, number: int) -> str:
    return f"{app}_{number:04d}"


def migration_name(rev: Script) -> str:
    return os.path.splitext(os.path.basename(rev.path))[0]


def split_by_app(script: ScriptDirectory, config: Config) -> Callable:
    """process_revision_directives hook: turns one autogenerate pass into one
    migration per app (migrations/<app>/NNNN_...), linked by FK dependencies."""

    def process(context, revision, directives) -> None:
        selected = config.attributes.get("apps")
        if not selected:
            return
        base = directives[0]
        autogenerate = config.attributes.get("autogenerate")

        groups: Dict[str, list] = {app: [] for app in selected}
        if autogenerate:
            owners = table_owners()
            for op in base.upgrade_ops.ops:
                owner = owners.get(getattr(op, "table_name", None))
                if owner in groups:
                    groups[owner].append(op)

        scripts, new_heads = [], {}
        for app in ordered_apps(selected):
            if autogenerate and not groups[app]:
                continue
            number = next_number(script, app)
            head = app_head(script, app)
            rev_id = revision_id(app, number)
            depends_on = [new_heads.get(dep) or app_head(script, dep) for dep in sorted(app_dependencies(app))]
            upgrade_ops = UpgradeOps(ops=groups[app])
            scripts.append(MigrationScript(
                rev_id,
                upgrade_ops,
                upgrade_ops.reverse(),
                message=config.attributes.get("message") or ("initial" if number == 1 else f"auto_{datetime.now():%Y%m%d_%H%M}"),
                imports=base.imports,
                head=head or "base",
                branch_label=None if head else app,
                version_path=app_migrations_dir(app),
                depends_on=[dep for dep in depends_on if dep] or None,
            ))
            new_heads[app] = rev_id

        directives[:] = scripts
        if not scripts:
            config.attributes["no_changes"] = True

    return process


def resolve_target(app: str, target: str) -> str:
    """Django-style target ('0002', '2', 'zero') -> Alembic revision id."""
    if target == "zero":
        return f"{app}@base"
    number = target.split("_")[0]
    return revision_id(app, int(number)) if number.isdigit() else target


async def _with_connection(fn):
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.run_sync(fn)
    await engine.dispose()
    return result


def current_heads() -> Tuple[str, ...]:
    """Revisions the database is at right now (one per migrated app)."""
    return asyncio.run(_with_connection(lambda c: MigrationContext.configure(c).get_current_heads()))


def existing_tables() -> Set[str]:
    return set(asyncio.run(_with_connection(lambda c: sa_inspect(c).get_table_names())))


def applied_revisions(script: ScriptDirectory) -> Set[str]:
    heads = current_heads()
    if not heads:
        return set()
    return {rev.revision for rev in script.iterate_revisions(heads, "base")}
