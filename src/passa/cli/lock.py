# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import os


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


def parse_arguments(argv):
    parser = argparse.ArgumentParser("passa-lock")
    parser.add_argument(
        "--project", dest="project_root",
        default=os.getcwd(),
        type=os.path.abspath,
    )
    options = parser.parse_args(argv)
    return options


def parsed_main(options):
    from passa.lockers import BasicLocker
    from passa.projects import Project

    project = Project(options.project_root)
    locker = BasicLocker(project)
    success = lock(locker)
    if not success:
        return

    project._l.write()
    print("Written to project at", project.root)


if __name__ == "__main__":
    from ._base import Command
    command = Command(parse_arguments, parsed_main)
    command()
