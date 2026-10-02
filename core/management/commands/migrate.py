"""
Module: management/commands/migrate.py

Description: Applies (or rolls back) migrations against DATABASE_URL, Django-style.

Usage:
    python manage.py migrate                   # apply everything
    python manage.py migrate users             # apply all of users' migrations
    python manage.py migrate users 0002        # move users to 0002 (up or down)
    python manage.py migrate users zero        # roll back all of users' migrations
    python manage.py migrate --fake            # mark as applied without running
    python manage.py migrate --fake-initial    # skip 0001s whose tables already exist
"""
import argparse
import os
import re
import sys

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util import CommandError
from sqlalchemy.exc import DBAPIError

from core.management.commands.base import BaseCommand
from core.management.migrations import (
    app_revisions,
    applied_revisions,
    existing_tables,
    get_alembic_config,
    get_script,
    load_models,
    migration_apps,
    migration_name,
    ordered_apps,
    resolve_target,
)


class MigrateCommand(BaseCommand):
    name = "migrate"
    help = "Apply migrations to the database"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("app", nargs="?", help="Only migrate this app")
        parser.add_argument("target", nargs="?", help="Migration number to move to, or 'zero'")
        parser.add_argument("--fake", action="store_true", help="Mark as applied without running")
        parser.add_argument("--fake-initial", action="store_true", help="Mark 0001 as applied if its tables already exist")

    def handle(self, args: argparse.Namespace) -> None:
        if args.app and args.app not in migration_apps():
            sys.exit(f"❌ App '{args.app}' has no migrations. Run: python manage.py makemigrations {args.app}")

        cfg = get_alembic_config()
        target = self._target(args)
        try:
            if args.fake_initial:
                self._fake_initial(cfg, args.app)
            if args.fake:
                command.stamp(cfg, target)
                print(f"➡️ Marked {target} as applied (fake).")
                return

            script = get_script(cfg)
            before = applied_revisions(script)
            if self._is_downgrade(script, args.app, target):
                command.downgrade(cfg, target)
            else:
                command.upgrade(cfg, target)
            after = applied_revisions(script)
        except CommandError as err:
            sys.exit(f"❌ {err}")
        except DBAPIError as err:
            if "already exists" in str(err.orig):
                sys.exit(f"❌ {err.orig}\n   The tables already exist. If they match the models, run: python manage.py migrate --fake-initial")
            raise
        self._report(script, before, after)

    @staticmethod
    def _report(script: ScriptDirectory, before: set, after: set) -> None:
        if before == after:
            print("No migrations to apply.")
            return
        load_models()
        for app in ordered_apps(migration_apps()):
            for rev in app_revisions(script, app):
                if rev.revision in after - before:
                    print(f"  Applying {app}.{migration_name(rev)}... OK")
                elif rev.revision in before - after:
                    print(f"  Unapplying {app}.{migration_name(rev)}... OK")

    @staticmethod
    def _target(args: argparse.Namespace) -> str:
        if not args.app:
            return "heads"
        if not args.target:
            return f"{args.app}@head"
        return resolve_target(args.app, args.target)

    @staticmethod
    def _is_downgrade(script: ScriptDirectory, app: str, target: str) -> bool:
        if target.endswith("@base"):
            return True
        if not app or "@" in target:
            return False
        applied = applied_revisions(script)
        applied_here = [rev.revision for rev in app_revisions(script, app) if rev.revision in applied]
        return target in applied_here and applied_here[-1] != target

    @staticmethod
    def _fake_initial(cfg: Config, only_app: str = None) -> None:
        script = get_script(cfg)
        applied = applied_revisions(script)
        tables = existing_tables()
        load_models()
        to_fake = []
        for app in [only_app] if only_app else ordered_apps(migration_apps()):
            revs = app_revisions(script, app)
            if not revs or revs[0].revision in applied:
                continue
            with open(revs[0].path) as f:
                created = set(re.findall(r"op\.create_table\(\s*['\"](\w+)['\"]", f.read()))
            if created and created <= tables:
                to_fake.append(revs[0])
        if not to_fake:
            return
        faked = {rev.revision for rev in to_fake}
        ancestors = {
            rev.revision: {a.revision for a in script.iterate_revisions(rev.revision, "base")} - {rev.revision}
            for rev in to_fake
        }
        # can't fake a migration whose dependencies are neither applied nor faked
        to_fake = [rev for rev in to_fake if ancestors[rev.revision] <= applied | faked]
        # stamp only the tips; a stamped revision implies everything it depends on
        implied = set().union(*(ancestors[rev.revision] for rev in to_fake))
        command.stamp(cfg, [rev.revision for rev in to_fake if rev.revision not in implied])
        for rev in to_fake:
            print(f"  Faking {os.path.basename(os.path.dirname(rev.path))}.{migration_name(rev)} (tables already exist)... OK")
