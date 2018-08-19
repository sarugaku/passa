# -*- coding=utf-8 -*-

# Recommended cases to test:
# * "oslo.utils==1.4.0"
# * "requests" "urllib3<1.21.1"
# * "pylint==1.9" "pylint-quotes==0.1.9"
# * "aiogremlin" "pyyaml"
# * Pipfile from pypa/pipenv#1974 (need to modify a bit)
# * Pipfile from pypa/pipenv#2529-410209718

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import os

from resolvelib import NoVersionsAvailable, ResolutionImpossible

from .projects import Project
from .reporters import print_title, print_requirement


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

    ok = False
    try:
        ok = project.lock(force=True)
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

    if not ok:
        return

    if options.output == "write":
        project.lockfile.write()
        print("Lock file written to", project.lockfile_location)
    if options.output == "print":
        print_title(" LOCK FILE ")
        print(project.lockfile.dumps())


def main(argv=None):
    options = parse_arguments(argv)
    parsed_main(options)


if __name__ == "__main__":
    main()
