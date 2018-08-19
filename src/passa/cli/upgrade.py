# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import os

from passa.projects import Project

from .lock import lock


def parse_arguments(argv):
    parser = argparse.ArgumentParser("passa-upgrade")
    parser.add_argument(
        "packages", metavar="package",
        nargs="+",
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
    changed = project.remove_entries_from_lockfile(options.packages)

    if changed:     # Remove the hash to trigger re-locking.
        project.lockfile.meta.hash = None

    success, updated = lock(project)
    if not success:
        return

    if updated:
        project._l.write()
    print("Written to project at", project.root)


def main(argv=None):
    options = parse_arguments(argv)
    parsed_main(options)


if __name__ == "__main__":
    main()
