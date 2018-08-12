# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import os

import requirementslib
import resolvelib

from .utils import identify_requirment


class RequirementsLibProvider(resolvelib.AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self, root_requirements):
        self.sources = None
        self.invalid_candidates = set()
        self.non_named_requirements = {
            self.identify(requirement): requirement
            for requirement in root_requirements
            if not requirement.is_named
        }

    def identify(self, dependency):
        return identify_requirment(dependency)

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirement):
        identifier = self.identify(requirement)
        if identifier in self.non_named_requirements:
            # TODO: Need to lock ref for VCS requirements here.
            return [self.non_named_requirements[identifier]]

        # Markers are intentionally dropped at this step. They will be added
        # back after resolution is done, so we can perform marker aggregation.
        name = requirement.normalized_name
        extras = requirement.as_ireq().extras
        candidates = requirement.find_all_matches(sources=self.sources)
        return [
            requirementslib.Requirement.from_metadata(
                name, version, extras, None,
            )
            for version in sorted(c.version for c in candidates)
        ]

    def is_satisfied_by(self, requirement, candidate):
        # A non-named requirement has exactly one candidate, as implemented in
        # `find_matches()`. It must match.
        if self.identify(requirement) in self.non_named_requirements:
            return True

        # Optimization: Everything matches if there are no specifiers.
        if not requirement.specifiers:
            return True

        # We can't handle old version strings before PEP 440. Drop them all.
        # Practically this shouldn't be a problem if the user is specifying a
        # remotely reasonable dependency not from before 2013.
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
            if os.environ.get("PASSA_NO_SUPPRESS_EXCEPTIONS"):
                raise
            print('failed to get dependencies for {0!r}: {1}'.format(
                candidate.as_line(), e,
            ))
            return []
        requirements = [
            requirementslib.Requirement.from_line(d)
            for d in dependencies
        ]
        return requirements
