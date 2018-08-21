# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import itertools
import os
import sys


def parse_arguments(argv):
    parser = argparse.ArgumentParser("passa-add")
    parser.add_argument(
        "requirement_lines", metavar="requirement",
        nargs="*",
    )
    parser.add_argument(
        "-e", "--editable",
        metavar="requirement", dest="editable_lines",
        action="append", default=[],
    )
    parser.add_argument(
        "--dev",
        action="store_true",
    )
    parser.add_argument(
        "--project", dest="project_root",
        default=os.getcwd(),
        type=os.path.abspath,
    )
    options = parser.parse_args(argv)
    if not options.editable_lines and not options.requirement_lines:
        parser.error("Must supply either a requirement or --editable")
    return options


def parsed_main(options):
    from passa.lockers import PinReuseLocker
    from passa.projects import Project
    from .lock import lock

    lines = list(itertools.chain(
        options.requirement_lines,
        ("-e {}".format(e) for e in options.editable_lines),
    ))

    project = Project(options.project_root)
    for line in lines:
        try:
            project.add_line_to_pipfile(line, develop=options.dev)
        except (TypeError, ValueError) as e:
            print("Cannot add {line!r} to Pipfile: {error}".format(
                line=line, error=str(e),
            ), file=sys.stderr)
            return 2

    locker = PinReuseLocker(project)
    success = lock(locker)
    if not success:
        return 1

    project._p.write()
    project._l.write()
    print("Written to project at", project.root)


if __name__ == "__main__":
    from ._base import Command
    command = Command(parse_arguments, parsed_main)
    command()
