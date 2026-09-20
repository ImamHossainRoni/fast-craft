
"""
Module: core/management/registry.py

Description: Discovers all Command classes defined in core/management/commands/*.py
so manage.py doesn't need to know about them individually.
"""
import importlib
import inspect
import pkgutil

from core.management import commands
from core.management.commands.base import BaseCommand


def discover_commands() -> dict[str, type[BaseCommand]]:
    registry: dict[str, type[BaseCommand]] = {}

    for _, module_name, _ in pkgutil.iter_modules(commands.__path__):
        if module_name == "base":
            continue

        module = importlib.import_module(f"core.management.commands.{module_name}")

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is BaseCommand or not issubclass(obj, BaseCommand):
                continue
            if obj.__module__ != module.__name__:
                continue
            registry[obj.name] = obj

    return registry
