# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import os
import sys


DEFAULT = "__default__"


# Classes here are intentionally imported lazily to reduce import overhead.
# Not evey command needs those instances.


def build_project(root):
    from passa.internals.projects import Project
    return Project(os.path.abspath(root))


def build_spinner_reporter(value):
    from passa.reporters import SpinnerReporter
    return SpinnerReporter()


class SetStdOutReporterAction(argparse.Action):
    def __call__(self, parser, options, values, flag=None):
        from passa.reporters import StdOutReporter
        options.reporter = StdOutReporter()


class BaseCommand(object):
    """A CLI command.
    """
    name = None
    description = None
    parsed_main = None

    def __init__(self, parser):
        self.parser = parser
        self.add_arguments()

    @classmethod
    def run_current_module(cls):
        parser = argparse.ArgumentParser(
            prog="passa {}".format(cls.name),
            description=cls.description,
        )
        cls(parser)()

    def __call__(self, argv=None):
        options = self.parser.parse_args(argv)
        result = self.main(options)
        if result is not None:
            sys.exit(result)

    def add_arguments(self):
        self.parser.add_argument(
            "--project", metavar="project",
            default=os.getcwd(),
            type=build_project,
            help="path to project root (directory containing Pipfile)",
        )
        self.parser.add_argument(
            "--verbose", dest="reporter",
            nargs=0, action=SetStdOutReporterAction, default=DEFAULT,
            type=build_spinner_reporter,
            help="path to project root (directory containing Pipfile)",
        )

    def main(self, options):
        # This __dict__ access is needed for Python 2 to prevent Python from
        # wrapping parsed_main into an unbounded method.
        return type(self).__dict__["parsed_main"](options)
