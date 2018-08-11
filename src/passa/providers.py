# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import operator

import packaging.markers
import resolvelib

from requirementslib import Requirement


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
            # TODO: Need to lock ref for VCS requirements here.
            return [self.non_named_requirements[name]]
        ireq = requirement.as_ireq()
        markers = ireq.markers
        extras = ireq.extras
        candidates = sorted(
            requirement.find_all_matches(sources=self.sources),
            key=operator.attrgetter('version'),
        )
        return [
            Requirement.from_metadata(name, c.version, extras, markers)
            for c in candidates
        ]

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
        return requirement.as_ireq().specifier.contains(version)

    def get_dependencies(self, candidate):
        try:
            dependencies = candidate.get_dependencies(sources=self.sources)
        except Exception as e:
            print('failed to get dependencies for {0!r}: {1}'.format(
                candidate.as_line(), e,
            ))
            return []
        ireq = candidate.as_ireq()
        if ireq.markers:
            markers = set(ireq.markers)
        else:
            markers = set()
        requirements = []
        for d in dependencies:
            requirement = Requirement.from_line(d)
            ireq = requirement.as_ireq()
            if ireq.markers and ireq.match_markers():
                markers = markers.add(ireq.markers)
                markers = packaging.markers.Marker(
                    " or ".join(str(m) for m in markers),
                )
                ireq.req.markers = markers
                requirement = Requirement.from_ireq(ireq)
            requirements.append(requirement)
        return requirements
