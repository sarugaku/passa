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
import collections
import io
import os

import six

from plette import Lockfile, Pipfile
from resolvelib import NoVersionsAvailable, ResolutionImpossible

from .caches import CACHE_DIR
from .locking import build_lockfile
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
    parser.add_argument(
        "--ignore-hashes",
        action="store_true",
        default=False,
        help="Ignore hashes",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print verbose logging to the console",
    )
    parser.add_argument(
        "-i", "--index",
        type=str, nargs="?",
        help="Index to search for packages"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        nargs="?",
        default=CACHE_DIR,
        help="Cache directory to use",
    )
    parser.add_argument(
        "--extra-index", "--extra-index-url",
        type=str,
        action="append",
        help="Extra indexes to search",
    )
    parser.add_argument(
        "--trusted-host",
        type=str,
        action="append",
        help="Addresses where we will skip ssl verification",
    )
    parser.add_argument(
        "--selective-upgrade",
        action="store_true",
        default=False,
        help="Perform a selective upgrade.",
    )
    parser.add_argument(
        "--src", "--src-dir",
        nargs="?",
        type=str,
        help="Location to check out repositories",
    )
    return parser.parse_args(argv)


DEFAULT_NEWLINES = "\n"


def preferred_newlines(f):
    if isinstance(f.newlines, six.text_type):
        return f.newlines
    return DEFAULT_NEWLINES


FileModel = collections.namedtuple("FileModel", "model location newline")

Project = collections.namedtuple("Project", "pipfile lockfile")


def build_project(root):
    pipfile_location = os.path.join(root, "Pipfile")
    with io.open(pipfile_location, encoding="utf-8") as f:
        pipfile = Pipfile.load(f)
        pipfile_le = preferred_newlines(f)

    lockfile_location = os.path.join(root, "Pipfile.lock")
    if os.path.exists(lockfile_location):
        with io.open(lockfile_location, encoding="utf-8") as f:
            lockfile = Lockfile.load(f)
            lockfile_le = preferred_newlines(f)
    else:
        lockfile = None
        lockfile_le = DEFAULT_NEWLINES

    return Project(
        pipfile=FileModel(pipfile, pipfile_location, pipfile_le),
        lockfile=FileModel(lockfile, lockfile_location, lockfile_le),
    )


class BuildFailure(Exception):
    pass


def build_new_lockfile(project):
    try:
        lockfile = build_lockfile(project.pipfile.model)
    except NoVersionsAvailable as e:
        print("\nCANNOT RESOLVE. NO CANDIDATES FOUND FOR:")
        print("{:>40}".format(e.requirement.as_line(include_hashes=False)))
        if e.parent:
            line = e.parent.as_line(include_hashes=False)
            print("{:>41}".format("(from {})".format(line)))
        else:
            print("{:>41}".format("(user)"))
        raise BuildFailure
    except ResolutionImpossible as e:
        print("\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:")
        for r in e.requirements:
            print_requirement(r)
        raise BuildFailure
    return lockfile


def write_lockfile(project):
    location = project.lockfile.location
    newline = project.lockfile.newline
    with io.open(location, "w", encoding="utf-8", newline=newline) as f:
        project.lockfile.model.dump(f)
        f.write("\n")
    print("Lock file written to", location)


def print_lockfile(project):
    print_title(" LOCK FILE ")
    strio = six.StringIO()
    project.lockfile.model.dump(strio)
    print(strio.getvalue())


def parsed_main(options):
    project = build_project(options.project_root)

    cwd = os.getcwd()
    os.chdir(options.project_root)
    try:
        lockfile = build_new_lockfile(project)
    except BuildFailure:
        return
    finally:
        os.chdir(cwd)

    project = project._replace(
        lockfile=project.lockfile._replace(model=lockfile),
    )

    if options.output == "write":
        write_lockfile(project)
    if options.output == "print":
        print_lockfile(project)


def main(argv=None):
    options = parse_arguments(argv)
    parsed_main(options)


if __name__ == "__main__":
    main()
