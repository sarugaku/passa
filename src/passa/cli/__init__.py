# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import sys

from passa import __version__


def main(argv=None):
    root_parser = argparse.ArgumentParser(
        prog="passa",
        description="Pipfile project management tool.",
    )
    root_parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s, version {}".format(__version__),
        help="show the version and exit",
    )

    # This needs to be imported locally, otherwise there would be an import
    # order mismatch when we run a passa.cli.[subcommand] module directly.
    from . import add, lock, remove, upgrade

    subparsers = root_parser.add_subparsers()
    for module in [add, remove, upgrade, lock]:
        klass = module.Command
        parser = subparsers.add_parser(klass.name, help=klass.description)
        command = klass(parser)
        parser.set_defaults(func=command.main)

    options = root_parser.parse_args(argv)

    try:
        f = options.func
    except AttributeError:
        root_parser.print_help()
        result = -1
    else:
        result = f(options)
    if result is not None:
        sys.exit(result)
