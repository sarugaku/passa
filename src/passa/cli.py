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
import io
import os

import six

from plette import Lockfile, Pipfile
from requirementslib.utils import temp_cd, temp_environ, fs_str
from resolvelib import NoVersionsAvailable, ResolutionImpossible

from .caches import CACHE_DIR
from .projects import Project
from .reporters import print_title, print_requirement


def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "project_root",
        type=os.path.abspath,
    )
    parser.add_argument(
        "--write",
        action="store_true",
        default=False,
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


def setup_pip(options):
    # XXX: Not working.
    extra_indexes, trusted_hosts, sources = [], [], []
    pipfile = Pipfile.load(options.project)
    sources = [s.expanded.get('url') for s in pipfile.sources]
    trusted_hosts = [
        six.moves.urllib.parse(s.url).hostname
        for s in pipfile.sources
        if not s.verify_ssl
    ]
    if options.index:
        sources.append(options.index)
    if options.extra_index:
        sources.extend(options.extra_index)
    if options.trusted_host:
        trusted_hosts.extend(options.trusted_host)
    for i, source in enumerate(sources):
        if i == 1:
            os.environ["PIP_INDEX"] = fs_str(source)
        else:
            extra_indexes.append(source)
    if trusted_hosts:
        os.environ["PIP_TRUSTED_HOST"] = fs_str(" ".join(trusted_hosts))
    if extra_indexes:
        os.environ["PIP_EXTRA_INDEX_URL"] = fs_str(" ".join(extra_indexes))
    if options.cache_dir:
        os.environ["PIP_CACHE_DIR"] = fs_str(options.cache_dir)
        os.environ["PIP_WHEEL_DIR"] = fs_str("{0}/wheels".format(options.cache_dir))
        os.environ["PIP_DESTINATION_DIR"] = fs_str(
            "{0}/pkgs".format(options.cache_dir)
        )
    if "PIP_SRC" not in os.environ and options.src:
        os.environ["PIP_SRC"] = fs_str(options.src)
    if not options.ignore_hashes:
        os.environ["PIP_REQUIRE_HASHES"] = fs_str("1")
    if options.selective_upgrade:
        os.environ["PIP_UPGRADE"] = fs_str("1")
        os.environ["PIP_UPGRADE_STRATEGY"] = fs_str("only-if-needed")
        os.environ["PIP_EXISTS_ACTION"] = fs_str("w")
    else:
        os.environ["PIP_EXISTS_ACTION"] = fs_str("i")


DEFAULT_NEWLINES = "\n"


def preferred_newlines(f):
    if isinstance(f.newlines, six.text_type):
        return f.newlines
    return DEFAULT_NEWLINES


def resolve(root, write=False):
    with io.open(os.path.join(root, "Pipfile"), encoding="utf-8") as f:
        pipfile = Pipfile.load(f)

    lock_path = os.path.join(root, "Pipfile.lock")
    if os.path.exists(lock_path):
        with io.open(lock_path, encoding="utf-8") as f:
            lockfile = Lockfile.load(f)
            lock_le = preferred_newlines(f)
    else:
        lockfile = None
        lock_le = DEFAULT_NEWLINES

    project = Project(pipfile=pipfile, lockfile=lockfile)

    try:
        project.lock()
    except NoVersionsAvailable as e:
        print("\nCANNOT RESOLVE. NO CANDIDATES FOUND FOR:")
        print("{:>40}".format(e.requirement.as_line(include_hashes=False)))
        if e.parent:
            line = e.parent.as_line(include_hashes=False)
            print("{:>41}".format("(from {})".format(line)))
        else:
            print("{:>41}".format("(user)"))
        return
    except ResolutionImpossible as e:
        print("\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:")
        for r in e.requirements:
            print_requirement(r)
        return

    if write:
        with io.open(lock_path, "w", encoding="utf-8", newline=lock_le) as f:
            project.lockfile.dump(f)
            f.write("\n")
        print("Lock file written to", lock_path)
    else:
        print_title(" LOCK FILE ")
        strio = six.StringIO()
        lockfile.dump(strio)
        print(strio.getvalue())


def cli(argv=None):
    options = parse_arguments(argv)
    with temp_environ(), temp_cd(options.project_root):
        # setup_pip(options)
        resolve(options.project_root, write=options.write)


if __name__ == "__main__":
    cli()
