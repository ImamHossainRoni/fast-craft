"""
Module: management/commands/showmigrations.py

Description: Lists each app's migrations, marking the applied ones with [X].

Usage:
    python manage.py showmigrations
    python manage.py showmigrations users
"""
import argparse

from core.management.commands.base import BaseCommand
from core.management.migrations import (
    app_revisions,
    applied_revisions,
    get_alembic_config,
    get_script,
    migration_apps,
    migration_name,
)


class ShowMigrationsCommand(BaseCommand):
    name = "showmigrations"
    help = "List migrations per app and whether they are applied"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("apps", nargs="*", help="App names (default: all apps)")

    def handle(self, args: argparse.Namespace) -> None:
        names = args.apps or migration_apps()
        if not names:
            print("No migrations yet. Run: python manage.py makemigrations")
            return

        script = get_script(get_alembic_config())
        applied = applied_revisions(script)
        for app in names:
            print(app)
            revs = app_revisions(script, app)
            if not revs:
                print(" (no migrations)")
            for rev in revs:
                mark = "X" if rev.revision in applied else " "
                print(f" [{mark}] {migration_name(rev)}")
