# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import argparse
import os
import sys


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
    from passa.lockers import EagerUpgradeLocker, PinReuseLocker
    from passa.projects import Project
    from .lock import lock

    project = Project(options.project_root)
    packages = options.packages
    for package in packages:
        if not project.contains_key_in_pipfile(package):
            print("{package!r} not found in Pipfile".format(
                package=package,
            ), file=sys.stderr)
            return 2

    project.remove_entries_from_lockfile(packages)

    if options.strategy == "eager":
        locker = EagerUpgradeLocker(project, packages)
    else:
        locker = PinReuseLocker(project)
    success = lock(locker)
    if not success:
        return 1

    project._l.write()
    print("Written to project at", project.root)


if __name__ == "__main__":
    from ._base import Command
    command = Command(parse_arguments, parsed_main)
    command()
