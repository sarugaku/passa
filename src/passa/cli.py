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
import json
import os

from requirementslib import Pipfile, Requirement
from requirementslib.models.cache import HashCache, CACHE_DIR
from requirementslib.utils import temp_cd, temp_environ, fs_str
from resolvelib import NoVersionsAvailable, ResolutionImpossible
from six.moves.urllib import parse as urllib_parse

from .lockfile import build_lockfile, trace
from .providers import RequirementsLibProvider
from .reporters import print_title, print_requirement, StdOutReporter
from .resolver import Resolver


def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=os.path.abspath)
    parser.add_argument("--write", action="store_true", default=False)
    parser.add_argument(
        "--ignore-hashes", action="store_true", default=False, help="Ignore hashes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print verbose logging to the console",
    )
    parser.add_argument(
        "-i", "--index", type=str, nargs="?", help="Index to search for packages"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        nargs="?",
        default=CACHE_DIR,
        help="Cache directory to use",
    )
    parser.add_argument(
        "--extra-index",
        "--extra-index-url",
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
        "--src",
        "--src-dir",
        nargs="?",
        type=str,
        help="Location to check out repositories",
    )
    parser.add_argument(
        "requirements",
        nargs="*",
        metavar="REQUIREMENT",
        type=Requirement.from_line,
        help="Packages to install",
    )
    return parser.parse_args(argv)


def resolve(requirements, pipfile=None, write=False):
    hash_cache = HashCache()
    provider = RequirementsLibProvider(requirements)
    reporter = StdOutReporter(requirements)

    r = Resolver(provider, reporter)
    try:
        state = r.resolve(requirements)
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
        print_title(" STABLE PINS ")
        lockfile = build_lockfile(r, state, hash_cache, pipfile=pipfile)
        criteria = r.criteria
        reverse_deps = trace(state.graph)
        for k in sorted(state.mapping):
            print(state.mapping[k].as_line(include_hashes=False))
            paths = reverse_deps[k]
            if paths:
                for path in paths:
                    print("   ", end="")
                    for v in reversed(path):
                        line = state.mapping[v].as_line(include_hashes=False)
                        print(" <=", line, end="")
                    print()
            else:
                print("    User requirement")

        if write:
            lockfile.write()
        else:
            print_title(" LOCK FILE ")
            print(json.dumps(lockfile.as_dict(), indent=4))


def cli(argv=None):
    options = parse_arguments(argv)
    requirements = list(options.requirements)
    pipfile = None
    with temp_environ(), temp_cd(options.project or os.getcwd()):
        extra_indexes, trusted_hosts, sources = [], [], []
        if options.project:
            pipfile = Pipfile.load(options.project)
            sources = [s.expanded.get('url') for s in pipfile.sources]
            trusted_hosts = [
                urllib_parse(s.url).hostname
                for s in pipfile.sources
                if not s.verify_ssl
            ]
            requirements.extend(pipfile.dev_packages.requirements)
            requirements.extend(pipfile.packages.requirements)
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
        resolve(requirements, pipfile=pipfile, write=options.write)


if __name__ == "__main__":
    cli()
