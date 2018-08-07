# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import operator

from requirementslib import Requirement
from requirementslib.models.utils import make_install_requirement

import resolvelib


class RequirementsLibProvider(resolvelib.AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self, root_requirements):
        self.sources = None
        self.invalid_candidates = set()
        self.non_named_requirements = {
            requirement.name: requirement
            for requirement in root_requirements
            if not requirement.is_named
        }
        # self.hash_cache =

    def identify(self, dependency):
        return dependency.normalized_name

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirement):
        name = requirement.normalized_name
        if name in self.non_named_requirements:
            return [self.non_named_requirements[name]]
        markers = requirement.ireq.markers
        extras = requirement.ireq.extras
        icans = sorted(
            requirement.find_all_matches(sources=self.sources),
            key=operator.attrgetter('version'),
        )
        return [Requirement.from_line(str(make_install_requirement(
            name, ican.version, extras=extras, markers=markers,
        ))) for ican in icans]

    def is_satisfied_by(self, requirement, candidate):
        name = requirement.normalized_name
        if name in self.non_named_requirements:
            return self.non_named_requirements[name] == requirement
        if not requirement.specifiers:  # Short circuit for speed.
            return True
        candidate_line = candidate.as_line()
        if candidate_line in self.invalid_candidates:
            return False
        try:
            version = candidate.get_specifier().version
        except ValueError:
            print('ignoring invalid version {}'.format(candidate_line))
            self.invalid_candidates.add(candidate_line)
            return False
        return requirement.ireq.specifier.contains(version)

    def get_dependencies(self, candidate):
        try:
            dependencies = candidate.get_dependencies(sources=self.sources)
        except Exception as e:
            print('failed to get dependencies for {0!r}: {1}'.format(
                candidate.as_line(), e,
            ))
            return []
        return [
            r for r in (Requirement.from_line(d) for d in dependencies)
            if not r.markers or r.ireq.match_markers()
        ]
