# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import os

import requirementslib
import resolvelib

from .dependencies import get_dependencies
from .utils import identify_requirment
from .vcs import set_ref


def _copy_requirement(requirement):
    name, data = next(iter(requirement.as_pipfile().items()))
    return requirementslib.Requirement.from_pipfile(name, data)


def _requirement_from_metadata(name, version, extras, index):
    # Markers are intentionally dropped here. They will be added to candidates
    # after resolution, so we can perform marker aggregation.
    r = requirementslib.Requirement.from_metadata(name, version, extras, None)
    r.index = index
    return r


def _filter_sources(requirement, sources):
    if not sources or not requirement.index:
        return sources
    for s in sources:
        if s.get("name") == requirement.index:
            return [s]
    return sources


class RequirementsLibProvider(resolvelib.AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self, root_requirements, sources):
        self.sources = sources
        self.invalid_candidates = set()
        self.non_named_requirements = {
            self.identify(requirement): _copy_requirement(requirement)
            for requirement in root_requirements
            if not requirement.is_named
        }

        # Remember dependencies of each pinned candidate. The resolver calls
        # `get_dependencies()` only when it wants to repin, so the last time
        # the dependencies we got when it is last called on a package, are
        # the set used by the resolver. We use this later to trace how a given
        # dependency is specified by a package.
        self.fetched_dependencies = {}

    def identify(self, dependency):
        return identify_requirment(dependency)

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirement):
        identifier = self.identify(requirement)
        if identifier in self.non_named_requirements:
            requirement = self.non_named_requirements[identifier]
            if requirement.is_vcs:
                set_ref(requirement)
            return [requirement]

        name = requirement.normalized_name
        extras = requirement.as_ireq().extras
        index = requirement.index
        sources = _filter_sources(requirement, self.sources)
        candidates = requirement.find_all_matches(sources=sources)
        return [
            _requirement_from_metadata(name, version, extras, index)
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
        sources = _filter_sources(candidate, self.sources)
        try:
            dependencies = get_dependencies(candidate, sources=sources)
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
        self.fetched_dependencies[self.identify(candidate)] = {
            self.identify(r): r for r in requirements
        }
        return requirements
