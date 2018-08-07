#!env python
# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import argparse
from .lockfile import get_hashes
import os
from .output import (
    _print_title, _print_dependency, _print_requirement,
    StdOutReporter,
)
from requirementslib import Pipfile, Requirement
from requirementslib.models.cache import HashCache
from requirementslib.utils import temp_cd
from resolvelib import Resolver, NoVersionsAvailable, ResolutionImpossible
from .resolver import RequirementsLibProvider


def resolve(requirements, hash_cache):
    _print_title(' User requirements ')
    for r in requirements:
        _print_requirement(r)
    r = Resolver(RequirementsLibProvider(requirements), StdOutReporter())
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
            _print_requirement(r)
    else:
        _print_title(' STABLE PINS ')
        for k in sorted(state.mapping):
            _print_dependency(state, k)
            print('Hashes: '.format(get_hashes(hash_cache, r, state, k)))

    print()


def cli():
    hash_cache = HashCache()
    parser = argparse.ArgumentParser()
    parser.add_argument('packages', metavar='PACKAGE', nargs='*')
    parser.add_argument('--project', type=os.path.abspath)
    options = parser.parse_args()
    requirements = [Requirement.from_line(line) for line in options.packages]
    if options.project:
        with temp_cd(options.project):
            pipfile = Pipfile.load(options.project)
            requirements.extend(pipfile.dev_packages.requirements)
            requirements.extend(pipfile.packages.requirements)
            resolve(requirements, hash_cache)


if __name__ == "__main__":
    cli()
