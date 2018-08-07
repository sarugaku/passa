# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import os

from .lockfile import get_hashes

from requirementslib import Pipfile, Requirement
from requirementslib.models.cache import HashCache
from requirementslib.utils import temp_cd

from resolvelib import Resolver, NoVersionsAvailable, ResolutionImpossible

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


def resolve(requirements):
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
            print('{:>41}'.format('(root dependency)'))
    except ResolutionImpossible as e:
        print('\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:')
        for r in e.requirements:
            print_requirement(r)
    else:
        print_title(' STABLE PINS ')
        for k in sorted(state.mapping):
            print_dependency(state, k)
            # print('Hashes: '.format(get_hashes(hash_cache, r, state, k)))

    print()


def main(argv=None):
    options = parse_arguments(argv)
    requirements = list(options.requirements)
    if options.project:
        pipfile = Pipfile.load(options.project)
        requirements.extend(pipfile.dev_packages.requirements)
        requirements.extend(pipfile.packages.requirements)
    with temp_cd(options.project or os.getcwd()):
        resolve(requirements)
