# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import itertools
import os

from passa.projects import Project

from .lock import lock


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
    lines = list(itertools.chain(
        options.requirement_lines,
        ("-e {}".format(e) for e in options.editable_lines),
    ))
    project = Project(options.project_root)
    project.add_lines_to_pipfile(lines, dev=options.dev)

    success, updated = lock(project)
    if not success:
        return

    project._p.write()
    if updated:
        project._l.write()
    print("Written to project at", project.root)


def main(argv=None):
    options = parse_arguments(argv)
    parsed_main(options)


if __name__ == "__main__":
    main()
