# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import os

from passa.projects import Project

from .lock import lock


def parse_arguments(argv):
    parser = argparse.ArgumentParser("passa-remove")
    parser.add_argument(
        "packages", metavar="package",
        nargs="+",
    )
    dev_group = parser.add_mutually_exclusive_group()
    dev_group.add_argument(
        "--dev", dest="only",
        action="store_const", const="dev",
        help="Only try to remove from [dev-packages]",
    )
    dev_group.add_argument(
        "--default", dest="only",
        action="store_const", const="default",
        help="Only try to remove from [packages]",
    )
    parser.add_argument(
        "--project", dest="project_root",
        default=os.getcwd(),
        type=os.path.abspath,
    )
    options = parser.parse_args(argv)
    return options


def parsed_main(options):
    project = Project(options.project_root)
    project.remove_lines_to_pipfile(
        options.packages,
        default=(options.only != "dev"),
        develop=(options.only != "default"),
    )

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
