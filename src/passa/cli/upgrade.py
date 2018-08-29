# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import sys

from ._base import BaseCommand


def main(options):
    from passa.lockers import EagerUpgradeLocker, PinReuseLocker
    from passa.operations.lock import lock

    project = options.project
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


class Command(BaseCommand):

    name = "upgrade"
    description = "Upgrade packages in project."
    parsed_main = main

    def add_arguments(self):
        self.parser.add_argument(
            "packages", metavar="package",
            nargs="+",
            help="package to upgrade (can be used multiple times)",
        )
        self.parser.add_argument(
            "--strategy",
            choices=["eager", "only-if-needed"],
            default="only-if-needed",
            help="how dependency upgrading is handled",
        )


if __name__ == "__main__":
    Command.run_current_module()
