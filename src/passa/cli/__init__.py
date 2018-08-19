# -*- coding=utf-8 -*-

# TODO: Rewrite this into passa.cli.lock.

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import os

from passa.projects import Project
from passa.reporters import print_title

from .lock import lock


def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "project_root",
        type=os.path.abspath,
    )
    parser.add_argument(
        "--output",
        choices=["write", "print", "none"],
        default="print",
        help="How to output the lockfile",
    )
    return parser.parse_args(argv)


def parsed_main(options):
    project = Project(options.project_root)

    success, updated = lock(project, force=True)
    if not success:
        return

    if options.output == "write":
        if updated:
            project._l.write()
            print("Lock file written to", project._l.location)
        else:
            print("Not updating identical lock file")
    if options.output == "print":
        print_title(" LOCK FILE ")
        print(project._l.dumps())


def main(argv=None):
    options = parse_arguments(argv)
    parsed_main(options)


if __name__ == "__main__":
    main()
