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

from requirementslib import Pipfile, Requirement
from requirementslib.models.cache import HashCache
from requirementslib.utils import temp_cd
from resolvelib import Resolver, NoVersionsAvailable, ResolutionImpossible

from .lockfile import build_lockfile, get_hash, trace
from .providers import RequirementsLibProvider
from .reporters import (
    print_title, print_dependency, print_requirement,
    StdOutReporter,
)


def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'requirements', metavar='REQUIREMENT',
        nargs='*', type=Requirement.from_line,
    )
    parser.add_argument('--project', type=os.path.abspath)
    return parser.parse_args(argv)


def resolve(requirements, pipfile=None):
    hash_cache = HashCache()
    provider = RequirementsLibProvider(requirements)
    reporter = StdOutReporter(requirements)

    r = Resolver(provider, reporter)
    try:
        state = r.resolve(requirements)
    except NoVersionsAvailable as e:
        print('\nCANNOT RESOLVE. NO CANDIDATES FOUND FOR:')
        print('{:>40}'.format(e.requirement.as_line()))
        if e.parent:
            print('{:>41}'.format('(from {})'.format(e.parent.as_line())))
        else:
            print('{:>41}'.format('(user)'))
    except ResolutionImpossible as e:
        print('\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:')
        for r in e.requirements:
            print_requirement(r)
    else:
        print_title(' STABLE PINS ')
        lockfile = build_lockfile(r, state, hash_cache, pipfile=pipfile)
        path_lists = trace(state.graph)
        for k in sorted(state.mapping):
            print(state.mapping[k].as_line())
            try:
                paths = path_lists[k]
            except KeyError:
                print('  User requirement')
                continue
            for path in paths:
                print('   ', end='')
                for v in reversed(path):
                    print(' <=', state.mapping[v].as_line(), end='')
                print()
            for h in get_hash(hash_cache, state.mapping[k]):
                print('   ', h)
        print(lockfile.as_dict())


def cli(argv=None):
    options = parse_arguments(argv)
    requirements = list(options.requirements)
    pipfile = None
    with temp_cd(options.project or os.getcwd()):
        if options.project:
            pipfile = Pipfile.load(options.project)
            requirements.extend(pipfile.dev_packages.requirements)
            requirements.extend(pipfile.packages.requirements)
        resolve(requirements, pipfile=pipfile)


if __name__ == "__main__":
    cli()
