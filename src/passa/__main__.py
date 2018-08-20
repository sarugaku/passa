# -*- coding=utf-8 -*-

"""Debug-purpose command entry point.

Recommended cases to test:

* "oslo.utils==1.4.0"
* "requests" "urllib3<1.21.1"
* "pylint==1.9" "pylint-quotes==0.1.9"
* "aiogremlin" "pyyaml"
* Pipfile from pypa/pipenv#1974 (need to modify a bit)
* Pipfile from pypa/pipenv#2529-410209718
"""

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import os

from .lockers import BasicLocker
from .projects import Project
from .reporters import print_title

from .cli.lock import lock


def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "project_root",
        type=os.path.abspath,
    )
    parser.add_argument(
        "-o", "--output",
        choices=["write", "print", "none"],
        default="print",
        help="How to output the lockfile",
    )
    return parser.parse_args(argv)


def parsed_main(options):
    project = Project(options.project_root)
    locker = BasicLocker(project)
    success = lock(locker)
    if not success:
        return

    if options.output == "write":
        project._l.write()
        print("Lock file written to", project._l.location)
    if options.output == "print":
        print_title(" LOCK FILE ")
        print(project._l.dumps())


def main(argv=None):
    options = parse_arguments(argv)
    parsed_main(options)


if __name__ == "__main__":
    main()
