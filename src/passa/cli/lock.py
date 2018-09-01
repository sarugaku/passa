# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from ._base import BaseCommand


def main(options):
    from passa.internals.lockers import BasicLocker
    from passa.operations.lock import lock

    project = options.project
    locker = BasicLocker(project)
    success = lock(locker)
    if not success:
        return

    if options.dry_run:
        print(project._l.dumps())
    else:
        project._l.write()
        print("Written to project at", project.root)


class Command(BaseCommand):

    name = "lock"
    description = "Generate Pipfile.lock."
    parsed_main = main

    def add_arguments(self):
        super(Command, self).add_arguments()
        self.parser.add_argument(
            "--dry-run",
            action="store_true", default=False,
            help="run locking on Pipfile, but do not write to Pipfile.lock",
        )


if __name__ == "__main__":
    Command.run_current_module()
