#!env python
# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from .cli import main
import argparse
import os

from requirementslib import Pipfile, Requirement
from requirementslib.models.cache import HashCache
from requirementlib.utils import temp_cd

if __name__ == "__main__":
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
            main(requirements, hash_cache)
