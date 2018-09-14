# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import os
import sys

import tomlkit.exceptions

from .options import project


def build_project(root):
    # This is imported lazily to reduce import overhead. Not evey command
    # needs the project instance.
    from passa.internals.projects import Project
    root = os.path.abspath(root)
    if not os.path.isfile(os.path.join(root, "Pipfile")):
        raise argparse.ArgumentError(
            "{0!r} is not a Pipfile project".format(root),
        )
    try:
        project = Project(root)
    except tomlkit.exceptions.ParseError as e:
        raise argparse.ArgumentError(
            "failed to parse Pipfile: {0!r}".format(str(e)),
        )
    return project


# Better error reporting. Recent argparse would emit something like
# "invalid project root value: 'xxxxxx'". The str() wrapper is needed to
# keep Python 2 happy :(
build_project.__name__ = str("project root")


class BaseCommand(object):
    """A CLI command.
    """
    name = None
    description = None
    parsed_main = None
    arguments = []

    def __init__(self, parser=None):
        if not parser:
            parser = argparse.ArgumentParser(
                prog=os.path.basename(sys.argv[0]),
                description="Base argument parser for passa"
            )
        self.parser = parser
        self.default_aguments = [project]
        self.add_arguments()

    @classmethod
    def build_parser(cls):
        parser = argparse.ArgumentParser(
            prog="passa {}".format(cls.name),
            description=cls.description,
        )
        return cls(parser)

    @classmethod
    def run_parser(cls):
        parser = cls.build_parser()
        parser()

    def __call__(self, argv=None):
        options = self.parser.parse_args(argv)
        result = self.main(options)
        if result is not None:
            sys.exit(result)

    def add_default_arguments(self):
        for arg in self.default_aguments:
            arg.add_to_parser(self.parser)

    def add_arguments(self):
        self.add_default_arguments()
        for arg in self.arguments:
            arg.add_to_parser(self.parser)

    def main(self, options):
        return self.run(options)

    def run(self, options):
        raise NotImplementedError
