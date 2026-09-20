#! python
# -*- coding: utf-8 -*-

"""
Module: management/commands/base.py

Description: Base class every management command subclasses. Each command
module must define exactly one BaseCommand subclass with a 'name' attribute;
it is auto-discovered by management/registry.py.
"""
import argparse


class BaseCommand:
    name: str = ""
    help: str = ""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Override to add command-specific arguments."""

    def handle(self, args: argparse.Namespace) -> None:
        raise NotImplementedError
