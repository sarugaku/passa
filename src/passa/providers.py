# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import requirementslib
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
        return "{0}{1}".format(
            dependency.normalized_name,
            dependency.extras_as_pip,
        )

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirement):
        name = requirement.normalized_name
        if name in self.non_named_requirements:
            # TODO: Need to lock ref for VCS requirements here.
            return [self.non_named_requirements[name]]

        # Markers are intentionally dropped at this step. They will be added
        # back after resolution is done, so we can perform marker aggregation.
        extras = requirement.as_ireq().extras
        candidates = requirement.find_all_matches(sources=self.sources)
        return [
            requirementslib.Requirement.from_metadata(
                name, version, extras, None,
            )
            for version in sorted(c.version for c in candidates)
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
        requirements = [
            requirementslib.Requirement.from_line(d)
            for d in dependencies
        ]
        return requirements
