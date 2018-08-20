# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import os


def parse_arguments(argv):
    parser = argparse.ArgumentParser("passa-upgrade")
    parser.add_argument(
        "packages", metavar="package",
        nargs="+",
    )
    parser.add_argument(
        "--strategy",
        choices=["eager", "only-if-needed"],
        default="only-if-needed",
    )
    parser.add_argument(
        "--project", dest="project_root",
        default=os.getcwd(),
        type=os.path.abspath,
    )
    options = parser.parse_args(argv)
    return options


def parsed_main(options):
    from passa.lockers import EagerLocker, Locker
    from passa.projects import Project
    from .lock import lock

    packages = options.packages
    # TODO: Ensure all lines are valid.

    project = Project(options.project_root)
    project.remove_entries_from_lockfile(packages)

    if options.strategy == "eager":
        locker = EagerLocker(project, packages)
    else:
        locker = Locker(project)
    success = lock(locker)
    if not success:
        return

    project._l.write()
    print("Written to project at", project.root)


def main(argv=None):
    options = parse_arguments(argv)
    parsed_main(options)


if __name__ == "__main__":
    main()
