# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from ._base import BaseCommand


NAME = "lock"
DESC = "Generate Pipfile.lock."


def lock(locker):
    from passa.reporters import print_requirement
    from resolvelib import NoVersionsAvailable, ResolutionImpossible

    success = False
    try:
        locker.lock()
    except NoVersionsAvailable as e:
        print("\nCANNOT RESOLVE. NO CANDIDATES FOUND FOR:")
        print("{:>40}".format(e.requirement.as_line(include_hashes=False)))
        if e.parent:
            line = e.parent.as_line(include_hashes=False)
            print("{:>41}".format("(from {})".format(line)))
        else:
            print("{:>41}".format("(user)"))
    except ResolutionImpossible as e:
        print("\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:")
        for r in e.requirements:
            print_requirement(r)
    else:
        success = True
    return success


def main(options):
    from passa.lockers import BasicLocker
    from passa.projects import Project

    project = Project(options.project_root)
    locker = BasicLocker(project)
    success = lock(locker)
    if not success:
        return

    project._l.write()
    print("Written to project at", project.root)


class Command(BaseCommand):
    parsed_main = main


if __name__ == "__main__":
    Command.run_current_module()
