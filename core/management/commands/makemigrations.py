"""
Module: management/commands/makemigrations.py

Description: Detects model changes and writes new migration files, one folder per app
(migrations/<app>/0001_initial.py, 0002_..., ...).

Apps that already have migrations are compared against the database; apps without
any are compared against a blank one, so they always get a full 0001_initial.

Usage:
    python manage.py makemigrations                        # every app with changes
    python manage.py makemigrations users                  # only the users app
    python manage.py makemigrations users -m "add phone"
    python manage.py makemigrations users --empty -m "backfill data"
"""
import argparse
import os
import sys
import tempfile
from typing import List, Optional

from alembic import command
from alembic.util import CommandError

from core.management.commands.base import BaseCommand
from core.management.migrations import (
    app_head,
    app_migrations_dir,
    app_revisions,
    get_alembic_config,
    get_script,
    load_models,
)


class MakeMigrationsCommand(BaseCommand):
    name = "makemigrations"
    help = "Create new migrations from model changes, per app"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("apps", nargs="*", help="App names (default: all apps)")
        parser.add_argument("-m", "--message", type=str, help="Short description used in the file name")
        parser.add_argument("--empty", action="store_true", help="Create an empty migration to fill in by hand")

    def handle(self, args: argparse.Namespace) -> None:
        known = load_models()
        unknown = [app for app in args.apps if app not in known]
        if unknown:
            sys.exit(f"❌ No app with a models.py named: {', '.join(unknown)}")
        if args.empty and len(args.apps) != 1:
            sys.exit("❌ --empty needs exactly one app, e.g. makemigrations users --empty")

        selected = args.apps or known
        script = get_script(get_alembic_config())
        tracked = [app for app in selected if app_revisions(script, app)]
        new = [app for app in selected if app not in tracked]

        created = []
        try:
            if args.empty:
                created += self._revision(selected, args, empty=True)
            else:
                # tracked apps first: diffing them needs the database at the latest heads,
                # which new files from the blank-database pass would break
                if tracked:
                    created += self._revision(tracked, args)
                if new:
                    with tempfile.TemporaryDirectory() as tmp:
                        created += self._revision(new, args, blank_url=f"sqlite+aiosqlite:///{tmp}/blank.db")
        except CommandError as err:
            if "not up to date" in str(err):
                sys.exit("❌ The database has unapplied migrations. Run `python manage.py migrate` first.")
            sys.exit(f"❌ {err}")

        if not created:
            print("No changes detected.")
            return
        for path in created:
            print(f"➡️ Created {os.path.relpath(path)}")
        print("   Review them, then run: python manage.py migrate")

    def _revision(self, apps: List[str], args: argparse.Namespace, empty: bool = False,
                  blank_url: Optional[str] = None) -> List[str]:
        new_dirs = [app for app in apps if not os.path.isdir(app_migrations_dir(app))]
        for app in new_dirs:
            os.makedirs(app_migrations_dir(app))
        try:
            cfg = get_alembic_config()
            cfg.set_main_option("file_template", "%%(rev)s_%%(slug)s")
            cfg.attributes.update(apps=apps, autogenerate=not empty, message=args.message)
            if blank_url:
                cfg.attributes["url"] = blank_url
                command.stamp(cfg, "heads")  # blank DB "has" every existing migration, but none of the new apps' tables

            # an --empty migration never reaches autogenerate, so Alembic needs its base up front
            head = (app_head(get_script(cfg), apps[0]) or "base") if empty else "heads"
            scripts = command.revision(cfg, message=args.message, autogenerate=not empty, head=head)
        finally:
            for app in new_dirs:
                if not os.listdir(app_migrations_dir(app)):
                    os.rmdir(app_migrations_dir(app))

        if cfg.attributes.get("no_changes") or not scripts:
            return []
        return [self._drop_app_prefix(s.path) for s in (scripts if isinstance(scripts, list) else [scripts])]

    @staticmethod
    def _drop_app_prefix(path: str) -> str:
        """users_0001_initial.py -> 0001_initial.py (the revision id keeps the app prefix)."""
        folder, filename = os.path.split(path)
        new_path = os.path.join(folder, filename[len(os.path.basename(folder)) + 1:])
        os.rename(path, new_path)
        return new_path
