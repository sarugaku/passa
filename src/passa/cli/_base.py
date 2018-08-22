# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import os
import sys


class BaseCommand(object):
    """A CLI command.
    """
    parsed_main = None

    def __init__(self, parser):
        self.parser = parser
        self.add_arguments()

    @classmethod
    def run_current_module(cls):
        module = sys.modules[cls.__module__]
        parser = argparse.ArgumentParser(
            prog="passa {}".format(module.NAME),
            description=module.DESC,
        )
        cls(parser)()

    def __call__(self, argv=None):
        options = self.parser.parse_args(argv)
        result = self.main(options)
        if result is not None:
            sys.exit(result)

    def add_arguments(self):
        self.parser.add_argument(
            "--project",
            dest="project_root", metavar="project",
            default=os.getcwd(),
            type=os.path.abspath,
            help="path to project root (directory containing Pipfile)",
        )

    def main(self, options):
        return type(self).parsed_main(options)
