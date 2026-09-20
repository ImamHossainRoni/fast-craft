"""
Module: manage.py

Description: CLI entrypoint. Actual commands live in core/management/commands/;
this file only discovers and dispatches them.

Usage:
    python manage.py <command> [args...]
"""
import argparse

from core.management import discover_commands


def main() -> None:
    parser = argparse.ArgumentParser(description="Management utility for the project.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands = discover_commands()

    for name, command_cls in commands.items():
        command = command_cls()
        subparser = subparsers.add_parser(name, help=command.help)
        command.add_arguments(subparser)
        subparser.set_defaults(_command=command)

    args = parser.parse_args()
    args._command.handle(args)


if __name__ == "__main__":
    main()
