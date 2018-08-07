# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import operator
import packaging.markers
from requirementslib import Requirement
from requirementslib.models.utils import (
    make_install_requirement, format_requirement
)

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
        return [Requirement.from_line(format_requirement(
            make_install_requirement(name, ican.version, extras=extras,
                                      markers=markers)
        )) for ican in icans]

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
        requirements = []
        markers = set(candidate.ireq.markers) if candidate.ireq.markers else set()
        for d in dependencies:
            r = Requirement.from_line(d)
            if r.ireq.markers and r.ireq.match_markers():
                markers = markers.add(r.ireq.markers)
                markers = packaging.markers.Marker(" or ".join([str(m) for m in markers]))
                r.ireq.req.markers = markers
            requirements.append(r)
        return requirements
